import os
import sys
import tkinter as tk

import speech as Speech
import filterwid as Filter
import settings as Settings
import controls as Controls
import widgets as Widgets
import inputs as Inputs

window = None

def setup():
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

    # Create the top controls
    Controls.setup(top_controls)

    # Create the main frame for input entries
    Inputs.setup()

    # --- BOTTOM ---

    bottom_controls = Widgets.create_frame(window)
    bottom_controls.configure(height=50)  # Set fixed height to give space for buttons at bottom
    bottom_controls.pack(fill="x", pady=(0, 0), padx=0)
    bottom_controls.pack_propagate(False)  #

    Filter.setup(bottom_controls)

    # Handle window close event
    window.protocol("WM_DELETE_WINDOW", on_closing)
    start_keyboard_detection()

def on_closing():
    """Handle the window closing event"""
    Speech.stop()
    Filter.reset()
    Settings.save_speech()
    Settings.save()
    window.destroy()
    sys.exit(0)


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