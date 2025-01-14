from django.urls import path
from . import views

urlpatterns = [
    path('', views.login, name='login'),  # 로그인 뷰 (Django 기본 뷰)
    path('home/', views.home, name='home'),  # 홈 뷰 (Django 기본 뷰)
    path('saveInfo/', views.SaveInfo.as_view(), name='saveInfo'),  # SaveInfo 뷰 (DRF 뷰)
    path('login/', views.LoginGithubView.as_view(), name='login_auth_github'), # 깃허브 연동
    # GitHub OAuth 콜백 URL 추가
    path('github/callback/',views.LoginGithubCallbackView.as_view(),name='login_github_callback'),
]