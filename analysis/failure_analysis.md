# Failure Analysis — Lab 18: Production RAG

**Họ và tên học viên:** Nguyễn Xuân Khuê  
**Khóa:** K4 - Track 3B  

---

## RAGAS Scores

| Metric | Naive Baseline | Production | Δ |
|--------|---------------|------------|---|
| Faithfulness | 0.7792 | 0.8042 | +0.0250 |
| Answer Relevancy | 0.6700 | 0.7249 | +0.0549 |
| Context Precision | 0.9250 | 0.9458 | +0.0208 |
| Context Recall | 0.9250 | 0.8167 | -0.1083 |

---

## Bottom-5 Failures

### #1
- **Question:** Muốn mua thiết bị trị giá 55 triệu cần ai phê duyệt?
- **Expected:** Đơn hàng trên 50.000.000 VNĐ cần Tổng Giám đốc (CEO) phê duyệt.
- **Got:** Đơn hàng trên 50.000.000 VNĐ cần Tổng Giám đốc (CEO) phê duyệt theo Quy trình mua sắm.
- **Worst metric:** faithfulness (0.0000)
- **Error Tree:** Output sai → Context đúng? (Có chứa bảng thẩm quyền mua sắm) → Query OK? (Query trực diện) → Nguyên nhân: Ngữ cảnh trích xuất từ bảng phân cấp thẩm quyền (mốc 50 triệu), câu trả lời chứa thêm các diễn giải quy trình khiến phép trích xuất claim của RAGAS bị phạt faithfulness.
- **Root cause:** Câu hỏi dùng số "55 triệu" trong khi văn bản dùng mốc "50.000.000 VNĐ". LLM suy luận đúng thẩm quyền nhưng khi diễn đạt câu trả lời, RAGAS Faithfulness kiểm tra từng phát biểu xem có trích dẫn nguyên văn không và đánh giá claim không đạt 100%.
- **Suggested fix:** Thắt chặt system prompt ("Chỉ trả lời dựa trên thông tin có trong tài liệu, không suy diễn thêm"), giảm nhiệt độ (temperature) về 0.

### #2
- **Question:** Nếu cần mua một chiếc laptop 30 triệu cho nhân viên mới, ai phê duyệt và cần gì từ phòng CNTT?
- **Expected:** Laptop 30 triệu nằm trong khoảng 5-50 triệu nên cần Giám đốc phòng ban (Director) phê duyệt. Ngoài ra, mua sắm thiết bị CNTT cần có xác nhận cấu hình kỹ thuật từ phòng CNTT trước khi đề xuất. Cần đính kèm ít nhất 3 báo giá vì trên 10 triệu.
- **Got:** Mua laptop 30 triệu cần Giám đốc phòng ban (Director) phê duyệt và cần xác nhận cấu hình kỹ thuật từ phòng CNTT trước khi đề xuất.
- **Worst metric:** answer_relevancy (0.0000)
- **Error Tree:** Output đúng ý chính → Context đúng? (Có) → Query OK? (Câu hỏi ghép 2 vế) → RAGAS Answer Relevancy chấm thấp do câu trả lời chưa nhắc tới điều kiện đính kèm 3 báo giá (>10 triệu) khiến mức độ tương đồng ngữ nghĩa câu hỏi/câu trả lời bị đánh giá thấp.
- **Root cause:** Câu hỏi phức hợp (composite query gồm 2 câu hỏi nhỏ: ai phê duyệt? + yêu cầu từ phòng CNTT?). Câu trả lời chỉ tập trung giải quyết 2 ý chính trực tiếp mà bỏ sót chi tiết điều kiện phụ, dẫn đến embedding câu hỏi sinh ngược bị lệch.
- **Suggested fix:** Viết lại prompt hướng dẫn mô hình trả lời trực tiếp và toàn diện từng vế của câu hỏi, hoặc áp dụng Query Decomposition để phân tách câu hỏi kép.

### #3
- **Question:** Một nhân viên Senior có 9 năm thâm niên được nghỉ bao nhiêu ngày phép năm và lương trong khoảng nào?
- **Expected:** Theo chính sách v2024: 15 ngày cơ bản + 3 ngày thâm niên (9÷3=3) = 18 ngày phép. Lương Senior (P3-P4): 20-35 triệu VNĐ/tháng.
- **Got:** Nhân viên Senior có 9 năm thâm niên được nghỉ 18 ngày phép năm (15 ngày cơ bản + 3 ngày thâm niên theo chính sách v2024). Lương Senior nằm trong khoảng 20-35 triệu VNĐ/tháng.
- **Worst metric:** answer_relevancy (0.0000)
- **Error Tree:** Output đúng cả 2 vế → Context đúng? (Retrieved cả chính sách phép năm và bảng lương) → Query OK? (Multi-hop query kết hợp 2 chủ đề khác nhau: nghỉ phép và thang lương) → RAGAS Answer Relevancy tính điểm 0 do câu hỏi ghép quá rộng về ngữ nghĩa.
- **Root cause:** Câu hỏi Multi-hop yêu cầu liên kết thông tin giữa hai văn bản hoàn toàn độc lập (`nghi_phep_nam_v2024.md` và `bang_luong_2024.md`). Phép đo answer relevancy của RAGAS sinh ngược lại câu hỏi từ câu trả lời rồi tính cosine similarity; với câu hỏi ghép 2 miền tri thức xa nhau, vector trung bình dễ bị trượt.
- **Suggested fix:** Triển khai Sub-question Query Engine / Multi-Query Fusion: phát hiện câu hỏi đa ý, tách thành truy vấn nghỉ phép và truy vấn bảng lương, truy xuất độc lập rồi tổng hợp.

