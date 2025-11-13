from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pathlib import Path
import shutil
from ultralytics import YOLO
import base64 # Base64 Decoding के लिए
import numpy as np # Byte Array Handling के लिए
import cv2 # cv2.imdecode के लिए (Numpy array को image में बदलना)
import json # हालांकि FastAPI JSON को सीधे संभालता है, यह import अच्छा है

# ==============================
# Setup
# ==============================
app = FastAPI()
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
# **मॉडल पाथ को सही करें** - सुनिश्चित करें कि यह पाथ Render पर मौजूद है।
MODEL_PATH = Path("runs/train/cctv_yolov8/weights/best.pt")

# Load YOLO trained model
try:
    model = YOLO(str(MODEL_PATH))
    print("YOLO model loaded successfully.")
except Exception as e:
    print(f"Error loading YOLO model: {e}")
    # Fallback/Dummy model if real one fails to load
    class DummyModel:
        def predict(self, data, save=False, verbose=False):
            return []
    model = DummyModel()


# Pydantic Model for incoming JSON from Flutter
class ImagePayload(BaseModel):
    image: str
    camera_id: str


# ==============================
# Frontend HTML (Testing/Root Access)
# ==============================
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CCTV Video Alert</title>
<style>
body { font-family: Arial; text-align:center; margin-top:50px; background-color: #f0f4f8; }
h1 { color: #2c3e50; }
input, button { margin:10px; padding:12px 20px; font-size:16px; border-radius: 8px; border: none; cursor: pointer; transition: background-color 0.3s; }
button { background-color: #3498db; color: white; }
button:hover { background-color: #2980b9; }
#alert-box { margin-top:20px; padding: 15px; font-size:18px; font-weight:bold; border-radius: 8px; background-color: #ecf0f1; border: 2px solid transparent; }
.alert-safe { color: #27ae60; border-color: #2ecc71; }
.alert-error { color: #c0392b; border-color: #e74c3c; }
video { margin-top:20px; max-width:80%; height:auto; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
</style>
</head>
<body>
<h1>CCTV Video Upload & Alert Test</h1>
<p>This endpoint is for testing file uploads. The Flutter app uses /analyze_frame.</p>
<input type="file" id="videoFile" accept="video/*"><br>
<button onclick="uploadVideo()">Upload & Check</button>
<div id="alert-box"></div>
<video id="video-preview" controls></video>

<script>
async function uploadVideo() {
    const fileInput = document.getElementById('videoFile');
    const file = fileInput.files[0];
    if (!file) { alert("Select a video first!"); return; }

    const videoPreview = document.getElementById('video-preview');
    videoPreview.src = URL.createObjectURL(file);

    const formData = new FormData();
    formData.append('file', file);
    const alertBox = document.getElementById('alert-box');
    alertBox.className = '';
    alertBox.innerText = "Processing video...";

    try {
        const response = await fetch('/upload_video/', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const data = await response.json();
            // Flutter के साथ consistency के लिए alert_status का उपयोग करें
            alertBox.innerText = data.alert_status; 
             if (data.alert_status.includes("ALERT")) {
                alertBox.classList.add('alert-error');
             } else {
                alertBox.classList.add('alert-safe');
             }
        } else {
            alertBox.innerText = "Upload failed! Status: " + response.status;
             alertBox.classList.add('alert-error');
        }
    } catch (error) {
        alertBox.innerText = "Error connecting to server.";
        alertBox.classList.add('alert-error');
        console.error(error);
    }
}
</script>
</body>
</html>
"""

# ==============================
# Routes
# ==============================
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    return HTML_CONTENT

# 1. Video Upload Route (Original, modified to return 'alert_status')
@app.post("/upload_video/")
async def upload_video(file: UploadFile = File(...)):
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Predict using YOLO 
    # Note: YOLO model.predict on video can be very slow.
    results = model.predict(str(file_path), save=False)

    # Unique detected classes
    detected_classes = set()
    for r in results:
        detected_classes.update([r.names[int(cls)] for cls in r.boxes.cls])

    if detected_classes:
        alert_msg = f"ALERT! Detected: {', '.join(detected_classes)}"
    else:
        alert_msg = "Safe: No threat detected."

    # Flutter compatibility के लिए alert_status key का उपयोग करें
    return {"alert_status": alert_msg}


# 2. Frame Analysis Route (NEW - for Flutter App)
@app.post("/analyze_frame")
async def analyze_frame(payload: ImagePayload):
    """
    Accepts JSON payload from Flutter, decodes Base64 image, runs YOLO on the frame.
    """
    try:
        # 1. Base64 Decode
        image_bytes = base64.b64decode(payload.image)
        
        # 2. Convert to OpenCV Image (Numpy Array)
        # imdecode uses numpy array to convert bytes into an image
        np_arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            # If imdecode fails, it means the bytes were not a valid image format (like PNG/JPEG)
            return {"alert_status": "Error: Frame decode failed (Invalid Image Data)"}
        
        # 3. AI Analysis (YOLO)
        # We pass the NumPy array (frame) directly to model.predict
        results = model.predict(frame, save=False, verbose=False) 
        
        # 4. Extract Results (Reusing the logic from /upload_video/)
        detected_classes = set()
        for r in results:
            detected_classes.update([r.names[int(cls)] for cls in r.boxes.cls])

        if detected_classes:
            alert_msg = f"ALERT! Detected: {', '.join(detected_classes)} on Camera {payload.camera_id}"
        else:
            alert_msg = f"Safe: No threat detected on Camera {payload.camera_id}"

        # 5. Return result in the expected format for Flutter
        return {"alert_status": alert_msg}
    
    except Exception as e:
        print(f"Error during frame analysis from camera {payload.camera_id}: {e}")
        return {"alert_status": f"AI Backend Error (Check Server Logs)"}
