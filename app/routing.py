from django.urls import re_path
from app.core.consumers import TranslationConsumer

websocket_urlpatterns = [
    re_path(r'ws/translate/$', TranslationConsumer.as_asgi()),
]