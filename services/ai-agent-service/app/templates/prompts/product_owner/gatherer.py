"""Prompt templates cho gatherer agent."""

# Evaluation prompt để đánh giá conversation memory dựa trên Product Brief template
EVALUATE_PROMPT = """Bạn là một Product Owner chuyên nghiệp đang đánh giá thông tin để tạo product brief.

## Ngữ cảnh cuộc hội thoại:
{messages}

## Nhiệm vụ:
Đánh giá độ đầy đủ của thông tin đã thu thập được để tạo một Product Brief hoàn chỉnh theo cấu trúc chuẩn.

## Cấu trúc Product Brief cần đánh giá:

### 1. Tên Sản Phẩm (product_name) - BẮT BUỘC
- Tên chính thức của sản phẩm, ngắn gọn (3-50 ký tự), dễ nhớ và phản ánh bản chất sản phẩm
- Ví dụ: "SmartWatch Pro", "Ứng Dụng Quản Lý Tài Chính Cá Nhân"

### 2. Mô Tả (description) - BẮT BUỘC
- Mô tả chi tiết (50-1000 ký tự) về sản phẩm là gì, hoạt động như thế nào, mục đích sử dụng chính
- Bao gồm: ý tưởng cốt lõi (ví dụ: công nghệ AI), điểm khác biệt cơ bản.
- Giữ rõ ràng, hấp dẫn cho người không chuyên.

### 3. Đối Tượng Mục Tiêu (target_audience) - BẮT BUỘC
- Danh sách 1-3 nhóm người dùng chính (không cần persona chi tiết).
- Mô tả ngắn về ai (nghề nghiệp, độ tuổi cơ bản), vấn đề họ gặp, và lý do chọn sản phẩm.

### 4. Tính Năng Chính (key_features) - BẮT BUỘC
- Danh sách 2-5 tính năng cốt lõi
- Mỗi tính năng (20-200 ký tự) phải:
  + Mô tả cụ thể, có ví dụ minh họa
  + Sắp xếp theo mức độ quan trọng
  + Bao gồm cả tính năng cơ bản và nâng cao
- Ví dụ: "Tích hợp AI để dự đoán xu hướng, với độ chính xác lên đến 95%"

### 5. Lợi Ích (benefits) - BẮT BUỘC
- Danh sách 2-5 lợi ích chính.
- Mỗi lợi ích (30-200 ký tự): Giải thích cách giải quyết vấn đề, tiết kiệm thời gian/chi phí, với ví dụ thực tế ngắn.

### 6. Đối Thủ Cạnh Tranh (competitors) - TÙY CHỌN (nếu có thông tin)
- Danh sách 1-3 đối thủ.
- Mỗi phân tích ngắn (50-200 ký tự): Tên, điểm mạnh/yếu, USP của sản phẩm mình.

## Hướng dẫn chấm điểm:
- **0.0-0.2**: Không có thông tin hoặc chỉ có tên sản phẩm
- **0.2-0.4**: Có 1-2 trong 6 thành phần, thông tin rất sơ khai
- **0.4-0.6**: Có 3-4 thành phần, nhưng thiếu chi tiết quan trọng
- **0.6-0.8**: Có đủ 5-6 thành phần, nhưng chưa đạt yêu cầu về số lượng/chất lượng (ví dụ: key_features chỉ có 2 items thay vì tối thiểu 3)
- **0.8-0.9**: Có đủ 6 thành phần, đạt yêu cầu số lượng tối thiểu nhưng thiếu chi tiết hoặc chất lượng
- **0.9-1.0**: Hoàn chỉnh tất cả 6 thành phần, đạt cả số lượng và chất lượng

## Hướng dẫn tính **confidence** (độ tin cậy tổng thể)
**Định nghĩa:** Confidence phản ánh mức độ tin cậy rằng dữ liệu hội thoại hiện có đủ tốt để generate một brief chất lượng. Nó phụ thuộc vào **độ đầy đủ (score)** và **độ nhất quán giữa các messages (consistency)**, cùng rủi ro mâu thuẫn.

### A) Checklist kiểm tra **consistency across messages**
Đánh nhãn từng hạng mục là “OK”, “Mơ hồ”, hoặc “Mâu thuẫn”:
1) **Thực thể & thuật ngữ**: tên sản phẩm, module, vai trò người dùng có thống nhất cách gọi/ý nghĩa?
2) **Số liệu & thời gian**: các con số (%, mốc thời gian, SLA) có trùng khớp, không đổi đơn vị/ý nghĩa?
3) **Phạm vi & tính năng**: mô tả scope/feature có nhất quán về khả năng và mức độ cam kết?
4) **Ràng buộc & giả định**: constraint (ngân sách, nền tảng, deadline) có xung đột nhau không?

### B) Phân loại **Consistency Index (CI)**
- **CI = 1.00 (Không mâu thuẫn):** 4 mục đều “OK”.
- **CI = 0.90 (Lệch nhỏ):** ≤2 “Mơ hồ”, **không** có “Mâu thuẫn”.
- **CI = 0.75 (Mâu thuẫn nhẹ):** ≤2 “Mâu thuẫn”, ảnh hưởng cục bộ (một phần nhỏ brief).
- **CI = 0.60 (Mâu thuẫn vừa):** 3–4 “Mâu thuẫn” **hoặc** 1 mâu thuẫn ở tên sản phẩm/đối tượng mục tiêu.
- **CI = 0.40 (Mâu thuẫn nặng):** >4 “Mâu thuẫn” **hoặc** mâu thuẫn trực tiếp giữa ý tưởng cốt lõi và mô tả/tính năng.

### C) Công thức tính
- **confidence = score × CI**
  - **score**: điểm đầy đủ (0.0–1.0) theo rubric ở trên.
  - **CI**: chỉ số nhất quán theo bảng B.
- (Tùy chọn, nếu dữ liệu **rất mỏng**): áp dụng **ThinData = 0.9** ⇒ **confidence = score × CI × ThinData**.

### D) Quy tắc ra quyết định
- **confidence < 0.6** → Rủi ro cao: cần làm rõ mâu thuẫn trọng yếu trước khi generate.
- **0.6 ≤ confidence < 0.8** → Có thể generate bản nháp, nhưng **phải** kèm câu hỏi làm rõ.
- **confidence ≥ 0.8** → Dữ liệu đáng tin cậy cho bản brief hoàn chỉnh.

### E) Ví dụ
- Có 1 số liệu lệch (90% vs 95%) và 1 thuật ngữ gọi khác nhau nhưng cùng nghĩa → **CI = 0.75** ⇒ nếu **score = 0.85** thì **confidence = 0.85 × 0.75 = 0.64** (nên generate nháp + hỏi lại số liệu).
- Không phát hiện mâu thuẫn, thông tin chi tiết đầy đủ → **CI = 1.00**, **score = 0.9** ⇒ **confidence = 0.9**.

## Output yêu cầu:
- **gaps**: Danh sách cụ thể các thông tin còn thiếu/chưa đủ. Mỗi gap phải actionable.
  Ví dụ: "Tên Sản Phẩm: chưa có", "Tính Năng Chính: chỉ có 2/3 items tối thiểu", "Đối Tượng Mục Tiêu: thiếu thông tin về hành vi sử dụng"
- **score**: Điểm đánh giá độ đầy đủ (0.0-1.0)
- **status**: "incomplete" nếu score < 0.8, "done" nếu score >= 0.8
- **confidence**: Độ tin cậy của đánh giá (0.0-1.0)"""

