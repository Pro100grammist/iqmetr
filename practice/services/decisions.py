import re
from pathlib import Path
from datetime import datetime, timezone as dtz


def _now_iso():
    return datetime.now(dtz.utc).isoformat()


def _normalize_text(s: str) -> str:
    s = re.sub(r"\r\n?", "\n", s)
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def load_txt(path_str: str, base_dir: Path) -> str:
    p = Path(path_str)
    if not p.is_absolute():
        p = (base_dir / p).resolve()
    text = p.read_text(encoding="utf-8")
    return _normalize_text(text)
