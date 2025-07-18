import widgets as Widgets

entries = []

def create(container, speech):
    global entries

    entry = Widgets.create_entry(container)
    entry.insert(0, speech)
    entry.pack(side="left", padx=0, pady=2, fill="x", expand=True)
    entries.append(entry)
    return entry