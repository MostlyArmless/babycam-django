import logging
from channels.generic.websocket import AsyncWebsocketConsumer
import json

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class MonitorConsumer(AsyncWebsocketConsumer):
    """MonitorConsumer is used to send WS messages containing the most recent audio level measured by a given monitor device."""
    async def connect(self):
        self.device_id = self.scope['url_route']['kwargs']['device_id']
        
        self.channel_layer = get_channel_layer()
        if self.channel_layer is None:
            logger.error("Failed to get channel layer")
            await self.close()
            return
        
        self.room_group_name = f'monitor_{self.device_id}'
        logger.debug(f"New connection attempt for device {self.device_id}")

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        logger.debug(f"Added {self.channel_name} to group {self.room_group_name}")
        await self.accept()
        logger.info(f"WebSocket connected for device {self.device_id}")


    async def disconnect(self, code):
        logger.debug(f"Disconnecting from group: {self.room_group_name}")
        if self.channel_layer is not None:
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        else:
            logger.error("Channel layer is None, cannot discard group")

    async def monitor_message(self, event):
        logger.debug(f"Consumer received event to broadcast: {event}")
        try:
            await self.send(text_data=json.dumps({
                'message': event['message']
            }))
            logger.debug("Successfully sent message to client")
        except Exception as e:
            logger.error(f"Error sending message: {e}", exc_info=True)