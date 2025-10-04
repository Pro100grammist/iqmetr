from django.contrib import admin
from django.urls import path, include
from iq import views as iq_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", iq_views.start, name="start"),
    path("rules/", iq_views.rules, name="rules"),
    path("test/<uuid:session_uuid>/", iq_views.test_view, name="test"),
    path("finish/<uuid:session_uuid>/", iq_views.finish, name="finish"),
    path("result/<uuid:session_uuid>/", iq_views.result, name="result"),
    path("autosave/<uuid:session_uuid>/", iq_views.autosave, name="autosave"),
    path("metrics/", include("metrics.urls")),  # endpoint: /m/collect
    path("practice/", include("practice.urls")),
]
