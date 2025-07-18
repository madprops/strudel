import widgets as Widgets
import settings as Settings
import window as Window

def setup(container):
    # Center container for voice, speed, and volume controls
    controls_container = Widgets.create_frame(container)
    controls_container.pack(side="left", fill="x", expand=True)

    Settings.setup_voice(controls_container)
    Settings.setup_speed(controls_container)
    Settings.setup_volume(controls_container)

    # Bottom controls - positioned at the right side and vertically aligned to the bottom
    buttons = Widgets.create_frame(container)
    buttons.pack(side="right", fill="y", anchor="s")

    # Save button

    save_btn = Widgets.create_button(buttons, "Save", lambda: (Settings.save_speech(), Settings.save()))
    save_btn.pack(side="right", padx=Widgets.PAD_X, anchor="s", pady=(0, 5))

    # Reset button
    reset_btn = Widgets.create_button(buttons, "Reset", Settings.reset)
    reset_btn.pack(side="right", padx=Widgets.PAD_X, anchor="s", pady=(0, 5))

    # Close button
    close_btn = Widgets.create_button(buttons, "Close", Window.on_closing)
    close_btn.pack(side="right", padx=Widgets.PAD_X, anchor="s", pady=(0, 5))