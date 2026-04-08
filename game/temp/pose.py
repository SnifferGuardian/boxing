import subprocess
import sys
import cv2
import time
import os
import math
import pandas as pd
import matplotlib.pyplot as plt
import signal
from ultralytics import YOLO

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
save_path = os.path.join(BASE_DIR, "save.txt")
extend_path = os.path.join(BASE_DIR, "extend.txt")
stop_signal_path = os.path.join(BASE_DIR, "stop_signal.txt")
graph_path = os.path.join(BASE_DIR, "split_performance_graph.png")
MODEL_PATH = os.path.join(BASE_DIR, "yolo11n-pose.engine")

for p in [save_path, extend_path]:
    with open(p, "w") as f:
        f.close()

if os.path.exists(stop_signal_path):
    os.remove(stop_signal_path)

punch_data = [] 
prev_rwrist = None 
prev_time = time.time() 

def run_final_processing():
    try:
        if os.path.exists(save_path):
            with open(save_path, "r") as f:
                velocities = [float(l.strip()) for l in f if l.strip()]
            if velocities:
                with open(os.path.join(BASE_DIR, "avg.txt"), "a") as f_v:
                    f_v.write(f"{sum(velocities)/len(velocities):.2f}\n")

        if os.path.exists(extend_path):
            with open(extend_path, "r") as f:
                extensions = [float(l.strip()) for l in f if l.strip()]
            if extensions:
                with open(os.path.join(BASE_DIR, "exvg.txt"), "a") as f_e:
                    f_e.write(f"{sum(extensions)/len(extensions):.2f}\n")
        print("Averages saved.")
    except Exception as e:
        print(f"Average calc error: {e}")

    try:
        process_script = os.path.join(BASE_DIR, "process.py")
        print(f"Attempting to run process script at: {process_script}")
        subprocess.run([sys.executable, process_script], check=True)
        print("process.py finished successfully.")
    except Exception as e:
        print(f"process.py failed: {e}")

def save_and_plot():
    if not punch_data:
        print("No punches recorded this session.")
        return
    
    df = pd.DataFrame(punch_data, columns=['Timestamp', 'Velocity', 'Extension'])
    csv_path = os.path.join(BASE_DIR, "grandpa_progress.csv")
    df.to_csv(csv_path, index=False)

    plt.figure("Current Session Performance", figsize=(10, 8))
    plt.style.use('ggplot')
    
    plt.subplot(2, 1, 1)
    plt.plot(df['Timestamp'] - df['Timestamp'].min(), df['Velocity'], color='blue', linewidth=2)
    plt.title("Current Session: Punch Speed")
    plt.ylabel("Velocity (px/s)")

    plt.subplot(2, 1, 2)
    plt.plot(df['Timestamp'] - df['Timestamp'].min(), df['Extension'], color='green', linewidth=2)
    plt.title("Current Session: Arm Extension")
    plt.ylabel("Reach (px)")
    plt.xlabel("Time (seconds)")

    plt.tight_layout()
    plt.savefig(graph_path) 
    print("Opening Session Graph Window...")
    plt.show()

def get_distance(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def main():
    global punch_data, prev_rwrist, prev_time
    
    print("Initializing Camera...")
    cv2.namedWindow("Boxing AI Live Stream", cv2.WINDOW_NORMAL) 
    cv2.setWindowProperty("Boxing AI Live Stream", cv2.WND_PROP_TOPMOST, 1) 
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print(f"Loading AI Model from: {MODEL_PATH}")
    #subprocess.run(["python", "temp/power_reaction_perc.py"])
    model = YOLO(MODEL_PATH, task="pose")

    try:
        while True:
            success, frame = cap.read()
            if not success: 
                break

            frame = cv2.flip(frame, 1)
            curr_time = time.time()
            dt = curr_time - prev_time
            
            results = model.predict(frame, verbose=False, half=True, imgsz=640)
            annotated_frame = results[0].plot()

            if results[0].keypoints is not None and len(results[0].keypoints.data) > 0:
                kpts = results[0].keypoints.data[0]
                try:
                    r_shoulder = (kpts[6][0].item(), kpts[6][1].item())
                    r_wrist = (kpts[10][0].item(), kpts[10][1].item())
                    conf = kpts[10][2].item()

                    if conf > 0.5:
                        extension = get_distance(r_shoulder, r_wrist)
                        velocity = 0
                        if prev_rwrist is not None and dt > 0:
                            dist_moved = get_distance(r_wrist, prev_rwrist)
                            velocity = dist_moved / dt
                        
                        prev_rwrist = r_wrist
                        prev_time = curr_time

                        if velocity > 500:
                            punch_data.append([curr_time, velocity, extension])
                            with open(save_path, "a") as f: 
                                f.write(f"{velocity:.2f}\n")
                            with open(extend_path, "a") as f: 
                                f.write(f"{extension:.2f}\n")
                            
                            cv2.putText(annotated_frame, "PUNCH DETECTED!", (200, 450), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

                        cv2.putText(annotated_frame, f"Extension: {int(extension)}px", (20, 80), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                except Exception:
                    pass

            inf_ms = results[0].speed['inference']
            fps = 1000/inf_ms if inf_ms > 0 else 0
            cv2.putText(annotated_frame, f"AI FPS: {int(fps)}", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(annotated_frame, "Press 'q' to Quit", (450, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

            cv2.imshow("Boxing AI Live Stream", annotated_frame)
            cv2.resizeWindow("Boxing AI Live Stream", 1000, 750)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                # subprocess.Popen([sys.executable, "temp/power_reaction_perc.py"])
                break

    except KeyboardInterrupt:
        pass
    finally:
        print("\nClosing AI and generating reports...")
        cap.release()
        cv2.destroyAllWindows()
        save_and_plot()
        run_final_processing()
        print("Exiting...")
        subprocess.run(["python", "temp/stop_ai.py"])
    

if __name__ == '__main__':
    main()