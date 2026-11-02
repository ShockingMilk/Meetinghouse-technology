"""Training guide catalog, private working copies, and immutable publications."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class TrainingCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True)
    description = models.CharField(max_length=300, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('display_order', 'name')
        verbose_name_plural = 'training categories'

    def __str__(self):
        return self.name


class TrainingGuide(models.Model):
    class PublicationStatus(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        IN_REVIEW = 'in_review', 'In Review'
        PUBLISHED = 'published', 'Published'
        ARCHIVED = 'archived', 'Archived'

    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True)
    summary = models.CharField(max_length=400, blank=True)
    content_markdown = models.TextField(blank=True)
    category = models.ForeignKey(TrainingCategory, on_delete=models.PROTECT, related_name='guides')
    tags = models.CharField(max_length=500, blank=True, help_text='Comma-separated keywords.')
    status = models.CharField(max_length=20, choices=PublicationStatus.choices, default=PublicationStatus.DRAFT)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='authored_training_guides')
    last_editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='edited_training_guides')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    review_date = models.DateField(null=True, blank=True)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_training_guides')
    review_notes = models.TextField(blank=True)
    published_revision = models.ForeignKey('TrainingGuideRevision', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    assets = models.ManyToManyField('inventory.Asset', blank=True, related_name='training_guides')
    rooms = models.ManyToManyField('inventory.Room', blank=True, related_name='training_guides')

    class Meta:
        ordering = ('title',)
        permissions = [
            ('publish_trainingguide', 'Can publish training guides'),
            ('review_trainingguide', 'Can review training guides'),
            ('archive_trainingguide', 'Can archive training guides'),
            ('restore_trainingguide', 'Can restore a training guide revision'),
        ]

    def __str__(self):
        return self.title

    def delete(self, *args, **kwargs):
        raise ValidationError('Training guides are archived instead of deleted so their revision history is retained.')

    @property
    def has_publication(self):
        return bool(self.published_revision_id and self.status != self.PublicationStatus.ARCHIVED)


class TrainingGuideRevision(models.Model):
    guide = models.ForeignKey(TrainingGuide, on_delete=models.PROTECT, related_name='revisions')
    revision_number = models.PositiveIntegerField()
    title = models.CharField(max_length=180)
    summary = models.CharField(max_length=400, blank=True)
    category_name = models.CharField(max_length=100)
    category_slug = models.SlugField(max_length=110)
    content_markdown = models.TextField()
    tags = models.CharField(max_length=500, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='training_publications_authored')
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='training_publications_edited')
    published_at = models.DateTimeField(default=timezone.now)
    related_references = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ('-revision_number',)
        constraints = [models.UniqueConstraint(fields=('guide', 'revision_number'), name='unique_training_guide_revision')]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError('Published guide revisions are immutable. Restore a revision into a new working copy instead.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('Published guide revisions cannot be deleted.')

    def __str__(self):
        return f'{self.guide.title} · revision {self.revision_number}'
