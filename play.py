import librosa
import numpy as np
import pygame
import time
import cv2
import math
import random
from ultralytics import YOLO

AUDIO_FILE = 'GeometryDash/grief.mp3'  
MODEL_PATH = 'temp/yolo11n-pose.engine'  
LANE_COUNT = 12
SENSITIVITY = 0.08 
HOP = 128
OFFSET = 0.06 
SHOOT_TIME = 1.0  
CIRCLE_SIZE = 50   
HIT_WINDOW = 0.15
PERFECT_WINDOW = 0.05
RIPPLE_DURATION = 0.5 
HOLD_THRESHOLD = 0.2 

SCORE = 0
POINTS_PERFECT = 100
POINTS_GOOD = 50
POINTS_MISS = -25
POINTS_PENALTY = -500

TRACK_INDICES = [9, 10, 15, 16] 

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
            
    notes.append({
        'time': t, 
        'lane': lane, 
        'is_hold': is_hold, 
        'duration': duration,
        'is_penalty': is_penalty 
    })

pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

def generate_tone(freq):
    t = np.linspace(0, 0.1, int(44100 * 0.1), False)
    wave = np.sign(np.sin(2 * np.pi * freq * t)) * 0.15
    audio = (wave * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(np.repeat(audio[:, np.newaxis], 2, axis=1))

lane_sounds = [generate_tone(440 * (2 ** ((i - 9) / 12))) for i in range(12)]

width, height = 1000, 1000
center = (width // 2, height // 2)
max_radius = width // 2 - 80
window_name = "Radial Hero: Pose Edition"
cv2.namedWindow(window_name)

def map_to_ring(x, y, cam_w, cam_h):
    """Maps camera coordinates to the circular game ring."""
    gx = width - (x / cam_w * width)
    gy = y / cam_h * height
    
    dx = gx - center[0]
    dy = gy - center[1]
    dist = math.sqrt(dx**2 + dy**2)
    
    if dist == 0: return center
    
    constrained_x = center[0] + (dx / dist) * max_radius
    constrained_y = center[1] + (dy / dist) * max_radius
    return int(constrained_x), int(constrained_y)

model = YOLO(MODEL_PATH)
cap = cv2.VideoCapture(0)
pygame.mixer.music.load(AUDIO_FILE)

active_bullets = []
active_ripples = []
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
                                tracked_points.append(map_to_ring(kp[0], kp[1], cam_w, cam_h))

        if beat_index < len(notes):
            n = notes[beat_index]
            if elapsed >= (n['time'] - SHOOT_TIME - OFFSET):
                active_bullets.append([n['lane'], elapsed, 0, n['is_hold'], n['duration'], n['is_penalty']])
                beat_index += 1

        frame = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.circle(frame, center, max_radius, (40, 40, 40), 2)
        cv2.putText(frame, f"SCORE: {SCORE}", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)

        for (tx, ty) in tracked_points:
            cv2.circle(frame, (tx, ty), 25, (255, 0, 255), -1)
            cv2.circle(frame, (tx, ty), 30, (255, 255, 255), 2)  #magenta

        new_ripples = []
        for rx, ry, lane, r_start in active_ripples:
            r_prog = (elapsed - r_start) / RIPPLE_DURATION
            if r_prog < 1.0:
                alpha = 1.0 - r_prog
                cv2.circle(frame, (rx, ry), int(120 * r_prog), (255, 255, 255), max(1, int(12 * alpha)))
                new_ripples.append([rx, ry, lane, r_start])
        active_ripples = new_ripples

        new_bullets = []
        for bullet in active_bullets:
            lane, start_time, state, is_hold, dur, is_penalty = bullet
            bullet_elapsed = elapsed - start_time
            progress = bullet_elapsed / SHOOT_TIME
            angle = 2 * math.pi - ((lane / LANE_COUNT) * 2 * math.pi)
            bx, by = int(center[0] + (progress * max_radius) * math.cos(angle)), int(center[1] + (progress * max_radius) * math.sin(angle))

            is_touching = False
            for (tx, ty) in tracked_points:
                if math.sqrt((bx - tx)**2 + (by - ty)**2) < (CIRCLE_SIZE + 40):
                    is_touching = True
                    break

            if state == 0: 
                delta = bullet_elapsed - SHOOT_TIME
                if abs(delta) < HIT_WINDOW and is_touching:
                    if is_penalty:
                        SCORE += POINTS_PENALTY
                        feedback_messages.append(["DANGER! -500", (0, 0, 255), elapsed])
                        bullet[2] = 2 
                    else:
                        is_perfect = abs(delta) <= PERFECT_WINDOW
                        SCORE += POINTS_PERFECT if is_perfect else POINTS_GOOD
                        msg = "PERFECT" if is_perfect else "GOOD"
                        color = (0, 255, 0) if is_perfect else (0, 255, 255)
                        feedback_messages.append([f"{msg} ({int(delta*1000)}ms)", color, elapsed])
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
                    tx, ty = int(center[0] + (tail_p * max_radius) * math.cos(angle)), int(center[1] + (tail_p * max_radius) * math.sin(angle))
                    cv2.line(frame, (bx, by), (tx, ty), b_color, 10)
                
                cv2.circle(frame, (bx, by), int(CIRCLE_SIZE * min(progress, 1.0)), b_color, -1)
                new_bullets.append(bullet)

        active_bullets = new_bullets

        new_fb = []
        for msg, color, spawn in feedback_messages:
            f_el = elapsed - spawn
            if f_el < 0.8:
                alpha = 1.0 - (f_el/0.8)
                tx = center[0] - cv2.getTextSize(msg, 0, 1.0, 2)[0][0] // 2
                cv2.putText(frame, msg, (tx, center[1] - int(f_el * 120)), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 
                            (int(color[0]*alpha), int(color[1]*alpha), int(color[2]*alpha)), 3)
                new_fb.append([msg, color, spawn])
        feedback_messages = new_fb

        cv2.imshow(window_name, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

except KeyboardInterrupt: pass
cap.release()
pygame.mixer.music.stop()
cv2.destroyAllWindows()