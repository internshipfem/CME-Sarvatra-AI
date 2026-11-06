from django.contrib import admin
from .models import UserProfile, Conversation, UploadedFile, Message, GeneratedDocument


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'department', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'employee_id', 'department')


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'model_name', 'created_at', 'updated_at')
    search_fields = ('title', 'user__username')
    list_filter = ('model_name', 'created_at')


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'user', 'file_size', 'uploaded_at')
    search_fields = ('original_name', 'user__username')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('role', 'conversation', 'created_at', 'response_time')
    search_fields = ('content', 'conversation__title')
    list_filter = ('role', 'created_at')


@admin.register(GeneratedDocument)
class GeneratedDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'document_type', 'user', 'version', 'model_used', 'generation_time', 'created_at')
    search_fields = ('title', 'document_type', 'user__username')
    list_filter = ('document_type', 'created_at')
