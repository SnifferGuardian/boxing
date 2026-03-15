import librosa
import numpy as np
import pygame
import time

audio_file = 'GeometryDash/Amethyst.mp3'
print(f"Analyzing {audio_file}...")

y, sr = librosa.load(audio_file)
stft = np.abs(librosa.stft(y))
freqs = librosa.fft_frequencies(sr=sr)

target_bins = np.where((freqs >= 400) & (freqs <= 1000))[0]
avg_energy = np.mean(stft[target_bins, :], axis=0)

peaks = librosa.util.peak_pick(avg_energy, pre_max=3, post_max=3, pre_avg=10, post_avg=10, delta=0.1, wait=10)
beat_times = librosa.frames_to_time(peaks, sr=sr)

print(f"Analysis complete! Found {len(beat_times)} beats.")

pygame.mixer.pre_init(44100, -16, 2, 512) 
pygame.init()

def generate_click():
    """Generates a short 50ms click sound digitally."""
    sample_rate = 44100
    duration = 0.05
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave = np.sin(2 * np.pi * 1000 * t) * 0.3
    fade = np.linspace(1.0, 0.0, len(wave))
    audio = (wave * fade * 32767).astype(np.int16)
    # Create stereo buffer
    stereo_audio = np.repeat(audio[:, np.newaxis], 2, axis=1)
    return pygame.sndarray.make_sound(stereo_audio)

click_sound = generate_click()
pygame.mixer.music.load(audio_file)

print("Starting in 2 seconds...")
time.sleep(2)

pygame.mixer.music.play()
start_time = time.time()
beat_index = 0
offset = 0.00

try:
    while pygame.mixer.music.get_busy():
        elapsed = time.time() - start_time
        
        if beat_index < len(beat_times):
            if elapsed >= (beat_times[beat_index] - offset):
                click_sound.play()
                print(f"Beat {beat_index+1}/{len(beat_times)} at {elapsed:.2f}s")
                beat_index += 1
        
        time.sleep(0.000)

except KeyboardInterrupt:
    pygame.mixer.music.stop()
    print("\nStopped.")