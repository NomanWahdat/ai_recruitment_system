from pathlib import Path
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.utils.text import get_valid_filename

ALLOWED_CV_EXTENSIONS = {".pdf", ".docx"}
MAX_CV_FILE_SIZE = 10 * 1024 * 1024


def validate_cv_file(file):
    extension = Path(file.name).suffix.lower()

    if extension not in ALLOWED_CV_EXTENSIONS:
        raise ValidationError("Only PDF and DOCX files are allowed.")

    if file.size > MAX_CV_FILE_SIZE:
        raise ValidationError("CV file size must not exceed 10MB.")


def get_file_extension(filename):
    return Path(filename).suffix.lower()


def validate_cv_extension(filename):
    extension = get_file_extension(filename)

    if extension not in ALLOWED_CV_EXTENSIONS:
        raise ValidationError("Only PDF and DOCX files are allowed.")

    return extension


def validate_file_size(file):
    if file.size > MAX_CV_FILE_SIZE:
        raise ValidationError("CV file size must not exceed 10MB.")


def build_safe_filename(filename):
    extension = validate_cv_extension(filename)
    stem = get_valid_filename(Path(filename).stem) or "cv"
    return f"{stem}-{uuid4().hex}{extension}"
