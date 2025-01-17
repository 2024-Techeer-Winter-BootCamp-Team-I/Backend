# from django.urls import path
# from .views import BackendSetupView

# urlpatterns = [
#     path('setup/', BackendSetupView.as_view(), name='backend-setup'),
# ]

from django.urls import path
from .views import BackendSetupView, BackendView

urlpatterns = [
    path('setup', BackendSetupView.as_view(), name='backend-setup'),
    path('search', BackendView.as_view(), name='backend-view'),  # /backend/ 경로 추가
]