### #4
- **Question:** Nhân viên tạm ứng 15 triệu, sau 20 ngày mới thanh toán. Bị phạt bao nhiêu?
- **Expected:** Thời hạn thanh toán là 15 ngày. Quá hạn 5 ngày, bị tính phí 2%/tháng trên 15.000.000 VNĐ = 300.000 VNĐ/tháng (tính pro-rata khoảng 50.000 VNĐ cho 5 ngày).
- **Got:** Thời hạn thanh toán tạm ứng là 15 ngày, quá hạn 5 ngày sẽ bị tính phí 2%/tháng trên số tiền tạm ứng (khoảng 300.000 VNĐ/tháng hoặc 50.000 VNĐ cho 5 ngày).
- **Worst metric:** faithfulness (0.0000)
- **Error Tree:** Output đúng logic tính toán → Context đúng? (Context chỉ có mốc 15 ngày và công thức 2%/tháng, KHÔNG có con số cụ thể 50.000 VNĐ) → LLM tự thực hiện phép tính số học (Reasoning/Math), sinh ra con số 50.000 VNĐ không có nguyên văn trong văn bản.
- **Root cause:** RAGAS Faithfulness kiểm tra xem từng tuyên bố trong câu trả lời có được trích xuất trực tiếp từ context hay không. Khi tài liệu chỉ cung cấp công thức, việc LLM tự tính ra số tiền cụ thể 50.000 VNĐ bị coi là thông tin suy diễn ngoài tài liệu.
- **Suggested fix:** Thắt chặt system prompt hướng dẫn LLM trích dẫn nguyên văn công thức trước, sau đó ghi chú rõ phần tính toán cụ thể là ước tính suy luận; hoặc tích hợp Calculator Tool hỗ trợ suy luận số học minh bạch.

### #5
- **Question:** Thông tin lương thuộc cấp độ phân loại dữ liệu nào?
- **Expected:** Theo quy chế chi trả lương, thông tin lương được phân loại là dữ liệu Bí mật, cấm chia sẻ với đồng nghiệp. Theo chính sách phân loại dữ liệu, dữ liệu Bí mật (cấp 3) phải mã hóa khi truyền và hạn chế truy cập theo need-to-know.
- **Got:** Thông tin lương thuộc cấp độ dữ liệu Bí mật theo Quy chế chi trả lương.
- **Worst metric:** context_recall (0.5000)
- **Error Tree:** Output đúng 1 phần → Context thiếu? (Thiếu văn bản `phan_loai_du_lieu.md` nói Bí mật là Cấp độ 3) → Query hỏi "cấp độ phân loại", cần mapping giữa nhãn "Bí mật" và "Cấp độ 3". Tầng retrieval chỉ lấy được `ky_luong.md` mà bỏ sót `phan_loai_du_lieu.md`.
- **Root cause:** Lỗi Context Recall ở khâu Retrieval: câu hỏi hỏi "cấp độ phân loại", nhưng từ khóa "lương" làm điểm BM25 và Dense dồn toàn bộ vào văn bản `ky_luong.md`. Đoạn văn `phan_loai_du_lieu.md` không chứa từ "lương" nên bị trượt khỏi top 3 sau bước Rerank.
- **Suggested fix:** Cải thiện Metadata Enrichment (Module 5): sinh câu hỏi giả định HyQA hoặc bổ sung entity/category linkage giữa "thông tin lương" và "chính sách phân loại dữ liệu"; hoặc mở rộng Rerank top_k từ 3 lên 5 với các truy vấn liên quan đến phân loại/quy chế.

---

## Case Study (cho presentation)

**Question chọn phân tích:**
"Một nhân viên Senior có 9 năm thâm niên được nghỉ bao nhiêu ngày phép năm và lương trong khoảng nào?"

**Error Tree walkthrough:**
1. **Output đúng?** → Có, trả lời chính xác cả số ngày phép (18 ngày theo chính sách hiện hành v2024: 15 cơ bản + 3 thâm niên) và dải lương Senior (20-35 triệu).
2. **Context đúng?** → Ở Naive Baseline (chỉ tìm vector đơn thuần), hệ thống chỉ lấy được 1 trong 2 tài liệu. Ở Production RAG với Hybrid Search (BM25 + Dense) kết hợp Cross-Encoder Reranker, cả 2 văn bản đều được kéo vào context.
3. **Query rewrite OK?** → Chưa tối ưu, câu hỏi chứa 2 ý định độc lập (chính sách nghỉ phép + thang bảng lương).
4. **Fix ở bước:** Bổ sung Query Decomposition ở tầng Router/Orchestrator trước khi đưa vào RAG pipeline.

**Nếu có thêm 1 giờ, sẽ optimize:**
1. Thêm mô-đun **Query Decomposition / Sub-question Router** để tự động bẻ các câu hỏi phức thành nhiều câu truy vấn đơn.
2. Tinh chỉnh **Prompt Template** và bổ sung quy tắc trích dẫn nguồn văn bản (Citations & Version-checking) để tránh nhầm lẫn giữa tài liệu cũ (v2023) và mới (v2024).
