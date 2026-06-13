from fastapi import FastAPI
from pydantic import BaseModel
import os
import docker
from sandbox_api.utils.file_utils import download_all_files
import shutil
import time
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler

client = docker.from_env()

DOCKER_VOLUME_NAME = "mads_shared_vol" 
API_WORKSPACE_DIR = "/workspace"  
TTL_SECONDS = 3600   

def cleanup_expired_workspaces():
    """Hàm chạy ngầm quét dọn các folder hết hạn"""
    now = time.time()
    print("[Garbage Collector] Đang quét dọn workspace...")
    
    if not os.path.exists(API_WORKSPACE_DIR):
        return

    for session_folder in os.listdir(API_WORKSPACE_DIR):
        folder_path = os.path.join(API_WORKSPACE_DIR, session_folder)
        
        if os.path.isdir(folder_path):
            folder_mtime = os.stat(folder_path).st_mtime
            
            if folder_mtime < (now - TTL_SECONDS):
                try:
                    shutil.rmtree(folder_path)
                    print(f"Đã xóa workspace hết hạn: {session_folder}")
                except Exception as e:
                    print(f"Lỗi xóa {session_folder}: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()
    scheduler.add_job(cleanup_expired_workspaces, 'interval', minutes=15)
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(title="MADS Sandbox API", lifespan=lifespan)

class CodeRequest(BaseModel):
    session_id: str 
    code: str

class PrepareRequest(BaseModel):
    session_id: str 
    s3_path_lst: list[str]


@app.post("/prepare_file_data")
async def prepare_file_data(request: PrepareRequest):
    try:
        session_dir = os.path.join(API_WORKSPACE_DIR, request.session_id)

        download_all_files(request.s3_path_lst, session_dir)
        return {"Prepare file result": "Success"}
    except Exception as e:
        print(e)
        return {"Prepare file result": "Fail"}


@app.post("/execute")
async def execute_code(request: CodeRequest):
    session_id = request.session_id
    
    session_dir = os.path.join(API_WORKSPACE_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)
    os.chmod(session_dir, 0o777)

    script_path = os.path.join(session_dir, "script.py")
    
    # Mã mồi (Boilerplate) tự động nạp dữ liệu
    boilerplate = """
import pandas as pd
import glob
import os

try:
    import plotly.io as pio
    pio.templates.default = "none"
except ImportError:
    pass

dfs = {}
for file in glob.glob("*.*"):
    if file.endswith('.csv'):
        dfs[file] = pd.read_csv(file)
    elif file.endswith(('.xls', '.xlsx')):
        dfs[file] = pd.read_excel(file)

if len(dfs) == 1:
    df = list(dfs.values())[0]

# --- USER CODE START ---
"""
    
    with open(script_path, "w") as f:
        f.write(boilerplate + request.code)

    try:
        container = client.containers.run(
            image="mads-sandbox-base",
            command=["python", "script.py"],
            volumes={
                DOCKER_VOLUME_NAME: {'bind': '/workspace', 'mode': 'rw'}
            },

            working_dir=f"/workspace/{session_id}", 
            network_disabled=True, 
            mem_limit="512m",        
            cpu_quota=100000,          

            detach=True
        )

        result = container.wait(timeout=15)
        logs = container.logs().decode("utf-8")
        container.remove(force=True)

        is_success = result["StatusCode"] == 0

        return {
            "success": is_success,
            "logs": logs,
        }
    except Exception as e:
        return {"success": False, "logs": str(e)}