from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
import re

register = template.Library()

# Optional leading label like "Умова:" or "Завдання:" at the very start
PREFIX_RE = re.compile(r"^\s*((?:Умова|Завдання)\s*:?)\s*", flags=re.IGNORECASE)


@register.filter(needs_autoescape=True)
def format_question(value, autoescape=True):
    """
    Format question text for display:
    - Preserve paragraphs and single line breaks (\n and \n\n)
    - Optionally highlight a leading label like "Умова:" with .q-label
    The result is safe HTML consisting of <p> blocks with <br> inside.
    """
    text = "" if value is None else str(value)
    # Normalize newlines first
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    esc = conditional_escape if autoescape else (lambda x: x)
    s = esc(text)

    # Highlight an optional prefix label once at the very beginning
    def repl(m):
        label = m.group(1)
        return f'<strong class="q-label">{label}</strong> '

    s = PREFIX_RE.sub(repl, s, count=1)

    # Split into paragraphs on two or more newlines, convert single newlines to <br>
    parts = [p.strip() for p in re.split(r"\n{2,}", s) if p.strip()]
    html_parts = []
    for p in parts:
        p_html = p.replace("\n", "<br>")
        html_parts.append(f"<p>{p_html}</p>")

    html = "".join(html_parts) if html_parts else f"<p>{s}</p>"
    return mark_safe(html)

