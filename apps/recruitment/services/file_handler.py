from django.core.exceptions import ValidationError

from apps.recruitment.utils.validators import (
    build_safe_filename,
    validate_cv_extension,
    validate_file_size,
)


class CVFileHandler:
    def validate(self, file):
        validate_cv_extension(file.name)
        validate_file_size(file)

    def prepare_upload(self, file):
        self.validate(file)
        original_name = file.name
        file.name = build_safe_filename(file.name)
        return original_name, file

    def format_validation_error(self, error):
        if isinstance(error, ValidationError):
            return "; ".join(error.messages)
        return str(error)
