import hashlib
import os

BOT_RE = (
    "bot",
    "spider",
    "crawler",
    "preview",
    "feedfetcher",
    "facebookexternalhit",
    "whatsapp",
)


def client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def ip_hash(request):
    ip = client_ip(request) or ""
    salt = os.getenv("ANALYTICS_SALT", "iqmetr-salt-dev")  # додай у Render ENV у проді
    return hashlib.sha256(f"{salt}:{ip}".encode("utf-8")).hexdigest()


def is_bot(ua: str) -> bool:
    if not ua:
        return False
    ual = ua.lower()
    return any(k in ual for k in BOT_RE)
