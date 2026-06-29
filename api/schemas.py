from typing import Optional, List
from pydantic import BaseModel, Field

class DownloadRequest(BaseModel):
    url: str = Field(..., description="Đường dẫn YouTube cần tải (video chất lượng cao nhất)")

class JobStatusResponse(BaseModel):
    id: str
    url: str
    status: str  # pending, downloading, completed, failed
    message: str
    filename: Optional[str] = None  # tên file kết quả khi status = completed

class JobsListResponse(BaseModel):
    jobs: List[JobStatusResponse]

class SystemStatusResponse(BaseModel):
    status: str  # online
    output_dir: str
    output_writable: bool
    version: str
