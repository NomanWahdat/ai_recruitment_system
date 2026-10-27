from django.db import transaction
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from .models import Candidate


@receiver(post_delete, sender=Candidate)
def delete_resume(sender, instance, **kwargs):
    if instance.cv_file:
        storage, name = instance.cv_file.storage, instance.cv_file.name
        transaction.on_commit(lambda: storage.delete(name))


@receiver(pre_save, sender=Candidate)
def replace_resume(sender, instance, **kwargs):
    if instance.pk:
        previous = sender.objects.filter(pk=instance.pk).values_list("cv_file", flat=True).first()
        if previous and previous != instance.cv_file.name:
            storage = instance.cv_file.storage
            transaction.on_commit(lambda: storage.delete(previous))
