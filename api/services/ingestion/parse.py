from core.docling_converter import converter
import os

def parse_file(file_path: str) -> str:
    try:
        result = converter.convert(file_path)
        return result.document.export_to_markdown()
    except Exception as e:
        print(e)
        if os.path.exists(file_path):
            os.remove(file_path)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)