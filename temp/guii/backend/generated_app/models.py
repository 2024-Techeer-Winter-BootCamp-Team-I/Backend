
# Generated Django Models from ERD
from django.db import models


class o(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=255)


class IMAGE_GENERATION(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    user_id = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    generated_image_url = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)


class IMAGE_STORAGE(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    image_generation_id = models.CharField(max_length=255)
    stored_image_url = models.CharField(max_length=255)
    encryption_key = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)


class IMAGE_EDITING(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    image_generation_id = models.CharField(max_length=255)
    edited_image_url = models.CharField(max_length=255)
    edit_options = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)


class MESSAGE_SENDING(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    image_generation_id = models.CharField(max_length=255)
    recipient_phone_number = models.CharField(max_length=255)
    message_content = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    sent_at = models.DateTimeField(auto_now_add=True)


class MESSAGE_HISTORY(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    user_id = models.CharField(max_length=255)
    message_sending_id = models.CharField(max_length=255)
    viewed_at = models.DateTimeField(auto_now_add=True)

