"""Guide publication snapshots and public-safe catalog replication."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.safestring import mark_safe

from .markdown import render_markdown as sanitize_markdown
from .models import TrainingGuide, TrainingGuideRevision


def render_markdown(source):
    """Return sanitized markup as safe template content."""
    return mark_safe(sanitize_markdown(source))


def public_queryset():
    """Return guides with an active published snapshot, never unreviewed-only drafts."""
    return TrainingGuide.objects.filter(
        published_revision__isnull=False,
        category__is_active=True,
    ).exclude(status=TrainingGuide.PublicationStatus.ARCHIVED).select_related(
        'category', 'published_revision',
    )


@transaction.atomic
def publish_guide(guide, *, editor):
    guide = TrainingGuide.objects.select_for_update().select_related('category').get(pk=guide.pk)
    if guide.status != TrainingGuide.PublicationStatus.IN_REVIEW:
        raise ValidationError('Submit this guide for review before publishing it.')
    if not guide.review_date:
        raise ValidationError('Record a review before publishing this guide.')
    previous = guide.revisions.order_by('-revision_number').first()
    number = previous.revision_number + 1 if previous else 1
    refs = []
    for asset in guide.assets.select_related('room').order_by('inventory_number'):
        refs.append({'kind': 'asset', 'id': asset.pk, 'inventory_number': asset.inventory_number,
                     'name': asset.name, 'category': asset.get_category_display(),
                     'room': asset.room.name if asset.room_id else ''})
    for room in guide.rooms.order_by('name'):
        refs.append({'kind': 'room', 'id': room.pk, 'name': room.name, 'room_number': room.room_number})
    revision = TrainingGuideRevision.objects.create(
        guide=guide, revision_number=number, title=guide.title, summary=guide.summary,
        category_name=guide.category.name, category_slug=guide.category.slug,
        content_markdown=guide.content_markdown, tags=guide.tags,
        author=guide.author, editor=editor, related_references=refs,
    )
    guide.published_revision = revision
    guide.published_at = revision.published_at
    guide.status = TrainingGuide.PublicationStatus.PUBLISHED
    guide.last_editor = editor
    guide.save(update_fields=('published_revision', 'published_at', 'status', 'last_editor', 'updated_at'))
    return revision


def restore_working_copy(guide, revision, *, editor):
    if revision.guide_id != guide.pk:
        raise ValidationError('That revision belongs to a different guide.')
    guide.title = revision.title
    guide.summary = revision.summary
    guide.content_markdown = revision.content_markdown
    guide.tags = revision.tags
    from .models import TrainingCategory
    guide.category = TrainingCategory.objects.filter(slug=revision.category_slug).first() or guide.category
    guide.status = TrainingGuide.PublicationStatus.DRAFT
    guide.last_editor = editor
    guide.review_date = None
    guide.reviewer = None
    guide.save()
    asset_ids = [item.get('id') for item in revision.related_references if item.get('kind') == 'asset' and item.get('id')]
    room_ids = [item.get('id') for item in revision.related_references if item.get('kind') == 'room' and item.get('id')]
    guide.assets.set(asset_ids)
    guide.rooms.set(room_ids)
    return guide
