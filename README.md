# mdCSV

**mdCSV** is a lightweight, no-dependency **Markdown ↔ CSV management tool** for Windows 11 built in pure Python (Tkinter). It’s designed for **database-friendly workflows**, letting you easily **view, edit, convert, and export** Markdown tables to and from CSV — all side-by-side with a live Markdown and CSV Table preview.


## ✨ Features

- **Side-by-side editing**
  - Markdown editor on the left
  - Live rendered preview on the right
- **Full Table Editing Suite**
  - Detect multiple Markdown pipe tables in a document
  - Switch between tables with a dropdown selector
  - Add/Delete rows
  - Copy selection or entire table to clipboard as CSV or Markdown
  - Paste rows from clipboard (CSV or TSV)
  - Export any table to CSV or Markdown file
  - Commit changes back to the Markdown file
- **Database-Ready Conversions**
  - Convert Markdown tables to clean CSV for import into database tools
  - Convert CSV exports back into proper Markdown tables
- **Lightweight & Portable**
  - 100% Python standard library — no pip installs needed
  - Runs on any system with Python 3.x + Tkinter
- **Smart File Handling**
  - Open, Save, Save As
  - Remembers last opened file on startup


## 📦 Installation

1. **Clone the repo**:
   ```powershell
   git clone https://github.com/YOURUSERNAME/mdCSV.git
   cd mdCSV

2. **(Optional) Create & activate the `mdCSV` environment**:

   ```powershell
   python -m venv mdCSV
   .\mdCSV\Scripts\Activate.ps1
   ```

3. **Run mdCSV**:

   ```powershell
   python mdCSV.py
   ```


## 🖥 Usage

* **Markdown Editing:** Edit any `.md` file in the left pane.
* **Preview:** Live preview updates automatically in the right pane.
* **Table Tools:**

  1. Click **Detect Tables** to load all Markdown tables.
  2. Select a table from the dropdown.
  3. Edit cells, add/remove rows, paste CSV/TSV data.
  4. Export to CSV or Markdown, or copy to clipboard.
  5. Click **Commit to Markdown** to update the document.


## 📸 Screenshots

<img width="1570" height="637" alt="mdCSV-screenshot1" src="https://github.com/user-attachments/assets/d4e0776a-20c7-4f77-97c5-4284978eb9f9" />

<img width="1571" height="642" alt="mdCSV-screenshot2" src="https://github.com/user-attachments/assets/de0ccbdf-924d-4409-8dcc-769813732d21" />

## 📝 Requirements

* Python **3.8+**
* Tkinter (included with most Python installations)
* Windows 11 recommended for modern UI (works cross-platform with Tkinter)


## ⚖ License

MIT License — see [LICENSE](LICENSE) for details.


## 💡 Notes

* mdCSV is ideal for anyone working with Markdown-based data storage, GitHub wikis, or documentation that contains tables.
* Use it as a quick CSV-to-Markdown converter without installing large apps or extensions.
* Tested on Windows 11 + Python 3.12.
