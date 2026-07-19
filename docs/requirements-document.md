# VADS — Tài liệu yêu cầu sản phẩm

| Thuộc tính | Nội dung |
|---|---|
| Sản phẩm | VADS — Hệ thống phân tích văn bản hành chính |
| Loại tài liệu | Product Requirements Document (PRD) kết hợp Software Requirements Specification (SRS) |
| Phiên bản | 1.0 |
| Trạng thái | Baseline đề xuất |
| Ngày lập | 19/07/2026 |
| Nguồn | Proposal VADS và hiện trạng repository VADS |

## 1. Mục đích tài liệu

Tài liệu này xác định yêu cầu nghiệp vụ, chức năng, dữ liệu, bảo mật, AI, vận hành và tiêu chí nghiệm thu cho VADS. Đây là căn cứ thống nhất giữa product owner, chuyên gia nghiệp vụ hành chính/pháp lý, UX/UI, đội phát triển, kiểm thử và vận hành.

Các từ khóa **phải**, **nên**, **có thể** lần lượt biểu thị yêu cầu bắt buộc, yêu cầu ưu tiên và khả năng mở rộng.

## 2. Bối cảnh và vấn đề

Cán bộ tại UBND, HĐND và các sở, ban, ngành thường phải nghiên cứu đồng thời nhiều báo cáo, tờ trình, dự thảo nghị quyết, đề án, hồ sơ đầu tư và văn bản pháp luật dài hàng chục đến hàng trăm trang trong thời gian ngắn. Thông tin quan trọng như phương án đề xuất, nội dung cần quyết định, trách nhiệm, kinh phí, thời hạn, chỉ tiêu và căn cứ pháp lý nằm rải rác trong nội dung chính, bảng và phụ lục.

Các công cụ đọc PDF, tìm kiếm từ khóa hoặc chatbot tổng quát chưa đáp ứng đầy đủ việc nhận diện cấu trúc hành chính/pháp lý, đối chiếu số liệu, phát hiện thiếu sót và dẫn chính xác về trang, mục, điều, khoản của nguồn gốc. Điều này làm tăng thời gian chuẩn bị, nguy cơ bỏ sót thông tin và rủi ro ra quyết định thiếu căn cứ.

## 3. Tầm nhìn và mục tiêu

VADS là trợ lý AI chuyên biệt giúp biến tài liệu hành chính thành hồ sơ thông minh có cấu trúc, có quan hệ và có thể kiểm chứng.

### 3.1 Mục tiêu nghiệp vụ

- Rút ngắn thời gian đọc và chuẩn bị tài liệu họp.
- Giúp người dùng nhận biết nhanh nội dung cần lãnh đạo quyết định và vấn đề cần làm rõ.
- Trích xuất thống nhất trách nhiệm, nguồn lực, tiến độ, chỉ tiêu, đối tượng tác động và căn cứ pháp lý.
- Phát hiện sớm dữ liệu mâu thuẫn, thiếu hoặc chưa rõ.
- Duy trì bối cảnh giữa báo cáo mới, báo cáo cũ và các phiên phân tích.
- Bảo đảm mọi kết quả quan trọng đều có nguồn để người dùng kiểm chứng.
- Hỗ trợ con người ra quyết định; không tự động thay thế người có thẩm quyền.

### 3.2 Chỉ số thành công đề xuất

Các ngưỡng chính thức phải được xác nhận bằng bộ dữ liệu đánh giá đại diện trước khi phát hành production.

| Mã | Chỉ số | Mục tiêu MVP |
|---|---|---|
| KPI-01 | Tệp PDF/DOCX hợp lệ được tiếp nhận và xử lý thành công | ≥ 95% trên bộ kiểm thử |
| KPI-02 | Kết quả tóm tắt/trả lời có ít nhất một citation hợp lệ | 100% đối với claim dựa trên tài liệu |
| KPI-03 | Citation mở đúng tài liệu và đúng trang | ≥ 95% |
| KPI-04 | Trường hành chính cốt lõi trích xuất đúng | F1 ≥ 0,85 trên bộ dữ liệu đã gán nhãn |
| KPI-05 | Câu trả lời không đủ bằng chứng được từ chối hoặc gắn “Cần kiểm chứng” | 100% ca kiểm thử bắt buộc |
| KPI-06 | Phân tách tenant/xã trong kiểm thử authorization | 100%, không chấp nhận rò rỉ chéo tenant |
| KPI-07 | Thời gian tạo hồ sơ cho tài liệu text-based 50 trang | P95 ≤ 10 phút trong cấu hình chuẩn |

## 4. Phạm vi sản phẩm

### 4.1 Phạm vi MVP bắt buộc

