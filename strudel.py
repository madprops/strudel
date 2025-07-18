import os
import re
import tkinter as tk
import threading
import signal
import sys
from tkinter import ttk, messagebox
from subprocess import Popen, PIPE
from pathlib import Path

settings = {}
speech = []
voices = []
window = None
input_entries = []
row_frames = []     # Store references to row frames containing all elements
voice_var = None
speed_var = None  # Variable for speech speed
volume_var = None  # Variable for speech volume
current_speech_process = None
speech_lock = threading.Lock()
filtered_indices = None  # Track which entries are currently filtered (shown)
frame = None  # The frame containing the input entries
filter_var = None  # Variable for filter input
filter_entry = None  # The filter entry widget
canvas = None

PAD_X = 5
BUTTON_SIZE = 10
ENTRY_FONT = ("sans", 14)

def main():
    try:
        # Setup signal handler for SIGINT (Ctrl+C)
        # Signal handling needs to be set up immediately for both SIGINT and SIGTERM
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Make sure Python's signal handling works during Tkinter's mainloop
        # by ensuring signals are checked regularly
        def check_signals():
            # Check signals every 100ms
            window.after(100, check_signals)

        get_settings()
        get_speech()
        get_voices()
        make_window()
        start_keyboard_detection()

        # Start the signal checking loop once window is created
        window.after(100, check_signals)
        window.after(100, focus_filter())

        window.mainloop()
    except Exception as e:
        print(f"Error in main function: {e}")
        messagebox.showerror("Error", f"An error occurred: {e}")

