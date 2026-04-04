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

AUDIO_FILE = 'GeometryDash/Amethyst.mp3'  
MODEL_PATH = 'temp/yolo11n-pose.engine'  

try:
    with open('difficulty.txt', 'r') as f:
        content_int = float(f.read())
        print(f"Difficulty loaded: {content_int}")
except FileNotFoundError:
    content_int = 1.0
    print("difficulty.txt not found, defaulting to 1.0")

SENSITIVITY = 0.35#2.00 - content_int 

HOP = 128
OFFSET = 0.06 

BASE_SHOOT_TIME = 0.7   
SHOOT_TIME = BASE_SHOOT_TIME 
width, height = 2000, 1000 
CIRCLE_SIZE = 60        
HIT_WINDOW = 0.15
PERFECT_WINDOW = 0.05
RIPPLE_DURATION = 0.5 
EXPLOSION_DURATION = 0.4

INACTIVITY_LIMIT = 3.0       
PENALTY_INTERVAL = 0.1       
PENALTY_AMOUNT = -1       
BASE_JITTER = 20   
JITTER_THRESHOLD = BASE_JITTER

SCORE = 0
POINTS_PERFECT = 100
POINTS_GOOD = 50
POINTS_MISS = -25
stats = {
    "hits": 0,
    "misses": 0,
    "danger_dodged": 0,
    "danger_hit": 0,
    "points_log": []  
}

TRACK_INDICES = [9, 10] # 9: Left Wrist, 10: Right Wrist

print("Analyzing audio... please wait.")
y, sr = librosa.load(AUDIO_FILE)
onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
peaks = librosa.util.peak_pick(onset_env, pre_max=2, post_max=2, pre_avg=3, post_avg=3, delta=SENSITIVITY, wait=5)
beat_times = librosa.frames_to_time(peaks, sr=sr, hop_length=HOP)

notes = []
for i in range(len(peaks)):
    t = beat_times[i]
    
    # 0 = Left/Yellow, 1 = Right/Blue, 2 = Danger/Red
    rand_val = random.random()
    if rand_val < 0.15:
        orb_type = 2 
    elif rand_val < 0.575:
        orb_type = 0 
    else:
        orb_type = 1 

    # Hemisphere Logic
    pad = 120
    mid_x = width // 2
    
    if orb_type == 0: # Left / Yellow
        nx = random.randint(pad, mid_x)
    elif orb_type == 1: # Right / Blue
        nx = random.randint(mid_x, width - pad)
    else: # Danger / Red (Can spawn anywhere)
        nx = random.randint(pad, width - pad)

    ny = random.randint(pad, height - pad)

    notes.append({'time': t, 'x': nx, 'y': ny, 'type': orb_type})

pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

