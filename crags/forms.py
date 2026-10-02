from django import forms
import io

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import Area, Crag, Photo

MAX_UPLOAD_BYTES = 15 * 1024 * 1024   # 15 MB
MAX_PIXELS = 60_000_000               # protects against decompression bombs
MAX_EDGE = 1600                       # longest side after resize
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "MPO"}  # HEIC is converted to JPEG by iOS before upload


class PhotoForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = ["image", "category", "caption"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hint for the phone's file picker; iPhones convert HEIC to JPEG for this
        self.fields["image"].widget.attrs["accept"] = "image/jpeg,image/png,image/webp"

    def clean_image(self):
        upload = self.cleaned_data["image"]

        if upload.size > MAX_UPLOAD_BYTES:
            raise ValidationError("Das Bild ist zu groß (maximal 15 MB).")

        try:
            img = Image.open(upload)
            if img.format not in ALLOWED_FORMATS:
                raise ValidationError("Bitte ein JPG-, PNG- oder WebP-Bild hochladen.")
            if img.width * img.height > MAX_PIXELS:
                raise ValidationError("Das Bild hat zu viele Pixel.")

            img = ImageOps.exif_transpose(img)  # apply rotation BEFORE dropping EXIF
            img = img.convert("RGB")
            img.thumbnail((MAX_EDGE, MAX_EDGE))

            buffer = io.BytesIO()
            img.save(buffer, format="WEBP", quality=80, method=4)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise ValidationError("Die Datei konnte nicht als Bild gelesen werden.")

        # The filename is replaced by photo_upload_path on save
        return ContentFile(buffer.getvalue(), name="photo.webp")


class CragForm(forms.ModelForm):
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
        "description",
        "approach_minutes",
        "stroller_friendly",
        "family_rating",
        "family_notes",
        "orientation",
    ]

    class Meta:
        model = Crag
        fields = [
            "name",
            "area",
            "description",
            "approach_minutes",
            "stroller_friendly",
            "family_rating",
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