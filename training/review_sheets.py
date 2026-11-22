"""Native-speaker review of the test set as Excel files, and applying the answers back.

Run from the repo root:
    python training/review_sheets.py export   # writes data/processed/review_kn.xlsx and review_kok.xlsx
    python training/review_sheets.py import data/processed/review_kn.xlsx [review_kok.xlsx ...]
Import copies fixed translations into data/processed/constitution_test.csv and marks the row
reviewed=yes once every language in it has been checked (OK or a fix).
"""
import csv
import sys

from aksharamukha import transliterate
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

TEST = "data/processed/constitution_test.csv"
LANGS = {"kn": ("Kannada", "kn"), "kok": ("Konkani", "kok_deva")}
INSTRUCTIONS = """How to review (about 30 minutes)

Each row is one sentence from the Constitution of India: the English text and its OFFICIAL {name}
translation. The {name} text was read from a scanned PDF by a computer (OCR), so a few letters may
be wrong. We use these rows to measure our translation system, so they must be correct.

For each row in the "Review" sheet:
  1. Read the English, then the {name} text.
  2. In column "Check", choose:
       OK   - the {name} text is correct (small style differences are fine; do NOT rewrite it)
       FIX  - there is a wrong letter, missing word, or text from another sentence
  3. If FIX: type the corrected {name} text in column "Corrected text".
     Only fix mistakes. Do not change the wording to your own style.
  4. Anything unsure? Write it in "Notes".

You do not need to check numbers like (2), 21A or 1950 - keep them as they are.
Save the file and send it back. Thank you!"""


def export():
    rows = list(csv.DictReader(open(TEST, encoding="utf-8-sig")))
    for lang, (name, col) in LANGS.items():
        wb = Workbook()
        info = wb.active
        info.title = "Instructions"
        info["A1"] = INSTRUCTIONS.format(name=name)
        info["A1"].alignment = Alignment(wrap_text=True, vertical="top")
        info.column_dimensions["A"].width = 110
        info.row_dimensions[1].height = 400
        ws = wb.create_sheet("Review")
        header = ["id", "English", f"Official {name}", "Check", "Corrected text", "Notes"]
        if lang == "kok":  # Karnataka Konkani speakers often read Kannada script more easily
            header.insert(3, "Same text in Kannada script (for reading only)")
        ws.append(header)
        for r in rows:
            line = [r["id"], r["en"], r[col], "", "", ""]
            if lang == "kok":
                line.insert(3, transliterate.process("Devanagari", "Kannada", r[col]))
            ws.append(line)
        check_col = "E" if lang == "kok" else "D"
        dv = DataValidation(type="list", formula1='"OK,FIX"', allow_blank=True)
        ws.add_data_validation(dv)
        dv.add(f"{check_col}2:{check_col}{len(rows) + 1}")
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="FFF2CC")
        widths = {"A": 9, "B": 55, "C": 55, "D": 55 if lang == "kok" else 10, "E": 10 if lang == "kok" else 55,
                  "F": 55 if lang == "kok" else 25, "G": 25}
        for c, w in widths.items():
            ws.column_dimensions[c].width = w
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "B2"
        out = f"data/processed/review_{lang}.xlsx"
        wb.save(out)
        print(f"wrote {out} ({len(rows)} rows)")


def import_(paths):
    rows = list(csv.DictReader(open(TEST, encoding="utf-8-sig")))
    by_id = {r["id"]: r for r in rows}
    checked = {r["id"]: set() for r in rows}
    for path in paths:
        ws = load_workbook(path)["Review"]
        header = [c.value for c in ws[1]]
        lang = "kok" if header[2] == "Official Konkani" else "kn"
        col = LANGS[lang][1]
        i_id, i_check, i_fix = header.index("id"), header.index("Check"), header.index("Corrected text")
        n_ok = n_fix = n_todo = 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            rid, check, fix = row[i_id], (row[i_check] or "").strip().upper(), (row[i_fix] or "").strip()
            if rid not in by_id:
                continue
            if check == "OK":
                n_ok += 1
                checked[rid].add(lang)
            elif check == "FIX" and fix:
                by_id[rid][col] = fix
                n_fix += 1
                checked[rid].add(lang)
            else:
                n_todo += 1  # blank, or FIX without a correction: leave it unreviewed
        print(f"{path}: {n_ok} OK, {n_fix} fixed, {n_todo} not done")
    for r in rows:
        if checked[r["id"]] >= set(LANGS):
            r["reviewed"] = "yes"
    with open(TEST, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"{sum(r['reviewed'] == 'yes' for r in rows)}/{len(rows)} rows now reviewed=yes in both languages")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1:2] == ["export"]:
        export()
    elif sys.argv[1:2] == ["import"] and len(sys.argv) > 2:
        import_(sys.argv[2:])
    else:
        sys.exit(__doc__)
