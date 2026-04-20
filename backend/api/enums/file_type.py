from enum import Enum

class FileType(Enum):
    PDF = "application/pdf"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"