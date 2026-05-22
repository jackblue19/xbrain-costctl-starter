# REFLECTIONS

## 1. Multi-account support

Nếu cần chạy costctl trên 100 AWS accounts, em sẽ không hardcode credential trong code. Em sẽ dùng cross-account IAM Role, sau đó tool sẽ assume role từng account bằng STS. CLI có thể nhận danh sách account/profile từ file YAML/JSON, loop qua từng account, chạy list/cost/clean ở từng region, rồi export kết quả ra CSV/TXT.

P/S:
- Mỗi account phải có role permission rõ ràng.
- Không dùng access key admin lâu dài.
- Mọi destructive command như clean/terminate phải có dry-run, confirm, và allowlist account. (ko nên --apply)
- Output cần có thêm account_id và region để tránh nhầm resource.

## 2. Blast radius của clean --apply

`clean --apply` nguy hiểm vì nó có thể xoá nhiều resource cùng lúc. Nếu chạy nhầm tag như Environment=dev trong account dùng chung, tool có thể terminate resource của team khác.

    => chỉ test thì nên là ko dùng còn nếu thực tiễn cần dùng thì mới --apply

Các guardrail em muốn thêm:
- Mặc định dry-run -> an toàn.
- Bắt buộc nhập exact confirmation phrase, ví dụ: DELETE purpose=practice.
- Chỉ cho clean resource có tag Owner=jack hoặc Project=W6.
- Có `--max-count` để chặn xoá quá nhiều resource.
- Có account/region summary trước khi apply.
- Ghi audit log ra file trước khi xoá.

## 3. AI assistance

Em dùng AI để giải thích requirement, đề xuất flow implement, và hỗ trợ viết code logic các func trong từng file pytho. Tuy nhiên, em vẫn tự đọc test cases, chạy pytest, sửa lỗi theo expected behavior, và verify bằng AWS CLI thật. Những phần em kiểm soát kỹ nhất là confirm safety, S3 non-empty guard, dry-run behavior, và AWS profile/region setup.