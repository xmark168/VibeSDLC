## Epics

### Epic 1: Hiển thị và tìm kiếm sách
**Domain:** Sản phẩm
**Description:** Cung cấp chức năng xem danh mục, tìm kiếm và lọc sách giúp khách hàng dễ dàng lựa chọn sản phẩm phù hợp.

**User Stories (3):**

1.1. Với vai trò khách hàng, tôi muốn xem danh mục sách trên trang chủ để dễ dàng chọn sách phù hợp nhu cầu
   **Description:** Khách hàng có thể xem danh sách các sách nổi bật hoặc đầy đủ trên trang chủ website.
   **Acceptance Criteria:**
   - Given tôi đang truy cập trang chủ, When trang chủ tải xong, Then tôi thấy danh mục sách được hiển thị rõ ràng.
   - Given tôi xem mục danh mục sách, When tôi nhấn vào một thể loại hoặc danh mục, Then hệ thống chỉ hiển thị sách thuộc mục đó.

1.2. Với vai trò khách hàng, tôi muốn tìm kiếm sách theo tên, tác giả, thể loại để dễ dàng lọc ra sản phẩm mong muốn
   **Description:** Có khung tìm kiếm cho phép lọc sách theo nhiều thông tin khác nhau.
   **Acceptance Criteria:**
   - Given tôi nhập từ khoá vào ô tìm kiếm, When tôi nhấn nút tìm, Then hệ thống hiển thị kết quả đúng với nội dung tôi tìm.
   - Given tôi sử dụng bộ lọc nâng cao, When tôi chọn các tiêu chí (giá, nhà xuất bản...), Then hệ thống lọc và hiển thị đúng sách thỏa mãn.    

1.3. Với vai trò khách hàng, tôi muốn xem chi tiết sách (mô tả, ảnh, giá, đánh giá) để quyết định mua
   **Description:** Mỗi sản phẩm sách phải có trang chi tiết hiển thị thông tin đầy đủ, minh bạch cho khách hàng tham khảo.
   **Acceptance Criteria:**
   - Given tôi đang xem danh mục hoặc kết quả tìm kiếm, When tôi nhấn vào ảnh hoặc tên sách, Then hệ thống mở trang chi tiết chứa mô tả, ảnh, giá, nhận xét.

### Epic 2: Quản lý giỏ hàng
**Domain:** Giỏ hàng
**Description:** Hỗ trợ khách hàng thêm, kiểm tra, chỉnh sửa sách muốn mua trong giỏ hàng.

**User Stories (2):**

2.1. Với vai trò khách hàng, tôi muốn thêm sách vào giỏ hàng để chuẩn bị mua sắm
   **Description:** Cho phép thêm từng cuốn sách vào giỏ hàng, xác nhận thành công, hiển thị số lượng sách đã chọn.
   **Acceptance Criteria:**
   - Given tôi đang xem chi tiết sách, When tôi nhấn 'Thêm vào giỏ hàng', Then hệ thống thêm vào giỏ và xác nhận thành công.
   - Given tôi đã thêm nhiều sách vào giỏ, When tôi kiểm tra giỏ hàng, Then tôi thấy đúng danh sách sách đã chọn.

2.2. Với vai trò khách hàng, tôi muốn chỉnh sửa giỏ hàng (thay đổi số lượng, xoá sách) để tùy chỉnh cho đơn hàng
   **Description:** Khách hàng có thể thay đổi số lượng từng cuốn sách, hoặc loại bỏ khỏi giỏ hàng trước khi đặt hàng.
   **Acceptance Criteria:**
   - Given tôi vào trang giỏ hàng, When tôi thay đổi số lượng hoặc xoá sách, Then hệ thống cập nhật lại tổng số lượng và giá trị đơn hàng.      
   - Given tôi vừa chỉnh sửa giỏ hàng, When tôi kiểm tra lại, Then tôi thấy thông tin cập nhật đúng.

### Epic 3: Đặt hàng và thanh toán trực tuyến
**Domain:** Đơn hàng & Thanh toán
**Description:** Hỗ trợ khách hàng đặt mua sách, nhập thông tin giao nhận và thanh toán trực tuyến qua nhiều phương thức, đặc biệt là quét mã QR.

**User Stories (3):**

3.1. Với vai trò khách hàng, tôi muốn nhập thông tin giao nhận để đơn hàng được giao đúng địa chỉ
   **Description:** Khách hàng điền tên, địa chỉ, số điện thoại nhận hàng khi đặt đơn, đảm bảo việc giao nhận chính xác.
   **Acceptance Criteria:**
   - Given tôi đang đặt hàng, When hệ thống yêu cầu nhập thông tin giao nhận, Then tôi có thể nhập đầy đủ thông tin cần thiết và hệ thống xác nhận.
   - Given các trường thông tin đã nhập, When tôi gửi yêu cầu, Then hệ thống kiểm tra hợp lệ trước khi tiếp tục thanh toán.

