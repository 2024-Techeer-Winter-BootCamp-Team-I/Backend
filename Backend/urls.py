from django.urls import path
from .views import BackendSetupView

urlpatterns = [
    path('setup/', BackendSetupView.as_view(), name='backend-setup'),
]