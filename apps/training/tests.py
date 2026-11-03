"""Publication, permissions, search, related records, and Markdown safety tests."""

import json
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import Resolver404, resolve, reverse
from django.utils import timezone

from apps.inventory.models import Asset, Room
from .markdown import render_markdown
from .models import TrainingCategory, TrainingGuide, TrainingGuideRevision
from .services import publish_guide


class TrainingGuideWorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.author = User.objects.create_superuser(username='training-admin', email='training@example.invalid', password='long-safe-password')
        self.client.force_login(self.author)
        self.category, _ = TrainingCategory.objects.get_or_create(
            slug='audio-systems',
            defaults={
                'name': 'Audio Systems',
                'is_active': True,
            },
        )
        self.guide = TrainingGuide.objects.create(
            title='Operate the sound system', slug='operate-sound-system',
            summary='Start and check room audio.', category=self.category,
            content_markdown='# First version\n\nUse the approved controls.',
            tags='audio, microphone', author=self.author, last_editor=self.author,
        )

    def publish(self, guide=None):
        guide = guide or self.guide
        guide.status = TrainingGuide.PublicationStatus.IN_REVIEW
        guide.review_date = timezone.localdate()
        guide.reviewer = self.author
        guide.save()
        revision = publish_guide(guide, editor=self.author)
        guide.refresh_from_db()
        return revision

    def test_new_guide_is_draft_and_is_not_public(self):
        response = self.client.get(reverse('training:manage_guide_edit', args=(self.guide.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.guide.status, TrainingGuide.PublicationStatus.DRAFT)
        self.assertEqual(self.client.get(reverse('training:guide_detail', args=(self.guide.slug,))).status_code, 404)

    def test_publish_creates_immutable_revision_and_publication_snapshot(self):
        revision = self.publish()
        self.assertEqual(revision.revision_number, 1)
        response = self.client.get(reverse('training:guide_detail', args=(self.guide.slug,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'First version')
        self.guide.refresh_from_db()
        self.guide.content_markdown = '# Edited working copy'
        self.guide.save()
        self.assertEqual(self.guide.published_revision.content_markdown, '# First version\n\nUse the approved controls.')
        with self.assertRaises(ValidationError):
            revision.save()
        with self.assertRaises(ValidationError):
            revision.delete()

    def test_editing_and_review_keep_last_published_version_until_confirmed_publish(self):
        first = self.publish()
        edit_url = reverse('training:manage_guide_edit', args=(self.guide.pk,))
        payload = {
            'title': 'Operate the sound system', 'slug': self.guide.slug,
            'summary': 'Updated instructions.', 'category': str(self.category.pk),
            'tags': 'audio, updated', 'content_markdown': '# New version',
            'assets': [], 'rooms': [], 'action': 'save',
        }
        self.client.post(edit_url, payload)
        self.guide.refresh_from_db()
        self.assertEqual(self.guide.published_revision_id, first.pk)
        self.assertContains(self.client.get(reverse('training:guide_detail', args=(self.guide.slug,))), 'First version')
        self.client.post(reverse('training:manage_guide_submit_review', args=(self.guide.pk,)))
        self.guide.refresh_from_db()
        self.assertEqual(self.guide.status, TrainingGuide.PublicationStatus.IN_REVIEW)
        self.assertContains(self.client.get(reverse('training:guide_detail', args=(self.guide.slug,))), 'First version')
        publish_url = reverse('training:manage_guide_publish', args=(self.guide.pk,))
        self.client.post(publish_url, {'confirm_publish': 'yes'})
        self.guide.refresh_from_db()
        self.assertEqual(self.guide.published_revision.revision_number, 2)
        self.assertEqual(self.guide.revisions.count(), 2)
        self.assertContains(self.client.get(reverse('training:guide_detail', args=(self.guide.slug,))), 'New version')

    def test_archived_published_guide_is_hidden_without_deleting_revisions(self):
        revision = self.publish()
        response = self.client.post(reverse('training:manage_guide_archive', args=(self.guide.pk,)), {'confirm_archive': 'yes'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.guide.revisions.count(), 1)
        self.assertEqual(self.client.get(reverse('training:guide_detail', args=(self.guide.slug,))).status_code, 404)
        self.assertTrue(TrainingGuideRevision.objects.filter(pk=revision.pk).exists())

    def test_restore_older_revision_creates_working_copy_and_keeps_history(self):
        first = self.publish()
        self.guide.content_markdown = '# Second version'
        self.guide.status = TrainingGuide.PublicationStatus.IN_REVIEW
        self.guide.review_date = first.published_at.date()
        self.guide.save()
        self.publish()
        response = self.client.post(reverse('training:manage_guide_restore', args=(self.guide.pk, first.pk)))
        self.assertEqual(response.status_code, 302)
        self.guide.refresh_from_db()
        self.assertEqual(self.guide.content_markdown, first.content_markdown)
        self.assertEqual(self.guide.revisions.count(), 2)
        self.assertContains(self.client.get(reverse('training:guide_detail', args=(self.guide.slug,))), 'Second version')

    def test_editor_preview_does_not_save_and_slug_cannot_change_after_publication(self):
        self.publish()
        before = self.guide.published_revision_id
        payload = {
            'title': self.guide.title, 'slug': 'changed-url', 'summary': self.guide.summary,
            'category': self.category.pk, 'tags': '', 'content_markdown': '# Preview only',
            'assets': [], 'rooms': [], 'action': 'preview',
        }
        response = self.client.post(reverse('training:manage_guide_edit', args=(self.guide.pk,)), payload)
        self.assertContains(response, 'Preview only')
        self.guide.refresh_from_db()
        self.assertEqual(self.guide.published_revision_id, before)
        self.assertEqual(self.guide.slug, 'operate-sound-system')
        payload['action'] = 'save'
        invalid = self.client.post(reverse('training:manage_guide_edit', args=(self.guide.pk,)), payload)
        self.assertContains(invalid, 'A published guide URL is permanent')


class TrainingPublicAndSecurityTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(username='training-publisher', email='publisher@example.invalid', password='long-safe-password')
        self.category, _ = TrainingCategory.objects.get_or_create(
            slug='cameras-zoom',
            defaults={
                'name': 'Cameras and Zoom',
                'is_active': True,
            },
        )
        self.guide = TrainingGuide.objects.create(
            title='Camera quick start', slug='camera-quick-start', summary='Start a camera session.',
            content_markdown='# Camera steps\n\n1. Turn on the approved display.\n2. Select a preset.',
            category=self.category, status=TrainingGuide.PublicationStatus.DRAFT,
        )
        self.guide.status = TrainingGuide.PublicationStatus.IN_REVIEW
        self.guide.review_date = timezone.localdate()
        self.guide.save()
        publish_guide(self.guide, editor=self.admin)
        self.guide.refresh_from_db()

    def test_public_categories_search_and_related_guides(self):
        landing = self.client.get(reverse('training:index'))
        self.assertEqual(landing.status_code, 200)
        self.assertContains(landing, 'Cameras and Zoom')
        search = self.client.get(reverse('training:index'), {'q': 'preset'})
        self.assertContains(search, 'Camera quick start')
        category = self.client.get(reverse('training:category_detail', args=(self.category.slug,)))
        self.assertContains(category, 'Camera quick start')

    def test_markdown_formatting_is_preserved_and_unsafe_html_urls_and_embeds_are_removed(self):
        safe_html = render_markdown('## Heading\n\n**Bold** and `code`\n\n| A | B |\n|---|---|\n| 1 | 2 |')
        self.assertIn('<h2>Heading</h2>', safe_html)
        self.assertIn('<strong>Bold</strong>', safe_html)
        self.assertIn('<table>', safe_html)
        unsafe_html = render_markdown('<script>alert(1)</script>\n\n[bad](javascript:alert(1))\n\n<iframe src="https://example.invalid"></iframe>')
        self.assertNotIn('<script', unsafe_html.lower())
        self.assertNotIn('javascript:', unsafe_html.lower())
        self.assertNotIn('<iframe', unsafe_html.lower())

    def test_anonymous_users_cannot_open_editor_and_authenticated_users_need_permissions(self):
        edit_url = reverse('training:manage_guide_edit', args=(self.guide.pk,))
        self.assertEqual(self.client.get(edit_url).status_code, 302)
        User = get_user_model()
        ordinary = User.objects.create_user(username='ordinary-reader', password='long-safe-password')
        self.client.force_login(ordinary)
        self.assertEqual(self.client.get(reverse('training:manage_guides')).status_code, 403)
        self.assertEqual(self.client.post(reverse('training:manage_guide_publish', args=(self.guide.pk,)), {'confirm_publish': 'yes'}).status_code, 403)
        self.assertEqual(self.client.get(reverse('training:guide_detail', args=(self.guide.slug,))).status_code, 200)

    def test_draft_in_review_and_archived_guides_are_not_searchable_or_guessable(self):
        hidden = TrainingGuide.objects.create(title='Secret draft', slug='secret-draft', summary='Hidden summary', content_markdown='unique hidden phrase', category=self.category)
        self.assertEqual(self.client.get(reverse('training:guide_detail', args=(hidden.slug,))).status_code, 404)
        self.assertNotContains(self.client.get(reverse('training:index'), {'q': 'unique hidden phrase'}), 'Secret draft')
        self.guide.status = TrainingGuide.PublicationStatus.ARCHIVED
        self.guide.save()
        self.assertEqual(self.client.get(reverse('training:guide_detail', args=(self.guide.slug,))).status_code, 404)

    @override_settings(ROOT_URLCONF='config.training_urls', TRAINING_ONLY=True)
    def test_training_only_urlconf_excludes_editor_admin_inventory_and_login(self):
        with override_settings(ROOT_URLCONF='config.training_urls'):
            for path in ('/training/manage/guides/', '/admin/', '/inventory/', '/login/'):
                with self.subTest(path=path), self.assertRaises(Resolver404):
                    resolve(path, urlconf='config.training_urls')
            self.assertEqual(self.client.get(reverse('training:guide_detail', args=(self.guide.slug,), urlconf='config.training_urls')).status_code, 200)

    def test_asset_and_room_pages_link_only_published_guides_without_sensitive_inventory_fields(self):
        room = Room.objects.create(name='Cultural Hall', room_number='101')
        asset = Asset.objects.create(inventory_number='VID-090', name='PTZ Camera', room=room, serial_number='PRIVATE-SERIAL', notes='PRIVATE-NOTE')
        self.guide.assets.add(asset)
        self.guide.rooms.add(room)
        self.guide.status = TrainingGuide.PublicationStatus.IN_REVIEW
        self.guide.review_date = self.guide.published_revision.published_at.date()
        self.guide.save()
        publish_guide(self.guide, editor=self.admin)
        self.client.force_login(self.admin)
        asset_page = self.client.get(reverse('inventory:asset_detail', args=(asset.pk,)))
        room_page = self.client.get(reverse('inventory:room_detail', args=(room.pk,)))
        self.assertContains(asset_page, 'Camera quick start')
        self.assertContains(room_page, 'Camera quick start')
        self.client.logout()
        public_page = self.client.get(reverse('training:guide_detail', args=(self.guide.slug,)))
        self.assertContains(public_page, 'VID-090')
        self.assertNotContains(public_page, 'PRIVATE-SERIAL')
        self.assertNotContains(public_page, 'PRIVATE-NOTE')
        self.assertNotContains(public_page, f'/inventory/{asset.pk}/')

    def test_export_contains_published_public_content_only(self):
        draft = TrainingGuide.objects.create(title='Private draft', slug='private-draft', category=self.category, content_markdown='do not export')
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'catalog.json'
            call_command('export_training_catalog', output=str(output))
            data = json.loads(output.read_text(encoding='utf-8'))
        self.assertEqual([item['slug'] for item in data['guides']], [self.guide.slug])
        self.assertNotIn(draft.slug, [item['slug'] for item in data['guides']])
        self.assertIn(self.category.slug, [item['slug'] for item in data['categories']])
