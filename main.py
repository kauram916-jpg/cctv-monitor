from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from ultralytics import YOLO
import shutil
import time

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "frames"
UPLOAD_DIR.mkdir(exist_ok=True)

# Load Model
MODEL_PATH = Path("runs/train/cctv_yolov8/weights/best.pt")
try:
    model = YOLO(str(MODEL_PATH))
    print("✅ YOLO Model Loaded Successfully")
except Exception as e:
    print("❌ Model Load Error:", e)
    model = None

# ============================
# GLOBAL COOLDOWN VARIABLES
# ============================
cooldown_active = False
last_detection_time = 0
COOLDOWN_DURATION = 120   # 2 minutes


@app.post("/predict/")
async def predict_frame(frame: UploadFile = File(...)):
    global cooldown_active, last_detection_time

    # 1️⃣ Check model available
    if model is None:
        return {"status": "MODEL_ERROR"}

    # 2️⃣ Check cooldown
    if cooldown_active:
        if time.time() - last_detection_time < COOLDOWN_DURATION:
            return {"status": "COOLDOWN_ACTIVE"}
        else:
            cooldown_active = False  # Cooldown reset

    # 3️⃣ Save uploaded image temporarily
    frame_path = UPLOAD_DIR / frame.filename
    try:
        with open(frame_path, "wb") as buffer:
            shutil.copyfileobj(frame.file, buffer)
    except:
        return {"status": "FILE_SAVE_ERROR"}

    # 4️⃣ Run YOLO on image
    try:
        results = model.predict(str(frame_path), save=False)
    except Exception as e:
        print("Prediction Error:", e)
        return {"status": "PREDICTION_ERROR"}

    # 5️⃣ Extract detected classes
    detected_classes = set()
    for r in results:
        for cls in r.boxes.cls:
            detected_classes.add(r.names[int(cls)])

    # 6️⃣ If any object detected → ALERT + Cooldown on
    if detected_classes:
        cooldown_active = True
        last_detection_time = time.time()

        return {
            "status": "DETECTED",
            "objects": list(detected_classes)
        }

    # 7️⃣ No detection
    return {"status": "SAFE"}
