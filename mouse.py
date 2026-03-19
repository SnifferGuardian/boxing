import librosa
import numpy as np
import pygame
import time
import cv2
import math

AUDIO_FILE = 'GeometryDash/butterfly.mp3'
LANE_COUNT = 12
SENSITIVITY = 0.08 
HOP = 128 
OFFSET = 0.06 
SHOOT_TIME = 1.0  
CIRCLE_SIZE = 35   
HIT_WINDOW = 0.15  
HIT_THRESHOLD = 0.15
RIPPLE_DURATION = 0.5 

y, sr = librosa.load(AUDIO_FILE)
onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
peaks = librosa.util.peak_pick(onset_env, pre_max=2, post_max=2, pre_avg=3, post_avg=3, delta=SENSITIVITY, wait=5)
beat_times = librosa.frames_to_time(peaks, sr=sr, hop_length=HOP)
chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=HOP)

lane_assignments = []
for frame in peaks:
    f = min(frame, chroma.shape[1] - 1)
    lane = np.argmax(chroma[:, f])
    lane_assignments.append(lane)

pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

def generate_square_tone(freq):
    duration = 0.1
    t = np.linspace(0, duration, int(44100 * duration), False)
    wave = np.sign(np.sin(2 * np.pi * freq * t)) * 0.2
    audio = (wave * 32767).astype(np.int16)
    stereo_audio = np.repeat(audio[:, np.newaxis], 2, axis=1)
    return pygame.sndarray.make_sound(stereo_audio)

lane_sounds = [generate_square_tone(440 * (2 ** ((i - 9) / 12))) for i in range(12)]
pygame.mixer.music.load(AUDIO_FILE)
pygame.mixer.music.set_volume(0.8)

width, height = 800, 800
center = (width // 2, height // 2)
max_radius = width // 2 - 80
window_name = "Radial Hero: Key Guided"
cv2.namedWindow(window_name)

mouse_pos = (0, 0)
mouse_clicked = False

key_chars = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=']
keys = [ord(c) for c in key_chars]

def on_mouse(event, x, y, flags, param):
    global mouse_pos, mouse_clicked
    mouse_pos = (x, y)
    if event == cv2.EVENT_LBUTTONDOWN:
        mouse_clicked = True

cv2.setMouseCallback(window_name, on_mouse)

active_bullets = []
active_ripples = []

key_positions = []
for i in range(LANE_COUNT):
    angle = (i / LANE_COUNT) * 2 * math.pi
    tx = int(center[0] + max_radius * math.cos(angle))
    ty = int(center[1] + max_radius * math.sin(angle))
    key_positions.append((tx, ty))

pygame.mixer.music.play()
game_start_time = time.time()
beat_index = 0

try:
    while pygame.mixer.music.get_busy():
        elapsed = time.time() - game_start_time
        key_pressed = cv2.waitKey(1) & 0xFF
        
        if beat_index < len(beat_times):
            if elapsed >= (beat_times[beat_index] - SHOOT_TIME - OFFSET):
                active_bullets.append([lane_assignments[beat_index], elapsed, False])
                beat_index += 1

        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        cv2.circle(frame, center, max_radius, (40, 40, 40), 2)
        
        for i in range(LANE_COUNT):
            kx, ky = key_positions[i]
            cv2.circle(frame, (kx, ky), 22, (20, 20, 20), -1)
            
            text_color = (150, 150, 150)
            text_size = cv2.getTextSize(key_chars[i], cv2.FONT_HERSHEY_DUPLEX, 0.7, 1)[0]
            text_offset_x = text_size[0] // 2
            text_offset_y = text_size[1] // 2
            
            cv2.putText(frame, key_chars[i], (kx - text_offset_x, ky + text_offset_y), 
                        cv2.FONT_HERSHEY_DUPLEX, 0.7, text_color, 1, cv2.LINE_AA)
            
            angle = (i / LANE_COUNT) * 2 * math.pi
            end_x = int(center[0] + (max_radius + 40) * math.cos(angle))
            end_y = int(center[1] + (max_radius + 40) * math.sin(angle))
            #cv2.line(frame, center, (end_x, end_y), (30, 30, 30), 1)

        new_ripple_list = []
        for rx, ry, lane, r_start_time in active_ripples:
            r_elapsed = elapsed - r_start_time
            if r_elapsed < RIPPLE_DURATION:
                prog = r_elapsed / RIPPLE_DURATION
                alpha = 1.0 - prog
                cv2.circle(frame, (rx, ry), int(70 * prog), 
                           (int(255*alpha*(1-lane/12)), int(200*alpha), int(255*alpha*(lane/12))), 
                           max(1, int(12 * alpha)))
                new_ripple_list.append([rx, ry, lane, r_start_time])
        active_ripples = new_ripple_list

        new_bullet_list = []
        for bullet in active_bullets:
            lane, start_time, has_played = bullet
            bullet_elapsed = elapsed - start_time
            progress = bullet_elapsed / SHOOT_TIME
            
            if progress < 1.1:
                angle = (lane / LANE_COUNT) * 2 * math.pi
                curr_dist = min(progress, 1.0) * max_radius
                bx = int(center[0] + curr_dist * math.cos(angle))
                by = int(center[1] + curr_dist * math.sin(angle))
                
                is_hit_this_frame = False
                
                if key_pressed in keys:
                    if keys.index(key_pressed) == lane and abs(progress - 1.0) < HIT_THRESHOLD:
                        is_hit_this_frame = True
                
                if mouse_clicked:
                    dist_to_mouse = math.sqrt((bx - mouse_pos[0])**2 + (by - mouse_pos[1])**2)
                    if dist_to_mouse < CIRCLE_SIZE + 20 and abs(progress - 1.0) < HIT_THRESHOLD:
                        is_hit_this_frame = True

                if is_hit_this_frame and not has_played:
                    lane_sounds[lane].play()
                    bullet[2] = True 
                    active_ripples.append([bx, by, lane, elapsed])

                if not bullet[2]:
                    color = (int(255*(1-lane/12)), 150, int(255*(lane/12)))
                    size = int(CIRCLE_SIZE * min(progress, 1.0))
                    cv2.circle(frame, (bx, by), size, color, -1)
                    new_bullet_list.append(bullet)
                else:
                    cv2.circle(frame, (bx, by), CIRCLE_SIZE + 5, (255, 255, 255), -1)

        active_bullets = new_bullet_list
        mouse_clicked = False 
        
        cv2.imshow(window_name, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

except KeyboardInterrupt:
    pass

pygame.mixer.music.stop()
cv2.destroyAllWindows()