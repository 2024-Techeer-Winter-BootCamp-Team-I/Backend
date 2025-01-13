from django.db import models

class Repository(models.Model):
    name = models.CharField(max_length=20, null=True, blank=True, verbose_name="레포지토리 아이디")
    url = models.CharField(max_length=200, null=True, blank=True, verbose_name="레포지토리 이름")
    created_at = models.DateTimeField(null=True, blank=True, verbose_name="생성 일시")
    updated_at = models.DateTimeField(null=True, blank=True, verbose_name="수정 일시시")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="삭제 일시")

    class Meta:
        verbose_name = '레포지토리'
        verbose_name_plural = '레포지토리들'
        db_table='repo'

    def __str__(self):
        return self.name or "Unnamed Repository"