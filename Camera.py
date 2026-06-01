import os
import sys
import cv2
import mysql.connector
import time
import threading
import shutil
from datetime import datetime
from nudenet import NudeDetector


# ==========================================
# ADVANCED PYINSTALLER COMPATIBILITY LAYER
# ==========================================
def initialize_failsafe_detector():
    """
    Forces the application to construct a permanent, uncorrupted directory
    outside of PyInstaller's volatile temporary '_MEIxxxx' space.
    """
    home_dir = os.path.expanduser("~")
    permanent_nudenet_dir = os.path.join(home_dir, ".nudenet")
    os.makedirs(permanent_nudenet_dir, exist_ok=True)

    permanent_model_path = os.path.join(permanent_nudenet_dir, "320n.onnx")

    # Case A: Running as a compiled PyInstaller EXE
    if hasattr(sys, '_MEIPASS'):
        extracted_model_source = os.path.join(sys._MEIPASS, "nudenet", "320n.onnx")
        if os.path.exists(extracted_model_source) and not os.path.exists(permanent_model_path):
            try:
                shutil.copy2(extracted_model_source, permanent_model_path)
                print("[System]: Successfully cloned AI weights to stable user environment.")
            except Exception as e:
                print(f"[Warning]: File migration notice: {e}")

    # Case B: Running raw in PyCharm
    else:
        pycharm_venv_source = r"C:\Users\Misha\PycharmProjects\PythonProject\.venv\Lib\site-packages\nudenet\320n.onnx"
        if os.path.exists(pycharm_venv_source) and not os.path.exists(permanent_model_path):
            try:
                shutil.copy2(pycharm_venv_source, permanent_model_path)
            except:
                pass

    if os.path.exists(permanent_model_path):
        print(f"[System]: Deploying AI Engine from stable path: {permanent_model_path}")
        return NudeDetector(model_path=permanent_model_path)
    else:
        print("[System]: Stable weight file not found. Initializing auto-download engine fallback...")
        return NudeDetector()


# ======================
# TARGET GALLERY FOLDER
# ======================
TARGET_FOLDER = r"C:\Users\Misha\PycharmProjects\PythonProject"
os.makedirs(TARGET_FOLDER, exist_ok=True)

# ======================
# MYSQL DATABASE CONFIG
# ======================
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Ersha@123",
    database="camera_monitor"
)
cursor = db.cursor()
print("Database Connected Successfully.")

# Initialize the detector
detector = initialize_failsafe_detector()

BLOCK_CLASSES = {
    "FEMALE_BREAST_EXPOSED",
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "BUTTOCKS_EXPOSED",
    "ANUS_EXPOSED",
    "EXPOSED_VULVA",
    "EXPOSED_GENITALIA",
    "EXPOSED_BUTTOCKS"
}

# ======================
# HARDWARE SELECTION LAYER
# ======================
# Forcing manual camera indexing 0 (front/primary) and 1 (back/secondary)
AVAILABLE_CAMERAS = [0, 1]
current_list_pointer = 0
current_camera_index = AVAILABLE_CAMERAS[current_list_pointer]

PLATFORM_BACKEND = cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_ANY
cap = cv2.VideoCapture(current_camera_index, PLATFORM_BACKEND)

video_writer = None
recording = False
take_photo = False
exit_app = False
press_time = None

# Threading control states
detection_frame = None
blocked = False
is_processing = False


# ======================
# SAVE LOGS TO DATABASE
# ======================
def save_log(status, media_type):
    try:
        cursor.execute(
            """
            INSERT INTO detection_logs (event_time, status, video_type)
            VALUES (%s, %s, %s)
            """,
            (datetime.now(), status, media_type)
        )
        db.commit()
    except mysql.connector.Error as err:
        print(f"Database Log Error: {err}")


# ======================
# ASYNC AI WORKER THREAD
# ======================
def ai_detection_worker():
    global blocked, is_processing, detection_frame

    while not exit_app:
        if detection_frame is not None and not is_processing:
            is_processing = True
            local_frame = detection_frame.copy()

            try:
                success, encoded_img = cv2.imencode('.jpg', local_frame)
                if success:
                    result = detector.detect(encoded_img.tobytes())

                    for r in result:
                        label = r["class"]
                        score = r["score"]

                        # Sensitivity optimized to 0.70 to handle fast motion/low angles
                        if label in BLOCK_CLASSES and score > 0.70:
                            blocked = True
                            print(f"\n[⚠️ RESTRICTED CONTENT DETECTED]: {label} ({score:.2f})")
                            break
            except Exception as e:
                print(f"Detection pipeline notice: {e}")

            is_processing = False
        time.sleep(0.03)


threading.Thread(target=ai_detection_worker, daemon=True).start()


