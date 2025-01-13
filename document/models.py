from django.conf import settings
from django.db import models
#from gunicorn.config import User


# Create your models here.
class Document(models.Model):
    id = models.AutoField(primary_key=True)
    # user_id = models.ForeinKey(
    #     settings.AUTH_USER_MODEL,
    #     on_delete=models.CASCADE,
    #     db_column='user_id',
    #     db_index=True,
    #     null=False
    # )

    title = models.CharField(max_length=255)
    content = models.TextField()
    requirements = models.TextField(default="No requirements provided")
    result = models.TextField(default="")

    diagram_code = models.TextField()
    erd_code = models.TextField()
    api_code = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "document"

    def __str__(self):
        return f"Document {self.id} by {self.user.username}"