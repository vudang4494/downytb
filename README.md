# 🎬 downytb — Media Downloader

<div align="center">
  <img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/yt--dlp-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="yt-dlp">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License">
</div>

<br>

**downytb** là một REST API + Web Dashboard gọn nhẹ theo phong cách [cobalt.tools](https://cobalt.tools): **dán một URL bất kỳ → chọn định dạng → nhận file**. Hỗ trợ YouTube, TikTok, Instagram, Twitter/X, Vimeo, SoundCloud... (1800+ site qua `yt-dlp`).

---

## 🔥 Tính năng chính (Key Features)

- **🌐 Đa nền tảng**: bất kỳ URL nào `yt-dlp` hỗ trợ, không chỉ YouTube.
- **🎛️ Tối giản, tập trung MP4**: chế độ `video` (MP4) hoặc `audio` (MP3), chọn độ phân giải (144p → 4K → `max`).
- **📥 API trả về file**: sau khi job xong, `GET /api/v1/jobs/{job_id}/file` tải thẳng file về (đúng MIME type).
- **🗂️ Mỗi job một thư mục riêng**: các lần tải không ghi đè lên nhau.
- **💎 Web Dashboard**: Dark Mode tối giản, theo dõi tiến trình real-time + nút tải file.
- **🧱 Cấu hình qua `.env`**: thư mục lưu, Deno (tùy chọn), host/port.

> ℹ️ **Lưu ý sử dụng**: Chỉ tải nội dung bạn có quyền tải, tuân thủ Điều khoản dịch vụ của nền tảng và luật bản quyền tại nơi bạn sống. Dự án không host/lưu trữ nội dung tải về lâu dài.

---

## 📂 Cấu trúc mã nguồn (Project Structure)

```
downytb/
├── api/
│   ├── main.py                 # REST endpoints + phục vụ Web Dashboard
│   ├── schemas.py              # Pydantic models (DownloadRequest có mode/quality/...)
│   └── services.py             # Logic tải ngầm (background) bằng yt-dlp
├── core/
│   ├── config.py               # build_ydl_opts(): dịch lựa chọn -> cấu hình yt-dlp
│   └── logger.py               # Logging tập trung
├── scripts/
│   └── download_sync.py        # CLI: tải 1 hoặc nhiều URL
├── templates/
│   └── dashboard.html          # Web Dashboard (Dark Mode)
├── downloads/                  # Thư mục output mặc định (gitignored)
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🛠️ Cài đặt & Sử dụng

### 1. Yêu cầu hệ thống
- **Python 3.10+**
- **FFmpeg** (gộp video+audio, trích xuất MP3).
- **Deno** *(tùy chọn)* — JS runtime giúp giải mã JS YouTube ổn định hơn cho một số video.

### 2. Cài đặt

```bash
git clone https://github.com/vudang4494/downytb.git
cd downytb
pip install -r requirements.txt
cp .env.example .env   # tùy chọn
```

### 3. Chạy API Server & Web Dashboard

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
* 🌐 **Web Dashboard**: `http://localhost:8000`
* 📖 **Swagger UI**: `http://localhost:8000/docs`

---

## 🔌 REST API

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/api/v1/download` | Tạo job tải. Body bên dưới. |
| `GET`  | `/api/v1/jobs` | Danh sách job trong phiên |
| `GET`  | `/api/v1/jobs/{job_id}` | Trạng thái job (`pending`/`downloading`/`completed`/`failed`) |
| `GET`  | `/api/v1/jobs/{job_id}/file` | Tải file kết quả (khi `completed`) |
| `GET`  | `/api/v1/system/status` | Trạng thái hệ thống & thư mục output |

**Body của `POST /api/v1/download`** (chỉ `url` bắt buộc):

| Field | Giá trị | Mặc định |
|-------|---------|----------|
| `url` | URL bất kỳ (bắt buộc) | — |
| `mode` | `video` (MP4) \| `audio` (MP3) | `video` |
| `quality` | `144`..`2160` \| `max` | `max` |

**Ví dụ bằng `curl`:**

```bash
# Tải video 1080p MP4
curl -s -X POST http://localhost:8000/api/v1/download \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","mode":"video","quality":"1080"}'

# Trích MP3
curl -s -X POST http://localhost:8000/api/v1/download \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","mode":"audio"}'

# Khi status = completed, tải file về (giữ nguyên tên gốc)
curl -OJ http://localhost:8000/api/v1/jobs/job_xxxxxxxxxxxx/file
```

---

## ⚙️ CLI (tùy chọn)

```bash
python scripts/download_sync.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

---

## 🛡️ Giấy phép
Phân phối dưới giấy phép **MIT License** — xem [LICENSE](LICENSE).
