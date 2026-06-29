from typing import Optional, List, Literal
from pydantic import BaseModel, Field

# Lựa chọn rời rạc, tối giản: chủ yếu là MP4 (video), kèm tùy chọn trích MP3.
DownloadMode = Literal["video", "audio"]
VideoQuality = Literal["144", "240", "360", "480", "720", "1080", "1440", "2160", "max"]


class DownloadRequest(BaseModel):
    url: str = Field(..., description="URL cần tải (YouTube, TikTok, Instagram, Twitter/X... — bất kỳ site nào yt-dlp hỗ trợ)")
    mode: DownloadMode = Field("video", description="video = MP4 (video+audio), audio = trích MP3")
    quality: VideoQuality = Field("max", description="Giới hạn độ phân giải tối đa; 'max' = cao nhất có thể")


class JobStatusResponse(BaseModel):
    id: str
    url: str
    status: str  # pending, downloading, completed, failed
    message: str
    mode: Optional[str] = None
    quality: Optional[str] = None
    filename: Optional[str] = None  # tên file kết quả khi status = completed


class JobsListResponse(BaseModel):
    jobs: List[JobStatusResponse]


class SystemStatusResponse(BaseModel):
    status: str  # online
    output_dir: str
    output_writable: bool
    version: str
