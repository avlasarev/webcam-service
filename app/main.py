from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from camera import generate_frames

app = FastAPI()

@app.get("/stream")
def stream():
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/health")
def health():
    return {"status": "ok"}