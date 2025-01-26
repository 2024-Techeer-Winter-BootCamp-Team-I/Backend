from rest_framework import serializers

class LoginResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    access = serializers.CharField()
    refresh = serializers.CharField()
    
class UserProfileSerializer(serializers.Serializer):
    github_username = serializers.CharField()
    email = serializers.EmailField()
    document_titles = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()),
        allow_empty=True
    )