- Đăng nhập, hồ sơ người dùng, phân quyền theo tenant/xã và vai trò.
- Tải lên PDF, DOCX và tài liệu scan; kiểm tra định dạng, kích thước, nội dung thực và trùng lặp.
- OCR chọn lọc, nhận diện trang và cấu trúc chương, mục, điều, khoản, bảng, phụ lục.
- Tạo chunk có metadata và citation anchor.
- Tóm tắt theo nhu cầu cuộc họp và ngữ cảnh người dùng.
- Trích xuất thông tin hành chính có cấu trúc.
- Xác định nội dung cần quyết định.
- Hỏi đáp dựa trên tài liệu bằng hybrid retrieval và citation.
- Phát hiện một số mâu thuẫn/thiếu thông tin theo quy tắc cốt lõi.
- Tạo câu hỏi phản biện.
- Hiển thị nguồn, độ chắc chắn và nhãn cần kiểm chứng.
- Lưu tài liệu, phiên xử lý, kết quả phân tích và nhật ký hoạt động.

### 4.2 Phạm vi mở rộng sau MVP

- So sánh đầy đủ báo cáo theo nhiều kỳ và kế thừa dữ liệu có kiểm soát.
- Bản đồ tri thức tương tác hoàn chỉnh.
- Theo dõi nhiệm vụ, tiến độ và kết quả sau cuộc họp.
- Tra cứu trạng thái hiệu lực từ nguồn pháp lý chính thức.
- Phân tích thay đổi giữa các phiên bản văn bản và tác động đến dự án/phòng ban.
- Tìm kiếm xuyên kho tài liệu cấp tỉnh và nền tảng Trí tuệ Hành chính.

### 4.3 Ngoài phạm vi

- Tự ban hành, phê duyệt hoặc ký văn bản.
- Tự đưa ra quyết định hành chính/pháp lý thay người có thẩm quyền.
- Cam kết tư vấn pháp lý tuyệt đối chính xác khi chưa có kiểm chứng chuyên gia.
- Tự coi văn bản liên quan là còn hiệu lực nếu chưa xác minh từ nguồn đáng tin cậy.
- Chỉnh sửa nội dung file gốc trong MVP.

## 5. Bên liên quan và vai trò người dùng

| Vai trò | Nhu cầu chính |
|---|---|
| Lãnh đạo/người chủ trì | Nắm nhanh vấn đề, phương án, nội dung cần quyết định, rủi ro và câu hỏi trọng tâm |
| Chuyên viên tham mưu | Đọc, kiểm tra, trích xuất, đối chiếu, chuẩn bị hồ sơ và câu hỏi phản biện |
| Thư ký cuộc họp | Tổ chức tài liệu, đánh dấu nội dung, lưu câu hỏi và nhiệm vụ sau họp |
| Đơn vị soạn thảo | Phát hiện nội dung thiếu, mâu thuẫn và căn cứ chưa rõ trước khi trình |
| Chuyên viên pháp lý | Kiểm tra viện dẫn, quan hệ văn bản, trạng thái xác minh và thay đổi quy định |
| Quản trị viên xã/đơn vị | Quản lý người dùng trong phạm vi tenant, khóa/mở tài khoản và xem audit log |
| Quản trị vận hành | Cấu hình hạ tầng, model, giám sát job và xử lý sự cố; không mặc nhiên được đọc nội dung nghiệp vụ |

## 6. Luồng nghiệp vụ chính

1. Người dùng đăng nhập và hệ thống nạp hồ sơ gồm chức vụ, phòng ban, đơn vị, địa phương và trách nhiệm.
2. Người dùng tạo/chọn workspace, tải báo cáo mới, báo cáo cũ và văn bản liên quan; có thể nhập lưu ý phân tích.
3. Hệ thống xác thực tệp, lưu bản gốc bất biến, phân loại text/scan/hybrid, OCR khi cần và nhận diện cấu trúc.
4. Hệ thống tạo chỉ mục tìm kiếm và chạy workflow phân tích.
5. Người dùng xem hồ sơ thông minh: tóm tắt, trường hành chính, nội dung cần quyết định, cảnh báo, thuật ngữ, câu hỏi và nguồn.
6. Trước/trong cuộc họp, người dùng hỏi đáp và mở đúng vị trí nguồn để kiểm chứng.
7. Sau cuộc họp, người dùng có thể lưu ghi chú, câu hỏi và thông tin cần chỉnh sửa; chức năng giao việc là phạm vi mở rộng.

## 7. Yêu cầu chức năng

### 7.1 Xác thực, người dùng và phân quyền

