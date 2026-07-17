# VADS Backend

Backend modular monolith cho VADS, hiện thực đầy đủ **Module 1 — Backend Core và
Quản lý tài liệu**. API dùng FastAPI, SQLAlchemy 2, PostgreSQL, Celery/Redis và
object storage tương thích S3 (MinIO mặc định).

## Chức năng đã có

- Tạo workspace.
- Upload PDF/DOCX bằng `multipart/form-data`.
- Kiểm tra extension, MIME khai báo, magic bytes/cấu trúc DOCX, tên file, file
  rỗng và giới hạn dung lượng cấu hình được.
- SHA-256 checksum và chặn file trùng trong cùng workspace.
- Lưu file gốc vào MinIO/S3, metadata vào PostgreSQL và tạo processing job.
- Poll metadata/trạng thái, phần trăm và bước xử lý.
- State machine chống giảm tiến độ hoặc chuyển trạng thái không hợp lệ.
- Soft delete; có thể bật xóa object bất đồng bộ theo chính sách.
- Error JSON thống nhất và request ID.

Các module extraction, summary, citation, knowledge graph và vector store mới có
ranh giới package/schema để phát triển tiếp; chúng chưa tạo kết quả giả.

## Chạy bằng Docker

Yêu cầu Docker và Docker Compose:

```bash
docker compose up --build
```

API docs: `http://localhost:8000/api/docs`  
MinIO console: `http://localhost:9001`

Compose tự chạy migration trước khi khởi động API. Worker chỉ tiếp nhận job và
đưa trạng thái từ `UPLOADED` sang `QUEUED`; module extraction ở giai đoạn tiếp
theo sẽ gọi `ProcessingStateService` để cập nhật các bước còn lại.

## Chạy trực tiếp

Python 3.12:

```bash
python -m venv .venv
pip install -e ".[test]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Chạy worker và bộ lập lịch ở hai terminal khác:

```bash
celery -A app.config.celery_app:celery_app worker --loglevel=INFO
celery -A app.config.celery_app:celery_app beat --loglevel=INFO
```

## API

Tạo workspace:

```bash
curl -X POST http://localhost:8000/api/workspaces \
  -H "Content-Type: application/json" \
  -d '{"name":"Phân tích dự thảo","description":"Phiên họp thẩm định"}'
```

Upload PDF (thay `{workspaceId}` bằng ID vừa nhận):

```bash
curl -X POST http://localhost:8000/api/workspaces/{workspaceId}/documents \
  -F "file=@du-thao.pdf;type=application/pdf" \
  -F "displayName=Dự thảo kế hoạch"
```

Các endpoint còn lại:

```text
GET    /api/documents/{documentId}
GET    /api/documents/{documentId}/status
DELETE /api/documents/{documentId}
```

Lỗi luôn theo mẫu:

```json
{
  "error": {
    "code": "DUPLICATE_DOCUMENT",
    "message": "Tệp này đã tồn tại trong workspace.",
    "requestId": "...",
    "details": {"existingDocumentId": "doc-...", "checksum": "..."}
  }
}
```

## Kiểm thử

```bash
pytest
```

Test API dùng SQLite và object storage/dispatcher giả lập, nên không cần chạy
PostgreSQL, Redis hoặc MinIO. Chi tiết quyết định kiến trúc nằm tại
[`docs/architecture.md`](docs/architecture.md).
