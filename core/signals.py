from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import transaction
from .models import Task, Profile

@receiver(pre_save, sender=Task)
def task_pre_save(sender, instance, **kwargs):
    # store previous status for comparison
    if instance.pk:
        try:
            instance._prev_status = Task.objects.get(pk=instance.pk).status
        except Task.DoesNotExist:
            instance._prev_status = None
    else:
        instance._prev_status = None

@receiver(post_save, sender=Task)
def task_post_save(sender, instance, created, **kwargs):
    # only update on create or status change
    try:
        profile = instance.created_by.profile
    except Profile.DoesNotExist:
        return

    prev = getattr(instance, "_prev_status", None)
    curr = instance.status

    if created and curr == 'complete':
        with transaction.atomic():
            profile.completed_tasks_count = (profile.completed_tasks_count or 0) + 1
            profile.save(update_fields=['completed_tasks_count'])
    else:
        # status changed
        if prev != curr:
            with transaction.atomic():
                if prev != 'complete' and curr == 'complete':
                    profile.completed_tasks_count = (profile.completed_tasks_count or 0) + 1
                    profile.save(update_fields=['completed_tasks_count'])
                elif prev == 'complete' and curr != 'complete' and profile.completed_tasks_count > 0:
                    profile.completed_tasks_count = profile.completed_tasks_count - 1
                    profile.save(update_fields=['completed_tasks_count'])
