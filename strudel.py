import re
import tkinter as tk
from tkinter import ttk, messagebox
from subprocess import Popen, PIPE
from pathlib import Path
import threading
import signal
import sys

settings = {}
speech = []
voices = []
window = None
num_items = 20  # This could be made configurable in settings
input_entries = []
voice_var = None
speed_var = None  # Variable for speech speed
current_speech_process = None
speech_lock = threading.Lock()

DEFAULT_TEXT = ""  # Default text for speech entries

def main():
    try:
        # Setup signal handler for SIGINT (Ctrl+C)
        signal.signal(signal.SIGINT, signal_handler)

        get_settings()
        get_speech()
        get_voices()
        make_window()

        window.mainloop()
    except Exception as e:
        print(f"Error in main function: {e}")
        messagebox.showerror("Error", f"An error occurred: {e}")

def make_window():
    global window, input_entries, voice_var, speed_var

    window = tk.Tk()
    window.title("Strudel")
    window.configure(bg="#2d2d2d")
    window.geometry("600x700")
    font = ("sans", 16)
    input_entries = []

    # Create main container with scrolling ability
    main_container = tk.Frame(window, bg="#2d2d2d")
    main_container.pack(fill="both", expand=True, padx=10, pady=10)

    # Create canvas with scrollbar for scrolling through items
    canvas = tk.Canvas(main_container, bg="#2d2d2d", highlightthickness=0)
    scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)

    frame = tk.Frame(canvas, bg="#2d2d2d")

    # Configure scrolling
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Create a window inside the canvas for the frame
    canvas_frame = canvas.create_window((0, 0), window=frame, anchor="nw")

    # Configure the canvas to resize with the frame
    def configure_canvas(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfig(canvas_frame, width=event.width)

    frame.bind("<Configure>", configure_canvas)
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_frame, width=e.width))

    # Add mouse wheel scrolling
    def _on_mousewheel(event):
        # Check if the mousewheel event is over a combobox
        widget = window.winfo_containing(event.x_root, event.y_root)
        if isinstance(widget, ttk.Combobox) or "TCombobox" in str(widget):
            return  # Don't scroll the canvas if over a combobox
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)  # Windows and MacOS

    # Filter for Linux scrolling events too
    def _on_scroll_up(event):
        widget = window.winfo_containing(event.x_root, event.y_root)
        if isinstance(widget, ttk.Combobox) or "TCombobox" in str(widget):
            return
        canvas.yview_scroll(-1, "units")

    def _on_scroll_down(event):
        widget = window.winfo_containing(event.x_root, event.y_root)
        if isinstance(widget, ttk.Combobox) or "TCombobox" in str(widget):
            return
        canvas.yview_scroll(1, "units")

    canvas.bind_all("<Button-4>", _on_scroll_up)  # Linux
    canvas.bind_all("<Button-5>", _on_scroll_down)   # Linux

    # Create speech input rows using grid layout
    for n in range(num_items):
        btn = tk.Button(frame, text="Speak", font=("sans", 11), height=1, width=6, command=lambda n=n: speak_callback(n))
        btn.grid(row=n, column=0, padx=5, pady=2, sticky="nsw")

        entry = tk.Entry(frame, width=50, font=("sans", 14))
        entry.insert(0, speech[n])
        entry.grid(row=n, column=1, padx=5, pady=2, sticky="ew")
        input_entries.append(entry)

    # Make the entry columns expand
    frame.grid_columnconfigure(1, weight=1)

    # Bottom controls
    bottom = tk.Frame(window, bg="#2d2d2d")
    bottom.pack(fill="x", pady=(10, 10), padx=10)

    # Voice selection with label
    voice_label = tk.Label(bottom, text="Voice:", bg="#2d2d2d", fg="white", font=("sans", 12))
    voice_label.pack(side="left", padx=(0, 5))

    voice_var = tk.StringVar(value=settings.get("voice", voices[0] if voices else ""))

    # Apply a style to make the combobox match button height
    style = ttk.Style()
    style.configure("Strudel.TCombobox", padding=(0, 4, 0, 4))  # Add padding to match button height

    # Configure the dropdown popup to have larger text and wider arrow
    style.map("TCombobox", fieldbackground=[("readonly", "#ffffff")])
    style.configure("TCombobox", arrowsize=20)  # Make the dropdown arrow wider

    # Configure the dropdown popup list style (for Windows and Linux)
    window.option_add("*TCombobox*Listbox.font", ("sans", 12))

    voice_combo = ttk.Combobox(bottom, textvariable=voice_var, values=voices, width=8,
                               font=("sans", 12), style="Strudel.TCombobox")

    voice_combo.pack(side="left", padx=(0, 10))

    # Remove focus and highlighting when item is selected
    def handle_combobox_select(event):
        # Use tkinter's scheduler to shift focus after a short delay
        window.after(1, lambda: (voice_combo.selection_clear(), window.focus_force()))

    voice_combo.bind("<<ComboboxSelected>>", handle_combobox_select)

    # Tooltip for voice
    tooltip = tk.Label(window, text="", bg="#f0f0f0", fg="#000000", relief="solid", borderwidth=1)
    tooltip.pack_forget()  # Hide initially

    def show_voice_tooltip(event):
        voice = voice_var.get()

        if voice:
            tooltip.config(text=f"Selected: {voice}")
            x = voice_combo.winfo_rootx()
            y = voice_combo.winfo_rooty() + voice_combo.winfo_height()
            tooltip.place(x=x, y=y)

    def hide_voice_tooltip(event):
        tooltip.pack_forget()

    voice_combo.bind("<Enter>", show_voice_tooltip)
    voice_combo.bind("<Leave>", hide_voice_tooltip)

    # Speed selection with label
    speed_label = tk.Label(bottom, text="Speed:", bg="#2d2d2d", fg="white", font=("sans", 12))
    speed_label.pack(side="left", padx=(10, 5))

    # Available speech speeds
    speeds = ["0.5", "0.75", "1.0", "1.25", "1.5", "1.75", "2.0"]
    speed_var = tk.StringVar(value=settings.get("speed", "1.0"))

    speed_combo = ttk.Combobox(bottom, textvariable=speed_var, values=speeds, width=5,
                              font=("sans", 12), style="Strudel.TCombobox")
    speed_combo.pack(side="left", padx=(0, 10))

    # Remove focus and highlighting when item is selected
    def handle_speed_select(event):
        # Use tkinter's scheduler to shift focus after a short delay
        window.after(10, lambda: (speed_combo.selection_clear(), window.focus_force()))
        # Update settings when speed changes
        settings["speed"] = speed_var.get()

    speed_combo.bind("<<ComboboxSelected>>", handle_speed_select)

    # Tooltip for speed
    speed_tooltip = tk.Label(window, text="", bg="#f0f0f0", fg="#000000", relief="solid", borderwidth=1)
    speed_tooltip.pack_forget()  # Hide initially

    def show_speed_tooltip(event):
        speed = speed_var.get()

        if speed:
            speed_tooltip.config(text=f"Speed: {speed}x")
            x = speed_combo.winfo_rootx()
            y = speed_combo.winfo_rooty() + speed_combo.winfo_height()
            speed_tooltip.place(x=x, y=y)

    def hide_speed_tooltip(event):
        speed_tooltip.pack_forget()

    speed_combo.bind("<Enter>", show_speed_tooltip)
    speed_combo.bind("<Leave>", hide_speed_tooltip)

    # Button height to match combobox
    button_height = 1

    # Save button
    save_btn = tk.Button(bottom, text="Save", font=("sans", 11), height=button_height,
                        command=lambda: (save_speech(), save_settings()))
    save_btn.pack(side="right", padx=5)

    # Reset button
    reset_btn = tk.Button(bottom, text="Reset", font=("sans", 11), height=button_height, command=reset_inputs)
    reset_btn.pack(side="right", padx=5)

    # Close button
    close_btn = tk.Button(bottom, text="Close", font=("sans", 11), height=button_height, command=on_closing)
    close_btn.pack(side="right", padx=5)

    # Handle window close event
    window.protocol("WM_DELETE_WINDOW", on_closing)

