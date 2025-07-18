from tkinter import ttk
import tkinter as tk

import window as Window

BUTTON_HEIGHT = 1
BUTTON_FONT = ("sans", 10)
ENTRY_FONT = ("sans", 14)
LABEL_FONT = ("sans", 12)
COMBOBOX_FONT = ("sans", 12)
PAD_X = 5

def setup():
    # Apply a style to make the combobox match button height
    style = ttk.Style()
    style.configure("Strudel.TCombobox", padding=(0, 4, 0, 4))  # Add padding to match button height

    # Configure the dropdown popup to have larger text and wider arrow
    style.map("TCombobox", fieldbackground=[("readonly", "#ffffff")])
    style.configure("TCombobox", arrowsize=20)  # Make the dropdown arrow wider

    # Configure the dropdown popup list style (for Windows and Linux)
    Window.window.option_add("*TCombobox*Listbox.font", ("sans", 12))

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

def create_button(container, text, command):
    return tk.Button(container, text=text, font=BUTTON_FONT,
        height=BUTTON_HEIGHT, command=command)

def create_label(container, text):
    return tk.Label(container, text=text, bg="#2d2d2d", fg="white", font=LABEL_FONT)

def create_frame(container):
    return tk.Frame(container, bg="#2d2d2d")

def create_combobox(container, var, values):
    return ttk.Combobox(container, textvariable=var, values=values, width=8,
                        font=COMBOBOX_FONT, style="Strudel.TCombobox")