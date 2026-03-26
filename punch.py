import cv2
import numpy as np
import time
from pynput.keyboard import Key, Controller
from ultralytics import YOLO

# 1. Initialize Keyboard Controller (Better for games than PyAutoGUI)
keyboard = Controller()

# 2. Load the Engine
# Make sure this path is correct for your setup
model = YOLO("temp/yolo11n-pose.engine", task="pose")

# 3. Settings
PUNCH_THRESHOLD = 0.5  # Distance between shoulder and wrist
is_punching = False     # State tracker

# 4. Camera Setup
# Use CAP_DSHOW on Windows for faster initialization and lower lag
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # Crucial: Don't queue old frames
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("--- PUNCH TO JUMP ACTIVE ---")
print("Using 640x640 inference to match your Engine file.")

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    # Flip for natural 'mirror' movement
    frame = cv2.flip(frame, 1)

    # 5. Run Inference 
    # CRITICAL: imgsz must be 640 to match your specific .engine file
    results = model(frame, imgsz=640, verbose=False, stream=True, conf=0.5)

    punch_detected = False

    for r in results:
        if r.keypoints is not None:
            # xyn = normalized coordinates (0.0 to 1.0)
            kpts = r.keypoints.xyn.cpu().numpy()
            
            if len(kpts) > 0:
                person = kpts[0] # Focus on the first person detected
                if len(person) >= 11:
                    # Keypoints: 5=L_Shoulder, 6=R_Shoulder, 9=L_Wrist, 10=R_Wrist
                    ls, rs = person[5], person[6]
                    lw, rw = person[9], person[10]

                    # Check Right Arm or Left Arm extension
                    r_ext = np.linalg.norm(rs - rw)
                    l_ext = np.linalg.norm(ls - lw)

                    if r_ext > PUNCH_THRESHOLD or l_ext > PUNCH_THRESHOLD:
                        punch_detected = True

    # 6. Keyboard Logic (Edge Detection)
    if punch_detected and not is_punching:
        keyboard.press(Key.space)
        is_punching = True
        print(">> JUMP (Space Down)")
    elif not punch_detected and is_punching:
        keyboard.release(Key.space)
        is_punching = False
        print(".. RELEASE (Space Up)")

    # 7. Visual Feedback
    display_color = (0, 255, 0) if is_punching else (0, 0, 255)
    cv2.putText(frame, f"PUNCH: {is_punching}", (20, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, display_color, 3)
    
    cv2.imshow("Geometry Dash AI Controller", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
if is_punching:
    keyboard.release(Key.space)
cap.release()
cv2.destroyAllWindows()  