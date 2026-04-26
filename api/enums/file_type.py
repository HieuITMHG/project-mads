from enum import Enum

class FileType(Enum):
    PDF = "application/pdf"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    
    CSV = "text/csv"
    TXT = "text/plain"
    JSON = "application/json"
    XML = "application/xml"
    
    JPG = "image/jpeg"
    PNG = "image/png"
    GIF = "image/gif"
    
    ZIP = "application/zip"
    RAR = "application/vnd.rar"