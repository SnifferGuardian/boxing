import librosa
import numpy as np
import pygame
import time
import cv2
import math
import random
import serial
import threading
import os


if not os.path.exists("temp"):
    os.makedirs("temp")

try:
    ser = serial.Serial('COM5', 115200, timeout=1)
except Exception as e:
    print(f"Serial Error auto.py: {e}")
    ser = None

def send_to_arduino(pin, color, duration):
    if ser and ser.is_open:
        cmd = f"{pin},{color},{duration}\n"
        ser.write(cmd.encode())

# --- Score Tracker ---
class ScoreTracker:
    def __init__(self):
        self.current_total = 0.0
    def update(self, raw_input):
        try:
            parts = str(raw_input).split(",")
            if len(parts) >= 1:
                self.current_total += float(parts[0])
                # Write to file so app.py can read it
                with open("temp/current_score.txt", "w") as f:
                    f.write(str(self.current_total))
        except ValueError:
            pass

tracker = ScoreTracker()

def serial_listener():
    while True:
        if ser and ser.in_waiting > 0:
            try:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    tracker.update(line)
            except Exception as e:
                print(f"Read error: {e}")
        time.sleep(0.01)

threading.Thread(target=serial_listener, daemon=True).start()

# --- Game Logic ---
with open('song_file.txt', 'r') as f:
    AUDIO_FILE = f.read().strip()

LANE_COUNT = 12
SENSITIVITY = 0.1
HOP = 96
OFFSET = 0.06 
SHOOT_TIME = 1.0   
CIRCLE_SIZE = 70   

y, sr = librosa.load(AUDIO_FILE)
onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
peaks = librosa.util.peak_pick(onset_env, pre_max=2, post_max=2, pre_avg=3, post_avg=3, delta=SENSITIVITY, wait=5)
beat_times = librosa.frames_to_time(peaks, sr=sr, hop_length=HOP)
chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=HOP)

lane_assignments = [np.argmax(chroma[:, min(frame, chroma.shape[1] - 1)]) for frame in peaks]

pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
pygame.mixer.music.load(AUDIO_FILE)
pygame.mixer.music.play()

width, height = 1000, 1000
center = (width // 2, height // 2)
max_radius = width // 2 - 80
window_name = "Automatic Radial Symphony"
cv2.namedWindow(window_name)

active_bullets = []
game_start_time = time.time()
beat_index = 0

try:
    while pygame.mixer.music.get_busy():
        elapsed = time.time() - game_start_time
        
        # Beat/Bullet Logic
        if beat_index < len(beat_times) and elapsed >= (beat_times[beat_index] - SHOOT_TIME - OFFSET):
            lane = lane_assignments[beat_index]
            active_bullets.append([lane, elapsed, False])
            beat_index += 1
            
            # Direct Serial Command (Replaces cmd.txt)
            send_to_arduino(random.randint(0, 3), 'R' if random.randint(1, 4) == 1 else 'G', 700)

        # Drawing
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        new_bullet_list = []
        for bullet in active_bullets:
            lane, start_time, has_played = bullet
            progress = (elapsed - start_time) / SHOOT_TIME
            
            if progress < 1.1:
                angle = (lane / LANE_COUNT) * 2 * math.pi
                curr_dist = min(progress, 1.0) * max_radius
                x, y_pos = int(center[0] + curr_dist * math.cos(angle)), int(center[1] + curr_dist * math.sin(angle))
                
                size = int(CIRCLE_SIZE * progress)
                cv2.circle(frame, (x, y_pos), max(5, size), (255, 150, 0), -1)
                new_bullet_list.append(bullet)
        
        active_bullets = new_bullet_list
        cv2.imshow(window_name, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

except KeyboardInterrupt:
    pass

pygame.mixer.music.stop()
cv2.destroyAllWindows()