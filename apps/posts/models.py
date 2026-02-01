from django.conf import settings
from django.db import models
from apps.vehicles.models import UserVehicle

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True)

    def __str__(self):
        return self.name

class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    vehicle = models.ForeignKey(UserVehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts")

    title = models.CharField(max_length=150)
    body = models.TextField()
    tags = models.ManyToManyField(Tag, blank=True, related_name="posts")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="posts/%Y/%m/")
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "id"]
