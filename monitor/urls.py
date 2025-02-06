from django.urls import path
from . import views

urlpatterns = [
    path(
        "chat/<str:room_name>/delete",
        views.delete_chat_history,
        name="delete_chat_history",
    ),
    path("device/<str:device_id>", views.get_monitor_device, name="get_monitor_device"),
    path(
        "device/<str:device_id>/start", views.start_monitoring, name="start_monitoring"
    ),
    path("device/<str:device_id>/stop", views.stop_monitoring, name="stop_monitoring"),
]
