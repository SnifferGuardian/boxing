import librosa
import numpy as np
import pygame
import time
import cv2
import math
import random
import os
from ultralytics import YOLO
import matplotlib.pyplot as plt
with open('difficulty.txt', 'r') as f:
    content = f.read()
    content_int = float(content)
    print(content_int)

AUDIO_FILE = 'GeometryDash/Back On Track.mp3'  
MODEL_PATH = 'temp/yolo11n-pose.engine'  
LANE_COUNT = 12

try:
    with open('difficulty.txt', 'r') as f:
        content_int = float(f.read())
except:
    content_int = 1.0

SENSITIVITY = 2.00 - content_int 
HOP = 128
OFFSET = 0.06 

BASE_SHOOT_TIME = 0.8   
width, height = 2000, 1000 
UFO_SIZE = 50   
OBSTACLE_SIZE = 40

GRAVITY = 3500.0        
JUMP_STRENGTH = -1100.0 
ufo_y = float(height // 2)
ufo_vy = 0.0
is_punched = False      

SCORE = 0
POINTS_DODGE = 50
POINTS_HIT_PENALTY = -50
stats = {"dodged": 0, "hit": 0, "points_log": []}

TRACK_INDICES = [5, 6, 9, 10] 

print("Analyzing audio for obstacles... please wait.")
y, sr = librosa.load(AUDIO_FILE)
onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
peaks = librosa.util.peak_pick(onset_env, pre_max=2, post_max=2, pre_avg=3, post_avg=3, delta=SENSITIVITY, wait=5)
beat_times = librosa.frames_to_time(peaks, sr=sr, hop_length=HOP)
chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=HOP)

obstacles = []
for i in range(len(peaks)):
    f = min(peaks[i], chroma.shape[1] - 1)
    lane = np.argmax(chroma[:, f])
    t = beat_times[i]
    is_chaos = random.random() < 0.20 
    obstacles.append({'time': t, 'lane': lane, 'is_chaos': is_chaos})

pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

SPAWN_X = width + 50               
HIT_X = 200        

cv2.namedWindow("UFO Dodge", cv2.WINDOW_NORMAL)

model = YOLO(MODEL_PATH)
cap = cv2.VideoCapture(0)
pygame.mixer.music.load(AUDIO_FILE)

active_obstacles = []
feedback_messages = [] 
beat_index = 0

flash_end_time, speed_end_time, gravity_end_time = 0, 0, 0

pygame.mixer.music.play()
game_start_time = time.time()
last_frame_time = game_start_time

