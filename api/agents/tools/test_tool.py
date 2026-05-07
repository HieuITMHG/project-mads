import sys
from pathlib import Path

# --- BƯỚC 1: HACK SYS.PATH ĐỂ PYTHON NHÌN THẤY THƯ MỤC ROOT ---
# File này nằm ở MADS/api/agents/tools/test_tool.py
# Chúng ta lùi về 4 cấp để lấy được đường dẫn thư mục MADS
root_dir = Path(__file__).resolve().parents[3] 

# Thêm MADS vào danh sách đường dẫn tìm kiếm module của Python
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# --- BƯỚC 2: LOAD BIẾN MÔI TRƯỜNG (Dành cho Qdrant/Settings) ---
import os
from dotenv import load_dotenv
# Tìm file .env ở thư mục MADS
load_dotenv(root_dir / ".env.dev") 

# --- BƯỚC 3: BÂY GIỜ BẠN CÓ THỂ IMPORT BÌNH THƯỜNG ---
import asyncio
# Sử dụng import tuyệt đối từ thư mục gốc
from api.agents.tools.rag import search_rag 

async def debug_tool():
    query_from_llm = "customer service"
    mock_session_ids = [1] # Điền ID thực tế trong Qdrant nếu có
    
    print(f"--- Đang gọi tool search_rag với query: {query_from_llm} ---")
    
    try:
        results = await search_rag.ainvoke({
            "llm_rewrite_query": query_from_llm,
            "sessionfile_ids": mock_session_ids
        })
        print(f"\n--- Kết quả trả về ({len(results)} contexts) ---")
        for i, res in enumerate(results):
            print(f"[{i}] Payload: {res}")
            
    except Exception as e:
        print(f"Lỗi: {e}")

if __name__ == "__main__":
    asyncio.run(debug_tool())