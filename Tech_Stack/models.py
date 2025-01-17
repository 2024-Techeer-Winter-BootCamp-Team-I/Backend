from django.db import models
from django.utils import timezone
from login.models import Project  

class TechStack(models.Model):
    """
    기술 스택 모델
    """
    id = models.AutoField(primary_key=True, verbose_name='기술 스택 아이디')
    name = models.CharField(max_length=20, verbose_name='기술 스택 이름', null=False)
    file_path = models.CharField(max_length=200, verbose_name='기술 스택 파일 또는 경로', null=False)
    type = models.CharField(max_length=50, verbose_name='기술 스택 타입', null=True, blank=True)
    install_command = models.TextField(verbose_name='설치 명령어', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, verbose_name='생성일시', null=False)
    deleted_at = models.DateTimeField(verbose_name='삭제일시', null=True, blank=True)

    class Meta:
        verbose_name = '기술 스택'
        verbose_name_plural = '기술 스택들'
        db_table = 'tech_stack'

    def __str__(self):
        return self.name


class ProjectTech(models.Model):
    """
    프로젝트 기술 모델
    """
    id = models.AutoField(primary_key=True, verbose_name='프로젝트 기술 아이디')
    project_id = models.ForeignKey('login.Project', on_delete=models.CASCADE, verbose_name='프로젝트 아이디', null=False)
    tech_id = models.ForeignKey(TechStack, on_delete=models.CASCADE, verbose_name='기술 스택 아이디', null=False)
    created_at = models.DateTimeField(default=timezone.now, verbose_name='생성일시', null=False)
    deleted_at = models.DateTimeField(verbose_name='삭제일시', null=True, blank=True)

    class Meta:
        verbose_name = '프로젝트 기술'
        verbose_name_plural = '프로젝트 기술들'
        db_table = 'project_tech'

    def __str__(self):
        return f"ProjectTech {self.id}"