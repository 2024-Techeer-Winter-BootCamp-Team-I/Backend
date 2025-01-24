from django.urls import path
from .view import create_dind_handler  # or similar

urlpatterns = [
    path('', create_dind_handler, name='create_dind_handler'),
    path('task', create_dind_handler, name='create_dind_task'),
]