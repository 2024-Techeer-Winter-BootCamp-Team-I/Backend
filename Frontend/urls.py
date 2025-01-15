from django.urls import path
from .views import FrontendSetupView

urlpatterns = [
    path('setup/', FrontendSetupView.as_view(), name='frontend-setup'),
]