def make_window():
    global window, input_entries, voice_var, speed_var, speed_map, volume_var, volume_map, filtered_indices, frame, filter_var, filter_entry, row_frames, canvas

    window = tk.Tk()
    window.title(get_title())
    window.configure(bg=get_background())
    window.geometry(f"{get_width()}x{get_height()}")  # Set initial size

    # Initialize filtered_indices as None (no filtering)
    filtered_indices = None

    # Set application icon
    try:
        icon_path = os.path.join(os.path.dirname(__file__), "strudel.png")

        if not os.path.exists(icon_path):
            # Fall back to jpg if png doesn't exist
            icon_path = os.path.join(os.path.dirname(__file__), "strudel.jpg")

        if os.path.exists(icon_path):
            icon = tk.PhotoImage(file=icon_path)
            window.iconphoto(True, icon)
    except Exception as e:
        print(f"Error setting window icon: {e}")

    font = ("sans", 16)
    input_entries = []

    # Create top controls for voice, speed, and volume - centered at the top
    top_controls = tk.Frame(window, bg="#2d2d2d", height=60)  # Set fixed height to give space for buttons at bottom
    top_controls.pack(fill="x", pady=(10, 5), padx=(5, 5))
    top_controls.pack_propagate(False)  # Prevent the frame from shrinking to fit its contents

    # Center container for voice, speed, and volume controls
    controls_container = tk.Frame(top_controls, bg="#2d2d2d")
    controls_container.pack(side="left", fill="x", expand=True)

    # Apply a style to make the combobox match button height
    style = ttk.Style()
    style.configure("Strudel.TCombobox", padding=(0, 4, 0, 4))  # Add padding to match button height

    # Configure the dropdown popup to have larger text and wider arrow
    style.map("TCombobox", fieldbackground=[("readonly", "#ffffff")])
    style.configure("TCombobox", arrowsize=20)  # Make the dropdown arrow wider

    # Configure the dropdown popup list style (for Windows and Linux)
    window.option_add("*TCombobox*Listbox.font", ("sans", 12))

    # Voice selection with label
    voice_frame = tk.Frame(controls_container, bg="#2d2d2d")
    voice_frame.pack(side="left", padx=PAD_X)

    voice_label = tk.Label(voice_frame, text="Voice:", bg="#2d2d2d", fg="white", font=("sans", 12))
    voice_label.pack(side="top", pady=(0, 2))

    voice_var = tk.StringVar(value=get_voice())

    voice_combo = ttk.Combobox(voice_frame, textvariable=voice_var, values=voices, width=8,
                              font=("sans", 12), style="Strudel.TCombobox")

    voice_combo.pack(side="top")

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
    speed_frame = tk.Frame(controls_container, bg="#2d2d2d")
    speed_frame.pack(side="left", padx=PAD_X)

    speed_label = tk.Label(speed_frame, text="Speed:", bg="#2d2d2d", fg="white", font=("sans", 12))
    speed_label.pack(side="top", pady=(0, 2))

    # Available speech speeds with descriptive labels
    speed_values = ["2.0", "1.75", "1.5", "1.25", "1.0", "0.75", "0.5", "0.25"]
    speed_labels = ["2.0×", "1.75×", "1.5×", "1.25×", "1.0×", "0.75×", "0.5×", "0.25×"]

    # Create a dictionary to map display labels to actual values
    speed_map = dict(zip(speed_labels, speed_values))

    # Get the current speed value and find its corresponding label
    current_speed = get_speed()

    current_speed_label = next((label for label, value in speed_map.items()
                            if value == current_speed), "1.0×")  # Default to 1.0× if not found

    speed_var = tk.StringVar(value=current_speed_label)

    speed_combo = ttk.Combobox(speed_frame, textvariable=speed_var, values=speed_labels, width=5,
                             font=("sans", 12), style="Strudel.TCombobox")

    speed_combo.pack(side="top")

    # Remove focus and highlighting when item is selected
    def handle_speed_select(event):
        # Use tkinter's scheduler to shift focus after a short delay
        window.after(10, lambda: (speed_combo.selection_clear(), window.focus_force()))
        # Get the selected display label and convert to actual value
        selected_label = speed_var.get()
        actual_value = speed_map.get(selected_label, "1.0")  # Default to 1.0 if not found
        # Update settings when speed changes
        settings["speed"] = actual_value

    speed_combo.bind("<<ComboboxSelected>>", handle_speed_select)

    # Tooltip for speed
    speed_tooltip = tk.Label(window, text="", bg="#f0f0f0", fg="#000000", relief="solid", borderwidth=1)
    speed_tooltip.pack_forget()  # Hide initially

    def show_speed_tooltip(event):
        speed_label = speed_var.get()

        if speed_label:
            speed_tooltip.config(text=f"Speed: {speed_label}")
            x = speed_combo.winfo_rootx()
            y = speed_combo.winfo_rooty() + speed_combo.winfo_height()
            speed_tooltip.place(x=x, y=y)

    def hide_speed_tooltip(event):
        speed_tooltip.pack_forget()

    speed_combo.bind("<Enter>", show_speed_tooltip)
    speed_combo.bind("<Leave>", hide_speed_tooltip)

    # Volume selection with label
    volume_frame = tk.Frame(controls_container, bg="#2d2d2d")
    volume_frame.pack(side="left", padx=PAD_X)

    volume_label = tk.Label(volume_frame, text="Volume:", bg="#2d2d2d", fg="white", font=("sans", 12))
    volume_label.pack(side="top", pady=(0, 2))

    # Available volume levels (1.0 to 0.1) with percentage display
    volume_values = ["1.0", "0.9", "0.8", "0.7", "0.6", "0.5", "0.4", "0.3", "0.2", "0.1"]
    volume_labels = ["100%", "90%", "80%", "70%", "60%", "50%", "40%", "30%", "20%", "10%"]

    # Create a dictionary to map display labels to actual values
    volume_map = dict(zip(volume_labels, volume_values))

    # Get the current volume value and find its corresponding label
    current_volume = get_volume()

    current_volume_label = next((label for label, value in volume_map.items()
                             if value == current_volume), "100%")  # Default to 100% if not found

    volume_var = tk.StringVar(value=current_volume_label)

    volume_combo = ttk.Combobox(volume_frame, textvariable=volume_var, values=volume_labels, width=5,
                              font=("sans", 12), style="Strudel.TCombobox")

    volume_combo.pack(side="top")

    # Bottom controls - positioned at the right side and vertically aligned to the bottom
    buttons = tk.Frame(top_controls, bg="#2d2d2d")
    buttons.pack(side="right", fill="y", anchor="s")

    # Button height to match combobox
    button_height = 1

    # Save button
    save_btn = tk.Button(buttons, text="Save", font=("sans", BUTTON_SIZE), height=button_height,
                        command=lambda: (save_speech(), save_settings()))

    save_btn.pack(side="right", padx=PAD_X, anchor="s", pady=(0, 5))

    # Reset button
    reset_btn = tk.Button(buttons, text="Reset", font=("sans", BUTTON_SIZE), height=button_height, command=reset_inputs)
    reset_btn.pack(side="right", padx=PAD_X, anchor="s", pady=(0, 5))

    # Close button
    close_btn = tk.Button(buttons, text="Close", font=("sans", BUTTON_SIZE), height=button_height, command=on_closing)
    close_btn.pack(side="right", padx=PAD_X, anchor="s", pady=(0, 5))

    # Remove focus and highlighting when item is selected
    def handle_volume_select(event):
        # Use tkinter's scheduler to shift focus after a short delay
        window.after(10, lambda: (volume_combo.selection_clear(), window.focus_force()))
        # Get the selected display label and convert to actual value
        selected_label = volume_var.get()
        actual_value = volume_map.get(selected_label, "1.0")  # Default to 1.0 if not found
        # Update settings when volume changes
        settings["volume"] = actual_value

    volume_combo.bind("<<ComboboxSelected>>", handle_volume_select)

    # Tooltip for volume
    volume_tooltip = tk.Label(window, text="", bg="#f0f0f0", fg="#000000", relief="solid", borderwidth=1)
    volume_tooltip.pack_forget()  # Hide initially

    def show_volume_tooltip(event):
        volume_label = volume_var.get()

        if volume_label:
            volume_tooltip.config(text=f"Volume: {volume_label}")
            x = volume_combo.winfo_rootx()
            y = volume_combo.winfo_rooty() + volume_combo.winfo_height()
            volume_tooltip.place(x=x, y=y)

    def hide_volume_tooltip(event):
        volume_tooltip.pack_forget()

    volume_combo.bind("<Enter>", show_volume_tooltip)
    volume_combo.bind("<Leave>", hide_volume_tooltip)

    # Filter functionality is now implemented at the top of the window

    # Create main container with scrolling ability
    main_container = tk.Frame(window, bg="#2d2d2d")
    main_container.pack(fill="both", expand=True, padx=10, pady=5)

    # Create canvas with scrollbar for scrolling through items
    canvas = tk.Canvas(main_container, bg="#2d2d2d", highlightthickness=0)
    scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)

    # Use the global frame variable
    global frame
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
        try:
            # Check if the mousewheel event is over a combobox
            widget = window.winfo_containing(event.x_root, event.y_root)
            if isinstance(widget, ttk.Combobox) or "TCombobox" in str(widget):
                return  # Don't scroll the canvas if over a combobox
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except KeyError:
            # Skip scrolling when dropdown is active
            pass

    canvas.bind_all("<MouseWheel>", _on_mousewheel)  # Windows and MacOS

    # Filter for Linux scrolling events too
    def _on_scroll_up(event):
        try:
            widget = window.winfo_containing(event.x_root, event.y_root)

            if isinstance(widget, ttk.Combobox) or "TCombobox" in str(widget):
                return

            canvas.yview_scroll(-1, "units")
        except KeyError:
            # Skip scrolling when dropdown is active
            pass

    def _on_scroll_down(event):
        try:
            widget = window.winfo_containing(event.x_root, event.y_root)

            if isinstance(widget, ttk.Combobox) or "TCombobox" in str(widget):
                return

            canvas.yview_scroll(1, "units")
        except KeyError:
            # Skip scrolling when dropdown is active
            pass

    canvas.bind_all("<Button-4>", _on_scroll_up)  # Linux
    canvas.bind_all("<Button-5>", _on_scroll_down)   # Linux

    # Clear any previous references
    row_frames = []
    input_entries = []

    for n in range(get_num_items()):
        # Create a frame for this row
        row_frame = tk.Frame(frame, bg="#2d2d2d")
        row_frame.grid(row=n, column=0, sticky="ew", padx=0, pady=1)
        row_frames.append(row_frame)

        # Add the speak button
        btn = tk.Button(row_frame, text="Speak", font=("sans", 10), height=1, width=6,
                      command=lambda n=n: speak_callback(n))

        btn.pack(side="left", padx=(0, 5), pady=2)

        entry = create_entry(row_frame)
        entry.insert(0, speech[n])
        entry.pack(side="left", padx=0, pady=2, fill="x", expand=True)
        input_entries.append(entry)

        # Button container for up/down buttons
        button_container = tk.Frame(row_frame, bg="#2d2d2d")
        button_container.pack(side="right", padx=5)

        # Up button
        up_btn = tk.Button(button_container, text="▲", font=("sans", BUTTON_SIZE), height=1, width=1,
                          command=lambda n=n: move_item_up(n))

        up_btn.pack(side="left", padx=(2, 0))

        # Down button
        down_btn = tk.Button(button_container, text="▼", font=("sans", BUTTON_SIZE), height=1, width=1,
                            command=lambda n=n: move_item_down(n))

        down_btn.pack(side="left", padx=(0, 5))

    # Make the row frames expand horizontally
    frame.grid_columnconfigure(0, weight=1)

    # --- BOTTOM ---

    bottom_controls = tk.Frame(window, bg="#2d2d2d", height=50)  # Set fixed height to give space for buttons at bottom
    bottom_controls.pack(fill="x", pady=(0, 0), padx=0)
    bottom_controls.pack_propagate(False)  #
    # Add filter input above the speech entries
    filter_frame = tk.Frame(bottom_controls, bg="#2d2d2d")
    filter_frame.pack(fill="x", pady=(0, 5), padx=10)

    filter_var = tk.StringVar()
    filter_entry = create_entry(filter_frame)
    filter_entry.configure(textvariable=filter_var)
    filter_entry.pack(side="left", fill="x", expand=True, pady=(5, 5))

    # Bind Escape key to clear the filter
    filter_entry.bind("<Escape>", lambda e: clear_filter())    # Clear button for the filter

    # Use the global clear_filter function
    clear_filter_btn = tk.Button(filter_frame, text="Clear", font=("sans", BUTTON_SIZE),
                              command=clear_filter)

    clear_filter_btn.pack(side="right", padx=(5, 0), pady=(5, 5))

    # Bind the filter entry to update filtering on text change
    def on_filter_change(*args):
        # Get the current filter text
        current_filter = filter_var.get()
        apply_filter(current_filter)

    # Use both write and read traces to ensure it catches all changes
    filter_var.trace_add("write", on_filter_change)

    # Handle window close event
    window.protocol("WM_DELETE_WINDOW", on_closing)

