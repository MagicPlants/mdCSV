"""
QuickMD v2 — Enhanced Markdown Viewer/Editor for Windows 11 (no external packages)
- Side-by-side: Editor (left) + Notebook (Preview | Table) on the right
- Preview pane renders simple text-friendly view (no deps) and updates on edit
- Table tools:
    * Detect multiple pipe tables and pick one to edit
    * Add/Delete rows
    * Export table to CSV or Markdown
    * Copy selection or entire table to clipboard as CSV or Markdown
    * Paste rows from clipboard as CSV or TSV
    * Commit changes back into the Markdown document
"""
import os
import re
import csv
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_NAME = "QuickMD"
SETTINGS_PATH = os.path.join(os.path.expanduser("~"), f".{APP_NAME.lower()}_settings.json")


# ---------------- Settings ----------------
def load_settings():
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_settings(s):
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(s, f)
    except Exception:
        pass


# ---------------- Markdown table model ----------------
class MarkdownTable:
    def __init__(self, header, aligns, rows):
        self.header = header or []
        self.aligns = aligns or []
        self.rows = rows or []

    def to_markdown(self):
        cols = len(self.header)
        widths = [len(self.header[i]) if i < len(self.header) else 0 for i in range(cols)]
        for r in self.rows:
            for i in range(cols):
                cell = r[i] if i < len(r) else ""
                widths[i] = max(widths[i], len(cell))

        def fmt_row(cells):
            out = []
            for i in range(cols):
                text = cells[i] if i < len(cells) else ""
                out.append(" " + text.ljust(widths[i]) + " ")
            return "|" + "|".join(out) + "|"

        def fmt_align(i):
            a = self.aligns[i] if i < len(self.aligns) else "left"
            if a == "left":
                d = ":" + "-" * (widths[i] + 1)
            elif a == "right":
                d = "-" * (widths[i] + 1) + ":"
            else:
                d = ":" + "-" * widths[i] + ":"
            return d

        md = [fmt_row(self.header)]
        md.append("|" + "|".join(fmt_align(i) for i in range(cols)) + "|")
        for r in self.rows:
            md.append(fmt_row(r))
        return "\n".join(md)


# ---------------- Markdown parsing helpers ----------------
def parse_pipe_table(lines, start_index):
    # Parse a GitHub style pipe table starting at start_index
    table_lines = []
    i = start_index
    while i < len(lines):
        ln = lines[i].rstrip("\n")
        if "|" in ln and ln.strip() != "":
            table_lines.append(ln)
            i += 1
        else:
            break
    if len(table_lines) < 2:
        return None, start_index

    def split_row(s):
        s = s.strip()
        if s.startswith("|"):
            s = s[1:]
        if s.endswith("|"):
            s = s[:-1]
        parts = [p.strip() for p in s.split("|")]
        return parts

    header = split_row(table_lines[0])
    separator = split_row(table_lines[1])

    # Validate separator row
    if not all(re.match(r"^:?-{2,}:?$", seg) for seg in separator):
        return None, start_index

    def align_of(seg):
        seg = seg.strip()
        left = seg.startswith(":")
        right = seg.endswith(":")
        if left and right:
            return "center"
        if right:
            return "right"
        return "left"

    aligns = [align_of(seg) for seg in separator]
    rows = [split_row(r) for r in table_lines[2:]]
    t = MarkdownTable(header, aligns, rows)
    return t, i


def find_tables(md_text):
    lines = md_text.splitlines()
    tables = []
    i = 0
    while i < len(lines):
        t, j = parse_pipe_table(lines, i)
        if t:
            tables.append((i, j, t))  # start, end (exclusive), table
            i = j
        else:
            i += 1
    return tables


def simple_markdown_to_text(md):
    # Simple preview: headings, emphasis, code fences and inline code
    out = []
    in_code = False
    for line in md.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            out.append("[code]" if in_code else "[/code]")
            continue
        if in_code:
            out.append(line)
            continue
        t = re.sub(r"\*\*(.+?)\*\*", r"[bold]\1[/bold]", line)
        t = re.sub(r"\*(.+?)\*", r"[italic]\1[/italic]", t)
        t = re.sub(r"`(.+?)`", r"[code]\1[/code]", t)
        out.append(t)
    return "\n".join(out)


