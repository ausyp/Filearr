import os
import re

CAM_PATTERNS = re.compile(
    r"\b(CAM|HDCAM|TS|HDTS|TELESYNC|TC|SCR|SCREENER|WORKPRINT|WP)\b",
    re.I
)

def is_cam(filename):
    """
    Returns True if the filename suggests a CAM or Telesync copy.
    """
    # Strip the extension so "movie.ts" (MPEG transport stream) isn't mistaken for Telesync
    name, _ = os.path.splitext(os.path.basename(filename))
    return bool(CAM_PATTERNS.search(name))
