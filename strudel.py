import os
import tkinter as tk
import signal
import sys
from tkinter import ttk, messagebox

import widgets as Widgets
import speech as Speech
import inputs as Inputs
import settings as Settings
import filterwid as Filter

window = None
PAD_X = 5

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

        Settings.setup()
        make_window()
        start_keyboard_detection()

        # Start the signal checking loop once window is created
        window.after(100, check_signals)
        window.after(100, Filter.focus())

        Speech.setup(window)
        window.mainloop()
    except Exception as e:
        print(f"Error in main function: {e}")
        messagebox.showerror("Error", f"An error occurred: {e}")

def make_window():
    global window

    window = tk.Tk()
    window.title(Settings.get("title"))
    window.configure(bg=Settings.get("background"))
    width = Settings.get("width")
    height = Settings.get("height")
    window.geometry(f"{width}x{height}")  # Set initial size

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

    input_entries = []

    # Create top controls for voice, speed, and volume - centered at the top
    top_controls = Widgets.create_frame(window)
    top_controls.configure(height=60) # Set fixed height to give space for buttons at bottom
    top_controls.pack(fill="x", pady=(10, 5), padx=(5, 5))
    top_controls.pack_propagate(False)  # Prevent the frame from shrinking to fit its contents

    # Center container for voice, speed, and volume controls
    controls_container = Widgets.create_frame(top_controls)
    controls_container.pack(side="left", fill="x", expand=True)

    # Apply a style to make the combobox match button height
    style = ttk.Style()
    style.configure("Strudel.TCombobox", padding=(0, 4, 0, 4))  # Add padding to match button height

    # Configure the dropdown popup to have larger text and wider arrow
    style.map("TCombobox", fieldbackground=[("readonly", "#ffffff")])
    style.configure("TCombobox", arrowsize=20)  # Make the dropdown arrow wider

    # Configure the dropdown popup list style (for Windows and Linux)
    window.option_add("*TCombobox*Listbox.font", ("sans", 12))

    Settings.setup_voice(controls_container)
    Settings.setup_speed(controls_container)
    Settings.setup_volume(controls_container)

    # Bottom controls - positioned at the right side and vertically aligned to the bottom
    buttons = Widgets.create_frame(top_controls)
    buttons.pack(side="right", fill="y", anchor="s")

    # Save button

    save_btn = Widgets.create_button(buttons, "Save", lambda: (Settings.save_speech(), Settings.save()))
    save_btn.pack(side="right", padx=PAD_X, anchor="s", pady=(0, 5))

    # Reset button
    reset_btn = Widgets.create_button(buttons, "Reset", Settings.reset)
    reset_btn.pack(side="right", padx=PAD_X, anchor="s", pady=(0, 5))

    # Close button
    close_btn = Widgets.create_button(buttons, "Close", on_closing)
    close_btn.pack(side="right", padx=PAD_X, anchor="s", pady=(0, 5))

    # Create the main frame for input entries
    Inputs.setup(window)

    # --- BOTTOM ---

    bottom_controls = Widgets.create_frame(window)
    bottom_controls.configure(height=50)  # Set fixed height to give space for buttons at bottom
    bottom_controls.pack(fill="x", pady=(0, 0), padx=0)
    bottom_controls.pack_propagate(False)  #

    Filter.setup(bottom_controls)

    # Handle window close event
    window.protocol("WM_DELETE_WINDOW", on_closing)

def on_closing():
    """Handle the window closing event"""
    Speech.stop()
    Filter.reset()
    Settings.save_speech()
    Settings.save()
    window.destroy()
    sys.exit(0)

def signal_handler(sig, frame):
    """Handle Ctrl+C by cleaning up and exiting gracefully"""
    print("\nExiting Strudel...")

    # Stop any speech if running
    try:
        Speech.stop()
    except:
        pass

    # Don't try to interact with the window - it might be causing the hang
    # Force immediate exit with os._exit which doesn't run cleanup handlers
    os._exit(0)

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
            Speech.callback(None, focused_entry)
        else:
            # Find the first non-empty entry
            for i, entry in enumerate(input_entries):

                if Filter.indices:
                    if i not in Filter.indices:
                        continue

                if entry.get().strip():
                    Speech.callback(i)
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

if __name__ == "__main__":
    main()
