from . import models
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
import logging
from typing import List, Optional
from datetime import datetime
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

class ChatHandler:
    def __init__(self, user, channel_layer = None, room_group_name = None):
        self.user = user
        self.channel_layer = channel_layer
        self.room_group_name = room_group_name

    @database_sync_to_async
    def get_chat_rooms(self) -> List[models.ChatRoom]:
        """Get all chat rooms for the current user"""
        try:
            return list(models.ChatRoom.objects.filter(participants=self.user).prefetch_related('participants'))
        except Exception as e:
            logger.error(f"Error fetching chat rooms for user {self.user.id}: {str(e)}")
            return []

    @database_sync_to_async
    def get_messages(self, room: str, limit: int = 50) -> tuple[List[models.Message], Optional[datetime]]:
        """Get messages for a specific room with pagination and last read timestamp"""
        try:
            messages = list(models.Message.objects.filter(room=room)
                       .select_related('sender')
                       .order_by('-timestamp')[:limit])
            
            # Get the timestamp of the first unread message
            first_unread = models.Message.objects.filter(
                room=room,
                sender__id=self.user.id,
                is_read=False
            ).order_by('timestamp').first()
            
            unread_timestamp = first_unread.timestamp if first_unread else None
            return messages, unread_timestamp
        except Exception as e:
            logger.error(f"Error fetching messages for room {room}: {str(e)}")
            return [], None

    @database_sync_to_async
    def send_message(self, room_id: str, content: str) -> Optional[models.Message]:
        """Send a message to a specific room"""
        try:
            # Convert room_id to int
            room_id = int(room_id)
            room = models.ChatRoom.objects.get(id=room_id)
            
            message = models.Message.objects.create(
                room=room,
                sender=self.user,
                content=content
            )
            return message
        except (ValueError, models.ChatRoom.DoesNotExist):
            logger.error(f"Invalid room ID or room not found: {room_id}")
            return None
        except Exception as e:
            logger.error(f"Error sending message to room {room_id}: {str(e)}")
            return None

    @database_sync_to_async
    def get_or_create_chat_room(self, other_user) -> tuple[models.ChatRoom, bool]:
        """Get existing chat room or create new one"""
        try:
            room = models.ChatRoom.objects.filter(
                participants=self.user
            ).filter(
                participants=other_user
            ).first()
            
            if room:
                return room, False
                
            with transaction.atomic():
                room = models.ChatRoom.objects.create()
                room.participants.add(self.user, other_user)
                return room, True
        except Exception as e:
            logger.error(f"Error creating chat room with user {other_user.id}: {str(e)}")
            raise

    @database_sync_to_async
    def get_chat_room_by_id(self, room_id: int) -> Optional[models.ChatRoom]:
        """Get chat room by ID with error handling"""
        try:
            return models.ChatRoom.objects.get(id=room_id)
        except ObjectDoesNotExist:
            logger.warning(f"Chat room {room_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error fetching chat room {room_id}: {str(e)}")
            return None

    @database_sync_to_async
    def mark_messages_as_read(self, room: str) -> None:
        """Mark all messages in a room as read and update last read timestamp"""
        try:
            with transaction.atomic():
                # Get the latest message timestamp before marking as read
                latest_message = models.Message.objects.filter(
                    room=room,
                    is_read=False
                ).exclude(
                    sender=self.user
                ).order_by('-timestamp').first()

                if latest_message:
                    # Update all unread messages
                    models.Message.objects.filter(
                        room=room,
                        timestamp__lte=latest_message.timestamp,
                        is_read=False
                    ).exclude(
                        sender=self.user
                    ).update(
                        is_read=True,
                        is_delivered=True
                    )

                    # Update the last read timestamp for the room
                    models.ChatRoom.objects.filter(id=room).update(
                        last_read_at=latest_message.timestamp
                    )
        except Exception as e:
            logger.error(f"Error marking messages as read in room {room}: {str(e)}")

    @database_sync_to_async
    def mark_message_as_delivered(self, message_id: int) -> None:
        """Mark a specific message as delivered"""
        try:
            models.Message.objects.filter(
                id=message_id,
                is_delivered=False
            ).update(is_delivered=True)
        except Exception as e:
            logger.error(f"Error marking message {message_id} as delivered: {str(e)}")

    @database_sync_to_async
    def update_user_status(self, is_online: bool) -> None:
        """Update user's online status"""
        try:
            status, _ = models.UserStatus.objects.get_or_create(user=self.user)
            status.update_status(is_online)
            # Broadcast the status update with last_seen
            self.broadcast_status_update(is_online, status.last_seen)
        except Exception as e:
            logger.error(f"Error updating user status for user {self.user.id}: {str(e)}")

    @database_sync_to_async
    def get_user_status(self, user_id: int) -> bool:
        """Get user's online status"""
        try:
            status = models.UserStatus.objects.filter(user_id=user_id).first()
            return status.is_online if status else False
        except Exception as e:
            logger.error(f"Error getting user status for user {user_id}: {str(e)}")
            return False
        
    def broadcast_status_update(self, is_online: bool, last_seen: datetime) -> None:
        """Broadcast user status update to the room group"""
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'user_status',
                'user': self.user.username,
                'status': 'online' if is_online else 'offline',
                'last_seen': last_seen.isoformat()
            }
        )

    @database_sync_to_async
    def get_last_read_timestamp(self, room_id: int) -> Optional[datetime]:
        """Get the timestamp of the last read message in a room"""
        try:
            return models.Message.objects.filter(
                room_id=room_id,
                sender__id=self.user.id,
                is_read=True
            ).order_by('-timestamp').first().timestamp
        except Exception as e:
            logger.error(f"Error getting last read timestamp for room {room_id}: {str(e)}")
            return None

    @database_sync_to_async
    def get_unread_count(self, room_id: int) -> int:
        """Get count of unread messages in a room"""
        try:
            return models.Message.objects.filter(
                room_id=room_id,
                is_read=False
            ).exclude(
                sender=self.user
            ).count()
        except Exception as e:
            logger.error(f"Error getting unread count for room {room_id}: {str(e)}")
            return 0