| Mã | Yêu cầu | Ưu tiên |
|---|---|---|
| FR-AUTH-01 | Hệ thống phải hỗ trợ đăng nhập bằng username hoặc email và cấp access token ngắn hạn cùng refresh token xoay vòng. | Must |
| FR-AUTH-02 | Hệ thống phải từ chối token khi user bị khóa, session bị thu hồi hoặc token version không còn phù hợp. | Must |
| FR-AUTH-03 | Mọi tài nguyên phải được giới hạn theo tenant/xã; truy cập chéo tenant phải bị từ chối mà không làm lộ sự tồn tại tài nguyên. | Must |
| FR-AUTH-04 | Quản trị viên tenant được tạo user thường, khóa/mở khóa, reset mật khẩu và xem audit log trong tenant của mình. | Must |
| FR-AUTH-05 | Hệ thống phải áp dụng quyền theo vai trò, ownership, explicit grant và trạng thái tài nguyên. | Must |
| FR-AUTH-06 | Người dùng phải xem và cập nhật ngữ cảnh cá nhân được phép dùng để cá nhân hóa kết quả. | Must |

### 7.2 Workspace và tiếp nhận tài liệu

| Mã | Yêu cầu | Ưu tiên |
|---|---|---|
| FR-DOC-01 | Người dùng có quyền phải tạo được workspace và tải lên PDF hoặc DOCX. | Must |
| FR-DOC-02 | Mỗi tài liệu phải được gắn loại nguồn: báo cáo mới, báo cáo cũ, văn bản liên quan hoặc nguồn khác. | Must |
| FR-DOC-03 | Hệ thống phải kiểm tra extension, MIME, magic bytes, tên file, giới hạn kích thước và SHA-256 trước khi chấp nhận. | Must |
| FR-DOC-04 | Hệ thống phải lưu file gốc bằng khóa do server sinh và không ghi đè phiên bản cũ. | Must |
| FR-DOC-05 | Hệ thống phải hiển thị trạng thái UPLOADED, QUEUED, PROCESSING, COMPLETED, FAILED hoặc CANCELLED cùng tiến độ. | Must |
| FR-DOC-06 | Người dùng phải có thể retry/reprocess tài liệu thất bại mà không tạo dữ liệu trùng không kiểm soát. | Must |
| FR-DOC-07 | Xóa tài liệu phải là soft-delete; quyền khôi phục và chính sách xóa object phải được kiểm soát. | Must |
| FR-DOC-08 | Người dùng có thể nhập lưu ý cần tập trung phân tích; trường này không bắt buộc. | Should |

### 7.3 Xử lý và cấu trúc tài liệu

| Mã | Yêu cầu | Ưu tiên |
|---|---|---|
| FR-PROC-01 | Hệ thống phải phân loại tài liệu TEXT_BASED, SCANNED hoặc HYBRID. | Must |
| FR-PROC-02 | Hệ thống phải ưu tiên text layer và chỉ OCR trang cần thiết. | Must |
| FR-PROC-03 | Hệ thống phải lưu trang, block, bảng, bounding box và độ tin cậy OCR khi có. | Must |
| FR-PROC-04 | Hệ thống phải nhận diện cấu trúc trang, chương, mục, điều, khoản, bảng và phụ lục ở mức tốt nhất có thể. | Must |
| FR-PROC-05 | Hệ thống phải tạo chunk kèm document ID, page, section, vị trí, loại nội dung, ngày nguồn, phiên xử lý và OCR confidence. | Must |
| FR-PROC-06 | Phần OCR có độ tin cậy dưới ngưỡng cấu hình phải được đánh dấu để kiểm tra với ảnh gốc. | Must |

### 7.4 Hồ sơ phân tích thông minh

| Mã | Yêu cầu | Ưu tiên |
|---|---|---|
| FR-ANA-01 | Hệ thống phải tạo tóm tắt gồm bối cảnh, thực trạng, mục tiêu, nội dung chính, phương án, nội dung cần quyết định, tác động và vấn đề cần làm rõ. | Must |
| FR-ANA-02 | Nội dung liên quan trực tiếp đến chức vụ, đơn vị và địa phương của người dùng nên được ưu tiên hiển thị. | Should |
| FR-ANA-03 | Hệ thống phải trích xuất cơ quan chủ trì, cơ quan phối hợp, nhiệm vụ, kinh phí, nguồn vốn, thời hạn, tiến độ, chỉ tiêu, đối tượng tác động và căn cứ pháp lý. | Must |
| FR-ANA-04 | Mỗi trường trích xuất phải lưu giá trị, nguồn, ngày/phiên bản, confidence và trạng thái xác minh. | Must |
| FR-ANA-05 | Hệ thống phải xác định riêng nội dung cần lãnh đạo quyết định, phương án tương ứng và căn cứ hỗ trợ. | Must |
| FR-ANA-06 | Hệ thống phải phân biệt rõ nội dung trích nguyên văn với nội dung AI tổng hợp, giải thích hoặc đề xuất. | Must |
| FR-ANA-07 | Hệ thống nên phát hiện và giải thích thuật ngữ chuyên ngành theo ngữ cảnh, kèm nguồn nếu lấy từ tài liệu. | Should |

