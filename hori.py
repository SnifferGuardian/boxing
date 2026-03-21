import librosa
import numpy as np
import pygame
import time
import cv2
import math
import random
from ultralytics import YOLO

AUDIO_FILE = 'GeometryDash/flamewall3.mp3'  
MODEL_PATH = 'temp/yolo11n-pose.engine'  
LANE_COUNT = 12
SENSITIVITY = 0.08 
HOP = 128
OFFSET = 0.06 

SHOOT_TIME = 1   
width, height = 2000, 1000 
CIRCLE_SIZE = 50   
HIT_WINDOW = 0.15
PERFECT_WINDOW = 0.05
RIPPLE_DURATION = 0.5 
EXPLOSION_DURATION = 0.4  
HOLD_THRESHOLD = 0.2 

SCORE = 0
POINTS_PERFECT = 100
POINTS_GOOD = 50
POINTS_MISS = -25
POINTS_PENALTY = -500

TRACK_INDICES = [9, 10, 13, 14] 

print("Analyzing audio")
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

window_name = "Explosive Line Hero"
cv2.namedWindow(window_name)

def map_to_line(x, y, cam_w, cam_h):
    """Locks the X coordinate to the HIT_X line."""
    gy = y / cam_h * height
    return int(HIT_X), int(gy)

model = YOLO(MODEL_PATH)
cap = cv2.VideoCapture(0)
pygame.mixer.music.load(AUDIO_FILE)

active_bullets = []
active_ripples = []
active_explosions = [] 
feedback_messages = [] 
beat_index = 0
pygame.mixer.music.play()
game_start_time = time.time()

try:
    while pygame.mixer.music.get_busy():
        now = time.time()
        elapsed = now - game_start_time
        
        ret, frame_cam = cap.read()
        if not ret: break
        cam_h, cam_w, _ = frame_cam.shape
        
        results = model(frame_cam, verbose=False, stream=True)
        tracked_points = []
        for r in results:
            if r.keypoints is not None:
                kps = r.keypoints.xy.cpu().numpy()
                if len(kps) > 0:
                    person = kps[0] 
                    for idx in TRACK_INDICES:
                        if idx < len(person):
                            kp = person[idx]
                            if kp[0] > 0 and kp[1] > 0:
                                tracked_points.append(map_to_line(kp[0], kp[1], cam_w, cam_h))

        if beat_index < len(notes):
            n = notes[beat_index]
            if elapsed >= (n['time'] - SHOOT_TIME - OFFSET):
                active_bullets.append([n['lane'], elapsed, 0, n['is_hold'], n['duration'], n['is_penalty']])
                beat_index += 1

        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        cv2.line(frame, (HIT_X, 0), (HIT_X, height), (100, 100, 100), 8)
        cv2.putText(frame, f"SCORE: {SCORE}", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)

        for (tx, ty) in tracked_points:
            cv2.circle(frame, (tx, ty), 35, (255, 0, 255), -1)
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
                cv2.circle(frame, (ex, ey), int(200 * e_prog), (0, 69, 255), -1) # Red
                cv2.circle(frame, (ex, ey), int(120 * e_prog), (0, 165, 255), -1) # Orange 
                cv2.circle(frame, (ex, ey), int(60 * e_prog), (0, 255, 255), -1)  # Yellow 
                new_explosions.append([ex, ey, e_start])
        active_explosions = new_explosions

        new_bullets = []
        for bullet in active_bullets:
            lane, start_time, state, is_hold, dur, is_penalty = bullet
            bullet_elapsed = elapsed - start_time
            progress = bullet_elapsed / SHOOT_TIME
            
            bx = int(SPAWN_X + (progress * (HIT_X - SPAWN_X)))
            by = int((lane + 0.5) * (height / LANE_COUNT))

            is_touching = False
            for (tx, ty) in tracked_points:
                if abs(by - ty) < (CIRCLE_SIZE + 40) and abs(bx - tx) < 80:
                    is_touching = True
                    break

            if state == 0: 
                delta = bullet_elapsed - SHOOT_TIME
                if abs(delta) < HIT_WINDOW and is_touching:
                    if is_penalty:
                        SCORE += POINTS_PENALTY
                        feedback_messages.append(["DANGER!", (0, 0, 255), elapsed])
                        
                        active_explosions.append([bx, by, elapsed])
                        bullet[2] = 2 
                    else:
                        is_perfect = abs(delta) <= PERFECT_WINDOW
                        SCORE += POINTS_PERFECT if is_perfect else POINTS_GOOD
                        msg = "PERFECT" if is_perfect else "GOOD"
                        feedback_messages.append([msg, (0, 255, 0) if is_perfect else (0, 255, 255), elapsed])
                        lane_sounds[lane].play()
                        active_ripples.append([bx, by, lane, elapsed])
                        bullet[2] = 3 if is_hold else 1
                elif progress > (1.0 + HIT_WINDOW):
                    if not is_penalty:
                        SCORE += POINTS_MISS
                        feedback_messages.append(["MISS", (0, 0, 150), elapsed])
                    bullet[2] = 2

            elif state == 3: 
                if not is_touching:
                    feedback_messages.append(["DROPPED!", (0, 165, 255), elapsed])
                    bullet[2] = 2
                elif progress > (1.0 + (dur / SHOOT_TIME)): 
                    SCORE += 50
                    feedback_messages.append(["HELD!", (255, 255, 0), elapsed])
                    bullet[2] = 1

            if bullet[2] in [0, 3]:
                b_color = (0, 0, 255) if is_penalty else ((0, 255, 255) if state == 3 else (255, 200, 0))
                if is_hold:
                    tail_p = max(0, progress - 0.2)
                    tx_tail = int(SPAWN_X + (tail_p * (HIT_X - SPAWN_X)))
                    cv2.line(frame, (bx, by), (tx_tail, by), b_color, 95)
                
                cv2.circle(frame, (bx, by), CIRCLE_SIZE, b_color, -1)
                new_bullets.append(bullet)

        active_bullets = new_bullets

        new_fb = []
        for msg, color, spawn in feedback_messages:
            f_el = elapsed - spawn
            if f_el < 0.8:
                alpha = 1.0 - (f_el/0.8)
                cv2.putText(frame, msg, (HIT_X - 250, height // 2), 
                            cv2.FONT_HERSHEY_SIMPLEX, 2.0, 
                            (int(color[0]*alpha), int(color[1]*alpha), int(color[2]*alpha)), 5)
                new_fb.append([msg, color, spawn])
        feedback_messages = new_fb

        cv2.imshow(window_name, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

except KeyboardInterrupt: pass
cap.release()
pygame.mixer.music.stop()
cv2.destroyAllWindows()