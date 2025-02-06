from django.urls import path
from . import views

urlpatterns = [
    # We'll add view URLs later
    path(
        "chat/<str:room_name>/history",
        views.delete_chat_history,
        name="delete_chat_history",
    ),
]
