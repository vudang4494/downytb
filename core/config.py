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


def get_ydl_opts(custom_opts: dict = None) -> dict:
    """Trả về cấu hình yt-dlp lấy video chất lượng cao nhất cho một URL YouTube bất kỳ.

    Deno JS runtime chỉ được bật khi DENO_PATH được cấu hình và tồn tại, nên tool
    chạy được trên mọi máy kể cả khi chưa cài Deno.
    """
    base_opts = {
        'paths': {
            'home': str(OUTPUT_DIR),
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
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'ignoreerrors': True,
        'no_warnings': False,
        'quiet': False,
    }

    # Chỉ kích hoạt Deno khi đường dẫn hợp lệ (tránh lỗi trên máy chưa cài Deno)
    if DENO_PATH and Path(DENO_PATH).exists():
        base_opts['js_runtimes'] = {'deno': {'path': DENO_PATH}}
        base_opts['remote_components'] = ['ejs:github', 'ejs:npm']

    if custom_opts:
        base_opts.update(custom_opts)
    return base_opts
