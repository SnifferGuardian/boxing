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

try:
    with open('difficulty.txt', 'r') as f:
        content_int = float(f.read())
        
    with open('song_file.txt', 'r') as f:
        AUDIO_FILE = f.read().strip()
except:
    content_int = 1.0

MODEL_PATH = 'temp/yolo11n-pose.engine' 
LANE_COUNT = 12

SENSITIVITY = 2.00 - content_int
HOP = 128
OFFSET = 0.06 

BASE_SHOOT_TIME = 0.8   
width, height = 1920, 1080 
SHIP_SIZE = 60
OBSTACLE_SIZE = 45

HIT_X_LEFT = 150
HIT_X_RIGHT = 300
left_ship_y = height / 2
right_ship_y = height / 2

SCORE = 0
POINTS_DODGE = 70
POINTS_HIT_PENALTY = -2
INACTIVITY_DRAIN = -7.5
THRESH = 50.0
stats = {"dodged": 0, "hit": 0, "points_log": []}

print("Analyzing audio... please wait.")
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
    obstacles.append({'time': t, 'lane': lane, 'is_chaos': random.random() < 0.20})

pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Dual Wrist Ships")

SPAWN_X = width + 50               

model = YOLO(MODEL_PATH)
cap = cv2.VideoCapture(0)

cam_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
cam_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
if cam_h == 0: cam_h = 480 

pygame.mixer.music.load(AUDIO_FILE)

active_obstacles = []
feedback_messages = [] 
beat_index = 0

flash_end_time, speed_end_time = 0, 0
decay_end_time = 0 

last_left_y, last_right_y = left_ship_y, right_ship_y
last_active_time = time.time()
last_drain_time = time.time()

stars = [[random.randint(0, width), random.randint(0, height), random.uniform(100, 400), random.randint(1, 3)] for _ in range(150)]

def draw_ship(frame, x, y, size, color):
    pts = np.array([
        [int(x - size), int(y - size * 0.5)],
        [int(x + size), int(y)],
        [int(x - size), int(y + size * 0.5)],
        [int(x - size * 0.5), int(y)]
    ], np.int32)
    cv2.fillPoly(frame, [pts], color)
    cv2.polylines(frame, [pts], True, (255, 255, 255), 2)
    
    cockpit = np.array([
        [int(x - size * 0.2), int(y - size * 0.2)],
        [int(x + size * 0.5), int(y)],
        [int(x - size * 0.2), int(y)]
    ], np.int32)
    cv2.fillPoly(frame, [cockpit], (200, 255, 255))
    
    fire_len = random.randint(20, 40)
    fire = np.array([
        [int(x - size), int(y - size * 0.3)],
        [int(x - size - fire_len), int(y)],
        [int(x - size), int(y + size * 0.3)]
    ], np.int32)
    cv2.fillPoly(frame, [fire], (0, 120, 255))

pygame.mixer.music.play()
game_start_time = time.time()
last_frame_time = game_start_time
running = True

