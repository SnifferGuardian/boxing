import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
stop_signal_path = os.path.join(BASE_DIR, "stop_signal.txt")

def stop_the_ai():
    print("Stop signal")
    with open(stop_signal_path, "w") as f:
        f.write("stop")
    print("Signal sent")

if __name__ == "__main__":
    stop_the_ai()