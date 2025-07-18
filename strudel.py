import os
import tkinter as tk
import signal
import sys
from tkinter import ttk, messagebox

import widgets as Widgets
import speech as Speech
import settings as Settings
import filterwid as Filter
import window as Window

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
            Window.window.after(100, check_signals)

        Settings.setup()
        Window.setup()

        # Start the signal checking loop once window is created
        Window.window.after(100, check_signals)
        Window.window.after(100, Filter.focus())

        Widgets.setup()
        Window.window.mainloop()
    except Exception as e:
        print(f"Error in main function: {e}")
        messagebox.showerror("Error", f"An error occurred: {e}")

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

if __name__ == "__main__":
    main()
