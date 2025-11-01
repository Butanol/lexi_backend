"""Utilities to detect whether a newly downloaded PDF differs from the previously
archived PDF in the logs/temp folder by comparing SHA-256 hashes.

Usage:
    from langchain_modules.tools.pdf_change_detector import compare_with_previous

    result = compare_with_previous("/path/to/new.pdf")

Returns a dict with keys:
  - different: bool
  - new_hash: str
  - prev_hash: str or None
  - prev_path: str or None
  - archived_path: str or None (where the new file was archived)
  - reason: optional string for informational messages

This function will, by default, archive the new PDF into the project `logs/temp` folder
so subsequent runs can compare against it.
"""
from pathlib import Path
import hashlib
import shutil
from datetime import datetime, timezone
from typing import Optional, Dict, Any


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compare_with_previous(new_pdf_path: str, logs_temp_dir: Optional[str] = None, archive_new: bool = True) -> Dict[str, Any]:
    """Compare SHA-256 of new_pdf_path with the most recent PDF in logs_temp_dir.

    If logs_temp_dir is not provided, defaults to the `logs/temp` folder under the
    `langchain-workflow` project root (calculated relative to this file).
    """
    new_pdf = Path(new_pdf_path).resolve()
    if not new_pdf.exists():
        raise FileNotFoundError(f"New PDF not found: {new_pdf}")

    # Default logs/temp under langchain-workflow
    if logs_temp_dir is None:
        logs_temp_dir = Path(__file__).resolve().parents[2] / "logs" / "temp"
    else:
        logs_temp_dir = Path(logs_temp_dir)

    logs_temp_dir.mkdir(parents=True, exist_ok=True)

    new_hash = _sha256_of_file(new_pdf)

    # Find candidate previous PDFs (exclude the new file if it's already in the folder)
    candidates = [p for p in logs_temp_dir.glob("*.pdf")]
    candidates = [p for p in sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)
                  if p.resolve() != new_pdf]

    prev_path = candidates[0] if candidates else None

    prev_hash = None
    different = True
    reason = "no previous file to compare" if prev_path is None else "hash mismatch"

    if prev_path is not None:
        prev_hash = _sha256_of_file(prev_path)
        different = prev_hash != new_hash
        reason = "files are different" if different else "files are identical"

    archived_path = None
    # Archive new file for future comparisons (timestamped). Don't overwrite existing files.
    if archive_new:
        # use timezone-aware UTC timestamp for portability
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds").replace(":", "-")
        target_name = f"{ts}__{new_pdf.name}"
        target = logs_temp_dir / target_name
        # If new_pdf is already inside logs_temp_dir under the same name, we still copy to timestamped name
        try:
            shutil.copy2(str(new_pdf), str(target))
            archived_path = str(target)
        except Exception:
            # archival failed but comparison result is still valid
            archived_path = None

    result = {
        "different": bool(different),
        "new_hash": new_hash,
        "prev_hash": prev_hash,
        "prev_path": str(prev_path) if prev_path is not None else None,
        "archived_path": archived_path,
        "reason": reason,
    }

    # If identical, delete the more recent duplicate (between previous and the new/archived copy)
    deleted_path = None
    if prev_path is not None and not different:
        # Determine candidates to compare for deletion: prefer archived copy if present
        candidate_a = prev_path
        candidate_b = Path(archived_path) if archived_path is not None else new_pdf

        try:
            a_mtime = candidate_a.stat().st_mtime
        except Exception:
            a_mtime = 0
        try:
            b_mtime = candidate_b.stat().st_mtime
        except Exception:
            b_mtime = 0

        # Delete the more recent file
        if b_mtime >= a_mtime:
            try:
                candidate_b.unlink()
                deleted_path = str(candidate_b)
            except Exception:
                deleted_path = None
        else:
            try:
                candidate_a.unlink()
                deleted_path = str(candidate_a)
            except Exception:
                deleted_path = None

    # Small user-friendly printout
    if prev_path is None:
        print(f"No previous PDF found in {logs_temp_dir}. Archived new PDF: {archived_path}")
    else:
        msg = f"Compared new PDF ({new_pdf.name}) to previous ({prev_path.name}): {reason}"
        if deleted_path:
            msg += f" — deleted duplicate: {deleted_path}"
        print(msg)

    # include deleted_path in result for caller visibility
    result["deleted_path"] = deleted_path

    return result


if __name__ == "__main__":
    # quick manual test: supply a path to a PDF file
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pdf_change_detector.py /path/to/new.pdf")
    else:
        out = compare_with_previous(sys.argv[1])
        print(out)
