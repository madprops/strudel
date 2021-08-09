import re
from subprocess import Popen
import PySimpleGUI as sg
from pathlib import Path

settings = {}
speech = []
voices = []
window = None
num_items = 20

def main():
  get_settings()
  get_speech()
  get_voices()
  make_window()

  while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED:
        break
    elif event == "Close":
      break
    elif event.startswith("speak_"):
      n = int(re.sub("^speak_", "", event))
      speak(n, values[f"input_{n}"], values["input_voice"])

  window.close()

def make_window():
  global window
  sg.theme("DarkAmber")
  font = ("sans 16")
  column = make_items()
  column.append([
    sg.Button("Close", font=("sans 10")),
    sg.InputCombo((voices), size=(10, 1), default_value=settings["voice"], key="input_voice")
  ])
  layout = [[sg.Column(column, element_justification="center")]]
  window = sg.Window("Strudel", layout, font=font, element_padding=((2,2), 6))

def make_items():
  items = []
  for n in range(0, num_items):
    items.append([
      sg.Button("Speak", font=("sans 10"), key=f"speak_{n}"),
      sg.InputText(key=f"input_{n}", size=(50, 1), default_text=speech[n])
    ])
  return items

def speak(n, s, v):
  global speech
  Popen(["espeak", "-v", v, s])
  if speech[n] != s:
    speech[n] = s
    save_speech()
  if settings["voice"] != v:
    settings["voice"] = v
    save_settings()
  
def get_settings_path():
  thispath = Path(__file__).parent.resolve()
  filepath = Path(thispath) / Path("settings.txt")
  return filepath
  
def get_speech_path():
  thispath = Path(__file__).parent.resolve()
  filepath = Path(thispath) / Path("speech.txt")
  return filepath

def get_voices_path():
  thispath = Path(__file__).parent.resolve()
  filepath = Path(thispath) / Path("voices.txt")
  return filepath   

def get_settings():
  global settings
  filepath = get_settings_path()
  filepath.touch(exist_ok=True)
  file = open(filepath, "r")
  setts = file.read().split("\n")
  setts = list(map(str.strip, setts))
  setts = list(filter(None, setts))
  for s in setts:
    sp = s.split("=")
    settings[sp[0]] = sp[1]

def get_speech():
  global speech
  filepath = get_speech_path()
  filepath.touch(exist_ok=True)
  file = open(filepath, "r")
  speech = file.read().split("\n")
  speech = list(map(str.strip, speech))
  speech = list(filter(None, speech))
  for n in range(0, 20):
    if n >= len(speech):
      speech.append("Enter some text")

def get_voices():
  global voices
  filepath = get_voices_path()
  filepath.touch(exist_ok=True)
  file = open(filepath, "r")
  voices = file.read().split("\n")
  voices = list(map(str.strip, voices))
  voices = list(filter(None, voices))     

def save_speech():
  filepath = get_speech_path()
  file = open(filepath, "w")
  file.write("\n".join(speech).strip())
  file.close()

def save_settings():
  filepath = get_settings_path()
  file = open(filepath, "w")
  s = ""
  for key in settings:
    s += f"{key}={settings[key]}"
  file.write(s)
  file.close()    

if __name__ == "__main__": main()