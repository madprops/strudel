import widgets as Widgets
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from subprocess import Popen, PIPE

DEFAULTS = {
    "default_text": lambda: "",
    "voice": lambda: voices[0] if voices else "",
    "speed": lambda: "1.0",
    "volume": lambda: "1.0",
    "synth": lambda: "espeak",
    "width": lambda: 660,
    "height": lambda: 700,
    "background": lambda: "#2d2d2d",
    "title": lambda: "Strudel",
    "num_items": lambda: 50,
}

settings = {}
voice_var = None
speed_var = None
volume_var = None
speech = []
voices = []
volume_combo = None

PAD_X = 5

def get(key):
    value = settings.get(key, DEFAULTS[key]())

    if key in ["num_items"]:
        try:
            return int(value)
        except ValueError:
            return DEFAULTS[key]()

    return value

def set(key, value):
    """Set a setting value and update the global settings dictionary"""
    settings[key] = value

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

def setup():
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
                set(sp[0], sp[1])  # Update global settings
            else:
                print(f"Ignored malformed setting: {s}")
    except Exception as e:
        print(f"Error loading settings: {e}")
        settings = {}  # Reset to empty if there was an error

    get_speech()
    get_voices()

def setup_speed(container):
    global speed_var, speed_map

    # Speed selection with label
    speed_frame = Widgets.create_frame(container)
    speed_frame.pack(side="left", padx=PAD_X)

    speed_label = Widgets.create_label(speed_frame, "Speed:")
    speed_label.pack(side="top", pady=(0, 2))

    # Available speech speeds with descriptive labels
    speed_values = ["2.0", "1.75", "1.5", "1.25", "1.0", "0.75", "0.5", "0.25"]
    speed_labels = ["2.0×", "1.75×", "1.5×", "1.25×", "1.0×", "0.75×", "0.5×", "0.25×"]

    # Create a dictionary to map display labels to actual values
    speed_map = dict(zip(speed_labels, speed_values))

    # Get the current speed value and find its corresponding label
    current_speed = get("speed")

    current_speed_label = next((label for label, value in speed_map.items()
                            if value == current_speed), "1.0×")  # Default to 1.0× if not found

    speed_var = tk.StringVar(value=current_speed_label)

    speed_combo = Widgets.create_combobox(speed_frame, speed_var, speed_labels)
    speed_combo.pack(side="top")

    # Remove focus and highlighting when item is selected
    def handle_speed_select(event):
        # Use tkinter's scheduler to shift focus after a short delay
        window.after(10, lambda: (speed_combo.selection_clear(), window.focus_force()))
        # Get the selected display label and convert to actual value
        selected_label = speed_var.get()
        actual_value = speed_map.get(selected_label, "1.0")  # Default to 1.0 if not found
        # Update settings when speed changes
        set("speed", actual_value)

    speed_combo.bind("<<ComboboxSelected>>", handle_speed_select)

def setup_voice(container):
    global voice_var

    # Voice selection with label
    voice_frame = Widgets.create_frame(container)
    voice_frame.pack(side="left", padx=PAD_X)

    voice_label = Widgets.create_label(voice_frame, "Voice:")
    voice_label.pack(side="top", pady=(0, 2))

    voice_var = tk.StringVar(value=get("voice"))

    voice_combo = Widgets.create_combobox(voice_frame, voice_var, voices)
    voice_combo.pack(side="top")

    # Remove focus and highlighting when item is selected
    def handle_combobox_select(event):
        # Use tkinter's scheduler to shift focus after a short delay
        window.after(1, lambda: (voice_combo.selection_clear(), window.focus_force()))

    voice_combo.bind("<<ComboboxSelected>>", handle_combobox_select)

def setup_volume(container):
    global volume_combo, volume_var, volume_map

    # Volume selection with label
    volume_frame = Widgets.create_frame(container)
    volume_frame.pack(side="left", padx=PAD_X)

    volume_label = Widgets.create_label(volume_frame, "Volume:")
    volume_label.pack(side="top", pady=(0, 2))

    # Available volume levels (1.0 to 0.1) with percentage display
    volume_values = ["1.0", "0.9", "0.8", "0.7", "0.6", "0.5", "0.4", "0.3", "0.2", "0.1"]
    volume_labels = ["100%", "90%", "80%", "70%", "60%", "50%", "40%", "30%", "20%", "10%"]

    # Create a dictionary to map display labels to actual values
    volume_map = dict(zip(volume_labels, volume_values))

    # Get the current volume value and find its corresponding label
    current_volume = get("volume")

    current_volume_label = next((label for label, value in volume_map.items()
                             if value == current_volume), "100%")  # Default to 100% if not found

    volume_var = tk.StringVar(value=current_volume_label)

    volume_combo = Widgets.create_combobox(volume_frame, volume_var, volume_labels)
    volume_combo.pack(side="top")

def get_speech():
    global speech

    num_items = get("num_items")

    try:
        filepath = get_speech_path()
        filepath.touch(exist_ok=True)

        with open(filepath, "r") as file:
            speech = file.read().split("\n")
            # Keep empty strings by removing the filter
            speech = list(map(str.strip, speech))

        # Fill with default text if needed
        for n in range(0, num_items):
            if n >= len(speech):
                speech.append(get("default_text"))
    except Exception as e:
        print(f"Error loading speech: {e}")
        # Create default entries if loading fails
        speech = [get("default_text")] * num_items

def get_voices():
    global voices

    try:
        filepath = get_voices_path()
        filepath.touch(exist_ok=True)

        with open(filepath, "r") as file:
            voices = file.read().split("\n")
            voices = list(map(str.strip, voices))
            voices = list(filter(None, voices))

        # If no voices in file, try getting from synth
        if not voices:
            try:
                process = Popen([get("synth"), "--voices=en"], stdout=PIPE)
                output, _ = process.communicate()

                if output:
                    lines = output.decode().split("\n")

                    # Parse voices from synth output (skip header line)
                    for line in lines[1:]:
                        parts = line.split()

                        if len(parts) > 1:
                            voices.append(parts[3])
            except Exception as e:
                print(f"Error getting synth voices: {e}")
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
            # Don't strip the joined string to preserve empty lines
            file.write("\n".join(speech))
    except Exception as e:
        print(f"Error saving speech: {e}")
        messagebox.showerror("Error", f"Failed to save speech: {e}")

def save():
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

def reset():
    global speech, voices, settings

    """Reset all inputs to default values with confirmation"""
    # Show confirmation dialog
    confirm = messagebox.askyesno("Confirm Reset", "Are you sure you want to reset all inputs to default?")

    if not confirm:
        return

    # Reset all entry fields
    for i, entry in enumerate(input_entries):
        entry.delete(0, tk.END)
        entry.insert(0, get("default_text"))
        speech[i] = get("default_text")

    # Reset voice to first available voice
    if voices:
        voice_var.set(voices[0])
        set("voice", voices[0])

    # Reset speed to default if it exists
    if "speed" in settings:
        speed_var.set("1.0×")  # Set to the label for default speed
        set("speed", "1.0")

    # Reset volume to default
    if "volume" in settings:
        volume_var.set("100%")  # Set to the label for default volume
        set("volume", "1.0")

    # Clear any active filter
    clear_filter()

    # Save changes
    save_speech()
    save()