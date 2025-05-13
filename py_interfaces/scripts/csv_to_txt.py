#!/usr/bin/env python3
import os
import csv
import argparse

def row_to_text(row: dict) -> str:
    """
    Convert a CSV/TSV row dict into a plain‑text block
    listing each field:value on its own line.
    """
    lines = []
    for key, val in row.items():
        # If the cell contains JSON-like lists, you can leave them as-is
        # or pretty‑print them here with json.dumps(json.loads(val), indent=2)
        lines.append(f"{key}: {val}")
    return "\n".join(lines)

def main(input_file: str,
         output_dir: str,
         delimiter: str = "\t",
         id_field: str = "id"):
    os.makedirs(output_dir, exist_ok=True)
    with open(input_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for i, row in enumerate(reader):
            # Use the “id” column (or row index) as filename
            fname = row.get(id_field) or str(i)
            # sanitize fname if needed
            fname = "".join(c for c in fname if c.isalnum() or c in ("-", "_")).rstrip()
            out_path = os.path.join(output_dir, f"{fname}.txt")
            with open(out_path, "w", encoding="utf-8") as out:
                out.write(row_to_text(row))
    print(f"Wrote {i+1} text files to {output_dir}")

if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Turn each row of a CSV/TSV into its own .txt file")
    p.add_argument("input_file", help="Path to your CSV/TSV dataset")
    p.add_argument("output_dir", help="Directory to write .txt files into")
    p.add_argument("--delimiter", "-d",
                   default="\t",
                   help="Field delimiter (default: tab)")
    p.add_argument("--id-field", "-i",
                   default="id",
                   help="Which column to use for filenames (default: 'id')")
    args = p.parse_args()
    main(args.input_file, args.output_dir, args.delimiter, args.id_field)