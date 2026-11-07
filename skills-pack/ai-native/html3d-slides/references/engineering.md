# Kỹ thuật Dựng Runtime và Đồ họa 3D

## 1. Một nguồn dữ liệu và State đồng nhất

Toàn bộ nội dung chữ, ghi chú người nói, thông số mô hình và dữ liệu kiểm tra của bộ slide nên được dẫn xuất từ một cấu trúc dữ liệu trung tâm (JSON hoặc module cấu hình), tránh việc viết cứng (hardcode) cùng một con số ở cả HTML lẫn script 3D.

Cấu trúc state chuẩn:

```js
{
  slideId,       // Trang hiện tại
  buildId,       // Bước mở nội dung (build step) trên trang
  caseId,        // Kịch bản / ví dụ đang chọn
  filterId,      // Bộ lọc dữ liệu đang bật
  motionState,   // 'running' | 'paused' | 'reduced'
  time           // Thời gian tích lũy cho hiệu ứng ambient / nội suy
}
```

- **Quy tắc bất biến:** Chỉ `slideId`, `buildId`, `caseId`, `filterId` mới quyết định nội dung và số liệu nào được hiển thị. Biến `time` chỉ phục vụ chuyển động mượt (lerp/slerp) và hiệu ứng nền, tuyệt đối không dùng `if (time > X)` để tự động mở kết luận.
- **Hàm hành động chung:** Cả sự kiện click/phím trên nút DOM lẫn sự kiện chọn vật thể 3D (Raycaster) đều gọi chung `dispatchAction(type, payload)` để cập nhật `state` rồi render lại cả hai lớp.

## 2. Quản lý Renderer và Chống lỗi hiển thị 3D

- **Dùng chung một Renderer:** Với các bộ slide tiêu chuẩn, khởi tạo một `WebGLRenderer` (hoặc `WebGPURenderer` kèm fallback sang WebGL2) và gắn canvas vào vùng chứa của trang đang hoạt động để tránh vượt giới hạn số lượng WebGL context của trình duyệt.
- **Hệ trục cục bộ (Local Pivot):** Nhóm các bộ phận có chuyển động liên kết vào cùng một `THREE.Group` với tâm xoay chuẩn để khi biến hình hoặc mở nắp không bị lệch khớp nối.
- **Đồng bộ ẩn/hiện bóng đổ (Shadow Gating):** Khi ẩn một nhóm vật thể theo `caseId` hoặc `buildId`, phải cập nhật đồng thời `visible` và tắt `castShadow` của toàn bộ mesh con để không để lại "bóng ma" trên mặt sàn.

## 3. Độ phân giải Retina và Nhãn chữ trong 3D

Khung thiết kế chuẩn (ví dụ `1600 x 900`) được co giãn theo màn hình thực tế. Để hình ảnh 3D không bị mờ trên màn hình Retina/4K:

```js
const scale = host.getBoundingClientRect().width / (host.clientWidth || 1);
const pixelRatio = Math.min(pixelRatioCap, Math.max(1, window.devicePixelRatio * scale));
renderer.setPixelRatio(pixelRatio);
renderer.setSize(host.clientWidth, host.clientHeight, false);
```

- **Texture chữ trên mô hình 3D:** Nếu cần vẽ nhãn ngắn lên bề mặt 3D bằng `<canvas>` 2D, phải gọi `await document.fonts.load('600 48px "FontName"')` trước khi `fillText` để tránh lỗi vẽ bằng phông hệ thống mặc định. Giữ tỷ lệ khung hình của canvas 2D khớp với tỷ lệ mặt phẳng 3D để chữ không bị kéo giãn hoặc bẹt.

## 4. Hỗ trợ In ấn / Xuất PDF và Chế độ Dự phòng (Fallback)

- **Chế độ dự phòng tĩnh:** Khi thiết bị không hỗ trợ WebGL/WebGPU hoặc bật chế độ tiết kiệm tài nguyên, hiển thị hình chụp tĩnh (baked still PNG/WebP) tương ứng đúng với từng cặp `(slideId, buildId, caseId)`.
- **Sự kiện `beforeprint` / `afterprint`:** Trước khi in hoặc xuất PDF, lưu lại `state` hiện tại, kết xuất từng trang ở trạng thái hoàn chỉnh (full build), ẩn các vùng điều khiển động chỉ dành cho màn hình, và khôi phục nguyên vẹn `state` sau khi in xong.
