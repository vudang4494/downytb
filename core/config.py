import os
from pathlib import Path
from dotenv import load_dotenv

# Thư mục gốc của dự án (nằm trên thư mục core 1 bậc)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load file .env nếu có
load_dotenv(BASE_DIR / ".env")

# Templates (Web Dashboard)
TEMPLATES_DIR = BASE_DIR / "templates"
DASHBOARD_TEMPLATE_FILE = TEMPLATES_DIR / "dashboard.html"

# Thư mục lưu video tải về (cấu hình qua biến môi trường OUTPUT_DIR, mặc định ./downloads).
# Dùng cho bất kỳ URL YouTube nào — không phụ thuộc dịch vụ lưu trữ cụ thể.
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", str(BASE_DIR / "downloads"))).expanduser()

# Thư mục tạm cho các phần tải dở (yt-dlp partial files)
TEMP_DIR = OUTPUT_DIR / ".tmp"

# Đảm bảo các thư mục tồn tại
for _d in (TEMPLATES_DIR, OUTPUT_DIR, TEMP_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# (Tùy chọn) Deno JS Runtime — giúp giải mã JS của YouTube ổn định hơn cho một số video.
# Để trống nếu máy không cài Deno; tính năng vẫn chạy bình thường mà không cần Deno.
DENO_PATH = os.getenv("DENO_PATH", "").strip()

# Số fragment tải SONG SONG cho stream phân mảnh (HLS .m3u8 / DASH).
# Tải nhiều segment cùng lúc giúp link m3u8 nhanh gấp nhiều lần so với tải tuần tự.
CONCURRENT_FRAGMENTS = max(1, int(os.getenv("CONCURRENT_FRAGMENTS", "5")))

# Số VIDEO tải SONG SONG trong một channel/playlist (khác với fragment song song của 1 video).
# Để thấp để tránh YouTube chặn bot khi tải hàng loạt.
CHANNEL_CONCURRENCY = max(1, int(os.getenv("CHANNEL_CONCURRENCY", "3")))

# Trần CỨNG số video mỗi batch — áp dụng KỂ CẢ khi client bỏ trống `limit`
# (tránh lỡ tay tải nguyên một channel khổng lồ làm đầy đĩa / cạn băng thông).
MAX_CHANNEL_VIDEOS = max(1, int(os.getenv("MAX_CHANNEL_VIDEOS", "500")))

# Số batch channel được chạy ĐỒNG THỜI (admission control -> trả 429 nếu vượt).
MAX_CONCURRENT_CHANNELS = max(1, int(os.getenv("MAX_CONCURRENT_CHANNELS", "2")))


def build_ydl_opts(
    mode: str = "video",
    quality: str = "max",
    dest_dir=None,
    custom_opts: dict = None,
) -> dict:
    """Dịch lựa chọn sang cấu hình yt-dlp. Tập trung MP4.

    - mode: 'video' = MP4 (video+audio gộp) | 'audio' = trích MP3
    - quality: '144'..'2160' giới hạn độ phân giải tối đa, hoặc 'max' = cao nhất

    Deno JS runtime chỉ bật khi DENO_PATH hợp lệ, nên chạy được cả khi chưa cài Deno.
    """
    home_dir = dest_dir if dest_dir is not None else OUTPUT_DIR
    opts = {
        'paths': {
            'home': str(home_dir),
            'temp': str(TEMP_DIR),
        },
        'outtmpl': {
            'default': '[%(upload_date>%Y-%m-%d)s] %(title)s [%(id)s].%(ext)s'
        },
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'tv', 'web']
            }
        },
        # Tối ưu cho link m3u8 (HLS) / DASH: tải nhiều fragment song song + retry segment lỗi.
        'concurrent_fragment_downloads': CONCURRENT_FRAGMENTS,
        'fragment_retries': 10,
        'retries': 10,
        'ignoreerrors': True,
        'no_warnings': False,
        'quiet': False,
    }

    if mode == "audio":
        # Trích audio sang MP3 bằng FFmpeg
        opts['format'] = 'bestaudio/best'
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '0',  # chất lượng tốt nhất
        }]
    else:
        # video: bestvideo+bestaudio, gộp sang MP4
        height_filter = "" if quality == "max" else f"[height<={int(quality)}]"
        opts['format'] = f'bestvideo{height_filter}+bestaudio/best{height_filter}/best'
        opts['merge_output_format'] = 'mp4'

    # Chỉ kích hoạt Deno khi đường dẫn hợp lệ (tránh lỗi trên máy chưa cài Deno)
    if DENO_PATH and Path(DENO_PATH).exists():
        opts['js_runtimes'] = {'deno': {'path': DENO_PATH}}
        opts['remote_components'] = ['ejs:github', 'ejs:npm']

    if custom_opts:
        opts.update(custom_opts)
    return opts


def get_ydl_opts(custom_opts: dict = None) -> dict:
    """Cấu hình mặc định: MP4 chất lượng cao nhất (tương thích ngược cho CLI)."""
    return build_ydl_opts(custom_opts=custom_opts)


def build_enumerate_opts(limit: int = None) -> dict:
    """Opts để LIỆT KÊ nhanh video trong channel/playlist mà KHÔNG tải.

    extract_flat='in_playlist' chỉ lấy id/tiêu đề/url của từng video nên chạy
    gần như tức thì, kể cả channel hàng nghìn video. Dùng cho bước "đếm trước".
    """
    opts = {
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'ignoreerrors': True,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {'player_client': ['android', 'ios', 'tv', 'web']}
        },
    }
    if limit and int(limit) > 0:
        opts['playlistend'] = int(limit)
    if DENO_PATH and Path(DENO_PATH).exists():
        opts['js_runtimes'] = {'deno': {'path': DENO_PATH}}
        opts['remote_components'] = ['ejs:github', 'ejs:npm']
    return opts
