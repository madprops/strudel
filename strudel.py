import os
import tkinter as tk
import signal
import sys
from tkinter import ttk, messagebox

import widgets as Widgets
import speech as Speech
import inputs as Inputs
import settings as Settings

window = None
row_frames = []     # Store references to row frames containing all elements
filtered_indices = None  # Track which entries are currently filtered (shown)
frame = None  # The frame containing the input entries
filter_var = None  # Variable for filter input
filter_entry = None  # The filter entry widget
canvas = None

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
        window.after(100, focus_filter())

        Speech.setup(window)
        window.mainloop()
    except Exception as e:
        print(f"Error in main function: {e}")
        messagebox.showerror("Error", f"An error occurred: {e}")

def make_window():
    global window, input_entries, filtered_indices, frame, filter_var, filter_entry, row_frames, canvas

    window = tk.Tk()
    window.title(Settings.get("title"))
    window.configure(bg=Settings.get("background"))
    width = Settings.get("width")
    height = Settings.get("height")
    window.geometry(f"{width}x{height}")  # Set initial size

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

    # Remove focus and highlighting when item is selected
    def handle_volume_select(event):
        # Use tkinter's scheduler to shift focus after a short delay
        window.after(10, lambda: (Settings.volume_combo.selection_clear(), window.focus_force()))
        # Get the selected display label and convert to actual value
        selected_label = volume_var.get()
        actual_value = volume_map.get(selected_label, "1.0")  # Default to 1.0 if not found
        # Update settings when volume changes
        settings["volume"] = actual_value

    Settings.volume_combo.bind("<<ComboboxSelected>>", handle_volume_select)

    # Filter functionality is now implemented at the top of the window

    # Create main container with scrolling ability
    main_container = Widgets.create_frame(window)
    main_container.pack(fill="both", expand=True, padx=10, pady=5)

    # Create canvas with scrollbar for scrolling through items
    canvas = tk.Canvas(main_container, bg="#2d2d2d", highlightthickness=0)
    scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)

    # Use the global frame variable
    global frame
    frame = Widgets.create_frame(canvas)

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
    def on_scroll_up(event):
        try:
            widget = window.winfo_containing(event.x_root, event.y_root)

            if isinstance(widget, ttk.Combobox) or "TCombobox" in str(widget):
                return

            canvas.yview_scroll(-1, "units")
        except KeyError:
            # Skip scrolling when dropdown is active
            pass

    def on_scroll_down(event):
        try:
            widget = window.winfo_containing(event.x_root, event.y_root)

            if isinstance(widget, ttk.Combobox) or "TCombobox" in str(widget):
                return

            canvas.yview_scroll(1, "units")
        except KeyError:
            # Skip scrolling when dropdown is active
            pass

    canvas.bind_all("<Button-4>", on_scroll_up)  # Linux
    canvas.bind_all("<Button-5>", on_scroll_down)   # Linux

    # Clear any previous references
    row_frames = []
    input_entries = []

    for n in range(Settings.get("num_items")):
        # Create a frame for this row
        row_frame = Widgets.create_frame(frame)
        row_frame.grid(row=n, column=0, sticky="ew", padx=0, pady=1)
        row_frames.append(row_frame)

        # Add the speak button
        btn = Widgets.create_button(row_frame, "Speak", lambda n=n: Speech.callback(n))
        btn.pack(side="left", padx=(0, 5), pady=2)

        Inputs.create(row_frame, Settings.speech[n])

        # Button container for up/down buttons
        button_container = Widgets.create_frame(row_frame)
        button_container.pack(side="right", padx=5)

        # Up button
        up_btn = Widgets.create_button(button_container, "▲", lambda n=n: move_item_up(n))
        up_btn.pack(side="left", padx=(2, 0))

        # Down button
        down_btn = Widgets.create_button(button_container, "▼", lambda n=n: move_item_down(n))
        down_btn.pack(side="left", padx=(0, 5))

    # Make the row frames expand horizontally
    frame.grid_columnconfigure(0, weight=1)

    # --- BOTTOM ---

    bottom_controls = Widgets.create_frame(window)
    bottom_controls.configure(height=50)  # Set fixed height to give space for buttons at bottom
    bottom_controls.pack(fill="x", pady=(0, 0), padx=0)
    bottom_controls.pack_propagate(False)  #
    # Add filter input above the speech entries
    filter_frame = Widgets.create_frame(bottom_controls)
    filter_frame.pack(fill="x", pady=(0, 5), padx=10)

    filter_var = tk.StringVar()
    filter_entry = Widgets.create_entry(filter_frame)
    filter_entry.configure(textvariable=filter_var)
    filter_entry.pack(side="left", fill="x", expand=True, pady=(5, 5))

    # Bind Escape key to clear the filter
    filter_entry.bind("<Escape>", lambda e: clear_filter())    # Clear button for the filter

    # Use the global clear_filter function
    clear_filter_btn = Widgets.create_button(filter_frame, "Clear", clear_filter)
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
    Speech.stop()

    # Make sure all entries are visible before saving
    if filtered_indices is not None:
        filter_var.set("")
        apply_filter("")  # This will restore all items in their proper grid positions

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
    num_items = Settings.get("num_items")

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
    Settings.save_speech()

    """Move a speech item up in the list (swap with the item above it)"""
    if index <= 0:
        return  # Can't move the first item up

    # Swap entries in the speech list
    Settings.speech[index], Settings.speech[index-1] = Settings.speech[index-1], Settings.speech[index]

    # Update the text in the entries
    input_entries[index].delete(0, tk.END)
    input_entries[index].insert(0, Settings.speech[index])

    input_entries[index-1].delete(0, tk.END)
    input_entries[index-1].insert(0, Settings.speech[index-1])

    # Save the updated order
    Settings.save_speech()

    # Re-apply filter if there is active filtering
    if filtered_indices is not None:
        # Re-apply the current filter
        filter_text = filter_var.get()

        if filter_text:
            apply_filter(filter_text)

def move_item_down(index):
    Settings.save_speech()

    """Move a speech item down in the list (swap with the item below it)"""
    if index >= len(speech) - 1:
        return  # Can't move the last item down

    # Swap entries in the speech list
    Settings.speech[index], Settings.speech[index+1] = Settings.speech[index+1], Settings.speech[index]

    # Update the text in the entries
    input_entries[index].delete(0, tk.END)
    input_entries[index].insert(0, Settings.speech[index])

    input_entries[index+1].delete(0, tk.END)
    input_entries[index+1].insert(0, Settings.speech[index+1])

    # Save the updated order
    Settings.save_speech()

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
            Speech.callback(None, focused_entry)
        else:
            # Find the first non-empty entry
            for i, entry in enumerate(input_entries):

                if filtered_indices:
                    if i not in filtered_indices:
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

def scroll_to_top():
    """Scroll the canvas to the top position."""
    # Make sure the canvas exists before trying to scroll
    if "canvas" in globals():
        canvas.yview_moveto(0.0)  # Move view to the beginning (0.0 = top)

if __name__ == "__main__":
    main()
