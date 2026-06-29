import os
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from core.config import DASHBOARD_TEMPLATE_FILE, OUTPUT_DIR
from core.logger import get_logger
from api.schemas import DownloadRequest, JobsListResponse, JobStatusResponse, SystemStatusResponse
from api.services import execute_download_job, get_all_jobs, get_job_by_id, create_job

logger = get_logger("API_Main")

app = FastAPI(
    title="YouTube HD Downloader API",
    description="Nhập một URL YouTube bất kỳ → tải và trả về video chất lượng cao nhất của clip đó.",
    version="2.0.0",
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
    if not req.url or ("youtube.com" not in req.url and "youtu.be" not in req.url):
        raise HTTPException(status_code=400, detail="URL không hợp lệ. Vui lòng nhập đường dẫn YouTube.")

    job_id = create_job(req.url)
    background_tasks.add_task(execute_download_job, job_id, req.url)
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
    return FileResponse(filepath, filename=job.get("filename") or os.path.basename(filepath), media_type="video/mp4")

@app.get("/api/v1/system/status", response_model=SystemStatusResponse, tags=["System"])
async def check_system_status():
    return {
        "status": "online",
        "output_dir": str(OUTPUT_DIR),
        "output_writable": os.access(OUTPUT_DIR, os.W_OK),
        "version": "2.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
