import os
import uuid
from typing import Dict, Any, Optional
import yt_dlp
from core.config import build_ydl_opts, OUTPUT_DIR
from core.logger import get_logger

logger = get_logger("API_Service")

# Bộ nhớ lưu trạng thái các tiến trình tải
jobs: Dict[str, Dict[str, Any]] = {}

DEFAULT_OPTIONS = {"mode": "video", "quality": "max"}


def _resolve_output_path(info: dict, dest_dir: str) -> Optional[str]:
    """Xác định đường dẫn file cuối cùng từ info-dict của yt-dlp.

    Hỗ trợ video đơn lẫn playlist (lấy entry hợp lệ đầu tiên). Có fallback quét
    dest_dir theo video id để vẫn tìm được file kể cả khi đã qua postprocessor
    (vd trích audio đổi đuôi .webm -> .mp3).
    """
    if not info:
        return None
    entry = info
    if info.get("_type") == "playlist" or "entries" in info:
        entries = [e for e in (info.get("entries") or []) if e]
        if not entries:
            return None
        entry = entries[0]

    requested = entry.get("requested_downloads") or []
    if requested:
        fp = requested[0].get("filepath")
        if fp and os.path.exists(fp):
            return fp

    # Fallback: tìm theo video id trong tên file (outtmpl luôn chứa [<id>])
    vid = entry.get("id")
    if vid and os.path.isdir(dest_dir):
        tag = f"[{vid}]"
        candidates = [
            os.path.join(dest_dir, f)
            for f in os.listdir(dest_dir)
            if tag in f and os.path.isfile(os.path.join(dest_dir, f))
        ]
        if candidates:
            return max(candidates, key=os.path.getmtime)
    return None


def execute_download_job(job_id: str, url: str, options: dict = None):
    options = {**DEFAULT_OPTIONS, **(options or {})}
    jobs[job_id]["status"] = "downloading"
    jobs[job_id]["message"] = f"Đang tải ({options['mode']}, {options['quality']})..."

    # Mỗi job có thư mục riêng để các lần tải không ghi đè lên nhau
    dest_dir = os.path.join(OUTPUT_DIR, job_id)
    os.makedirs(dest_dir, exist_ok=True)

    ydl_opts = build_ydl_opts(
        mode=options["mode"],
        quality=options["quality"],
        dest_dir=dest_dir,
    )

    try:
        logger.info(f"[JOB {job_id}] Bắt đầu tải URL: {url} | options={options}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        # ignoreerrors=True khiến yt-dlp trả về None / không raise khi lỗi.
        if info is None:
            raise RuntimeError("Không tải được (URL không hợp lệ, bị chặn, hoặc không được hỗ trợ).")

        filepath = _resolve_output_path(info, dest_dir)
        if not filepath or not os.path.exists(filepath):
            raise RuntimeError("Tải xong nhưng không xác định được file kết quả.")

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["filepath"] = filepath
        jobs[job_id]["filename"] = os.path.basename(filepath)
        jobs[job_id]["message"] = "Tải thành công!"
        logger.info(f"[JOB {job_id}] Hoàn thành: {filepath}")
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = f"Lỗi: {str(e)}"
        logger.error(f"[JOB {job_id}] Lỗi khi tải URL {url}: {e}")


def get_all_jobs() -> list:
    return list(jobs.values())


def get_job_by_id(job_id: str) -> dict:
    return jobs.get(job_id)


def create_job(url: str, options: dict = None) -> str:
    options = {**DEFAULT_OPTIONS, **(options or {})}
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    jobs[job_id] = {
        "id": job_id,
        "url": url,
        "status": "pending",
        "mode": options["mode"],
        "quality": options["quality"],
        "filename": None,
        "filepath": None,
        "message": "Đang khởi tạo tiến trình tải...",
    }
    return job_id
