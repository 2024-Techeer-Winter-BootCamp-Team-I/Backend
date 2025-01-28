from .views import setup_project, stream_document, update_stream_document
from django.urls import path
from document.views import documents, update_document, dev_document, save_document_part

urlpatterns = [
    path('', documents, name="documents"),
    path('<int:document_id>/stream', stream_document, name = "stream_document"),
    path('<int:document_id>/update', update_stream_document, name = "update_stream_document"),
    path('<int:document_id>/design', dev_document, name = "dev_document"),
    path('<int:document_id>/save',save_document_part, name = "save_document_part"),

    #path('setup-project/<int:document_id>/', setup_project, name='setup_project'),
]