### 7.5 Dữ liệu mới, dữ liệu cũ và phiên bản

| Mã | Yêu cầu | Ưu tiên |
|---|---|---|
| FR-VER-01 | Báo cáo mới phải là nguồn ưu tiên cho cùng một trường dữ liệu. | Must |
| FR-VER-02 | Dữ liệu cũ chỉ được dùng để bổ sung bối cảnh hoặc trường tương ứng không xuất hiện trong báo cáo mới. | Must |
| FR-VER-03 | Nếu giá trị cũ và mới khác nhau, hệ thống không được tự gộp mà phải hiển thị riêng cùng nguồn và ngày cập nhật. | Must |
| FR-VER-04 | Nếu không có báo cáo mới, hệ thống có thể dùng phiên phân tích gần nhất nhưng phải cảnh báo rõ đây không phải dữ liệu mới. | Must |
| FR-VER-05 | Hệ thống phải lưu lịch sử phiên bản và không ghi đè kết quả phân tích trước. | Must |

### 7.6 Citation và trình xem nguồn

| Mã | Yêu cầu | Ưu tiên |
|---|---|---|
| FR-CIT-01 | Mọi claim do AI tạo dựa trên tài liệu phải gắn ít nhất một citation hỗ trợ. | Must |
| FR-CIT-02 | Citation phải gồm tài liệu, trang và khi có thể gồm mục/điều/khoản, block, offset và bounding box. | Must |
| FR-CIT-03 | Người dùng phải nhấn citation để mở đúng tài liệu, cuộn đến vị trí và highlight đoạn liên quan. | Must |
| FR-CIT-04 | Hệ thống phải kiểm tra đoạn nguồn có thực sự hỗ trợ claim trước khi hiển thị kết quả ở trạng thái đã xác minh. | Must |
| FR-CIT-05 | Citation không hợp lệ hoặc không đủ hỗ trợ phải khiến claim bị gắn “Cần kiểm chứng” hoặc bị loại. | Must |

### 7.7 Kiểm tra mâu thuẫn và thiếu thông tin

| Mã | Yêu cầu | Ưu tiên |
|---|---|---|
| FR-RISK-01 | Hệ thống phải đối chiếu số liệu giữa nội dung chính, bảng và phụ lục khi xác định được cùng phạm vi/kỳ/đối tượng. | Must |
| FR-RISK-02 | Hệ thống phải cảnh báo nhiệm vụ không có đơn vị chủ trì. | Must |
| FR-RISK-03 | Hệ thống phải cảnh báo nguồn vốn chưa gắn với hoạt động hoặc hạng mục cụ thể. | Must |
| FR-RISK-04 | Hệ thống phải cảnh báo thời hạn chưa có đầu ra/chỉ tiêu đo lường. | Must |
| FR-RISK-05 | Cảnh báo phải chứa loại rủi ro, mức độ, giải thích, các nguồn liên quan và trạng thái review. | Must |
| FR-RISK-06 | Nếu chưa xác định hai giá trị có cùng phạm vi, hệ thống phải nêu khả năng mâu thuẫn thay vì kết luận chắc chắn. | Must |

### 7.8 Câu hỏi phản biện và hỏi đáp

| Mã | Yêu cầu | Ưu tiên |
|---|---|---|
| FR-QA-01 | Hệ thống phải tạo câu hỏi phản biện về tính khả thi, trách nhiệm, nguồn lực, tiến độ, giám sát, tác động và căn cứ pháp lý. | Must |
| FR-QA-02 | Mỗi câu hỏi nên nêu lý do đặt câu hỏi và trỏ đến bằng chứng/cảnh báo liên quan. | Should |
| FR-QA-03 | Người dùng phải tạo được phiên chat trong workspace và hỏi trên một hoặc nhiều tài liệu được phép. | Must |
| FR-QA-04 | Retrieval phải kết hợp semantic search, keyword và bộ lọc metadata cho dữ liệu có độ chính xác cao như số tiền, ngày, số hiệu, cơ quan và điều khoản. | Must |
| FR-QA-05 | Câu trả lời phải chỉ dựa trên context truy xuất được và kèm citation. | Must |
| FR-QA-06 | Khi không đủ căn cứ, hệ thống phải nói không đủ thông tin hoặc gắn “Cần kiểm chứng”, không được suy đoán như sự thật. | Must |
| FR-QA-07 | Hệ thống phải lưu lịch sử hỏi đáp theo quyền truy cập và cho phép xóa session. | Must |
| FR-QA-08 | Streaming/SSE có thể được dùng để cải thiện trải nghiệm nhưng không được thay đổi contract nội dung và citation. | Should |

