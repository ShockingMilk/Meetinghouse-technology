# Generated manually to preserve the existing inventory migration history.
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def seed_categories(apps, schema_editor):
    Category = apps.get_model('training', 'TrainingCategory')
    rows = (
        ('Audio Systems', 'audio-systems', 'Microphones, room audio, and sound systems.'),
        ('Assistive Listening', 'assistive-listening', 'Using assistive listening equipment.'),
        ('Computers and Broadcast', 'computers-broadcast', 'Broadcast host and production workflows.'),
        ('Cameras and Zoom', 'cameras-zoom', 'Camera operation, meetings, and broadcasts.'),
        ('Networking', 'networking', 'User-facing network procedures and escalation guidance.'),
        ('Printing', 'printing', 'Printing and printer troubleshooting.'),
        ('Equipment Inventory', 'equipment-inventory', 'Equipment identification and inventory procedures.'),
        ('Maintenance and Troubleshooting', 'maintenance-troubleshooting', 'Authorized maintenance and troubleshooting.'),
        ('General Technology', 'general-technology', 'General meetinghouse technology guidance.'),
        ('Policies and Procedures', 'policies-procedures', 'Authorization, safety, and support procedures.'),
    )
    for order, (name, slug, description) in enumerate(rows, 1):
        Category.objects.get_or_create(slug=slug, defaults={
            'name': name, 'description': description, 'display_order': order, 'is_active': True,
        })


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('inventory', '0006_assetdependency_assetspecification_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TrainingCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=110, unique=True)),
                ('description', models.CharField(blank=True, max_length=300)),
                ('display_order', models.PositiveSmallIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'verbose_name_plural': 'training categories', 'ordering': ('display_order', 'name')},
        ),
        migrations.CreateModel(
            name='TrainingGuide',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=180)),
                ('slug', models.SlugField(max_length=200, unique=True)),
                ('summary', models.CharField(blank=True, max_length=400)),
                ('content_markdown', models.TextField(blank=True)),
                ('tags', models.CharField(blank=True, help_text='Comma-separated keywords.', max_length=500)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('in_review', 'In Review'), ('published', 'Published'), ('archived', 'Archived')], default='draft', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('published_at', models.DateTimeField(blank=True, null=True)),
                ('review_date', models.DateField(blank=True, null=True)),
                ('review_notes', models.TextField(blank=True)),
                ('assets', models.ManyToManyField(blank=True, related_name='training_guides', to='inventory.asset')),
                ('rooms', models.ManyToManyField(blank=True, related_name='training_guides', to='inventory.room')),
                ('author', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='authored_training_guides', to=settings.AUTH_USER_MODEL)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='guides', to='training.trainingcategory')),
                ('last_editor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='edited_training_guides', to=settings.AUTH_USER_MODEL)),
                ('reviewer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_training_guides', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('title',), 'permissions': [('publish_trainingguide', 'Can publish training guides'), ('review_trainingguide', 'Can review training guides'), ('archive_trainingguide', 'Can archive training guides'), ('restore_trainingguide', 'Can restore a training guide revision')]},
        ),
        migrations.CreateModel(
            name='TrainingGuideRevision',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('revision_number', models.PositiveIntegerField()),
                ('title', models.CharField(max_length=180)),
                ('summary', models.CharField(blank=True, max_length=400)),
                ('category_name', models.CharField(max_length=100)),
                ('category_slug', models.SlugField(max_length=110)),
                ('content_markdown', models.TextField()),
                ('tags', models.CharField(blank=True, max_length=500)),
                ('published_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('related_references', models.JSONField(blank=True, default=list)),
                ('author', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='training_publications_authored', to=settings.AUTH_USER_MODEL)),
                ('editor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='training_publications_edited', to=settings.AUTH_USER_MODEL)),
                ('guide', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='revisions', to='training.trainingguide')),
            ],
            options={'ordering': ('-revision_number',)},
        ),
        migrations.AddField(
            model_name='trainingguide',
            name='published_revision',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='training.trainingguiderevision'),
        ),
        migrations.AddConstraint(
            model_name='trainingguiderevision',
            constraint=models.UniqueConstraint(fields=('guide', 'revision_number'), name='unique_training_guide_revision'),
        ),
        migrations.RunPython(seed_categories, migrations.RunPython.noop),
    ]
