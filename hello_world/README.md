# Hello World add-on

A simple add-on with a sidebar web UI (via Ingress) and a config page.

## Web UI

After starting the add-on, enable **Show in sidebar** on the add-on's Info tab.
A "Hello World" panel appears in the sidebar showing your greeting and a form
to edit the options. "Save & restart" applies the new log settings immediately.

## Configuration

| Option         | Description                                   |
|----------------|-----------------------------------------------|
| `message`      | Message shown in the UI and written to the log |
| `name`         | Who to greet                                  |
| `color`        | Accent color for the UI (hex, e.g. `#03a9f4`) |
| `log_interval` | Seconds between log messages (5-3600)         |
