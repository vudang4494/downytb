from typing import Optional, List, Literal
from pydantic import BaseModel, Field

from core.config import MAX_CHANNEL_VIDEOS

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


# --- Channel / playlist (tải hàng loạt) ---

class ChannelRequest(BaseModel):
    url: str = Field(..., description="URL channel hoặc playlist (YouTube...)")
    mode: DownloadMode = Field("video", description="video = MP4, audio = trích MP3")
    quality: VideoQuality = Field("max", description="Giới hạn độ phân giải tối đa")
    limit: Optional[int] = Field(
        None, ge=1, le=MAX_CHANNEL_VIDEOS,
        description="Chỉ tải N video mới nhất; bỏ trống = tải tới trần tối đa của server"
    )


class ChannelVideoItem(BaseModel):
    id: str
    title: str
    status: str  # pending, downloading, completed, failed, skipped
    filename: Optional[str] = None


class ChannelBatchResponse(BaseModel):
    id: str
    url: str
    status: str  # pending, enumerating, downloading, completed, failed
    message: str
    channel_title: Optional[str] = None
    mode: Optional[str] = None
    quality: Optional[str] = None
    total: int = 0
    done: int = 0       # tải mới thành công
    failed: int = 0
    skipped: int = 0    # đã có sẵn file -> bỏ qua (sync tăng dần)


class ChannelManifestResponse(ChannelBatchResponse):
    videos: List[ChannelVideoItem] = []


class ChannelsListResponse(BaseModel):
    batches: List[ChannelBatchResponse]
