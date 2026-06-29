import os
import sys
import re
import subprocess
from pathlib import Path
import yt_dlp

# Đảm bảo import được module core
sys.path.append(str(Path(__file__).resolve().parent.parent))

from core.config import get_ydl_opts, OUTPUT_DIR, ARCHIVE_FILE, VERIFIED_MAX_QUALITY_FILE
from core.logger import get_logger

logger = get_logger("VerifyQualityCLI")

def get_video_resolution(file_path: str):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", file_path
    ]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode().strip()
        if "x" in output:
            w, h = map(int, output.split("x"))
            return w, h
    except Exception as e:
        logger.error(f"Lỗi ffprobe cho {file_path}: {e}")
    return 0, 0

def check_max_quality_youtube(video_id: str) -> int:
    opts = {
        'extract_flat': False,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'tv', 'web']}}
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            formats = info.get("formats", [])
            max_h = 0
            for f in formats:
                h = f.get("height")
                if h and h > max_h:
                    max_h = h
            return max_h
    except Exception as e:
        logger.error(f"Lỗi truy vấn YT cho ID {video_id}: {e}")
        return 0

def run_verify():
    logger.info("--- BẮT ĐẦU KIỂM TRA CHẤT LƯỢNG 2K/4K ---")
    if not OUTPUT_DIR.exists():
        logger.error(f"Không tìm thấy thư mục output: {OUTPUT_DIR}")
        return

    files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".mp4")]
    
    verified_max = set()
    if VERIFIED_MAX_QUALITY_FILE.exists():
        with open(VERIFIED_MAX_QUALITY_FILE, "r", encoding="utf-8") as f:
            verified_max = set(f.read().splitlines())

    id_pattern = re.compile(r'\[([a-zA-Z0-9_-]{11})\]')
    
    count_2k = 0
    count_max_author = 0
    count_redownloaded = 0
    count_errors = 0

    for fname in files:
        fpath = os.path.join(OUTPUT_DIR, fname)
        match = id_pattern.search(fname)
        if not match:
            logger.warning(f"Bỏ qua (Không tìm thấy ID): {fname}")
            continue
        vid = match.group(1)
        
        w, h = get_video_resolution(fpath)
        if w >= 2560 or h >= 1440:
            count_2k += 1
            continue
            
        if vid in verified_max:
            count_max_author += 1
            continue
            
        logger.info(f"[DƯỚI 2K] {fname} đang là {w}x{h}. Đang kiểm tra YouTube...")
        max_yt_h = check_max_quality_youtube(vid)
        
        if max_yt_h <= h:
            logger.info(f"👉 [CHẤT LƯỢNG TỐI ĐA CỦA TÁC GIẢ] File hiện tại ({h}p) đã là bản nét nhất.")
            with open(VERIFIED_MAX_QUALITY_FILE, "a", encoding="utf-8") as vf:
                vf.write(f"{vid}\n")
            verified_max.add(vid)
            count_max_author += 1
        else:
            logger.info(f"⚠️ Phát hiện bản nét hơn ({max_yt_h}p) cho {vid}. Đang tải lại...")
            try:
                os.remove(fpath)
                # Gỡ khỏi archive
                if ARCHIVE_FILE.exists():
                    with open(ARCHIVE_FILE, "r", encoding="utf-8") as af:
                        lines = af.readlines()
                    with open(ARCHIVE_FILE, "w", encoding="utf-8") as af:
                        for line in lines:
                            if vid not in line:
                                af.write(line)
                
                # Tải lại
                ydl_opts = get_ydl_opts()
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([f"https://www.youtube.com/watch?v={vid}"])
                logger.info(f"✅ Đã tải lại thành công bản nét nhất cho {vid}")
                count_redownloaded += 1
            except Exception as e:
                logger.error(f"❌ Lỗi khi tải lại {vid}: {e}")
                count_errors += 1

    logger.info("--- HOÀN TẤT KIỂM TRA & CẬP NHẬT 2K/4K ---")
    logger.info(f"Đạt chuẩn 2K/4K: {count_2k}")
    logger.info(f"Đạt chất lượng tối đa của tác giả: {count_max_author}")
    logger.info(f"Đã tải lại bản đẹp hơn: {count_redownloaded}")
    logger.info(f"Tổng số lỗi: {count_errors}")

if __name__ == "__main__":
    run_verify()
