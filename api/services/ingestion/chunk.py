import re
import tiktoken
from sqlalchemy.ext.asyncio import AsyncSession
from api.models.chunk import DocumentChunk

sicbh_include_headers_in_content = False
sicbh_filter_headers = ["Table of Contents", "This Page", "Navigation"]
sicbh_show_unwanted_chunks_metadata = False

sample_markdowm ="""# Tài liệu Hướng dẫn Hệ thống AI v1.0

## Table of Contents
* [Tổng quan](#tổng-quan)
* [Cấu trúc Dữ liệu](#cấu-trúc-dữ-liệu)
* [Cài đặt](#cài-đặt)

## 1. Tổng quan
Đây là đoạn văn bản thuộc Header 2 đầu tiên. Nó nên được lưu với metadata là `{"Header 1": "Tài liệu Hướng dẫn Hệ thống AI v1.0", "Header 2": "1. Tổng quan"}`.

## 2. Chi tiết Kỹ thuật [¶](#section-2)
Đoạn này test regex xóa ký tự đặc biệt trong header.

### 2.1. Cấu trúc Database
Dưới đây là bảng dữ liệu để test format:

| Column | Type | Description |
| :--- | :--- | :--- |
| id | Integer | Primary Key |
| content | Text | Nội dung chunk |
| metadata | JSON | Lưu trữ header |

#### 2.1.1. Chi tiết Indexing
Dữ liệu cấp độ sâu nhất (H4). Metadata lúc này phải chứa đủ H1, H2, H3, H4.

### 2.2. API Reference
Khi chuyển từ H4 về H3, thông tin của H4 cũ phải bị xóa khỏi metadata.

## 3. Hướng dẫn Cài đặt
Đoạn này test logic nhảy từ H3 lên lại H2. Các thông tin của H3 (2.2) phải biến mất.

```python
# Đây là comment trong code block, không phải Header
def hello_world():
    print("Mã nguồn không được bị split ở đây")
    # Header Giả trong code"""

def split_into_chunks_by_headers(md_doc: str):
    chunks = []
    header_pattern = re.compile(r'^(#{1,6})\s+(.*)')
    code_block_pattern = re.compile(r'^\s*```')
    in_code_block = False

    # Sử dụng dict với key là số nguyên (level) để dễ quản lý việc tăng/giảm cấp độ
    current_headers = {} 
    
    lines = md_doc.split('\n')
    current_chunk = {'headers': {}, 'content': ''}

    for line in lines:
        # Bật/tắt trạng thái block code để tránh parse nhầm comment/header trong code
        if code_block_pattern.match(line):
            in_code_block = not in_code_block

        if not in_code_block:
            match = header_pattern.match(line)

            if match:
                # 1. Lưu chunk hiện tại vào mảng nếu có nội dung
                if current_chunk['content'].strip():
                    current_chunk['content'] = current_chunk['content'].strip()
                    
                    # Lấy header hiện tại sâu nhất để đối chiếu với filter
                    current_deepest_header = current_headers.get(max(current_headers.keys(), default=0), "")
                    
                    if current_deepest_header not in sicbh_filter_headers:
                        chunks.append(current_chunk)
                    
                    # Reset lại chunk content, giữ nguyên metadata cho các text tiếp theo
                    current_chunk = {'headers': current_chunk['headers'].copy(), 'content': ''}

                # 2. Xử lý logic Header mới
                header_level = len(match.group(1))
                header_text = match.group(2)

                # Clean header
                header_text = re.sub(r'\\', '', header_text)
                header_text = re.sub(r'\[¶\]\(.*?\)', '', header_text).strip()

                # Cập nhật header ở level hiện tại
                current_headers[header_level] = header_text
                
                # Xóa TẤT CẢ các header có cấp độ sâu hơn cấp độ hiện tại (ví dụ đang H2 thì xóa H3, H4)
                keys_to_remove = [k for k in current_headers.keys() if k > header_level]
                for k in keys_to_remove:
                    del current_headers[k]

                # Map lại metadata thành dạng format chuẩn { 'Header 1': '...', 'Header 2': '...' }
                formatted_headers = {f'Header {k}': v for k, v in sorted(current_headers.items())}
                current_chunk['headers'] = formatted_headers

                # Tùy chọn giữ lại text của header trong chính nội dung chunk
                if sicbh_include_headers_in_content:
                    current_chunk['content'] += f"{match.group(1)} {header_text}\n"
                
                continue  # Bỏ qua dòng này để không add header vào content lần 2 (nếu flag trên = False)

        # Append dòng bình thường vào chunk
        current_chunk['content'] += line + '\n'
    
    # Xử lý đoạn text cuối cùng (tránh bị sót)
    if current_chunk['content'].strip():
        current_chunk['content'] = current_chunk['content'].strip()
        current_deepest_header = current_headers.get(max(current_headers.keys(), default=0), "")
        
        if current_deepest_header not in sicbh_filter_headers:
            chunks.append(current_chunk)

    return chunks

tiktoken_encoder = "cl100k_base"
chunk_max_tokens = 500
scbt_text_follow_code_block = True

# Function to split a chunk into smaller parts based on token count
def split_chunk_by_tokens(content, tokenizer, max_tokens):
    # Split content into code blocks and paragraphs
    parts = re.split(r'(\n```\n.*?\n```\n)', content, flags=re.DOTALL)
    final_parts = []
    for part in parts:
        if part.startswith('\n```\n') and part.endswith('\n```\n'):
            final_parts.append(part)
        else:
            final_parts.extend(re.split(r'\n\s*\n', part))
    # Remove newlines from the start and end of each part
    parts = [part.strip() for part in final_parts if part.strip()]

    # Calculate total tokens
    total_tokens = sum(len(tokenizer.encode(part)) for part in parts)
    target_tokens_per_chunk = total_tokens // (total_tokens // max_tokens + 1)

    # Initialize variables
    chunks = []
    current_chunk = ""
    current_token_count = 0

    # Iterate over the parts and merge them if needed
    i = 0
    while i < len(parts):
        part = parts[i]

        # Merge parts if the current part ends with ":" or "```" (if enabled) and has a following part
        while (part.endswith(":") or (scbt_text_follow_code_block and part.endswith("```"))) and i + 1 < len(parts):
            part += "\n\n" + parts[i + 1]
            i += 1  # Skip the next part as it has been merged

        # Calculate the token count of the part
        part_tokens = tokenizer.encode(part)
        part_token_count = len(part_tokens)

        # Split the part into smaller parts if it exceeds the target token count
        if current_token_count + part_token_count > target_tokens_per_chunk and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = part
            current_token_count = part_token_count
        else:
            current_chunk += "\n\n" + part if current_chunk else part
            current_token_count += part_token_count

        i += 1

    # Add the last chunk if it has content
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

async def split_markdown(md_doc: str, db: AsyncSession, sessionfile_id: int):
    chunks = split_into_chunks_by_headers(md_doc=md_doc)
    
    db_chunks = []
    for chunk_data in chunks:
        new_chunk = DocumentChunk(
            session_file_id=sessionfile_id,
            content=chunk_data['content'],
            headers=chunk_data['headers']
        )
        db_chunks.append(new_chunk)

        try:
            db.add_all(db_chunks)
            await db.flush()
            print("Đã chunk và lưu chunk vào db thành công")
        except Exception as e:
            print(e)
        

