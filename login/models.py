# from django.db import models
# from django.utils import timezone

# class User(models.Model):
#     user_id = models.CharField(max_length=20, unique=True, verbose_name='사용자 아이디')
#     name = models.CharField(max_length=20, verbose_name='이름')
#     email = models.EmailField(max_length=254, verbose_name='이메일')
#     last_login = models.DateTimeField(null=True, blank=True, verbose_name='마지막 로그인 시간')
#     created_at = models.DateTimeField(default=timezone.now, verbose_name='생성 시간')
#     deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='삭제 시간')

#     class Meta:
#         db_table="user"

#     def __str__(self):
#         return self.user_id
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser  # AbstractUser를 상속받음

class User(AbstractUser):
    """
    사용자 모델
    - Django의 기본 User 모델을 확장하여 사용합니다.
    - `allauth`와 호환되도록 `AbstractUser`를 상속받습니다.
    """
    # 기존 필드 유지
    user_id = models.CharField(max_length=20, unique=True, verbose_name='사용자 아이디')
    name = models.CharField(max_length=20, verbose_name='이름')
    email = models.EmailField(max_length=254, verbose_name='이메일')
    last_login = models.DateTimeField(null=True, blank=True, verbose_name='마지막 로그인 시간')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='생성 시간')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='삭제 시간')

    class Meta:
        db_table = "user"  # 데이터베이스 테이블 이름
        verbose_name = "사용자"  # 관리자 페이지에서 표시될 이름
        verbose_name_plural = "사용자"  # 복수형 이름

    def __str__(self):
        return self.user_id  # 사용자 아이디를 문자열로 반환