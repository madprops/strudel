import widgets as Widgets
import tkinter as tk

import inputs as Inputs
import settings as Settings

indices = None  # Track which entries are currently filtered (shown)
filter_var = None  # Variable for filter input
filter_entry = None  # The filter entry widget

def setup(container):
    global indices, filter_var, filter_entry

    # Add filter input above the speech entries
    filter_frame = Widgets.create_frame(container)
    filter_frame.pack(fill="x", pady=(0, 5), padx=10)

    filter_var = tk.StringVar()
    filter_entry = Widgets.create_entry(filter_frame)
    filter_entry.configure(textvariable=filter_var)
    filter_entry.pack(side="left", fill="x", expand=True, pady=(5, 5))

    # Bind Escape key to clear the filter
    filter_entry.bind("<Escape>", lambda e: clear())    # Clear button for the filter

    # Use the global clear function
    clear_btn = Widgets.create_button(filter_frame, "Clear", clear)
    clear_btn.pack(side="right", padx=(5, 0), pady=(5, 5))

    # Bind the filter entry to update filtering on text change
    def on_filter_change(*args):
        # Get the current filter text
        current_filter = filter_var.get()
        apply(current_filter)

    # Use both write and read traces to ensure it catches all changes
    filter_var.trace_add("write", on_filter_change)

def clear():
    """Clear the filter and show all entries"""
    if filter_var:
        filter_var.set("")
        apply("")

        # Try to focus the filter entry if it exists
        if "filter_entry" in globals():
            filter_entry.focus_set()

def apply(filter_text=""):
    """Filter the speech entries based on the given text"""
    global indices

    Inputs.scroll_to_top()

    if not filter_text:
        # Get current filter text if not provided
        filter_text = filter_var.get()

    # Ensure we have a clean starting point
    filter_text = filter_text.strip()

    # Make sure we have all the widgets we need
    num_items = Settings.get("num_items")

    if len(Inputs.row_frames) != num_items or len(Inputs.entries) != num_items:
        print(f"Warning: Widget count mismatch. Expected {num_items}, got {len(Inputs.row_frames)} row frames, "
              f"{len(Inputs.entries)} entries")

        return

    # If no filter text, show all entries
    if not filter_text:
        indices = None

        # Show all entry rows
        for n in range(num_items):
            # Use grid with the correct row to restore position
            Inputs.row_frames[n].grid(row=n, column=0, sticky="ew", padx=0, pady=1)

        return

    # Convert filter to lowercase for case-insensitive comparison
    filter_text = filter_text.lower()

    # Create a list to store indices of entries that match the filter
    indices = []

    # Counter for visible rows to ensure compact display
    visible_row = 0

    # Check each entry against the filter
    for n in range(num_items):
        if n < len(Inputs.entries):
            entry_text = Inputs.entries[n].get().lower()

            if filter_text in entry_text:
                indices.append(n)
                # Show this entry row and reposition it to be compact
                Inputs.row_frames[n].grid(row=visible_row, column=0, sticky="ew", padx=0, pady=1)
                visible_row += 1
            else:
                # Completely remove this entry from the grid
                Inputs.row_frames[n].grid_forget()

def focus():
    """Focus the filter entry."""
    filter_entry.focus_set()

def reset():
    # Make sure all entries are visible before saving
    if indices is not None:
        filter_var.set("")
        apply("")  # This will restore all items in their proper grid positions