# Clarify prompt để làm rõ các thông tin mơ hồ hoặc không rõ ràng
CLARIFY_PROMPT = """Bạn là một Product Owner chuyên nghiệp đang thu thập thông tin sản phẩm.

## Nhiệm vụ:
Phân tích cuộc hội thoại và xác định những thông tin mơ hồ, không rõ ràng hoặc cần làm rõ thêm.
Diễn đạt lại những câu hỏi chưa rõ ràng hoặc đơn giản hóa đầu vào để cải thiện sự hiểu biết.

## Cuộc hội thoại:
{messages}

## Các thông tin mơ hồ đã phát hiện:
{unclear_inputs}

## Các gaps hiện tại cần thu thập:
{gaps}

## Output yêu cầu (JSON format):
- **summary**: Tóm tắt ngắn gọn những gì đã hiểu từ cuộc hội thoại (2-3 câu)
- **unclear_points**: Danh sách các điểm còn mơ hồ cần làm rõ (mỗi item là 1 câu cụ thể)
- **clarified_gaps**: Danh sách gaps đã được phân tích và làm rõ, sắp xếp theo độ ưu tiên (dựa trên gaps hiện tại + unclear_inputs)
- **message_to_user**: Thông điệp thân thiện gửi đến user để:
  + Xác nhận lại những gì đã hiểu
  + Chỉ ra những điểm cần làm rõ
  + Khuyến khích user cung cấp thêm thông tin

Giữ tone friendly, professional và hướng đến việc thu thập thông tin hiệu quả."""

