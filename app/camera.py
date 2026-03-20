import cv2
import threading
import time

class CameraStream:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.frame = None
        self.lock = threading.Lock()
        thread = threading.Thread(target=self._capture_loop, daemon=True)
        thread.start()

    def _capture_loop(self):
        while True:
            success, frame = self.cap.read()
            if success:
                with self.lock:
                    self.frame = frame
            time.sleep(0.066)

    def get_frame(self):
        with self.lock:
            return self.frame

camera = CameraStream()

def generate_frames():
    while True:
        frame = camera.get_frame()
        if frame is None:
            continue
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n'
            + buffer.tobytes()
            + b'\r\n'
        )
        time.sleep(0.066)
