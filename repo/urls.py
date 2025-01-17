from django.urls import path
from .views import create_repo

urlpatterns = [
    path('post', create_repo, name='create_repo'),  # 레포지토리 생성 API
]