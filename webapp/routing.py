from django.urls import path

from .consumers import TyresConsumer

websocket_urlpatterns = [
    path('tyres/', TyresConsumer.as_asgi())
]
