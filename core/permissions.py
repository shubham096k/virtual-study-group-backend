from rest_framework import permissions
from .models import GroupMembership, Group, Document


class IsGroupAdmin(permissions.BasePermission):
    """
    Allows access only to users who are admin of the given group.
    Works with both group_id in request or object.group.
    """

    def has_permission(self, request, view):
        # If the request is authenticated, allow further checks
        if not request.user or not request.user.is_authenticated:
            return False

        # Try to get group_id directly (useful for /groups/<id>/something)
        group_pk = view.kwargs.get('group_pk') or request.data.get('group')

        # If not found, try to infer it from a Document (for /documents/<id>/approve/)
        if not group_pk and view.kwargs.get('pk'):
            try:
                doc = Document.objects.get(pk=view.kwargs['pk'])
                group_pk = doc.group_id
            except Document.DoesNotExist:
                return False

        if not group_pk:
            # No way to identify a group, deny permission
            return False

        # Check if user is admin of that group or is a superuser
        return GroupMembership.objects.filter(
            group_id=group_pk, user=request.user, role='admin'
        ).exists() or request.user.is_superuser

    def has_object_permission(self, request, view, obj):
        # For object-level permissions (when DRF calls get_object)
        group = getattr(obj, 'group', None)
        if not group:
            return False
        return GroupMembership.objects.filter(
            group=group, user=request.user, role='admin'
        ).exists() or request.user.is_superuser
