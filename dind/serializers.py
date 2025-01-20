from rest_framework import serializers


class CreateDindSerializer(serializers.Serializer):
    github_name = serializers.CharField(required=True, max_length=255, help_text="닉네임")
    github_url = serializers.CharField(required=True, max_length=255,help_text="깃허브 레포지토리 링크")
    repo_name =  serializers.CharField(required=True, max_length=255,help_text="레포지토리 이름")
