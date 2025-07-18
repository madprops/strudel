import threading
from tkinter import messagebox
import os
import signal
from subprocess import Popen, PIPE

import inputs as Inputs
import settings as Settings
import window as Window

speech_lock = threading.Lock()
current_speech_process = None

def callback(n, entry=None):
    if not entry:
      entry = Inputs.entries[n]

    s = entry.get().strip()

    if not s:
      return

    v = Settings.voice_var.get()
    # Update speed setting to current selection - convert from label to value
    selected_speed_label = Settings.speed_var.get()
    Settings.set("speed", Settings.speed_map.get(selected_speed_label, "1.0"))

    # Update volume setting to current selection - convert from label to value
    selected_volume_label = Settings.volume_var.get()
    Settings.set("volume", Settings.volume_map.get(selected_volume_label, "1.0"))

    speak(n, s, v)

def stop():
    """Stop any currently running speech"""
    global current_speech_process

    with speech_lock:
        if current_speech_process and current_speech_process.poll() is None:
            try:
                current_speech_process.terminate()
                # Wait briefly for process to terminate
                current_speech_process.wait(timeout=1)
            except Exception as e:
                print("Error stopping speech")
                # Force kill if terminate fails
                try:
                    os.kill(current_speech_process.pid, signal.SIGKILL)
                except:
                    pass

def run_thread(n, s, v):
    """Function to run in a separate thread for speaking"""
    global current_speech_process, speech

    try:
        # Get current speed setting
        speed = Settings.get("speed")
        # Get current volume setting
        volume = Settings.get("volume")

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
            current_speech_process = Popen([Settings.get("synth"), "-v", v, "-s", str(wpm), "-a", str(amplitude), s], stderr=PIPE)

        # Wait for the process outside the lock to allow other threads to interrupt
        _, error = current_speech_process.communicate()

        with speech_lock:
            if current_speech_process.returncode != 0 and error:
                error_msg = error.decode().strip()
                print(f"Synth error: {error_msg}")
                # Use after() to schedule the messagebox from the main thread
                Window.window.after(0, lambda: messagebox.showerror("Speech Error", f"Failed to speak: {error_msg}"))
                return

            # Voice settings will still be saved
            # (We're not updating speech here anymore as it's done in save_speech)

            # Update voice setting if it changed
            if Settings.get("voice") != v:
                Settings.set("voice", v)
                # Use after() to schedule the save from the main thread
                Window.window.after(0, Settings.save)

    except Exception as e:
        print(e)
        # Use after() to schedule the messagebox from the main thread
        Window.window.after(0, lambda: messagebox.showerror("Error", "Failed to run synth"))

def speak(n, s, v):
    """Start speech in a separate thread, stopping any current speech first"""
    stop()

    # Start a new thread for speaking
    speech_thread = threading.Thread(target=run_thread, args=(n, s, v))
    speech_thread.daemon = True  # Make thread exit when main program exits
    speech_thread.start()