'''Building room models'''
from django.db import models

class RoomPriority(models.TextChoices):
    '''Priority for assessing and supporting a room'''

    PRIORITY = 'priority', 'Priority'
    NORMAL = 'normal', 'Normal'
    LOW = 'low', 'Low'
    UNKNOWN = 'unknown', 'Unknown'

class Room(models.Model):
    '''A room or functional area within the building'''

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    room_number = models.CharField(
        max_length=30,
        blank=True,
    )

    priority = models.CharField(
        max_length=20,
        choices=RoomPriority.choices,
        default=RoomPriority.UNKNOWN,
    )

    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        '''Return the room name'''
        return self.name
