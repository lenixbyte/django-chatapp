from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.index, name='index'),
    path('signup/', views.signup, name='signup'),
    path('rooms/', views.rooms, name='rooms'),
    path('contacts/', views.contacts, name='contacts'),
    path('profile/', views.profile, name='profile'),
    path('settings/', views.settings, name='settings'),
    path('chat/<int:user_id>/', views.room, name='room'),
    path('chats/', views.get_chat_list, name='chat_list'),
    path('logout/', views.logout_handler, name='logout'),
] 