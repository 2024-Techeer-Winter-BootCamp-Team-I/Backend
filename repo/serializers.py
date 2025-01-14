from rest_framework import serializers

class CreateRepoSerializer(serializers.Serializer):
    organization_name = serializers.CharField(required=False, allow_blank=True, help_text="조직 이름 (선택사항)")
    repo_name = serializers.CharField(required=True, help_text="생성할 레포지토리 이름")
    private = serializers.BooleanField(required=False, default=False, help_text="비공개 레포지토리 여부 (선택사항, 기본값: false)")