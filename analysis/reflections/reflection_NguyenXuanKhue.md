# Individual Reflection — Lab 18: Production RAG

**Họ và tên:** Nguyễn Xuân Khuê  
**Khóa:** K4 - Track 3B  
**Ngày hoàn thành:** 04/10/2026  

---

## Phần 1: Mapping bài giảng (Lecture Mapping)
Map từng concept trong lecture vào code bạn vừa viết trong lab:

| Lecture Concept | Module | Hàm cụ thể | Observation & Phân tích |
|----------------|--------|-------------|--------------------------|
| Semantic chunking | M1 | `chunk_semantic()` | Dùng mô hình `all-MiniLM-L6-v2` mã hóa câu và tính cosine similarity giữa các câu liên tiếp; ngắt đoạn khi độ tương đồng rơi xuống dưới ngưỡng threshold ($0.85$). Kết quả tạo ra các chunk bảo toàn trọn vẹn ngữ nghĩa từng chủ đề thay vì cắt ngang giữa câu như basic chunking. |
| Hierarchical chunking | M1 | `chunk_hierarchical()` | Chia tài liệu theo mô hình phân cấp Cha - Con: đoạn cha lớn (2048 ký tự) lưu giữ bối cảnh toàn diện, các đoạn con nhỏ (256 ký tự) giúp tìm kiếm vector/BM25 chính xác từ khóa. Mỗi đoạn con liên kết với đoạn cha qua `parent_id`. Đây là chiến lược mặc định tối ưu nhất cho Production RAG. |
| Structure-aware chunking | M1 | `chunk_structure_aware()` | Phân tích tiêu đề Markdown (`#`, `##`, `###`) bằng regex để gom đoạn theo cấu trúc logic của văn bản quy phạm, bảo toàn nguyên vẹn bảng biểu, danh sách và lưu tên mục vào `metadata["section"]`. |
| BM25 + Dense fusion | M2 | `reciprocal_rank_fusion()` | Kết hợp thế mạnh bắt từ khóa chính xác của BM25 (đã chuẩn hóa tách từ tiếng Việt qua `underthesea` và chuyển `_` thành khoảng trắng) với khả năng hiểu ngữ nghĩa sâu của Dense Search (`BAAI/bge-m3`). Thuật toán RRF ($k=60$) độc lập thang đo điểm số, gộp thứ hạng chuẩn xác. |
| Cross-encoder reranking | M3 | `CrossEncoderReranker.rerank()` | Tầng lọc thứ hai sử dụng mô hình Cross-Encoder `BAAI/bge-reranker-v2-m3` đánh giá đồng thời cả cặp (câu hỏi, đoạn trích) để lọc từ 20 ứng viên xuống top 3 xuất sắc nhất. Thời gian phản hồi chỉ vài chục mili-giây nhưng tăng vọt Context Precision (đạt $0.9458$). |
| RAGAS 4 metrics | M4 | `evaluate_ragas()` / `failure_analysis()` | Tự động đo lường chất lượng hệ thống qua 4 chỉ số: Faithfulness ($0.8042$), Answer Relevancy ($0.7249$), Context Precision ($0.9458$), Context Recall ($0.8167$). Kết hợp cây chẩn đoán (Diagnostic Tree) để tự động phân loại nguyên nhân lỗi và đề xuất hướng khắc phục. |
| Contextual embeddings & Enrichment | M5 | `contextual_prepend()` / `_enrich_single_call()` | Làm giàu ngữ cảnh văn bản trước khi lập chỉ mục: bổ sung tóm tắt, câu hỏi giả định HyQA, câu bối cảnh vị trí tài liệu (Contextual Prepend) và siêu dữ liệu tự động. Tối ưu gom 4 tác vụ vào 1 lần gọi LLM duy nhất giúp tiết kiệm chi phí và tăng tốc độ xử lý. |

---

## Phần 2: Khó khăn & Cách giải quyết (Challenges & Debugging)

- **Lỗi kỹ thuật gặp phải (Exact error message):**
  - Khi bắt đầu chạy thử nghiệm với `sentence_transformers` và `pandas`, gặp lỗi:
    ```text
    ImportError: DLL load failed while importing indexing: An Application Control policy has blocked this file.
    ```
  - Khi sử dụng thư viện `underthesea`, các từ ghép tiếng Việt bị nối bằng dấu `_` (như `nghỉ_phép`), dẫn đến việc BM25 tokenize bằng dấu cách không khớp được với câu hỏi người dùng gõ từ khóa thông thường (`nghỉ phép`).

