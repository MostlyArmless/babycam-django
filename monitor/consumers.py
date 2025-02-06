import logging
from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.layers import get_channel_layer
from typing import Any, Dict, List
from asgiref.sync import sync_to_async

from monitor.models import ChatMessage, ChatRoom

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class MonitorConsumer(AsyncWebsocketConsumer):
    """MonitorConsumer is used to send WS messages containing the most recent audio level measured by a given monitor device."""

    async def connect(self):
        self.device_id = self.scope["url_route"]["kwargs"]["device_id"]

        self.channel_layer = get_channel_layer()
        if self.channel_layer is None:
            logger.error("Failed to get channel layer")
            await self.close()
            return

        self.room_group_name = f"monitor_{self.device_id}"
        logger.debug(f"New connection attempt for device {self.device_id}")

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        logger.debug(f"Added {self.channel_name} to group {self.room_group_name}")
        await self.accept()
        logger.info(f"WebSocket connected for device {self.device_id}")

    async def disconnect(self, code):
        logger.debug(f"Disconnecting from group: {self.room_group_name}")
        if self.channel_layer is not None:
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )
        else:
            logger.error("Channel layer is None, cannot discard group")

    async def monitor_message(self, event):
        logger.debug(f"Consumer received event to broadcast: {event}")
        try:
            await self.send(text_data=json.dumps({"message": event["message"]}))
            logger.debug("Successfully sent message to client")
        except Exception as e:
            logger.error(f"Error sending message: {e}", exc_info=True)


class ChatConsumer(AsyncWebsocketConsumer):
    """ChatConsumer is used to send and receive chat messages from each of the parent clients."""

    async def connect(self):
        """On connect, the server should send all chat history to the client"""

        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.channel_layer = get_channel_layer()
        if self.channel_layer is None:
            logger.error("Failed to get channel layer")
            await self.close()
            return

        # There's only one group for now.
        # We may later decide to split based on child (monitor).
        self.room_group_name = f"chat_{self.room_name}"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        history = await fetch_history(self.room_name)
        await self.send(
            text_data=json.dumps({"type": "chat_history", "messages": history})
        )

    async def disconnect(self, code):
        # Leave room group
        if self.channel_layer is not None:
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )
        else:
            logger.error("Channel layer is None, cannot discard group")

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            logger.error("Received empty chat message")
            return

        logger.debug(f"Chat message received: {text_data}")
        try:
            data = json.loads(text_data)
            message_data = {
                "user": data["user"],
                "text": data["text"],
                "timestamp": data["timestamp"],  # Already in ISO format from frontend
            }

            # Save message to database
            await save_message(self.room_name, message_data)

            # Send message to room group
            if self.channel_layer is None:
                logger.error("Channel layer is None, cannot send group message")
                return

            await self.channel_layer.group_send(
                self.room_group_name, {"type": "chat_message", "message": message_data}
            )
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"Error processing message: {e}")
            return

    async def chat_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send(
            text_data=json.dumps({"type": "chat_message", "message": message})
        )


@sync_to_async
def fetch_history(room_name: str) -> List[Dict[str, Any]]:
    room, _ = ChatRoom.objects.get_or_create(name=room_name)
    messages = ChatMessage.objects.filter(room=room).order_by("id")
    # Convert to frontend Message interface format
    history = [
        {
            "user": msg["user"],
            "text": msg["text"],
            "timestamp": msg["timestamp"].isoformat(),
        }
        for msg in messages.values("user", "text", "timestamp")
    ]
    return history


@sync_to_async
def save_message(room_name: str, message_data: Dict[str, Any]) -> None:
    room, _ = ChatRoom.objects.get_or_create(name=room_name)
    # Frontend sends ISO format timestamp, parse it for database
    ChatMessage.objects.create(
        room=room,
        user=message_data["user"],
        text=message_data["text"],
        timestamp=message_data[
            "timestamp"
        ],  # Django will parse ISO format automatically
    )
