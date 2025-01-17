from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import secrets
from repo.models import Repository

def generate_temporary_password():
    # 랜덤 문자열로 임시 비밀번호 생성
    return secrets.token_urlsafe(16)

class UserManager(BaseUserManager):
    def create_user(self, github_id, github_username, email=None, profile_image=None, access_token=None, password=None, **extra_fields):
        if not github_id:
            raise ValueError('GitHub ID는 필수 항목입니다.')
        if password is None:
            password = "temporary_password"  # 고정된 정적 패스워드

        email = self.normalize_email(email)  # 이메일 정규화
        user = self.model(
            github_id=github_id,
            github_username=github_username,
            email=email,
            password=password,
            profile_image=profile_image,
            access_token=access_token,
            **extra_fields
        )
        
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    github_id = models.CharField(max_length=100, unique=True, verbose_name='GitHub ID')
    github_username = models.CharField(max_length=100, null=True, blank=True, verbose_name='GitHub 사용자 이름')
    email = models.EmailField(unique=True, blank=True, null=True)  # 널값 허용
    password = models.CharField(max_length=100, blank=True, null=True)  # 널값 허용
    profile_image = models.URLField(max_length=500, null=True, blank=True, verbose_name='프로필 이미지 URL')
    access_token = models.CharField(max_length=500, null=True, blank=True, verbose_name='GitHub 액세스 토큰')
    last_login = models.DateTimeField(null=True, blank=True, verbose_name='마지막 로그인 시간')
    created_at = models.DateTimeField(default=timezone.now, null=True, verbose_name='생성 시간')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='삭제 시간')

    is_staff = models.BooleanField(default=False, verbose_name='스태프 권한')
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')

    objects = UserManager()

    USERNAME_FIELD = 'github_id'  # 로그인 시 사용할 필드
    # REQUIRED_FIELDS = ['github_username', 'email']  # 슈퍼유저 생성 시 필요한 필드

    class Meta:
        verbose_name = '사용자'
        verbose_name_plural = '사용자들'
        db_table = 'user'

    def __str__(self):
        return self.github_username or self.github_id

class Project(models.Model):
    id = models.AutoField(primary_key=True, verbose_name='프로젝트 아이디')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects', verbose_name='사용자 아이디')
    #repository = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name='projects', verbose_name='레포지토리 아이디')
    name = models.CharField(max_length=20, verbose_name='프로젝트 이름')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name='수정일시')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='삭제일시')

    class Meta:
        verbose_name = '프로젝트'
        verbose_name_plural = '프로젝트들'
        db_table = 'project'

    def __str__(self):
        return self.name