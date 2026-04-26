from fastapi import FastAPI
from pydantic import BaseModel
import uuid
import os
import docker

client = docker.from_env()

app = FastAPI(title="MADS Sandbox API")

class CodeRequest(BaseModel):
    code: str

@app.post("/execute")
async def execute_code(request: CodeRequest):
    session_id = str(uuid.uuid4())

    api_workspace = f"/tmp/uploads/{session_id}"
    os.makedirs(api_workspace, exist_ok=True)

    os.chmod(api_workspace, 0o777)

    with open(os.path.join(api_workspace, "script.py"), "w") as f:
        f.write(request.code)

    host_shared_tmp = os.getenv("HOST_SHARED_TMP_DIR")
    host_session_path = f"{host_shared_tmp}/{session_id}"

    try:
        container = client.containers.run(
            image="mads-sandbox-base",
            command=["python", "script.py"],
            volumes={host_session_path: {'bind': '/app', 'mode': 'rw'}},
            network_disabled=True, 
            mem_limit="512m",        
            cpu_quota=100000,          
            read_only=True,            
            tmpfs={'/tmp': '', '/home/appuser': ''}, 
            security_opt=["no-new-privileges"],
            detach=True
        )

        result = container.wait(timeout=15)
        logs = container.logs().decode("utf-8")
        container.remove(force=True)

        files = [f for f in os.listdir(api_workspace) if f != "script.py"]

        return {
            "success": result["StatusCode"] == 0,
            "logs": logs,
            "files": [f"{session_id}/{f}" for f in files]
        }
    except Exception as e:
        return {"success": False, "logs": str(e), "files": []}