from django.urls import path
from .views import create_directories

urlpatterns = [
    path('', create_directories, name='create_directories'),
]