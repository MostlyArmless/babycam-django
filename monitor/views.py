from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django.urls import reverse
from .models import ChatRoom, ChatMessage, MonitorDevice, AudioEvent
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import requests
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import MonitorDeviceSerializer, AudioEventSerializer
import logging
import re
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

# Create your views here.


@csrf_exempt  # TODO remove this when you implement auth with JWT, we only did this temporarily to allow the vite frontend to talk to the django backend in dev
@require_http_methods(["DELETE"])
def delete_chat_history(request, room_name):
    try:
        room = ChatRoom.objects.get(name=room_name)
        ChatMessage.objects.filter(room=room).delete()
        return JsonResponse({"status": "success", "message": "Chat history deleted"})
    except ChatRoom.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Chat room not found"}, status=404
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


class MonitorDeviceViewSet(viewsets.ModelViewSet):
    queryset = MonitorDevice.objects.all()
    serializer_class = MonitorDeviceSerializer


class AudioEventViewSet(viewsets.ModelViewSet):
    queryset = AudioEvent.objects.all()
    serializer_class = AudioEventSerializer
