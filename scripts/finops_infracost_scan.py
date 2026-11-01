#!/usr/bin/env python3
"""FinOps Shift-Left Cost Analysis Scanner (Infracost-inspired).

Scans Terraform HCL manifests (deploy/azure/main.tf) to calculate cloud costs,
evaluate budget limits ($150 enterprise / $100 Azure for Students), and output
actionable cost breakdown reports in JSON and tabular formats.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class CostItem:
    resource_type: str
    resource_name: str
    sku_or_tier: str
    monthly_cost_usd: float
    unit_description: str
    notes: str


@dataclass
class CostReport:
    manifest_path: str
    items: List[CostItem]
    total_monthly_usd: float
    enterprise_budget_usd: float
    student_credit_usd: float
    within_enterprise_budget: bool
    within_student_credit: bool
    enterprise_headroom_usd: float
    student_headroom_usd: float


PRICE_CATALOG = {
    "azurerm_container_registry": {
        "Basic": (5.00, "1 registry instance / month", "Basic SKU (10GB included storage)"),
        "Standard": (20.00, "1 registry instance / month", "Standard SKU (100GB storage)"),
        "Premium": (150.00, "1 registry instance / month", "Premium SKU with geo-replication"),
    },
    "azurerm_storage_account": {
        "Standard_LRS": (2.40, "~100GB hot data + 50k ops", "Locally-redundant hot blob storage"),
        "Standard_GRS": (4.80, "~100GB hot data geo-replicated", "Geo-redundant blob storage"),
    },
    "azurerm_redis_cache": {
        "Basic_C0": (16.06, "250MB cache node / month", "Basic C0 single node cache"),
        "Basic_C1": (40.15, "1GB cache node / month", "Basic C1 single node cache"),
        "Standard_C0": (32.12, "250MB replicated pair / month", "Standard C0 high-availability pair"),
    },
    "azurerm_container_app": {
        "default": (46.80, "1.0 vCPU + 2.0GiB RAM (~100k req/mo)", "Container Apps active consumption"),
    },
    "azurerm_log_analytics_workspace": {
        "PerGB2018": (4.41, "~1.5 GB ingestion / month", "Per-GB ingestion + 30-day retention"),
    },
}


def parse_terraform_resources(tf_content: str) -> List[Dict[str, str]]:
    pattern = r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{([^}]*)\}'
    matches = re.finditer(pattern, tf_content, re.DOTALL)
    resources: List[Dict[str, str]] = []
    for m in matches:
        rtype = m.group(1)
        rname = m.group(2)
        body = m.group(3)
        resources.append({"type": rtype, "name": rname, "body": body})
    return resources


def scan_manifest(tf_path: Path, budget_limit: float = 150.0, student_limit: float = 100.0) -> CostReport:
    if not tf_path.exists():
        raise FileNotFoundError(f"Terraform manifest not found: {tf_path}")

    content = tf_path.read_text(encoding="utf-8")
    raw_resources = parse_terraform_resources(content)
    cost_items: List[CostItem] = []

    for r in raw_resources:
        rtype = r["type"]
        rname = r["name"]
        body = r["body"]

        if rtype == "azurerm_container_registry":
            sku_m = re.search(r'sku\s*=\s*"([^"]+)"', body)
            sku = sku_m.group(1) if sku_m else "Basic"
            cost, unit, notes = PRICE_CATALOG["azurerm_container_registry"].get(sku, (5.00, "1 instance", "ACR"))
            cost_items.append(CostItem(rtype, rname, sku, cost, unit, notes))

        elif rtype == "azurerm_storage_account":
            tier_m = re.search(r'account_tier\s*=\s*"([^"]+)"', body)
            repl_m = re.search(r'account_replication_type\s*=\s*"([^"]+)"', body)
            sku = f"{tier_m.group(1) if tier_m else 'Standard'}_{repl_m.group(1) if repl_m else 'LRS'}"
            cost, unit, notes = PRICE_CATALOG["azurerm_storage_account"].get(sku, (2.40, "hot blob", "Storage"))
            cost_items.append(CostItem(rtype, rname, sku, cost, unit, notes))

        elif rtype == "azurerm_redis_cache":
            sku_m = re.search(r'sku_name\s*=\s*"([^"]+)"', body)
            family_m = re.search(r'family\s*=\s*"([^"]+)"', body)
            cap_m = re.search(r'capacity\s*=\s*([0-9]+)', body)
            sku = f"{sku_m.group(1) if sku_m else 'Basic'}_{family_m.group(1) if family_m else 'C'}{cap_m.group(1) if cap_m else '0'}"
            cost, unit, notes = PRICE_CATALOG["azurerm_redis_cache"].get(sku, (16.06, "redis cache", "Redis"))
            cost_items.append(CostItem(rtype, rname, sku, cost, unit, notes))

        elif rtype == "azurerm_container_app":
            cpu_m = re.search(r'cpu\s*=\s*([0-9.]+)', body)
            mem_m = re.search(r'memory\s*=\s*"([^"]+)"', body)
            sku = f"{cpu_m.group(1) if cpu_m else '1.0'} vCPU, {mem_m.group(1) if mem_m else '2.0Gi'}"
            cost, unit, notes = PRICE_CATALOG["azurerm_container_app"]["default"]
            cost_items.append(CostItem(rtype, rname, sku, cost, unit, notes))

        elif rtype == "azurerm_log_analytics_workspace":
            sku_m = re.search(r'sku\s*=\s*"([^"]+)"', body)
            sku = sku_m.group(1) if sku_m else "PerGB2018"
            cost, unit, notes = PRICE_CATALOG["azurerm_log_analytics_workspace"].get(sku, (4.41, "ingestion", "LAW"))
            cost_items.append(CostItem(rtype, rname, sku, cost, unit, notes))

    total = sum(item.monthly_cost_usd for item in cost_items)
    return CostReport(
        manifest_path=str(tf_path),
        items=cost_items,
        total_monthly_usd=round(total, 2),
        enterprise_budget_usd=budget_limit,
        student_credit_usd=student_limit,
        within_enterprise_budget=(total <= budget_limit),
        within_student_credit=(total <= student_limit),
        enterprise_headroom_usd=round(budget_limit - total, 2),
        student_headroom_usd=round(student_limit - total, 2),
    )


def format_table(report: CostReport) -> str:
    lines = [
        "=" * 85,
        "FINOPS SHIFT-LEFT CLOUD COST ANALYSIS (Infracost Benchmark Standard)",
        f"Manifest: {report.manifest_path}",
        "-" * 85,
        f"{'RESOURCE TYPE':<32} {'SKU / CONFIG':<18} {'EST. COST/MO':>14}  {'UNIT / NOTE'}",
        "-" * 85,
    ]
    for it in report.items:
        lines.append(f"{it.resource_type:<32} {it.sku_or_tier:<18} ${it.monthly_cost_usd:>10.2f}/mo  {it.notes}")
    lines.extend([
        "-" * 85,
        f"{'TOTAL ESTIMATED MONTHLY COST:':<51} ${report.total_monthly_usd:>10.2f}/mo",
        f"{'Enterprise Budget Target ($150.00/mo):':<51} {'PASSED (Headroom: $' + str(report.enterprise_headroom_usd) + ')' if report.within_enterprise_budget else 'EXCEEDED'}",
        f"{'Azure for Students Credit ($100.00/mo):':<51} {'PASSED (Headroom: $' + str(report.student_headroom_usd) + ')' if report.within_student_credit else 'EXCEEDED'}",
        "=" * 85,
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="FinOps Infracost-inspired cost scanner for Terraform.")
    parser.add_argument("--tf-file", default="deploy/azure/main.tf", help="Path to Terraform manifest.")
    parser.add_argument("--budget-limit", type=float, default=150.0, help="Enterprise budget limit.")
    parser.add_argument("--student-limit", type=float, default=100.0, help="Student credit budget limit.")
    parser.add_argument("--format", choices=["table", "json"], default="table", help="Output format.")
    parser.add_argument("--output-json", default=None, help="Save JSON report to file.")
    args = parser.parse_args()

    tf_path = Path(args.tf_file)
    try:
        report = scan_manifest(tf_path, args.budget_limit, args.student_limit)
    except Exception as exc:
        print(f"Error scanning manifest: {exc}", file=sys.stderr)
        return 1

    report_dict = asdict(report)
    if args.output_json:
        out_p = Path(args.output_json)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(report_dict, indent=2), encoding="utf-8")

    if args.format == "json":
        print(json.dumps(report_dict, indent=2))
    else:
        print(format_table(report))

    return 0 if (report.within_enterprise_budget and report.within_student_credit) else 2


if __name__ == "__main__":
    sys.exit(main())
