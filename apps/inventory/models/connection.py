"""Physical connections between inventory assets"""

from django.db import models


class ConnectionType(models.TextChoices):
    """Purpose of the connection"""

    AUDIO = "audio", "Audio"
    CONTROL = "control", "Control"
    NETWORK = "network", "Network"
    POWER = "power", "Power"
    VIDEO = "video", "Video"
    OTHER = "other", "Other"


class ConnectionMedium(models.TextChoices):
    """Physical or wireless connection medium"""

    DISPLAYPORT = "displayport", "DisplayPort"
    ETHERNET = "ethernet", "Ethernet"
    HDMI = "hdmi", "HDMI"
    RF = "rf", "Radio Frequency"
    USB = "usb", "USB"
    WIRELESS = "wireless", "Wireless"
    XLR = "xlr", "XLR"
    OTHER = "other", "Other"


class CompatibilityStatus(models.TextChoices):
    """Verification status of a connection"""

    VERIFIED = "verified", "Verified"
    UNVERIFIED = "unverified", "Not Yet Verified"
    INCOMPATIBLE = "incompatible", "Incompatible"
    UNKNOWN = "unknown", "Unknown"


class AssetConnection(models.Model):
    """A connection from one asset to another"""

    source = models.ForeignKey(
        "inventory.Asset",
        on_delete=models.PROTECT,
        related_name="outgoing_connections",
    )

    destination = models.ForeignKey(
        "inventory.Asset",
        on_delete=models.PROTECT,
        related_name="incoming_connections",
    )

    connection_type = models.CharField(
        max_length=20,
        choices=ConnectionType.choices,
        default=ConnectionType.OTHER,
    )

    connection_medium = models.CharField(
        max_length=20,
        choices=ConnectionMedium.choices,
        default=ConnectionMedium.OTHER,
    )

    interface = models.CharField(
        max_length=100,
        blank=True,
    )

    signal_description = models.CharField(
        max_length=200,
        blank=True,
    )

    compatibility = models.CharField(
        max_length=20,
        choices=CompatibilityStatus.choices,
        default=CompatibilityStatus.UNKNOWN,
    )

    is_required = models.BooleanField(default=True)

    last_verified = models.DateField(
        null=True,
        blank=True,
    )

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["source__inventory_number", "destination__inventory_number"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "source",
                    "destination",
                    "connection_type",
                    "connection_medium",
                ],
                name="unique_asset_connection",
            ),
        ]

    def __str__(self) -> str:
        """Describe the connection"""
        return f"{self.source.inventory_number} → {self.destination.inventory_number}"
