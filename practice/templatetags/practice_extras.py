import re
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def format_outline(text: str):
    """Екранує текст, робить жирними заголовки '1.x ...:' та '2.x ...:' і розбиває рядки на <br>."""
    s = escape(text or "")
    s = re.sub(r"(?m)^(1\.[1-6][^:\n]*:)", r"<strong>\1</strong>", s)
    s = re.sub(r"(?m)^(2\.[1-4][^:\n]*:)", r"<strong>\1</strong>", s)
    # Center all-caps lines (Cyrillic/Latin, incl. ІЇЄҐ)
    center_line = re.compile(r"(?m)^(?=.{3,}$)(?!.*[a-zа-яіїєґ])(?=.*[A-ZА-ЯІЇЄҐ]).+$")
    s = center_line.sub(lambda m: f'<div style="text-align:center">{m.group(0)}</div>', s)
    s = s.replace("\n", "<br>")
    # Post-process: center ALL-CAPS lines robustly even if regex above fails
    _parts = []
    for _ln in s.split("<br>"):
        # Skip if already wrapped as centered
        if _ln.startswith('<div style="text-align:center">'):
            _parts.append(_ln)
            continue
        has_letter = any(ch.isalpha() for ch in _ln)
        no_lower = not any(ch.islower() for ch in _ln)
        if has_letter and no_lower and len(_ln.strip()) >= 3:
            _parts.append(f'<div style="text-align:center">{_ln}</div>')
        else:
            _parts.append(_ln)
    s = "<br>".join(_parts)
    return mark_safe(s)


@register.filter
def format_duration(seconds):
    """Return H:MM:SS or M:SS to avoid '0 minutes'."""
    try:
        sec = int(seconds or 0)
    except Exception:
        return ""
    if sec < 0:
        sec = 0
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
