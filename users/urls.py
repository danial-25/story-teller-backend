from django.urls import path
from . import views
urlpatterns = [
    path('history', views.user_history),
    path('favorites', views.user_favorites),
    path('character', views.user_character),
]
