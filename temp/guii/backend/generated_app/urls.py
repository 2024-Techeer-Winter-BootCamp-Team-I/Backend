from django.urls import path
from . import views

urlpatterns = [
    path('generateimageview', views.GenerateImageview.as_view(), name='generateimageview'),
    path('sendsmsview', views.SendSmsview.as_view(), name='sendsmsview'),
    path('saveimageview', views.SaveImageview.as_view(), name='saveimageview'),
    path('editimageview', views.EditImageview.as_view(), name='editimageview'),
    path('smshistoryview', views.SmsHistoryview.as_view(), name='smshistoryview'),
]