from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.db.models import Q
from .models import ChatRoom, Message, UserStatus
from .forms import SignUpForm
from django.contrib.auth import logout

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('chat:index')
    else:
        form = SignUpForm()
    return render(request, 'chat/signup.html', {'form': form})

def logout_handler(request):
    logout(request)
    return redirect('login')

@login_required
def index(request):
    # Get all users except the current user
    # users = User.objects.exclude(id=request.user.id)
    # users_with_messages = []
    
    # for user in users:
    #     # Get the chat room between current user and this user if it exists
    #     chat_room = ChatRoom.objects.filter(participants=request.user).filter(participants=user).first()
    #     last_message = None
    #     if chat_room:
    #         last_message = chat_room.messages.last()
        
    #     users_with_messages.append({
    #         'user': user,
    #         'last_message': last_message
    #     })
    
    # return render(request, 'chat/index.html', {'users': users_with_messages})
    if not request.user.is_authenticated:
        return redirect('chat:login')
    
    # Get all users except the current user
    users = User.objects.exclude(id=request.user.id)
    
    context = {
        'users': users,
    }
    return render(request, 'chat/rooms.html', context)

@login_required
def room(request, user_id):
    other_user = User.objects.get(id=user_id)
    
    # Get or create chat room for these users
    chat_room = ChatRoom.objects.filter(participants=request.user).filter(participants=other_user).first()
    
    if not chat_room:
        chat_room = ChatRoom.objects.create()
        chat_room.participants.add(request.user, other_user)
    
    # Get all chat rooms for sidebar with other participant info
    chat_rooms = []
    for room in ChatRoom.objects.filter(participants=request.user).prefetch_related('participants'):
        other_participant = room.get_other_participant(request.user)
        if other_participant:  # Make sure we have a valid other participant
            chat_rooms.append({
                'room': room,
                'other_user': other_participant,
                'last_message': room.messages.last(),
                'unread_count': room.messages.filter(is_read=False).exclude(sender=request.user).count()
            })
    
    # Get user status
    user_status = UserStatus.objects.get_or_create(user=other_user)[0]
    
    messages = chat_room.messages.all().values(
        'id',
        'content',
        'sender__username',
        'timestamp',
        'is_read',
        'is_delivered'
    )
    
    formatted_messages = [{
        'id': msg['id'],
        'message': msg['content'],
        'sender': msg['sender__username'],
        'timestamp': msg['timestamp'].isoformat(),
        'is_read': msg['is_read'],
        'is_delivered': msg['is_delivered']
    } for msg in messages]
    
    return render(request, 'chat/room.html', {
        'room': chat_room,
        'other_user': other_user,
        'online': user_status.is_online,
        'last_seen': user_status.last_seen.isoformat(),
        'messages': formatted_messages,
        'chat_rooms': chat_rooms,
        'current_room_id': chat_room.id
    })

@login_required
def get_chat_list(request):
    chat_rooms = ChatRoom.objects.filter(participants=request.user)
    chats = []
    
    for room in chat_rooms:
        other_user = room.get_other_participant(request.user)
        last_message = room.messages.last()
        unread_count = room.messages.filter(is_read=False).exclude(sender=request.user).count()
        
        chats.append({
            'room': room,
            'other_user': other_user,
            'last_message': last_message,
            'unread_count': unread_count
        })
    
    return render(request, 'chat/chat_list.html', {'chats': chats})

@login_required
def rooms(request):
    if not request.user.is_authenticated:
        return redirect('chat:login')
    
    # Get all users except the current user
    users = User.objects.exclude(id=request.user.id)
    
    context = {
        'users': users,
    }
    return render(request, 'chat/rooms.html', context)

@login_required
def contacts(request):
    contacts = User.objects.exclude(id=request.user.id)
    return render(request, 'chat/contacts.html', {'contacts': contacts})

@login_required
def profile(request):
    return render(request, 'chat/profile.html', {
        'user': request.user
    })

@login_required
def settings(request):
    return render(request, 'chat/settings.html', {
        'user': request.user
    }) 