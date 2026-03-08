
from asyncio import subprocess
import os
import threading
import flet as ft
import serial
import time
import flet_audio as fta
from pathlib import Path
url = r"C:\Users\Matt\Desktop\yolopose\GeometryDash\1-05. Cycles.mp3"
try:
    # Open once at start. Ensure Arduino Serial Monitor is CLOSED.
    ser = serial.Serial('COM13', 9600, timeout=1) 
except Exception as e:
    print(f"Serial Error: {e}")
    ser = None

# Global elements for shared access
bpm_input = ft.TextField(label="Enter BPM", width=100, visible=False)

def change_bpm(e):
    if ser and bpm_input.value:
        # Sends whatever is in the text box
        ser.write(f"{bpm_input.value}\n".encode())

send_custom_btn = ft.ElevatedButton("Send BPM", on_click=change_bpm, visible=False)

def main(page: ft.Page):
    page.title = "Rhythmic Box Controller"
    # --- UI TEXT ELEMENTS ---
    header_text = ft.Text("What do you want to do?", theme_style=ft.TextThemeStyle.DISPLAY_LARGE)
    selec_text = ft.Text("Select the ports used down below!", theme_style=ft.TextThemeStyle.DISPLAY_MEDIUM, visible=False)
    
    # --- PORT SWITCHES ---
    ports = [
        ft.Switch(label="Port 1", active_color=ft.Colors.GREEN, visible=False, value=False),
        ft.Switch(label="Port 2", active_color=ft.Colors.YELLOW, visible=False, value=False),
        ft.Switch(label="Port 3", active_color=ft.Colors.RED, visible=False, value=False),
        ft.Switch(label="Port 4", active_color=ft.Colors.ORANGE, visible=False, value=False),
        ft.Switch(label="Port 5", active_color=ft.Colors.PURPLE, visible=False, value=False),
        ft.Switch(label="Port 6", active_color=ft.Colors.PINK, visible=False, value=False),
    ]
    async def check_audio_status(e):
    # Check if the audio has finished playing
        if e.state == "completed":
            print("Song finished! Stopping AI and generating results...")
            # Path to the script that sends the stop signal
            stop_script = os.path.join(os.path.dirname(__file__), "stop_ai.py")
            await subprocess.create_subprocess_exec('python', stop_script)

    audio = fta.Audio(
        src=url,
        autoplay=False,
        volume=1,
        balance=0,
        release_mode=fta.ReleaseMode.STOP,
        on_loaded=lambda _: print("Loaded"),
        on_duration_change=lambda e: print("Duration changed:", e.duration),
        on_position_change=lambda e: print("Position changed:", e.position),
        on_state_change=check_audio_status,
        on_seek_complete=lambda _: print("Seek complete"),
    )
    # --- SERIAL FUNCTIONALITY ---
    # async def handle_pick_files(e: ft.Event[ft.Button]):
    #     files = await ft.FilePicker().pick_files(allow_multiple=True)
    #     selected_files.value = (
    #         ", ".join(map(lambda f: f.name, files)) if files else "Cancelled!"
    #     )
    #     print(selected_files.value)
    #     full_path = get_absolute_path("")
    #     url = f"{full_path}\GeometryDash\{selected_files.value}"
    #     print(full_path)
    #     print(url)
    async def audio_off(e):
        await audio.seek(position=0)
        await audio.pause()

    async def off_send(e):
        tracker.reset()
        if ser:
            ser.write("off\n".encode())
            ser.flush()
            await audio_off(e)

    async def send_inactive_ports(e):
        await off_send(e)  # Reset all ports first
        char_map = ["a", "b", "c", "d", "e", "f"]
        
        if ser and ser.is_open:
            print("Syncing unselected ports...")
            for index, p in enumerate(ports):
                if not p.value:
                    char_to_send = char_map[index]
                    ser.write(f"{char_to_send}\n".encode())
                    time.sleep(0.1)
        else:
            print("Serial port not available.")

    # --- NAVIGATION LOGIC ---
    def show_image(e):
        toggle_visibility(graph=True)

    def set_ports(e):
        toggle_visibility(ports_view=True)

    def game_page(e):
        toggle_visibility(game_menu=True)

    def rhythmic_game(e):
        toggle_visibility(rhythm_game=True)

    def go_back(e):
        toggle_visibility(main=True)
    async def cycles_play(e):
        tracker.reset()
        await off_send(None)  # Ensure all ports are reset before starting the game
        await subprocess.create_subprocess_exec('python', 'temp/pose.py')
        time.sleep(0.2)
        url= r"C:\Users\Matt\Desktop\yolopose\GeometryDash\1-05. Cycles.mp3"
        bpm = 140  # Set your desired BPM here
        if ser and ser.is_open:
            ser.write(f"{bpm}\n".encode())  # Send BPM to Arduino
        audio.src = url
        await audio.play()

        #await score(none)  # Start listening for score updates from Arduino
    async def electroman_play(e):
        await subprocess.create_subprocess_exec('python', 'temp/pose.py')
        tracker.reset()
        await off_send(None)  # Ensure all ports are reset before starting the game
        time.sleep(0.2)
        url = r"C:\Users\Matt\Desktop\yolopose\GeometryDash\3-05. Electroman Adventures.mp3"
        bpm = 170  # Set your desired BPM here
        if ser and ser.is_open:
            ser.write(f"{bpm}\n".encode())  # Send BPM to Arduino
        audio.src = url
        await audio.play()
        #await score(none)
    async def geometrical_play(e):
        await subprocess.create_subprocess_exec('python', 'temp/pose.py')
        tracker.reset()
        await off_send(None)  # Ensure all ports are reset before starting the game
        time.sleep(0.2)
        url = r"C:\Users\Matt\Desktop\yolopose\GeometryDash\5-03. Geometrical Dominator.mp3"
        bpm = 148  # Set your desired BPM here
        if ser and ser.is_open:
            ser.write(f"{bpm}\n".encode())
        audio.src = url
        await audio.play()
        #await score(none)
    async def hexagon_play(e):
        await subprocess.create_subprocess_exec('python', 'temp/pose.py')
        tracker.reset()
        await off_send(None)  # Ensure all ports are reset before starting the game
        time.sleep(0.2)
        url = r"C:\Users\Matt\Desktop\yolopose\GeometryDash\4-09. Hexagon Force.mp3"
        bpm = 81  # Set your desired BPM here
        if ser and ser.is_open:
            ser.write(f"{bpm}\n".encode())
        audio.src = url
        await audio.play()
    async def electrodynamix_play(e):
        await subprocess.create_subprocess_exec('python', 'temp/pose.py')
        tracker.reset()
        await off_send(None)  # Ensure all ports are reset before starting the game
        time.sleep(0.2)
        url = r"C:\Users\Matt\Desktop\yolopose\GeometryDash\Electrodynamix.mp3"
        bpm = 127  # Set your desired BPM here
        if ser and ser.is_open:
            ser.write(f"{bpm}\n".encode())
        audio.src = url
        await audio.play()
        #await score(none)

    def score():
        while True:
            if ser and ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        tracker.update(line)
                        # Optional: page.update() if you add a score label to the UI
                except Exception as e:
                    print(f"Serial Read Error: {e}")
            time.sleep(0.01) # Small sleep to prevent 100% CPU usage

    # Start the background thread once when the app starts
    thread = threading.Thread(target=score, daemon=True)
    thread.start()

    class ScoreTracker:
        def __init__(self):
            self.current_total = 0.0
        def reset(self):
            self.current_total = 0.0
            print(f">>> RESET: Score is now {self.current_total}")

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
                score_text.value = f"Score: {self.current_total}"
                page.update()
            except ValueError:
                if input_str: # Ignore empty lines
                    print(f"Warning: Ignored non-numeric serial data: '{input_str}'")
    tracker = ScoreTracker()

    def toggle_visibility(main=False, ports_view=False, graph=False, game_menu=False, rhythm_game=False):
        # Handle Main Menu visibility
        header_text.visible = main
        show_btn.visible = main
        port_btn.visible = main
        game_btn.visible = main
        off_btn.visible = main
        
        # Handle Port Setup visibility
        selec_text.visible = ports_view
        sync_btn.visible = ports_view
        for p in ports: p.visible = ports_view
        
        # Handle Graph visibility
        my_graph.visible = graph
        
        # Handle Game Menu visibility
        rhythmic_btn.visible = game_menu
        
        # Handle Rhythmic Mode (BPM) visibility
        #bpm_input.visible = rhythm_game
        send_custom_btn.visible = rhythm_game

        cycles_btn.visible = rhythm_game
        electroman_btn.visible = rhythm_game
        geometrical_btn.visible = rhythm_game
        hexagon_btn.visible = rhythm_game
        electrodynamix_btn.visible = rhythm_game
        score_text.visible = rhythm_game
        #audio_btn.visible = rhythm_game
        
        #selected_btn.visible = main
        # Handle Global Back Button
        back_btn.visible = not main
        page.update()

    # --- UI COMPONENTS ---
    my_graph = ft.Image(src="historical_progress_graph.png", visible=False, width=1200, height=900)
    
    show_btn = ft.ElevatedButton(content=ft.Text("📈 Show Graph", size=45), on_click=show_image, height=100, width=400)
    back_btn = ft.ElevatedButton(content=ft.Text("🏠", size=45), on_click=go_back, height=100, width=400, visible=False)
    port_btn = ft.ElevatedButton(content=ft.Text("⚙️ Port Setup", size=45), on_click=set_ports, height=100, width=400)
    sync_btn = ft.ElevatedButton(content=ft.Text("Upload", size=45), on_click=send_inactive_ports, height=100, width=400, visible=False)
    off_btn = ft.ElevatedButton(content=ft.Text("🛑 Reset", size=45), on_click=off_send, bgcolor=ft.Colors.RED, height=100, width=400)
    game_btn = ft.ElevatedButton(content=ft.Text("🎮 Games?", size=45), on_click=game_page, height=100, width=400)
    rhythmic_btn = ft.ElevatedButton(content=ft.Text("🥊 Boxing!", size=45), on_click=rhythmic_game, visible=False, width=400)
    cycles_btn = ft.ElevatedButton(content=ft.Text("Cycles", size=45), on_click=cycles_play, height=100, width=400)
    electroman_btn = ft.ElevatedButton(content=ft.Text("Electroman", size=45), on_click=electroman_play, height=100, width=400)
    geometrical_btn = ft.ElevatedButton(content=ft.Text("Geometrical Dominator", size=35), on_click=geometrical_play, height=100, width=400)
    hexagon_btn = ft.ElevatedButton(content=ft.Text("Hexagon Force", size=45), on_click=hexagon_play, height=100, width=400)
    electrodynamix_btn = ft.ElevatedButton(content=ft.Text("Electrodynamix", size=45), on_click=electrodynamix_play, height=100, width=400)
    score_text = ft.Text(f"Score: {tracker.current_total}", size=135)
    page.add(
        header_text, 
        show_btn, 
        port_btn, 
        game_btn, 
        off_btn, 
        back_btn, 
        my_graph, 
        selec_text, 
        *ports, 
        sync_btn,
        rhythmic_btn,
        bpm_input, 
        #send_custom_btn,
        cycles_btn,
        electroman_btn,
        geometrical_btn,
        hexagon_btn,
        electrodynamix_btn,
        score_text,
    )

ft.app(target=main)