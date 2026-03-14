import os
import time
import threading
import asyncio
from pathlib import Path
import flet as ft
import flet_audio as fta
import serial
import matplotlib.pyplot as plt
import subprocess 
import asyncio
from asyncio import create_subprocess_exec 

powerlist = []
reactionlist = []
script_dir = os.path.dirname(os.path.abspath(__file__))
reaction_path = os.path.join(script_dir, "reaction.txt")
power_path = os.path.join(script_dir, "power.txt")
history_plot_path = os.path.join(script_dir, "history_report.png")
stop_signal_path = os.path.join(script_dir, "temp/stop_signal.txt") 


url = r"C:\Users\Matt\Desktop\yolopose\GeometryDash\1-05. Cycles.mp3"
try:
    ser = serial.Serial('COM13', 9600, timeout=1) 
except Exception as e:
    print(f"Serial Error: {e}")
    ser = None

bpm_input = ft.TextField(label="Enter BPM", width=100, visible=False)

def change_bpm(e):
    if ser and bpm_input.value:
        ser.write(f"{bpm_input.value}\n".encode())

send_custom_btn = ft.ElevatedButton("Send BPM", on_click=change_bpm, visible=False)

def main(page: ft.Page):
    page.title = "Rhythmic Box Controller"
    
    header_text = ft.Text("What do you want to do?", theme_style=ft.TextThemeStyle.DISPLAY_LARGE)
    selec_text = ft.Text("Select the ports used down below!", theme_style=ft.TextThemeStyle.DISPLAY_MEDIUM, visible=False)
    
    
    ports = [
        ft.Switch(label="Port 1", active_color=ft.Colors.GREEN, visible=False, value=False),
        ft.Switch(label="Port 2", active_color=ft.Colors.YELLOW, visible=False, value=False),
        ft.Switch(label="Port 3", active_color=ft.Colors.RED, visible=False, value=False),
        ft.Switch(label="Port 4", active_color=ft.Colors.ORANGE, visible=False, value=False),
        ft.Switch(label="Port 5", active_color=ft.Colors.PURPLE, visible=False, value=False),
        ft.Switch(label="Port 6", active_color=ft.Colors.PINK, visible=False, value=False),
    ]
    async def check_audio_status(e):
   
        if e.state == "completed":
            print("Song finished! Stopping AI and generating results...")
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
    # funct for picking file but atp idc
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
            ser.write("reset_ports\n".encode()) 
            ser.flush()
            await audio_off(e)

    async def send_inactive_ports(e):
        if ser is None:
            print("Error: No Arduino detected. Check your USB cable and COM port.")
            return 

        ser.write("reset_ports\n".encode())
        ser.flush()
        print("Arduino ports reset. Waiting for sync...")
        
        await asyncio.sleep(0.2) 
    
        char_map = ["a", "b", "c", "d", "e", "f"]
    
        for index, p in enumerate(ports):
            if not p.value: 
                msg = f"{char_map[index]}\n"
                ser.write(msg.encode()) 
                ser.flush()
                print(f"Sent Disable command: {char_map[index]}")
                await asyncio.sleep(0.1) 

        print("Sync Complete.")
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
        await off_send(None)  
        await create_subprocess_exec('python', 'temp/pose.py')
        time.sleep(0.2)
        url= r"GeometryDash\1-05. Cycles.mp3"
        bpm = 140  
        if ser and ser.is_open:
            ser.write(f"{bpm}\n".encode())  
        audio.src = url
        await audio.play()
        await power_calc()  

        
    async def electroman_play(e):
        await create_subprocess_exec('python', 'temp/pose.py')
        tracker.reset()
        await off_send(None) 
        time.sleep(0.2)
        url = r"GeometryDash\3-05. Electroman Adventures.mp3"
        bpm = 170  
        if ser and ser.is_open:
            ser.write(f"{bpm}\n".encode())  
        audio.src = url
        await audio.play()
        await power_calc()  
        #await score(none)
    async def geometrical_play(e):
        await create_subprocess_exec('python', 'temp/pose.py')
        tracker.reset()
        await off_send(None)  
        time.sleep(0.2)
        url = r"GeometryDash\5-03. Geometrical Dominator.mp3"
        bpm = 148  # Set your desired BPM here
        if ser and ser.is_open:
            ser.write(f"{bpm}\n".encode())
        audio.src = url
        await audio.play()
        await power_calc()  
        #await score(none)
    async def hexagon_play(e):
        await create_subprocess_exec('python', 'temp/pose.py')
        tracker.reset()
        await off_send(None)
        time.sleep(0.2)
        url = r"GeometryDash\4-09. Hexagon Force.mp3"
        bpm = 81  
        if ser and ser.is_open:
            ser.write(f"{bpm}\n".encode())
        audio.src = url
        await audio.play()
        await power_calc()  
    async def electrodynamix_play(e):
        await create_subprocess_exec('python', 'temp/pose.py')
        tracker.reset()
        await off_send(None)  
        time.sleep(0.2)
        url = r"GeometryDash\Electrodynamix.mp3"
        bpm = 127  
        if ser and ser.is_open:
            ser.write(f"{bpm}\n".encode())
        audio.src = url
        await audio.play()
        await power_calc()  
        #await score(none)
    async def tidalwave_play(e):
        await create_subprocess_exec('python', 'temp/pose.py')
        tracker.reset()
        await off_send(None)  
        time.sleep(0.2)
        url = r"GeometryDash\Dion_Timmer_-_Shiawase_(mp3.pm).mp3"
        bpm = 141 
        if ser and ser.is_open:
            ser.write(f"{bpm}\n".encode())
        audio.src = url
        await audio.play()
        await power_calc()
    async def amethyst_play(e):
        await create_subprocess_exec('python', 'temp/pose.py')
        tracker.reset()
        await off_send(None)  
        time.sleep(0.2)
        url = r"GeometryDash\Amethyst.mp3"
        bpm = 166
        if ser and ser.is_open:
            ser.write(f"{bpm}\n".encode())
        audio.src = url
        await audio.play()
        await power_calc()

    def score():
        while True:
            if ser and ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        tracker.update(line)
                except Exception as e:
                    print(f"Serial Read Error: {e}")
            time.sleep(0.01) 

    thread = threading.Thread(target=score, daemon=True)
    thread.start()

    class ScoreTracker:
        def __init__(self):
            self.current_total = 0.0
        def reset(self):
            self.current_total = 0.0
            print(f">>> RESET: Score is now {self.current_total}")

        def update(self, raw_input):
            input_str = str(raw_input).lower().strip()

            if input_str in ["off", "reset", "false", "0"]:
                self.current_total = 0.0
                reactionlist.clear()
                powerlist.clear()
                print(f">>> RESET: Score and Lists cleared.")
                return

            try:
                parts = input_str.split(",") 
                
                incoming_reaction = int(parts[0])
                
                self.current_total += float(incoming_reaction)

                if len(parts) == 2:
                    incoming_power = int(parts[1])
                    
                    reactionlist.append(incoming_reaction)
                    powerlist.append(incoming_power)
                    
                    print("-" * 67) 
                    print(f"Received Data: '{input_str}'")
                    print(f"HIT")
                    print(f"Reaction: {incoming_reaction} ms")
                    print(f"Power:    {incoming_power}")
                    print(f"Score: {self.current_total}")
                    print(powerlist)
                    print(reactionlist)
                    print("-" * 67) #676767676767

                score_text.value = f"Score: {self.current_total}"
                page.update()

            except (ValueError, IndexError):
                if input_str: 
                    print(f"Warning: Ignored non-numeric serial data: '{input_str}'")    
    tracker = ScoreTracker()

    def toggle_visibility(main=False, ports_view=False, graph=False, game_menu=False, rhythm_game=False):
       
        header_text.visible = main
        show_btn.visible = main
        port_btn.visible = main
        game_btn.visible = main
        off_btn.visible = main
        
        
        selec_text.visible = ports_view
        sync_btn.visible = ports_view
        for p in ports: p.visible = ports_view
        
        
        my_graph.visible = graph
        
        
        rhythmic_btn.visible = game_menu
        
        send_custom_btn.visible = rhythm_game

        cycles_btn.visible = rhythm_game
        electroman_btn.visible = rhythm_game
        geometrical_btn.visible = rhythm_game
        hexagon_btn.visible = rhythm_game
        electrodynamix_btn.visible = rhythm_game
        score_text.visible = rhythm_game
        back_btn.visible = not main
        bpm_input.visible = rhythm_game
        tidalwave_btn.visible = rhythm_game
        amethyst_btn.visible = rhythm_game
        page.update()

    my_graph = ft.Image(src="historical_progress_graph.png", visible=False, width=1200, height=900)
    
    show_btn = ft.ElevatedButton(content=ft.Text("📈 Show Graph", size=45), on_click=show_image, height=100, width=400)
    back_btn = ft.ElevatedButton(content=ft.Text("🏠", size=45), on_click=go_back, height=100, width=400, visible=False)
    port_btn = ft.ElevatedButton(content=ft.Text("⚙️ Port Setup", size=45), on_click=set_ports, height=100, width=400)
    sync_btn = ft.ElevatedButton(content=ft.Text("Upload", size=45), on_click=send_inactive_ports, height=100, width=400, visible=False)
    off_btn = ft.ElevatedButton(content=ft.Text("🛑 Reset", size=45), on_click=off_send, bgcolor=ft.Colors.RED, height=100, width=400)
    game_btn = ft.ElevatedButton(content=ft.Text("🎮 Games?", size=45), on_click=game_page, height=100, width=400)
    rhythmic_btn = ft.ElevatedButton(content=ft.Text("🥊 Boxing!", size=45), on_click=rhythmic_game, visible=False, width=400)
    cycles_btn = ft.ElevatedButton(content=ft.Text("Cycles", size=45), on_click=cycles_play, height=90, width=400)
    electroman_btn = ft.ElevatedButton(content=ft.Text("Electroman", size=45), on_click=electroman_play, height=90, width=400)
    geometrical_btn = ft.ElevatedButton(content=ft.Text("Geometrical Dominator", size=35), on_click=geometrical_play, height=90, width=400)
    hexagon_btn = ft.ElevatedButton(content=ft.Text("Hexagon Force", size=45), on_click=hexagon_play, height=90, width=400)
    electrodynamix_btn = ft.ElevatedButton(content=ft.Text("Electrodynamix", size=45), on_click=electrodynamix_play, height=90, width=400)
    tidalwave_btn = ft.ElevatedButton(content=ft.Text("Tidalwave", size=45), on_click=tidalwave_play, height=90, width=400)
    amethyst_btn = ft.ElevatedButton(content=ft.Text("Amethyst", size=45), on_click=amethyst_play, height=90, width=400)
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
        #bpm_input, 
        #send_custom_btn,
        tidalwave_btn,
        amethyst_btn,
        cycles_btn,
        electroman_btn,
        geometrical_btn,
        hexagon_btn,
        electrodynamix_btn,
        score_text,
        
    )










    async def power_calc():
        reactionlist.clear()
        powerlist.clear()
        print("Recording started... Data is being collected by the background thread.")

        try:
            while not os.path.exists(stop_signal_path):
                await asyncio.sleep(0.5)  
            
            print("Stop signal detected! Processing results...")

        except Exception as e:
            print(f"Error in power_calc loop: {e}")

        if len(reactionlist) > 0:
            cur_avg_r = sum(reactionlist) / len(reactionlist)
            cur_avg_p = sum(powerlist) / len(powerlist)
            hit_results = [0 if r == -30 else 1 for r in reactionlist]
            
            accuracy_percent = (sum(hit_results) / len(hit_results)) * 100
            
            perc_path = os.path.join(script_dir, "perc.txt")

            with open(perc_path, 'a') as f3: 
                f3.write(f"{accuracy_percent:.2f}\n")

            history_perc = []
            if os.path.exists(perc_path):
                with open(perc_path, 'r') as f:
                    history_perc = [float(l.strip()) for l in f if l.strip()]
            
            with open(reaction_path, 'a') as f1: f1.write(f"{cur_avg_r:.2f}\n")
            with open(power_path, 'a') as f2: f2.write(f"{cur_avg_p:.2f}\n")

            history_r = []
            history_p = []
            if os.path.exists(reaction_path):
                with open(reaction_path, 'r') as f:
                    history_r = [float(l.strip()) for l in f if l.strip()]
            if os.path.exists(power_path):
                with open(power_path, 'r') as f:
                    history_p = [float(l.strip()) for l in f if l.strip()]

            plt.style.use('ggplot')
            
            fig1, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6))
            fig1.canvas.manager.set_window_title('Current Session Data')
            ax1.plot(reactionlist, color='tab:blue', label='Reaction Time')
            ax1.axhline(y=cur_avg_r, color='navy', linestyle='--', label=f'Avg: {cur_avg_r:.1f}')
            ax1.set_title("Short-Term: Current Session Reaction")
            
            ax2.plot(powerlist, color='tab:red', label='Power')
            ax2.axhline(y=cur_avg_p, color='darkred', linestyle='--', label=f'Avg: {cur_avg_p:.1f}')
            ax2.set_title("Short-Term: Current Session Power")
            plt.tight_layout()

            # Create 3 subplots instead of 2
            fig2, (ax3, ax4, ax5) = plt.subplots(3, 1, figsize=(9, 9))
            fig2.canvas.manager.set_window_title('Historical Performance')
            
            # Existing Reaction/Power plots
            ax3.plot(history_r, color='blue', marker='o', label='Reaction Avg')
            ax3.set_title("Historical Reaction Time")
            
            ax4.plot(history_p, color='red', marker='s', label='Power Avg')
            ax4.set_title("Historical Power")

            # New Accuracy Percent plot
            ax5.plot(history_perc, color='green', marker='^', label='Accuracy %')
            ax5.set_title("Percent of lights hit")
            ax5.set_ylim(0, 105)  # Percentage is usually 0-100
            ax5.set_ylabel("Percentage (%)")

            plt.tight_layout()
            plt.savefig(history_plot_path)
            plt.show()
    
            plt.savefig(history_plot_path)
            print(f"Historical graph saved: {history_plot_path}")
            
            plt.show() 
        else:
            print("No data was collected during this session.")

        if os.path.exists(stop_signal_path):
            os.remove(stop_signal_path)

ft.app(target=main)