# ======================
# SWITCH CAMERA LOGIC
# ======================
def switch_camera():
    global cap, current_list_pointer, current_camera_index, video_writer, recording

    print("[System]: Re-routing hardware feeds smoothly...")

    if recording:
        recording = False
        if video_writer is not None:
            video_writer.release()
            video_writer = None
        save_log("Allowed", "Normal Video (Camera Switched)")

    current_list_pointer = (current_list_pointer + 1) % len(AVAILABLE_CAMERAS)
    current_camera_index = AVAILABLE_CAMERAS[current_list_pointer]

    cap.release()
    cap = cv2.VideoCapture(current_camera_index, PLATFORM_BACKEND)
    time.sleep(0.3)


# ======================
# INTERACTIVE MOUSE CALLBACK
# ======================
def handle_mouse_click(event, x, y, flags, param):
    global press_time, recording, video_writer, take_photo, exit_app

    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"[Debug Click]: Registered click at position X: {x}, Y: {y}")

    # MAIN SHUTTER BUTTON (Center-Bottom)
    if 225 < x < 275 and 395 < y < 445:
        if event == cv2.EVENT_LBUTTONDOWN:
            press_time = time.time()

        elif event == cv2.EVENT_LBUTTONUP and press_time is not None:
            duration = time.time() - press_time
            press_time = None

            if duration < 1.5:
                take_photo = True
            else:
                if recording:
                    recording = False
                    if video_writer is not None:
                        video_writer.release()
                        video_writer = None
                    save_log("Allowed", "Normal Video")
                    print("[System]: Video capture saved successfully.")
                else:
                    recording = True
                    print("[System]: Video recording initialized.")

    # FLIP/SWITCH CAMERA BUTTON (Top-Right Area)
    if event == cv2.EVENT_LBUTTONDOWN and 540 < x < 620 and 20 < y < 50:
        switch_camera()

    # QUIT UI BUTTON (Top-Left Area)
    if event == cv2.EVENT_LBUTTONDOWN and 20 < x < 70 and 20 < y < 50:
        print("[System]: Exit click registered on screen button.")
        exit_app = True


# Create workspace window surface
cv2.namedWindow("Smart Camera")
cv2.setMouseCallback("Smart Camera", handle_mouse_click)
print("Camera Window Running...")

# ======================
# APPLICATION MAIN LOOP
# ======================
while True:
    ret, frame = cap.read()
    if not ret:
        if exit_app:
            break
        time.sleep(0.1)
        continue

    if not is_processing:
        detection_frame = frame.copy()

    key = cv2.waitKey(1) & 0xFF
    if key == ord("n"):
        blocked = True
        print("\n[TEST MODE OVERRIDE TRIGGERED]")

    # CRITICAL BLOCK PIPELINE HANDLING
    if blocked:
        save_log("Blocked", "Nude Video")
        if video_writer is not None:
            video_writer.release()
            video_writer = None
        print("[System Shutdown]: Feed terminated due to restricted environment markers.")
        break

    # PHOTO CAPTURE PIPELINE (AUTOMATED ROUTING)
    if take_photo:
        filename = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        full_save_path = os.path.join(TARGET_FOLDER, filename)

        cv2.imwrite(full_save_path, frame)
        save_log("Allowed", "Photo")
        print(f"[Success]: Photo auto-routed to -> {full_save_path}")
        take_photo = False

    # VIDEO CAPTURE PIPELINE (AUTOMATED ROUTING)
    if recording:
        if video_writer is None:
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            filename = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.avi"
            full_save_path = os.path.join(TARGET_FOLDER, filename)

            video_writer = cv2.VideoWriter(
                full_save_path,
                cv2.VideoWriter_fourcc(*"XVID"),
                20.0,
                (width, height)
            )
            print(f"[System]: Video path active -> {full_save_path}")

        video_writer.write(frame)

    # ------------------
    # DRAW INTERACTIVE UI LAYER
    # ------------------
    display_frame = frame.copy()

    # Draw Close Button (Top Left)
    cv2.rectangle(display_frame, (20, 20), (70, 50), (0, 0, 255), -1)
    cv2.putText(display_frame, "X", (37, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    # Force drawing the FLIP button on screen permanently
    cv2.rectangle(display_frame, (540, 20), (620, 50), (200, 100, 0), -1)
    cv2.putText(display_frame, "FLIP", (555, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    # Draw Shutter Button Ring (Bottom Center)
    button_color = (0, 0, 255) if recording else (255, 255, 255)
    cv2.circle(display_frame, (250, 420), 25, button_color, -1)
    cv2.circle(display_frame, (250, 420), 28, (0, 0, 0), 2)

    if recording:
        cv2.putText(display_frame, "• REC", (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    cv2.imshow("Smart Camera", display_frame)

    # Failsafe Exit Break checks (X button click, ESC key, or 'q' key)
    if exit_app or key == 27 or key == ord('q'):
        print("[System]: Termination sequence active. Closing camera loop...")
        break

# ======================
# TEARDOWN & RECOVERY PROCEDURES
# ======================
exit_app = True
cap.release()
if video_writer is not None:
    video_writer.release()
cv2.destroyAllWindows()

cursor.close()
db.close()
print("Execution Space Finished Cleanly.")