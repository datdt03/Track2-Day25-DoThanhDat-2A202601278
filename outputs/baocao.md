# Bài Viết Thu Hoạch Lab 25: Tối Ưu Chi Phí Hạ Tầng GPU FinOps

Họ và tên sinh viên: Đỗ Thành Đạt  
Mã sinh viên: 2A202601278  
Bài lab: Day 25 - Track 2 (Infrastructure) — GPU FinOps Workshop  

---

## 1. Tổng Quan Hiệu Quả Tối Ưu Chi Phí

Qua quá trình phân tích và áp dụng các đòn bẩy FinOps cho hệ thống, tổng chi phí hạ tầng hàng tháng đã giảm từ 27,133 USD xuống còn 14,626 USD, đạt mức tiết kiệm 12,507 USD (tương đương cắt giảm 46% ngân sách).

Chi phí đơn vị phục vụ mô hình tính theo mỗi triệu token cũng giảm từ 6.488 USD xuống còn 1.126 USD (giảm 82.6%), cho thấy khả năng tối ưu vượt trội trên mỗi đơn vị công việc đầu ra.

---

## 2. Phân Tích Các Đòn Bẩy Tiết Kiệm Chính

Mức tiết kiệm chi phí đạt được nhờ sự đóng góp của bốn đòn bẩy cốt lõi:

* Đòn bẩy mua sắm cam kết và Spot: Đóng góp phần lớn hiệu quả tiết kiệm (hơn 10,000 USD mỗi tháng) bằng cách chuyển các ứng dụng chạy liên tục 24/7 sang gói mua cam kết 3 năm giảm giá 45%, đồng thời đưa các công việc huấn luyện mô hình có thể gián đoạn sang dạng Spot kết hợp cơ chế lưu trạng thái tự động.
* Đòn bẩy tối ưu phục vụ mô hình: Tiết kiệm hơn 1,200 USD mỗi tháng bằng việc điều phối câu hỏi đơn giản sang mô hình nhỏ hơn, sử dụng lại bộ nhớ đệm cho các văn bản lặp lại, và nhóm các yêu cầu không khẩn cấp để xử lý theo đợt.
* Đòn bẩy điều chỉnh quy mô GPU phù hợp: Tiết kiệm thêm 655 USD mỗi tháng khi hạ cấp các máy chủ GPU bị nghẽn bộ nhớ sang dòng card phù hợp hơn với khối lượng tính toán thực tế.
* Thu hồi GPU nhàn rỗi: Tiết kiệm 600 USD mỗi tháng nhờ tắt các máy chủ chạy không có tải.

---

## 3. Bản Chất Của Hiện Tượng GPU-Util Lie

Một điểm mới quan trọng em học được là sự sai lệch giữa chỉ số GPU Util trên phần mềm theo dõi và hiệu suất tính toán thực tế MFU.

Trong thực tế audit, dòng card GPU H100 hiển thị mức hoạt động 98.2% trên công cụ nvidia-smi nhưng chỉ số MFU thực tế chỉ đạt 19.4%. Lý do là chỉ số GPU Util chỉ phản ánh thời gian xung nhịp clock đang bật, chứ không đo hiệu suất tính toán thực sự. Đối với giai đoạn decode của mô hình ngôn ngữ lớn, GPU thường xuyên rơi vào trạng thái nghẽn băng thông bộ nhớ HBM, dẫn đến việc core phải đứng chờ dữ liệu nhưng hệ thống vẫn báo bận 98%. Việc chuyển sang quản lý theo chi phí trên triệu token giúp nhận diện và loại bỏ hoàn toàn sự lãng phí này.

---

## 4. Các Phát Hiện Mới Từ Phần Mở Rộng

* Chính sách mua sắm nâng cao: Điểm hòa vốn cho gói cam kết 3 năm (giảm 45%) là khi mức sử dụng đạt từ 55% trở lên, trong khi gói 1 năm (giảm 30%) đòi hỏi mức sử dụng tối thiểu 70%.
* Tối ưu hóa theo dung lượng bộ nhớ: Tính toán đơn giá chi phí trên dung lượng VRAM và băng thông giúp chọn chính xác dòng GPU thay thế phù hợp mà không làm suy giảm hiệu năng ứng dụng.
* Kiểm định tính kinh tế của bộ nhớ đệm: Việc lưu trữ đệm chỉ thực sự mang lại lợi nhuận khi tần suất đọc lại văn bản vượt qua ngưỡng chi phí lưu trữ ban đầu (trung bình cần từ 1.0 đến 1.28 lần đọc lại).
* Ngân sách cho các luồng xử lý suy luận: Luồng xử lý suy luận (Reasoning) tuy chỉ chiếm 8.4% số lượng yêu cầu nhưng tiêu tốn đến 16.5% chi phí và ngốn gần 94% tổng điện năng tiêu thụ do chuỗi suy nghĩ dài.
* Lập lịch hướng tới năng lượng xanh: Việc điều phối các bài toán huấn luyện mô hình sang trung tâm dữ liệu tại Na Uy (sử dụng nguồn thủy điện) giúp giảm đến 92.1% lượng phát thải carbon so với các vùng sử dụng nhiệt điện than.

---

## 5. Khuyến Nghị Quản Lý Hạ Tầng

* Áp dụng bắt buộc gói mua cam kết 3 năm cho toàn bộ ứng dụng chạy liên tục 24/7 và chuyển toàn bộ bài toán huấn luyện sang dòng Spot.
* Thiết lập cấu hình mặc định bộ nhớ đệm prompt và phân tầng mô hình trên cổng giao tiếp chung của hệ thống.
* Kiểm soát giới hạn độ dài chuỗi suy luận của các luồng suy luận và áp dụng chính sách phân bổ chi phí minh bạch cho từng nhóm phát triển.
