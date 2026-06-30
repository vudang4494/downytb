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
- **📺 Hỗ trợ link `.m3u8` (HLS) / DASH**: dán thẳng link stream → tự tải & ghép mọi segment thành 1 file MP4. Tải **nhiều fragment song song** (~5–8× nhanh hơn tải tuần tự).
- **📡 Tải nguyên Channel / Playlist**: dán URL channel/playlist → tự liệt kê & tải hàng loạt (song song có giới hạn), **sync tăng dần** (lần sau bỏ qua video đã có), có trần an toàn + giới hạn batch đồng thời.
- **🎛️ Tối giản, tập trung MP4**: chế độ `video` (MP4) hoặc `audio` (MP3), chọn độ phân giải (144p → 4K → `max`).
- **📥 API trả về file**: sau khi job xong, `GET /api/v1/jobs/{job_id}/file` tải thẳng file về (đúng MIME type).
- **🗂️ Mỗi job một thư mục riêng**: các lần tải không ghi đè lên nhau.
- **💎 Web Dashboard**: Dark Mode tối giản, theo dõi tiến trình real-time + nút tải file + hướng dẫn lấy link m3u8.
- **🧱 Cấu hình qua `.env`**: thư mục lưu, số fragment song song, Deno (tùy chọn), host/port.

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
| `POST` | `/api/v1/channel` | Tải nguyên channel/playlist (body bên dưới). `429` nếu quá nhiều batch |
| `GET`  | `/api/v1/channels` | Danh sách batch channel trong phiên |
| `GET`  | `/api/v1/channel/{batch_id}` | Tiến độ batch (`total`/`done`/`failed`/`skipped`) |
| `GET`  | `/api/v1/channel/{batch_id}/manifest` | Tiến độ kèm danh sách từng video |
| `GET`  | `/api/v1/channel/{batch_id}/videos/{video_id}/file` | Tải file 1 video trong batch |
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

## 📺 Tải từ link `.m3u8` (HLS)

Nhiều trang phát video bằng HLS — file `.m3u8` chứa danh sách các đoạn (segment). downytb tải toàn bộ segment rồi ghép thành 1 file MP4 hoàn chỉnh, **tải song song nhiều fragment** nên rất nhanh.

**Cách lấy link trên trang lạ:**
1. Mở trang có video → nhấn **F12** (DevTools) → tab **Network**.
2. Bấm Play, gõ `m3u8` vào ô lọc.
3. Chuột phải request `.m3u8` → **Copy → Copy link address**.
4. Dán vào dashboard (hoặc API) rồi tải như URL thường.

```bash
curl -s -X POST http://localhost:8000/api/v1/download \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/path/master.m3u8","mode":"video","quality":"max"}'
```

> 💡 Ưu tiên `master.m3u8` (playlist tổng) để chọn được chất lượng cao nhất. Link `.m3u8` thường có hạn dùng ngắn — copy xong nên tải ngay. Stream DRM (Widevine…) **không** tải được.
> Điều chỉnh số fragment song song qua biến `CONCURRENT_FRAGMENTS` trong `.env` (mặc định `5`).

---

## 📡 Tải nguyên Channel / Playlist

Dán URL channel (`/@tên`, `/channel/UC...`) hoặc playlist → hệ thống **liệt kê nhanh** danh sách video rồi tải hàng loạt vào thư mục riêng theo channel (`downloads/channels/<channel>/`). Lần chạy sau trên cùng channel sẽ **bỏ qua video đã có** (sync tăng dần).

```bash
# Tải 20 video mới nhất của một channel, dạng MP4 720p
curl -s -X POST http://localhost:8000/api/v1/channel \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/@MrBeast","mode":"video","quality":"720","limit":20}'
# -> {"batch_id":"ch_xxxxxxxxxxxx", ...}

# Theo dõi tiến độ
curl -s http://localhost:8000/api/v1/channel/ch_xxxxxxxxxxxx
# -> {"total":20,"done":12,"skipped":3,"failed":0,"status":"downloading", ...}

# Danh sách từng video + tải 1 video
curl -s http://localhost:8000/api/v1/channel/ch_xxxxxxxxxxxx/manifest
curl -OJ http://localhost:8000/api/v1/channel/ch_xxxxxxxxxxxx/videos/<video_id>/file
```

| Field (POST body) | Giá trị | Mặc định |
|-------|---------|----------|
| `url` | URL channel/playlist (bắt buộc) | — |
| `mode` | `video` \| `audio` | `video` |
| `quality` | `144`..`2160` \| `max` | `max` |
| `limit` | `1`..`MAX_CHANNEL_VIDEOS` — số video mới nhất | trần tối đa của server |

> ⚙️ Cấu hình qua `.env`: `CHANNEL_CONCURRENCY` (video song song), `MAX_CHANNEL_VIDEOS` (trần cứng mỗi batch), `MAX_CONCURRENT_CHANNELS` (số batch đồng thời, vượt → `429`). Tải nhiều dễ bị YouTube chặn bot — hệ thống tự nghỉ ngắn giữa các video.

---

## ⚙️ CLI (tùy chọn)

```bash
python scripts/download_sync.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

---

## 🛡️ Giấy phép
Phân phối dưới giấy phép **MIT License** — xem [LICENSE](LICENSE).
