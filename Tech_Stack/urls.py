# from django.urls import path
# from .views import TechStackSetupView

# urlpatterns = [
#     path('setup', TechStackSetupView.as_view(), name='tech-stack-setup'),
# ]
from django.urls import path
from .views import TechStackSetupView

urlpatterns = [
    path('setup', TechStackSetupView.as_view({'post': 'setup_project'}), name='tech-stack-setup'),
]