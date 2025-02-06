from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import MonitorDeviceViewSet, AudioEventViewSet

router = DefaultRouter()
router.register(r"monitor", MonitorDeviceViewSet)
router.register(r"audio-events", AudioEventViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "chat/<str:room_name>/history",
        views.delete_chat_history,
        name="delete_chat_history",
    ),
]
