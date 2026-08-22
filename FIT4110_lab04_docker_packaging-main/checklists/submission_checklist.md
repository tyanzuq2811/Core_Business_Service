# Submission Checklist — Lab 04 (Core Business Service)

Danh mục các artefact cần nộp và bàn giao cho **Core Business Service**:

- [x] `Dockerfile` — File đóng gói multi-stage, non-root, native healthcheck.
- [x] `.dockerignore` — Loại bỏ context rác khi build image.
- [x] `.env.example` — Mẫu biến môi trường mặc định an toàn.
- [x] `RUN_LOCAL.md` — Tài liệu hướng dẫn chạy và kiểm thử cục bộ trong 3–5 bước.
- [x] `README.md` — Tài liệu tổng quan về Core Business Service.
- [x] `.spectral.yaml` — Quy chuẩn kiểm tra OpenAPI 3.1.0 contract.
- [x] `contracts/core-business.openapi.yaml` — Hợp đồng OpenAPI 3.1.0 của Core Business.
- [x] `src/core_app/` — Mã nguồn backend FastAPI xử lý nghiệp vụ.
- [x] `postman/collections/FIT4110_lab04_core_business.postman_collection.json` — Bộ test Postman 24 requests.
- [x] `postman/environments/FIT4110_lab04_core_local.postman_environment.json` — Environment kiểm thử container.
- [x] `reports/newman-lab04-local.xml` — Báo cáo kết quả kiểm thử JUnit XML.
- [x] `reports/newman-lab04-local.html` — Báo cáo kết quả kiểm thử HTML trực quan.
- [x] `.github/workflows/docker-newman.yml` — Kịch bản CI tự động build và test.
- [x] Image tag quy ước: `v0.1.0-core-business`.
