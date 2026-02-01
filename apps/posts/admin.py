from django.contrib import admin
from .models import Post, PostImage, Tag

admin.site.register(Post)
admin.site.register(PostImage)
admin.site.register(Tag)