def generate_tone(freq):
    t = np.linspace(0, 0.1, int(44100 * 0.1), False)
    wave = np.sign(np.sin(2 * np.pi * freq * t)) * 0.15
    audio = (wave * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(np.repeat(audio[:, np.newaxis], 2, axis=1))

tone_left = generate_tone(440)     # A4
tone_right = generate_tone(523.25) # C5
tone_danger = generate_tone(200)   # Low tone

window_name = "chaos"
cv2.namedWindow(window_name)

def map_to_screen(x, y, cam_w, cam_h, reverse_x=True, reverse_y=False):
    sx = int((1.0 - x / cam_w) * width) if reverse_x else int((x / cam_w) * width)
    sy = int((1.0 - y / cam_h) * height) if reverse_y else int((y / cam_h) * height)
    return sx, sy

model = YOLO(MODEL_PATH)
cap = cv2.VideoCapture(0)
pygame.mixer.music.load(AUDIO_FILE)

active_orbs = []
active_ripples = []
active_explosions = []
feedback_messages = [] 
beat_index = 0
last_move_time = time.time()
last_penalty_hit_time = 0
prev_wrist_positions = {9: (0, 0), 10: (0, 0)}

flash_end_time, speed_end_time, slow_end_time, gravity_end_time = 0, 0, 0, 0

pygame.mixer.music.play()
game_start_time = time.time()

try:
    while pygame.mixer.music.get_busy():
        now = time.time()
        elapsed = now - game_start_time
        
        is_flashbanged = now < flash_end_time
        SHOOT_TIME = BASE_SHOOT_TIME / 2.0 if now < speed_end_time else BASE_SHOOT_TIME
        JITTER_THRESHOLD = BASE_JITTER * 2.5 if now < slow_end_time else BASE_JITTER
        is_gravity_reversed = now < gravity_end_time

        ret, frame_cam = cap.read()
        if not ret: break
        cam_h, cam_w, _ = frame_cam.shape
        
        results = model(frame_cam, verbose=False, stream=True)
        current_wrists = {}

        for r in results:
            if r.keypoints is not None:
                kps = r.keypoints.xy.cpu().numpy()
                if len(kps) > 0:
                    person = kps[0] 
                    for idx in TRACK_INDICES:
                        if idx < len(person):
                            kp = person[idx]
                            if kp[0] > 0 and kp[1] > 0:
                                screen_pos = map_to_screen(kp[0], kp[1], cam_w, cam_h, reverse_x=True, reverse_y=is_gravity_reversed)
                                current_wrists[idx] = screen_pos

        moved_significantly = False
        for idx in [9, 10]:
            if idx in current_wrists:
                curr = current_wrists[idx]
                prev = prev_wrist_positions[idx]
                dist = math.sqrt((curr[0]-prev[0])**2 + (curr[1]-prev[1])**2)
                if dist > JITTER_THRESHOLD: moved_significantly = True
                prev_wrist_positions[idx] = curr

        if moved_significantly: last_move_time = now
        idle_time = now - last_move_time

        if idle_time > INACTIVITY_LIMIT:
            if (now - last_penalty_hit_time) > PENALTY_INTERVAL:
                SCORE += PENALTY_AMOUNT
                last_penalty_hit_time = now
                feedback_messages.append(["IDLE PENALTY!", (0, 0, 255), elapsed])

        frame = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.putText(frame, f"SCORE: {SCORE}", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)

        active_mods = []
        if is_gravity_reversed: active_mods.append(f"REV GRAVITY ({int(gravity_end_time-now)}s)")
        if now < speed_end_time: active_mods.append(f"2X SPEED ({int(speed_end_time-now)}s)")
        if now < slow_end_time: active_mods.append(f"LOW SENSITIVITY ({int(slow_end_time-now)}s)")
        for i, mod in enumerate(active_mods):
            cv2.putText(frame, mod, (30, 120 + i*40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

        if idle_time > 1.5:
            cv2.putText(frame, "MOVE!", (width//2 - 100, 100), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 255), 8)

        # Draw Wrists
        if 9 in current_wrists:
            lx, ly = current_wrists[9]
            cv2.circle(frame, (lx, ly), 35, (0, 255, 255), -1) # Yellow for Left Hand
            cv2.circle(frame, (lx, ly), 40, (255, 255, 255), 2)
        if 10 in current_wrists:
            rx, ry = current_wrists[10]
            cv2.circle(frame, (rx, ry), 35, (255, 0, 0), -1)   # Blue for Right Hand
            cv2.circle(frame, (rx, ry), 40, (255, 255, 255), 2)

        new_ripples = []
        for rx, ry, color, r_start in active_ripples:
            r_prog = (elapsed - r_start) / RIPPLE_DURATION
            if r_prog < 1.0:
                alpha = 1.0 - r_prog
                cv2.circle(frame, (rx, ry), int(150 * r_prog), color, max(1, int(15 * alpha)))
                new_ripples.append([rx, ry, color, r_start])
        active_ripples = new_ripples

        new_explosions = []
        for ex, ey, e_start in active_explosions:
            e_prog = (elapsed - e_start) / EXPLOSION_DURATION
            if e_prog < 1.0:
                cv2.circle(frame, (ex, ey), int(200 * e_prog), (0, 69, 255), -1)
                cv2.circle(frame, (ex, ey), int(120 * e_prog), (0, 165, 255), -1)
                cv2.circle(frame, (ex, ey), int(60 * e_prog), (0, 255, 255), -1)
                new_explosions.append([ex, ey, e_start])
        active_explosions = new_explosions

        if beat_index < len(notes):
            n = notes[beat_index]
            if elapsed >= (n['time'] - SHOOT_TIME - OFFSET):
                active_orbs.append([n['x'], n['y'], elapsed, 0, n['type']])
                beat_index += 1

        new_orbs = []
        for orb in active_orbs:
            ox, oy, start_time, state, orb_type = orb
            orb_elapsed = elapsed - start_time
            progress = orb_elapsed / SHOOT_TIME

            dist_left = math.inf
            dist_right = math.inf
            if 9 in current_wrists:
                lw = current_wrists[9]
                dist_left = math.hypot(lw[0]-ox, lw[1]-oy)
            if 10 in current_wrists:
                rw = current_wrists[10]
                dist_right = math.hypot(rw[0]-ox, rw[1]-oy)

            touching_left = dist_left < (CIRCLE_SIZE + 30)
            touching_right = dist_right < (CIRCLE_SIZE + 30)
            any_touching = touching_left or touching_right

            color = (0, 255, 255) if orb_type == 0 else ((255, 0, 0) if orb_type == 1 else (0, 0, 255))

            if state == 0: 
                delta = orb_elapsed - SHOOT_TIME
                
                approach_radius = max(CIRCLE_SIZE, int(CIRCLE_SIZE + (1.0 - progress) * 150))
                cv2.circle(frame, (ox, oy), CIRCLE_SIZE, color, -1)
                if progress <= 1.0:
                    cv2.circle(frame, (ox, oy), approach_radius, color, 3)

                if abs(delta) < HIT_WINDOW:
                    hit_valid = False
                    if orb_type == 0 and touching_left: hit_valid = True
                    elif orb_type == 1 and touching_right: hit_valid = True
                    elif orb_type == 2 and any_touching:
                        effect = random.choice(["flash", "speed", "slow", "grav"])
                        if effect == "flash": flash_end_time = now + 0.5
                        elif effect == "speed": speed_end_time = now + 5.0
                        elif effect == "slow": slow_end_time = now + 15.0
                        elif effect == "grav": gravity_end_time = now + 6.0
                        stats["danger_hit"] += 1
                        SCORE += PENALTY_AMOUNT
                        feedback_messages.append(["DANGER HIT!", (0, 0, 255), elapsed])
                        active_explosions.append([ox, oy, elapsed])
                        tone_danger.play()
                        orb[3] = 2 
                        continue

                    if hit_valid:
                        is_p = abs(delta) <= PERFECT_WINDOW
                        pts = POINTS_PERFECT if is_p else POINTS_GOOD
                        SCORE += pts
                        stats["hits"] += 1
                        stats["points_log"].append(pts)
                        feedback_messages.append(["PERFECT" if is_p else "GOOD", (0, 255, 0) if is_p else (0, 255, 255), elapsed])
                        if orb_type == 0: tone_left.play()
                        else: tone_right.play()
                        active_ripples.append([ox, oy, color, elapsed])
                        orb[3] = 1 

                elif progress > (1.0 + HIT_WINDOW):
                    if orb_type != 2: 
                        SCORE += POINTS_MISS
                        stats["misses"] += 1
                        stats["points_log"].append(POINTS_MISS)
                        feedback_messages.append(["MISS", (0, 0, 150), elapsed])
                    else:
                        stats["danger_dodged"] += 1
                    orb[3] = 2

            if orb[3] == 0:
                new_orbs.append(orb)
        active_orbs = new_orbs

        new_fb = []
        for msg, color, spawn in feedback_messages:
            f_el = elapsed - spawn
            if f_el < 0.8:
                alpha = 1.0 - (f_el/0.8)
                cv2.putText(frame, msg, (width // 2 - 150, height // 2 + random.randint(-10,10)), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.8, (int(color[0]*alpha), int(color[1]*alpha), int(color[2]*alpha)), 5)
                new_fb.append([msg, color, spawn])
        feedback_messages = new_fb

        if is_flashbanged: frame[:, :] = 255 

        cv2.imshow(window_name, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

except KeyboardInterrupt: pass
cap.release()
pygame.mixer.music.stop()
cv2.destroyAllWindows()

def show_analytics():
    total_notes = stats["hits"] + stats["misses"]
    hit_pc = (stats["hits"] / total_notes * 100) if total_notes > 0 else 0
    total_danger = stats["danger_hit"] + stats["danger_dodged"]
    dodge_pc = (stats["danger_dodged"] / total_danger * 100) if total_danger > 0 else 0
    avg_pts_per_orb = np.mean(stats["points_log"]) if stats["points_log"] else 0

    with open("graph/2D/coin2.txt", "a") as f: f.write(f"{avg_pts_per_orb}\n")
    with open("graph/2D/hit2.txt", "a") as f: f.write(f"{hit_pc}\n")

    def load_data(file):
        data = []
        if os.path.exists(file):
            with open(file, "r") as f:
                for line in f:
                    if line.strip(): data.append(float(line.strip()))
        return data

    coin_history = load_data("graph/2D/coin2.txt")
    hit_history = load_data("graph/2D/hit2.txt")

    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.canvas.manager.set_window_title('Game Analytics & History')

    axes[0,0].bar(['Hit %', 'Dodge %'], [hit_pc, dodge_pc], color=['#27ae60', '#e74c3c'])
    axes[0,0].set_ylim(0, 110)
    axes[0,0].set_title('Current Session Performance')
    for i, v in enumerate([hit_pc, dodge_pc]):
        axes[0,0].text(i, v + 2, f"{v:.1f}%", ha='center', fontweight='bold')

    x_indices = range(len(stats["points_log"]))
    axes[0,1].scatter(x_indices, stats["points_log"], alpha=0.5, color='#3498db')
    axes[0,1].axhline(y=avg_pts_per_orb, color='orange', linestyle='--', label=f'Avg: {avg_pts_per_orb:.1f}')
    axes[0,1].set_title('Scoring Distribution (Excl. Danger)')
    axes[0,1].set_ylabel('Points')
    axes[0,1].legend()

    axes[1,0].plot(coin_history, marker='o', color='#8e44ad', linewidth=2)
    axes[1,0].set_title('History: Average Points per Orb')
    axes[1,0].set_xlabel('Game Session')
    axes[1,0].grid(True, alpha=0.3)

    axes[1,1].plot(hit_history, marker='s', color='#16a085', linewidth=2)
    axes[1,1].set_title('History: Hit Percentage (%)')
    axes[1,1].set_xlabel('Game Session')
    axes[1,1].set_ylim(0, 105)
    axes[1,1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

if stats["points_log"] or (stats["danger_hit"] + stats["danger_dodged"]) > 0:
    show_analytics()