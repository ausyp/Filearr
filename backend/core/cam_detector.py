import re

CAM_PATTERNS = re.compile(
    r"(CAM|HDCAM|TS|HDTS|TELESYNC|TC|SCR|SCREENER|WORKPRINT|WP)",
    re.I
)

def is_cam(filename):
    """
    Returns True if the filename suggests a CAM or Telesync copy.
    """
    return bool(CAM_PATTERNS.search(filename))