### 7.9 Bản đồ tri thức và văn bản liên quan

| Mã | Yêu cầu | Ưu tiên |
|---|---|---|
| FR-KG-01 | Hệ thống nên tạo node cho cơ quan, nhiệm vụ, kinh phí, nguồn vốn, thời hạn, chỉ tiêu, dự án và văn bản. | Should |
| FR-KG-02 | Mỗi edge phải có loại quan hệ, bằng chứng và nguồn gốc phiên phân tích. | Should |
| FR-KG-03 | Người dùng phải xem được chi tiết và nguồn khi chọn node/edge. | Should |
| FR-LEGAL-01 | Hệ thống nên nhận diện số hiệu và tên văn bản được viện dẫn, đồng thời liên kết về đoạn nguồn. | Should |
| FR-LEGAL-02 | Khi chưa kiểm chứng với nguồn bên ngoài, trạng thái phải là `EXTRACTED_NOT_EXTERNALLY_VERIFIED` hoặc nhãn tiếng Việt tương đương. | Must |
| FR-LEGAL-03 | Hệ thống không được tuyên bố văn bản còn/hết hiệu lực nếu không có đủ dữ liệu xác minh. | Must |

### 7.10 Audit và quản trị vận hành

| Mã | Yêu cầu | Ưu tiên |
|---|---|---|
| FR-AUD-01 | Các hành động đăng nhập, quản trị user, upload, xóa/khôi phục, phân tích, review và thay đổi quyền phải được audit. | Must |
| FR-AUD-02 | Audit phải có actor, tenant, action, resource, thời gian, kết quả và correlation ID; không lưu password, token hoặc secret. | Must |
| FR-AUD-03 | Mỗi lần chạy model phải lưu model/alias, prompt version, tham số, thời gian, trạng thái, chi phí/token nếu có và liên kết workflow. | Must |
| FR-AUD-04 | Retry workflow phải tạo attempt mới và giữ nguyên lịch sử attempt trước. | Must |

## 8. Quy tắc nghiệp vụ

| Mã | Quy tắc |
|---|---|
| BR-01 | AI chỉ hỗ trợ; kết quả cuối cùng thuộc trách nhiệm người có thẩm quyền. |
| BR-02 | Không có bằng chứng phù hợp thì không được tạo kết luận chắc chắn. |
| BR-03 | Trích xuất trực tiếp và nội dung AI suy luận/tổng hợp phải có cách trình bày khác nhau. |
| BR-04 | Dữ liệu mới ưu tiên hơn dữ liệu cũ; dữ liệu cũ chỉ kế thừa khi trường tương ứng bị thiếu và phải giữ provenance. |
| BR-05 | Hai giá trị khác nhau không được tự hòa giải thành một giá trị duy nhất. |
| BR-06 | Mọi dẫn xuất phải kế thừa tenant và authorization từ tài liệu nguồn. |
| BR-07 | UUID không phải cơ chế phân quyền; mọi truy vấn tài nguyên phải được tenant-scope và policy-check. |
| BR-08 | File gốc và phiên bản văn bản là bất biến; cập nhật tạo version/analysis mới. |
| BR-09 | Cảnh báo và kết quả AI có vòng đời: generated, needs_review, accepted hoặc rejected. |
| BR-10 | Trạng thái hiệu lực pháp lý chỉ được xác nhận từ nguồn đáng tin cậy hoặc bởi chuyên gia có thẩm quyền. |

## 9. Yêu cầu dữ liệu

### 9.1 Thực thể tối thiểu

- Tenant/commune, user, role, permission, auth session và audit log.
- Workspace, document, document file, document family/version và processing job.
- Page, block, table, section, chunk và citation anchor.
- User context và document access grant.
- Analysis workflow/run/task, model execution và prompt version.
- Summary, extracted fact, decision item, red flag, critical question và glossary item.
- Search index/embedding, chat session/message và retrieval evidence.
- Knowledge node/edge, legal relation và verification result.

### 9.2 Provenance bắt buộc

Mọi fact, claim, cảnh báo và quan hệ tri thức phải truy được về: tenant, document/version, analysis version, page/section/block, đoạn trích, loại nguồn, ngày nguồn, OCR confidence (nếu có), model/rule version, confidence và verification status.

### 9.3 Lưu trữ và vòng đời

- PostgreSQL là nguồn dữ liệu giao dịch chuẩn; pgvector phục vụ chỉ mục vector trong MVP.
- MinIO/S3 lưu binary gốc; Redis/Celery phục vụ hàng đợi và job nền.
- Chính sách retention, backup, purge và legal hold phải cấu hình theo môi trường và quy định của đơn vị triển khai.
- Xóa logic không được làm mất audit và provenance cần cho kiểm tra; xóa vật lý phải theo policy đã phê duyệt.

