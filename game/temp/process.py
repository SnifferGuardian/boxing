import matplotlib.pyplot as plt
import re
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_vals(filename):
    """Extracts numerical values using an absolute path."""
    vals = []
    full_path = os.path.join(BASE_DIR, filename)
    try:
        with open(full_path, 'r') as f:
            for line in f:
                matches = re.findall(r'(\d+\.?\d*)', line)
                if matches:
                    vals.append(float(matches[-1]))
    except FileNotFoundError:
        print(f"File {filename} not found at {full_path}")
    return vals

avg_vals = get_vals('avg.txt')
exvg_vals = get_vals('exvg.txt')

plt.figure("Historical Progress", figsize=(10, 10))
fig, (ax1, ax2) = plt.subplots(2, 1, num="Historical Progress", figsize=(10, 10), sharex=True)
plt.style.use('ggplot')

if avg_vals:
    ax1.plot(range(1, len(avg_vals) + 1), avg_vals, marker='o', label='Avg Speed', color='skyblue', linewidth=2)
    ax1.set_title('Average Speed per Session')
    ax1.set_ylabel('Velocity (px/s)')
    ax1.legend()
else:
    ax1.text(0.5, 0.5, 'No data in avg.txt', ha='center', va='center')

if exvg_vals:
    ax2.plot(range(1, len(exvg_vals) + 1), exvg_vals, marker='s', label='Avg Extension', color='salmon', linewidth=2)
    ax2.set_title('Average Extension per Session')
    ax2.set_xlabel('Session Index')
    ax2.set_ylabel('Extension (px)')
    ax2.legend()
else:
    ax2.text(0.5, 0.5, 'No data in exvg.txt', ha='center', va='center')

plt.tight_layout()

# Updated saving logic:
# Navigate one directory up ('..') and then into the 'assets' folder
target_dir = os.path.abspath(os.path.join(BASE_DIR, '..', 'assets'))
os.makedirs(target_dir, exist_ok=True) # Ensures the folder exists
output_path = os.path.join(target_dir, 'historical_progress_graph.png')

plt.savefig(output_path)
print(f"Graph saved to {output_path}")
plt.show()