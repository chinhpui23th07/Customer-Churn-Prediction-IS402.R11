# Modular Decomposition Patterns (Các Mẫu Phân Rã Mã Nguồn)

Cẩm nang hướng dẫn cách chia nhỏ một file lớn thành các file nhỏ dưới 400 dòng theo các kiến trúc chuẩn mực:

## 1. Mẫu Phân Rã Service / Controller (Backend)

### Trước khi phân rã: `UserService.ts` (600 dòng)
Chứa: Đăng ký, đăng nhập, gửi email OTP, upload avatar, hash password, query database.

### Sau khi phân rã:
1. `src/services/user/userAuth.ts`: Xác thực, tạo JWT, refresh token (~150 dòng).
2. `src/services/user/userProfile.ts`: Cập nhật thông tin cá nhân, avatar (~120 dòng).
3. `src/services/user/userNotification.ts`: Gửi OTP qua email/SMS (~90 dòng).
4. `src/repositories/userRepository.ts`: Các query DB CRUD (~180 dòng).
5. `src/services/user/index.ts`: Export facade hoặc tập trung các module con (~30 dòng).

## 2. Mẫu Phân Rã Component Giao Diện (Frontend)

### Trước khi phân rã: `DashboardPage.jsx` (550 dòng)
Chứa: Stats cards, Biểu đồ doanh thu, Bảng đơn hàng gần đây, Modal thêm sản phẩm, Fetch API.

### Sau khi phân rã:
1. `src/pages/DashboardPage.jsx`: Chỉ quản lý layout và import các component con (~80 dòng).
2. `src/components/dashboard/StatCardsGroup.jsx`: 4 thẻ chỉ số chính (~110 dòng).
3. `src/components/dashboard/RevenueChart.jsx`: Vẽ biểu đồ doanh thu (~140 dòng).
4. `src/components/dashboard/RecentOrdersTable.jsx`: Bảng danh sách đơn hàng (~160 dòng).
5. `src/components/dashboard/CreateProductModal.jsx`: Modal popup thêm mới (~190 dòng).
6. `src/hooks/useDashboardData.js`: Custom hook chứa toàn bộ logic gọi API và state (~120 dòng).

## 3. Lợi Ích Của Việc Giới Hạn < 400 Dòng
- **Đọc hiểu tức thì:** AI và con người có thể đọc hết toàn bộ file trong 1 lần lướt mà không bị quá tải.
- **Dễ viết Unit Test:** Mỗi file chỉ có 1-3 hàm nghiệp vụ, việc mock và viết test cực kỳ đơn giản.
- **Không bao giờ bị tràn Context Window:** Tiết kiệm tối đa chi phí token và hạn chế lỗi ngắt quãng khi AI sinh code.
