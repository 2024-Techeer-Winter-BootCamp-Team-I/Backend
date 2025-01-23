
# Generated Django Models from ERD
from django.db import models


class o(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    integer = models.CharField(max_length=255)
    string = models.CharField(max_length=255)
    string = models.CharField(max_length=255)
    string = models.CharField(max_length=255)
    datetime = models.CharField(max_length=255)


class POST(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    integer = models.CharField(max_length=255)
    integer = models.CharField(max_length=255)
    string = models.CharField(max_length=255)
    string = models.CharField(max_length=255)
    datetime = models.CharField(max_length=255)
    datetime = models.CharField(max_length=255)


class COMMENT(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    integer = models.CharField(max_length=255)
    integer = models.CharField(max_length=255)
    integer = models.CharField(max_length=255)
    string = models.CharField(max_length=255)
    datetime = models.CharField(max_length=255)
    datetime = models.CharField(max_length=255)


class LIKE(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    integer = models.CharField(max_length=255)
    integer = models.CharField(max_length=255)
    integer = models.CharField(max_length=255)
    datetime = models.CharField(max_length=255)

