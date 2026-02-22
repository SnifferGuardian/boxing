import cv2
import time
import os
import math
import pandas as pd
import matplotlib.pyplot as plt
from threading import Thread
from ultralytics import YOLO
from flask import Flask, Response

# --- 1. GLOBAL STATE & LOGGING ---
output_frame = None
app = Flask(__name__)

# Data storage for session
punch_data = [] # Stores [timestamp, velocity, extension]
prev_rwrist = None 
prev_time = time.time()

# --- 2. INITIALIZE CAMERA & MODEL ---
print("Step 1: Initializing Camera...")
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("Step 2: Loading AI Model...")
# Using your 11n-pose engine for 110fps performance
model = YOLO("yolo11n-pose.engine", task="pose")

# --- 3. MATH UTILS ---
def get_distance(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

# --- 4. PROCESSING LOOP ---
def detection_loop():
    global output_frame, prev_rwrist, prev_time
    print("Step 3: AI Thread Started...")
    
    while True:
        success, frame = cap.read()
        if not success: continue

        frame = cv2.flip(frame, 1)
        curr_time = time.time()
        dt = curr_time - prev_time
        
        # Inference
        results = model.predict(frame, verbose=False, half=True, imgsz=640)
        annotated_frame = results[0].plot()

        # --- PARKINSON'S DATA EXTRACTION ---
        if results[0].keypoints is not None and len(results[0].keypoints.data) > 0:
            # Keypoint indices: 6 = R Shoulder, 10 = R Wrist
            kpts = results[0].keypoints.data[0]
            
            try:
                r_shoulder = (kpts[6][0].item(), kpts[6][1].item())
                r_wrist = (kpts[10][0].item(), kpts[10][1].item())
                conf = kpts[10][2].item()

                if conf > 0.5:
                    # 1. Calculate Extension (Shoulder to Wrist)
                    extension = get_distance(r_shoulder, r_wrist)
                    
                    # 2. Calculate Velocity (Change in wrist pos / time)
                    velocity = 0
                    if prev_rwrist is not None and dt > 0:
                        dist_moved = get_distance(r_wrist, prev_rwrist)
                        velocity = dist_moved / dt # pixels per second
                    
                    prev_rwrist = r_wrist
                    prev_time = curr_time

                    # 3. Detect "Active Punch" (e.g., if velocity > threshold)
                    if velocity > 500: # Adjust this threshold based on testing
                        punch_data.append([curr_time, velocity, extension])
                        cv2.putText(annotated_frame, "PUNCH DETECTED!", (200, 450), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

                    # Display metrics on screen for Grandpa
                    cv2.putText(annotated_frame, f"Extension: {int(extension)}px", (20, 80), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            except Exception as e:
                pass

        # FPS Counter
        inf_ms = results[0].speed['inference']
        fps = 1000/inf_ms if inf_ms > 0 else 0
        cv2.putText(annotated_frame, f"AI FPS: {int(fps)}", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Convert to JPEG for Web Stream
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        if ret:
            output_frame = buffer.tobytes()

# --- 5. WEB SERVER ---
@app.route('/video_feed')
def video_feed():
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

def generate():
    global output_frame
    while True:
        if output_frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + output_frame + b'\r\n')
        time.sleep(0.01) # Low sleep to maintain high-speed visual feel

# --- 6. DATA PLOTTING (RUNS ON EXIT) ---
def save_and_plot():
    if not punch_data:
        print("No punches recorded this session.")
        return
    
    df = pd.DataFrame(punch_data, columns=['Timestamp', 'Velocity', 'Extension'])
    df.to_csv("grandpa_progress.csv", index=False)
    print(f"Data saved to grandpa_progress.csv. Recorded {len(df)} punch samples.")

    # Create the Progress Screen
    plt.style.use('ggplot')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    
    ax1.plot(df['Timestamp'] - df['Timestamp'].min(), df['Velocity'], color='blue', linewidth=2)
    ax1.set_title("Punch Speed (Fighting Slowness)")
    ax1.set_ylabel("Velocity (px/s)")

    ax2.plot(df['Timestamp'] - df['Timestamp'].min(), df['Extension'], color='green', linewidth=2)
    ax2.set_title("Arm Extension (Fighting Stiffness)")
    ax2.set_ylabel("Reach (px)")
    ax2.set_xlabel("Session Time (seconds)")

    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    try:
        t = Thread(target=detection_loop, daemon=True)
        t.start()
        
        print("Step 4: Server online at http://localhost:5000/video_feed")
        app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\nSession Ended by User.")
    finally:
        save_and_plot()
        cap.release()