"""Tests for Redis FinOps 2026 Deprecation Remediation and Budget Compliance.

Validates that:
1. Legacy azurerm_redis_cache Basic C0 (deprecated April 1, 2026) is eliminated from IaC.
2. Azure Managed Redis (AMR Balanced B0) / Valkey 8.0 and Standard_LRS are properly configured.
3. FinOps Infracost cost analysis scans Terraform manifests and enforces TCO < $75.00/month.
4. ARM template definitions and FinOps documentation remain strictly synchronized.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.finops_infracost_scan import (
    PRICE_CATALOG,
    CostReport,
    parse_terraform_resources,
    scan_manifest,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
TF_PATH = REPO_ROOT / "deploy" / "azure" / "main.tf"
ARM_PATH = REPO_ROOT / "deploy" / "azure" / "arm_template.json"
FINOPS_SCRIPT = REPO_ROOT / "scripts" / "finops_infracost_scan.py"
DOC_PATH = REPO_ROOT / "configs" / "cloud_architecture_and_cost.md"


def test_terraform_no_deprecated_redis_basic_c0() -> None:
    """Ensure deploy/azure/main.tf contains NO legacy azurerm_redis_cache Basic C0."""
    assert TF_PATH.exists(), f"Terraform manifest not found at {TF_PATH}"
    tf_content = TF_PATH.read_text(encoding="utf-8")

    # Assert legacy resource is completely absent
    assert 'resource "azurerm_redis_cache"' not in tf_content, (
        "Legacy azurerm_redis_cache resource still present in main.tf; "
        "must be migrated to azurerm_redis_enterprise_cluster (AMR) or Valkey."
    )
    assert 'sku_name                      = "Basic"' not in tf_content

    # Assert Azure Managed Redis (AMR Balanced B0) is configured
    assert 'resource "azurerm_redis_enterprise_cluster" "redis"' in tf_content
    assert 'sku_name            = "Balanced_B0"' in tf_content
    assert 'resource "azurerm_redis_enterprise_database" "redis_db"' in tf_content

    # Assert Storage Account replication is Standard_LRS ($2.40/mo)
    assert 'account_replication_type          = "LRS"' in tf_content

    # Assert Container App env vars connect to AMR cluster and database port
    assert "azurerm_redis_enterprise_cluster.redis.hostname" in tf_content
    assert "azurerm_redis_enterprise_database.redis_db.port" in tf_content


def test_arm_template_amr_and_storage_configuration() -> None:
    """Ensure deploy/azure/arm_template.json uses AMR Balanced B0 and Standard_LRS."""
    assert ARM_PATH.exists(), f"ARM template not found at {ARM_PATH}"
    with open(ARM_PATH, encoding="utf-8") as f:
        arm_data = json.load(f)

    resource_types = [r.get("type") for r in arm_data.get("resources", [])]

    # Verify legacy Microsoft.Cache/Redis is removed
    assert "Microsoft.Cache/Redis" not in resource_types, (
        "Legacy Microsoft.Cache/Redis found in arm_template.json; must be Microsoft.Cache/redisEnterprise"
    )

    # Verify Microsoft.Cache/redisEnterprise exists
    assert "Microsoft.Cache/redisEnterprise" in resource_types
    amr_res = next(r for r in arm_data["resources"] if r.get("type") == "Microsoft.Cache/redisEnterprise")
    assert amr_res.get("sku", {}).get("name") == "Balanced_B0"

    # Verify Storage Account is Standard_LRS
    sa_res = next(r for r in arm_data["resources"] if r.get("type") == "Microsoft.Storage/storageAccounts")
    assert sa_res.get("sku", {}).get("name") == "Standard_LRS"

    # Verify Container App environment variables and ports
    app_res = next(r for r in arm_data["resources"] if r.get("type") == "Microsoft.App/containerApps")
    containers = app_res.get("properties", {}).get("template", {}).get("containers", [])
    assert len(containers) > 0
    envs = {e.get("name"): e.get("value") for e in containers[0].get("env", [])}
    assert "Microsoft.Cache/redisEnterprise" in envs.get("REDIS_HOST", "")
    assert envs.get("REDIS_PORT") == "10000"


def test_infracost_scan_direct_api_budget_compliance() -> None:
    """Verify scan_manifest computes TCO < $75.00/mo and passes all budget gates."""
    report: CostReport = scan_manifest(TF_PATH, budget_limit=150.0, student_limit=100.0, course_budget_limit=75.0)

    # Assert total cost is strictly below the $75.00 student course budget
    assert report.total_monthly_usd < 75.00, f"Expected total cost < $75.00/mo, got ${report.total_monthly_usd}"
    assert report.total_monthly_usd > 50.00, f"Expected realistic total cost, got ${report.total_monthly_usd}"
    assert report.within_course_budget is True
    assert report.within_enterprise_budget is True
    assert report.within_student_credit is True
    assert report.course_headroom_usd > 0.0

    # Verify items contain AMR Balanced B0 and Standard_LRS
    res_map = {item.resource_type: item for item in report.items}
    assert "azurerm_redis_enterprise_cluster" in res_map
    assert res_map["azurerm_redis_enterprise_cluster"].sku_or_tier == "Balanced_B0"
    assert res_map["azurerm_redis_enterprise_cluster"].monthly_cost_usd == 12.00

    assert "azurerm_storage_account" in res_map
    assert res_map["azurerm_storage_account"].sku_or_tier == "Standard_LRS"
    assert res_map["azurerm_storage_account"].monthly_cost_usd == 2.40


def test_infracost_scan_cli_table_and_json_output() -> None:
    """Verify CLI execution of finops_infracost_scan.py returns 0 and outputs reports."""
    # Test JSON output
    cmd_json = [sys.executable, str(FINOPS_SCRIPT), "--tf-file", str(TF_PATH), "--format", "json"]
    proc_json = subprocess.run(cmd_json, capture_output=True, text=True, check=True)
    data = json.loads(proc_json.stdout)
    assert data["total_monthly_usd"] < 75.00
    assert data["within_course_budget"] is True

    # Test Table output
    cmd_table = [sys.executable, str(FINOPS_SCRIPT), "--tf-file", str(TF_PATH), "--format", "table"]
    proc_table = subprocess.run(cmd_table, capture_output=True, text=True, check=True)
    output = proc_table.stdout
    assert "TOTAL ESTIMATED MONTHLY COST:" in output
    assert "Cloud FinOps Budget Target ($75.00/mo):" in output
    assert "PASSED" in output
    assert "Balanced_B0" in output


def test_infracost_supports_amr_and_valkey_skus(tmp_path: Path) -> None:
    """Verify scanner supports both AMR Balanced B0 and containerized Valkey 8.0."""
    assert "azurerm_redis_enterprise_cluster" in PRICE_CATALOG
    assert "Balanced_B0" in PRICE_CATALOG["azurerm_redis_enterprise_cluster"]
    assert "valkey" in PRICE_CATALOG["azurerm_container_app"]
    assert "Valkey_8_0" in PRICE_CATALOG["valkey_container_app"]

    # Test scanning synthetic manifest with containerized Valkey 8.0 on ACA
    valkey_tf = tmp_path / "valkey_test.tf"
    valkey_tf.write_text(
        """
        resource "azurerm_container_registry" "acr" {
          sku = "Basic"
        }
        resource "azurerm_storage_account" "sa" {
          account_tier = "Standard"
          account_replication_type = "LRS"
        }
        resource "azurerm_container_app" "valkey_cache" {
          name = "valkey-cache"
          image = "valkey/valkey:8.0-alpine"
        }
        resource "azurerm_container_app" "app" {
          cpu = 1.0
          memory = "2.0Gi"
        }
        resource "azurerm_log_analytics_workspace" "law" {
          sku = "PerGB2018"
        }
        """,
        encoding="utf-8",
    )
    valkey_report = scan_manifest(valkey_tf, course_budget_limit=75.0)
    assert valkey_report.total_monthly_usd == 63.61  # 5 + 2.40 + 5 (valkey) + 46.80 + 4.41
    assert valkey_report.within_course_budget is True


def test_cloud_architecture_documentation_consistency() -> None:
    """Verify configs/cloud_architecture_and_cost.md documents AMR/Valkey and < $75 budget."""
    assert DOC_PATH.exists(), f"Architecture doc not found at {DOC_PATH}"
    doc_text = DOC_PATH.read_text(encoding="utf-8")

    assert "Azure Managed Redis (AMR Balanced B0)" in doc_text
    assert "Valkey 8.0" in doc_text
    assert "01/04/2026" in doc_text
    assert "$70.61/month" in doc_text
    assert "$75.00/month" in doc_text
