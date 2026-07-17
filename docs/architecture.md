# Kiến trúc Module 1

## Ranh giới module

Luồng gọi tuân thủ `Router -> Service -> Repository -> Database/External
Service`. Router chỉ xử lý HTTP và dependency injection; transaction, validation,
state transition và rollback bù nằm ở service.

```text
HTTP multipart
  -> documents.router
  -> DocumentService
       -> FileValidator
       -> Workspace/Document repositories
       -> S3ObjectStorage
       -> Document + DocumentFile + ProcessingJob (một transaction)
       -> Celery dispatcher
```

PostgreSQL được chọn làm nguồn dữ liệu chuẩn. MinIO/S3 chỉ giữ binary gốc. Redis
làm Celery broker/result backend. Kiến trúc vẫn là một deployment unit, với API,
worker và beat là ba process dùng chung cùng codebase.

## Tính nhất quán upload

Không thể có ACID transaction chung giữa PostgreSQL và S3. Luồng dùng chiến lược
`upload object -> commit database`; nếu commit thất bại, service thực hiện xóa bù
object. Unique partial index trên `(workspace_id, checksum)` chống race condition
cho tài liệu chưa bị soft-delete.

Job `UPLOADED` đã commit đóng vai trò recovery point nếu Redis tạm thời lỗi.
Celery Beat định kỳ phát lại các job còn `UPLOADED`; thao tác chuyển `QUEUED` là
idempotent.

## State machine

```text
UPLOADED -> QUEUED -> PROCESSING -> COMPLETED
    |          |          |
    +----------+----------+----> FAILED | CANCELLED
```

`ProcessingStateService` khóa row khi cập nhật, không cho giảm progress và đồng
bộ trạng thái sang bảng `documents`. Các worker tương lai không cập nhật database
trực tiếp mà phải đi qua service này.

## Chính sách xóa

`DELETE` luôn soft-delete `documents` trước và cancel job chưa kết thúc. Mặc định
file gốc được giữ lại. Khi `VADS_DELETE_OBJECT_ON_SOFT_DELETE=true`, API enqueue
task xóa object; chỉ sau khi object được xóa thành công mới đặt
`document_files.deleted_at`.

## Bảo mật file

Tệp chỉ được chấp nhận khi extension, MIME khai báo và nội dung cùng khớp. PDF
phải bắt đầu bằng `%PDF-`; DOCX phải là ZIP có `[Content_Types].xml` và
`word/document.xml`. File được đọc theo chunk vào spooled temporary file, tính
SHA-256 trong cùng lượt đọc và dừng khi vượt giới hạn. Tên object do server sinh,
không dùng tên file từ client.

## Hướng mở rộng

- PostgreSQL + pgvector là lựa chọn MVP cho vector và graph tables, tránh thêm
  Neo4j/Qdrant trước khi có nhu cầu tải thực tế.
- `citations.schemas.CitationAnchor` giữ page, block, offset và bounding boxes để
  frontend cuộn/highlight đúng nguồn.
- `knowledge_graph.schemas` định nghĩa sẵn node/edge JSON cho React hoặc Vue.
- Polling qua `/status` là contract bắt buộc hiện tại. SSE có thể thêm sau trên
  cùng state store khi tần suất polling hoặc số client trở thành vấn đề.

