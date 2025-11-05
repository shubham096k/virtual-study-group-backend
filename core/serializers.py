from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Profile, Group, GroupMembership, Task, Document, DocumentComment,
    StudySession, TimerSession, Notification
)

# User Serializer (register)
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=6)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')

    def create(self, validated_data):
        user = User(username=validated_data['username'], email=validated_data.get('email', ''))
        user.set_password(validated_data['password'])
        user.save()
        # create related profile
        Profile.objects.create(user=user)
        return user

# Profile Serializer
class ProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.ReadOnlyField(source='user.id')
    username = serializers.ReadOnlyField(source='user.username')
    groups_created_count = serializers.SerializerMethodField()
    groups_joined_count = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ('user_id', 'username', 'theme_mode', 'total_study_time',
                  'completed_tasks_count', 'bio', 'profile_picture',
                  'groups_created_count', 'groups_joined_count')
        read_only_fields = ('total_study_time', 'completed_tasks_count', 'user_id', 'username')

    def get_groups_created_count(self, obj):
        return obj.user.created_groups.count()

    def get_groups_joined_count(self, obj):
        return obj.user.memberships.count()


# Group Serializer
class GroupSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()

    def get_created_by(self, obj):
        return {
            "id": obj.created_by.id,
            "username": obj.created_by.username
        }
    

    class Meta:
        model = Group
        fields = ('id', 'name', 'description', 'created_by', 'created_at')

# GroupMembership Serializer
class GroupMembershipSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    class Meta:
        model = GroupMembership
        fields = ('id', 'user', 'group', 'role', 'joined_at')

# Task Serializer
class TaskSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ('id', 'session', 'created_by', 'title', 'description',
                  'status', 'due_date', 'created_at')
        read_only_fields = ('created_by',)

    def get_created_by(self, obj):
        return {"id": obj.created_by.id, "username": obj.created_by.username}


# Document Serializer
class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.SerializerMethodField()
    file = serializers.FileField()

    class Meta:
        model = Document
        fields = ('id', 'group', 'uploaded_by', 'title', 'file',
                  'file_type', 'file_size', 'uploaded_at', 'approved')

    def get_uploaded_by(self, obj):
        return {"id": obj.uploaded_by.id, "username": obj.uploaded_by.username}


# StudySession Serializer
class StudySessionSerializer(serializers.ModelSerializer):
    tasks_count = serializers.SerializerMethodField()

    class Meta:
        model = StudySession
        fields = ('id', 'group', 'title', 'description', 'start_time', 'end_time', 'tasks_count')

    def get_tasks_count(self, obj):
        return obj.tasks.count()
    
    def validate(self, attrs):
        start = attrs.get('start_time')
        end = attrs.get('end_time')
        if start and end and start >= end:
            raise serializers.ValidationError(
                "Start time must be before end time.")
        return attrs

# TimerSession Serializer
class TimerSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimerSession
        fields = '__all__'   # ensures all model fields are included
        read_only_fields = ['user', 'started_at']

# Notification Serializer
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ('id', 'user', 'message', 'created_at', 'read_status')


# Document Discussion Serializer
class DocumentCommentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = DocumentComment
        fields = ('id', 'document', 'user', 'comment', 'created_at')
        read_only_fields = ('user', 'created_at')

    def get_user(self, obj):
        return {"id": obj.user.id, "username": obj.user.username}

