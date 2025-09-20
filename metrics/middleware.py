import uuid
from django.utils import timezone
from .models import Visitor, PageView
from .utils import ip_hash, is_bot

VISITOR_COOKIE = "v_id"
COOKIE_MAX_AGE = 60 * 60 * 24 * 180  # 180 днів


class VisitorMiddleware:
    """Виставляє first-party cookie, логгує pageview (GET)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # пропускаємо технічні шляхи
        path = request.path or ""
        if path.startswith("/static/"):
            return self.get_response(request)

        # підхоплюємо або створюємо visitor_id
        v_id = request.COOKIES.get(VISITOR_COOKIE)
        if not v_id:
            v_id = str(uuid.uuid4())
            request._set_new_cookie = True
        else:
            request._set_new_cookie = False

        ua = request.META.get("HTTP_USER_AGENT", "")
        visitor, _ = Visitor.objects.get_or_create(visitor_id=v_id)
        visitor.last_seen = timezone.now()
        if not visitor.initial_referrer:
            visitor.initial_referrer = request.META.get("HTTP_REFERER", "")
        visitor.user_agent = ua[:400]
        visitor.ip_hash = ip_hash(request)
        visitor.is_bot = is_bot(ua)
        visitor.save(
            update_fields=[
                "last_seen",
                "initial_referrer",
                "user_agent",
                "ip_hash",
                "is_bot",
            ]
        )

        request.visitor = visitor

        # GET page view
        if (
            request.method == "GET"
            and not visitor.is_bot
            and not path.startswith("/admin/")
        ):
            PageView.objects.create(
                visitor=visitor,
                path=path,
                referrer=request.META.get("HTTP_REFERER", ""),
                method="GET",
            )

        response = self.get_response(request)
        if request._set_new_cookie:
            response.set_cookie(
                VISITOR_COOKIE,
                v_id,
                max_age=COOKIE_MAX_AGE,
                samesite="Lax",
                secure=True,
            )
        return response
