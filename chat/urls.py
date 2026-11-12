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
    
    # Document Creation Agent Endpoints
    path('api/templates/', views.list_document_types_api, name='list_document_types_api'),
    path('api/agent/detect-type/', views.detect_document_type_api, name='detect_document_type_api'),
    path('api/agent/start/', views.start_document_session_api, name='start_document_session_api'),
    path('api/agent/generate/', views.generate_document_api, name='generate_document_api'),
    path('api/agent/revise/<uuid:document_id>/', views.revise_document_api, name='revise_document_api'),
    path('api/documents/<uuid:document_id>/update-text/', views.update_document_text_api, name='update_document_text_api'),
    path('api/documents/', views.list_user_documents_api, name='list_user_documents_api'),
    path('api/documents/<uuid:document_id>/lock/', views.toggle_document_lock_api, name='toggle_document_lock_api'),
    path('api/documents/<uuid:document_id>/verify-pin/', views.verify_document_pin_api, name='verify_document_pin_api'),
    path('api/documents/<uuid:document_id>/toggle-final/', views.toggle_document_final_api, name='toggle_document_final_api'),
    path('api/documents/<uuid:document_id>/detail/', views.get_document_detail_api, name='get_document_detail_api'),
    path('api/documents/<uuid:document_id>/download/', views.download_document_api, name='download_document_api'),
    path('api/documents/<uuid:document_id>/pdf/', views.download_pdf_api, name='download_pdf_api'),
    
    # Signatures & Profile APIs
    path('api/signatures/', views.list_signatures_api, name='list_signatures_api'),
    path('api/signatures/upload/', views.upload_signature_api, name='upload_signature_api'),
    path('api/signatures/<uuid:signature_id>/delete/', views.delete_signature_api, name='delete_signature_api'),
    path('api/signatures/<uuid:signature_id>/set-default/', views.set_default_signature_api, name='set_default_signature_api'),
    path('api/profile/update/', views.update_profile_api, name='update_profile_api'),

    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
]
