import os
import uuid
from typing import Dict, Any, Optional
import yt_dlp
from core.config import get_ydl_opts
from core.logger import get_logger

logger = get_logger("API_Service")

# Bộ nhớ lưu trạng thái các tiến trình tải
jobs: Dict[str, Dict[str, Any]] = {}


def _extract_output_path(info: dict) -> Optional[str]:
    """Lấy đường dẫn file cuối cùng (đã merge) từ info-dict của yt-dlp.

    Hỗ trợ cả video đơn lẫn playlist (lấy entry hợp lệ đầu tiên).
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
        return requested[0].get("filepath")
    return None


def execute_download_job(job_id: str, url: str):
    jobs[job_id]["status"] = "downloading"
    jobs[job_id]["message"] = "Đang tải video chất lượng cao nhất..."

    ydl_opts = get_ydl_opts()

    try:
        logger.info(f"[JOB {job_id}] Bắt đầu tải URL: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        # ignoreerrors=True khiến yt-dlp trả về None / không raise khi lỗi.
        # Phải tự kiểm tra để tránh báo "completed" giả.
        if info is None:
            raise RuntimeError("Không tải được video (URL không hợp lệ hoặc bị chặn).")

        filepath = _extract_output_path(info)
        if not filepath or not os.path.exists(filepath):
            raise RuntimeError("Tải xong nhưng không xác định được file kết quả.")

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["filepath"] = filepath
        jobs[job_id]["filename"] = os.path.basename(filepath)
        jobs[job_id]["message"] = "Tải video chất lượng cao nhất thành công!"
        logger.info(f"[JOB {job_id}] Hoàn thành: {filepath}")
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = f"Lỗi: {str(e)}"
        logger.error(f"[JOB {job_id}] Lỗi khi tải URL {url}: {e}")


def get_all_jobs() -> list:
    return list(jobs.values())


def get_job_by_id(job_id: str) -> dict:
    return jobs.get(job_id)


def create_job(url: str) -> str:
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    jobs[job_id] = {
        "id": job_id,
        "url": url,
        "status": "pending",
        "filename": None,
        "filepath": None,
        "message": "Đang khởi tạo tiến trình tải...",
    }
    return job_id