def on_closing():
    """Handle the window closing event"""
    stop_speech()

    # Make sure all entries are visible before saving
    if filtered_indices is not None:
        filter_var.set("")
        apply_filter("")  # This will restore all items in their proper grid positions

    save_speech()
    save_settings()
    window.destroy()
    sys.exit(0)

def speak_callback(n, entry=None):
    if not entry:
      entry = input_entries[n]

    s = entry.get().strip()

    if not s:
      return

    v = voice_var.get()
    # Update speed setting to current selection - convert from label to value
    selected_speed_label = speed_var.get()
    settings["speed"] = speed_map.get(selected_speed_label, "1.0")

    # Update volume setting to current selection - convert from label to value
    selected_volume_label = volume_var.get()
    settings["volume"] = volume_map.get(selected_volume_label, "1.0")

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
                    os.kill(current_speech_process.pid, signal.SIGKILL)
                except:
                    pass

def speak_thread(n, s, v):
    """Function to run in a separate thread for speaking"""
    global current_speech_process, speech

    try:
        # Get current speed setting
        speed = get_speed()
        # Get current volume setting
        volume = get_volume()

        # Convert speed to words per minute for synth (-s option)
        # Default synth speed is 175 words per minute
        base_wpm = 175

        try:
            speed_float = float(speed)
            wpm = int(base_wpm * speed_float)
        except (ValueError, TypeError):
            # Default to normal speed if conversion fails
            wpm = base_wpm

        # Convert volume to amplitude percentage for synth (-a option)
        # Default is 100, our UI shows 0.1 to 1.0
        try:
            volume_float = float(volume)
            amplitude = int(volume_float * 100)  # Convert to percentage (0-100)
        except (ValueError, TypeError):
            # Default to full volume if conversion fails
            amplitude = 100

        with speech_lock:
            current_speech_process = Popen([get_synth(), "-v", v, "-s", str(wpm), "-a", str(amplitude), s], stderr=PIPE)

        # Wait for the process outside the lock to allow other threads to interrupt
        _, error = current_speech_process.communicate()

        with speech_lock:
            if current_speech_process.returncode != 0 and error:
                error_msg = error.decode().strip()
                print(f"Synth error: {error_msg}")
                # Use after() to schedule the messagebox from the main thread
                window.after(0, lambda: messagebox.showerror("Speech Error", f"Failed to speak: {error_msg}"))
                return

            # Voice settings will still be saved
            # (We're not updating speech here anymore as it's done in save_speech)

            # Update voice setting if it changed
            if get_voice() != v:
                settings["voice"] = v
                # Use after() to schedule the save from the main thread
                window.after(0, save_settings)

    except Exception as e:
        print(f"Error running synth: {e}")
        # Use after() to schedule the messagebox from the main thread
        window.after(0, lambda: messagebox.showerror("Error", f"Failed to run synth: {e}"))

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

