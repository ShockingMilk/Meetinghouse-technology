from django.test import TestCase

from apps.inventory.guided_views import draft_from_asset
from apps.inventory.models import Asset, AssetConnection


class AssetDraftConnectionsTests(TestCase):
    def setUp(self):
        self.source = Asset.objects.create(
            inventory_number="A-001",
            name="Source Equipment",
        )

        self.destination_one = Asset.objects.create(
            inventory_number="A-002",
            name="Destination One",
        )

        self.destination_two = Asset.objects.create(
            inventory_number="A-003",
            name="Destination Two",
        )

        self.incoming_source = Asset.objects.create(
            inventory_number="A-004",
            name="Incoming Source",
        )

        # Connections originating from the asset being edited.
        AssetConnection.objects.create(
            source=self.source,
            destination=self.destination_one,
        )

        AssetConnection.objects.create(
            source=self.source,
            destination=self.destination_two,
        )

        # A connection pointing into the asset being edited.
        AssetConnection.objects.create(
            source=self.incoming_source,
            destination=self.source,
        )

    def test_draft_includes_existing_outgoing_connections(self):
        draft = draft_from_asset(self.source)

        self.assertEqual(
            set(draft["connected_assets"]),
            {
                self.destination_one.pk,
                self.destination_two.pk,
            },
        )

    def test_draft_does_not_include_incoming_connections(self):
        draft = draft_from_asset(self.source)

        self.assertNotIn(
            self.incoming_source.pk,
            draft["connected_assets"],
        )

    def test_draft_stores_connection_ids_as_a_list(self):
        draft = draft_from_asset(self.source)

        self.assertIsInstance(draft["connected_assets"], list)
