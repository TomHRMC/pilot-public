This `README.md` is designed to be clear and professional, making it easy for anyone to understand how to use your new comparison tool. You can save this text into a file named `README.md` in the same folder as your script.

---

# File Comparison Tool

A robust Python utility designed to compare two text or JSON files and generate clean, readable reports. It produces a **Side-by-Side HTML** report for visual review and a **Unified TXT** diff for quick terminal checks or logging.

## 🚀 Features

* **Clean 3-Column Layout:** Displays Line Numbers, File #1 Content, and File #2 Content.
* **Intelligent Wrapping:** Automatically wraps long strings (like JSON notes or long code lines) within their columns to prevent overlapping.
* **Detailed Summary:** Provides a count of Added, Deleted, and Modified lines at the top of the report.
* **Automatic Browser Launch:** Opens the HTML report in your default web browser immediately after generation.

## 🛠 How to Run

Ensure you have **Python 3** installed on your system. No external libraries are required as the script uses Python's built-in `difflib`.

### Command Syntax

```bash
python3 compare_files_final.py <file1> <file2> <output_name>

```

### Example

To compare `old_config.json` with `new_config.json` and create reports named `SyncReport`, run:

```bash
python3 compare_files_final.py old_config.json new_config.json SyncReport

```

## 📊 Interpreting the Output

The script generates two files: `<output_name>.html` and `<output_name>.txt`.

### HTML Report (Visual)

The HTML report uses color-coding to highlight differences:

* 🟢 **Green (Added):** Text that exists in File #2 but was not in File #1.
* 🔴 **Red (Deleted):** Text that was in File #1 but has been removed in File #2.
* 🟡 **Yellow (Modified):** Indicates a line that exists in both but contains internal changes.

### TXT Report (Technical)

The `.txt` file uses the standard "Unified Diff" format:

* Lines starting with `+` are additions.
* Lines starting with `-` are deletions.
* Lines starting with `     ` (space) are unchanged.

## 📋 Requirements

* **Python:** 3.6 or higher.
* **OS:** Windows, macOS, or Linux.

---

Would you like me to add a section on how to troubleshoot file encoding issues if you ever run into non-English characters?