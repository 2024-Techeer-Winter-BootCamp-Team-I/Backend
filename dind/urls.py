from django.urls import path

from .tasks import create_dind_task
from .view import create_dind_handler, create_dind_task_view  # or similar

urlpatterns = [
    path('', create_dind_handler, name='create_dind_handler'),
    path('task', create_dind_task_view, name='create_dind_task'),
]