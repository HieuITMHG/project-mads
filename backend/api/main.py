from fastapi import FastAPI
from routes import chat

app = FastAPI(title="This is my fucking api")

app.include_router(chat.router)

@app.get("/")
def health_check():
    return {"status": "ok", "service": "running"}