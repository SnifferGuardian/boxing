import matplotlib.pyplot as plt
import re
import os

# Ensure we use the correct directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_vals(filename):
    """Extracts all numerical values from a file, line by line."""
    vals = []
    path = os.path.join(BASE_DIR, filename)
    try:
        with open(path, 'r') as f:
            for line in f:
                matches = re.findall(r'(\d+\.?\d*)', line)
                if matches:
                    vals.append(float(matches[-1]))
    except FileNotFoundError:
        print(f"File {filename} not found.")
    return vals

# Source from long-term ledger files
avg_vals = get_vals('avg.txt')
exvg_vals = get_vals('exvg.txt')

# Create historical graph
plt.figure("Historical Long-Term Progress", figsize=(10, 10))
fig, (ax1, ax2) = plt.subplots(2, 1, num="Historical Long-Term Progress", figsize=(10, 10), sharex=True)

if avg_vals:
    ax1.plot(range(1, len(avg_vals) + 1), avg_vals, marker='o', label='Avg Speed', color='skyblue', linewidth=2)
    ax1.set_title('Progress: Average Speed per Session')
    ax1.set_ylabel('Velocity (px/s)')
    ax1.grid(True, linestyle='--', alpha=0.6)
    ax1.legend()
else:
    ax1.text(0.5, 0.5, 'No data in avg.txt', ha='center', va='center')

if exvg_vals:
    ax2.plot(range(1, len(exvg_vals) + 1), exvg_vals, marker='s', label='Avg Extension', color='salmon', linewidth=2)
    ax2.set_title('Progress: Average Extension per Session')
    ax2.set_xlabel('Session Index')
    ax2.set_ylabel('Extension (px)')
    ax2.grid(True, linestyle='--', alpha=0.6)
    ax2.legend()
else:
    ax2.text(0.5, 0.5, 'No data in exvg.txt', ha='center', va='center')

plt.tight_layout()
plt.savefig(os.path.join(BASE_DIR, 'historical_progress_graph.png'))
print("Historical progress graph saved as historical_progress_graph.png")
plt.show()