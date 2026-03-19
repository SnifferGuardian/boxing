import librosa
import numpy as np
import pygame
import time
import cv2
import math

# --- 1. CONFIGURATION ---
AUDIO_FILE = 'GeometryDash/butterfly.mp3'
LANE_COUNT = 12
SENSITIVITY = 0.08 
HOP = 128 
OFFSET = 0.06 
SHOOT_TIME = 1.0  
CIRCLE_SIZE = 35   
HIT_WINDOW = 0.15      # 150ms timing grace
PERFECT_WINDOW = 0.05  # 50ms for "Perfect"
RIPPLE_DURATION = 0.5 

# --- 2. AUDIO ANALYSIS ---
print("Analyzing music... please wait.")
try:
    y, sr = librosa.load(AUDIO_FILE)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
    peaks = librosa.util.peak_pick(onset_env, pre_max=2, post_max=2, pre_avg=3, post_avg=3, delta=SENSITIVITY, wait=5)
    beat_times = librosa.frames_to_time(peaks, sr=sr, hop_length=HOP)
    chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=HOP)
except Exception as e:
    print(f"Error loading audio: {e}")
    exit()

lane_assignments = []
for frame in peaks:
    f = min(frame, chroma.shape[1] - 1)
    lane = np.argmax(chroma[:, f])
    lane_assignments.append(lane)

# --- 3. PYGAME SETUP ---
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

def generate_square_tone(freq):
    duration = 0.1
    t = np.linspace(0, duration, int(44100 * duration), False)
    wave = np.sign(np.sin(2 * np.pi * freq * t)) * 0.15
    audio = (wave * 32767).astype(np.int16)
    stereo_audio = np.repeat(audio[:, np.newaxis], 2, axis=1)
    return pygame.sndarray.make_sound(stereo_audio)

lane_sounds = [generate_square_tone(440 * (2 ** ((i - 9) / 12))) for i in range(12)]
pygame.mixer.music.load(AUDIO_FILE)
pygame.mixer.music.set_volume(0.8)

