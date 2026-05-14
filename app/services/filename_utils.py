import re
from datetime import datetime

from werkzeug.utils import secure_filename


UPLOAD_PREFIX_RE = re.compile(r"^\d{8}_\d{6}_\d{6}_")


def make_upload_filename(original_filename):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"{timestamp}_{secure_filename(original_filename)}"


def display_filename(filename):
    return UPLOAD_PREFIX_RE.sub("", filename or "")