3.2. Với vai trò khách hàng, tôi muốn chọn phương thức thanh toán phù hợp, đặc biệt là quét mã QR ngân hàng
   **Description:** Hỗ trợ nhiều phương thức thanh toán online, trong đó có quét mã QR tài khoản ngân hàng.
   **Acceptance Criteria:**
   - Given tôi ở bước thanh toán, When tôi chọn phương thức 'Quét mã QR ngân hàng', Then hệ thống hiển thị đúng mã QR và hướng dẫn chuyển khoản.
   - Given tôi chọn phương thức khác (chuyển khoản, ví điện tử...), When tôi xác nhận, Then hệ thống hiển thị hướng dẫn tương ứng.

3.3. Với vai trò khách hàng, tôi muốn xác nhận hoàn tất thanh toán và nhận thông tin đơn hàng
   **Description:** Sau khi chuyển khoản/quét QR thành công, khách hàng xác nhận để hệ thống ghi nhận trạng thái đơn và hiển thị mã đơn hàng.   
   **Acceptance Criteria:**
   - Given tôi đã thực hiện giao dịch thanh toán, When tôi nhấn xác nhận, Then hệ thống kiểm tra và cập nhật trạng thái đơn, gửi thông tin đơn hàng.
   - Given thanh toán thành công, When hệ thống hoàn tất, Then tôi nhận được mã đơn và trạng thái mua hàng.

### Epic 4: Theo dõi trạng thái đơn hàng
**Domain:** Đơn hàng
**Description:** Cho phép khách hàng tra cứu, nhận thông báo về trạng thái xử lý, giao vận của đơn hàng.

**User Stories (2):**

4.1. Với vai trò khách hàng, tôi muốn tra cứu trạng thái đơn hàng đã thanh toán để biết tiến độ giao nhận
   **Description:** Khách hàng có thể tra cứu qua tài khoản hoặc mã đơn hàng để xem trạng thái (xử lý, đóng gói, đang giao, đã giao).
   **Acceptance Criteria:**
   - Given tôi đã đặt hàng, When tôi đăng nhập hoặc nhập mã đơn trên hệ thống, Then tôi thấy danh sách và trạng thái đơn hàng.
   - Given tôi chọn một đơn hàng cụ thể, When xem chi tiết, Then thấy thông tin đầy đủ về trạng thái xử lý.

4.2. Với vai trò khách hàng, tôi muốn nhận thông báo khi trạng thái đơn hàng thay đổi (qua hệ thống/email/sms nếu có)
   **Description:** Hệ thống gửi thông báo hoặc cập nhật cho khách hàng khi đơn thay đổi trạng thái nhằm tăng trải nghiệm.
   **Acceptance Criteria:**
   - Given tôi vừa đặt hàng, When trạng thái đơn chuyển từ xử lý sang đóng gói/giao hàng/thành công, Then tôi nhận được thông báo trên website (và email/sms nếu cấu hình).

### Epic 5: Quản lý kho và tồn kho
**Domain:** Kho
**Description:** Trang quản trị hỗ trợ nhân viên, quản lý kho kiểm tra tồn kho, cập nhật nhập/xuất sách và cảnh báo số lượng thấp.

**User Stories (3):**

5.1. Với vai trò nhân viên kho, tôi muốn kiểm tra tồn kho của từng đầu sách để đảm bảo kế hoạch vận hành
   **Description:** Nhân viên kho dùng hệ thống để kiểm tra số lượng tồn của từng loại sách và tránh hết hàng.
   **Acceptance Criteria:**
   - Given tôi đăng nhập trang quản trị kho, When tôi truy cập danh sách kho, Then hệ thống hiển thị đúng tồn kho từng đầu sách.
   - Given số liệu tồn kho hiển thị, When có thay đổi nhập/xuất, Then cập nhật số lượng ngay lập tức.

5.2. Với vai trò nhân viên kho, tôi muốn bổ sung hoặc giảm số lượng sách trong kho khi nhập mới hoặc xuất đơn hàng
   **Description:** Cập nhật số lượng sách khi nhập thêm hàng về kho hoặc xử lý xuất khỏi kho cho đơn hàng.
   **Acceptance Criteria:**
   - Given tôi đăng nhập quản trị kho, When tôi nhập số lượng mới hoặc giảm khi xuất hàng, Then hệ thống cập nhật tồn kho.
   - Given một đơn hàng hoàn tất, When hàng xuất kho, Then số lượng tồn kho giảm đúng số lượng sản phẩm bán ra.

