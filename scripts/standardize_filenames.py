import os
import sys
import re
from pathlib import Path
import yt_dlp

# Đảm bảo import được module core
sys.path.append(str(Path(__file__).resolve().parent.parent))

from core.config import OUTPUT_DIR
from core.logger import get_logger

logger = get_logger("StandardizeCLI")

def clean_title(title: str) -> str:
    cleaned = re.sub(r'[\\/*?:"<>|]', "", title)
    return cleaned.strip()

def run_standardize():
    logger.info("--- BẮT ĐẦU CHUẨN HÓA TÊN FILE ---")
    if not OUTPUT_DIR.exists():
        logger.error(f"Không tìm thấy thư mục output: {OUTPUT_DIR}")
        return

    files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".mp4")]
    
    std_pattern = re.compile(r'^\[\d{4}-\d{2}-\d{2}\]')
    id_pattern = re.compile(r'\[([a-zA-Z0-9_-]{11})\]')
    
    opts = {
        'extract_flat': False,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'tv', 'web']}}
    }
    
    count_success = 0
    count_skipped = 0

    with yt_dlp.YoutubeDL(opts) as ydl:
        for fname in files:
            if std_pattern.match(fname):
                count_skipped += 1
                continue
            
            match = id_pattern.search(fname)
            if not match:
                logger.warning(f"Bỏ qua (Không tìm thấy ID): {fname}")
                count_skipped += 1
                continue
            
            vid = match.group(1)
            logger.info(f"Đang xử lý chuẩn hóa cho: {fname}")
            try:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
                date = info.get("upload_date")
                title = info.get("title")
                if not date or not title:
                    logger.warning(f"Không lấy được metadata cho {vid}")
                    count_skipped += 1
                    continue
                
                fmt_date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
                c_title = clean_title(title)
                new_fname = f"[{fmt_date}] {c_title} [{vid}].mp4"
                
                old_path = os.path.join(OUTPUT_DIR, fname)
                new_path = os.path.join(OUTPUT_DIR, new_fname)
                
                if old_path != new_path:
                    os.rename(old_path, new_path)
                    logger.info(f"✅ Đã đổi tên: {fname} -> {new_fname}")
                    count_success += 1
                else:
                    count_skipped += 1
            except Exception as e:
                logger.error(f"❌ Lỗi đổi tên {fname}: {e}")
                count_skipped += 1

    logger.info("--- HOÀN TẤT CHUẨN HÓA ---")
    logger.info(f"Thành công: {count_success}")
    logger.info(f"Bỏ qua / Đã chuẩn: {count_skipped}")

if __name__ == "__main__":
    run_standardize()
