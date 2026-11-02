"""Export only public-safe, currently published guide snapshots."""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.training.models import TrainingCategory, TrainingGuide
from apps.training.services import public_queryset


class Command(BaseCommand):
    help = 'Export public training guides for the isolated training deployment.'

    def add_arguments(self, parser):
        parser.add_argument('--output', default=str(settings.BASE_DIR / 'data' / 'training-catalog.json'))

    def handle(self, *args, **options):
        guides = []
        for guide in public_queryset().order_by('slug'):
            revision = guide.published_revision
            guides.append({
                'slug': guide.slug,
                'revision_number': revision.revision_number,
                'title': revision.title,
                'summary': revision.summary,
                'category_name': revision.category_name,
                'category_slug': revision.category_slug,
                'content_markdown': revision.content_markdown,
                'tags': revision.tags,
                'published_at': revision.published_at.isoformat(),
                'related_references': revision.related_references,
            })
        visible_slugs = {guide['slug'] for guide in guides}
        hidden_slugs = list(TrainingGuide.objects.exclude(status=TrainingGuide.PublicationStatus.ARCHIVED).exclude(slug__in=visible_slugs).filter(published_revision__isnull=False).values_list('slug', flat=True))
        data = {
            'schema_version': 1,
            'exported_at': timezone.now().isoformat(),
            'categories': list(TrainingCategory.objects.filter(is_active=True).order_by('display_order', 'name').values('name', 'slug', 'description', 'display_order')),
            'guides': guides,
            'hidden_slugs': hidden_slugs,
            'archived_slugs': list(TrainingGuide.objects.filter(status=TrainingGuide.PublicationStatus.ARCHIVED).values_list('slug', flat=True)),
        }
        output = Path(options['output'])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f'Exported {len(guides)} published guides to {output}'))
