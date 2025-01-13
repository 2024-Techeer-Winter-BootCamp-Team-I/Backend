from django.urls import path
from . import views

urlpatterns = [
    path('', views.login, name='login'), # 깃허브 로그인
    path('home/', views.home, name='home'),
    path('saveInfo/',views.SaveInfo.as_view(), name='saveInfo'),
]