from django.urls import path
from . import views, api

urlpatterns = [
    path("", views.index, name="practice_index"),  # вибір спец.
    path("start/<str:spec>/", views.start_session, name="practice_start"),
    path("editor/<uuid:session_uuid>/", views.editor, name="practice_editor"),
    path("finish/<uuid:session_uuid>/", views.finish, name="practice_finish"),
    path("result/<uuid:session_uuid>/", views.result, name="practice_result"),
    # API
    path("api/autosave/<uuid:session_uuid>/", api.autosave, name="practice_autosave"),
    path(
        "api/evaluate/<uuid:session_uuid>/", api.evaluate_now, name="practice_evaluate"
    ),
]