- **Nguyên nhân gốc rễ & Cách debug:**
  - *Lỗi DLL:* Do tính năng an ninh **Smart App Control (SAC)** trên Windows 11 chặn nạp các file extension C++ (`.pyd` / `.dll`) chưa có chữ ký số Authenticode thương mại từ Microsoft của các thư viện mã nguồn mở (`pandas._libs.indexing`). Đã xác định nguyên nhân qua khóa registry `HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy` (`VerifiedAndReputablePolicyState = 1`) và xử lý bằng cách tắt Smart App Control trong Windows Security.
  - *Lỗi tách từ BM25:* Thư viện `underthesea` sinh ra định dạng từ ghép có dấu gạch dưới. Để sửa triệt để, sau khi gọi `word_tokenize(text, format="text")`, thực hiện thêm bước chuẩn hóa chuỗi bằng `.replace("_", " ")` trước khi đưa vào `BM25Okapi`.

- **Kiến thức còn thiếu & Cách khắc phục:**
  - Cần hiểu sâu hơn về kiến trúc Bi-Encoder (Dense Search) vs Cross-Encoder: Bi-Encoder ánh xạ độc lập hai vector nên nhanh nhưng mất thông tin tương tác giữa các token, trong khi Cross-Encoder cho token của query và document tương tác chéo qua các lớp self-attention nên độ chính xác phân biệt ngữ cảnh vượt trội.
  - Nắm vững công thức RRF và cách RAGAS đánh giá: RAGAS Answer Relevancy sử dụng LLM để sinh ngược lại câu hỏi từ câu trả lời rồi tính cosine embedding, do đó với các câu hỏi phức hợp đa ý (multi-hop) cần phải áp dụng thêm kỹ thuật Query Decomposition để đạt điểm tối ưu.

---

## Phần 3: Action Plan cho Project cá nhân (Application Plan)

Dựa trên những kỹ thuật đã học và thực hành, lập kế hoạch cụ thể áp dụng vào project của bạn:

### Project: Hệ thống Trợ lý Pháp lý & Tra cứu Quy chế Doanh nghiệp (Enterprise Legal Assistant RAG)

#### 1. Hiện trạng
- **Pipeline hiện tại:** Sử dụng Naive RAG cơ bản với Recursive Character Text Splitter (cắt cố định 500 ký tự) và Dense Search thuần túy qua OpenAI `text-embedding-3-small`.
- **Vấn đề / Bottlenecks đang gặp:**
  - *Mất bối cảnh quy định:* Các điều khoản luật hoặc chính sách nội bộ bị cắt đứt giữa chừng, mất liên kết với tiêu đề chương mục.
  - *Xung đột phiên bản văn bản:* Không phân biệt được quy chế cũ (đã hết hiệu lực) và quy chế mới sửa đổi bổ sung.
  - *Bỏ sót từ khóa mã hiệu văn bản:* Tìm kiếm vector thường trượt các mã số điều khoản, số hiệu công văn chính xác (như "Nghị định 13/2023", "Thông tư 05").

#### 2. Kế hoạch cải tiến
1. **Chunking strategy:** Áp dụng **Hierarchical Chunking** kết hợp **Structure-Aware Chunking**. Chia tài liệu theo các cấp Điều/Khoản lớn làm đoạn cha (Parent $\approx$ 2048 ký tự) và tách nhỏ từng điểm quy định thành đoạn con (Child $\approx$ 256 ký tự) lưu kèm số hiệu điều khoản và phiên bản văn bản trong metadata.
2. **Search retrieval:** Chuyển sang **Hybrid Search** kết hợp BM25 (đã chuẩn hóa tách từ tiếng Việt) và Dense Search (`BAAI/bge-m3`), gộp kết quả bằng thuật toán **RRF ($k=60$)**. BM25 sẽ bắt trúng 100% các số hiệu văn bản và mốc thời gian, trong khi Dense Search hiểu ngữ nghĩa câu hỏi tự nhiên.
3. **Reranking:** Tích hợp tầng **Cross-Encoder Reranker** (`BAAI/bge-reranker-v2-m3`) để sàng lọc từ top 25 kết quả xuống top 3 đoạn trích đắt giá nhất trước khi gửi vào LLM.
4. **Evaluation:** Thiết lập bộ 50 câu hỏi benchmark thực tế và chấm điểm tự động định kỳ bằng **RAGAS 4 metrics** (mục tiêu: Faithfulness $\ge 0.85$, Context Precision $\ge 0.90$).
5. **Enrichment:** Sử dụng **Contextual Prepend** để gắn tên văn bản, ngày ban hành và trạng thái hiệu lực vào đầu mỗi chunk; tự động trích xuất metadata (cơ quan ban hành, đối tượng áp dụng).

#### 3. Timeline triển khai
- **Tuần 1:** Tái cấu trúc cơ sở tri thức: Viết script phân đoạn Markdown theo cấu trúc Điều/Khoản (Structure-Aware & Hierarchical), thiết lập metadata phiên bản văn bản.
- **Tuần 2:** Triển khai Hybrid Search (BM25 + Qdrant) trên Docker, tích hợp thuật toán RRF và thử nghiệm kiểm thử từ khóa pháp lý.
- **Tuần 3:** Tích hợp Cross-Encoder Reranker, tinh chỉnh system prompt chống hallucination, thiết lập CI/CD pipeline tự động đánh giá RAGAS.