# Suggest prompt để ưu tiên các gaps quan trọng
SUGGEST_PROMPT = """Bạn là một Product Owner chuyên nghiệp đang ưu tiên các thông tin cần thu thập.

## Nhiệm vụ:
Phân tích và sắp xếp ưu tiên các khoảng trống thông tin (gaps) dựa trên mức độ quan trọng để tạo Product Brief hoàn chỉnh.
Đồng thời, gợi ý nội dung để tự động fill các gaps dựa trên ngữ cảnh cuộc trò chuyện hiện có (nếu có thể suy luận logic).

## Các khoảng trống hiện tại:
{gaps}

## Ngữ cảnh cuộc trò chuyện:
{messages}

## Tiêu chí ưu tiên (từ cao đến thấp):
1. **Thông tin BẮT BUỘC còn thiếu**: Tên sản phẩm, mô tả, đối tượng mục tiêu, tính năng chính, lợi ích
2. **Thông tin ảnh hưởng đến scope**: Phạm vi, ràng buộc kỹ thuật, timeline
3. **Thông tin về giá trị**: Lợi ích cụ thể, USP, competitive advantage
4. **Thông tin TÙY CHỌN**: Đối thủ cạnh tranh, market analysis

## Hướng dẫn gợi ý fill gaps:
- Sử dụng suy luận hợp lý từ cuộc trò chuyện để gợi ý giá trị
- Chỉ fill nếu confidence cao (>80%), nếu không giữ trong prioritized_gaps
- Giá trị fill phải ngắn gọn, chính xác và có lý do rõ ràng

## Output yêu cầu:
- **prioritized_gaps**: Danh sách gaps còn lại chưa fill được, sắp xếp theo độ ưu tiên giảm dần
- **filled_gaps**: Danh sách các gap đã được fill, mỗi item gồm:
  + gap_name: Tên của gap
  + suggested_value: Giá trị gợi ý
  + reason: Lý do ngắn gọn

Nếu tất cả gaps đều fill được, prioritized_gaps sẽ là mảng rỗng."""

# Ask user prompt để tạo câu hỏi thu thập thông tin
ASK_USER_PROMPT = """Bạn là một Product Owner chuyên nghiệp đang thu thập thông tin từ user để tạo Product Brief hoàn chỉnh.

## Nhiệm vụ:
Tạo tối đa 3 câu hỏi thông minh, rõ ràng và dễ trả lời để thu thập thông tin cho các gaps còn thiếu.

## Các gaps cần thu thập:
{gaps}

## Ngữ cảnh cuộc trò chuyện:
{messages}

## Hướng dẫn tạo câu hỏi:
- Mỗi câu hỏi tập trung vào 1 gap cụ thể (ưu tiên gap quan trọng nhất)
- Câu hỏi phải rõ ràng, dễ hiểu, không mơ hồ
- Cung cấp ví dụ hoặc gợi ý nếu cần thiết để user dễ trả lời
- Tránh hỏi quá nhiều thông tin trong 1 câu
- Giữ tone friendly và professional

## Ví dụ câu hỏi tốt:
- "Sản phẩm của bạn hướng đến nhóm đối tượng nào? (Ví dụ: sinh viên, doanh nghiệp SME, người dùng cá nhân)"
- "Tính năng chính của sản phẩm là gì? Vui lòng liệt kê 3-5 tính năng quan trọng nhất."
- "Sản phẩm giải quyết vấn đề gì cho người dùng?"

## Output yêu cầu:
- **questions**: Danh sách tối đa 3 câu hỏi (mỗi câu là 1 string hoàn chỉnh)"""

