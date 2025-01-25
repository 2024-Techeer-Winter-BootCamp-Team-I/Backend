from django.urls import path
from . import views

urlpatterns = [
    path('', views.LoginGithubView.as_view(), name='login_auth_github'), # 깃허브 연동
    path('github/callback',views.LoginGithubCallbackView.as_view(),name='login_github_callback'),
    path('code/view',views.CodeView.as_view(),name='code_view'),
    path('profile',views.MyPageView.as_view(),name='mypage_view'),
    path('profile/<int:document_id>',views.DocumentIDView.as_view(),name='document_id_view'),
    path('details',views.UserDetailsView.as_view(),name='user_datails_view'),
    path('refresh',views.RefreshTokenView.as_view(),name='refresh_token_view'),
]