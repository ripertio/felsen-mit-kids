from django import forms

from .models import Area, Crag


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