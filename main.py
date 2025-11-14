from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil
from ultralytics import YOLO

# ==============================
# Setup
# ==============================
app = FastAPI()

# 🔥 CORS FIX (upload failed ka main reason yahi tha)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Model path (FIXED)
MODEL_PATH = Path("runs/train/cctv_yolov8/weights/best.pt")

# Load Model
try:
    model = YOLO(str(MODEL_PATH))
except Exception as e:
    print("❌ Model Load Error:", e)
    model = None


# ==============================
# Frontend HTML
# ==============================
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CCTV Video Alert</title>
<style>
body { font-family: Arial; text-align:center; margin-top:50px; }
input, button { margin:10px; padding:10px; font-size:16px; }
#alert-box { margin-top:20px; font-size:18px; font-weight:bold; color:red; }
video { margin-top:20px; max-width:80%; height:auto; }
</style>
</head>
<body>
<h1>CCTV Video Upload & Alert Test</h1>
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
    alertBox.innerText = "Processing video...";

    try {
        const response = await fetch('/upload_video/', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        alertBox.innerText = data.alert || "Upload failed!";

    } catch (error) {
        alertBox.innerText = "Error connecting to server.";
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


@app.post("/upload_video/")
async def upload_video(file: UploadFile = File(...)):

    # Handle model load error
    if model is None:
        return {"alert": "❌ Model not loaded. Check server logs."}

    file_path = UPLOAD_DIR / file.filename

    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        return {"alert": f"❌ File save error: {e}"}

    # Run prediction
    try:
        results = model.predict(str(file_path), save=False)
    except Exception as e:
        return {"alert": f"❌ Prediction error: {e}"}

    detected_classes = set()
    for r in results:
        for cls in r.boxes.cls:
            detected_classes.add(r.names[int(cls)])

    if detected_classes:
        alert_msg = f"ALERT! Detected: {', '.join(detected_classes)}"
    else:
        alert_msg = "No threat detected."

    return {"alert": alert_msg}


# ==============================
# Run (Local)
# ==============================
# uvicorn main:app --reload
