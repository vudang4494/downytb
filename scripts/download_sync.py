import sys
from pathlib import Path
import yt_dlp

# Đảm bảo import được module core
sys.path.append(str(Path(__file__).resolve().parent.parent))

from core.config import get_ydl_opts
from core.logger import get_logger

logger = get_logger("DownloadCLI")

def run_download(urls: list):
    logger.info(f"--- BẮT ĐẦU TẢI {len(urls)} URL (chất lượng cao nhất) ---")
    ydl_opts = get_ydl_opts()

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for url in urls:
            logger.info(f"Đang tải: {url}")
            try:
                retcode = ydl.download([url])
                if retcode != 0:
                    logger.warning(f"⚠️ Tải xong nhưng có lỗi (một số video đã bị bỏ qua): {url}")
                else:
                    logger.info(f"✅ Tải thành công: {url}")
            except Exception as e:
                logger.error(f"❌ Lỗi tải {url}: {e}")

    logger.info("--- HOÀN TẤT ---")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Cách dùng: python scripts/download_sync.py <YOUTUBE_URL> [<YOUTUBE_URL> ...]")
        print("Ví dụ:     python scripts/download_sync.py \"https://www.youtube.com/watch?v=dQw4w9WgXcQ\"")
        sys.exit(1)
    run_download(sys.argv[1:])
