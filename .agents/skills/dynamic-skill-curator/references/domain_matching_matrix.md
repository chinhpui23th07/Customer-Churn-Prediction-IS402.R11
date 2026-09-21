# Domain Matching Matrix (Bảng Tra Cứu Tự Động Kỹ Năng)

Bảng quy chiếu giúp Agent tự động phát hiện và chọn kỹ năng dựa trên các file manifest trong thư mục gốc.

## 1. Bảng Quy Chiếu Tự Động Theo Manifest

| Tập Tin Định Danh / Cấu Hình | Nhận Diện Công Nghệ | Bộ Kỹ Năng Khuyên Dùng |
| :--- | :--- | :--- |
| `package.json` (chứa `next`, `react`, `tailwindcss`) | Fullstack React/Next.js | `ui-ux-pro-max`, `react-patterns`, `nextjs-best-practices`, `tailwind-patterns` |
| `package.json` (chứa `hardhat`, `ethers`, `@openzeppelin`) | Web3 / Smart Contracts | `genomics-smart-contracts`, `web3-testing`, `web3-portal-orchestrator` |
| `requirements.txt` / `pyproject.toml` (chứa `fastapi`, `uvicorn`) | FastAPI REST Engine | `fastapi-pro`, `python-pro`, `database-admin`, `security-auditor` |
| `requirements.txt` (chứa `torch`, `transformers`, `langchain`) | AI Engine / LLM App | `machine-learning-ops-ml-pipeline`, `embedding-strategies`, `llm-app-patterns` |
| `Cargo.toml` | Rust Systems / High-perf | `rust-pro`, `systems-programming-rust-project` |
| `go.mod` | Go Microservices | `golang-pro`, `database-admin`, `architect-review` |
| `pom.xml` / `build.gradle` | Java / Spring Boot | `java-pro`, `database-admin`, `security-auditor` |
| `pubspec.yaml` | Flutter Cross-Platform | `flutter-expert`, `ui-ux-pro-max`, `mobile-design` |
| `Dockerfile` / `docker-compose.yml` | Containerized App | `docker-expert`, `security-auditor`, `architect-review` |

## 2. Quy Tắc Kết Hợp Mặc Định
Bất kể dự án nào, Agent nên luôn kết hợp ít nhất 3 tầng kỹ năng:
1. **Tầng Kỹ Thuật Cốt Lõi (Core Tech):** Ví dụ `fastapi-pro` hoặc `react-patterns`.
2. **Tầng Trải Nghiệm Hoặc Lưu Trữ (UI/UX hoặc DB):** Ví dụ `ui-ux-pro-max` hoặc `database-admin`.
3. **Tầng Chất Lượng & Bảo Mật (Quality & Security):** `tdd-workflow` hoặc `security-auditor`.
