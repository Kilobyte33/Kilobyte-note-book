from time import timezone

from django.db import models
from django.contrib.auth.models import User

class Folder(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Note(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField() 
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    folder = models.ForeignKey(Folder, on_delete=models.SET_NULL, null=True, blank=True, related_name='notes')
    is_favorite = models.BooleanField(default=False)
    is_trashed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)


    def __str__(self):
        return self.title

class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    dark_mode = models.BooleanField(default=False)
    editor_mode = models.CharField(max_length=20, default='split') 

    def __str__(self):
        return f"Settings for {self.user.username}"

class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=[('user', 'User'), ('bot', 'Bot')])
    message = models.TextField()
    has_attachment = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role}: {self.message[:50]}..."
    
