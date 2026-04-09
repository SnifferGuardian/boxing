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

AUDIO_FILE = 'GeometryDash/amethyst.mp3'  
MODEL_PATH = 'temp/yolo11n-pose.engine'  
LANE_COUNT = 12
with open('difficulty.txt', 'r') as f:
    content = f.read()
    content_int = float(content)
    print(content_int)

SENSITIVITY = 2.00 - content_int 

HOP = 128
OFFSET = 0.06 

BASE_SHOOT_TIME = 0.5   
SHOOT_TIME = BASE_SHOOT_TIME 
width, height = 2000, 1000 
CIRCLE_SIZE = 50   
HIT_WINDOW = 0.15
PERFECT_WINDOW = 0.05
RIPPLE_DURATION = 0.5 
EXPLOSION_DURATION = 0.4
HOLD_THRESHOLD = 0.2 

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

TRACK_INDICES = [9, 10, 13, 14] 

print("Analyzing audio... please wait.")
y, sr = librosa.load(AUDIO_FILE)
onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
peaks = librosa.util.peak_pick(onset_env, pre_max=2, post_max=2, pre_avg=3, post_avg=3, delta=SENSITIVITY, wait=5)
beat_times = librosa.frames_to_time(peaks, sr=sr, hop_length=HOP)
chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=HOP)

notes = []
for i in range(len(peaks)):
    f = min(peaks[i], chroma.shape[1] - 1)
    lane = np.argmax(chroma[:, f])
    t = beat_times[i]
    is_penalty = random.random() < 0.25 
    is_hold = False
    duration = 0
    if not is_penalty and i < len(beat_times) - 1:
        diff = beat_times[i+1] - t
        if diff < HOLD_THRESHOLD:
            is_hold = True
            duration = diff
    notes.append({'time': t, 'lane': lane, 'is_hold': is_hold, 'duration': duration, 'is_penalty': is_penalty})

pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

