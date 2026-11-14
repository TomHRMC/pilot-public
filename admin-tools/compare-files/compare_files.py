import difflib
import argparse
import webbrowser
import os
from datetime import datetime

# UPDATED CSS: Clean, 3-column layout with forced wrapping for long strings
CUSTOM_CSS = """
<style>
    body { font-family: -apple-system, system-ui, sans-serif; padding: 20px; color: #24292f; background-color: #f8f9fa; }
    .summary { margin-bottom: 20px; padding: 20px; border: 1px solid #d0d7de; border-radius: 6px; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .diff-wrapper { width: 100%; border: 1px solid #d0d7de; border-radius: 6px; background: white; overflow: hidden; }
    
    table { width: 100%; border-collapse: collapse; table-layout: fixed; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 12px; }
    
    /* Column 1: Line Number */
    .ln { width: 50px; color: #afb8c1; text-align: right; padding: 0 10px; border-right: 1px solid #d0d7de; user-select: none; background: #f6f8fa; }
    
    /* Columns 2 & 3: Content - Handles indentation and wrapping */
    .code { 
        width: 47%; 
        white-space: pre-wrap;       
        word-break: break-all;      
        padding: 4px 12px; 
        vertical-align: top; 
        border-right: 1px solid #d0d7de; 
        line-height: 1.6;
    }
    .code:last-child { border-right: none; }

    /* Clean Highlight Colors */
    .add { background-color: #dafbe1; color: #1a7f37; }
    .del { background-color: #ffebe9; color: #cf222e; }
    .mod { background-color: #fff8c5; color: #9a6700; }
    
    tr { border-bottom: 1px solid #f0f0f0; }
    h2 { margin: 0 0 10px 0; font-size: 20px; color: #1f2328; }
    .file-comparison-line { margin-bottom: 15px; font-size: 14px; color: #57606a; border-bottom: 1px solid #eaeef2; padding-bottom: 10px; }
</style>
"""

def compare_files(file1_path, file2_path, output_base):
    try:
        # Get absolute paths for the header
        abs1 = os.path.basename(file1_path)
        abs2 = os.path.basename(file2_path)

        with open(file1_path, 'r', encoding='utf-8') as f1, open(file2_path, 'r', encoding='utf-8') as f2:
            lines1, lines2 = f1.readlines(), f2.readlines()

        d = difflib.Differ()
        diff = list(d.compare(lines1, lines2))

        rows = ""
        ln1, ln2 = 1, 1
        stats = {'+': 0, '-': 0, 'mod': 0}

        for line in diff:
            tag = line[0]
            code = line[2:].rstrip()
            
            if tag == ' ': 
                rows += f'<tr><td class="ln">{ln1}</td><td class="code">{code}</td><td class="code">{code}</td></tr>'
                ln1 += 1; ln2 += 1
            elif tag == '-': 
                rows += f'<tr><td class="ln">{ln1}</td><td class="code del">{code}</td><td class="code"></td></tr>'
                ln1 += 1; stats['-'] += 1
            elif tag == '+': 
                rows += f'<tr><td class="ln">{ln2}</td><td class="code"></td><td class="code add">{code}</td></tr>'
                ln2 += 1; stats['+'] += 1
            elif tag == '?':
                stats['mod'] += 1

        # Assemble Final HTML with the requested file names in the header
        html_content = f"""<!DOCTYPE html><html><head>{CUSTOM_CSS}</head><body>
            <div class="summary">
                <h2>File Comparison Report</h2>
                <div class="file-comparison-line">
                    <strong>File #1:</strong> <code style="color:#cf222e">{abs1}</code> 
                    <span style="margin: 0 10px;">➔</span> 
                    <strong>File #2:</strong> <code style="color:#1a7f37">{abs2}</code>
                </div>
                <p style="font-size: 12px; color:#8c959f; margin-bottom: 15px;">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <div style="font-size: 14px;">
                    <b style="color:#1a7f37">Added: {stats['+']}</b> | 
                    <b style="color:#cf222e">Deleted: {stats['-']}</b> | 
                    <b style="color:#9a6700">Modified: {stats['mod'] // 2}</b>
                </div>
            </div>
            <div class="diff-wrapper"><table>{rows}</table></div>
        </body></html>"""

        output_file = f"{output_base}.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Save TXT version
        with open(f"{output_base}.txt", 'w', encoding='utf-8') as f:
            f.write('\n'.join(diff))

        print(f"Comparison complete. Opening {output_file}...")
        webbrowser.open(f"file://{os.path.abspath(output_file)}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare two files with a clean 3-column HTML output.")
    parser.add_argument("f1", help="Path to the first file")
    parser.add_argument("f2", help="Path to the second file")
    parser.add_argument("out", help="Base name for the output files")
    args = parser.parse_args()
    compare_files(args.f1, args.f2, args.out)