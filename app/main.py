"""
Smart Motion Detector v2 - Main Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Smart Motion Detector API",
    version="2.0.0",
    description="Person detection with thermal/color camera support"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production'da değiştir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Smart Motion Detector v2", "status": "ok"}

@app.get("/ready")
async def ready():
    return {"ready": True, "status": "ok"}

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "uptime_s": 0,
        "ai": {"enabled": False, "reason": "not_configured"},
        "cameras": {"online": 0, "retrying": 0, "down": 0},
        "components": {"pipeline": "ok", "telegram": "disabled", "mqtt": "disabled"}
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