5.3. Với vai trò quản lý kho, tôi muốn nhận cảnh báo khi số lượng sách tồn kho thấp để lên kế hoạch nhập bổ sung
   **Description:** Hệ thống thông báo cho quản lý khi số lượng sách thấp hơn ngưỡng quy định.
   **Acceptance Criteria:**
   - Given lượng tồn kho giảm dưới ngưỡng, When tôi đăng nhập quản trị kho, Then tôi nhận được cảnh báo và có thể lên kế hoạch nhập bổ sung.    
   - Given có cảnh báo tồn kho thấp, When tôi xem báo cáo tồn kho, Then hệ thống đề xuất loại sách cần nhập thêm.

### Epic 6: Quản lý đơn hàng (Admin)
**Domain:** Đơn hàng
**Description:** Trang quản trị giúp kiểm tra, xác nhận và cập nhật trạng thái đơn hàng, truy xuất lịch sử mua bán.

**User Stories (3):**

6.1. Với vai trò nhân viên quản lý đơn hàng, tôi muốn kiểm tra danh sách các đơn mới đặt và xử lý theo quy trình
   **Description:** Nhân viên vào trang quản trị để xem danh sách đơn hàng mới và chuyển sang trạng thái xử lý.
   **Acceptance Criteria:**
   - Given tôi đăng nhập hệ thống quản trị, When tôi truy cập mục quản lý đơn hàng, Then tôi thấy danh sách đơn mới với thông tin khách hàng, sản phẩm, trạng thái.
   - Given một đơn hàng vừa đến, When tôi xử lý đơn, Then hệ thống cho phép chuyển trạng thái sang đang xử lý.

6.2. Với vai trò quản trị viên, tôi muốn xác nhận thanh toán và thay đổi trạng thái đơn hàng (xử lý, đóng gói, giao, hoàn thành)
   **Description:** Xác nhận giao dịch thanh toán, cập nhật từng trạng thái đơn hàng trong chuỗi xử lý.
   **Acceptance Criteria:**
   - Given tôi đăng nhập quản trị đơn hàng, When kiểm tra giao dịch thanh toán hợp lệ, Then có thể cập nhật trạng thái đơn hàng sang các trạng thái tiếp theo.
   - Given trạng thái vừa chuyển, When khách hoặc hệ thống kiểm tra, Then trạng thái đơn thể hiện đúng tiến trình xử lý.

6.3. Với vai trò nhân viên/quản trị viên, tôi muốn truy xuất lịch sử mua bán theo từng đơn/khách hàng để phân tích
   **Description:** Xem lại các đơn hàng đã hoàn thành, đối chiếu kế hoạch kinh doanh, phân tích dữ liệu khách hàng.
   **Acceptance Criteria:**
   - Given tôi đăng nhập trang quản trị đơn hàng, When chọn xem lịch sử mua bán, Then hệ thống hiển thị chi tiết các đơn hàng đã hoàn thành theo từng khách.
   - Given tôi xem lịch sử một khách cụ thể, When tôi truy xuất, Then thấy đầy đủ các đơn hàng theo đúng tài khoản/khách hàng.

### Epic 7: Quản lý sản phẩm/sách
**Domain:** Sản phẩm
**Description:** Trang quản trị cho phép thêm mới, chỉnh sửa, ẩn/xoá sách, đảm bảo thông tin chính xác và cập nhật thường xuyên.

**User Stories (3):**

7.1. Với vai trò quản trị viên, tôi muốn thêm sách mới với đầy đủ thông tin vào hệ thống để mở rộng danh mục sản phẩm
   **Description:** Thêm sách mới với đầy đủ tiêu đề, tác giả, ảnh bìa, mô tả, giá...
   **Acceptance Criteria:**
   - Given tôi đăng nhập quản trị sản phẩm, When tôi nhập thông tin sách đầy đủ và lưu, Then sách mới hiển thị trên website đúng thông tin đã nhập.
   - Given sách vừa thêm, When khách hàng tìm kiếm hoặc xem danh mục, Then sách xuất hiện đúng vị trí, thể loại.

7.2. Với vai trò quản trị viên, tôi muốn chỉnh sửa thông tin sách khi phát hiện sai sót hoặc cập nhật giá/miêu tả mới
   **Description:** Cập nhật lại thông tin sách đang hiển thị trên hệ thống.
   **Acceptance Criteria:**
   - Given tôi đang ở trang quản trị sách, When tôi chọn chỉnh sửa một sách, Then hệ thống cho phép cập nhật thông tin và lưu thay đổi.
   - Given thông tin đã chỉnh sửa, When khách hàng xem chi tiết hoặc tìm kiếm sách, Then thấy nội dung đúng đã cập nhật mới.

