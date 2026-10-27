from pathlib import Path
from uuid import uuid4
import hashlib
from zipfile import ZipFile, BadZipFile
from django.core.exceptions import ValidationError
from django.utils.text import get_valid_filename

ALLOWED_CV_EXTENSIONS = {".pdf", ".docx"}
MAX_CV_FILE_SIZE = 10 * 1024 * 1024


def validate_cv_extension(filename):
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_CV_EXTENSIONS:
        raise ValidationError("Only PDF and DOCX files are allowed.")
    return extension


def validate_file_size(file):
    if not 0 < file.size <= MAX_CV_FILE_SIZE:
        raise ValidationError("CV must be nonempty and no larger than 10 MB.")


def validate_cv_file(file):
    extension = validate_cv_extension(file.name)
    validate_file_size(file)
    position = file.tell()
    try:
        file.seek(0)
        if extension == ".pdf":
            if not file.read(5).startswith(b"%PDF-"):
                raise ValidationError("File content is not a PDF.")
        else:
            file.seek(0)
            with ZipFile(file) as archive:
                infos = archive.infolist()
                if len(infos) > 1000 or sum(i.file_size for i in infos) > 30 * 1024 * 1024:
                    raise ValidationError("DOCX archive exceeds processing limits.")
                if "word/document.xml" not in archive.namelist():
                    raise ValidationError("File content is not a DOCX document.")
                if any(i.flag_bits & 1 for i in infos):
                    raise ValidationError("Encrypted DOCX files are not supported.")
    except (BadZipFile, OSError, KeyError) as exc:
        raise ValidationError("Invalid document container.") from exc
    finally:
        file.seek(position)


def file_digest(file):
    position = file.tell()
    file.seek(0)
    result = hashlib.sha256()
    for chunk in file.chunks():
        result.update(chunk)
    file.seek(position)
    return result.hexdigest()


def get_file_extension(filename):
    return Path(filename).suffix.lower()


def build_safe_filename(filename):
    extension = validate_cv_extension(filename)
    return f"{get_valid_filename(Path(filename).stem)[:80] or 'cv'}-{uuid4().hex}{extension}"
