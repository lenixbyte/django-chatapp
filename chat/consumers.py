import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .ChatHandler import ChatHandler
from datetime import datetime

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Handle new WebSocket connection"""
        try:
            self.room_name = self.scope['url_route']['kwargs']['room_name']
            self.room_group_name = f'chat_{self.room_name}'
            self.user = self.scope['user']
            self.chat_handler = ChatHandler(self.user, self.channel_layer, self.room_group_name)

            # Update user status to online
            await self.chat_handler.update_user_status(True)

            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name,
            )
            await self.accept()
            
            # Send connection status
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status',
                    'status': 'online',
                    'user': self.user.username
                }
            )
        except Exception as e:
            logger.error(f"Error in connect: {str(e)}")
            await self.close()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        try:
            # Update user status to offline
            await self.chat_handler.update_user_status(False)
            
            # Send offline status
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status',
                    'status': 'offline',
                    'user': self.user.username
                }
            )
            
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        except Exception as e:
            logger.error(f"Error in disconnect: {str(e)}")

    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'message')

            if message_type == 'message':
                message = data['message']
                # Persist message
                saved_message = await self.chat_handler.send_message(self.room_name, message)
                
                if saved_message:
                    # Send message to room group
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'chat_message',
                            'message': message,
                            'sender': self.user.username,
                            'timestamp': datetime.now().isoformat(),
                            'message_id': saved_message.id
                        }
                    )
            elif message_type == 'typing':
                # Handle typing indicator
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'typing_status',
                        'user': self.user.username,
                        'is_typing': data['is_typing']
                    }
                )
            elif message_type == 'delivery_receipt':
                # Handle delivery receipt
                message_id = data.get('message_id')
                if message_id:
                    await self.chat_handler.mark_message_as_delivered(message_id)
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'delivery_status',
                            'message_id': message_id,
                            'status': 'delivered'
                        }
                    )
                
            elif message_type == 'read_receipt':
                # Handle read receipt for all messages
                await self.chat_handler.mark_messages_as_read(self.room_name)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'read_status',
                        'room': self.room_name,
                        'user': self.user.username
                    }
                )
        except Exception as e:
            logger.error(f"Error in receive: {str(e)}")
            await self.send_error("Failed to process message")

    async def chat_message(self, event):
        """Send chat message to WebSocket"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'message',
                'message': event['message'],
                'sender': event['sender'],
                'timestamp': event['timestamp'],
                'message_id': event['message_id']
            }))
        except Exception as e:
            logger.error(f"Error in chat_message: {str(e)}")

    async def typing_status(self, event):
        """Send typing status to WebSocket"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user': event['user'],
                'is_typing': event['is_typing']
            }))
        except Exception as e:
            logger.error(f"Error in typing_status: {str(e)}")

    async def user_status(self, event):
        """Send user online/offline status to WebSocket"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'status',
                'user': event['user'],
                'status': event['status']
            }))
        except Exception as e:
            logger.error(f"Error in user_status: {str(e)}")

    async def send_error(self, message):
        """Send error message to WebSocket"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': message
            }))
        except Exception as e:
            logger.error(f"Error in send_error: {str(e)}")

    async def delivery_status(self, event):
        """Send delivery status to WebSocket"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'delivery_status',
                'message_id': event['message_id'],
                'status': event['status']
            }))
        except Exception as e:
            logger.error(f"Error in delivery_status: {str(e)}")

    async def read_status(self, event):
        """Send read status to WebSocket"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'read_status',
                'room': event['room'],
                'user': event['user']
            }))
        except Exception as e:
            logger.error(f"Error in read_status: {str(e)}")
