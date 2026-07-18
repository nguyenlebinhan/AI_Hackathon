# Deploy VADS lên Azure VM

Kiến trúc deploy dùng một Ubuntu VM và Docker Compose. Chỉ frontend Caddy mở cổng
`80/443`; FastAPI, PostgreSQL, Redis và MinIO giao tiếp trong mạng Docker nội bộ.

## 1. Tạo VM

Trong Azure Portal, tạo Ubuntu Server 24.04 LTS với cấu hình đề xuất:

- Azure for Students: bắt đầu bằng `Standard_B2ms` (2 vCPU, 8 GB RAM) và dùng OCR mock.
- Khi thực sự cần PaddleOCR, resize tạm lên máy 4 vCPU, 16 GB RAM rồi hạ xuống sau demo.
- OS disk tối thiểu 64 GB, khuyến nghị 128 GB.
- Authentication bằng SSH public key.
- Inbound ports: `22`, `80`, `443`.

Không mở public các cổng `5432`, `6379`, `8000`, `9000` hoặc `9001`.

Với Azure for Students, bật **Auto-shutdown** trong trang VM và bấm **Stop** trong Azure Portal
khi không demo. Việc chỉ chạy `shutdown` bên trong Ubuntu có thể không deallocate VM nên vẫn phát sinh
compute cost. Đặt thêm budget alert trong **Cost Management + Billing** để theo dõi credit.

## 2. Cài Docker và lấy source

SSH vào VM:

```bash
ssh azureuser@<PUBLIC_IP>
```

Cài các công cụ cần thiết:

```bash
sudo apt-get update
sudo apt-get install -y git curl
curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
sudo sh /tmp/get-docker.sh
sudo usermod -aG docker "$USER"
exit
```

SSH lại để quyền group có hiệu lực, sau đó clone repo:

```bash
ssh azureuser@<PUBLIC_IP>
git clone <REPOSITORY_URL> vads
cd vads
cp .env.example .env
```

## 3. Cấu hình production

Sinh ba giá trị ngẫu nhiên độc lập:

```bash
openssl rand -hex 32
openssl rand -hex 32
openssl rand -hex 24
```

Mở `.env` bằng `nano .env` và thay ít nhất các giá trị sau:

```dotenv
VADS_ENVIRONMENT=production
VADS_DEBUG=false
VADS_LEGACY_API_ENABLED=false
VADS_SITE_ADDRESS=:80

VADS_JWT_SECRET_KEY=<RANDOM_SECRET_1>
VADS_REFRESH_TOKEN_PEPPER=<RANDOM_SECRET_2>

POSTGRES_PASSWORD=<RANDOM_DATABASE_PASSWORD>
VADS_DATABASE_URL=postgresql+psycopg://vads:<RANDOM_DATABASE_PASSWORD>@postgres:5432/vads
VADS_DATABASE_ASYNC_URL=postgresql+asyncpg://vads:<RANDOM_DATABASE_PASSWORD>@postgres:5432/vads

MINIO_ROOT_PASSWORD=<RANDOM_MINIO_PASSWORD>
VADS_S3_SECRET_KEY=<RANDOM_MINIO_PASSWORD>

VADS_CORS_ORIGINS=["http://<PUBLIC_IP>"]
```

Dùng password dạng hex như lệnh trên để không phải URL-encode ký tự đặc biệt trong database URL.
Nếu cần FPT AI, cấu hình thêm:

```dotenv
VADS_FPT_AI_ENABLED=true
VADS_FPT_AI_API_KEY=<FPT_AI_KEY>
VADS_FPT_AI_ALLOW_PRIVATE_DATA=true
```

Để lần deploy đầu nhanh hơn và không xử lý tài liệu scan, có thể dùng:

```dotenv
VADS_INSTALL_OCR=false
VADS_OCR_PROVIDER=MOCK
```

## 4. Deploy

Kiểm tra cấu hình rồi build và chạy toàn bộ stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.azure.yml config --quiet
docker compose -f docker-compose.yml -f docker-compose.azure.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.azure.yml ps
```

Kiểm tra từ trình duyệt hoặc terminal:

```bash
curl http://127.0.0.1/health/live
```

- Frontend: `http://<PUBLIC_IP>`
- API docs: `http://<PUBLIC_IP>/api/docs`
- Health check: `http://<PUBLIC_IP>/health/live`

Xem log khi service chưa healthy:

```bash
docker compose -f docker-compose.yml -f docker-compose.azure.yml logs -f api frontend worker
```

## 5. Bật domain và HTTPS

Tạo DNS record `A` trỏ domain vào public IP của VM. Sau khi DNS cập nhật, đổi `.env`:

```dotenv
VADS_SITE_ADDRESS=vads.example.com
VADS_CORS_ORIGINS=["https://vads.example.com"]
```

Áp dụng cấu hình:

```bash
docker compose -f docker-compose.yml -f docker-compose.azure.yml up -d
```

Caddy tự xin và gia hạn certificate. Dữ liệu certificate được giữ trong volume `caddy-data`.

## 6. Cập nhật và vận hành

Deploy phiên bản mới:

```bash
cd ~/vads
git pull
docker compose -f docker-compose.yml -f docker-compose.azure.yml up -d --build
```

Các lệnh hữu ích:

```bash
docker compose -f docker-compose.yml -f docker-compose.azure.yml ps
docker compose -f docker-compose.yml -f docker-compose.azure.yml logs --tail=200 api
docker compose -f docker-compose.yml -f docker-compose.azure.yml restart worker
```

Không chạy `docker compose down -v` trên môi trường có dữ liệu vì tùy chọn `-v` xóa các volume
PostgreSQL, MinIO, Redis và certificate. Database mới cũng cần bootstrap một tài khoản admin trước
khi có thể đăng nhập vào frontend.
