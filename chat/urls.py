from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_home, name='chat_home'),
    path('c/<uuid:conversation_id>/', views.chat_home, name='chat_detail'),
    path('api/conversations/create/', views.create_conversation, name='create_conversation'),
    path('api/conversations/<uuid:conversation_id>/rename/', views.rename_conversation, name='rename_conversation'),
    path('api/conversations/<uuid:conversation_id>/delete/', views.delete_conversation, name='delete_conversation'),
    path('api/conversations/<uuid:conversation_id>/send/', views.send_message_stream, name='send_message_stream'),
    path('api/models/', views.get_models_api, name='get_models_api'),
    path('api/upload/', views.upload_file_api, name='upload_file_api'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
]
