from django.urls import path
from . import views

urlpatterns = [
    path('generate-image/', views.generate_image, name='generate_image'),
    path('send-mms/', views.send_mms, name='send_mms'),
]