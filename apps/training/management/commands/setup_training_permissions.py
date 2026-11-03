"""Provision a reusable group for authorized Technology Specialists."""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from apps.training.models import TrainingCategory, TrainingGuide, TrainingGuideRevision


class Command(BaseCommand):
    help = 'Create the Technology Specialists group and grant training guide workflow permissions.'

    def handle(self, *args, **options):
        group, _ = Group.objects.get_or_create(name='Technology Specialists')
        models = (TrainingCategory, TrainingGuide, TrainingGuideRevision)
        content_types = [ContentType.objects.get_for_model(model) for model in models]
        codenames = {
            'view_trainingcategory', 'add_trainingcategory', 'change_trainingcategory',
            'view_trainingguide', 'add_trainingguide', 'change_trainingguide',
            'publish_trainingguide', 'review_trainingguide', 'archive_trainingguide',
            'restore_trainingguide', 'view_trainingguiderevision',
        }
        permissions = Permission.objects.filter(content_type__in=content_types, codename__in=codenames)
        group.permissions.set(permissions)
        self.stdout.write(self.style.SUCCESS(f'Configured {permissions.count()} permissions for {group.name}. Add authorized users to this group.'))
