from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from picamera2 import Picamera2
import io
import threading
import time
import cv2
import numpy as np

app = FastAPI()

class CameraStream:
    def __init__(self):
        self.picam2 = Picamera2()
        self.picam2.configure(self.picam2.create_video_configuration(main={"size": (1280, 720)}))
        self.picam2.start()
        self.frame = None
        self.lock = threading.Lock()
        threading.Thread(target=self._update_frame, daemon=True).start()

    def _update_frame(self):
        while True:
            with self.lock:
                # Capture frame (it will be in BGR format)
                frame = self.picam2.capture_array()
                # Convert BGR to RGB
                self.frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            time.sleep(0.1)  # Adjust based on desired frame rate

    def get_frame(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

camera_stream = CameraStream()

def generate_frames():
    while True:
        frame = camera_stream.get_frame()
        if frame is not None:
            # Convert frame to JPEG
            success, buffer = cv2.imencode('.jpg', frame)
            if success:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.1)  # Adjust based on desired frame rate

@app.get("/mjpeg")
async def mjpeg():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)