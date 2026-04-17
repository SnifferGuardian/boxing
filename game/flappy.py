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

#AUDIO_FILE = 'GeometryDash/jumper.mp3'  
MODEL_PATH = 'temp/yolo11n-pose.engine'  
LANE_COUNT = 12

SENSITIVITY = 2.00 - content_int 
HOP = 128
OFFSET = 0.06 

BASE_SHOOT_TIME = 0.8   
width, height = 2000, 1000 
UFO_SIZE = 60   
OBSTACLE_SIZE = 40

GRAVITY = 3500.0        # default = 3500
JUMP_STRENGTH = -1650.0 # default = 1100
ufo_y = float(height // 2)
ufo_vy = 0.0
arms_up = False      

SCORE = 0
POINTS_DODGE = 50
POINTS_HIT_PENALTY = -50
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

cv2.namedWindow("flappy bird", cv2.WINDOW_NORMAL)
model = YOLO(MODEL_PATH)
cap = cv2.VideoCapture(0)
pygame.mixer.music.load(AUDIO_FILE)

active_obstacles = []
feedback_messages = [] 
beat_index = 0

flash_end_time, speed_end_time, gravity_end_time = 0, 0, 0
burn_end_time = 0  
decay_end_time = 0 

last_ufo_y = ufo_y
last_ufo_move_time = time.time()
last_drain_time = time.time()

stars = [[random.randint(0, width), random.randint(0, height), random.uniform(100, 400), random.randint(1, 3)] for _ in range(150)]

pygame.mixer.music.play()
game_start_time = time.time()
last_frame_time = game_start_time

def draw_ufo(frame, x, y, size, color, is_inverted=False):
    if is_inverted:
        cv2.ellipse(frame, (x, int(y + size*0.1)), (int(size*0.6), int(size*0.5)), 0, 0, 180, (255, 230, 200), -1)
    else:
        cv2.ellipse(frame, (x, int(y - size*0.1)), (int(size*0.6), int(size*0.5)), 0, 180, 360, (255, 230, 200), -1)
        
    cv2.ellipse(frame, (x, int(y)), (size, int(size*0.35)), 0, 0, 360, color, -1)
    cv2.ellipse(frame, (x, int(y)), (size, int(size*0.35)), 0, 0, 360, (200, 200, 200), 2)
    
    for dx in [-size//2, 0, size//2]:
        cv2.circle(frame, (x + dx, int(y)), 4, (0, 255, 255), -1)

def draw_fire_borders(frame, w, h, offset_time):
    for x in range(0, w, 40):
         
        flame_h_bottom2 = 30 + int(60 * math.sin(x*0.02 + offset_time*12))
        pts_bottom = np.array([[x, h], [x+20, h-flame_h_bottom2], [x+40, h]])
        cv2.fillPoly(frame, [pts_bottom], (0, 60, 255)) 
        flame_h_bottom = 30 + int(45 * math.sin(x*0.03 + offset_time*10))
        pts_bottom = np.array([[x, h], [x+20, h-flame_h_bottom], [x+40, h]])
        cv2.fillPoly(frame, [pts_bottom], (0, 120, 255))
        
        flame_h_top2 = 30 + int(60 * math.cos(x*0.02 + offset_time*12))
        pts_top = np.array([[x, 0], [x+20, flame_h_top2], [x+40, 0]])
        cv2.fillPoly(frame, [pts_top], (0, 60, 255))
        flame_h_top = 30 + int(45 * math.cos(x*0.03 + offset_time*10))
        pts_top = np.array([[x, 0], [x+20, flame_h_top], [x+40, 0]])
        cv2.fillPoly(frame, [pts_top], (0, 120, 255))

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
                        if ls[0] > 0 and rs[0] > 0 and lw[0] > 0 and rw[0] > 0:
                            if lw[1] < ls[1] - 40 and rw[1] < rs[1] - 40:
                                arms_up = True
                            elif lw[1] > ls[1] + 20 and rw[1] > rs[1] + 20:
                                if arms_up:  
                                    current_jump = -JUMP_STRENGTH if is_gravity_reversed else JUMP_STRENGTH
                                    ufo_vy = current_jump
                                    arms_up = False  
                                    feedback_messages.append(["", (0, 255, 255), elapsed])

        current_grav = -GRAVITY if is_gravity_reversed else GRAVITY
        ufo_vy += current_grav * dt
        ufo_y += ufo_vy * dt

        if ufo_y > height - UFO_SIZE:
            ufo_y = height - UFO_SIZE
            ufo_vy = 0
        elif ufo_y < UFO_SIZE:
            ufo_y = UFO_SIZE
            ufo_vy = 0

        if abs(ufo_y - last_ufo_y) > 1.0:
            last_ufo_move_time = now
        last_ufo_y = ufo_y

        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        for star in stars:
            star[0] -= star[2] * dt
            if star[0] < 0:
                star[0] = width
                star[1] = random.randint(0, height)
            cv2.circle(frame, (int(star[0]), int(star[1])), star[3], (255, 255, 255), -1)
        draw_fire_borders(frame, width, height, elapsed)

        is_ufo_burning = False

        if now - last_ufo_move_time > 0.01:
            cv2.putText(frame, "dont touch the fire poophead", (width//2 - 250, height//2), 
                        cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 255), 5)
            is_ufo_burning = True 
            
            if now - last_drain_time > 0.1:
                SCORE += INACTIVITY_DRAIN
                stats["points_log"].append(INACTIVITY_DRAIN)
                feedback_messages.append(["", (0, 0, 255), elapsed])
                last_drain_time = now
        else:
            last_drain_time = now 

        cv2.putText(frame, f"SCORE: {SCORE}", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)

        active_mods = []
        if is_gravity_reversed: active_mods.append(f"REVERSE ({int(gravity_end_time-now)}s)")
        if now < speed_end_time: active_mods.append(f"2X ({int(speed_end_time-now)}s)")
        for i, mod in enumerate(active_mods):
            cv2.putText(frame, mod, (30, 120 + i*40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

        if beat_index < len(obstacles):
            obs = obstacles[beat_index]
            if elapsed >= (obs['time'] - current_shoot_time - OFFSET):
                active_obstacles.append([obs['lane'], elapsed, 0, obs['is_chaos']])
                beat_index += 1

        new_obstacles = []
        for obs in active_obstacles:
            lane, start_time, state, is_chaos = obs
            progress = (elapsed - start_time) / current_shoot_time
            bx = int(SPAWN_X - (progress * (SPAWN_X + 100))) 
            by = int((lane + 0.5) * (height / LANE_COUNT))

            if state == 0: 
                if abs(by - ufo_y) < (UFO_SIZE + OBSTACLE_SIZE) and abs(bx - HIT_X) < (UFO_SIZE + OBSTACLE_SIZE):
                    SCORE += POINTS_HIT_PENALTY
                    stats["hit"] += 1
                    if is_chaos: 
                        decay_end_time = now + 1.0 
                        effect = random.choice(["flash", "speed", "grav"])
                        if effect == "flash": flash_end_time = now + 0.5
                        elif effect == "speed": speed_end_time = now + 3.0
                        elif effect == "grav": gravity_end_time = now + 4.0
                    else: 
                        burn_end_time = now + 0.5 

                    feedback_messages.append(["", (0, 0, 255), elapsed])
                    obs[2] = 1 
                elif bx < HIT_X - 100:
                    SCORE += POINTS_DODGE
                    stats["dodged"] += 1
                    feedback_messages.append(["", (0, 255, 0), elapsed])
                    obs[2] = 2 

            if obs[2] == 0:
                if is_chaos:
                    cv2.circle(frame, (bx, by), OBSTACLE_SIZE, (255, 0, 255), -1) 
                    cv2.circle(frame, (bx, by), int(OBSTACLE_SIZE*0.6), (255, 100, 255), -1)
                    cv2.circle(frame, (bx, by), int(OBSTACLE_SIZE*0.3), (255, 255, 255), -1) 
                else:
                    cv2.circle(frame, (bx, by), OBSTACLE_SIZE, (0, 100, 255), -1) 
                    cv2.circle(frame, (bx + int(15 * math.cos(elapsed*10)), by + int(15 * math.sin(elapsed*10))), int(OBSTACLE_SIZE*0.7), (0, 165, 255), -1) 
                    cv2.circle(frame, (bx, by), int(OBSTACLE_SIZE*0.4), (0, 255, 255), -1) 
                    
                new_obstacles.append(obs)
        active_obstacles = new_obstacles

        player_color = (0, 255, 255) if is_gravity_reversed else (200, 100, 255)
        
        draw_ufo(frame, HIT_X, int(ufo_y), UFO_SIZE, player_color, is_inverted=is_gravity_reversed)
        
        if now < burn_end_time: 
            is_ufo_burning = True

        if is_ufo_burning:
            for _ in range(5):
                fx = HIT_X + random.randint(-UFO_SIZE, UFO_SIZE)
                fy = int(ufo_y) + random.randint(-UFO_SIZE, UFO_SIZE)
                cv2.circle(frame, (fx, fy), random.randint(10, 25), (0, 120, 255), -1)

        new_fb = []
        for msg, color, spawn in feedback_messages:
            if elapsed - spawn < 0.8:
                alpha = 1.0 - ((elapsed - spawn)/0.8)
                cv2.putText(frame, msg, (HIT_X + 100, int(ufo_y) + random.randint(-20,20)), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (int(color[0]*alpha), int(color[1]*alpha), int(color[2]*alpha)), 3)
                new_fb.append([msg, color, spawn])
        feedback_messages = new_fb

        if now < burn_end_time:
            overlay = np.full_like(frame, (0, 50, 200), dtype=np.uint8)
            frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
            
        if now < decay_end_time:
            frame = cv2.bitwise_not(frame)
            overlay = np.full_like(frame, (200, 0, 200), dtype=np.uint8)
            frame = cv2.addWeighted(frame, 0.8, overlay, 0.2, 0)

        if is_flashbanged: frame[:, :] = 255 
        
        cv2.imshow("flappy bird", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

except KeyboardInterrupt: pass
cap.release()
pygame.mixer.music.stop()
cv2.destroyAllWindows()

def show_analytics():
    total_obs = stats["hit"] + stats["dodged"]
    dodge_pc = (stats["dodged"] / total_obs * 100) if total_obs > 0 else 0
    with open("graph/Flap/1.txt", "a") as f: f.write(f"{SCORE}\n")
    with open("graph/Flap/2.txt", "a") as f: f.write(f"{dodge_pc}\n")

    def load_data(file):
        if not os.path.exists(file): return []
        with open(file, "r") as f:
            return [float(line.strip()) for line in f if line.strip()]

    h1, h2 = load_data("graph/Flap/1.txt"), load_data("graph/Flap/2.txt")
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].plot(h1, marker='o', color='#8e44ad'); axes[0].set_title('Score History')
    axes[1].plot(h2, marker='s', color='#16a085'); axes[1].set_title('Dodge % History')
    plt.tight_layout()
    plt.show()

if (stats["hit"] + stats["dodged"]) > 0:
    show_analytics()