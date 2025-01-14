from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q

class ChatRoom(models.Model):
    participants = models.ManyToManyField(User, related_name='chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_message_at = models.DateTimeField(auto_now=True, db_index=True)
    last_read_at = models.DateTimeField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    def get_other_participant(self, user):
        return self.participants.exclude(id=user.id).first()
    
    @property
    def unread_messages_count(self):
        return self.messages.filter(is_read=False).count()
    
    @classmethod
    def get_or_create_room(cls, user1, user2):
        room = cls.objects.filter(
            participants=user1
        ).filter(
            participants=user2
        ).first()
        
        if not room:
            room = cls.objects.create()
            room.participants.add(user1, user2)
        
        return room
    
    class Meta:
        ordering = ['-last_message_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['last_message_at']),
            models.Index(fields=['is_active']),
        ]

class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    is_read = models.BooleanField(default=False, db_index=True)
    is_delivered = models.BooleanField(default=False, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    client_message_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])
    
    def mark_as_delivered(self):
        if not self.is_delivered:
            self.is_delivered = True
            self.save(update_fields=['is_delivered'])
    
    def soft_delete(self):
        self.is_deleted = True
        self.save(update_fields=['is_deleted'])
    
    @classmethod
    def get_unread_messages(cls, user, room=None):
        queryset = cls.objects.filter(
            is_read=False,
            is_deleted=False
        ).exclude(sender=user)
        
        if room:
            queryset = queryset.filter(room=room)
            
        return queryset
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['is_read']),
            models.Index(fields=['is_delivered']),
            models.Index(fields=['is_deleted']),
            models.Index(fields=['client_message_id']),
        ]

class UserStatus(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chat_status')
    is_online = models.BooleanField(default=False, db_index=True)
    last_seen = models.DateTimeField(default=timezone.now, db_index=True)
    
    def update_status(self, is_online):
        self.is_online = is_online
        self.last_seen = timezone.now()
        self.save(update_fields=['is_online', 'last_seen'])
    
    def get_status_display(self):
        if self.is_online:
            return 'online'
        return self.last_seen
    
    class Meta:
        indexes = [
            models.Index(fields=['is_online']),
            models.Index(fields=['last_seen']),
        ] 