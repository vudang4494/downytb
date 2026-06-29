# 🎬 YouTube HD Downloader

<div align="center">
  <img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/yt--dlp-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="yt-dlp">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License">
</div>

<br>

**YouTube HD Downloader** là một REST API + Web Dashboard gọn nhẹ: bạn nhập **một URL YouTube bất kỳ**, hệ thống sẽ tải video ở **chất lượng cao nhất** (tự động gộp luồng video + audio sang MP4) và cho phép tải file kết quả về qua API.

---

## 🔥 Tính năng chính (Key Features)

- **🎯 Chất lượng cao nhất tự động**: Chọn `bestvideo+bestaudio` rồi gộp sang MP4 bằng FFmpeg — không cần chỉ định định dạng thủ công.
- **🌐 Hoạt động với mọi URL YouTube**: Video đơn, link `youtu.be`, hay link trong playlist đều dùng được — không gắn với kênh hay thư mục cụ thể nào.
- **📥 API trả về file**: Sau khi job hoàn tất, gọi `GET /api/v1/jobs/{job_id}/file` để tải thẳng file MP4 về.
- **💎 Web Dashboard**: Giao diện Dark Mode theo dõi tiến trình tải real-time (tự động cập nhật mỗi 3 giây).
- **🧱 Cấu trúc rõ ràng & cấu hình qua `.env`**: Tách lớp API / Core / Scripts; mọi cấu hình (thư mục lưu, Deno, host/port) đều qua biến môi trường.
- **🛠️ Bộ script CLI kèm theo**: tải hàng loạt, kiểm tra & nâng cấp lên 2K/4K, chuẩn hóa tên file.

> ℹ️ **Lưu ý sử dụng**: Chỉ tải nội dung bạn có quyền tải, tuân thủ Điều khoản dịch vụ của YouTube và luật bản quyền tại nơi bạn sống.

---

## 📂 Cấu trúc mã nguồn (Project Structure)

```
downytb/
├── api/                        # Khối API Server (FastAPI)
│   ├── main.py                 # REST endpoints + phục vụ Web Dashboard
│   ├── schemas.py              # Pydantic models (DownloadRequest, JobStatusResponse...)
│   └── services.py             # Logic tải ngầm (background) bằng yt-dlp
├── core/                       # Khối cấu hình & tiện ích chung
│   ├── config.py               # Cấu hình tập trung (OUTPUT_DIR, yt-dlp opts, .env)
│   └── logger.py               # Logging tập trung
├── scripts/                    # Công cụ CLI
│   ├── download_sync.py        # Tải 1 hoặc nhiều URL từ dòng lệnh
│   ├── verify_quality.py       # Kiểm tra 2K/4K & tải lại bản nét hơn nếu có
│   └── standardize_filenames.py# Chuẩn hóa tên file: [YYYY-MM-DD] Tiêu đề [ID].mp4
├── templates/
│   └── dashboard.html          # Web Dashboard (Dark Mode)
├── data/                       # Dữ liệu cục bộ (gitignored): archive, cache chất lượng
├── downloads/                  # Thư mục output mặc định (gitignored)
├── .env.example                # Mẫu cấu hình môi trường
├── requirements.txt            # Dependencies
└── README.md
```

---

## 🛠️ Cài đặt & Sử dụng (Installation & Usage)

### 1. Yêu cầu hệ thống (Prerequisites)
- **Python 3.10+**
- **FFmpeg & FFprobe** (để gộp video/audio và kiểm tra độ phân giải).
- **Deno** *(tùy chọn)* — JS runtime giúp giải mã JS YouTube ổn định hơn cho một số video.

### 2. Cài đặt & cấu hình

```bash
git clone https://github.com/vudang4494/downytb.git
cd downytb
pip install -r requirements.txt

# Tạo file cấu hình từ mẫu (tùy chọn — đã có giá trị mặc định hợp lý)
cp .env.example .env
```
*(Chỉnh `.env` để đổi `OUTPUT_DIR`, cấu hình `DENO_PATH`, hoặc host/port nếu cần.)*

### 3. Chạy API Server & Web Dashboard

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
* 🌐 **Web Dashboard**: `http://localhost:8000`
* 📖 **Tài liệu API (Swagger UI)**: `http://localhost:8000/docs`

---

## 🔌 REST API

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/api/v1/download` | Tạo job tải từ một URL YouTube. Body: `{"url": "..."}` |
| `GET`  | `/api/v1/jobs` | Danh sách toàn bộ job trong phiên |
| `GET`  | `/api/v1/jobs/{job_id}` | Trạng thái một job (`pending`/`downloading`/`completed`/`failed`) |
| `GET`  | `/api/v1/jobs/{job_id}/file` | Tải file MP4 kết quả (khi job `completed`) |
| `GET`  | `/api/v1/system/status` | Trạng thái hệ thống & thư mục output |

**Ví dụ luồng tải bằng `curl`:**

```bash
# 1) Tạo job
curl -s -X POST http://localhost:8000/api/v1/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
# -> {"job_id":"job_xxxxxxxxxxxx", ...}

# 2) Kiểm tra trạng thái
curl -s http://localhost:8000/api/v1/jobs/job_xxxxxxxxxxxx

# 3) Khi status = completed, tải file về
curl -OJ http://localhost:8000/api/v1/jobs/job_xxxxxxxxxxxx/file
```

---

## ⚙️ Công cụ CLI (tùy chọn)

```bash
# Tải 1 hoặc nhiều URL trực tiếp
python scripts/download_sync.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Kiểm tra & nâng cấp lên 2K/4K cho các file đã tải
python scripts/verify_quality.py

# Chuẩn hóa tên file về dạng [YYYY-MM-DD] Tiêu đề [ID].mp4
python scripts/standardize_filenames.py
```

---

## 🛡️ Giấy phép (License)
Phân phối dưới giấy phép **MIT License** — xem file [LICENSE](LICENSE).
