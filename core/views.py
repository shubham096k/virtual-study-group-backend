from rest_framework import viewsets, generics, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from . import models
from .models import Profile, Group, GroupMembership, Task, Document, StudySession, TimerSession, Notification, DocumentComment
from .serializers import (
    UserSerializer, ProfileSerializer, GroupSerializer,
    GroupMembershipSerializer, TaskSerializer, DocumentSerializer, DocumentCommentSerializer,
    StudySessionSerializer, TimerSessionSerializer, NotificationSerializer
)
from .permissions import IsGroupAdmin
from rest_framework.parsers import MultiPartParser, FormParser

# User registration


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserSerializer

# Profile view


class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ProfileSerializer

    def get_object(self):
        profile, created = Profile.objects.get_or_create(
            user=self.request.user)
        return profile

# Group ViewSet


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all().order_by('-created_at')
    serializer_class = GroupSerializer
    permission_classes = (IsAuthenticated,)

    def perform_create(self, serializer):
        group = serializer.save(created_by=self.request.user)
        # creator becomes a group admin
        GroupMembership.objects.create(
            user=self.request.user, group=group, role='admin')

    @action(detail=True, methods=['post'], url_path='join')
    def join_group(self, request, pk=None):
        group = self.get_object()
        # prevent duplicates
        membership, created = GroupMembership.objects.get_or_create(
            user=request.user, group=group, defaults={'role': 'member'})
        if created:
            return Response({'detail': 'Joined group'}, status=status.HTTP_201_CREATED)
        return Response({'detail': 'Already member'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='leave')
    def leave_group(self, request, pk=None):
        group = self.get_object()
        GroupMembership.objects.filter(user=request.user, group=group).delete()
        return Response({'detail': 'Left group'}, status=status.HTTP_200_OK)

    # Restrict deletion to group creator only
    def perform_destroy(self, instance):
        if instance.created_by != self.request.user:
            raise PermissionDenied(
                "Only the group creator can delete this group.")
        instance.delete()

# Task ViewSet


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all().order_by('-created_at')
    serializer_class = TaskSerializer
    permission_classes = (IsAuthenticated,)

    def perform_create(self, serializer):
        session = serializer.validated_data.get('session')
        if not session:
            raise serializers.ValidationError("session field is required")

        group = session.group
        if not GroupMembership.objects.filter(group=group, user=self.request.user).exists():
            raise PermissionDenied(
                'You must be a member of the group to create a session task')
        serializer.save(created_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        task = self.get_object()
        group = task.session.group
        membership = GroupMembership.objects.filter(
            group=group, user=request.user).first()

        # Only creator or group admin can delete
        if task.created_by == request.user or (membership and membership.role == 'admin'):
            return super().destroy(request, *args, **kwargs)
        else:
            return Response({'detail': 'Only task creator or group admin can delete this task.'}, status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        user = self.request.user
        member_groups = GroupMembership.objects.filter(
            user=user).values_list('group', flat=True)
        queryset = Task.objects.filter(
            session__group__in=member_groups).order_by('-created_at')

        # Optional filter: /tasks/?session=12
        session_id = self.request.query_params.get('session')
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        return queryset

# Document ViewSet


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all().order_by('-uploaded_at')
    serializer_class = DocumentSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        group = serializer.validated_data.get('group')
        # only members may upload
        if not GroupMembership.objects.filter(group=group, user=self.request.user).exists():
            raise PermissionDenied(
                'You must be a member of the group to upload documents')
        # uploaded_by is request.user; approved False by default
        serializer.save(uploaded_by=self.request.user, approved=False)

        # after serializer.save(...)
        group_admin = group.created_by
        if group_admin != self.request.user:
            Notification.objects.create(
                user=group_admin,
                message=f"{self.request.user.username} uploaded '{serializer.instance.title}' in '{group.name}' awaiting approval.",
                type='document_upload'
            )

    @action(detail=True, methods=['post'], url_path='approve', permission_classes=[IsAuthenticated, IsGroupAdmin])
    def approve_document(self, request, pk=None):
        doc = self.get_object()
        # check admin
        # IsGroupAdmin permission uses group id from request or obj
        doc.approved = True
        doc.save()
        return Response({'detail': 'Document approved'}, status=status.HTTP_200_OK)

    def get_queryset(self):
        user = self.request.user

        # Get all groups user is member of
        member_groups = GroupMembership.objects.filter(
            user=user).values_list('group', flat=True)
        # Get all groups where user is admin
        admin_groups = GroupMembership.objects.filter(
            user=user, role='admin').values_list('group', flat=True)

        # Uploader can always see their own docs
        # Members see approved docs
        # Admins see all docs (approved or not) in their groups
        return Document.objects.filter(
            Q(uploaded_by=user) |
            Q(group__in=member_groups, approved=True) |
            Q(group__in=admin_groups)
        ).order_by('-uploaded_at')

    def destroy(self, request, *args, **kwargs):
        document = self.get_object()
        # check if the user is admin of the document's group
        is_admin = GroupMembership.objects.filter(
            group=document.group,
            user=request.user,
            role='admin'
        ).exists() or request.user.is_superuser

        if not is_admin:
            raise PermissionDenied("Only group admins can delete documents.")

        return super().destroy(request, *args, **kwargs)


# StudySession ViewSet
class StudySessionViewSet(viewsets.ModelViewSet):
    queryset = StudySession.objects.all().order_by('-start_time')
    serializer_class = StudySessionSerializer
    permission_classes = (IsAuthenticated,)

    def perform_create(self, serializer):
        group = serializer.validated_data.get('group')
        # only group admins or members? Here allow admins or members to schedule if member present.
        if GroupMembership.objects.filter(group=group, user=self.request.user).exists():
            serializer.save()
        else:
            raise PermissionDenied(
                'You must be a group member to schedule a session')

    def destroy(self, request, *args, **kwargs):
        session = self.get_object()
        group = session.group
        membership = GroupMembership.objects.filter(
            group=group, user=request.user).first()

        # Only the creator or a group admin can delete
        if session.created_by == request.user or (membership and membership.role == 'admin'):
            return super().destroy(request, *args, **kwargs)
        return Response(
            {'detail': 'Only the session creator or group admin can delete this session.'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Only group admin can delete if membership and membership.role == 'admin': return super().destroy(request, *args, **kwargs) elif group.created_by == request.user: return super().destroy(request, *args, **kwargs) else: return Response({'detail': 'Only group admin can delete a session.'}, status=status.HTTP_403_FORBIDDEN)
    # def destroy(self, request, *args, **kwargs):
    #     session = self.get_object()
    #     group = session.group
    #     membership = GroupMembership.objects.filter(group=group, user=request.user).first()

    #     # Only group admin or group creator can delete
    #     if membership and membership.role == 'admin':
    #         return super().destroy(request, *args, **kwargs)
    #     elif group.created_by == request.user:
    #         return super().destroy(request, *args, **kwargs)
    #     else:
    #         return Response({'detail': 'Only group admin can delete a session.'}, status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        user = self.request.user
        member_groups = GroupMembership.objects.filter(
            user=user).values_list('group', flat=True)
        queryset = StudySession.objects.filter(
            group__in=member_groups).order_by('-start_time')

        # Optional filtering by group
        group_id = self.request.query_params.get('group')
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        return queryset

# TimerSession ViewSet


class TimerSessionViewSet(viewsets.ModelViewSet):
    queryset = TimerSession.objects.all().order_by('-started_at')
    serializer_class = TimerSessionSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        # users only see their own timer sessions
        return TimerSession.objects.filter(user=self.request.user).order_by('-started_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, started_at=timezone.now())

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        timer = self.get_object()
        if timer.ended_at:
            return Response({'error': 'Timer already stopped.'}, status=status.HTTP_400_BAD_REQUEST)
        timer.is_paused = True
        timer.paused_at = timezone.now()
        timer.save()
        return Response({'status': 'paused', 'paused_at': timer.paused_at}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        timer = self.get_object()
        if not timer.is_paused:
            return Response({'error': 'Timer is not paused.'}, status=status.HTTP_400_BAD_REQUEST)
        timer.is_paused = False
        timer.save()
        return Response({'status': 'resumed'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        timer = self.get_object()
        if timer.ended_at:
            return Response({'error': 'Timer already stopped.'}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        timer.ended_at = now
        timer.save(update_fields=['ended_at'])

        # calculate minutes elapsed (round down)
        delta = (timer.ended_at - timer.started_at).total_seconds()
        minutes = int(delta // 60)

        # update profile total study time
        profile = None
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            profile = None

        if profile and minutes > 0:
            with transaction.atomic():
                profile.total_study_time = (
                    profile.total_study_time or 0) + minutes
                profile.save(update_fields=['total_study_time'])

        return Response({'status': 'stopped', 'ended_at': timer.ended_at, 'added_minutes': minutes}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def restart(self, request, pk=None):
        timer = self.get_object()
        timer.started_at = timezone.now()
        timer.ended_at = None
        timer.is_paused = False
        timer.paused_at = None
        timer.save()
        return Response({
            'status': 'restarted',
            'started_at': timer.started_at
        }, status=status.HTTP_200_OK)


# Notification ViewSet
class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all().order_by('-created_at')
    serializer_class = NotificationSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notif = self.get_object()
        notif.read_status = True
        notif.save()
        return Response({'detail': 'Marked as read'}, status=status.HTTP_200_OK)


# DocumentCommentViewset
class DocumentCommentViewSet(viewsets.ModelViewSet):
    queryset = models.DocumentComment.objects.all().order_by('-created_at')
    serializer_class = DocumentCommentSerializer
    permission_classes = (IsAuthenticated,)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        user = self.request.user
        # Get all groups where this user is a member
        member_groups = GroupMembership.objects.filter(
            user=user
        ).values_list('group', flat=True)

        # Only comments from documents belonging to those groups
        queryset = DocumentComment.objects.filter(
            document__group__in=member_groups
        ).order_by('-created_at')

        # Optional filtering by document ID
        document_id = self.request.query_params.get('document')
        if document_id:
            queryset = queryset.filter(document_id=document_id)

        return queryset

    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        group = comment.document.group

        # Check group membership and role
        membership = GroupMembership.objects.filter(
            group=group, user=request.user).first()

        if comment.user == request.user or (membership and membership.role == 'admin'):
            return super().destroy(request, *args, **kwargs)
        return Response(
            {'detail': 'Only the comment author or a group admin can delete this comment.'},
            status=status.HTTP_403_FORBIDDEN
        )
