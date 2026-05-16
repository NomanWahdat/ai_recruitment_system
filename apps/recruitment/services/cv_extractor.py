from pathlib import Path

from docx import Document
from PyPDF2 import PdfReader

from apps.recruitment.utils.text import clean_extracted_text


class CVExtractionError(Exception):
    pass


class CVTextExtractor:
    def extract(self, file_path):
        extension = Path(file_path).suffix.lower()

        if extension == ".pdf":
            return self.extract_pdf(file_path)

        if extension == ".docx":
            return self.extract_docx(file_path)

        raise CVExtractionError("Unsupported CV file type.")

    def extract_pdf(self, file_path):
        try:
            reader = PdfReader(file_path)
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n\n".join(pages)
        except Exception as exc:
            raise CVExtractionError("Unable to read PDF file.") from exc

        return clean_extracted_text(text)

    def extract_docx(self, file_path):
        try:
            document = Document(file_path)
            paragraphs = [paragraph.text for paragraph in document.paragraphs]
            text = "\n".join(paragraphs)
        except Exception as exc:
            raise CVExtractionError("Unable to read DOCX file.") from exc

        return clean_extracted_text(text)
