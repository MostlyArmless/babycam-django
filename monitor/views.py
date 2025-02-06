from django.shortcuts import render
from django.http import JsonResponse
from .models import ChatRoom, ChatMessage
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json

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
