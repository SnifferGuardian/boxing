import serial
import time

class ScoreTracker:
    def __init__(self):
        self.current_total = 0.0

    def update(self, raw_input):
        # 1. Clean the serial data (remove \n or \r characters)
        input_str = str(raw_input).lower().strip()

        # 2. Check for Reset/Off triggers
        if input_str in ["off", "reset", "false", "0"]:
            self.current_total = 0.0
            print(f">>> RESET: Score is now {self.current_total}")
            return

        # 3. Numeric Calculation
        try:
            incoming_value = float(input_str)
            self.current_total += incoming_value
            print(f"Recv: {incoming_value} | Total Score: {self.current_total}")
        except ValueError:
            if input_str: # Ignore empty lines
                print(f"Warning: Ignored non-numeric serial data: '{input_str}'")

# --- Serial Configuration ---
PORT = 'COM13'
BAUD_RATE = 9600 # Adjust this to match your device (e.g., Arduino)

tracker = ScoreTracker()

try:
    # Initialize Serial Connection
    with serial.Serial(PORT, BAUD_RATE, timeout=1) as ser:
        print(f"Connected to {PORT} at {BAUD_RATE} baud.")
        print("Waiting for data...")

        while True:
            # Read a line of data from the serial port
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                
                if line:
                    tracker.update(line)
            
            time.sleep(0.01) # Small sleep to prevent high CPU usage

except serial.SerialException as e:
    print(f"Error: Could not open {PORT}. Is it plugged in or used by another app?")
except KeyboardInterrupt:
    print("\nClosing Serial Connection...")