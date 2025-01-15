
from django.urls import path
from document.views import create_document, update_document, dev_document, search_document

urlpatterns = [
    path('create', create_document, name = "create_document"),
    path('<int:document_id>/update', update_document, name = "update_document"),
    path('search', search_document, name = "search_document"),
    path('<int:document_id>/dev', dev_document, name = "dev_document")
]