# ---------------- App ----------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1400x800")
        self.file_path = None
        self.settings = load_settings()

        # Menubar
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New", command=self.new_file)
        filemenu.add_command(label="Open", command=self.open_file)
        filemenu.add_command(label="Save", command=self.save_file)
        filemenu.add_command(label="Save As", command=self.save_as)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=filemenu)
        self.config(menu=menubar)

        # Toolbar
        toolbar = ttk.Frame(self, padding=(6, 4))
        ttk.Button(toolbar, text="Open", command=self.open_file).pack(side="left", padx=(0, 4))
        ttk.Button(toolbar, text="Save", command=self.save_file).pack(side="left", padx=(0, 8))
        self.status = ttk.Label(toolbar, text="Ready")
        self.status.pack(side="right")
        toolbar.pack(fill="x")

        # Paned window: left editor, right tabs
        self.pane = ttk.PanedWindow(self, orient="horizontal")

        editor_frame = ttk.Frame(self.pane)
        self.editor = tk.Text(editor_frame, wrap="none", undo=True, font=("Consolas", 11))
        self.editor.bind("<<Modified>>", self.on_modified)
        editor_scroll_y = ttk.Scrollbar(editor_frame, command=self.editor.yview)
        self.editor.configure(yscrollcommand=editor_scroll_y.set)
        self.editor.pack(side="left", fill="both", expand=True)
        editor_scroll_y.pack(side="right", fill="y")

        right = ttk.Notebook(self.pane)

        # Preview tab
        preview_tab = ttk.Frame(right)
        self.preview = tk.Text(preview_tab, wrap="word", state="disabled", font=("Segoe UI", 11))
        pv_scroll = ttk.Scrollbar(preview_tab, command=self.preview.yview)
        self.preview.configure(yscrollcommand=pv_scroll.set)
        self.preview.pack(side="left", fill="both", expand=True)
        pv_scroll.pack(side="right", fill="y")
        right.add(preview_tab, text="Preview")

        # Table tab
        table_tab = ttk.Frame(right)
        topbar = ttk.Frame(table_tab)
        ttk.Label(topbar, text="Table:").pack(side="left")
        self.table_picker = ttk.Combobox(topbar, state="readonly", width=40, values=[])
        self.table_picker.bind("<<ComboboxSelected>>", lambda e: self.load_table_into_grid())
        self.btn_detect = ttk.Button(topbar, text="Detect Tables", command=self.detect_tables)
        self.btn_detect.pack(side="right")
        self.table_picker.pack(side="left", padx=(6, 8))
        topbar.pack(fill="x", padx=6, pady=6)

        self.table_cols = []
        self.tree = ttk.Treeview(table_tab, show="headings")
        tree_scroll_y = ttk.Scrollbar(table_tab, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set)
        self.tree.pack(fill="both", expand=True, side="left", padx=(6, 0), pady=(0, 6))
        tree_scroll_y.pack(fill="y", side="left", padx=(0, 6), pady=(0, 6))

        actions = ttk.Frame(table_tab)
        ttk.Label(actions, text="Actions").pack(anchor="w", pady=(8, 2))
        ttk.Button(actions, text="Add Row",
                   command=lambda: self.tree.insert("", "end", values=[""] * len(self.table_cols))).pack(fill="x", pady=2)
        ttk.Button(actions, text="Delete Row(s)", command=self.delete_rows).pack(fill="x", pady=2)
        ttk.Separator(actions, orient="horizontal").pack(fill="x", pady=6)
        ttk.Button(actions, text="Copy Selection (CSV)", command=lambda: self.copy_selection(fmt="csv")).pack(fill="x", pady=2)
        ttk.Button(actions, text="Copy All (CSV)", command=lambda: self.copy_all(fmt="csv")).pack(fill="x", pady=2)
        ttk.Button(actions, text="Copy All (Markdown)", command=lambda: self.copy_all(fmt="md")).pack(fill="x", pady=2)
        ttk.Button(actions, text="Paste Rows (CSV/TSV)", command=self.paste_rows).pack(fill="x", pady=2)
        ttk.Separator(actions, orient="horizontal").pack(fill="x", pady=6)
        ttk.Button(actions, text="Export CSV...", command=self.export_csv).pack(fill="x", pady=2)
        ttk.Button(actions, text="Export Markdown...", command=self.export_md).pack(fill="x", pady=2)
        ttk.Separator(actions, orient="horizontal").pack(fill="x", pady=6)
        ttk.Button(actions, text="Commit to Markdown", command=self.commit_table_to_md).pack(fill="x", pady=4)
        actions.pack(side="left", fill="y", padx=6, pady=(0, 6))

        right.add(table_tab, text="Table")

        self.pane.add(editor_frame, weight=1)
        self.pane.add(right, weight=1)
        self.pane.pack(fill="both", expand=True)

        # Table state
        self.current_tables = []         # list of (start, end, MarkdownTable)
        self.current_table_index = None  # index into self.current_tables

        # Load last file or starter content
        last = self.settings.get("last_file")
        if last and os.path.exists(last):
            self.load_file(last)
        else:
            self.editor.insert(
                "1.0",
                "# New Document\n\nType here...\n\n"
                "| Col A | Col B |\n"
                "| :--- | ---: |\n"
                "| one | 1 |\n"
                "| two | 2 |\n"
            )
            self.update_preview()

        # Enable in-place editing of cells on double click
        self.tree.bind("<Double-1>", self.edit_cell)

    # ------------- File ops -------------
    def new_file(self):
        self.editor.delete("1.0", "end")
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.configure(state="disabled")
        self.file_path = None
        self.status.config(text="New file")
        self.current_tables = []
        self.table_picker["values"] = []
        self.table_cols = []
        self.rebuild_tree_columns([])

    def open_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Markdown", "*.md *.markdown *.mdown *.mkd"), ("All files", "*.*")]
        )
        if not path:
            return
        self.load_file(path)

    def load_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Failed to open file\n{e}")
            return
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", text)
        self.file_path = path
        self.status.config(text=path)
        self.settings["last_file"] = path
        save_settings(self.settings)
        self.update_preview()
        self.detect_tables()

    def save_file(self):
        if not self.file_path:
            return self.save_as()
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(self.editor.get("1.0", "end-1c"))
            self.status.config(text=f"Saved {self.file_path}")
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Failed to save file\n{e}")

    def save_as(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".md", filetypes=[("Markdown", "*.md *.markdown"), ("All files", "*.*")]
        )
        if not path:
            return
        self.file_path = path
        self.save_file()

    # ------------- Preview -------------
    def on_modified(self, event=None):
        if self.editor.edit_modified():
            self.editor.edit_modified(False)
            self.after(200, self.update_preview)

    def update_preview(self):
        md = self.editor.get("1.0", "end-1c")
        txt = simple_markdown_to_text(md)
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", txt)
        self.preview.configure(state="disabled")

    # ------------- Table ops -------------
    def detect_tables(self):
        md = self.editor.get("1.0", "end-1c")
        self.current_tables = find_tables(md)
        if not self.current_tables:
            self.table_picker["values"] = []
            self.table_picker.set("")
            self.rebuild_tree_columns([])
            messagebox.showinfo(APP_NAME, "No pipe tables found in the document.")
            return
        labels = []
        for idx, (start, end, t) in enumerate(self.current_tables):
            header_preview = " | ".join(t.header) if t.header else f"Table {idx+1}"
            labels.append(f"{idx+1}: {header_preview}")
        self.table_picker["values"] = labels
        self.table_picker.current(0)
        self.current_table_index = 0
        self.load_table_into_grid()

    def load_table_into_grid(self):
        sel = self.table_picker.current()
        if sel is None or sel < 0:
            return
        self.current_table_index = sel
        _, _, t = self.current_tables[sel]
        cols = len(t.header)
        self.table_cols = [f"c{i}" for i in range(cols)]
        self.rebuild_tree_columns(t.header)

        # load rows
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for row in t.rows:
            values = [row[i] if i < len(row) else "" for i in range(cols)]
            self.tree.insert("", "end", values=values)

    def rebuild_tree_columns(self, headers):
        self.tree["columns"] = [f"c{i}" for i in range(len(headers))]
        for i, h in enumerate(headers):
            col = f"c{i}"
            self.tree.heading(col, text=h or f"Column {i+1}")
            width = max(80, min(300, (len(h) if h else 10) * 12))
            self.tree.column(col, width=width, anchor="w")

    def edit_cell(self, event):
        item = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not item or not col:
            return
        col_index = int(col[1:]) - 1
        bbox = self.tree.bbox(item, column=col)
        if not bbox:
            return
        x, y, w, h = bbox
        value_list = list(self.tree.item(item, "values"))
        current = value_list[col_index] if col_index < len(value_list) else ""
        entry = tk.Entry(self.tree)
        entry.place(x=x, y=y, width=w, height=h)
        entry.insert(0, current)
        entry.focus_set()

        def commit(event=None):
            value_list[col_index] = entry.get()
            self.tree.item(item, values=value_list)
            entry.destroy()

        entry.bind("<Return>", commit)
        entry.bind("<Escape>", lambda e: entry.destroy())
        entry.bind("<FocusOut>", commit)

    def delete_rows(self):
        sel = self.tree.selection()
        if not sel:
            return
        for iid in sel:
            self.tree.delete(iid)

    # ------------- Clipboard and export -------------
    def copy_selection(self, fmt="csv"):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(APP_NAME, "No rows selected.")
            return
        data = [self.tree.item(iid, "values") for iid in sel]
        self._clipboard_copy(data, fmt=fmt)

    def copy_all(self, fmt="csv"):
        data = [self.tree.item(iid, "values") for iid in self.tree.get_children()]
        if not data:
            messagebox.showinfo(APP_NAME, "No table loaded.")
            return
        self._clipboard_copy(data, fmt=fmt)

    def _clipboard_copy(self, rows, fmt="csv"):
        headers = [self.tree.heading(c)["text"] for c in self.tree["columns"]]
        if fmt == "md":
            t = MarkdownTable(headers, ["left"] * len(headers), rows).to_markdown()
            text = t
        else:
            output = []
            output.append(",".join(_escape_csv(h) for h in headers))
            for r in rows:
                output.append(",".join(_escape_csv(str(x)) for x in r))
            text = "\n".join(output)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status.config(text=f"Copied {len(rows)} row(s) to clipboard as {fmt.upper()}")

    def paste_rows(self):
        try:
            text = self.clipboard_get()
        except tk.TclError:
            messagebox.showinfo(APP_NAME, "Clipboard is empty or not text.")
            return
        rows = _parse_delimited(text, delimiter=",")
        if len(rows) <= 1:
            rows = _parse_delimited(text, delimiter="\t")
        if not rows:
            messagebox.showerror(APP_NAME, "Clipboard does not appear to contain CSV or TSV data.")
            return
        headers = [self.tree.heading(c)["text"] for c in self.tree["columns"]]
        start_idx = 1 if rows and _header_matches(rows[0], headers) else 0
        count = 0
        cols = len(self.tree["columns"])
        for r in rows[start_idx:]:
            values = [r[i] if i < len(r) else "" for i in range(cols)]
            self.tree.insert("", "end", values=values)
            count += 1
        self.status.config(text=f"Pasted {count} row(s) from clipboard")

    def export_csv(self):
        if not self.tree["columns"]:
            messagebox.showinfo(APP_NAME, "No table loaded.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        headers = [self.tree.heading(c)["text"] for c in self.tree["columns"]]
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(headers)
            for iid in self.tree.get_children():
                w.writerow(list(self.tree.item(iid, "values")))
        self.status.config(text=f"Exported CSV: {path}")

    def export_md(self):
        if not self.tree["columns"]:
            messagebox.showinfo(APP_NAME, "No table loaded.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".md", filetypes=[("Markdown", "*.md")])
        if not path:
            return
        headers = [self.tree.heading(c)["text"] for c in self.tree["columns"]]
        rows = [list(self.tree.item(iid, "values")) for iid in self.tree.get_children()]
        t = MarkdownTable(headers, ["left"] * len(headers), rows)
        with open(path, "w", encoding="utf-8") as f:
            f.write(t.to_markdown())
        self.status.config(text=f"Exported Markdown table: {path}")

    # ------------- Commit back -------------
    def commit_table_to_md(self):
        if self.current_table_index is None:
            messagebox.showinfo(APP_NAME, "No table selected.")
            return
        headers = [self.tree.heading(c)["text"] for c in self.tree["columns"]]
        rows = [list(self.tree.item(iid, "values")) for iid in self.tree.get_children()]
        start, end, old_table = self.current_tables[self.current_table_index]
        new_table = MarkdownTable(headers, old_table.aligns, rows)
        new_md_table = new_table.to_markdown()

        md = self.editor.get("1.0", "end-1c")
        lines = md.splitlines()
        md_before = "\n".join(lines[:start])
        md_after = "\n".join(lines[end:])
        combined = (md_before + "\n" if md_before else "") + new_md_table + ("\n" + md_after if md_after else "")
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", combined)
        self.update_preview()
        self.detect_tables()
        self.status.config(text="Table committed back to Markdown")


# ---------------- Small helpers ----------------
def _escape_csv(s):
    if any(ch in s for ch in [",", '"', "\n", "\r"]):
        s = '"' + s.replace('"', '""') + '"'
    return s


def _parse_delimited(text, delimiter=","):
    rows = []
    reader = csv.reader(text.splitlines(), delimiter=delimiter)
    for r in reader:
        rows.append(r)
    return rows


def _header_matches(row, headers):
    row_norm = [str(c).strip().lower() for c in row]
    hdr_norm = [str(c).strip().lower() for c in headers]
    return row_norm == hdr_norm


# ---------------- main ----------------
if __name__ == "__main__":
    app = App()
    app.mainloop()
