"""
Module Thanh tra Vạch trần Mã Giả, Tác vụ Rỗng và Điểm Nghẽn Kiến Trúc.
Nhiệm vụ: Phát hiện các điểm vi phạm liêm chính học thuật (stubs, mocks, echo deploy, local downgrades).
"""
import os
import sys
import json
import re

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class StubAndIntegrityDetector:
    def __init__(self):
        self.findings = []
        self.critical_count = 0
        self.warning_count = 0

    def add_finding(self, severity: str, category: str, file_path: str, line_no: int, issue: str, evidence: str):
        finding = {
            "severity": severity,
            "category": category,
            "file": os.path.relpath(file_path, BASE_DIR).replace("\\", "/"),
            "line": line_no,
            "issue": issue,
            "evidence": evidence.strip()
        }
        self.findings.append(finding)
        if severity == "CRITICAL":
            self.critical_count += 1
        else:
            self.warning_count += 1

    def audit_routes_management(self):
        """Thanh tra endpoint /api/v1/trigger_retrain: kiểm tra xem có chạy retrain thật hay chỉ in JSON."""
        target = os.path.join(BASE_DIR, "src", "api", "routes_management.py")
        if not os.path.exists(target):
            return
        with open(target, "r", encoding="utf-8") as f:
            lines = f.readlines()

        in_retrain = False
        retrain_start = 0
        retrain_body = []
        for i, line in enumerate(lines, 1):
            if "def trigger_retraining" in line:
                in_retrain = True
                retrain_start = i
            elif in_retrain and (line.startswith("def ") or line.startswith("@router.")):
                in_retrain = False
            elif in_retrain:
                retrain_body.append((i, line))

        # Kiểm tra xem thân hàm có gọi train_pipeline hoặc subprocess hoặc celery/background không
        has_train_call = any("train" in line.lower() and "import" not in line and "run_drift" not in line for _, line in retrain_body)
        has_subprocess = any("subprocess" in line or "os.system" in line for _, line in retrain_body)
        has_dispatch = any("dispatch" in line or "webhook" in line for _, line in retrain_body)

        if not (has_train_call or has_subprocess or has_dispatch):
            self.add_finding(
                severity="CRITICAL",
                category="TÁC VỤ RỖNG (STUB)",
                file_path=target,
                line_no=retrain_start,
                issue="Endpoint /api/v1/trigger_retrain là hàm rỗng, chỉ in chuỗi JSON tĩnh mà không kích hoạt tái huấn luyện thật",
                evidence="Hàm chỉ trả về {'status': 'TRIGGERED', 'message': '...'} mà không hề gọi train_pipeline.py hay gửi webhook."
            )

    def audit_github_workflow(self):
        """Thanh tra CI/CD workflow: Runner có phải self-hosted không, CD deploy có phải lệnh echo không."""
        target = os.path.join(BASE_DIR, ".github", "workflows", "mlops_ci.yml")
        if not os.path.exists(target):
            self.add_finding("CRITICAL", "THIẾU TỆP", target, 0, "Không tìm thấy file workflow CI/CD", "")
            return

        with open(target, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            if "runs-on:" in line and "ubuntu-latest" in line:
                self.add_finding(
                    severity="CRITICAL",
                    category="SAI ĐẶC TẢ ĐỀ BÀI",
                    file_path=target,
                    line_no=i,
                    issue="Đề bài yêu cầu 'Self-hosted Runner trong Github Actions' nhưng workflow đang dùng 'ubuntu-latest'",
                    evidence=line
                )
            if "echo" in line and ("Triển khai" in line or "Healthy" in line or "CD Pipeline" in line):
                self.add_finding(
                    severity="CRITICAL",
                    category="TRIỂN KHAI GIẢ LẬP (MOCK DEPLOY)",
                    file_path=target,
                    line_no=i,
                    issue="Bước CD Deploy chỉ chạy lệnh 'echo' mô phỏng bằng văn bản, không hề triển khai container thật",
                    evidence=line
                )

    def audit_feast_configuration(self):
        """Thanh tra cấu hình Feast: kiểm tra Online Store có phải Redis như sơ đồ đề bài hay hạ cấp về SQLite."""
        target = os.path.join(BASE_DIR, "data", "feast_repo", "feature_store.yaml")
        if not os.path.exists(target):
            self.add_finding("CRITICAL", "THIẾU CẤU HÌNH", target, 0, "Không tìm thấy feature_store.yaml của Feast", "")
            return

        with open(target, "r", encoding="utf-8") as f:
            content = f.read()

        if "type: sqlite" in content:
            self.add_finding(
                severity="CRITICAL",
                category="HẠ CẤP KIẾN TRÚC (ARCHITECTURAL DOWNGRADE)",
                file_path=target,
                line_no=7,
                issue="Sơ đồ Đề tài 11 yêu cầu Feast Online Store là Redis (In-Memory), nhưng thực tế đang cấu hình SQLite cục bộ",
                evidence="online_store:\n  type: sqlite\n  path: data/online_store.db"
            )

    def audit_dvc_remote(self):
        """Thanh tra DVC Remote: kiểm tra xem có kết nối Storage Cloud hay chỉ lưu ổ cứng cục bộ."""
        target = os.path.join(BASE_DIR, ".dvc", "config")
        has_cloud_remote = False
        evidence = "Không có remote cloud nào được cấu hình."
        if os.path.exists(target):
            with open(target, "r", encoding="utf-8") as f:
                content = f.read()
                evidence = content
                if "azure://" in content or "s3://" in content or "gs://" in content:
                    has_cloud_remote = True

        if not has_cloud_remote:
            self.add_finding(
                severity="CRITICAL",
                category="THIẾU CLOUD STORAGE",
                file_path=target if os.path.exists(target) else os.path.join(BASE_DIR, ".dvc"),
                line_no=1,
                issue="Rubric yêu cầu 'Lưu trữ vào trong Storage Cloud', nhưng DVC remote hoàn toàn không có Azure Blob hay S3",
                evidence=evidence
            )

    def audit_latency_measurement(self):
        """Thanh tra kịch bản đo độ trễ: kiểm tra xem có dựng server ở region khác hay chỉ ping ké."""
        target = os.path.join(BASE_DIR, "src", "data", "latency_simulator.py")
        if not os.path.exists(target):
            return
        with open(target, "r", encoding="utf-8") as f:
            content = f.read()

        if "dynamodb" in content and "amazonaws.com" in content:
            self.add_finding(
                severity="CRITICAL",
                category="LÁCH LUẬT THỰC NGHIỆM (WORKAROUND)",
                file_path=target,
                line_no=24,
                issue="Rubric yêu cầu 'Đo độ trễ khi thiết lập server ở vùng region khác', nhưng script chỉ lấy laptop ping vào domain Amazon DynamoDB",
                evidence="endpoint: dynamodb.ap-southeast-1.amazonaws.com"
            )

    def audit_web_static_table(self):
        """Thanh tra web UI: kiểm tra xem bảng so sánh model có bị hardcode HTML tĩnh hay không."""
        target = os.path.join(BASE_DIR, "src", "web", "index.html")
        if not os.path.exists(target):
            return
        with open(target, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            if "Random Forest (Champion)" in line and "0.9940" in line:
                self.add_finding(
                    severity="WARNING",
                    category="SỐ LIỆU TĨNH HARDCODED TRÊN WEB",
                    file_path=target,
                    line_no=i,
                    issue="Bảng so sánh 4 mô hình trên giao diện Web bị hardcode sẵn các số liệu HTML tĩnh thay vì vẽ biểu đồ động",
                    evidence=line
                )
                break

    def run_all_audits(self):
        self.audit_routes_management()
        self.audit_github_workflow()
        self.audit_feast_configuration()
        self.audit_dvc_remote()
        self.audit_latency_measurement()
        self.audit_web_static_table()

        return {
            "total_findings": len(self.findings),
            "critical_violations": self.critical_count,
            "warnings": self.warning_count,
            "findings": self.findings
        }


if __name__ == "__main__":
    detector = StubAndIntegrityDetector()
    report = detector.run_all_audits()
    print("=" * 80)
    print("BÁO CÁO THANH TRA VẠCH TRẦN MÃ GIẢ VÀ TÁC VỤ RỖNG (STUB DETECTOR)")
    print("=" * 80)
    print(f"[!] Tổng số vi phạm phát hiện: {report['total_findings']}")
    print(f"[!] Vi phạm mức NGUY CẤP (CRITICAL): {report['critical_violations']}")
    print(f"[!] Cảnh báo mức TRUNG BÌNH (WARNING): {report['warnings']}")
    print("-" * 80)
    for idx, f in enumerate(report["findings"], 1):
        print(f"[{idx}] [{f['severity']}] {f['category']}")
        print(f"    Tệp: {f['file']} (Dòng {f['line']})")
        print(f"    Vấn đề: {f['issue']}")
        print(f"    Bằng chứng: {f['evidence'][:120]}...")
        print()
