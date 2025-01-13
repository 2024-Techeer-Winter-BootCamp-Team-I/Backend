from django.db import models
from django.utils import timezone

class User(models.Model):
    user_id = models.CharField(max_length=20, unique=True, verbose_name='사용자 아이디')
    name = models.CharField(max_length=20, verbose_name='이름')
    email = models.EmailField(max_length=254, verbose_name='이메일')
    last_login = models.DateTimeField(null=True, blank=True, verbose_name='마지막 로그인 시간')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='생성 시간')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='삭제 시간')

    class Meta:
        verbose_name = '사용자'
        verbose_name_plural = '사용자들'
        db_table = 'user'  # 원하는 테이블 이름을 지정할 수 있음

    def __str__(self):
        return self.user_id