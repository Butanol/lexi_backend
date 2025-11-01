"""Trim headers and footers from a PDF and extract trimmed text.

This script crops each page by default removing the top 10% and bottom 8% of
the page height (adjustable via command-line args). It saves a cropped PDF
and a plain-text extraction of the cropped content.

Usage:
    python remove_headers_footers.py [input_pdf] [--top 0.10] [--bottom 0.08]

By default it processes: logs/temp/HKMA.pdf and writes:
  - logs/temp/HKMA_trimmed.pdf
  - langchain-workflow/data/processed/HKMA_trimmed.txt
"""
from pathlib import Path
import argparse
import sys
import json

def main():
    parser = argparse.ArgumentParser(description="Trim headers/footers from PDF pages")
    default_input = Path(__file__).resolve().parents[1] / "logs" / "temp" / "HKMA.pdf"
    parser.add_argument("input", nargs="?", default=str(default_input), help="Input PDF path")
    parser.add_argument("--top", type=float, default=0.10, help="Fraction of page height to trim from top (0-0.4)")
    parser.add_argument("--bottom", type=float, default=0.08, help="Fraction of page height to trim from bottom (0-0.4)")
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"Input PDF not found: {in_path}")
        sys.exit(1)

    out_pdf = in_path.parent / (in_path.stem + "_trimmed" + in_path.suffix)
    processed_dir = Path(__file__).resolve().parents[2] / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_txt = processed_dir / (in_path.stem + "_trimmed.txt")

    try:
        import fitz
    except Exception:
        print("PyMuPDF (fitz) is required. Install with: pip install PyMuPDF")
        sys.exit(2)

    doc = fitz.open(str(in_path))
    trimmed_text_parts = []
    top_lines_acc = []
    bottom_lines_acc = []

    for i, page in enumerate(doc):
        rect = page.rect
        top_cut = rect.y0 + rect.height * args.top
        bottom_cut = rect.y1 - rect.height * args.bottom
        clip = fitz.Rect(rect.x0, top_cut, rect.x1, bottom_cut)

        # extract text within clipped area
        try:
            page_text = page.get_text("text", clip=clip)
        except Exception as e:
            print(f"Warning: failed to extract page {i+1}: {e}")
            page_text = ""

        # collect top/bottom lines for repeated-header/footer detection
        lines = [l.strip() for l in page_text.splitlines() if l.strip()]
        top_lines_acc.append(lines[:3])
        bottom_lines_acc.append(lines[-3:])

        trimmed_text_parts.append(page_text.strip())

        # apply crop to page so saved PDF will be trimmed
        try:
            page.set_cropbox(clip)
        except Exception:
            # fallback: use mediabox if cropbox unsupported
            try:
                page.set_media_box(clip)
            except Exception:
                pass

    # detect repeated header/footer lines across pages and remove them from
    # the extracted page texts. Also remove explicit patterns like 'Cap. 615'
    # and lines that look like section numbers (e.g., '1.' or '2.1').
    from collections import Counter

    def _normalize(s: str) -> str:
        return " ".join(s.split()).lower()

    page_count = len(trimmed_text_parts)
    # flatten and count
    top_flat = [l for sub in top_lines_acc for l in sub if l]
    bottom_flat = [l for sub in bottom_lines_acc for l in sub if l]
    top_counts = Counter([_normalize(l) for l in top_flat])
    bottom_counts = Counter([_normalize(l) for l in bottom_flat])

    # threshold: appears on at least 50% of pages
    threshold = max(1, int(page_count * 0.5))
    repeated_headers = {k for k, v in top_counts.items() if v >= threshold}
    repeated_footers = {k for k, v in bottom_counts.items() if v >= threshold}

    # always remove 'cap. 615' if present
    repeated_headers.add(_normalize("Cap. 615"))

    import re

    cleaned_pages = []
    removed_patterns = set()
    for text in trimmed_text_parts:
        lines = [l for l in text.splitlines()]
        new_lines = []
        for ln in lines:
            n = _normalize(ln)
            # remove if matches repeated header/footer
            if n in repeated_headers or n in repeated_footers:
                removed_patterns.add(ln.strip())
                continue
            # remove if contains 'cap. 615'
            if "cap. 615" in n:
                removed_patterns.add("cap. 615")
                continue
            # remove section-number-only lines like '1.' or '2.1'
            if re.match(r"^\s*\d+(?:[\.]\d+)*\s*\.?\s*$", ln):
                removed_patterns.add(ln.strip())
                continue
            new_lines.append(ln)
        cleaned_pages.append("\n".join(new_lines).strip())

    # save metadata about removals
    meta = {
        "input": str(in_path),
        "pages": page_count,
        "removed_patterns": sorted(list(removed_patterns)),
    }

    meta_path = processed_dir / (in_path.stem + "_trimmed_meta.json")

    try:
        doc.save(str(out_pdf))
        print(f"Wrote trimmed PDF: {out_pdf}")
    except Exception as e:
        print(f"Failed to save trimmed PDF: {e}")

    # write trimmed text (cleaned)
    try:
        out_txt.write_text("\n\n".join([p for p in cleaned_pages if p]), encoding="utf-8")
        print(f"Wrote trimmed text: {out_txt}")
    except Exception as e:
        print(f"Failed to write trimmed text: {e}")

    try:
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote metadata: {meta_path}")
    except Exception as e:
        print(f"Failed to write metadata: {e}")


if __name__ == "__main__":
    main()
