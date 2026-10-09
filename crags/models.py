from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
import uuid

def photo_upload_path(instance, filename):
    # Random name: the user's filename is never used
    return f"crags/{uuid.uuid4().hex}.webp"

class Area(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class CragQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Crag.Status.PUBLISHED)

    def public(self):
        return self.filter(status__in=Crag.PUBLIC_STATUSES)


class Crag(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING = "PENDING", "Pending review"
        PUBLISHED = "PUBLISHED", "Published"
        REJECTED = "REJECTED", "Rejected"
       # statuses that anonymous visitors may see
    PUBLIC_STATUSES = (Status.PUBLISHED, Status.PENDING)

    class Orientation(models.TextChoices):
        N = "N", "North"
        NE = "NE", "North-East"
        E = "E", "East"
        SE = "SE", "South-East"
        S = "S", "South"
        SW = "SW", "South-West"
        W = "W", "West"
        NW = "NW", "North-West"

    class ApproachCharacteristic(models.TextChoices):
        ROCKFALL = "ROCKFALL", "Steinschlaggefahr"
        FALL_HAZARD = "FALL_HAZARD", "Absturzgefahr"
        STROLLER_FRIENDLY = "STROLLER_FRIENDLY", "Kinderwagentauglich"
        PARTIALLY_STROLLER_FRIENDLY = (
            "PARTIALLY_STROLLER_FRIENDLY",
            "Teilweise kinderwagentauglich",
        )
        NOT_STROLLER_FRIENDLY = "NOT_STROLLER_FRIENDLY", "Nicht kinderwagentauglich"
        STROLLER_UNKNOWN = "STROLLER_UNKNOWN", "Kinderwagentauglichkeit unbekannt"

    name = models.CharField(max_length=160)

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

    approach_characteristics = models.JSONField(
        default=list,
        blank=True,
    )

    rating_babies = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
        null=True,
        blank=True,
    )

    rating_ages_2_4 = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
        null=True,
        blank=True,
    )

    rating_ages_5_plus = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
        null=True,
        blank=True,
    )

    guidebook = models.CharField(max_length=250, blank=True)

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )

    parking = models.TextField(blank=True)

    family_notes = models.TextField(blank=True)

    orientation = models.CharField(
        max_length=2,
        choices=Orientation.choices,
        blank=True,
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="crags",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CragQuerySet.as_manager()

    def clean(self):
        super().clean()
        characteristics = self.approach_characteristics
        allowed = {value for value, _ in self.ApproachCharacteristic.choices}
        if not isinstance(characteristics, list) or any(
            not isinstance(value, str) or value not in allowed
            for value in characteristics
        ):
            raise ValidationError(
                {"approach_characteristics": "Ungültige Merkmale des Zustiegs."}
            )
        if len(characteristics) != len(set(characteristics)):
            raise ValidationError(
                {"approach_characteristics": "Merkmale dürfen nicht doppelt vorkommen."}
            )

        stroller_options = {
            self.ApproachCharacteristic.STROLLER_FRIENDLY,
            self.ApproachCharacteristic.PARTIALLY_STROLLER_FRIENDLY,
            self.ApproachCharacteristic.NOT_STROLLER_FRIENDLY,
            self.ApproachCharacteristic.STROLLER_UNKNOWN,
        }
        if len(set(characteristics) & stroller_options) > 1:
            raise ValidationError(
                {
                    "approach_characteristics":
                        "Nur eine Angabe zur Kinderwagentauglichkeit auswählen."
                }
            )

        if (self.latitude is None) != (self.longitude is None):
            raise ValidationError("Breiten- und Längengrad müssen zusammen angegeben werden.")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_approach_characteristics_display(self):
        labels = dict(self.ApproachCharacteristic.choices)
        return [labels[value] for value in self.approach_characteristics if value in labels]


class Photo(models.Model):
    class Category(models.TextChoices):
        CRAG = "CRAG", "Fels"
        BASE_AREA = "BASE_AREA", "Platz am Wandfuß"
        APPROACH = "APPROACH", "Zustieg"
        PARKING = "PARKING", "Parkplatz"
        TERRAIN = "TERRAIN", "Umgebung"
        OTHER = "OTHER", "Sonstiges"

    crag = models.ForeignKey(
        Crag,
        on_delete=models.CASCADE,
        related_name="photos",
    )

    image = models.ImageField(upload_to=photo_upload_path)

    category = models.CharField(
        max_length=10,
        choices=Category.choices,
        default=Category.CRAG,
    )

    caption = models.CharField(max_length=250, blank=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="photos",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Photo of {self.crag.name}"