"""Persistent, user-owned drafts for guided asset entry."""

import uuid

from django.conf import settings
from django.db import models


class AssetDraft(models.Model):
    """Incomplete equipment entry kept separate from saved inventory."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="inventory_asset_drafts",
    )
    draft_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)

    def __str__(self):
        return f"Equipment draft {self.id} ({self.created_by})"
