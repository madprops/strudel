import tkinter as tk
from tkinter import ttk

import widgets as Widgets
import settings as Settings
import filterwid as Filter
import speech as Speech

entries = []
row_frames = []     # Store references to row frames containing all elements
canvas = None
frame = None  # The frame containing the input entries

def setup(window):
    global frame, row_frames, canvas

    # Create main container with scrolling ability
    main_container = Widgets.create_frame(window)
    main_container.pack(fill="both", expand=True, padx=10, pady=5)

    # Create canvas with scrollbar for scrolling through items
    canvas = tk.Canvas(main_container, bg="#2d2d2d", highlightthickness=0)
    scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)

    # Use the global frame variable
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
    def on_mousewheel(event):
        try:
            # Check if the mousewheel event is over a combobox
            widget = window.winfo_containing(event.x_root, event.y_root)
            if isinstance(widget, ttk.Combobox) or "TCombobox" in str(widget):
                return  # Don't scroll the canvas if over a combobox
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except KeyError:
            # Skip scrolling when dropdown is active
            pass

    canvas.bind_all("<MouseWheel>", on_mousewheel)  # Windows and MacOS

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

        create_speak(row_frame, n)
        create_entry(row_frame, Settings.speech[n])
        create_buttons(row_frame, n)

    # Make the row frames expand horizontally
    frame.grid_columnconfigure(0, weight=1)

def create_speak(container, n):
        # Add the speak button
        btn = Widgets.create_button(container, "Speak", lambda n=n: Speech.callback(n))
        btn.pack(side="left", padx=(0, 5), pady=2)

def create_entry(container, speech):
    global entries

    entry = Widgets.create_entry(container)
    entry.insert(0, speech)
    entry.pack(side="left", padx=0, pady=2, fill="x", expand=True)
    entries.append(entry)
    return entry

def create_buttons(container, n):
    # Button container for up/down buttons
    button_container = Widgets.create_frame(container)
    button_container.pack(side="right", padx=5)

    # Up button
    up_btn = Widgets.create_button(button_container, "▲", lambda n=n: move_item_up(n))
    up_btn.pack(side="left", padx=(2, 0))

    # Down button
    down_btn = Widgets.create_button(button_container, "▼", lambda n=n: move_item_down(n))
    down_btn.pack(side="left", padx=(0, 5))

def scroll_to_top():
    """Scroll the canvas to the top position."""
    # Make sure the canvas exists before trying to scroll
    if "canvas" in globals():
        canvas.yview_moveto(0.0)  # Move view to the beginning (0.0 = top)

def move_item_up(index):
    Settings.save_speech()

    """Move a speech item up in the list (swap with the item above it)"""
    if index <= 0:
        return  # Can't move the first item up

    # Swap entries in the speech list
    Settings.speech[index], Settings.speech[index-1] = Settings.speech[index-1], Settings.speech[index]

    # Update the text in the entries
    entries[index].delete(0, tk.END)
    entries[index].insert(0, Settings.speech[index])

    entries[index-1].delete(0, tk.END)
    entries[index-1].insert(0, Settings.speech[index-1])

    # Save the updated order
    Settings.save_speech()
    Filter.apply()

def move_item_down(index):
    Settings.save_speech()

    """Move a speech item down in the list (swap with the item below it)"""
    if index >= len(speech) - 1:
        return  # Can't move the last item down

    # Swap entries in the speech list
    Settings.speech[index], Settings.speech[index+1] = Settings.speech[index+1], Settings.speech[index]

    # Update the text in the entries
    entries[index].delete(0, tk.END)
    entries[index].insert(0, Settings.speech[index])

    entries[index+1].delete(0, tk.END)
    entries[index+1].insert(0, Settings.speech[index+1])

    # Save the updated order
    Settings.save_speech()
    Filter.apply()