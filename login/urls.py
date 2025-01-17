from django.urls import path
from . import views

urlpatterns = [
    path('', views.LoginGithubView.as_view(), name='login_auth_github'), # 깃허브 연동
    # GitHub OAuth 콜백 URL 추가
    path('github/callback/',views.LoginGithubCallbackView.as_view(),name='login_github_callback'),
    path('code/view/',views.CodeView.as_view(),name='code_view'),
    path('profile/',views.MyPageView.as_view(),name='mypage_view'),
]