7.3. Với vai trò quản trị viên, tôi muốn ẩn hoặc xoá sách không còn bán trên hệ thống để tối ưu quản lý sản phẩm
   **Description:** Quản trị viên có thể ẩn sách khỏi website hoặc xoá sản phẩm khỏi hệ thống khi không bán nữa.
   **Acceptance Criteria:**
   - Given tôi ở trang quản trị, When tôi chọn xoá/ẩn sách, Then sách biến mất khỏi catalog website và không hiện khi khách xem/tìm kiếm.       
   - Given tôi vừa ẩn/xoá sách, When kiểm tra lại trên quản lý kho, Then thông tin sản phẩm cũng được cập nhật đúng trạng thái.

### Epic 8: Đánh giá và nhận xét sách
**Domain:** Đánh giá
**Description:** Khách hàng có thể nhận xét, cho điểm, đính kèm hình ảnh (nếu có) cho sách đã mua, tăng uy tín và hỗ trợ cộng đồng người mua.   

**User Stories (2):**

8.1. Với vai trò khách hàng, tôi muốn đánh giá và viết nhận xét cho sách đã mua để chia sẻ trải nghiệm với người khác
   **Description:** Sau khi hoàn thành đơn hàng, khách chọn mục nhận xét và viết đánh giá về sách (số sao, nội dung, hình ảnh kèm theo nếu có). 
   **Acceptance Criteria:**
   - Given tôi đã mua và nhận sách, When tôi vào lịch sử đơn hàng hoặc chi tiết sách, Then tôi có thể chọn mục đánh giá/nhận xét.
   - Given tôi đã viết nhận xét, When gửi lên hệ thống, Then đánh giá lập tức hiển thị trên trang chi tiết sách cho các khách khác xem.

8.2. Với vai trò khách hàng, tôi muốn đính kèm hình ảnh khi nhận xét sản phẩm để tăng minh chứng cho đánh giá
   **Description:** Khách hàng đính kèm hình ảnh thực tế nhận được khi viết nhận xét, giúp phản hồi minh bạch hơn.
   **Acceptance Criteria:**
   - Given tôi chọn đánh giá sách, When tôi tải lên hình ảnh kèm nội dung nhận xét, Then hệ thống hiển thị cả ảnh lẫn đánh giá trên chi tiết sản phẩm.
   - Given hình ảnh được thêm vào nhận xét, When khách khác truy cập, Then họ có thể xem hình ảnh và nội dung đánh giá.

### Epic 9: Quản lý tài khoản nhân sự
**Domain:** Tài khoản & Quyền hạn
**Description:** Quản trị viên quản lý, tạo mới, phân quyền tài khoản nhân viên sử dụng hệ thống.

**User Stories (2):**

9.1. Với vai trò quản trị viên, tôi muốn tạo tài khoản mới cho nhân viên sử dụng trang quản trị (phân quyền kho, đơn hàng, sản phẩm...)
   **Description:** Quản trị viên có thể cấp tài khoản cho nhân viên với chức năng chỉ định phù hợp.
   **Acceptance Criteria:**
   - Given tôi đăng nhập quản trị hệ thống, When tôi truy cập mục quản lý tài khoản và tạo mới, Then tài khoản nhân viên được thiết lập và phân quyền đúng.
   - Given tài khoản nhân viên vừa tạo, When nhân viên đăng nhập, Then hệ thống chỉ cho phép thao tác đúng với quyền hạn đã phân.
   - Given một tài khoản mới, When phân quyền, Then tôi có thể chọn chức năng quản lý kho, sản phẩm, đơn hàng tuỳ theo vị trí.

9.2. Với vai trò quản trị viên, tôi muốn sửa/xoá/khoá tài khoản nhân viên khi cần thay đổi nhân sự
   **Description:** Quản trị viên chủ động cập nhật thông tin tài khoản nhân sự, khoá hoặc xoá khi có thay đổi.
   **Acceptance Criteria:**
   - Given tôi vào trang quản lý tài khoản, When tôi chọn sửa/xoá/khoá một tài khoản, Then hệ thống cập nhật đúng trạng thái cho tài khoản nhân viên đó.
   - Given tài khoản đã bị khoá/xoá, When nhân viên đăng nhập, Then hệ thống không cho phép truy cập hệ thống nữa.