try:
    while running and pygame.mixer.music.get_busy():
        now = time.time()
        elapsed = now - game_start_time
        dt = now - last_frame_time 
        last_frame_time = now
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_q: running = False

        is_flashbanged = now < flash_end_time
        current_shoot_time = BASE_SHOOT_TIME / 2.0 if now < speed_end_time else BASE_SHOOT_TIME

        ret, frame_cam = cap.read()
        if not ret: break
        
        frame_cam = cv2.flip(frame_cam, 1)
        results = model(frame_cam, verbose=False, stream=True)

        target_left_y, target_right_y = left_ship_y, right_ship_y

        for r in results:
            if r.keypoints is not None:
                kps = r.keypoints.xy.cpu().numpy()
                if len(kps) > 0:
                    person = kps[0] 
                    if len(person) > 10:
                        rw, lw = person[9], person[10]
                        
                        if lw[0] > 0: 
                            target_left_y = (lw[1] / cam_h) * height
                        if rw[0] > 0:
                            target_right_y = (rw[1] / cam_h) * height

        left_ship_y += (target_left_y - left_ship_y) * 0.3
        right_ship_y += (target_right_y - right_ship_y) * 0.3

        if abs(left_ship_y - last_left_y) > THRESH or abs(right_ship_y - last_right_y) > THRESH: 
            last_active_time = now
        last_left_y, last_right_y = left_ship_y, right_ship_y

        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        for star in stars:
            star[0] -= star[2] * dt
            if star[0] < 0: star[0], star[1] = width, random.randint(0, height)
            cv2.circle(frame, (int(star[0]), int(star[1])), star[3], (255, 255, 255), -1)

        time_since_active = now - last_active_time
        if time_since_active > 1.5:
            for sy in [left_ship_y, right_ship_y]:
                for sx in [HIT_X_LEFT, HIT_X_RIGHT]:
                    for _ in range(4):
                        fx = sx + random.randint(-SHIP_SIZE, int(SHIP_SIZE*1.5))
                        fy = int(sy) + random.randint(-SHIP_SIZE, SHIP_SIZE)
                        cv2.circle(frame, (fx, fy), random.randint(15, 30), (0, 100, 255), -1)
                        cv2.circle(frame, (fx, fy), random.randint(5, 15), (0, 200, 255), -1)
            
            if math.sin(now * 15) > 0:
                cv2.putText(frame, "move poophead", (width//2 - 150, 100), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 255), 5)
            
            if now - last_drain_time > 0.1:
                SCORE += INACTIVITY_DRAIN
                stats["points_log"].append(INACTIVITY_DRAIN)
                last_drain_time = now

        cv2.putText(frame, f"SCORE: {SCORE}", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)

        if now < speed_end_time:
            cv2.putText(frame, f"2X SPEED ({int(speed_end_time-now)}s)", (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

        if beat_index < len(obstacles):
            obs = obstacles[beat_index]
            if elapsed >= (obs['time'] - current_shoot_time - OFFSET):
                active_obstacles.append([obs['lane'], elapsed, 0, obs['is_chaos']])
                beat_index += 1

        new_obstacles = []
        for obs in active_obstacles:
            lane, start_time, state, is_chaos = obs
            progress = (elapsed - start_time) / current_shoot_time
            bx, by = int(SPAWN_X - (progress * (SPAWN_X + 100))), int((lane + 0.5) * (height / LANE_COUNT))

            if state == 0: 
                dist_left = math.hypot(bx - HIT_X_LEFT, by - left_ship_y)
                dist_right = math.hypot(bx - HIT_X_RIGHT, by - right_ship_y)
                
                hit_radius = SHIP_SIZE + OBSTACLE_SIZE
                
                if dist_left < hit_radius or dist_right < hit_radius:
                    if is_chaos: 
                        SCORE += POINTS_HIT_PENALTY
                        stats["hit"] += 1
                        stats["points_log"].append(POINTS_HIT_PENALTY)
                        decay_end_time = now + 1.0
                        if random.random() < 0.5: flash_end_time = now + 0.5
                        else: speed_end_time = now + 3.0
                        feedback_messages.append(["", (255, 0, 255), elapsed, bx, by])
                    else: 
                        SCORE += POINTS_DODGE
                        stats["dodged"] += 1
                        stats["points_log"].append(POINTS_DODGE)
                        feedback_messages.append(["", (0, 255, 0), elapsed, bx, by])
                    obs[2] = 1 
                elif bx < min(HIT_X_LEFT, HIT_X_RIGHT) - 100:
                    if not is_chaos: 
                        SCORE += POINTS_HIT_PENALTY
                    obs[2] = 2 

            if obs[2] == 0:
                if is_chaos: 
                    cv2.circle(frame, (bx, by), OBSTACLE_SIZE, (255, 0, 255), -1)
                    cv2.circle(frame, (bx, by), int(OBSTACLE_SIZE*0.3), (255, 255, 255), -1)
                else: 
                    cv2.circle(frame, (bx, by), OBSTACLE_SIZE, (0, 255, 0), -1)
                    cv2.circle(frame, (bx, by), int(OBSTACLE_SIZE*0.4), (200, 255, 200), -1)
                new_obstacles.append(obs)
        active_obstacles = new_obstacles

        draw_ship(frame, HIT_X_LEFT, int(left_ship_y), SHIP_SIZE, (255, 100, 50))   
        draw_ship(frame, HIT_X_RIGHT, int(right_ship_y), SHIP_SIZE, (50, 100, 255)) 
        
        new_fb = []
        for msg, color, spawn, mx, my in feedback_messages:
            if elapsed - spawn < 0.8:
                alpha = 1.0 - ((elapsed - spawn)/0.8)
                cv2.putText(frame, msg, (mx, my - 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (int(color[0]*alpha), int(color[1]*alpha), int(color[2]*alpha)), 3)
                new_fb.append([msg, color, spawn, mx, my])
        feedback_messages = new_fb

        if now < decay_end_time:
            frame = cv2.bitwise_not(frame)
            overlay = np.full_like(frame, (200, 0, 200), dtype=np.uint8)
            frame = cv2.addWeighted(frame, 0.8, overlay, 0.2, 0)

        if is_flashbanged: frame[:, :] = 255 
        
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        surf = pygame.image.frombuffer(frame_rgb.flatten(), (width, height), 'RGB')
        screen.blit(surf, (0, 0))
        pygame.display.flip()

except KeyboardInterrupt: pass
cap.release()
pygame.quit()

def show_analytics():
    os.makedirs("graph/DualWrist", exist_ok=True)
    
    total_obs = stats["hit"] + stats["dodged"]
    dodge_pc = (stats["dodged"] / total_obs * 100) if total_obs > 0 else 0
    final_score = SCORE

    with open("graph/DualWrist/1.txt", "a") as f: f.write(f"{final_score}\n")
    with open("graph/DualWrist/2.txt", "a") as f: f.write(f"{dodge_pc}\n")

    def load_data(file):
        data = []
        if os.path.exists(file):
            with open(file, "r") as f:
                for line in f:
                    if line.strip(): data.append(float(line.strip()))
        return data

    history_1 = load_data("graph/DualWrist/1.txt")
    history_2 = load_data("graph/DualWrist/2.txt")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.canvas.manager.set_window_title('Dual Wrist Analytics')

    axes[0].plot(history_1, marker='o', color='#8e44ad', linewidth=2)
    axes[0].set_title('score')
    axes[0].set_xlabel('Game Session')
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(history_2, marker='s', color='#16a085', linewidth=2)
    axes[1].set_title('dodge percentage')
    axes[1].set_xlabel('Game Session')
    axes[1].set_ylim(0, 105)
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

if (stats["hit"] + stats["dodged"]) > 0:
    show_analytics()