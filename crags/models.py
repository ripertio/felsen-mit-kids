from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Area(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Crag(models.Model):
    class StrollerFriendly(models.TextChoices):
        YES = "YES", "Yes"
        PARTIALLY = "PARTIALLY", "Partially"
        NO = "NO", "No"
        UNKNOWN = "UNKNOWN", "Unknown"

    class Orientation(models.TextChoices):
        N = "N", "North"
        NE = "NE", "North-East"
        E = "E", "East"
        SE = "SE", "South-East"
        S = "S", "South"
        SW = "SW", "South-West"
        W = "W", "West"
        NW = "NW", "North-West"

    name = models.CharField(max_length=200)

    area = models.ForeignKey(
        Area,
        on_delete=models.PROTECT,
        related_name="crags",
    )

    description = models.TextField(blank=True)

    approach_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    stroller_friendly = models.CharField(
        max_length=10,
        choices=StrollerFriendly.choices,
        default=StrollerFriendly.UNKNOWN,
    )

    family_rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
        null=True,
        blank=True,
    )

    family_notes = models.TextField(blank=True)

    orientation = models.CharField(
        max_length=2,
        choices=Orientation.choices,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Photo(models.Model):
    crag = models.ForeignKey(
        Crag,
        on_delete=models.CASCADE,
        related_name="photos",
    )

    image = models.ImageField(upload_to="crags/")

    caption = models.CharField(
        max_length=250,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo of {self.crag.name}"