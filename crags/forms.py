from django import forms
import io

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError
import pillow_heif

from .models import Area, Crag, Photo

pillow_heif.register_heif_opener()

MAX_UPLOAD_BYTES = 15 * 1024 * 1024   # 15 MB
MAX_PIXELS = 60_000_000               # protects against decompression bombs
MAX_EDGE = 1600                       # longest side after resize
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "MPO", "HEIF"}
RATING_CHOICES = [
    ("", "– bitte wählen –"),
    (1, "★ 1/5"),
    (2, "★ 2/5"),
    (3, "★ 3/5"),
    (4, "★ 4/5"),
    (5, "★ 5/5"),
]


def process_image(upload):
    """Validate an upload and return it as a resized WEBP ContentFile."""
    if upload.size > MAX_UPLOAD_BYTES:
        raise ValidationError("Das Bild ist zu groß (maximal 15 MB).")

    try:
        upload.seek(0)
        img = Image.open(upload)
        if img.format not in ALLOWED_FORMATS:
            raise ValidationError(
                "Bitte ein JPG-, PNG-, WebP- oder HEIC-Bild hochladen."
            )
        if img.width * img.height > MAX_PIXELS:
            raise ValidationError("Das Bild hat zu viele Pixel.")

        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        img.thumbnail((MAX_EDGE, MAX_EDGE))

        buffer = io.BytesIO()
        img.save(buffer, format="WEBP", quality=80, method=4)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValidationError("Die Datei konnte nicht als Bild gelesen werden.")

    return ContentFile(buffer.getvalue(), name="photo.webp")


class BulkPhotoForm(forms.Form):
    category = forms.ChoiceField(
        choices=Photo.Category.choices,
        initial=Photo.Category.CRAG,
        label="Kategorie",
    )


class CragForm(forms.ModelForm):
    guidebook = forms.CharField(
        max_length=250, required=False, label="Kletterführer"
    )
    latitude = forms.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=-90,
        max_value=90,
        required=False,
        label="Breitengrad",
    )
    longitude = forms.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=-180,
        max_value=180,
        required=False,
        label="Längengrad",
    )
    parking = forms.CharField(
        required=False,
        widget=forms.Textarea,
        label="Parken",
        help_text="Parkplatzbeschreibung oder Kartenlink.",
    )
    rating_babies = forms.TypedChoiceField(
        choices=RATING_CHOICES, coerce=int, empty_value=None, required=False,
        label="Bewertung für Babys (0–1 Jahr)",
    )
    rating_ages_2_4 = forms.TypedChoiceField(
        choices=RATING_CHOICES, coerce=int, empty_value=None, required=False,
        label="Bewertung für Kinder (2–4 Jahre)",
    )
    rating_ages_5_plus = forms.TypedChoiceField(
        choices=RATING_CHOICES, coerce=int, empty_value=None, required=False,
        label="Bewertung für Kinder ab 5 Jahren",
    )
    approach_characteristics = forms.MultipleChoiceField(
        choices=Crag.ApproachCharacteristic.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Merkmale des Zustiegs",
    )
    new_area = forms.CharField(
        max_length=200,
        required=False,
        label="Oder neues Gebiet",
        help_text="Nur ausfüllen, wenn das Gebiet oben nicht in der Liste ist.",
    )

    field_order = [
        "name",
        "area",
        "new_area",
        "guidebook",
        "description",
        "approach_minutes",
        "approach_characteristics",
        "rating_babies",
        "rating_ages_2_4",
        "rating_ages_5_plus",
        "latitude",
        "longitude",
        "parking",
        "family_notes",
        "orientation",
    ]

    class Meta:
        model = Crag
        fields = [
            "name",
            "area",
            "guidebook",
            "description",
            "approach_minutes",
            "approach_characteristics",
            "rating_babies",
            "rating_ages_2_4",
            "rating_ages_5_plus",
            "latitude",
            "longitude",
            "parking",
            "family_notes",
            "orientation",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._new_area_name = ""
        # Either the dropdown or the text field is enough, so neither is required alone.
        # The clean() method below enforces "exactly one of them".
        self.fields["area"].required = False
        self.fields["area"].empty_label = "– bitte wählen –"

    def clean(self):
        cleaned = super().clean()
        characteristics = set(cleaned.get("approach_characteristics") or [])
        stroller_options = {
            Crag.ApproachCharacteristic.STROLLER_FRIENDLY,
            Crag.ApproachCharacteristic.PARTIALLY_STROLLER_FRIENDLY,
            Crag.ApproachCharacteristic.NOT_STROLLER_FRIENDLY,
            Crag.ApproachCharacteristic.STROLLER_UNKNOWN,
        }
        selected_stroller_options = characteristics & stroller_options
        if len(selected_stroller_options) > 1:
            self.add_error(
                "approach_characteristics",
                "Bitte nur eine Angabe zur Kinderwagentauglichkeit auswählen.",
            )

        latitude = cleaned.get("latitude")
        longitude = cleaned.get("longitude")
        if (latitude is None) != (longitude is None):
            message = "Bitte beide Koordinaten oder keine Koordinaten angeben."
            self.add_error("latitude", message)
            self.add_error("longitude", message)

        # collapse repeated spaces: "Neue   Wand" -> "Neue Wand"
        self._new_area_name = " ".join((cleaned.get("new_area") or "").split())
        area = cleaned.get("area")

        if self._new_area_name and area:
            self.add_error(
                "new_area",
                "Bitte entweder ein Gebiet auswählen oder ein neues eintragen, nicht beides.",
            )
        elif not self._new_area_name and not area:
            self.add_error(
                "area",
                "Bitte ein Gebiet auswählen oder ein neues eintragen.",
            )
        return cleaned

    def save(self, commit=True):
        crag = super().save(commit=False)

        if self._new_area_name:
            area = Area.objects.filter(name__iexact=self._new_area_name).first()
            if area is None:
                area = Area.objects.create(name=self._new_area_name)
            crag.area = area

        if commit:
            crag.save()
        return crag