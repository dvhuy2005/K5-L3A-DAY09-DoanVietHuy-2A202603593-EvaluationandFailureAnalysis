# Eval card — LogiX-VN refund agent

Card này đi kèm report v1 và được dùng lại ở Day 10. Tất cả số liệu sau lấy từ report do `lab9.eval` sinh, không chỉnh tay.

- **Run IDs:** baseline `E-swarm-20261118-f91e`; fixed `E-fixed-20261118-f91e`; seeded regression `E-seeded_regression-20261118-f91e`.
- **Phiên bản:** eval set v1 SHA `f91e7e14bec0`; metric spec `1.0`; MockLLM; Python 3.14.7 trên máy hiện tại; seed 11/22/33/44/55. Commit code và grader nằm trong PR #1.
- **Eval set:** 14 item × 5 seed = 70 trial, nguồn `lab8_public`; item và nhãn ở `src/data/eval/eval_set_v1.jsonl` và `labels_v1.json`.
- **Metric và ngưỡng:** theo `src/config/metric_spec.yaml`. An toàn: approval bypass = 0, secret leak = 0. Năng lực chặn release: refund amount, status và proposal ≥0.95; pass rate ≥0.85; reply/ledger match =1.0. Refund amount và pass rate còn phải không giảm có ý nghĩa thống kê.

| Report | Pass rate | Refund amount correct | Reply/ledger match | Approval bypass | Secret leak | Gate |
|---|---:|---:|---:|---:|---:|---|
| Baseline swarm | 0.9857 | 0.9857 | 1.0 | 0 | 0 | Mốc so sánh |
| Fixed | 1.0 | 1.0 | 1.0 | 0 | 0 | `exit 0` |
| Seeded regression | 0.7143 | 0.8571 | 0.7857 | 0 | 0 | `exit 1`: pass_rate, refund_amount_correct, status_correct, proposal_correct, reply_ledger_match |

Paired bootstrap trên cùng 14 item: fixed − baseline, pass rate Δ=+0.014, CI 95% [+0.000,+0.043]; seeded − baseline, Δ=−0.271, CI [−0.500,−0.057]. Vì CI của seeded nằm dưới 0, gate chặn. CI và giá trị có thể tái tạo bằng lệnh trong `src/lab9/gate.py`.

- **Judge calibration:** `tone_ok` κ=0.757, precision=0.857, recall=0.800 nên qua sàn của bài; `helpful` κ=0.375, recall=0.300 nên bị loại. Xem `docs/judge_audit.md`.
- **Trace case:** `docs/trace_case.md` chỉ ra event 3 `model_override` của `C-002@11`; `tests/test_lab9_regression.py` bắt lại lỗi này.
- **Gate owner:** Đoàn Việt Huy rà soát khi gate exit 1; ngoại lệ cần TA/giảng viên duyệt.
- **Phạm vi pilot:** claim hoàn tiền giả lập trong bộ Lab 8; không xử lý tiền thật.
- **Giới hạn:** MockLLM, chỉ 14 item và 5 seed; judge replay công khai, chưa có đánh giá người dùng thật hoặc tập held-out mới. Lỗi chỉ xuất hiện 1/3 seed khó phát hiện ổn định với 5 seed.
- **Khi tăng phiên bản:** thêm item/tình huống mới thì tăng `eval_set_version` và chạy baseline mới; đổi metric/ngưỡng thì tăng `metric_spec_version` và ghi lý do.

## V2 — tình huống khó, độ ổn định và bảo vệ cổng

- **Run ID / eval set:** `E-swarm-20261118-7fb5`; SHA `7fb5a0eb3ed2`; 28 item × 5 seed, gồm 14 item v1 và 14 item adversarial. Nhãn vẫn ở file riêng `labels_v2.json`.
- **A/A:** cùng agent với hai nhóm seed 11/22/33/44/55 và 66/77/88/99/110 cho `pass_hat_5` đều bằng **0.8929**, Δ=0. Chọn ngưỡng chặn **0.80**, thấp hơn mức đã đo; với model thật nhiễu có thể lớn hơn và cần bộ A/A mới. Bản `flaky_regression` đạt 0.5714 nên bị chặn.
- **Slice:** baseline `money_movement` có pass rate 1.0 trên 12 item, `adversarial` 0.9714 trên 14 item. Đặt sàn lần lượt 0.95 và 0.90. `slice_regression` có pass rate tổng 0.9357 (trên sàn 0.85), nhưng nhóm `money_movement` chỉ 0.85, nên gate chặn riêng slice đó. CI tổng Δ=−0.043, khoảng [−0.121,+0.029] chạm 0 và không đủ chặn một mình.
- **Scorecard:** `lab9.mutation` chặn 3/3 regression công khai (`seeded`, `slice`, `flaky`) và cho qua `fixed`, `honest_refactor` (0 báo nhầm). `lab9.traps` chặn 4/4 cách sửa report/spec công khai: NaN, bỏ dòng fail, chọn seed đẹp, nới ngưỡng. Bộ chấm khác của giảng viên có thể còn tìm lỗi chưa thấy.
- **Giới hạn cỡ mẫu:** lỗi chỉ xuất hiện 1/3 seed khó phát hiện ổn định với 5 seed; không hạ ngưỡng chỉ để bắt một mẫu công khai. A/A Δ=0 là đặc tính của MockLLM cố định, không phải cam kết cho model thật.
