from rest_framework import serializers

from document.models import Document
class CreateDocumentSerializer(serializers.Serializer):
    title = serializers.CharField(required=True, max_length=255, help_text="문서 제목")
    content = serializers.CharField(required=True, help_text="문서 내용")
    requirements = serializers.CharField(required=False, default="No requirements provided", help_text="기능 명세")


class UpdateDocumentSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, max_length=255, help_text="문서 제목")
    content = serializers.CharField(required=False, help_text="문서 내용")
    discription = serializers.CharField(required=False, help_text="기능 명세")