def on_closing():
    """Handle the window closing event"""
    stop_speech()
    save_speech()
    save_settings()
    window.destroy()
    sys.exit(0)

def speak_callback(n):
    s = input_entries[n].get()
    v = voice_var.get()
    # Update speed setting to current selection
    settings["speed"] = speed_var.get()
    speak(n, s, v)

def stop_speech():
    """Stop any currently running speech"""
    global current_speech_process

    with speech_lock:
        if current_speech_process and current_speech_process.poll() is None:
            try:
                current_speech_process.terminate()
                # Wait briefly for process to terminate
                current_speech_process.wait(timeout=1)
            except Exception as e:
                print(f"Error stopping speech: {e}")
                # Force kill if terminate fails
                try:
                    import os
                    os.kill(current_speech_process.pid, signal.SIGKILL)
                except:
                    pass

def speak_thread(n, s, v):
    """Function to run in a separate thread for speaking"""
    global current_speech_process, speech

    try:
        # Get current speed setting
        speed = settings.get("speed", "1.0")
        # Convert speed to words per minute for espeak (-s option)
        # Default espeak speed is 175 words per minute
        base_wpm = 175
        speed_float = float(speed)
        wpm = int(base_wpm * speed_float)

        with speech_lock:
            current_speech_process = Popen(["espeak", "-v", v, "-s", str(wpm), s], stderr=PIPE)

        # Wait for the process outside the lock to allow other threads to interrupt
        _, error = current_speech_process.communicate()

        with speech_lock:
            if current_speech_process.returncode != 0 and error:
                error_msg = error.decode().strip()
                print(f"espeak error: {error_msg}")
                # Use after() to schedule the messagebox from the main thread
                window.after(0, lambda: messagebox.showerror("Speech Error", f"Failed to speak: {error_msg}"))
                return

            # Voice settings will still be saved
            # (We're not updating speech here anymore as it's done in save_speech)

            # Update voice setting if it changed
            if settings.get("voice") != v:
                settings["voice"] = v
                # Use after() to schedule the save from the main thread
                window.after(0, save_settings)

    except Exception as e:
        print(f"Error running espeak: {e}")
        # Use after() to schedule the messagebox from the main thread
        window.after(0, lambda: messagebox.showerror("Error", f"Failed to run espeak: {e}"))

