from django.db import models
from django.utils import timezone

class User(models.Model):
    # GitHub OAuth2 관련 필드 추가
    github_id = models.CharField(max_length=100, null=True, blank=True, verbose_name='GitHub ID')
    github_username = models.CharField(max_length=100, null=True, blank=True, verbose_name='GitHub 사용자 이름')
    profile_image = models.URLField(max_length=500, null=True, blank=True, verbose_name='프로필 이미지 URL')
    access_token = models.CharField(max_length=500, null=True, blank=True, verbose_name='GitHub 액세스 토큰')
    last_login = models.DateTimeField(null=True, blank=True, verbose_name='마지막 로그인 시간')
    created_at = models.DateTimeField(default=timezone.now, null=True, verbose_name='생성 시간')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='삭제 시간')

    class Meta:
        verbose_name = '사용자'
        verbose_name_plural = '사용자들'
        db_table = 'user'

    def __str__(self):
        return self.github_id
