"""Create the starter training categories without overwriting local edits."""

from django.core.management.base import BaseCommand

from apps.training.models import TrainingCategory


STARTER_CATEGORIES = (
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


class Command(BaseCommand):
    help = 'Create the initial Meetinghouse Technology training guide categories.'

    def handle(self, *args, **options):
        created = 0
        for order, (name, slug, description) in enumerate(STARTER_CATEGORIES, 1):
            _, was_created = TrainingCategory.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'description': description, 'display_order': order, 'is_active': True},
            )
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f'Created {created} categories; existing categories were left unchanged.'))