def get_default_text():
  return settings.get("default_text", "")

def get_voice():
  return settings.get("voice", voices[0] if voices else "")

def get_speed():
  return settings.get("speed", "1.0")

def get_volume():
  return settings.get("volume", "1.0")

def get_synth():
  return settings.get("synth", "espeak")

def get_width():
  return settings.get("width", 660)

def get_height():
  return settings.get("height", 700)

def get_background():
  return settings.get("background", "#2d2d2d")

def get_title():
  return settings.get("title", "Strudel")

def get_num_items():
  # Convert num_items to int, with 50 as default
  try:
    return int(settings.get("num_items", 50))
  except ValueError:
    return 50

def get_speech():
    global speech

    num_items = get_num_items()

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
                speech.append(get_default_text())
    except Exception as e:
        print(f"Error loading speech: {e}")
        # Create default entries if loading fails
        speech = [get_default_text()] * num_items

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
                process = Popen([get_synth(), "--voices=en"], stdout=PIPE)
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
        entry.insert(0, get_default_text())
        speech[i] = get_default_text()

    # Reset voice to first available voice
    if voices:
        voice_var.set(voices[0])
        settings["voice"] = voices[0]

    # Reset speed to default if it exists
    if "speed" in settings:
        speed_var.set("1.0×")  # Set to the label for default speed
        settings["speed"] = "1.0"

    # Reset volume to default
    if "volume" in settings:
        volume_var.set("100%")  # Set to the label for default volume
        settings["volume"] = "1.0"

    # Clear any active filter
    clear_filter()

    # Save changes
    save_speech()
    save_settings()

