
from django.urls import path
from document.views import create_document, update_document, dev_document

urlpatterns = [
    path('', create_document, name = "create_document"),
    path('<int:document_id>', update_document, name = "update_document"),
    path('<int:document_id>/create', dev_document, name = "dev_document")
]