# --- 4. CV2 & INPUT SETUP ---
width, height = 800, 800
center = (width // 2, height // 2)
max_radius = width // 2 - 80
window_name = "Radial Hero: Ultimate Edition"
cv2.namedWindow(window_name)

mouse_pos = (0, 0)
mouse_clicked = False
key_chars = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=']
keys = [ord(c) for c in key_chars]

def on_mouse(event, x, y, flags, param):
    global mouse_pos, mouse_clicked
    mouse_pos = (x, y)
    if event == cv2.EVENT_LBUTTONDOWN: mouse_clicked = True

cv2.setMouseCallback(window_name, on_mouse)

# --- 5. GAME STATE ---
active_bullets = []
active_ripples = []
feedback_messages = [] 
key_positions = []
for i in range(LANE_COUNT):
    angle = (i / LANE_COUNT) * 2 * math.pi
    tx = int(center[0] + max_radius * math.cos(angle))
    ty = int(center[1] + max_radius * math.sin(angle))
    key_positions.append((tx, ty))

def get_feedback(delta_time):
    ms = int(delta_time * 1000)
    abs_ms = abs(ms)
    prefix = "+" if ms > 0 else ""
    if abs_ms <= PERFECT_WINDOW * 1000:
        return f"PERFECT ({prefix}{ms}ms)", (0, 255, 0)
    elif abs_ms <= HIT_WINDOW * 1000:
        return f"GOOD ({prefix}{ms}ms)", (0, 255, 255)
    return f"MISS ({prefix}{ms}ms)", (0, 0, 255)

# --- 6. MAIN LOOP ---
pygame.mixer.music.play()
game_start_time = time.time()
beat_index = 0

try:
    while pygame.mixer.music.get_busy():
        elapsed = time.time() - game_start_time
        key_pressed = cv2.waitKey(1) & 0xFF
        
        # A. Trigger New Bullets
        if beat_index < len(beat_times):
            if elapsed >= (beat_times[beat_index] - SHOOT_TIME - OFFSET):
                active_bullets.append([lane_assignments[beat_index], elapsed, False])
                beat_index += 1

        frame = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.circle(frame, center, max_radius, (40, 40, 40), 2)

        # Draw Key Guides
        for i in range(LANE_COUNT):
            kx, ky = key_positions[i]
            cv2.circle(frame, (kx, ky), 20, (20, 20, 20), -1)
            cv2.putText(frame, key_chars[i], (kx-8, ky+8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)

        # B. Update Ripples
        new_ripples = []
        for rx, ry, lane, r_start in active_ripples:
            r_prog = (elapsed - r_start) / RIPPLE_DURATION
            if r_prog < 1.0:
                alpha = 1.0 - r_prog
                color = (int(255*alpha*(1-lane/12)), int(200*alpha), int(255*alpha*(lane/12)))
                cv2.circle(frame, (rx, ry), int(80 * r_prog), color, max(1, int(12 * alpha)))
                new_ripples.append([rx, ry, lane, r_start])
        active_ripples = new_ripples

        # C. Process Orbs & Auto-Miss Logic
        new_bullets = []
        for bullet in active_bullets:
            lane, start_time, has_processed = bullet
            bullet_elapsed = elapsed - start_time
            progress = bullet_elapsed / SHOOT_TIME
            
            # --- AUTO-MISS TRIGGER ---
            if not has_processed and progress > (1.0 + HIT_WINDOW):
                feedback_messages.append(["MISS (Too Late)", (0, 0, 255), elapsed])
                bullet[2] = True # Mark as processed
                has_processed = True

            if progress < 1.2:
                angle = (lane / LANE_COUNT) * 2 * math.pi
                curr_dist = min(progress, 1.1) * max_radius
                bx = int(center[0] + curr_dist * math.cos(angle))
                by = int(center[1] + curr_dist * math.sin(angle))
                
                # Check for Input
                hit_detected = False
                if not has_processed:
                    if key_pressed in keys and keys.index(key_pressed) == lane:
                        hit_detected = True
                    elif mouse_clicked:
                        dist = math.sqrt((bx - mouse_pos[0])**2 + (by - mouse_pos[1])**2)
                        if dist < CIRCLE_SIZE + 20: hit_detected = True

                    if hit_detected:
                        delta = bullet_elapsed - SHOOT_TIME
                        if abs(delta) < HIT_WINDOW:
                            msg, color = get_feedback(delta)
                            feedback_messages.append([msg, color, elapsed])
                            lane_sounds[lane].play()
                            bullet[2] = True
                            active_ripples.append([bx, by, lane, elapsed])
                        else:
                            feedback_messages.append(["MISS (Early)", (0, 0, 255), elapsed])
                            bullet[2] = True 

                # Draw ORB
                if not bullet[2]:
                    color = (int(255*(1-lane/12)), 150, int(255*(lane/12)))
                    cv2.circle(frame, (bx, by), int(CIRCLE_SIZE * min(progress, 1.0)), color, -1)
                    new_bullets.append(bullet)
                elif progress < 1.05 and hit_detected: # Quick flash for hit orbs
                    cv2.circle(frame, (bx, by), CIRCLE_SIZE + 10, (255, 255, 255), -1)

        active_bullets = new_bullets

        # D. Feedback Messages
        new_feedback = []
        for msg, color, spawn_time in feedback_messages:
            f_elapsed = elapsed - spawn_time
            if f_elapsed < 0.7:
                alpha = 1.0 - (f_elapsed / 0.7)
                f_color = (int(color[0]*alpha), int(color[1]*alpha), int(color[2]*alpha))
                tx = center[0] - cv2.getTextSize(msg, 0, 0.8, 2)[0][0] // 2
                ty = center[1] - int(f_elapsed * 80)
                cv2.putText(frame, msg, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.8, f_color, 2)
                new_feedback.append([msg, color, spawn_time])
        feedback_messages = new_feedback

        mouse_clicked = False 
        cv2.imshow(window_name, frame)
        if key_pressed == ord('q'): break

except KeyboardInterrupt:
    pass

pygame.mixer.music.stop()
cv2.destroyAllWindows()