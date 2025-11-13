from fastapi import FastAPI, UploadFile, File, Form 
from fastapi.responses import HTMLResponse
from pathlib import Path
import shutil
from ultralytics import YOLO # YOLO library import
import base64 
import numpy as np 
import cv2 

# ==============================
# Setup
# ==============================
app = FastAPI()
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# 🛑 आपकी Custom Model का Path
CUSTOM_MODEL_PATH = Path("runs/train/cctv_yolov8/weights/best.pt")

# Load YOLO trained model
try:
    if CUSTOM_MODEL_PATH.exists():
        # 1. Custom model को load करने का प्रयास
        model = YOLO(str(CUSTOM_MODEL_PATH))
        print(f"YOLO model '{CUSTOM_MODEL_PATH}' loaded successfully from local file.")
    else:
        # 2. अगर Custom model नहीं मिला, तो crash से बचने के लिए generic model का उपयोग करें।
        # NOTE: If you want to use your custom model, ensure the 'runs' directory and 'best.pt' 
        # are committed to your Git repository.
        model = YOLO("yolov8n.pt") 
        print(f"⚠️ WARNING: Custom model not found at {CUSTOM_MODEL_PATH}. Using generic 'yolov8n.pt' as fallback for stability.")

except Exception as e:
    # 3. Critical failure handler
    print(f"CRITICAL ERROR: Failed to load any YOLO model: {e}")
    # Dummy Model class definition to prevent app crash
    class DummyModel:
        def predict(self, data, save=False, verbose=False):
            return []
        def __init__(self):
            # This is a dummy object, it needs the 'names' attribute for the prediction logic not to crash
            self.names = {0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle', 4: 'airplane'}
            
    model = DummyModel()


# ==============================
# Frontend HTML (Testing/Root Access)
# ==============================
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CCTV AI Monitor</title>
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
<p>This is the test page. The Flutter app sends data to /analyze_frame (using Form Data).</p>
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

# 1. Video Upload Route 
@app.post("/upload_video/")
async def upload_video(file: UploadFile = File(...)):
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Predict using YOLO 
    results = model.predict(str(file_path), save=False)

    # Unique detected classes
    detected_classes = set()
    # Ensure model is not the DummyModel before accessing 'names'
    if hasattr(model, 'names'):
        for r in results:
            detected_classes.update([model.names[int(cls)] for cls in r.boxes.cls])

    if detected_classes:
        alert_msg = f"ALERT! Detected: {', '.join(detected_classes)}"
    else:
        alert_msg = "Safe: No threat detected."

    return {"alert_status": alert_msg}


# 2. Frame Analysis Route (Uses Form/Column data)
@app.post("/analyze_frame")
async def analyze_frame(image: str = Form(...), camera_id: str = Form(...)):
    """
    Accepts Base64 image and camera_id as form data (columns).
    """
    try:
        # 1. Base64 Decode
        image_bytes = base64.b64decode(image)
        
        # 2. Convert to OpenCV Image (Numpy Array)
        np_arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return {"alert_status": "Error: Frame decode failed (Invalid Image Data)"}
        
        # 3. AI Analysis (YOLO)
        results = model.predict(frame, save=False, verbose=False) 
        
        # 4. Extract Results 
        detected_classes = set()
        # Ensure model is not the DummyModel before accessing 'names'
        if hasattr(model, 'names'):
            for r in results:
                detected_classes.update([model.names[int(cls)] for cls in r.boxes.cls])

        if detected_classes:
            alert_msg = f"ALERT! Detected: {', '.join(detected_classes)} on Camera {camera_id}"
        else:
            alert_msg = f"Safe: No threat detected on Camera {camera_id}"

        # 5. Return result in the expected format for Flutter
        return {"alert_status": alert_msg}
    
    except Exception as e:
        print(f"Error during form data frame analysis: {e}")
        return {"alert_status": f"AI Backend Error (Check Server Logs)"}
