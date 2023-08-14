from django.urls import path
from . import views
urlpatterns = [
    path('get_story', views.get_story, name='get_story'),
    path('id/<str:id>', views.story_by_id, name='story_by_id'),
    path('random_story', views.random_story)
]
