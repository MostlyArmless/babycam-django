from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/monitor/(?P<device_id>\w+)/$', consumers.MonitorConsumer.as_asgi()),
]