## 10. Yêu cầu phi chức năng

### 10.1 Bảo mật và riêng tư

| Mã | Yêu cầu |
|---|---|
| NFR-SEC-01 | Mã hóa TLS khi truyền và mã hóa dữ liệu/object/backup khi lưu. |
| NFR-SEC-02 | Secret chỉ nằm trong secret manager hoặc biến môi trường, không nằm trong source hoặc log. |
| NFR-SEC-03 | Access token có TTL ngắn; refresh token opaque, xoay vòng và phát hiện reuse. |
| NFR-SEC-04 | Password phải được băm bằng thuật toán phù hợp như Argon2id và áp dụng rate limiting cho login. |
| NFR-SEC-05 | API phải chống IDOR, mass assignment, upload độc hại và truy cập chéo tenant. |
| NFR-SEC-06 | Dữ liệu gửi tới model/provider bên ngoài phải theo chính sách phân loại dữ liệu và thỏa thuận xử lý dữ liệu được phê duyệt. |
| NFR-SEC-07 | Legacy API không có tenant scope phải tắt mặc định ở staging/production. |

### 10.2 Hiệu năng, khả dụng và mở rộng

| Mã | Yêu cầu |
|---|---|
| NFR-PERF-01 | API metadata/read thông thường nên đạt P95 ≤ 2 giây, không tính xử lý nền và streaming AI. |
| NFR-PERF-02 | Upload và xử lý dài phải chạy bất đồng bộ, có progress và không khóa request HTTP. |
| NFR-PERF-03 | Job dispatch, reprocess và recovery phải idempotent; worker crash không được làm mất recovery point. |
| NFR-PERF-04 | Hệ thống phải hỗ trợ scale độc lập API và worker. |
| NFR-AVL-01 | Có liveness/readiness check, retry có giới hạn, timeout, fallback và dead-letter/failed state rõ ràng. |
| NFR-AVL-02 | RPO/RTO production phải được chủ hệ thống phê duyệt trước go-live; giá trị đề xuất ban đầu là RPO ≤ 24 giờ và RTO ≤ 8 giờ. |

### 10.3 Chất lượng AI và khả năng giải thích

| Mã | Yêu cầu |
|---|---|
| NFR-AI-01 | Mỗi nhiệm vụ AI dùng prompt/schema riêng, output có cấu trúc và được validate trước khi lưu. |
| NFR-AI-02 | Retrieval và generation phải bị giới hạn bởi quyền truy cập của người dùng. |
| NFR-AI-03 | Hệ thống phải version hóa model, prompt, rule và bộ đánh giá. |
| NFR-AI-04 | Có bộ golden dataset tiếng Việt để đánh giá extraction, citation, groundedness, red flag và refusal trước release. |
| NFR-AI-05 | Model/provider lỗi phải tạo trạng thái rõ ràng; không được trả dữ liệu giả hoặc kết quả cũ như kết quả mới. |

### 10.4 Khả dụng giao diện và accessibility

- Giao diện tiếng Việt, thuật ngữ hành chính nhất quán và trạng thái dễ hiểu.
- Luôn hiển thị tài liệu/phiên dữ liệu đang được dùng, đặc biệt khi dùng dữ liệu cũ.
- Cảnh báo phải có màu, biểu tượng và nhãn chữ; không chỉ dựa vào màu.
- Người dùng có thể đi từ kết quả phân tích đến nguồn gốc trong tối đa hai thao tác.
- Các luồng cốt lõi nên đáp ứng WCAG 2.1 AA ở mức khả thi cho MVP.

### 10.5 Quan sát và bảo trì

- Log có cấu trúc, correlation ID và redaction dữ liệu nhạy cảm.
- Thu thập metric về latency, error rate, queue depth, OCR/model failure, token/cost, citation validation và tỷ lệ human review.
- Kiến trúc tuân thủ ranh giới Router → Service → Repository → Database/External service.
- OCR, storage, embedding và model gateway phải đi qua provider interface để có thể thay thế.

## 11. Kiến trúc và công nghệ ràng buộc

Kiến trúc mục tiêu là modular monolith triển khai bằng Docker, gồm React/Vite frontend; Python/FastAPI backend; Celery/Redis cho xử lý nền; PostgreSQL/pgvector; MinIO/S3; OCR provider; model gateway và hybrid retrieval. API, worker và scheduler có thể là các process độc lập dùng chung codebase.

Luồng logic:

```text
Upload → Validate → Object storage → Processing job
       → Text extraction/OCR → Structure → Chunk + metadata
       → Index → AI workflow/rules → Verification
       → Summary/Fact/Red flag/Question/Graph/Chat + Citation
```

