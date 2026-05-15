from django.urls import path
from .views import MeView

urlpatterns = [
    path('auth/users/me/', MeView.as_view(), name='user-me'),
]