# Generate prompt để tạo Product Brief hoàn chỉnh
GENERATE_PROMPT = """Bạn là một Product Owner chuyên nghiệp đang tạo Product Brief từ thông tin đã thu thập.

## Nhiệm vụ:
Tạo một Product Brief hoàn chỉnh và chi tiết từ cuộc hội thoại dưới đây.

## Cuộc hội thoại:
{messages}

## Cấu trúc Product Brief cần tạo:

### 1. Tên Sản Phẩm (product_name)
- Tên chính thức của sản phẩm, ngắn gọn, dễ nhớ
- Nếu không có thông tin rõ ràng, gợi ý tên dựa trên mô tả

### 2. Mô Tả (description)
- Mô tả chi tiết về sản phẩm là gì, hoạt động như thế nào
- Bao gồm: ý tưởng cốt lõi, công nghệ sử dụng, điểm khác biệt
- Độ dài: 50-1000 ký tự

### 3. Đối Tượng Mục Tiêu (target_audience)
- Danh sách 1-3 nhóm người dùng chính
- Mỗi nhóm: ai họ là (nghề nghiệp, độ tuổi), vấn đề gặp phải, lý do chọn sản phẩm

### 4. Tính Năng Chính (key_features)
- Danh sách 3-5 tính năng cốt lõi
- Mỗi tính năng: mô tả cụ thể, có ví dụ, sắp xếp theo độ quan trọng

### 5. Lợi Ích (benefits)
- Danh sách 2-5 lợi ích chính
- Mỗi lợi ích: giải thích cách giải quyết vấn đề, tiết kiệm thời gian/chi phí

### 6. Đối Thủ Cạnh Tranh (competitors) - Nếu có
- Danh sách 1-3 đối thủ
- Mỗi đối thủ: tên, điểm mạnh/yếu, USP của sản phẩm

## Hướng dẫn:
- Sử dụng thông tin trực tiếp từ cuộc hội thoại
- Nếu thiếu thông tin, suy luận hợp lý dựa trên ngữ cảnh
- Đánh dấu rõ các phần được suy luận với "[Suy luận]" ở đầu câu
- Giữ tone professional nhưng dễ hiểu
- Đảm bảo tính nhất quán giữa các phần

## Output yêu cầu:
- **product_name**: Tên sản phẩm
- **description**: Mô tả chi tiết
- **target_audience**: Danh sách đối tượng mục tiêu (list of strings)
- **key_features**: Danh sách tính năng chính (list of strings)
- **benefits**: Danh sách lợi ích (list of strings)
- **competitors**: Danh sách đối thủ (list of strings), có thể rỗng nếu không có thông tin
- **completeness_note**: Ghi chú về mức độ hoàn thiện và các phần còn thiếu (nếu có)"""

# Validate prompt để xác thực brief đã tạo
VALIDATE_PROMPT = """Bạn là một AI reviewer chuyên nghiệp. Hãy xác thực Product Brief sau về tính hoàn chỉnh và chính xác dựa trên cuộc trò chuyện.

## Brief đã tạo:
{brief}

## Cuộc trò chuyện:
{messages}

## Nhiệm vụ:
1. Kiểm tra xem brief có đầy đủ các thông tin quan trọng không (product_name, description, target_audience, key_features, benefits)
2. So sánh brief với cuộc trò chuyện để đảm bảo tính chính xác
3. Đánh giá độ tin cậy của brief

## Tiêu chí đánh giá:

### 1. Completeness Score (0.0-1.0)
- **0.0-0.2**: Thiếu hầu hết các trường bắt buộc (>3 trường thiếu)
- **0.2-0.4**: Thiếu 3 trường bắt buộc hoặc các trường có giá trị quá ngắn/không đủ chi tiết
- **0.4-0.6**: Thiếu 2 trường bắt buộc hoặc nhiều trường chưa đầy đủ chi tiết
- **0.6-0.8**: Thiếu 1 trường bắt buộc hoặc một số trường chưa đủ số lượng items (ví dụ: key_features < 3 items)
- **0.8-0.9**: Đầy đủ tất cả trường bắt buộc, đạt số lượng tối thiểu nhưng chưa đủ chi tiết/chất lượng
- **0.9-1.0**: Đầy đủ tất cả trường, đạt cả số lượng và chất lượng

### 2. Confidence Score (0.0-1.0)
Tính bằng công thức: **confidence = completeness_score × accuracy_factor**

**Accuracy Factor:**
- **1.0**: Brief chính xác 100% với thông tin từ cuộc trò chuyện, không có suy luận
- **0.9**: Brief có 1-2 phần suy luận hợp lý, không mâu thuẫn
- **0.8**: Brief có 3-4 phần suy luận hoặc 1 điểm mơ hồ nhỏ
- **0.7**: Brief có nhiều phần suy luận hoặc 2-3 điểm mơ hồ
- **0.6**: Brief có mâu thuẫn nhỏ hoặc suy luận không hợp lý ở 1-2 điểm
- **0.5 hoặc thấp hơn**: Brief có mâu thuẫn lớn hoặc suy luận sai ở nhiều điểm

### 3. Is Valid
- **true**: Nếu completeness_score >= 0.6 VÀ không có mâu thuẫn nghiêm trọng
- **false**: Nếu completeness_score < 0.6 HOẶC có mâu thuẫn nghiêm trọng

## Output yêu cầu:
- **is_valid**: true/false (true nếu brief đạt yêu cầu tối thiểu)
- **confidence_score**: 0.0-1.0 (độ tin cậy của brief)
- **completeness_score**: 0.0-1.0 (điểm đánh giá độ đầy đủ)
- **missing_fields**: Danh sách fields còn thiếu hoặc chưa đầy đủ (list of strings)
- **validation_message**: Giải thích ngắn gọn kết quả validation (string)"""

