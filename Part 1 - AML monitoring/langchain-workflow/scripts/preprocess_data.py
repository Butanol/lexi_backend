"""Preprocess raw documents into cleaned text files in data/processed.

This script extracts text from PDFs and (optionally) translates the extracted
text to English using the JigsawStack Text Translate API if configured.

Behavior:
- Uses pdfminer.six to extract text from PDFs.
- The JigsawStack translate endpoint and API key are read from environment
    variables: `JIGSAWSTACK_TRANSLATE_URL` and `JIGSAWSTACK_API_KEY`.
"""

import os
import sys
from pathlib import Path
from typing import Optional
import json

from pdfminer.high_level import extract_text
import requests


DATA_RAW = Path(__file__).resolve().parents[2] / "data" / "raw"
DATA_PROCESSED = Path(__file__).resolve().parents[2] / "data" / "processed"
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)


def process_pdf(path: Path) -> str:
    try:
        return extract_text(str(path))
    except Exception as e:
        print(f"Failed to extract {path}: {e}")
        return ""



def translate_text_jigsaw(text: str, target: str = "en") -> Optional[str]:
    """Translate text using JigsawStack Text Translate API.

    Requires environment variables:
      - JIGSAWSTACK_API_KEY
      - JIGSAWSTACK_TRANSLATE_URL (optional; default assumed)

    The function is conservative: on any error it returns None.
    """
    api_key = os.environ.get("JIGSAWSTACK_API_KEY")
    if not api_key:
        print("JIGSAWSTACK_API_KEY not set; skipping translation")
        return None

    translate_url = os.environ.get("JIGSAWSTACK_TRANSLATE_URL", "https://api.jigsawstack.com/v1/translate")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    # The API supports receiving the text as a plain string. Some deployments
    # may return `translated_text` as a list (one element) or as a string.
    # Send the document as a string and accept both kinds of responses.
    payload = {"text": text, "target_language": target}

    try:
        r = requests.post(translate_url, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        # Common successful shapes:
        # 1) { "success": true, "translated_text": "..." }
        # 2) { "success": true, "translated_text": ["..."] }
        if isinstance(data, dict) and "translated_text" in data:
            t = data["translated_text"]
            if isinstance(t, list):
                return "\n\n".join(t) if t else None
            if isinstance(t, str):
                return t

        # Fallback: handle other simple variants
        if isinstance(data, dict):
            for key in ("translation", "text", "translated"):
                if key in data and isinstance(data[key], str):
                    return data[key]
        if isinstance(data, str):
            return data
    except Exception as e:
        print(f"Translation request failed: {e}")

    return None


def main():
    for p in DATA_RAW.glob("**/*"):
        if p.suffix.lower() == ".pdf":
            text = process_pdf(p)

            # Always attempt to translate the extracted text to English via JigsawStack.
            translated = translate_text_jigsaw(text, target="en")
            if translated:
                out_text = translated
                meta = {"source_file": str(p), "translated": True, "detected_language": None}
            else:
                out_text = text
                meta = {"source_file": str(p), "translated": False, "detected_language": None}

            out = DATA_PROCESSED / (p.stem + ".txt")
            # Write a small JSON front-matter followed by the text to make provenance explicit
            try:
                out.write_text(json.dumps(meta, ensure_ascii=False) + "\n\n" + out_text, encoding="utf-8")
                print(f"Wrote {out} (lang={meta.get('detected_language')}, translated={meta['translated']})")
            except Exception as e:
                print(f"Failed to write {out}: {e}")

        elif p.suffix.lower() == ".txt":
            # copy
            out = DATA_PROCESSED / p.name
            out.write_text(p.read_text(encoding='utf-8'), encoding='utf-8')
            print(f"Copied {p} -> {out}")


if __name__ == "__main__":
    main()
