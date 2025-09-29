import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import sqlite3
import threading
import json
import datetime
import os
import traceback


DB_PATH = os.path.join(os.path.dirname(__file__), "tasks.db")


def now_iso():
    return datetime.datetime.now().isoformat(sep=" ", timespec="seconds")


class TaskStorage:
    """Simple SQLite-backed task storage."""
    def __init__(self, path=DB_PATH):
        self.path = path
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                notes TEXT,
                due TEXT,
                priority INTEGER DEFAULT 2,
                status TEXT DEFAULT 'todo',
                tags TEXT,
                created TEXT,
                updated TEXT,
                recurrence TEXT,
                parent_id INTEGER
            )
            """
        )
        self.conn.commit()

    def add_task(self, task):
        cur = self.conn.cursor()
        now = now_iso()
        cur.execute(
            """
            INSERT INTO tasks (title, notes, due, priority, status, tags, created, updated, recurrence, parent_id)
            VALUES (:title, :notes, :due, :priority, :status, :tags, :created, :updated, :recurrence, :parent_id)
            """,
            {
                'title': task.get('title'),
                'notes': task.get('notes'),
                'due': task.get('due'),
                'priority': task.get('priority', 2),
                'status': task.get('status', 'todo'),
                'tags': task.get('tags'),
                'created': now,
                'updated': now,
                'recurrence': task.get('recurrence'),
                'parent_id': task.get('parent_id'),
            },
        )
        self.conn.commit()
        return cur.lastrowid

    def update_task(self, task_id, fields):
        fields = dict(fields)
        fields['updated'] = now_iso()
        set_clause = ",".join(f"{k} = :{k}" for k in fields.keys())
        params = {**fields, 'id': task_id}
        cur = self.conn.cursor()
        cur.execute(f"UPDATE tasks SET {set_clause} WHERE id = :id", params)
        self.conn.commit()

    def delete_task(self, task_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()

    def get_task(self, task_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        return cur.fetchone()

    def list_tasks(self, where_clause=None, params=()):
        cur = self.conn.cursor()
        q = "SELECT * FROM tasks"
        if where_clause:
            q += " WHERE " + where_clause
        q += " ORDER BY due IS NULL, due, priority"
        cur.execute(q, params)
        return cur.fetchall()

    def export_json(self, path):
        rows = self.list_tasks()
        data = [dict(r) for r in rows]
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

    def import_json(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        inserted = 0
        for item in data:
            # simple mapping, ignore id from source
            task = {
                'title': item.get('title') or 'Untitled',
                'notes': item.get('notes'),
                'due': item.get('due'),
                'priority': item.get('priority', 2),
                'status': item.get('status', 'todo'),
                'tags': item.get('tags'),
                'recurrence': item.get('recurrence'),
                'parent_id': item.get('parent_id'),
            }
            self.add_task(task)
            inserted += 1
        return inserted


class TaskDialog(simpledialog.Dialog):
    def __init__(self, parent, title=None, task=None):
        self.task = task or {}
        super().__init__(parent, title=title)

    def body(self, master):
        tk.Label(master, text="Title:").grid(row=0, column=0, sticky='w')
        self.title_var = tk.StringVar(value=self.task.get('title', ''))
        self.title_entry = tk.Entry(master, textvariable=self.title_var, width=40)
        self.title_entry.grid(row=0, column=1, columnspan=3, sticky='we')

        tk.Label(master, text="Due (YYYY-MM-DD HH:MM):").grid(row=1, column=0, sticky='w')
        self.due_var = tk.StringVar(value=self.task.get('due') or '')
        tk.Entry(master, textvariable=self.due_var).grid(row=1, column=1, sticky='we')

        tk.Label(master, text="Priority (1=High,2=Normal,3=Low):").grid(row=1, column=2, sticky='w')
        self.prio_var = tk.IntVar(value=self.task.get('priority', 2))
        tk.Spinbox(master, from_=1, to=3, textvariable=self.prio_var, width=5).grid(row=1, column=3)

        tk.Label(master, text="Tags (comma separated):").grid(row=2, column=0, sticky='w')
        self.tags_var = tk.StringVar(value=self.task.get('tags') or '')
        tk.Entry(master, textvariable=self.tags_var).grid(row=2, column=1, columnspan=3, sticky='we')

        tk.Label(master, text="Notes:").grid(row=3, column=0, sticky='nw')
        self.notes_text = tk.Text(master, width=50, height=8)
        self.notes_text.grid(row=3, column=1, columnspan=3, sticky='we')
        if self.task.get('notes'):
            self.notes_text.insert('1.0', self.task.get('notes'))

        return self.title_entry

    def apply(self):
        self.result = {
            'title': self.title_var.get().strip() or 'Untitled',
            'due': self.due_var.get().strip() or None,
            'priority': int(self.prio_var.get()),
            'tags': self.tags_var.get().strip() or None,
            'notes': self.notes_text.get('1.0', 'end').strip() or None,
        }


class TodoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Todo — Minimal Pro')
        self.geometry('900x600')
        self.minsize(700, 400)
        self.style = ttk.Style(self)

        # Storage
        self.storage = TaskStorage()

        # Undo stack (very small: last action)
        self.undo_stack = []

        self._build_ui()
        self._bind_keys()
        self._load_tasks()

        # Start reminder thread
        self._reminder_interval = 30  # seconds
        self._start_reminders()

    def _build_ui(self):
        # Top toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(side='top', fill='x', padx=6, pady=6)

        ttk.Button(toolbar, text='New (Ctrl+N)', command=self.add_task).pack(side='left')
        ttk.Button(toolbar, text='Edit (Ctrl+E)', command=self.edit_task).pack(side='left')
        ttk.Button(toolbar, text='Delete (Del)', command=self.delete_task).pack(side='left')
        ttk.Button(toolbar, text='Complete', command=self.toggle_complete).pack(side='left')
        ttk.Button(toolbar, text='Import', command=self.import_tasks).pack(side='left')
        ttk.Button(toolbar, text='Export', command=self.export_tasks).pack(side='left')

        ttk.Label(toolbar, text='Search:').pack(side='left', padx=(10, 0))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var)
        search_entry.pack(side='left', padx=(2, 6))
        search_entry.bind('<KeyRelease>', lambda e: self._load_tasks())

        ttk.Label(toolbar, text='Filter:').pack(side='left')
        self.filter_var = tk.StringVar(value='All')
        filter_cb = ttk.Combobox(toolbar, values=['All', 'Todo', 'Completed', 'Overdue', 'Today'], width=12, state='readonly', textvariable=self.filter_var)
        filter_cb.pack(side='left')
        filter_cb.bind('<<ComboboxSelected>>', lambda e: self._load_tasks())

        ttk.Label(toolbar, text='Theme:').pack(side='right')
        self.theme_var = tk.StringVar(value='Light')
        theme_cb = ttk.Combobox(toolbar, values=['Light', 'Dark'], width=8, state='readonly', textvariable=self.theme_var)
        theme_cb.pack(side='right')
        theme_cb.bind('<<ComboboxSelected>>', lambda e: self._apply_theme())

        # Split main area
        main = ttk.Frame(self)
        main.pack(fill='both', expand=True, padx=6, pady=(0,6))

        # Task list (Treeview)
        cols = ('title', 'due', 'priority', 'tags', 'status')
        self.tree = ttk.Treeview(main, columns=cols, show='headings', selectmode='browse')
        self.tree.heading('title', text='Title')
        self.tree.heading('due', text='Due')
        self.tree.heading('priority', text='Prio')
        self.tree.heading('tags', text='Tags')
        self.tree.heading('status', text='Status')
        self.tree.column('title', width=360)
        self.tree.column('due', width=140)
        self.tree.column('priority', width=60, anchor='center')
        self.tree.column('tags', width=120)
        self.tree.column('status', width=80, anchor='center')
        self.tree.pack(side='left', fill='both', expand=True)
        self.tree.bind('<Double-1>', lambda e: self.edit_task())

        # Right pane for details
        right = ttk.Frame(main, width=320)
        right.pack(side='right', fill='y')
        ttk.Label(right, text='Details', font=('Segoe UI', 10, 'bold')).pack(anchor='nw')
        self.details = tk.Text(right, width=40, height=20, state='disabled')
        self.details.pack(fill='both', expand=True)

        # Bottom status
        self.status_var = tk.StringVar(value='Ready')
        status = ttk.Label(self, textvariable=self.status_var, relief='sunken', anchor='w')
        status.pack(side='bottom', fill='x')

        # selection change
        self.tree.bind('<<TreeviewSelect>>', lambda e: self._show_details())

    def _apply_theme(self):
        theme = self.theme_var.get()
        if theme == 'Dark':
            self.style.theme_use('clam')
            self.configure(bg='#222')
        else:
            # default
            try:
                self.style.theme_use('default')
            except Exception:
                pass
            self.configure(bg=None)

    def _bind_keys(self):
        self.bind('<Control-n>', lambda e: self.add_task())
        self.bind('<Control-N>', lambda e: self.add_task())
        self.bind('<Control-e>', lambda e: self.edit_task())
        self.bind('<Control-E>', lambda e: self.edit_task())
        self.bind('<Delete>', lambda e: self.delete_task())
        self.bind('<Return>', lambda e: self.edit_task())
        self.bind('<Control-f>', lambda e: self.focus_search())
        self.bind('<Control-z>', lambda e: self.undo())

    def focus_search(self):
        self.focus_force()
        # find search entry
        for child in self.winfo_children():
            if isinstance(child, ttk.Frame):
                for w in child.winfo_children():
                    if isinstance(w, ttk.Entry):
                        w.focus_set()
                        return

    def _load_tasks(self):
        qparts = []
        params = []
        s = self.search_var.get().strip()
        if s:
            qparts.append("(title LIKE ? OR notes LIKE ? OR tags LIKE ?)")
            like = f"%{s}%"
            params += [like, like, like]

        filter_opt = self.filter_var.get()
        if filter_opt == 'Todo':
            qparts.append("status = 'todo'")
        elif filter_opt == 'Completed':
            qparts.append("status = 'done'")
        elif filter_opt == 'Overdue':
            qparts.append("due IS NOT NULL AND datetime(due) < datetime('now') AND status != 'done'")
        elif filter_opt == 'Today':
            today = datetime.date.today().isoformat()
            qparts.append("date(due) = ?")
            params.append(today)

        where = None
        if qparts:
            where = ' AND '.join(qparts)

        rows = self.storage.list_tasks(where, params)
        # clear
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in rows:
            pr = {1: 'High', 2: 'Normal', 3: 'Low'}.get(r['priority'], str(r['priority']))
            status = 'Done' if r['status'] == 'done' else 'Todo'
            due = r['due'] or ''
            self.tree.insert('', 'end', iid=str(r['id']), values=(r['title'], due, pr, r['tags'] or '', status))

        self.status_var.set(f'{len(rows)} tasks')

    def _show_details(self):
        sel = self.tree.selection()
        if not sel:
            self.details.config(state='normal')
            self.details.delete('1.0', 'end')
            self.details.config(state='disabled')
            return
        task_id = int(sel[0])
        r = self.storage.get_task(task_id)
        if not r:
            return
        txt = []
        txt.append(f"Title: {r['title']}")
        txt.append(f"Status: {r['status']}")
        txt.append(f"Priority: {r['priority']}")
        txt.append(f"Due: {r['due']}")
        txt.append(f"Tags: {r['tags']}")
        txt.append('')
        txt.append('Notes:')
        txt.append(r['notes'] or '')
        self.details.config(state='normal')
        self.details.delete('1.0', 'end')
        self.details.insert('1.0', '\n'.join(txt))
        self.details.config(state='disabled')

    def add_task(self):
        try:
            d = TaskDialog(self, title='New Task')
            if d.result:
                tid = self.storage.add_task(d.result)
                self.undo_stack.append(('add', tid))
                self._load_tasks()
                self.status_var.set('Task added')
        except Exception:
            traceback.print_exc()
            messagebox.showerror('Error', 'Failed to add task')

    def edit_task(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('Edit Task', 'Select a task to edit')
            return
        tid = int(sel[0])
        r = self.storage.get_task(tid)
        if not r:
            return
        initial = dict(r)
        d = TaskDialog(self, title='Edit Task', task=initial)
        if d.result:
            self.storage.update_task(tid, d.result)
            self.undo_stack.append(('edit', tid, initial))
            self._load_tasks()
            self.status_var.set('Task updated')

    def delete_task(self):
        sel = self.tree.selection()
        if not sel:
            return
        tid = int(sel[0])
        r = self.storage.get_task(tid)
        if not r:
            return
        if not messagebox.askyesno('Delete', f"Delete task '{r['title']}'?"):
            return
        # push undo
        self.undo_stack.append(('delete', dict(r)))
        self.storage.delete_task(tid)
        self._load_tasks()
        self.status_var.set('Task deleted')

    def toggle_complete(self):
        sel = self.tree.selection()
        if not sel:
            return
        tid = int(sel[0])
        r = self.storage.get_task(tid)
        if not r:
            return
        new_status = 'done' if r['status'] != 'done' else 'todo'
        self.storage.update_task(tid, {'status': new_status})
        self._load_tasks()
        self.status_var.set('Status toggled')

    def undo(self):
        if not self.undo_stack:
            self.status_var.set('Nothing to undo')
            return
        action = self.undo_stack.pop()
        kind = action[0]
        if kind == 'add':
            tid = action[1]
            self.storage.delete_task(tid)
            self.status_var.set('Undo add')
        elif kind == 'delete':
            task = action[1]
            # reinsert
            t = {k: task[k] for k in task.keys() if k not in ('id',)}
            self.storage.add_task(t)
            self.status_var.set('Undo delete')
        elif kind == 'edit':
            tid = action[1]
            old = action[2]
            # restore old
            fields = {k: old[k] for k in old.keys() if k not in ('id',)}
            self.storage.update_task(tid, fields)
            self.status_var.set('Undo edit')
        self._load_tasks()

    def import_tasks(self):
        path = filedialog.askopenfilename(filetypes=[('JSON', '*.json'), ('All', '*.*')])
        if not path:
            return
        try:
            n = self.storage.import_json(path)
            self._load_tasks()
            messagebox.showinfo('Import', f'Imported {n} tasks')
        except Exception as e:
            messagebox.showerror('Import error', str(e))

    def export_tasks(self):
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON', '*.json')])
        if not path:
            return
        try:
            self.storage.export_json(path)
            messagebox.showinfo('Export', f'Exported tasks to {path}')
        except Exception as e:
            messagebox.showerror('Export error', str(e))

    def _start_reminders(self):
        def check():
            try:
                rows = self.storage.list_tasks("due IS NOT NULL AND status != 'done'")
                now = datetime.datetime.now()
                for r in rows:
                    try:
                        if not r['due']:
                            continue
                        due_dt = None
                        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                            try:
                                due_dt = datetime.datetime.strptime(r['due'], fmt)
                                break
                            except Exception:
                                continue
                        if not due_dt:
                            continue
                        delta = (due_dt - now).total_seconds()
                        # if within next minute or overdue, notify
                        if -5 <= delta <= 60:
                            self._notify(f"Due: {r['title']}", f"Due at {r['due']}")
                    except Exception:
                        continue
            except Exception:
                pass
            # schedule next
            self.after(self._reminder_interval * 1000, check)

        check()

    def _notify(self, title, message):
        try:
            # simple in-app pop-up
            messagebox.showinfo(title, message)
        except Exception:
            pass


if __name__ == '__main__':
    app = TodoApp()
    app.mainloop()
