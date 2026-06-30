import os
import re
import mimetypes
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from core.config import DASHBOARD_TEMPLATE_FILE, OUTPUT_DIR
from core.logger import get_logger
from api.schemas import (
    DownloadRequest, JobsListResponse, JobStatusResponse, SystemStatusResponse,
    ChannelRequest, ChannelBatchResponse, ChannelManifestResponse, ChannelsListResponse,
)
from api.services import (
    execute_download_job, get_all_jobs, get_job_by_id, create_job,
    create_channel_job, execute_channel_job, get_channel_by_id, get_channel_video,
    get_all_channels, channel_slots_available,
)

logger = get_logger("API_Main")

app = FastAPI(
    title="downytb — Media Downloader API",
    description="Nhập một URL bất kỳ (YouTube, TikTok, Instagram, Twitter/X...) → tải video/audio ở chất lượng mong muốn.",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # allow_credentials phải là False khi allow_origins=["*"], nếu không trình duyệt sẽ từ chối CORS.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse, tags=["Web Dashboard"])
async def serve_dashboard():
    if not DASHBOARD_TEMPLATE_FILE.exists():
        return HTMLResponse(content="<h1>Lỗi: Không tìm thấy file dashboard.html trong thư mục templates/</h1>", status_code=404)
    with open(DASHBOARD_TEMPLATE_FILE, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/v1/download", tags=["Download Jobs"])
async def start_download_job(req: DownloadRequest, background_tasks: BackgroundTasks):
    if not req.url or not re.match(r"^https?://", req.url.strip()):
        raise HTTPException(status_code=400, detail="URL không hợp lệ. Vui lòng nhập một đường dẫn http(s).")

    options = {
        "mode": req.mode,
        "quality": req.quality,
    }
    job_id = create_job(req.url.strip(), options)
    background_tasks.add_task(execute_download_job, job_id, req.url.strip(), options)
    return JSONResponse({"job_id": job_id, "status": "pending", "message": "Tiến trình tải ngầm đã được kích hoạt."})

@app.get("/api/v1/jobs", response_model=JobsListResponse, tags=["Download Jobs"])
async def list_jobs():
    return {"jobs": get_all_jobs()}

@app.get("/api/v1/jobs/{job_id}", response_model=JobStatusResponse, tags=["Download Jobs"])
async def get_job_status(job_id: str):
    job = get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tiến trình với ID: {job_id}")
    return job

@app.get("/api/v1/jobs/{job_id}/file", tags=["Download Jobs"])
async def download_job_file(job_id: str):
    """Trả về file video chất lượng cao nhất sau khi job hoàn tất."""
    job = get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tiến trình với ID: {job_id}")
    if job.get("status") != "completed" or not job.get("filepath"):
        raise HTTPException(status_code=409, detail=f"File chưa sẵn sàng (trạng thái: {job.get('status')}).")
    filepath = job["filepath"]
    if not os.path.exists(filepath):
        raise HTTPException(status_code=410, detail="File kết quả không còn tồn tại trên máy chủ.")
    media_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"
    return FileResponse(filepath, filename=job.get("filename") or os.path.basename(filepath), media_type=media_type)

@app.post("/api/v1/channel", tags=["Channel / Playlist"])
async def start_channel_job(req: ChannelRequest, background_tasks: BackgroundTasks):
    """Nhập URL channel/playlist → tự liệt kê & tải hàng loạt (mỗi job có thư mục channel riêng)."""
    if not req.url or not re.match(r"^https?://", req.url.strip()):
        raise HTTPException(status_code=400, detail="URL không hợp lệ. Vui lòng nhập một đường dẫn http(s).")
    if not channel_slots_available():
        raise HTTPException(status_code=429, detail="Đang có quá nhiều batch channel chạy. Vui lòng thử lại sau.")
    options = {"mode": req.mode, "quality": req.quality, "limit": req.limit}
    batch_id = create_channel_job(req.url.strip(), options)
    background_tasks.add_task(execute_channel_job, batch_id, req.url.strip(), options)
    return JSONResponse({"batch_id": batch_id, "status": "pending", "message": "Đã bắt đầu xử lý channel."})


@app.get("/api/v1/channels", response_model=ChannelsListResponse, tags=["Channel / Playlist"])
async def list_channels():
    return {"batches": get_all_channels()}


@app.get("/api/v1/channel/{batch_id}", response_model=ChannelBatchResponse, tags=["Channel / Playlist"])
async def get_channel_status(batch_id: str):
    batch = get_channel_by_id(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy batch: {batch_id}")
    return batch


@app.get("/api/v1/channel/{batch_id}/manifest", response_model=ChannelManifestResponse, tags=["Channel / Playlist"])
async def get_channel_manifest(batch_id: str):
    """Trạng thái batch kèm danh sách từng video (id, tiêu đề, trạng thái, tên file)."""
    batch = get_channel_by_id(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy batch: {batch_id}")
    return batch


@app.get("/api/v1/channel/{batch_id}/videos/{video_id}/file", tags=["Channel / Playlist"])
async def download_channel_video_file(batch_id: str, video_id: str):
    """Tải file của một video cụ thể trong batch channel."""
    item = get_channel_video(batch_id, video_id)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy video trong batch.")
    if item.get("status") not in ("completed", "skipped") or not item.get("filepath"):
        raise HTTPException(status_code=409, detail=f"File chưa sẵn sàng (trạng thái: {item.get('status')}).")
    filepath = item["filepath"]
    if not os.path.exists(filepath):
        raise HTTPException(status_code=410, detail="File kết quả không còn tồn tại trên máy chủ.")
    media_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"
    return FileResponse(filepath, filename=item.get("filename") or os.path.basename(filepath), media_type=media_type)


@app.get("/api/v1/system/status", response_model=SystemStatusResponse, tags=["System"])
async def check_system_status():
    return {
        "status": "online",
        "output_dir": str(OUTPUT_DIR),
        "output_writable": os.access(OUTPUT_DIR, os.W_OK),
        "version": "3.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
