import librosa
import numpy as np
import pygame
import time
import cv2
import math
import random

# ... [Previous Constants stay the same] ...
AUDIO_FILE = 'GeometryDash/flamewall3.mp3'
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
KEY_TIMEOUT = 0.15 

# NEW SCORING CONSTANTS
SCORE = 0
POINTS_PERFECT = 100
POINTS_GOOD = 50
POINTS_MISS = -25
POINTS_PENALTY = -500

# ... [Audio loading and chroma analysis stays the same] ...
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
    
    # NEW: 1:4 Ratio for Penalty Orbs
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
        'is_penalty': is_penalty # New attribute
    })

# ... [Pygame init and lane_sounds remain the same] ...
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

def generate_tone(freq):
    t = np.linspace(0, 0.1, int(44100 * 0.1), False)
    wave = np.sign(np.sin(2 * np.pi * freq * t)) * 0.15
    audio = (wave * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(np.repeat(audio[:, np.newaxis], 2, axis=1))

lane_sounds = [generate_tone(440 * (2 ** ((i - 9) / 12))) for i in range(12)]
pygame.mixer.music.load(AUDIO_FILE)

width, height = 1000, 1000
center = (width // 2, height // 2)
max_radius = width // 2 - 80
window_name = "Radial Hero: Penalty Orbs"
cv2.namedWindow(window_name)

# ... [Key handling and key_positions remain the same] ...
key_chars = ['=', '-', '0', '9', '8', '7', '6', '5', '4', '3', '2', '1']
keys_list = [ord(c) for c in key_chars]
key_states = {k: False for k in keys_list}
key_fresh_press = {k: False for k in keys_list}
last_seen_key = {k: 0 for k in keys_list} 

def update_keys(current_key_code, current_time):
    global key_fresh_press
    for k in key_fresh_press: key_fresh_press[k] = False
    if current_key_code in keys_list:
        if not key_states[current_key_code]: key_fresh_press[current_key_code] = True
        key_states[current_key_code] = True
        last_seen_key[current_key_code] = current_time
    for k in keys_list:
        if current_time - last_seen_key[k] > KEY_TIMEOUT: key_states[k] = False

# Mouse callback
mouse_down = False
mouse_pos = (0,0)
def on_mouse(event, x, y, flags, param):
    global mouse_down, mouse_pos
    mouse_pos = (x,y)
    if event == cv2.EVENT_LBUTTONDOWN: mouse_down = True
    if event == cv2.EVENT_LBUTTONUP: mouse_down = False
cv2.setMouseCallback(window_name, on_mouse)

key_positions = []
for i in range(LANE_COUNT):
    angle = 2 * math.pi - ((i / LANE_COUNT) * 2 * math.pi)
    tx = int(center[0] + max_radius * math.cos(angle))
    ty = int(center[1] + max_radius * math.sin(angle))
    key_positions.append((tx, ty))

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
        
        raw_key = cv2.waitKey(1) & 0xFF
        update_keys(raw_key, now) 

        if beat_index < len(notes):
            n = notes[beat_index]
            if elapsed >= (n['time'] - SHOOT_TIME - OFFSET):
                # Added 'is_penalty' to the bullet list: [lane, start, state, is_hold, dur, is_penalty]
                active_bullets.append([n['lane'], elapsed, 0, n['is_hold'], n['duration'], n['is_penalty']])
                beat_index += 1

        frame = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.circle(frame, center, max_radius, (40, 40, 40), 2)
        
        # DRAW SCORE
        cv2.putText(frame, f"SCORE: {SCORE}", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)

        for i in range(LANE_COUNT):
            kx, ky = key_positions[i]
            cv2.putText(frame, key_chars[i], (kx-8, ky+8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)

        # Ripple processing (Same as before)
        new_ripples = []
        for rx, ry, lane, r_start in active_ripples:
            r_prog = (elapsed - r_start) / RIPPLE_DURATION
            if r_prog < 1.0:
                alpha = 1.0 - r_prog
                cv2.circle(frame, (rx, ry), int(100 * r_prog), (255, 255, 255), max(1, int(10 * alpha)))
                new_ripples.append([rx, ry, lane, r_start])
        active_ripples = new_ripples

        new_bullets = []
        for bullet in active_bullets:
            lane, start_time, state, is_hold, dur, is_penalty = bullet
            bullet_elapsed = elapsed - start_time
            progress = bullet_elapsed / SHOOT_TIME
            angle = 2 * math.pi - ((lane / LANE_COUNT) * 2 * math.pi)
            bx, by = int(center[0] + (progress * max_radius) * math.cos(angle)), int(center[1] + (progress * max_radius) * math.sin(angle))

            current_lane_key = keys_list[lane]
            is_pressing = key_states[current_lane_key]
            is_fresh = key_fresh_press[current_lane_key]
            
            mouse_near = math.sqrt((bx-mouse_pos[0])**2 + (by-mouse_pos[1])**2) < CIRCLE_SIZE + 20
            if mouse_near and mouse_down:
                is_pressing = True
                if state == 0: is_fresh = True

            if state == 0: 
                delta = bullet_elapsed - SHOOT_TIME
                # HIT LOGIC
                if abs(delta) < HIT_WINDOW and is_fresh:
                    if is_penalty:
                        # HITTING A RED ORB
                        SCORE += POINTS_PENALTY
                        feedback_messages.append(["DANGER! -500", (0, 0, 255), elapsed])
                        bullet[2] = 2 # Mark as dead/missed
                    else:
                        # HITTING A NORMAL ORB
                        is_perfect = abs(delta) <= PERFECT_WINDOW
                        SCORE += POINTS_PERFECT if is_perfect else POINTS_GOOD
                        
                        msg = "PERFECT" if is_perfect else "GOOD"
                        color = (0, 255, 0) if is_perfect else (0, 255, 255)
                        feedback_messages.append([f"{msg} (+{int(delta*1000)}ms)", color, elapsed])
                        
                        lane_sounds[lane].play()
                        active_ripples.append([bx, by, lane, elapsed])
                        bullet[2] = 3 if is_hold else 1
                
                # MISS LOGIC
                elif progress > (1.0 + HIT_WINDOW):
                    if not is_penalty: # Only lose points for missing regular notes
                        SCORE += POINTS_MISS
                        feedback_messages.append(["MISS", (0, 0, 255), elapsed])
                    bullet[2] = 2

            elif state == 3: # HOLD LOGIC
                if not is_pressing:
                    feedback_messages.append(["DROPPED!", (0, 165, 255), elapsed])
                    bullet[2] = 2
                elif progress > (1.0 + (dur / SHOOT_TIME)): 
                    SCORE += 50 # Bonus for finishing hold
                    feedback_messages.append(["HELD!", (255, 255, 0), elapsed])
                    bullet[2] = 1

            # DRAWING
            if bullet[2] in [0, 3]:
                if is_penalty:
                    color = (0, 0, 255) # Bright Red for Penalty
                else:
                    color = (0, 255, 255) if bullet[2] == 3 else (int(255*(1-lane/12)), 150, int(255*(lane/12)))
                
                if is_hold:
                    tail_p = max(0, progress - 0.2)
                    tx, ty = int(center[0] + (tail_p * max_radius) * math.cos(angle)), int(center[1] + (tail_p * max_radius) * math.sin(angle))
                    cv2.line(frame, (bx, by), (tx, ty), color, 8)
                
                cv2.circle(frame, (bx, by), int(CIRCLE_SIZE * min(progress, 1.0)), color, -1)
                new_bullets.append(bullet)

        active_bullets = new_bullets

        # Feedback text processing (Same as before)
        new_fb = []
        for msg, color, spawn in feedback_messages:
            f_el = elapsed - spawn
            if f_el < 0.7:
                alpha = 1.0 - (f_el/0.7)
                tx = center[0] - cv2.getTextSize(msg, 0, 0.8, 2)[0][0] // 2
                cv2.putText(frame, msg, (tx, center[1] - int(f_el * 100)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 
                            (int(color[0]*alpha), int(color[1]*alpha), int(color[2]*alpha)), 2)
                new_fb.append([msg, color, spawn])
        feedback_messages = new_fb

        cv2.imshow(window_name, frame)
        if raw_key == ord('q'): break

except KeyboardInterrupt: pass
pygame.mixer.music.stop()
cv2.destroyAllWindows()