Việc chọn Azure hay nền tảng cloud cụ thể là quyết định triển khai; contract nghiệp vụ không được phụ thuộc chặt vào một nhà cung cấp.

## 12. Yêu cầu giao diện/API cấp cao

API chính thức phải được đặt dưới namespace versioned và tenant-secured. API cần bao phủ:

- Auth, user profile, user administration và audit.
- Workspace, document list/detail/upload/delete/restore/status/reprocess.
- Pages, sections, chunks và signed source access.
- Analysis workflow, summary, extracted facts, decision items, red flags, questions và knowledge graph.
- Index status và hybrid retrieval.
- Chat session, message history, grounded answer và streaming tùy chọn.
- Regulatory versions, changes, legal relations, projects/impacts và human review trong giai đoạn mở rộng.

Response lỗi phải có mã ổn định, thông điệp an toàn và correlation ID. API không được làm lộ stack trace, prompt, secret hoặc sự tồn tại của tài nguyên ngoài tenant.

## 13. Tiêu chí nghiệm thu end-to-end

### AC-01 — Nhập và xử lý tài liệu

**Given** người dùng có quyền upload một PDF/DOCX hợp lệ, **when** tải file lên, **then** hệ thống lưu bản gốc, tạo job, hiển thị tiến độ và tạo pages/sections/chunks khi hoàn tất. File giả định dạng hoặc quá giới hạn phải bị từ chối bằng mã lỗi phù hợp.

### AC-02 — Tài liệu scan

**Given** tài liệu có trang scan, **when** xử lý, **then** hệ thống OCR các trang cần thiết, lưu bounding box/confidence và đánh dấu đoạn dưới ngưỡng để kiểm tra.

### AC-03 — Tóm tắt có nguồn

**Given** tài liệu đã xử lý, **when** tạo tóm tắt, **then** các claim quan trọng có citation; nhấn citation mở đúng trang và highlight nguồn.

### AC-04 — Trích xuất hành chính

**Given** tài liệu nêu nhiệm vụ, đơn vị, kinh phí và thời hạn ở nhiều đoạn, **when** phân tích, **then** hệ thống kết nối thành fact có cấu trúc nhưng vẫn giữ toàn bộ nguồn liên quan.

### AC-05 — Dữ liệu cũ và mới

**Given** báo cáo cũ và mới có giá trị khác nhau cho cùng chỉ tiêu, **when** tổng hợp, **then** hệ thống hiển thị hai giá trị riêng cùng kỳ/ngày/nguồn, ưu tiên nguồn mới và không tự gộp.

### AC-06 — Phát hiện thiếu thông tin

**Given** một nhiệm vụ không chỉ rõ đơn vị chủ trì, **when** chạy kiểm tra, **then** hệ thống tạo cảnh báo có evidence và trạng thái cần review, không tự gán đơn vị.

### AC-07 — Hỏi đáp có căn cứ

**Given** câu hỏi có câu trả lời trong tài liệu được phép, **when** người dùng hỏi, **then** hệ thống trả lời đúng phạm vi và có citation. Nếu không đủ nguồn, hệ thống phải từ chối hoặc nói rõ chưa đủ căn cứ.

### AC-08 — Phân quyền tenant

**Given** hai user thuộc hai tenant khác nhau, **when** user A dùng ID tài liệu của tenant B, **then** hệ thống không trả metadata, nội dung, citation, kết quả AI hoặc dấu hiệu xác nhận tài nguyên tồn tại.

### AC-09 — Audit và tái lập

**Given** một workflow AI đã chạy, **when** kiểm tra lịch sử, **then** có thể xác định tài liệu/version, task, model, prompt version, input evidence, output, verification và actor; retry tạo attempt mới.

### AC-10 — Trạng thái pháp lý

**Given** hệ thống chỉ trích xuất được một văn bản viện dẫn nhưng chưa tra nguồn chính thức, **when** hiển thị, **then** kết quả phải mang nhãn chưa được xác minh ngoài hệ thống và không khẳng định hiệu lực.

## 14. Chiến lược kiểm thử

- Unit test cho validation, parser, rule, policy, state transition và citation validator.
- Integration test cho PostgreSQL, object storage, queue, OCR/model adapter và transaction compensation.
- Contract/API test cho authorization, schema, error code, pagination và idempotency.
- Golden-set evaluation cho extraction, summary, grounded Q&A, contradiction và refusal.
- Security test cho IDOR, tenant isolation, token reuse, brute force, malicious upload và log leakage.
- End-to-end test bằng tài liệu tiếng Việt đại diện: PDF text, PDF scan, hybrid, DOCX, bảng/phụ lục và tài liệu dài.
- User acceptance test với lãnh đạo, chuyên viên tham mưu và chuyên viên pháp lý.

