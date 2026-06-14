import asyncio
import os
import sys
from dotenv import load_dotenv

# Load biến môi trường từ .env.dev để tránh lỗi Pydantic ValidationError của core.config
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env.dev'))
load_dotenv(dotenv_path=env_path)

# Đảm bảo Python có thể tìm thấy thư mục gốc của project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from api.agents.graph import build_agent_graph

async def run_demo():
    print("\n[HỆ THỐNG] Đang biên dịch Main Graph...")
    main_graph = build_agent_graph()
    print("[HỆ THỐNG] Biên dịch thành công!\n")

    
    from langchain_core.messages import HumanMessage

    # State ban đầu giả lập một yêu cầu mới từ người dùng
    initial_state = {
        "messages": [HumanMessage(content="Hãy phân tích biểu đồ doanh thu giúp tôi. (Test chạy giả lập)")], 
        "collected_results": [],
        "current_instruction": "",
        "chatbox_id": 1,
        "sessionfile_ids": [],
        "file_context": "No file uploaded.",
        "summary": ""
    }
    
    print("================ BẮT ĐẦU CHẠY LUỒNG ================\n")
    
    # Chạy graph thông qua astream để xem từng bước thực thi
    async for output in main_graph.astream(initial_state):
        for node_name, state_update in output.items():
            print(f"\n[Engine] ---> Xong Node '{node_name}'.")
            
    print("\n================ KẾT THÚC LUỒNG ================")

if __name__ == "__main__":
    asyncio.run(run_demo())
