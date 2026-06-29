import sys
import logging

def get_logger(name: str = "YouTubeSync") -> logging.Logger:
    """Khởi tạo và trả về bộ Logger trung tâm chuẩn hóa."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s")
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
