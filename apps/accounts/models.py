from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    country = models.CharField(max_length=2, blank=True, default="")  # ISO 3166-1 alpha-2