try:
    while pygame.mixer.music.get_busy():
        now = time.time()
        elapsed = now - game_start_time
        dt = now - last_frame_time 
        last_frame_time = now
        
        is_flashbanged = now < flash_end_time
        current_shoot_time = BASE_SHOOT_TIME / 2.0 if now < speed_end_time else BASE_SHOOT_TIME
        is_gravity_reversed = now < gravity_end_time

        ret, frame_cam = cap.read()
        if not ret: break
        
        results = model(frame_cam, verbose=False, stream=True)

        for r in results:
            if r.keypoints is not None:
                kps = r.keypoints.xy.cpu().numpy()
                if len(kps) > 0:
                    person = kps[0] 
                    if len(person) > 10:
                        ls, rs, lw, rw = person[5], person[6], person[9], person[10]
                        
                        if ls[0] > 0 and rs[0] > 0:
                            shoulder_width = math.sqrt((ls[0] - rs[0])**2 + (ls[1] - rs[1])**2)
                            
                            if shoulder_width > 10: 
                                reach_r = 0
                                reach_l = 0
                                
                                if rw[0] > 0: 
                                    reach_r = math.sqrt((rw[0] - rs[0])**2 + (rw[1] - rs[1])**2) / shoulder_width
                                
                                if lw[0] > 0: 
                                    reach_l = math.sqrt((lw[0] - ls[0])**2 + (lw[1] - ls[1])**2) / shoulder_width

                                max_reach = max(reach_r, reach_l)
                                
                                if max_reach > 1.6:
                                    if not is_punched:
                                        current_jump = -JUMP_STRENGTH if is_gravity_reversed else JUMP_STRENGTH
                                        ufo_vy = current_jump
                                        is_punched = True
                                        feedback_messages.append(["FLAP!", (0, 255, 255), elapsed])
                                
                                elif max_reach < 1.3:
                                    is_punched = False

        current_grav = -GRAVITY if is_gravity_reversed else GRAVITY
        ufo_vy += current_grav * dt
        ufo_y += ufo_vy * dt

        if ufo_y > height - UFO_SIZE:
            ufo_y = height - UFO_SIZE
            ufo_vy = 0
        elif ufo_y < UFO_SIZE:
            ufo_y = UFO_SIZE
            ufo_vy = 0

        frame = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.putText(frame, f"SCORE: {SCORE}", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)

        active_mods = []
        if is_gravity_reversed: active_mods.append(f"REV GRAVITY ({int(gravity_end_time-now)}s)")
        if now < speed_end_time: active_mods.append(f"2X SPEED ({int(speed_end_time-now)}s)")
        for i, mod in enumerate(active_mods):
            cv2.putText(frame, mod, (30, 120 + i*40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

        player_color = (0, 255, 255) if is_gravity_reversed else (200, 100, 255)
        cv2.circle(frame, (HIT_X, int(ufo_y)), UFO_SIZE, player_color, -1)
        cv2.circle(frame, (HIT_X, int(ufo_y)), UFO_SIZE, (255, 255, 255), 3)
        cv2.circle(frame, (HIT_X, int(ufo_y) - 15), 25, (100, 200, 255), -1)

        if beat_index < len(obstacles):
            obs = obstacles[beat_index]
            if elapsed >= (obs['time'] - current_shoot_time - OFFSET):
                active_obstacles.append([obs['lane'], elapsed, 0, obs['is_chaos']])
                beat_index += 1

        new_obstacles = []
        for obs in active_obstacles:
            lane, start_time, state, is_chaos = obs
            obs_elapsed = elapsed - start_time
            progress = obs_elapsed / current_shoot_time
            
            bx = int(SPAWN_X - (progress * (SPAWN_X + 100))) 
            by = int((lane + 0.5) * (height / LANE_COUNT))

            is_touching = abs(by - ufo_y) < (UFO_SIZE + OBSTACLE_SIZE) and abs(bx - HIT_X) < (UFO_SIZE + OBSTACLE_SIZE)

            if state == 0: 
                if is_touching:
                    SCORE += POINTS_HIT_PENALTY
                    stats["hit"] += 1
                    stats["points_log"].append(POINTS_HIT_PENALTY)
                    
                    if is_chaos:
                        effect = random.choice(["flash", "speed", "grav"])
                        if effect == "flash": flash_end_time = now + 0.5
                        elif effect == "speed": speed_end_time = now + 3.0
                        elif effect == "grav": gravity_end_time = now + 4.0
                        feedback_messages.append(["CHAOS DAMAGE!", (0, 0, 255), elapsed])
                    else:
                        feedback_messages.append(["CRASH!", (0, 0, 255), elapsed])
                    
                    obs[2] = 1 
                elif bx < HIT_X - 100:
                    SCORE += POINTS_DODGE
                    stats["dodged"] += 1
                    stats["points_log"].append(POINTS_DODGE)
                    feedback_messages.append(["DODGE +50", (0, 255, 0), elapsed])
                    obs[2] = 2 

            if obs[2] == 0:
                obs_color = (0, 0, 255) if is_chaos else (255, 100, 100)
                cv2.circle(frame, (bx, by), OBSTACLE_SIZE, obs_color, -1)
                cv2.circle(frame, (bx, by), OBSTACLE_SIZE+5, (255, 255, 255), 2)
                new_obstacles.append(obs)
                
        active_obstacles = new_obstacles

        new_fb = []
        for msg, color, spawn in feedback_messages:
            f_el = elapsed - spawn
            if f_el < 0.8:
                alpha = 1.0 - (f_el/0.8)
                cv2.putText(frame, msg, (HIT_X + 100, int(ufo_y) + random.randint(-30,30)), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (int(color[0]*alpha), int(color[1]*alpha), int(color[2]*alpha)), 3)
                new_fb.append([msg, color, spawn])
        feedback_messages = new_fb

        if is_flashbanged: frame[:, :] = 255 

        cv2.imshow("UFO Dodge", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

except KeyboardInterrupt: pass
cap.release()
pygame.mixer.music.stop()
cv2.destroyAllWindows()

def show_analytics():
    total_obs = stats["hit"] + stats["dodged"]
    dodge_pc = (stats["dodged"] / total_obs * 100) if total_obs > 0 else 0
    final_score = SCORE

    with open("1.txt", "a") as f: f.write(f"{final_score}\n")
    with open("2.txt", "a") as f: f.write(f"{dodge_pc}\n")

    def load_data(file):
        data = []
        if os.path.exists(file):
            with open(file, "r") as f:
                for line in f:
                    if line.strip(): data.append(float(line.strip()))
        return data

    history_1 = load_data("1.txt")
    history_2 = load_data("2.txt")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.canvas.manager.set_window_title('Historical Analytics')

    axes[0].plot(history_1, marker='o', color='#8e44ad', linewidth=2)
    axes[0].set_title('History: Final Score')
    axes[0].set_xlabel('Game Session')
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(history_2, marker='s', color='#16a085', linewidth=2)
    axes[1].set_title('History: Dodge Percentage (%)')
    axes[1].set_xlabel('Game Session')
    axes[1].set_ylim(0, 105)
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

if (stats["hit"] + stats["dodged"]) > 0:
    show_analytics()