def generate_tone(freq):
    t = np.linspace(0, 0.1, int(44100 * 0.1), False)
    wave = np.sign(np.sin(2 * np.pi * freq * t)) * 0.15
    audio = (wave * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(np.repeat(audio[:, np.newaxis], 2, axis=1))

lane_sounds = [generate_tone(440 * (2 ** ((i - 9) / 12))) for i in range(12)]

SPAWN_X = -50               
HIT_X = width - 200         

window_name = "chaos"
cv2.namedWindow(window_name)

def map_to_line(x, y, cam_w, cam_h, gravity_reversed=False):
    y_percent = y / cam_h
    gy = (1.0 - y_percent) * height if gravity_reversed else y_percent * height
    return int(HIT_X), int(gy)

model = YOLO(MODEL_PATH)
cap = cv2.VideoCapture(0)
pygame.mixer.music.load(AUDIO_FILE)

active_bullets = []
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
        tracked_points = []
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
                                screen_pos = map_to_line(kp[0], kp[1], cam_w, cam_h, is_gravity_reversed)
                                tracked_points.append(screen_pos)
                                if idx in [9, 10]: current_wrists[idx] = (kp[0], kp[1])

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
        cv2.line(frame, (HIT_X, 0), (HIT_X, height), (100, 100, 100), 8)
        cv2.putText(frame, f"SCORE: {SCORE}", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)

        active_mods = []
        if is_gravity_reversed: active_mods.append(f"REV GRAVITY ({int(gravity_end_time-now)}s)")
        if now < speed_end_time: active_mods.append(f"2X SPEED ({int(speed_end_time-now)}s)")
        if now < slow_end_time: active_mods.append(f"LOW SENSITIVITY ({int(slow_end_time-now)}s)")
        for i, mod in enumerate(active_mods):
            cv2.putText(frame, mod, (30, 120 + i*40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

        if idle_time > 1.5:
            cv2.putText(frame, "MOVE!", (width//2 - 100, 100), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 255), 8)

        player_color = (0, 255, 255) if is_gravity_reversed else (255, 0, 255)
        for (tx, ty) in tracked_points:
            cv2.circle(frame, (tx, ty), 35, player_color, -1)
            cv2.circle(frame, (tx, ty), 40, (255, 255, 255), 2)

        new_ripples = []
        for rx, ry, lane, r_start in active_ripples:
            r_prog = (elapsed - r_start) / RIPPLE_DURATION
            if r_prog < 1.0:
                alpha = 1.0 - r_prog
                cv2.circle(frame, (rx, ry), int(150 * r_prog), (255, 255, 255), max(1, int(15 * alpha)))
                new_ripples.append([rx, ry, lane, r_start])
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
                active_bullets.append([n['lane'], elapsed, 0, n['is_hold'], n['duration'], n['is_penalty']])
                beat_index += 1

        new_bullets = []
        for bullet in active_bullets:
            lane, start_time, state, is_hold, dur, is_penalty = bullet
            bullet_elapsed = elapsed - start_time
            progress = bullet_elapsed / SHOOT_TIME
            bx = int(SPAWN_X + (progress * (HIT_X - SPAWN_X)))
            by = int((lane + 0.5) * (height / LANE_COUNT))

            is_touching = any(abs(by - ty) < (CIRCLE_SIZE + 40) and abs(bx - tx) < 80 for (tx, ty) in tracked_points)

            if state == 0: 
                delta = bullet_elapsed - SHOOT_TIME
                if abs(delta) < HIT_WINDOW and is_touching:
                    if is_penalty:
                        effect = random.choice(["flash", "speed", "slow", "grav"])
                        if effect == "flash": flash_end_time = now + 0.5
                        elif effect == "speed": speed_end_time = now + 5.0
                        elif effect == "slow": slow_end_time = now + 15.0
                        elif effect == "grav": gravity_end_time = now + 6.0
                        stats["danger_hit"] += 1
                        feedback_messages.append(["DANGER HIT!", (0, 0, 255), elapsed])
                        active_explosions.append([bx, by, elapsed])
                        bullet[2] = 2 
                    else:
                        is_p = abs(delta) <= PERFECT_WINDOW
                        pts = POINTS_PERFECT if is_p else POINTS_GOOD
                        SCORE += pts
                        stats["hits"] += 1
                        stats["points_log"].append(pts)
                        feedback_messages.append(["PERFECT" if is_p else "GOOD", (0, 255, 0) if is_p else (0, 255, 255), elapsed])
                        lane_sounds[lane].play()
                        active_ripples.append([bx, by, lane, elapsed])
                        bullet[2] = 3 if is_hold else 1
                elif progress > (1.0 + HIT_WINDOW):
                    if not is_penalty: 
                        SCORE += POINTS_MISS
                        stats["misses"] += 1
                        stats["points_log"].append(POINTS_MISS)
                        feedback_messages.append(["MISS", (0, 0, 150), elapsed])
                    else:
                        stats["danger_dodged"] += 1
                    bullet[2] = 2
            elif state == 3: 
                if not is_touching: 
                    feedback_messages.append(["DROPPED!", (0, 165, 255), elapsed])
                    bullet[2] = 2
                elif progress > (1.0 + (dur / SHOOT_TIME)): 
                    SCORE += 50
                    stats["points_log"].append(50)
                    feedback_messages.append(["HELD!", (255, 255, 0), elapsed])
                    bullet[2] = 1

            if bullet[2] in [0, 3]:
                b_color = (0, 0, 255) if is_penalty else ((0, 255, 255) if state == 3 else (255, 200, 0))
                if is_hold:
                    tx_tail = int(SPAWN_X + (max(0, progress - 0.2) * (HIT_X - SPAWN_X)))
                    cv2.line(frame, (bx, by), (tx_tail, by), b_color, 95)
                cv2.circle(frame, (bx, by), CIRCLE_SIZE, b_color, -1)
                new_bullets.append(bullet)
        active_bullets = new_bullets

        new_fb = []
        for msg, color, spawn in feedback_messages:
            f_el = elapsed - spawn
            if f_el < 0.8:
                alpha = 1.0 - (f_el/0.8)
                cv2.putText(frame, msg, (HIT_X - 450, height // 2 + random.randint(-10,10)), 
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

    with open("graph/Ship/coin.txt", "a") as f: f.write(f"{avg_pts_per_orb}\n")
    with open("graph/Ship/hit.txt", "a") as f: f.write(f"{hit_pc}\n")

    def load_data(file):
        data = []
        if os.path.exists(file):
            with open(file, "r") as f:
                for line in f:
                    if line.strip(): data.append(float(line.strip()))
        return data

    coin_history = load_data("graph/Ship/coin.txt")
    hit_history = load_data("graph/Ship/hit.txt")

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