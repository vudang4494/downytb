import os
import re
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional
import yt_dlp
from core.config import (
    build_ydl_opts, build_enumerate_opts, OUTPUT_DIR,
    CHANNEL_CONCURRENCY, MAX_CHANNEL_VIDEOS, MAX_CONCURRENT_CHANNELS,
)
from core.logger import get_logger

logger = get_logger("API_Service")

# Bộ nhớ lưu trạng thái các tiến trình tải
jobs: Dict[str, Dict[str, Any]] = {}

# Bộ nhớ lưu trạng thái các batch tải channel/playlist
channels: Dict[str, Dict[str, Any]] = {}

# Giữ tối đa N batch trong bộ nhớ (evict các batch đã xong cũ nhất để tránh phình RAM).
MAX_BATCHES_KEEP = max(MAX_CONCURRENT_CHANNELS * 10, int(os.getenv("MAX_BATCHES_KEEP", "100")))

DEFAULT_OPTIONS = {"mode": "video", "quality": "max"}

# Đuôi file tạm/đang tải — KHÔNG tính là file kết quả hoàn chỉnh.
_TEMP_EXTS = (".part", ".ytdl", ".tmp", ".temp", ".download")


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

    # Fallback: khớp CHẶT tag id ngay trước phần mở rộng (outtmpl luôn là `...[<id>].<ext>`),
    # loại file tạm — tránh trả nhầm '.part'/file trung gian hoặc title chứa '[id]'.
    vid = entry.get("id")
    if vid and os.path.isdir(dest_dir):
        pat = re.compile(r"\[" + re.escape(vid) + r"\]\.[^.]+$")
        candidates = [
            os.path.join(dest_dir, f)
            for f in os.listdir(dest_dir)
            if pat.search(f) and not f.endswith(_TEMP_EXTS)
            and os.path.isfile(os.path.join(dest_dir, f))
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


# ======================================================================
# CHANNEL / PLAYLIST — tải hàng loạt (batch job cha/con)
# ======================================================================

def _slugify(text: str, fallback: str) -> str:
    """Biến tên/ID channel thành tên thư mục an toàn (1 segment, không path-traversal)."""
    # strip cả '_' lẫn '.' để '..'/'.' không sống sót thành tên thư mục.
    slug = re.sub(r"[^\w.-]+", "_", (text or "").strip()).strip("_.")
    if not slug or slug in (".", ".."):
        return fallback
    return slug[:60]


def _normalize_channel_url(url: str) -> str:
    """Channel root chưa có tab -> thêm /videos để lấy thẳng danh sách video.

    vd: https://youtube.com/@abc  ->  https://youtube.com/@abc/videos
    Bỏ qua query/fragment khi so khớp (vd /@abc?foo=bar vẫn nhận diện là channel root).
    Playlist / watch / URL đã có tab thì giữ nguyên.
    """
    base = re.split(r"[?#]", url.strip(), 1)[0].rstrip("/")
    if re.search(r"youtube\.com/(@[\w.-]+|channel/[\w-]+|c/[\w.-]+|user/[\w.-]+)$", base):
        return base + "/videos"
    return url


def _flatten_entries(info: dict) -> list:
    """Duyệt info-dict GIỮ NGUYÊN THỨ TỰ, trả về list entry (gồm cả stub) theo đúng
    trình tự channel liệt kê (mới→cũ), để videos[:limit] lấy đúng N video MỚI nhất.

    Đệ quy in-order (không dùng stack LIFO vì sẽ đảo ngược thứ tự). Channel YouTube
    chỉ lồng nông (channel→tab→video) nên độ sâu đệ quy không đáng ngại.
    """
    out = []

    def walk(node):
        if not node:
            return
        if node.get("_type") == "playlist" or "entries" in node:
            for child in (node.get("entries") or []):
                walk(child)
        else:
            out.append(node)

    walk(info)
    return out


def _find_existing(dest_dir: str, vid: str) -> Optional[str]:
    """Tìm file ĐÃ TẢI HOÀN CHỈNH của 1 video (để bỏ qua khi sync).

    Khớp chặt tag id ngay trước phần mở rộng: `...[<id>].<ext>` (anchored cuối tên),
    nên không dính title chứa '[id]' và không nhầm với file tạm/format trung gian
    như `[id].f398.mp4`, `[id].mp4.part`.
    """
    if not vid or not os.path.isdir(dest_dir):
        return None
    pat = re.compile(r"\[" + re.escape(vid) + r"\]\.[^.]+$")
    for f in os.listdir(dest_dir):
        if f.endswith(_TEMP_EXTS):
            continue
        fp = os.path.join(dest_dir, f)
        if pat.search(f) and os.path.isfile(fp):
            return fp
    return None


def _is_video_entry(e: dict) -> bool:
    """Phân biệt entry là VIDEO thật với playlist/tab-stub khi liệt kê flat.

    extract_flat trả tab/playlist lồng nhau dưới dạng stub (_type='url', ie_key chứa
    'Playlist'/'Tab') — phải loại để không đưa URL playlist vào hàng tải.
    """
    if not e or e.get("_type") == "playlist" or "entries" in e:
        return False
    ie = str(e.get("ie_key") or e.get("extractor_key") or "").lower()
    if "playlist" in ie or "tab" in ie:
        return False
    return bool(e.get("id"))


def enumerate_channel(url: str, limit: int = None):
    """Liệt kê nhanh (không tải) các video của channel/playlist.

    Trả về: (meta dict {title, channel_id} | None, list[{id,title,url}]).
    """
    opts = build_enumerate_opts(limit=limit)
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(_normalize_channel_url(url), download=False)
    if not info:
        return None, []
    meta = {
        "title": info.get("title") or info.get("uploader") or info.get("id") or "channel",
        "channel_id": info.get("channel_id") or info.get("uploader_id") or info.get("id") or "channel",
    }
    videos, seen = [], set()
    for e in _flatten_entries(info):
        if not _is_video_entry(e):
            continue
        vid = e.get("id")
        if vid in seen:  # dedupe — tránh tải trùng / total bị thổi phồng
            continue
        vurl = e.get("url") or e.get("webpage_url") or f"https://www.youtube.com/watch?v={vid}"
        seen.add(vid)
        videos.append({"id": vid, "title": e.get("title") or vid, "url": vurl})
    if limit and int(limit) > 0:
        videos = videos[: int(limit)]
    return meta, videos


def _download_single(video_url: str, dest_dir: str, options: dict) -> str:
    """Tải 1 video về dest_dir; trả về đường dẫn file. Raise nếu lỗi."""
    # Nghỉ ngắn ngẫu nhiên giữa các video để giảm rủi ro bị chặn bot khi tải hàng loạt.
    throttle = {"sleep_interval": 1, "max_sleep_interval": 3}
    ydl_opts = build_ydl_opts(
        mode=options["mode"], quality=options["quality"],
        dest_dir=dest_dir, custom_opts=throttle,
    )
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
    if info is None:
        raise RuntimeError("Không tải được video (bị chặn/riêng tư/không hỗ trợ).")
    filepath = _resolve_output_path(info, dest_dir)
    if not filepath or not os.path.exists(filepath):
        raise RuntimeError("Tải xong nhưng không xác định được file kết quả.")
    return filepath


_ACTIVE_STATES = ("pending", "enumerating", "downloading")


def active_channel_count() -> int:
    """Số batch channel đang chạy — dùng cho admission control (giới hạn batch đồng thời)."""
    return sum(1 for b in channels.values() if b.get("status") in _ACTIVE_STATES)


def channel_slots_available() -> bool:
    return active_channel_count() < MAX_CONCURRENT_CHANNELS


def _prune_channels():
    """Evict bớt batch ĐÃ XONG cũ nhất khi vượt MAX_BATCHES_KEEP (giữ batch đang chạy)."""
    while len(channels) > MAX_BATCHES_KEEP:
        for bid, b in channels.items():  # dict giữ thứ tự chèn -> cái cũ nhất ở đầu
            if b.get("status") not in _ACTIVE_STATES:
                channels.pop(bid, None)
                break
        else:
            break  # không còn batch nào đã xong để evict


def create_channel_job(url: str, options: dict = None) -> str:
    options = {**DEFAULT_OPTIONS, **(options or {})}
    _prune_channels()
    batch_id = f"ch_{uuid.uuid4().hex[:12]}"
    channels[batch_id] = {
        "id": batch_id,
        "url": url,
        "status": "pending",
        "message": "Đang khởi tạo batch tải channel...",
        "channel_title": None,
        "mode": options["mode"],
        "quality": options["quality"],
        "total": 0, "done": 0, "failed": 0, "skipped": 0,
        "videos": [],
        "dest_dir": None,
    }
    return batch_id


def execute_channel_job(batch_id: str, url: str, options: dict = None):
    options = {**DEFAULT_OPTIONS, **(options or {})}
    batch = channels[batch_id]
    # Trần CỨNG: kể cả client bỏ trống `limit` cũng không vượt MAX_CHANNEL_VIDEOS.
    # Clamp về [1, MAX] để giá trị âm/0 (nếu lọt qua) không vô hiệu hóa giới hạn.
    requested = options.get("limit")
    effective_limit = min(int(requested), MAX_CHANNEL_VIDEOS) if requested else MAX_CHANNEL_VIDEOS
    effective_limit = max(1, effective_limit)
    try:
        batch["status"] = "enumerating"
        batch["message"] = "Đang liệt kê video trong channel..."
        meta, videos = enumerate_channel(url, limit=effective_limit)
        if not videos:
            raise RuntimeError("Không tìm thấy video nào (URL có phải channel/playlist không?).")

        batch["channel_title"] = meta["title"]
        # Lưu theo thư mục channel để hỗ trợ SYNC TĂNG DẦN (lần sau bỏ qua video đã có).
        dest_dir = os.path.join(OUTPUT_DIR, "channels", _slugify(meta["channel_id"], batch_id))
        os.makedirs(dest_dir, exist_ok=True)
        batch["dest_dir"] = dest_dir
        batch["total"] = len(videos)
        batch["videos"] = [
            {**v, "status": "pending", "filename": None, "filepath": None, "message": ""}
            for v in videos
        ]
        batch["status"] = "downloading"
        batch["message"] = f"Đang tải {len(videos)} video..."
        logger.info(f"[CHANNEL {batch_id}] '{meta['title']}' — {len(videos)} video -> {dest_dir}")

        lock = threading.Lock()

        def work(item: dict):
            # Incremental: đã có file [id] -> bỏ qua (xóa file thì lần sau tự tải lại).
            existing = _find_existing(dest_dir, item["id"])
            if existing:
                with lock:
                    item["status"] = "skipped"
                    item["filepath"] = existing
                    item["filename"] = os.path.basename(existing)
                    batch["skipped"] += 1
                return
            with lock:
                item["status"] = "downloading"
            try:
                fp = _download_single(item["url"], dest_dir, options)
                with lock:
                    item["status"] = "completed"
                    item["filepath"] = fp
                    item["filename"] = os.path.basename(fp)
                    batch["done"] += 1
            except Exception as e:
                with lock:
                    item["status"] = "failed"
                    # RuntimeError = thông báo sạch tự raise; lỗi yt-dlp/OS -> message chung
                    # (chi tiết vào log) để không lộ path/nội bộ nếu sau này expose message.
                    item["message"] = str(e) if isinstance(e, RuntimeError) else "Tải video thất bại."
                    batch["failed"] += 1
                logger.warning(f"[CHANNEL {batch_id}] Lỗi video {item['id']}: {e}")

        with ThreadPoolExecutor(max_workers=CHANNEL_CONCURRENCY) as ex:
            list(ex.map(work, batch["videos"]))

        batch["status"] = "completed"
        batch["message"] = (
            f"Hoàn tất: {batch['done']} tải mới, {batch['skipped']} bỏ qua, {batch['failed']} lỗi."
        )
        logger.info(f"[CHANNEL {batch_id}] {batch['message']}")
    except Exception as e:
        batch["status"] = "failed"
        # RuntimeError là thông báo "sạch" mình chủ động raise; lỗi khác -> message chung
        # để tránh lộ đường dẫn local / chi tiết nội bộ ra client (chi tiết vẫn vào log).
        batch["message"] = str(e) if isinstance(e, RuntimeError) else "Lỗi xử lý channel (xem log máy chủ)."
        logger.error(f"[CHANNEL {batch_id}] Lỗi batch: {e}")


def get_all_channels() -> list:
    return list(channels.values())


def get_channel_by_id(batch_id: str) -> dict:
    return channels.get(batch_id)


def get_channel_video(batch_id: str, video_id: str) -> Optional[dict]:
    batch = channels.get(batch_id)
    if not batch:
        return None
    return next((v for v in batch.get("videos", []) if v.get("id") == video_id), None)
