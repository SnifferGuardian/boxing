import librosa
import numpy as np
import pygame
import time

AUDIO_FILE = 'GeometryDash/Amethyst.mp3'
LANE_COUNT = 12  
OFFSET = 0.04   

#Lower = more notes; it catches quite taps, Higher = fewer notes
SENSITIVITY = 0.07 
#Smaller = faster detection (128 is 4x faster than default) idk i made it a composer
HOP = 128 
#Minimum frames between notes (5 is ~0.03 seconds)
MIN_DISTANCE = 5 

print(f"Analyzing {AUDIO_FILE} for a 12-lane melody...")
y, sr = librosa.load(AUDIO_FILE)

onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP, aggregate=np.median)

peaks = librosa.util.peak_pick(
    onset_env, 
    pre_max=2, post_max=2, pre_avg=3, post_avg=3, 
    delta=SENSITIVITY, 
    wait=MIN_DISTANCE
)

beat_times = librosa.frames_to_time(peaks, sr=sr, hop_length=HOP)

chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=HOP)

lane_assignments = []
note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

for frame in peaks:
    f = min(frame, chroma.shape[1] - 1)
    lane = np.argmax(chroma[:, f])
    lane_assignments.append(lane)

print(f"Analysis complete! Found {len(beat_times)} notes mapped to 12 lanes.")

pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

def generate_tone(freq):
    duration = 0.04
    t = np.linspace(0, duration, int(44100 * duration), False)
    wave = np.sin(2 * np.pi * freq * t) * 0.3
    fade = np.linspace(1.0, 0.0, len(wave))
    audio = (wave * fade * 32767).astype(np.int16)
    stereo_audio = np.repeat(audio[:, np.newaxis], 2, axis=1)
    return pygame.sndarray.make_sound(stereo_audio)

lane_sounds = []
for i in range(12):
    freq = 440 * (2 ** ((i - 9) / 12))
    lane_sounds.append(generate_tone(freq))

pygame.mixer.music.load(AUDIO_FILE)
print("\n--- MUSIC STARTING (12 Lanes) ---")
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
                
                display = ["."] * 12
                display[lane] = "\033[1;35m█\033[0m" #I FOUND IT ON THE INTERNET AND I THINK IT LOOKS COOL IDK
                current_note = note_names[lane]
                
                print(f"{''.join(display)} | {current_note.ljust(3)} | {elapsed:.2f}s")
                
                lane_sounds[lane].play()
                beat_index += 1
        
        time.sleep(0.0005)

except KeyboardInterrupt:
    pygame.mixer.music.stop()
    print("\nStopped.")