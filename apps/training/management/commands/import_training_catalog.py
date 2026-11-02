"""Import a public guide catalog into the isolated training-only database."""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_datetime

from apps.training.models import TrainingCategory, TrainingGuide, TrainingGuideRevision


class Command(BaseCommand):
    help = 'Import a published guide catalog exported from the management deployment.'

    def add_arguments(self, parser):
        parser.add_argument(
            'catalog', nargs='?', default=getattr(settings, 'TRAINING_CATALOG_PATH', None),
            help='Path to the exported training-catalog.json file.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not options['catalog']:
            raise CommandError('Provide a catalog path or configure TRAINING_CATALOG_PATH.')
        path = Path(options['catalog'])
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as error:
            raise CommandError(f'Cannot read training catalog: {error}') from error
        if data.get('schema_version') != 1 or not isinstance(data.get('guides'), list):
            raise CommandError('Unsupported or invalid training catalog format.')

        TrainingCategory.objects.update(is_active=False)
        categories = {}
        for item in data.get('categories', []):
            category, _ = TrainingCategory.objects.update_or_create(
                slug=item['slug'], defaults={
                    'name': item['name'], 'description': item.get('description', ''),
                    'display_order': item.get('display_order', 0), 'is_active': True,
                },
            )
            categories[category.slug] = category

        imported = 0
        for item in data['guides']:
            category_slug = item['category_slug']
            category = categories.get(category_slug)
            if category is None:
                category, _ = TrainingCategory.objects.get_or_create(
                    slug=category_slug,
                    defaults={'name': item['category_name'], 'is_active': True},
                )
                categories[category_slug] = category
            guide, _ = TrainingGuide.objects.get_or_create(
                slug=item['slug'],
                defaults={'title': item['title'], 'category': category, 'status': TrainingGuide.PublicationStatus.PUBLISHED},
            )
            revision_number = item['revision_number']
            revision = TrainingGuideRevision.objects.filter(guide=guide, revision_number=revision_number).first()
            published_at = parse_datetime(item['published_at'])
            if not published_at:
                raise CommandError(f"Invalid publication date for guide {item['slug']}.")
            revision_fields = {
                'title': item['title'], 'summary': item.get('summary', ''),
                'category_name': item['category_name'], 'category_slug': category_slug,
                'content_markdown': item['content_markdown'], 'tags': item.get('tags', ''),
                'published_at': published_at, 'related_references': item.get('related_references', []),
            }
            if revision is None:
                revision = TrainingGuideRevision.objects.create(guide=guide, revision_number=revision_number, **revision_fields)
                imported += 1
            elif any(getattr(revision, field) != value for field, value in revision_fields.items()):
                raise CommandError(f"Published revision {revision_number} for {item['slug']} differs from its immutable local copy.")
            guide.title = item['title']
            guide.summary = item.get('summary', '')
            guide.category = category
            guide.tags = item.get('tags', '')
            guide.content_markdown = item['content_markdown']
            guide.status = TrainingGuide.PublicationStatus.PUBLISHED
            guide.published_revision = revision
            guide.published_at = published_at
            guide.save()

        for slug in data.get('hidden_slugs', []) + data.get('archived_slugs', []):
            TrainingGuide.objects.filter(slug=slug).update(status=TrainingGuide.PublicationStatus.ARCHIVED)
        self.stdout.write(self.style.SUCCESS(f'Imported {imported} new revisions from {path}.'))
