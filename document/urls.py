
from django.urls import path
from document.views import create_document

urlpatterns = [
    path('/create', create_document, name = "create_document")
]