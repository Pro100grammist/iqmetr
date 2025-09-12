from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
import re

register = template.Library()

PREFIX_RE = re.compile(r"^\s*(Запитання:|Питання:)\s*", flags=re.IGNORECASE)


@register.filter(needs_autoescape=True)
def format_question(value, autoescape=True):
    text = "" if value is None else str(value)
    esc = conditional_escape if autoescape else (lambda x: x)
    s = esc(text)

    def repl(m):
        label = m.group(1)
        return f'<strong class="q-label">{label}</strong>'

    formatted = PREFIX_RE.sub(repl, s, count=1)
    return mark_safe(formatted)
