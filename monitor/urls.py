from django.urls import path
from . import views

urlpatterns = [
    path(
        "monitor/<int:device_id>/", views.get_monitor_device, name="get_monitor_device"
    ),
    # We'll add view URLs later
    path(
        "chat/<str:room_name>/history",
        views.delete_chat_history,
        name="delete_chat_history",
    ),
]
