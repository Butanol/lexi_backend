"""Preprocess raw documents into cleaned text files in data/processed.

This script is intentionally minimal: it discovers PDF files in data/raw and extracts text
using pdfminer or falls back to reading .txt files.
"""
import sys
from pathlib import Path
from pdfminer.high_level import extract_text


DATA_RAW = Path(__file__).resolve().parents[2] / "data" / "raw"
DATA_PROCESSED = Path(__file__).resolve().parents[2] / "data" / "processed"
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)


def process_pdf(path: Path) -> str:
    try:
        return extract_text(str(path))
    except Exception as e:
        print(f"Failed to extract {path}: {e}")
        return ""


def main():
    for p in DATA_RAW.glob("**/*"):
        if p.suffix.lower() == ".pdf":
            text = process_pdf(p)
            out = DATA_PROCESSED / (p.stem + ".txt")
            out.write_text(text, encoding="utf-8")
            print(f"Wrote {out}")
        elif p.suffix.lower() == ".txt":
            # copy
            out = DATA_PROCESSED / p.name
            out.write_text(p.read_text(encoding='utf-8'), encoding='utf-8')
            print(f"Copied {p} -> {out}")


if __name__ == "__main__":
    main()
