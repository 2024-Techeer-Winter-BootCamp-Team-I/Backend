# from django.urls import path
# from .views import FrontendSetupView

# urlpatterns = [
#     path('setup/', FrontendSetupView.as_view(), name='frontend-setup'),
# ]

from django.urls import path
from .views import FrontendSetupView, FrontendView 

urlpatterns = [
    path('setup', FrontendSetupView.as_view(), name='frontend-setup'),
    path('search', FrontendView.as_view(), name='frontend-view'),  # /frontend/ 경로 추가
]