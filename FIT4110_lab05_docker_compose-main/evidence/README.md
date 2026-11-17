# Verification Evidence — Core Business Service (`FIT4110_lab05_docker_compose-main`)

Thư mục này lưu giữ các bằng chứng kiểm chứng kỹ thuật cho Core Business Service (bài tập lớn FIT4110).

## Danh mục bằng chứng

| Tệp bằng chứng | Nội dung kiểm chứng | Trạng thái |
|---|---|---|
| [../reports/newman-lab05-compose.html](../reports/newman-lab05-compose.html) | Báo cáo chi tiết giao diện HTML từ Newman cho toàn bộ bộ test API + tích hợp Mock | Đã cập nhật sau hoàn thiện |
| [../reports/newman-lab05-compose.xml](../reports/newman-lab05-compose.xml) | Báo cáo JUnit XML chuẩn CI/CD từ Newman | Đã cập nhật sau hoàn thiện |
| [verification-summary.txt](verification-summary.txt) | Nhật ký chạy cục bộ qua `.venv`: Spectral lint, Compose config check, Unit/Storage tests & Newman trên 6 FastAPI services (`InMemoryStore`) | Đã cập nhật sau hoàn thiện |
| [verification-docker-compose.txt](verification-docker-compose.txt) | Nhật ký chạy thực tế trên Docker Compose (`--profile mock`): 7 containers Healthy, `PostgresStore` thật, 5/5 ONLINE, `34/34` Newman PASS & kiểm chứng bền vững sau restart | Đã kiểm chứng với Docker Desktop |

## Cách tái lập bằng chứng kiểm thử

```powershell
# 1. Kiểm tra hợp đồng OpenAPI 3.1.0
npm run lint:openapi

# 2. Kiểm tra cú pháp Docker Compose (LAN & Mock profile)
npm run lint:compose

# 3. Chạy Stack với 5 Mock Services
docker compose -f docker-compose.yml -f docker-compose.mock.yml --profile mock up -d --build --wait

# 4. Chạy bộ kiểm thử tự động Newman (34 requests)
npm run test:compose
```
