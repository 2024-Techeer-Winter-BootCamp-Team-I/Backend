
from django.urls import path
from document.views import documents, update_document, dev_document

urlpatterns = [
    path('', documents, name="documents"),
    path('<int:document_id>', update_document, name = "update_document"),
    path('<int:document_id>/design', dev_document, name = "dev_document")
]