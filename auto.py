import librosa
import numpy as np
import pygame
import time
import cv2
import math
import random

AUDIO_FILE = 'GeometryDash/Amethyst.mp3'
LANE_COUNT = 12
SENSITIVITY = 0.1
HOP = 96
OFFSET = 0.06 
SHOOT_TIME = 1.0   
CIRCLE_SIZE = 70   

try:
    ser = serial.Serial('COM13', 115200, timeout=1) 
except Exception as e:
    print(f"Serial Error: {e}")
    ser = None


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
    wave = np.sign(np.sin(2 * np.pi * freq * t)) * 0.15 
    audio = (wave * 32767).astype(np.int16)
    stereo_audio = np.repeat(audio[:, np.newaxis], 2, axis=1)
    return pygame.sndarray.make_sound(stereo_audio)
# def generate_square_tone(freq):
#     t = np.linspace(0, 0.1, int(44100 * 0.1), False)
    
#     wave = np.sin(2 * np.pi * freq * t) * 0.3
    
#     fade_out = np.linspace(1.0, 0.0, len(t))
#     wave = wave * fade_out
    
#     audio = (wave * 32767).astype(np.int16)
    
#     return pygame.sndarray.make_sound(np.repeat(audio[:, np.newaxis], 2, axis=1))
lane_sounds = [generate_square_tone(440 * (2 ** ((i - 9) / 12))) for i in range(12)]
pygame.mixer.music.load(AUDIO_FILE)
pygame.mixer.music.set_volume(0.0) 
width, height = 1000, 1000
center = (width // 2, height // 2)
max_radius = width // 2 - 80
window_name = "Automatic Radial Symphony"
cv2.namedWindow(window_name)

active_bullets = []
ring_flash = 0 

pygame.mixer.music.play()
game_start_time = time.time()
beat_index = 0

try:
    while pygame.mixer.music.get_busy():
        elapsed = time.time() - game_start_time
        
        if beat_index < len(beat_times):
            if elapsed >= (beat_times[beat_index] - SHOOT_TIME - OFFSET):
                active_bullets.append([lane_assignments[beat_index], elapsed, False])
                beat_index += 1
                choice = random.randint(1, 4)
                randpin = random.randint(0, 3)
                if choice == 1:
                    with open('cmd.txt', 'w') as f:
                        f.write(f"{randpin},G,700\n")
                else:
                    with open('cmd.txt', 'w') as f:
                        f.write(f"{randpin},G,700\n")

        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        ring_color = (ring_flash, ring_flash, ring_flash)
        cv2.circle(frame, center, max_radius, ring_color, 3)
        ring_flash = max(40, int(ring_flash * 0.9)) 

        new_bullet_list = []
        for bullet in active_bullets:
            lane, start_time, has_played = bullet
            bullet_elapsed = elapsed - start_time
            
            progress = bullet_elapsed / SHOOT_TIME
            
            if progress < 1.1: 
                angle = (lane / LANE_COUNT) * 2 * math.pi
                curr_dist = min(progress, 1.0) * max_radius
                
                x = int(center[0] + curr_dist * math.cos(angle))
                y = int(center[1] + curr_dist * math.sin(angle))
                
                if progress >= 1.0 and not has_played:
                    lane_sounds[lane].play()
                    bullet[2] = True 
                    ring_flash = 255 
                b = int(255 * (1 - lane/12) * progress)
                g = int(150 * progress)
                r = int(255 * (lane/12) * progress)
                
                size = int(CIRCLE_SIZE * progress)
                cv2.circle(frame, (x, y), max(5, size), (b, g, r), -1)
                
                new_bullet_list.append(bullet)

        active_bullets = new_bullet_list
        
        cv2.imshow(window_name, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

except KeyboardInterrupt:
    pass

pygame.mixer.music.stop()
cv2.destroyAllWindows()