def speak(n, s, v):
    """Start speech in a separate thread, stopping any current speech first"""
    stop_speech()

    # Start a new thread for speaking
    speech_thread = threading.Thread(target=speak_thread, args=(n, s, v))
    speech_thread.daemon = True  # Make thread exit when main program exits
    speech_thread.start()

def get_settings_path():
    thispath = Path(__file__).parent.resolve()
    filepath = Path(thispath) / "settings.txt"
    return filepath

def get_speech_path():
    thispath = Path(__file__).parent.resolve()
    filepath = Path(thispath) / "speech.txt"
    return filepath

def get_voices_path():
    thispath = Path(__file__).parent.resolve()
    filepath = Path(thispath) / "voices.txt"
    return filepath

def get_settings():
    global settings

    try:
        filepath = get_settings_path()
        filepath.touch(exist_ok=True)

        with open(filepath, "r") as file:
            setts = file.read().split("\n")
            setts = list(map(str.strip, setts))
            setts = list(filter(None, setts))

        settings = {}  # Reset settings before loading

        for s in setts:
            if "=" in s:
                sp = s.split("=", 1)  # Split on first = only
                settings[sp[0]] = sp[1]
            else:
                print(f"Ignored malformed setting: {s}")
    except Exception as e:
        print(f"Error loading settings: {e}")
        settings = {}  # Reset to empty if there was an error