Không phát hành production nếu còn lỗi tenant isolation, citation giả, lộ secret hoặc AI đưa kết luận chắc chắn trong các ca bắt buộc phải từ chối.

## 15. Phân kỳ phát triển

| Giai đoạn | Kết quả |
|---|---|
| P0 — Nền tảng | Auth/tenant, upload, storage, processing, OCR, structure, chunk, status, audit |
| P1 — Intelligence MVP | Index/retrieval, tóm tắt, extraction, decision items, citation, grounded chat |
| P2 — Kiểm tra và chuẩn bị họp | Red flags, critical questions, glossary, personalization và review workflow |
| P3 — Liên kết tri thức | Knowledge graph, báo cáo cũ/mới, multi-document và regulatory version diff |
| P4 — Nền tảng cấp tỉnh | Legal-source integration, task tracking, cross-meeting analytics và kho tri thức thống nhất |

## 16. Hiện trạng repository và khoảng cách so với yêu cầu

| Nhóm | Hiện trạng nhận diện từ repository | Hành động |
|---|---|---|
| Pipeline tài liệu | Đã có nền tảng PDF/DOCX, MinIO, Celery, OCR, structure, chunk và citation metadata | Kiểm thử trên bộ tài liệu thật và chốt ngưỡng chất lượng |
| AI orchestration | Đã có workflow, model gateway, summary, graph, red flag và critical question | Chuẩn hóa output, evaluation và human-review UX |
| Retrieval/chat | Đã có index, hybrid retrieval, chat và SSE contract | Bảo đảm toàn bộ route đi qua tenant authorization và citation validation |
| Bảo mật | Đã có `/api/v1`, JWT/refresh rotation, tenant policy, admin và audit | Di chuyển/bao phủ các legacy capability vào secure v1; tắt legacy production |
| Regulatory change | Đã có vertical slice version/diff/impact/verification | Giữ ở P3 trừ khi đây là use case ưu tiên của MVP |
| Frontend | Có portal và các thành phần UI; một số màn hình còn dữ liệu mẫu | Kết nối API thật và hoàn thiện viewer/citation/review state |
| Dữ liệu cũ/mới | Có nền tảng versioning nhưng workflow proposal chưa hoàn chỉnh xuyên suốt | Bổ sung source role, precedence, inheritance và conflict presentation |
| Legal verification | Mới trích xuất và gắn trạng thái chưa xác minh | Tích hợp nguồn pháp lý chính thức ở giai đoạn sau |

## 17. Phụ thuộc, giả định và điểm cần xác nhận

### 17.1 Phụ thuộc

- Bộ tài liệu hành chính thật đã ẩn danh và bộ nhãn do chuyên gia nghiệp vụ xác nhận.
- Chính sách dữ liệu, retention và phê duyệt sử dụng AI/model provider.
- Nguồn tra cứu pháp luật đáng tin cậy nếu triển khai kiểm tra hiệu lực.
- Hạ tầng object storage, database, queue, monitoring và secret management.

### 17.2 Giả định

- MVP phục vụ tiếng Việt và ưu tiên tài liệu hành chính Việt Nam.
- Người dùng luôn phải đăng nhập; không có chia sẻ tài liệu công khai.
- Phân tích là bất đồng bộ; người dùng có thể rời màn hình và quay lại xem kết quả.
- Human-in-the-loop là yêu cầu bắt buộc đối với cảnh báo, tác động và kết luận pháp lý.

### 17.3 Quyết định cần Product Owner xác nhận

1. Tenant chuẩn là xã, cơ quan, hay workspace và quan hệ phân cấp giữa các cấp.
2. Vai trò nào được upload, chia sẻ, review, xóa, restore và xem audit.
3. Giới hạn tệp, số trang, số tài liệu/workspace và SLA theo gói triển khai.
4. Ngưỡng OCR confidence, extraction confidence và citation support.
5. PII/dữ liệu mật nào được phép gửi tới model provider bên ngoài.
6. Nguồn pháp lý chính thức và trách nhiệm xác nhận trạng thái hiệu lực.
7. Regulatory Change Intelligence có thuộc MVP chính thức hay là nhánh mở rộng.
8. Chính sách lưu lịch sử chat, ghi chú cuộc họp và xóa dữ liệu.

## 18. Definition of Done cho một yêu cầu

Một yêu cầu chỉ được coi là hoàn thành khi có code review, test tự động phù hợp, authorization/tenant scope, audit nếu là mutation quan trọng, tài liệu API, trạng thái lỗi rõ ràng, metric/log cần thiết, kiểm tra không lộ dữ liệu nhạy cảm và Product Owner chấp nhận theo tiêu chí nghiệm thu.
