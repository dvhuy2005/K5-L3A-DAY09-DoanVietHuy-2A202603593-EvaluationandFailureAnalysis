# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có | Chỉ dùng để theo dõi giọng điệu; không dùng để chấm tiền |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không | Loại khỏi gate |

## ≥5 case audit thủ công
| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú |
|---|---|---|---|---|---|
| 1 | H-008 | PASS | FAIL | Người | “em … nha” quá suồng sã; rubric cần cấm cách xưng hô này với khách. |
| 2 | H-017 | PASS | FAIL | Người | “bạn ơi … nha” không phù hợp; thêm ví dụ phản diện. |
| 3 | H-029 | PASS | FAIL | Người | “không cần nhắn thêm” mang giọng ra lệnh; judge phải đọc toàn câu. |
| 4 | H-042 | FAIL | PASS | Người | Ngắn vẫn lịch sự và đủ ý; bỏ yêu cầu phải có lời xin lỗi. |
| 5 | H-051 | FAIL | PASS | Người | Từ “refund” được CS LogiX cho phép; thêm vào ví dụ hợp lệ. |
| 6 | HL-015 | PASS | FAIL | Người | Reply nói 55.000đ, ledger 40.000đ; helpful phải kiểm tiền bằng code. |
| 7 | HL-016 | PASS | FAIL | Người | Lời xin lỗi dài không cứu được số tiền 55.000đ sai so với ledger 35.000đ. |
| 8 | HL-020 | PASS | FAIL | Người | Reply 90.000đ, ledger 120.000đ; thêm kiểm tra số tiền trước khi xét văn phong. |

## Kết luận
- `tone_ok` qua sàn: TP=24, FP=4, FN=6, TN=66. Tỷ lệ lỗi quan sát 0.28; Rogan-Gladen hiệu chỉnh thành 0.30. Vẫn cần kiểm tra tay với tình huống mới.
- `helpful` bị loại: TP=9, FP=0, **FN=21**, TN=70; recall 0.30 và κ 0.375. Nó bỏ lọt nhiều reply nói sai tiền vì nghe có vẻ lịch sự. Tiền và approval phải chấm bằng code đối chiếu ledger, không giao cho judge này.
- Rủi ro còn lại: judge chỉ được kiểm trên dữ liệu replay công khai, chưa có tập nhãn người độc lập.
