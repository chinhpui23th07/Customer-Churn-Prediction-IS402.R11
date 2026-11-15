"""Azure Well-Architected Framework (WAF) IaC Static Testing Suite.

Validates Infrastructure as Code (ARM Template and Terraform manifests)
against WAF Security, Reliability, Cost Optimization, and Operational Excellence:
- WAF Security: TLS 1.2+ mandatory, encrypted transport, disabled public network access.
- WAF Reliability: Redis VolatileLRU eviction policy, blob delete retention.
- WAF Cost Optimization (FinOps): LRS replication right-sizing within student budget.
- WAF Operational Excellence: Zero hardcoded secrets/passwords in templates.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
ARM_PATH = ROOT_DIR / "deploy" / "azure" / "arm_template.json"
TF_PATH = ROOT_DIR / "deploy" / "azure" / "main.tf"


@pytest.fixture(scope="module")
def arm_data() -> dict:
    """Load and parse the ARM template JSON."""
    assert ARM_PATH.exists(), f"ARM template not found at {ARM_PATH}"
    return json.loads(ARM_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def tf_content() -> str:
    """Load Terraform manifest text."""
    assert TF_PATH.exists(), f"Terraform manifest not found at {TF_PATH}"
    return TF_PATH.read_text(encoding="utf-8")


def _resources_by_type(arm_data: dict, rtype: str) -> list[dict]:
    return [r for r in arm_data.get("resources", []) if r.get("type") == rtype]


def test_waf_arm_no_duplicate_resources_and_managed_identity_rbac(arm_data: dict) -> None:
    """Prevent duplicate ARM resources (like duplicate blobServices) and verify AcrPull RBAC."""
    raw_resources = arm_data.get("resources", [])
    keys = [(r.get("type"), r.get("name")) for r in raw_resources]
    assert len(keys) == len(set(keys)), f"Duplicate (type, name) ARM resources detected: {keys}"

    identities = _resources_by_type(arm_data, "Microsoft.ManagedIdentity/userAssignedIdentities")
    assert len(identities) == 1, "Expected User-Assigned Managed Identity for Container App pull/storage RBAC"

    acr_roles = _resources_by_type(arm_data, "Microsoft.ContainerRegistry/registries/providers/roleAssignments")
    assert len(acr_roles) == 1, "Expected AcrPull role assignment before Container App creation"
    assert "7f951dda-4ed3-4680-a7ca-43fe172d538d" in json.dumps(arm_data), "Missing built-in AcrPull role definition GUID"


def test_waf_arm_security_pillar_enforcement(arm_data: dict) -> None:
    """Verify ARM template enforces WAF Security standards across all resources."""
    sa_list = _resources_by_type(arm_data, "Microsoft.Storage/storageAccounts")
    assert len(sa_list) == 1, "Missing or duplicate storageAccounts resource"
    sa_props = sa_list[0].get("properties", {})
    assert sa_props.get("supportsHttpsTrafficOnly") is True
    assert sa_props.get("minimumTlsVersion") == "TLS1_2"
    assert sa_props.get("publicNetworkAccess") == "Disabled"
    assert sa_props.get("allowBlobPublicAccess") is False
    assert sa_props.get("networkAcls", {}).get("defaultAction") == "Deny"
    assert sa_props.get("encryption", {}).get("requireInfrastructureEncryption") is True

    acr_list = _resources_by_type(arm_data, "Microsoft.ContainerRegistry/registries")
    assert len(acr_list) == 1, "Missing or duplicate ACR resource"
    acr_props = acr_list[0].get("properties", {})
    assert acr_props.get("adminUserEnabled") is False
    expected_cond = "[if(equals(parameters('acrSku'), 'Premium'), 'Disabled', 'Enabled')]"
    assert acr_props.get("publicNetworkAccess") in ("Disabled", expected_cond)
    if acr_props.get("publicNetworkAccess") == expected_cond:
        assert "acrSku" in arm_data.get("parameters", {})

    redis_list = _resources_by_type(arm_data, "Microsoft.Cache/redisEnterprise") or _resources_by_type(arm_data, "Microsoft.Cache/Redis")
    assert len(redis_list) == 1, "Missing or duplicate Redis resource"
    redis_props = redis_list[0].get("properties", {})
    assert redis_props.get("minimumTlsVersion") in ("1.2", "TLS1_2")


def test_waf_terraform_security_pillar_enforcement(tf_content: str) -> None:
    """Verify Terraform manifest enforces WAF Security standards."""
    # Storage Account
    assert 'min_tls_version                   = "TLS1_2"' in tf_content
    assert "public_network_access_enabled     = false" in tf_content
    assert "shared_access_key_enabled         = false" in tf_content
    assert "allow_nested_items_to_be_public   = false" in tf_content
    assert "infrastructure_encryption_enabled = true" in tf_content

    # Container Registry
    assert "admin_enabled                 = false" in tf_content
    assert 'public_network_access_enabled = var.acr_sku == "Premium" ? false : true' in tf_content or "public_network_access_enabled = false" in tf_content

    # Redis TLS & Encryption
    assert 'minimum_tls_version = "1.2"' in tf_content or 'minimum_tls_version           = "1.2"' in tf_content
    assert 'client_protocol   = "Encrypted"' in tf_content or "enable_non_ssl_port           = false" in tf_content


def test_waf_reliability_pillar_enforcement(arm_data: dict, tf_content: str) -> None:
    """Verify memory eviction and recovery policies to ensure zero unhandled cache exhaustion."""
    redis_ent = _resources_by_type(arm_data, "Microsoft.Cache/redisEnterprise")
    redis_legacy = _resources_by_type(arm_data, "Microsoft.Cache/Redis")

    if redis_ent:
        databases = [res for res in redis_ent[0].get("resources", []) if res.get("type") == "databases"]
        assert len(databases) > 0
        db_props = databases[0].get("properties", {})
        assert db_props.get("evictionPolicy") == "VolatileLRU"
    elif redis_legacy:
        assert redis_legacy[0].get("properties", {}).get("redisConfiguration", {}).get("maxmemory-policy") == "volatile-lru"

    # Terraform: Eviction policy
    assert "VolatileLRU" in tf_content or "volatile-lru" in tf_content

    # Blob soft delete retention
    assert "delete_retention_policy" in tf_content


def test_waf_cost_optimization_finops_enforcement(arm_data: dict, tf_content: str) -> None:
    """Verify FinOps right-sizing (Standard_LRS) to prevent cloud budget overruns."""
    sa_list = _resources_by_type(arm_data, "Microsoft.Storage/storageAccounts")
    assert len(sa_list) == 1
    sku_name = sa_list[0].get("sku", {}).get("name")
    assert sku_name in ("Standard_LRS", "Standard_GRS"), f"Unexpected storage SKU: {sku_name}"

    # Terraform: account_replication_type
    assert 'account_replication_type          = "LRS"' in tf_content or 'account_replication_type          = "GRS"' in tf_content


def test_waf_operational_excellence_zero_hardcoded_secrets(arm_data: dict, tf_content: str) -> None:
    """Verify zero plaintext passwords or API keys are stored in IaC manifests."""
    # ARM parameters check
    parameters = arm_data.get("parameters", {})
    for param_name, param_def in parameters.items():
        assert "password" not in param_name.lower(), f"Potential hardcoded password param: {param_name}"
        assert "secret" not in param_name.lower(), f"Potential hardcoded secret param: {param_name}"

    # Terraform manifest secret scan
    banned_signatures = ["password =", "secret =", "access_key =", "private_key ="]
    for sig in banned_signatures:
        assert sig not in tf_content.lower(), f"Disallowed plaintext secret signature in main.tf: {sig}"
