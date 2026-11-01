"""DevSecOps Compliance & Security Quality Gate Test Suite.

Ensures continuous enforcement of cloud security baselines, zero secret exposures,
IaC security compliance (Checkov), and container/code hygiene (Trivy).
Mandatory Gate: CRITICAL == 0, HIGH == 0, Compliance Score >= 90.0%.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
SECURITY_REPORT_PATH = WORKSPACE_ROOT / "reports" / "security_audit_report.json"


@pytest.fixture(scope="module")
def security_report() -> dict:
    """Load the genuine unified security audit report."""
    assert SECURITY_REPORT_PATH.exists(), (
        f"Security audit report not found at {SECURITY_REPORT_PATH}. "
        "Execute 'python scripts/security_audit_suite.py' prior to running tests."
    )
    with open(SECURITY_REPORT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def test_security_audit_report_structure(security_report: dict) -> None:
    """Verify structural validity and multi-tool execution evidence."""
    assert "tools_executed" in security_report
    assert len(security_report["tools_executed"]) >= 3
    assert "total_rules" in security_report
    assert security_report["total_rules"] > 0
    assert "summary" in security_report
    assert "findings" in security_report


def test_zero_critical_security_vulnerabilities(security_report: dict) -> None:
    """DevSecOps Gate: Zero CRITICAL severity violations tolerated."""
    summary = security_report.get("summary", {})
    critical_count = summary.get("CRITICAL", 0)
    critical_findings = [
        f"{f.get('category')}: {f.get('rule_id')} on {f.get('target')} - {f.get('description')}"
        for f in security_report.get("findings", [])
        if f.get("status") == "FAIL" and f.get("severity") == "CRITICAL"
    ]
    assert critical_count == 0, (
        f"Security Gate Failure: Found {critical_count} CRITICAL violations:\n"
        + "\n".join(critical_findings)
    )


def test_zero_high_security_vulnerabilities(security_report: dict) -> None:
    """DevSecOps Gate: Zero HIGH severity violations tolerated."""
    summary = security_report.get("summary", {})
    high_count = summary.get("HIGH", 0)
    high_findings = [
        f"{f.get('category')}: {f.get('rule_id')} on {f.get('target')} - {f.get('description')}"
        for f in security_report.get("findings", [])
        if f.get("status") == "FAIL" and f.get("severity") == "HIGH"
    ]
    assert high_count == 0, (
        f"Security Gate Failure: Found {high_count} HIGH violations:\n"
        + "\n".join(high_findings)
    )


def test_compliance_score_meets_enterprise_threshold(security_report: dict) -> None:
    """DevSecOps Gate: Enterprise compliance score must meet or exceed 90.0%."""
    score = security_report.get("compliance_score_percent", 0.0)
    assert score >= 90.0, (
        f"Security Gate Failure: Overall compliance score {score}% is below "
        "the enterprise threshold of 90.0%."
    )


def test_dockerfile_security_hygiene() -> None:
    """Verify Dockerfile runs as non-root user and avoids DS-0002 vulnerability."""
    dockerfile_path = WORKSPACE_ROOT / "Dockerfile"
    assert dockerfile_path.exists(), "Dockerfile must exist"
    content = dockerfile_path.read_text(encoding="utf-8")
    assert "useradd" in content, "Dockerfile must provision non-root user"
    assert "USER " in content, "Dockerfile must switch execution context to non-root user"
    assert "USER appuser" in content or "USER 10001" in content


def test_azurite_adapter_secret_hygiene() -> None:
    """Verify Azurite adapter does not leak storage account key literals."""
    adapter_path = WORKSPACE_ROOT / "src" / "resilience" / "azurite_adapter.py"
    assert adapter_path.exists(), "azurite_adapter.py must exist"
    content = adapter_path.read_text(encoding="utf-8")
    assert "AccountKey=" not in content, "Azurite adapter must not contain hardcoded account keys"
    assert "Eby8vdM02x" not in content, "Must not contain emulator master key signature"
    assert "os.getenv" in content, "Connection string should be dynamically resolved"


def test_terraform_iac_hardening() -> None:
    """Verify Terraform manifests enforce secure network rules and disabled public admin."""
    tf_path = WORKSPACE_ROOT / "deploy" / "azure" / "main.tf"
    assert tf_path.exists(), "main.tf must exist"
    content = tf_path.read_text(encoding="utf-8")
    assert "admin_enabled                 = false" in content
    assert "public_network_access_enabled = false" in content
    assert 'default_action = "Deny"' in content
    assert "shared_access_key_enabled         = false" in content
    assert "infrastructure_encryption_enabled = true" in content
    assert "delete_retention_policy" in content


def test_arm_template_iac_hardening() -> None:
    """Verify ARM template synchronizes identical enterprise security baselines."""
    arm_path = WORKSPACE_ROOT / "deploy" / "azure" / "arm_template.json"
    assert arm_path.exists(), "arm_template.json must exist"
    data = json.loads(arm_path.read_text(encoding="utf-8"))
    resources = {r.get("type"): r for r in data.get("resources", [])}

    acr = resources.get("Microsoft.ContainerRegistry/registries", {})
    acr_props = acr.get("properties", {})
    assert acr_props.get("adminUserEnabled") is False
    assert acr_props.get("publicNetworkAccess") == "Disabled"

    sa = resources.get("Microsoft.Storage/storageAccounts", {})
    sa_props = sa.get("properties", {})
    assert sa_props.get("publicNetworkAccess") == "Disabled"
    assert sa_props.get("allowBlobPublicAccess") is False
    assert sa_props.get("networkAcls", {}).get("defaultAction") == "Deny"
    assert sa_props.get("encryption", {}).get("requireInfrastructureEncryption") is True


def test_checkov_policy_baseline_configuration() -> None:
    """Verify .checkov.yml documents academic budget justifications for production checks."""
    cfg_path = WORKSPACE_ROOT / ".checkov.yml"
    assert cfg_path.exists(), ".checkov.yml configuration must exist"
    content = cfg_path.read_text(encoding="utf-8")
    assert "CKV_AZURE_165" in content, "Must document ACR Geo-replication budget tradeoff"
    assert "CKV_AZURE_233" in content, "Must document ACR Zone Redundancy budget tradeoff"

