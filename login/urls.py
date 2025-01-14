from django.urls import path
from . import views

urlpatterns = [
    path('', views.login, name='login'),  # 로그인 뷰 (Django 기본 뷰)
    path('home/', views.home, name='home'),  # 홈 뷰 (Django 기본 뷰)
    path('saveInfo/', views.SaveInfo.as_view(), name='saveInfo'),  # SaveInfo 뷰 (DRF 뷰)
    path('get_access_token/', views.GetAccessToken.as_view(), name='get_access_token'),  # 액세스 토큰 조회 뷰 (DRF 뷰)
    path('reauthenticate_github/', views.reauthenticate_github, name='reauthenticate_github'),  # 재인증 뷰 (Django 기본 뷰)
    path('error/', views.error_page, name='error_page'),  # 오류 페이지 뷰 (Django 기본 뷰)
    
    # GitHub OAuth 콜백 URL 추가
    path('accounts/github/login/callback/', views.github_callback, name='github_callback'),
]