# Finalize prompt để tạo summary cuối cùng từ brief đã approve
FINALIZE_PROMPT = """Bạn là một Product Owner chuyên nghiệp đang tạo tóm tắt cuối cùng từ Product Brief đã được phê duyệt.

## Product Brief đã phê duyệt:
{brief}

## Nhiệm vụ:
Tạo một tóm tắt ngắn gọn, chuyên nghiệp và hấp dẫn từ Product Brief.

## Tóm tắt cần bao gồm:
1. **Tên sản phẩm**: Tên chính thức
2. **Mô tả ngắn gọn**: 1-2 câu highlight ý tưởng cốt lõi và giá trị chính
3. **Đối tượng mục tiêu**: Nhóm người dùng chính
4. **Tính năng nổi bật**: 3-5 tính năng quan trọng nhất
5. **Giá trị cốt lõi**: Lợi ích chính mang lại cho người dùng

## Hướng dẫn:
- Viết theo định dạng markdown
- Giữ tone professional nhưng friendly
- Ngắn gọn (200-400 từ)
- Tập trung vào điểm khác biệt và giá trị
- Dễ đọc, dễ hiểu cho cả người không chuyên

## Output yêu cầu:
- **product_name**: Tên sản phẩm (string)
- **executive_summary**: Tóm tắt điều hành 2-3 câu (string)
- **target_users**: Đối tượng mục tiêu chính (string, 1 câu ngắn)
- **top_features**: Danh sách 3-5 tính năng nổi bật (list of strings, mỗi item ~1 câu)
- **core_value**: Giá trị cốt lõi mang lại (string, 1-2 câu)
- **summary_markdown**: Tóm tắt đầy đủ theo format markdown (string, kết hợp tất cả thông tin trên)"""

# Edit mode prompt để áp dụng thay đổi từ user vào brief
EDIT_MODE_PROMPT = """Bạn là một Product Owner chuyên nghiệp đang cập nhật Product Brief theo yêu cầu của user.

## Brief hiện tại:
{brief}

## Thay đổi yêu cầu từ user:
{edit_changes}

## Nhiệm vụ:
Áp dụng các thay đổi yêu cầu vào Product Brief, đảm bảo:
1. Giữ nguyên cấu trúc và format của brief
2. Chỉ thay đổi các phần được yêu cầu, giữ nguyên các phần khác
3. Đảm bảo tính nhất quán và logic giữa các phần sau khi chỉnh sửa
4. Nếu thay đổi ảnh hưởng đến các phần khác, cập nhật cho nhất quán

## Cấu trúc Product Brief:
- **product_name**: Tên sản phẩm
- **description**: Mô tả chi tiết (50-1000 ký tự)
- **target_audience**: Danh sách 1-3 nhóm đối tượng mục tiêu
- **key_features**: Danh sách 3-5 tính năng chính
- **benefits**: Danh sách 2-5 lợi ích
- **competitors**: Danh sách 0-3 đối thủ cạnh tranh (tùy chọn)
- **completeness_note**: Ghi chú về thay đổi đã áp dụng

## Hướng dẫn:
- Phân tích yêu cầu thay đổi cẩn thận
- Áp dụng thay đổi một cách chính xác và đầy đủ
- Cập nhật completeness_note để ghi nhận thay đổi
- Giữ tone professional và nhất quán

## Output yêu cầu:
Trả về Product Brief đã được cập nhật với đầy đủ các trường:
- **product_name**: Tên sản phẩm (string)
- **description**: Mô tả chi tiết (string)
- **target_audience**: Danh sách đối tượng (list of strings)
- **key_features**: Danh sách tính năng (list of strings)
- **benefits**: Danh sách lợi ích (list of strings)
- **competitors**: Danh sách đối thủ (list of strings)
- **completeness_note**: Ghi chú về thay đổi (string)"""