import librosa
import numpy as np
import pygame
import time
import cv2

AUDIO_FILE = 'GeometryDash/b.mp3'
LANE_COUNT = 12
SENSITIVITY = 0.03
HOP = 128 
OFFSET = 0.06 

print(f"Analyzing {AUDIO_FILE} for full AV playback...")
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
    duration = 0.06
    t = np.linspace(0, duration, int(44100 * duration), False)
    wave = np.sign(np.sin(2 * np.pi * freq * t)) * 0.1 
    audio = (wave * 32767 * 0.7).astype(np.int16) 
    stereo_audio = np.repeat(audio[:, np.newaxis], 2, axis=1)
    return pygame.sndarray.make_sound(stereo_audio)

lane_sounds = [generate_square_tone(440 * (2 ** ((i - 9) / 12))) for i in range(12)]

pygame.mixer.music.load(AUDIO_FILE)
pygame.mixer.music.set_volume(1) 

width, height = 1200, 400
lane_width = width // LANE_COUNT
cv2.namedWindow("Melody Blast", cv2.WINDOW_NORMAL)
lane_brightness = np.zeros(LANE_COUNT)

print("\n--- STARTING FULL PLAYBACK ---")
time.sleep(1)

pygame.mixer.music.play()
start_time = time.time()
beat_index = 0

try:
    while pygame.mixer.music.get_busy():
        elapsed = time.time() - start_time
        
        if beat_index < len(beat_times):
            if elapsed >= (beat_times[beat_index] - OFFSET):
                lane = lane_assignments[beat_index]
                lane_brightness[lane] = 255 
                lane_sounds[lane].play()
                beat_index += 1
        
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        for i in range(LANE_COUNT):
            b = int(lane_brightness[i] * (1 - i/12))
            g = int(lane_brightness[i] * 1)
            r = int(lane_brightness[i] * (i/12))
            
            cv2.rectangle(frame, (i * lane_width, 0), ((i+1) * lane_width, height), (b, g, r), -1)
            
            lane_brightness[i] *= 0.98 
            if lane_brightness[i] < 0: lane_brightness[i] = 0

        cv2.imshow("Melody Blast", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            pygame.mixer.music.stop()
            break

except KeyboardInterrupt:
    pygame.mixer.music.stop()
    print("\nStopped.")

cv2.destroyAllWindows()