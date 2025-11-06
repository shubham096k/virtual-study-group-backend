from django.conf import settings
from django.db import models
from django.contrib.auth.models import User  # using default User
from django.utils import timezone

# Profile (1:1 with User)
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    theme_mode = models.CharField(max_length=10, default='light')  # 'light' or 'dark'
    total_study_time = models.PositiveIntegerField(default=0)  # minutes
    completed_tasks_count = models.PositiveIntegerField(default=0)
    bio = models.TextField(blank=True, null=True)  # Added for user profile
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)  # Added

    def __str__(self):
        return f"{self.user.username} Profile"


# Group
class Group(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# GroupMembership (junction for users <-> groups)
class GroupMembership(models.Model):
    ROLE_CHOICES = (('admin', 'Admin'), ('member', 'Member'))

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'group')

    def __str__(self):
        return f"{self.user.username} in {self.group.name} as {self.role}"


# Task (can be personal or group-based)
class Task(models.Model):
    STATUS_CHOICES = (('pending', 'Pending'), ('complete', 'Complete'))

    session = models.ForeignKey('StudySession', on_delete=models.CASCADE, related_name='tasks')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


# Document (requires admin approval)
def document_upload_path(instance, filename):
    return f"documents/group_{instance.group.id}/{filename}"


class Document(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='documents')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_documents')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to=document_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)
    file_size = models.PositiveIntegerField(default=0)  # Added
    file_type = models.CharField(max_length=50, blank=True)  # Added

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
            self.file_type = self.file.name.split('.')[-1]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


# Document comments/discussion
class DocumentComment(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.document.title}"


# StudySession (scheduling)
class StudySession(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='sessions')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    # created_by = models.ForeignKey(
    #     User, on_delete=models.CASCADE, related_name='created_sessions')
    # created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.group.name})"
    
    @property
    def status(self):
        """Returns 'active' if session is ongoing, 'completed' if past."""
        now = timezone.now()
        if self.end_time < now:
            return "completed"
        return "active"


# TimerSession (user personal sessions)
class TimerSession(models.Model):
    MODE_CHOICES = (('timer', 'Timer'), ('focused', 'Focused'), ('pomodoro', 'Pomodoro'))

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='timer_sessions')
    mode = models.CharField(max_length=20, choices=MODE_CHOICES)
    duration = models.PositiveIntegerField(help_text='Duration in minutes')
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    is_paused = models.BooleanField(default=False)
    paused_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.mode} - {self.duration}m"


# Notification
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_status = models.BooleanField(default=False)
    type = models.CharField(max_length=50, default='info')  # Added (optional categorization)

    def __str__(self):
        return f"Notif for {self.user.username} at {self.created_at}"