def signal_handler(sig, frame):
    """Handle Ctrl+C by cleaning up and exiting gracefully"""
    print("\nExiting Strudel...")

    # Stop any speech if running
    try:
        stop_speech()
    except:
        pass

    # Don't try to interact with the window - it might be causing the hang
    # Force immediate exit with os._exit which doesn't run cleanup handlers
    os._exit(0)

def clear_filter():
    """Clear the filter and show all entries"""
    if filter_var:
        filter_var.set("")
        apply_filter("")

        # Try to focus the filter entry if it exists
        if "filter_entry" in globals():
            filter_entry.focus_set()

def apply_filter(filter_text):
    """Filter the speech entries based on the given text"""
    global filtered_indices

    scroll_to_top()

    # Ensure we have a clean starting point
    filter_text = filter_text.strip()

    # Make sure we have all the widgets we need
    num_items = get_num_items()

    if len(row_frames) != num_items or len(input_entries) != num_items:
        print(f"Warning: Widget count mismatch. Expected {num_items}, got {len(row_frames)} row frames, "
              f"{len(input_entries)} entries")

        return

    # If no filter text, show all entries
    if not filter_text:
        filtered_indices = None

        # Show all entry rows
        for n in range(num_items):
            # Use grid with the correct row to restore position
            row_frames[n].grid(row=n, column=0, sticky="ew", padx=0, pady=1)

        return

    # Convert filter to lowercase for case-insensitive comparison
    filter_text = filter_text.lower()

    # Create a list to store indices of entries that match the filter
    filtered_indices = []

    # Counter for visible rows to ensure compact display
    visible_row = 0

    # Check each entry against the filter
    for n in range(num_items):
        if n < len(input_entries):
            entry_text = input_entries[n].get().lower()

            if filter_text in entry_text:
                filtered_indices.append(n)
                # Show this entry row and reposition it to be compact
                row_frames[n].grid(row=visible_row, column=0, sticky="ew", padx=0, pady=1)
                visible_row += 1
            else:
                # Completely remove this entry from the grid
                row_frames[n].grid_forget()