def get_speech():
    global speech

    try:
        filepath = get_speech_path()
        filepath.touch(exist_ok=True)

        with open(filepath, "r") as file:
            speech = file.read().split("\n")
            speech = list(map(str.strip, speech))
            speech = list(filter(None, speech))

        # Fill with default text if needed
        for n in range(0, num_items):
            if n >= len(speech):
                speech.append(DEFAULT_TEXT)
    except Exception as e:
        print(f"Error loading speech: {e}")
        # Create default entries if loading fails
        speech = [DEFAULT_TEXT] * num_items

def get_voices():
    global voices

    try:
        filepath = get_voices_path()
        filepath.touch(exist_ok=True)

        with open(filepath, "r") as file:
            voices = file.read().split("\n")
            voices = list(map(str.strip, voices))
            voices = list(filter(None, voices))

        # If no voices in file, try getting from espeak
        if not voices:
            try:
                process = Popen(["espeak", "--voices=en"], stdout=PIPE)
                output, _ = process.communicate()

                if output:
                    lines = output.decode().split("\n")

                    # Parse voices from espeak output (skip header line)
                    for line in lines[1:]:
                        parts = line.split()
                        if len(parts) > 1:
                            voices.append(parts[3])
            except Exception as e:
                print(f"Error getting espeak voices: {e}")
    except Exception as e:
        print(f"Error loading voices: {e}")
        voices = ["default"]  # Provide at least a default option

def save_speech():
    try:
        # Update the speech list with the current text in all input entries
        for i, entry in enumerate(input_entries):
            if i < len(speech):
                speech[i] = entry.get()
            else:
                speech.append(entry.get())

        filepath = get_speech_path()

        with open(filepath, "w") as file:
            file.write("\n".join(speech).strip())
    except Exception as e:
        print(f"Error saving speech: {e}")
        messagebox.showerror("Error", f"Failed to save speech: {e}")

def save_settings():
    try:
        filepath = get_settings_path()

        with open(filepath, "w") as file:
            settings_text = ""

            for key in settings:
                settings_text += f"{key}={settings[key]}\n"

            file.write(settings_text.strip())
    except Exception as e:
        print(f"Error saving settings: {e}")
        messagebox.showerror("Error", f"Failed to save settings: {e}")

def reset_inputs():
    """Reset all inputs to default values with confirmation"""
    # Show confirmation dialog
    confirm = messagebox.askyesno("Confirm Reset", "Are you sure you want to reset all inputs to default?")
    if not confirm:
        return

    # Reset all entry fields
    for i, entry in enumerate(input_entries):
        entry.delete(0, tk.END)
        entry.insert(0, DEFAULT_TEXT)
        speech[i] = DEFAULT_TEXT

    # Reset voice to first available voice
    if voices:
        voice_var.set(voices[0])
        settings["voice"] = voices[0]

    # Reset speed to default if it exists
    if 'speed' in settings:
        speed_var.set("1.0")
        settings["speed"] = "1.0"

    # Save changes
    save_speech()
    save_settings()

def signal_handler(sig, frame):
    """Handle Ctrl+C by cleaning up and exiting gracefully"""
    print("\nExiting Strudel...")
    if window:
        window.quit()  # Properly terminate the Tkinter main loop
        on_closing()   # Call our cleanup function
    else:
        # If window isn't initialized yet, just exit
        sys.exit(0)

if __name__ == "__main__":
    # Handle Ctrl+C (SIGINT) to stop speech and exit gracefully
    def signal_handler(sig, frame):
        print("Signal received, exiting gracefully...")
        stop_speech()
        save_speech()
        save_settings()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    main()
