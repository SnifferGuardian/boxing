import os

# Get the path to the current directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
stop_signal_path = os.path.join(BASE_DIR, "stop_signal.txt")

def stop_the_ai():
    print("Sending stop signal to AI...")
    # Create an empty file to act as the signal
    with open(stop_signal_path, "w") as f:
        f.write("stop")
    print("Signal sent. The AI should now close and save results.")

if __name__ == "__main__":
    stop_the_ai()