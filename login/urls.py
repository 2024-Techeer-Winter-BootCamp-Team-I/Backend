from django.urls import path
from .views import login, home

urlpatterns = [
    path('github/', login, name='login'), # 깃허브 로그인
    path('home/', home, name='home'),
]