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

#AUDIO_FILE = 'GeometryDash/Amethyst.mp3' 
MODEL_PATH = 'temp/yolo11n-pose.engine' 
LANE_COUNT = 12

SENSITIVITY = 2.00 - content_int
HOP = 128
OFFSET = 0.06 

BASE_SHOOT_TIME = 0.8   
width, height = 2000, 1000 
SHIP_SIZE = 60
OBSTACLE_SIZE = 40

GRAVITY = 2800.0        
THRUST = 5500.0  
ship_y = float(height // 2)
ship_vy = 0.0
is_thrusting = False      

SCORE = 0
POINTS_DODGE = 400
POINTS_HIT_PENALTY = 0
INACTIVITY_DRAIN = -75  
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

SPAWN_X = width + 50               
HIT_X = 200        

cv2.namedWindow("ship", cv2.WINDOW_NORMAL)
model = YOLO(MODEL_PATH)
cap = cv2.VideoCapture(0)
pygame.mixer.music.load(AUDIO_FILE)

active_obstacles = []
feedback_messages = [] 
beat_index = 0

flash_end_time, speed_end_time, gravity_end_time = 0, 0, 0
burn_end_time = 0  
decay_end_time = 0 

last_ship_y = ship_y
last_ship_move_time = time.time()
last_drain_time = time.time()

stars = [[random.randint(0, width), random.randint(0, height), random.uniform(100, 400), random.randint(1, 3)] for _ in range(150)]

def draw_ship(frame, x, y, size, color, is_inverted=False, thrusting=False):
    dy = -1 if is_inverted else 1
    pts = np.array([
        [int(x - size), int(y - size * 0.5 * dy)],
        [int(x + size), int(y)],
        [int(x - size), int(y + size * 0.5 * dy)],
        [int(x - size * 0.5), int(y)]
    ], np.int32)
    cv2.fillPoly(frame, [pts], color)
    cv2.polylines(frame, [pts], True, (255, 255, 255), 2)
    
    cockpit = np.array([
        [int(x - size * 0.2), int(y - size * 0.2 * dy)],
        [int(x + size * 0.5), int(y)],
        [int(x - size * 0.2), int(y)]
    ], np.int32)
    cv2.fillPoly(frame, [cockpit], (200, 255, 255))
    
    if thrusting:
        fire_len = random.randint(20, 40)
        fire = np.array([
            [int(x - size), int(y - size * 0.3)],
            [int(x - size - fire_len), int(y)],
            [int(x - size), int(y + size * 0.3)]
        ], np.int32)
        cv2.fillPoly(frame, [fire], (0, 120, 255))
        
        inner_fire = np.array([
            [int(x - size), int(y - size * 0.15)],
            [int(x - size - fire_len + 10), int(y)],
            [int(x - size), int(y + size * 0.15)]
        ], np.int32)
        cv2.fillPoly(frame, [inner_fire], (0, 255, 255))

def draw_fire_borders(frame, w, h, offset_time):
    for x in range(0, w, 40):
        flame_h_bottom = 35 + int(30 * math.sin(x*0.05 + offset_time*10))
        pts_bottom = np.array([[x, h], [x+20, h-flame_h_bottom], [x+40, h]])
        cv2.fillPoly(frame, [pts_bottom], (0, 120, 255))
        flame_h_top = 35 + int(30 * math.cos(x*0.05 + offset_time*12))
        pts_top = np.array([[x, 0], [x+20, flame_h_top], [x+40, 0]])
        cv2.fillPoly(frame, [pts_top], (0, 120, 255))

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
        is_thrusting = False

        for r in results:
            if r.keypoints is not None:
                kps = r.keypoints.xy.cpu().numpy()
                if len(kps) > 0:
                    person = kps[0] 
                    if len(person) > 10:
                        ls, rs, lw, rw = person[5], person[6], person[9], person[10]
                        if ls[0] > 0 and rs[0] > 0:
                            sw = math.sqrt((ls[0]-rs[0])**2 + (ls[1]-rs[1])**2)
                            reach = 0
                            if rw[0] > 0: reach = max(reach, math.sqrt((rw[0]-rs[0])**2 + (rw[1]-rs[1])**2)/sw)
                            if lw[0] > 0: reach = max(reach, math.sqrt((lw[0]-ls[0])**2 + (lw[1]-ls[1])**2)/sw)
                            
                            if reach > 1.5:
                                is_thrusting = True

        current_grav = -GRAVITY if is_gravity_reversed else GRAVITY
        current_thrust = THRUST if is_gravity_reversed else -THRUST

        if is_thrusting:
            ship_vy += current_thrust * dt
        else:
            ship_vy += current_grav * dt
            
        ship_vy *= 0.95  
        ship_y += ship_vy * dt

        is_ship_burning = False
        if ship_y > height - SHIP_SIZE:
            ship_y, ship_vy = height - SHIP_SIZE, 0
            is_ship_burning = True
        elif ship_y < SHIP_SIZE:
            ship_y, ship_vy = SHIP_SIZE, 0
            is_ship_burning = True

        if abs(ship_y - last_ship_y) > 1.0: last_ship_move_time = now
        last_ship_y = ship_y

        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        for star in stars:
            star[0] -= star[2] * dt
            if star[0] < 0: star[0], star[1] = width, random.randint(0, height)
            cv2.circle(frame, (int(star[0]), int(star[1])), star[3], (255, 255, 255), -1)

        draw_fire_borders(frame, width, height, elapsed)
        cv2.putText(frame, f"SCORE: {SCORE}", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        active_mods = []
        if is_gravity_reversed: active_mods.append(f"REV GRAVITY ({int(gravity_end_time-now)}s)")
        if now < speed_end_time: active_mods.append(f"2X SPEED ({int(speed_end_time-now)}s)")
        for i, mod in enumerate(active_mods):
            cv2.putText(frame, mod, (30, 120 + i*40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

        if is_ship_burning or (now - last_ship_move_time > 0.01):
            if now - last_drain_time > 0.1:
                SCORE += INACTIVITY_DRAIN
                stats["points_log"].append(INACTIVITY_DRAIN)
                last_drain_time = now
                feedback_messages.append(["", (0, 0, 255), elapsed])

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
                if abs(by - ship_y) < (SHIP_SIZE + OBSTACLE_SIZE) and abs(bx - HIT_X) < (SHIP_SIZE + OBSTACLE_SIZE):
                    if is_chaos:
                        SCORE += POINTS_HIT_PENALTY
                        stats["hit"] += 1
                        stats["points_log"].append(POINTS_HIT_PENALTY)
                        decay_end_time = now + 1.0
                        effect = random.choice(["flash", "speed", "grav"])
                        if effect == "flash": flash_end_time = now + 0.5
                        elif effect == "speed": speed_end_time = now + 3.0
                        elif effect == "grav": gravity_end_time = now + 4.0
                        feedback_messages.append(["", (255, 0, 255), elapsed])
                    else: 
                        SCORE += POINTS_DODGE
                        stats["dodged"] += 1
                        stats["points_log"].append(POINTS_DODGE)
                        feedback_messages.append(["", (0, 255, 0), elapsed])
                    obs[2] = 1 
                elif bx < HIT_X - 100:
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

        ship_color = (0, 255, 255) if is_gravity_reversed else (200, 50, 50)
        draw_ship(frame, HIT_X, int(ship_y), SHIP_SIZE, ship_color, is_inverted=is_gravity_reversed, thrusting=is_thrusting)
        
        new_fb = []
        for msg, color, spawn in feedback_messages:
            if elapsed - spawn < 0.8:
                alpha = 1.0 - ((elapsed - spawn)/0.8)
                cv2.putText(frame, msg, (HIT_X + 100, int(ship_y) + random.randint(-20,20)), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (int(color[0]*alpha), int(color[1]*alpha), int(color[2]*alpha)), 3)
                new_fb.append([msg, color, spawn])
        feedback_messages = new_fb
        if is_ship_burning:
            for _ in range(5):
                fx, fy = HIT_X + random.randint(-SHIP_SIZE, SHIP_SIZE), int(ship_y) + random.randint(-SHIP_SIZE, SHIP_SIZE)
                cv2.circle(frame, (fx, fy), random.randint(10, 25), (0, 120, 255), -1)
            overlay = np.full_like(frame, (0, 50, 200), dtype=np.uint8)
            frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
            
        if now < decay_end_time:
            frame = cv2.bitwise_not(frame)
            overlay = np.full_like(frame, (200, 0, 200), dtype=np.uint8)
            frame = cv2.addWeighted(frame, 0.8, overlay, 0.2, 0)

        if is_flashbanged: frame[:, :] = 255 
        cv2.imshow("ship", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

except KeyboardInterrupt: pass
cap.release()
pygame.mixer.music.stop()
cv2.destroyAllWindows()

def show_analytics():
    os.makedirs("graph/Ship", exist_ok=True)
    
    total_obs = stats["hit"] + stats["dodged"]
    dodge_pc = (stats["dodged"] / total_obs * 100) if total_obs > 0 else 0
    final_score = SCORE

    with open("graph/Ship/1.txt", "a") as f: f.write(f"{final_score}\n")
    with open("graph/Ship/2.txt", "a") as f: f.write(f"{dodge_pc}\n")

    def load_data(file):
        data = []
        if os.path.exists(file):
            with open(file, "r") as f:
                for line in f:
                    if line.strip(): data.append(float(line.strip()))
        return data

    history_1 = load_data("graph/Ship/1.txt")
    history_2 = load_data("graph/Ship/2.txt")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.canvas.manager.set_window_title('Ship Mode Analytics')

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