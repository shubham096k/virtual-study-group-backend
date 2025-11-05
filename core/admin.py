from django.contrib import admin
from .models import Profile, Group, GroupMembership, Task, Document, StudySession, TimerSession, Notification

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'theme_mode', 'total_study_time')

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'created_at')

@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'role', 'joined_at')
    list_filter = ('role',)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'session', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'session')
    search_fields = ('title', 'description', 'created_by__username')

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'group', 'uploaded_by', 'approved', 'uploaded_at')
    list_filter = ('approved',)

@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'group', 'start_time', 'end_time')

@admin.register(TimerSession)
class TimerSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'mode', 'duration', 'started_at', 'ended_at')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'created_at', 'read_status')
