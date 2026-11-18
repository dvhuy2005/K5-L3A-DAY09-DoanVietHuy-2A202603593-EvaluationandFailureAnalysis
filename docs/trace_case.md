# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Ca đã phân tích

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, run `E-seeded_regression-20261118-f91e` |
| Triệu chứng | Lab 8 grader FAIL: `status resolved != denied`. Reply nói đã hoàn 20.000đ; ledger ghi 20.000đ, trong khi nhãn cần 0đ. |
| Bước sai đầu tiên | Event **3** `model_override`: `{"delay_days": 5}`. |
| Vì sao là bước đầu tiên | Event 1 chỉ tạo handoff đúng phạm vi; event 2 tra order `O-202` từ DB với `delay_days=2`. Event 3 mới thay 2 thành 5 theo ticket. |
| Failure mode | `FM-03 ticket_trust` trong `failure_taxonomy.md`. |
| Đối chứng | `fixed C-002@11`: không có `model_override`; event 3 là quote 0đ, ledger 0đ, status denied, Lab 8 grader PASS. |
| Regression test | `tests/test_lab9_regression.py::test_lab9_ticket_delay_cannot_override_order_fact` xác nhận bản lỗi hoàn 20.000đ và bản sửa hoàn 0đ. |
| Chưa chắc chắn | Trace cho thấy lỗi trong MockLLM/variant công khai; chưa chứng minh agent với model thật sẽ mắc cùng tỷ lệ lỗi. |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