def move_item_up(index):
    save_speech()

    """Move a speech item up in the list (swap with the item above it)"""
    if index <= 0:
        return  # Can't move the first item up

    # Swap entries in the speech list
    speech[index], speech[index-1] = speech[index-1], speech[index]

    # Update the text in the entries
    input_entries[index].delete(0, tk.END)
    input_entries[index].insert(0, speech[index])

    input_entries[index-1].delete(0, tk.END)
    input_entries[index-1].insert(0, speech[index-1])

    # Save the updated order
    save_speech()

    # Re-apply filter if there is active filtering
    if filtered_indices is not None:
        # Re-apply the current filter
        filter_text = filter_var.get()

        if filter_text:
            apply_filter(filter_text)

def move_item_down(index):
    save_speech()

    """Move a speech item down in the list (swap with the item below it)"""
    if index >= len(speech) - 1:
        return  # Can't move the last item down

    # Swap entries in the speech list
    speech[index], speech[index+1] = speech[index+1], speech[index]

    # Update the text in the entries
    input_entries[index].delete(0, tk.END)
    input_entries[index].insert(0, speech[index])

    input_entries[index+1].delete(0, tk.END)
    input_entries[index+1].insert(0, speech[index+1])

    # Save the updated order
    save_speech()

    # Re-apply filter if there is active filtering
    if filtered_indices is not None:
        # Re-apply the current filter
        filter_text = filter_var.get()

        if filter_text:
            apply_filter(filter_text)

def focus_filter():
    """Focus the filter entry."""
    if "filter_entry" in globals():
        filter_entry.focus_set()

def start_keyboard_detection():
    """Register keyboard event bindings to the window for shortcuts.

    This function sets up event bindings for:
    - Enter key to play the first non-empty entry
    - Ctrl+1 through Ctrl+0 to play entries 1-10
    """
    window.bind("<Key>", handle_keyboard_shortcuts)

def handle_keyboard_shortcuts(event):
    """Handle keyboard shortcuts for playing speech entries.
    Enter key: Play the first non-empty entry
    """
    # Handle Enter key to play first non-empty input
    if event.keysym == "Return":
        # Get focused entry
        focused_entry = get_focused_entry()

        if focused_entry:
            speak_callback(None, focused_entry)
        else:
            # Find the first non-empty entry
            for i, entry in enumerate(input_entries):

                if filtered_indices:
                    if i not in filtered_indices:
                        continue

                if entry.get().strip():
                    speak_callback(i)
                    break

def get_focused_entry():
    """Return the currently focused input entry widget, or None if none focused or if focus is elsewhere.

    Returns:
        The input entry widget that currently has focus, or None if no input entry is focused.
    """
    focused = window.focus_get()  # Get the currently focused widget

    # Return None if no widget is focused
    if not focused:
        return None

    # Check if the focused widget is one of our input entries
    if focused in input_entries:
        # Return the focused entry
        return focused

    # Return None if focus is on another widget (like filter_entry)
    return None

def scroll_to_top():
    """Scroll the canvas to the top position."""
    # Make sure the canvas exists before trying to scroll
    if "canvas" in globals():
        canvas.yview_moveto(0.0)  # Move view to the beginning (0.0 = top)

def create_entry(container):
    color_1 = "#cccccc"
    border_color = "pink"

    # Add the entry with styling
    entry = tk.Entry(container, width=30, font=ENTRY_FONT,
                    bg="#f0f0f0", fg="#000000",
                    relief="solid", bd=1,
                    highlightthickness=2,
                    highlightbackground=color_1,
                    highlightcolor=border_color)

    # Add focus event handlers
    def on_entry_focus_in(event):
        event.widget.config(highlightbackground=color_1, highlightcolor=border_color)

    def on_entry_focus_out(event):
        event.widget.config(highlightbackground=color_1, highlightcolor=color_1)

    entry.bind("<FocusIn>", on_entry_focus_in)
    entry.bind("<FocusOut>", on_entry_focus_out)
    return entry

# Call the main function when the script is run directly
if __name__ == "__main__":
    main()
