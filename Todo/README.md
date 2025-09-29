Todo — Minimal Pro
===================

This is a single-file Tkinter-based TODO application with SQLite persistence. It supports:

- Add / Edit / Delete tasks
- Due dates, priority, tags, notes
- Search and basic filters (Today, Overdue, Completed)
- Import / Export JSON
- Simple undo (last action)
- Desktop reminders via popups

Run
---

Requires Python 3.8+. From the `Todo` folder run:

```powershell
python main.py
```

Usage
-----

- Ctrl+N: New task
- Ctrl+E / Enter: Edit selected
- Delete: Delete selected
- Ctrl+F: Focus search
- Ctrl+Z: Undo

Notes
-----
The app stores data in `tasks.db` alongside the script. Import expects JSON in the same format produced by Export.

License
-------
MIT
