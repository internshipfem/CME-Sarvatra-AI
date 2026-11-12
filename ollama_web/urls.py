"""ollama_web URL Configuration

Air-gapped deployment configured for standalone WSGI / Waitress / Desktop execution.
"""
import os
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('chat.urls')),
]

# Ensure media files (uploaded signatures, generated documents) are ALWAYS served in air-gapped node
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    # Air-gapped production standalone fallback (Waitress without external reverse proxy)
    static_dir = settings.STATIC_ROOT if (os.path.exists(settings.STATIC_ROOT) and os.listdir(settings.STATIC_ROOT)) else (settings.BASE_DIR / 'static')
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', serve, {'document_root': static_dir}),
    ]
