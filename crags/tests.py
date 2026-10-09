import io
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Area, Crag, Photo

User = get_user_model()


def form_data(base_area, **overrides):
    data = {
        "name": "Testfels",
        "area": base_area.pk,
        "new_area": "",
        "description": "",
        "approach_minutes": "",
        "approach_characteristics": [],
        "rating_babies": "",
        "rating_ages_2_4": "",
        "rating_ages_5_plus": "",
        "guidebook": "",
        "latitude": "",
        "longitude": "",
        "parking": "",
        "family_notes": "",
        "orientation": "",
        "action": "draft",
    }
    data.update(overrides)
    return data


def image_upload(name):
    image_buffer = io.BytesIO()
    Image.new("RGB", (32, 24), "red").save(image_buffer, format="JPEG")
    return SimpleUploadedFile(name, image_buffer.getvalue(), content_type="image/jpeg")


class CragTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.area = Area.objects.create(name="Allgäu")
        cls.alice = User.objects.create_user("alice", "alice@example.com", "pw-alice-123")
        cls.bob = User.objects.create_user("bob", "bob@example.com", "pw-bob-123")
        cls.staff = User.objects.create_user(
            "staff", "staff@example.com", "pw-staff-123", is_staff=True
        )

        cls.published = Crag.objects.create(
            name="Öffentlich", area=cls.area, created_by=cls.alice,
            status=Crag.Status.PUBLISHED,
        )
        cls.draft = Crag.objects.create(
            name="Entwurf", area=cls.area, created_by=cls.alice,
            status=Crag.Status.DRAFT,
        )
        cls.pending = Crag.objects.create(
            name="Wartend", area=cls.area, created_by=cls.alice,
            status=Crag.Status.PENDING,
        )


class PublicVisibilityTests(CragTestBase):
    def test_homepage_displays_crag_list(self):
        resp = self.client.get("/")

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "crags/crag_list.html")
        self.assertContains(resp, "Öffentlich")

    def test_list_shows_published_and_pending_but_not_drafts(self):
        resp = self.client.get(reverse("crags:list"))
        self.assertContains(resp, "Öffentlich")
        self.assertContains(resp, "Wartend")
        self.assertNotContains(resp, "Entwurf")

    def test_rejected_crag_is_hidden_from_public(self):
        rejected = Crag.objects.create(
            name="Abgelehnt", area=self.area, created_by=self.alice,
            status=Crag.Status.REJECTED,
        )
        self.assertNotContains(self.client.get(reverse("crags:list")), "Abgelehnt")
        resp = self.client.get(reverse("crags:detail", args=[rejected.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_anonymous_can_open_pending_detail(self):
        resp = self.client.get(reverse("crags:detail", args=[self.pending.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_list_ignores_bad_filter_input(self):
        resp = self.client.get(reverse("crags:list"), {"rating": "abc", "area": "xyz"})
        self.assertEqual(resp.status_code, 200)

    def test_rating_filter_matches_any_age_group(self):
        self.pending.rating_ages_2_4 = 4
        self.pending.save()

        response = self.client.get(reverse("crags:list"), {"rating": "4"})

        self.assertContains(response, "Wartend")
        self.assertNotContains(response, "Öffentlich")

    def test_list_filters_by_area_name(self):
        other_area = Area.objects.create(name="Tannheimer Tal")
        Crag.objects.create(
            name="Anderer Fels",
            area=other_area,
            created_by=self.alice,
            status=Crag.Status.PUBLISHED,
        )

        resp = self.client.get(reverse("crags:list"), {"area": self.area.name})

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Öffentlich")
        self.assertNotContains(resp, "Anderer Fels")
        self.assertEqual(resp.context["selected_area"], self.area.name)
        self.assertContains(resp, f'value="{self.area.name}"')

    def test_anonymous_can_open_published_detail(self):
        resp = self.client.get(reverse("crags:detail", args=[self.published.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_anonymous_gets_404_for_draft(self):
        resp = self.client.get(reverse("crags:detail", args=[self.draft.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_other_user_gets_404_for_foreign_draft(self):
        self.client.force_login(self.bob)
        resp = self.client.get(reverse("crags:detail", args=[self.draft.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_owner_can_see_own_draft(self):
        self.client.force_login(self.alice)
        resp = self.client.get(reverse("crags:detail", args=[self.draft.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_staff_can_see_any_draft(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse("crags:detail", args=[self.draft.pk]))
        self.assertEqual(resp.status_code, 200)


class LoginRequiredTests(CragTestBase):
    def test_anonymous_is_redirected_from_protected_pages(self):
        urls = [
            reverse("crags:create"),
            reverse("crags:mine"),
            reverse("crags:edit", args=[self.published.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 302)
                self.assertIn("/accounts/login/", resp["Location"])


class EditPermissionTests(CragTestBase):
    def test_other_user_cannot_open_edit_page(self):
        self.client.force_login(self.bob)
        resp = self.client.get(reverse("crags:edit", args=[self.published.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_other_user_cannot_post_edit(self):
        self.client.force_login(self.bob)
        resp = self.client.post(
            reverse("crags:edit", args=[self.published.pk]),
            form_data(self.area, name="Gehackt"),
        )
        self.assertEqual(resp.status_code, 404)
        self.published.refresh_from_db()
        self.assertEqual(self.published.name, "Öffentlich")

    def test_owner_can_edit_own_crag(self):
        self.client.force_login(self.alice)
        resp = self.client.post(
            reverse("crags:edit", args=[self.draft.pk]),
            form_data(self.area, name="Umbenannt"),
        )
        self.assertEqual(resp.status_code, 302)
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.name, "Umbenannt")

    def test_staff_can_edit_any_crag(self):
        self.client.force_login(self.staff)
        resp = self.client.post(
            reverse("crags:edit", args=[self.published.pk]),
            form_data(self.area, name="Korrigiert"),
        )
        self.assertEqual(resp.status_code, 302)
        self.published.refresh_from_db()
        self.assertEqual(self.published.name, "Korrigiert")
        # staff edits do not change the status
        self.assertEqual(self.published.status, Crag.Status.PUBLISHED)

    def test_editing_published_crag_requires_new_review(self):
        self.client.force_login(self.alice)
        self.client.post(
            reverse("crags:edit", args=[self.published.pk]),
            form_data(self.area, name="Geändert"),
        )
        self.published.refresh_from_db()
        self.assertEqual(self.published.status, Crag.Status.PENDING)


class CreateTests(CragTestBase):
    def test_create_draft_sets_owner_and_status(self):
        self.client.force_login(self.bob)
        self.client.post(reverse("crags:create"), form_data(self.area, name="Bobs Fels"))
        crag = Crag.objects.get(name="Bobs Fels")
        self.assertEqual(crag.created_by, self.bob)
        self.assertEqual(crag.status, Crag.Status.DRAFT)

    def test_submit_sets_pending(self):
        self.client.force_login(self.bob)
        self.client.post(
            reverse("crags:create"),
            form_data(self.area, name="Bobs Fels", action="submit"),
        )
        self.assertEqual(Crag.objects.get(name="Bobs Fels").status, Crag.Status.PENDING)

    def test_user_cannot_inject_status_or_owner(self):
        self.client.force_login(self.bob)
        self.client.post(
            reverse("crags:create"),
            form_data(
                self.area,
                name="Schummler",
                status="PUBLISHED",
                created_by=self.alice.pk,
            ),
        )
        crag = Crag.objects.get(name="Schummler")
        self.assertEqual(crag.status, Crag.Status.DRAFT)
        self.assertEqual(crag.created_by, self.bob)

    def test_create_form_includes_optional_photo_upload(self):
        self.client.force_login(self.bob)
        response = self.client.get(reverse("crags:create"))

        self.assertContains(response, 'name="images"')
        self.assertContains(response, "Fotos hinzufügen (optional)")
        self.assertContains(response, '<select name="rating_babies"')
        self.assertContains(response, "Bewertung für Babys")
        self.assertContains(response, "Teilweise kinderwagentauglich")
        self.assertContains(response, "Aktuellen Standort verwenden")
        self.assertContains(response, 'data-location-status role="status"')

    def test_age_ratings_save_selected_values(self):
        self.client.force_login(self.bob)
        self.client.post(
            reverse("crags:create"),
            form_data(
                self.area,
                name="Bewerteter Fels",
                rating_babies="2",
                rating_ages_2_4="3",
                rating_ages_5_plus="4",
            ),
        )

        crag = Crag.objects.get(name="Bewerteter Fels")
        self.assertEqual(crag.rating_babies, 2)
        self.assertEqual(crag.rating_ages_2_4, 3)
        self.assertEqual(crag.rating_ages_5_plus, 4)

    def test_approach_characteristics_support_partial_stroller_access(self):
        self.client.force_login(self.bob)
        self.client.post(
            reverse("crags:create"),
            form_data(
                self.area,
                name="Teilweise erreichbar",
                approach_characteristics=[
                    Crag.ApproachCharacteristic.ROCKFALL,
                    Crag.ApproachCharacteristic.PARTIALLY_STROLLER_FRIENDLY,
                ],
                guidebook="Kletterführer Allgäu",
                latitude="47.123456",
                longitude="10.654321",
                parking="Parkplatz am Ortsrand",
            ),
        )

        crag = Crag.objects.get(name="Teilweise erreichbar")
        self.assertEqual(
            crag.approach_characteristics,
            ["ROCKFALL", "PARTIALLY_STROLLER_FRIENDLY"],
        )
        self.assertEqual(crag.guidebook, "Kletterführer Allgäu")
        self.assertEqual(str(crag.latitude), "47.123456")
        self.assertEqual(str(crag.longitude), "10.654321")
        self.assertEqual(crag.parking, "Parkplatz am Ortsrand")

    def test_stroller_characteristics_are_mutually_exclusive(self):
        self.client.force_login(self.bob)
        response = self.client.post(
            reverse("crags:create"),
            form_data(
                self.area,
                name="Widersprüchliche Angaben",
                approach_characteristics=[
                    Crag.ApproachCharacteristic.STROLLER_FRIENDLY,
                    Crag.ApproachCharacteristic.PARTIALLY_STROLLER_FRIENDLY,
                ],
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Crag.objects.filter(name="Widersprüchliche Angaben").exists())
        self.assertContains(
            response,
            "Bitte nur eine Angabe zur Kinderwagentauglichkeit auswählen.",
        )

    def test_coordinates_must_be_provided_as_a_pair(self):
        self.client.force_login(self.bob)
        response = self.client.post(
            reverse("crags:create"),
            form_data(
                self.area,
                name="Unvollständige Koordinaten",
                latitude="47.123456",
                longitude="",
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Crag.objects.filter(name="Unvollständige Koordinaten").exists())
        self.assertContains(response, "Bitte beide Koordinaten oder keine Koordinaten angeben.")

    def test_create_crag_with_multiple_photos(self):
        self.client.force_login(self.bob)
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    reverse("crags:create"),
                    {
                        **form_data(self.area, name="Fels mit Fotos"),
                        "category": Photo.Category.PARKING,
                        "images": [image_upload("first.jpg"), image_upload("second.jpg")],
                    },
                )

        crag = Crag.objects.get(name="Fels mit Fotos")
        self.assertRedirects(response, reverse("crags:detail", args=[crag.pk]))
        photos = Photo.objects.filter(crag=crag)
        self.assertEqual(photos.count(), 2)
        self.assertEqual(
            set(photos.values_list("category", flat=True)),
            {Photo.Category.PARKING},
        )
        self.assertTrue(all(photo.image.name.endswith(".webp") for photo in photos))

    def test_invalid_photo_prevents_crag_creation(self):
        self.client.force_login(self.bob)
        response = self.client.post(
            reverse("crags:create"),
            {
                **form_data(self.area, name="Ungültiges Foto"),
                "category": Photo.Category.CRAG,
                "images": [
                    SimpleUploadedFile(
                        "not-an-image.jpg", b"not an image", content_type="image/jpeg"
                    )
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Crag.objects.filter(name="Ungültiges Foto").exists())
        self.assertContains(response, "Die Datei konnte nicht als Bild gelesen werden.")


class NewAreaTests(CragTestBase):
    def setUp(self):
        self.client.force_login(self.bob)

    def test_new_area_is_created(self):
        self.client.post(
            reverse("crags:create"),
            form_data(self.area, name="Neu", area="", new_area="Tannheimer Tal"),
        )
        self.assertEqual(Crag.objects.get(name="Neu").area.name, "Tannheimer Tal")

    def test_new_area_reuses_existing_name_case_insensitive(self):
        self.client.post(
            reverse("crags:create"),
            form_data(self.area, name="Neu", area="", new_area="  allgäu "),
        )
        self.assertEqual(Area.objects.filter(name__iexact="allgäu").count(), 1)
        self.assertEqual(Crag.objects.get(name="Neu").area, self.area)

    def test_both_empty_is_rejected(self):
        resp = self.client.post(
            reverse("crags:create"),
            form_data(self.area, name="Neu", area="", new_area=""),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Crag.objects.filter(name="Neu").exists())

    def test_both_filled_is_rejected(self):
        resp = self.client.post(
            reverse("crags:create"),
            form_data(self.area, name="Neu", new_area="Anderes Gebiet"),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Crag.objects.filter(name="Neu").exists())


class PhotoUploadTests(CragTestBase):
    def test_crag_detail_renders_gallery_with_direct_image_fallback(self):
        self.client.force_login(self.alice)
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                photo = Photo.objects.create(
                    crag=self.draft,
                    image=image_upload("gallery.jpg"),
                    category=Photo.Category.CRAG,
                    uploaded_by=self.alice,
                )
                response = self.client.get(reverse("crags:detail", args=[self.draft.pk]))

        self.assertContains(response, 'class="gallery-trigger"')
        self.assertContains(response, 'href="/media/%s"' % photo.image.name)
        self.assertContains(response, 'dialog class="photo-gallery"')
        self.assertContains(response, "data-gallery-next")
        self.assertContains(response, "/static/js/photo-gallery.")

    def test_owner_can_upload_multiple_photos(self):
        image_buffer = io.BytesIO()
        Image.new("RGB", (32, 24), "red").save(image_buffer, format="JPEG")
        image_bytes = image_buffer.getvalue()

        self.client.force_login(self.alice)
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    reverse("crags:photo_add", args=[self.draft.pk]),
                    {
                        "category": Photo.Category.CRAG,
                        "images": [
                            SimpleUploadedFile(
                                "first.jpg", image_bytes, content_type="image/jpeg"
                            ),
                            SimpleUploadedFile(
                                "second.jpg", image_bytes, content_type="image/jpeg"
                            ),
                        ],
                    },
                )

        self.assertRedirects(response, reverse("crags:detail", args=[self.draft.pk]))
        photos = Photo.objects.filter(crag=self.draft).order_by("pk")
        self.assertEqual(photos.count(), 2)
        self.assertTrue(all(photo.image.name.endswith(".webp") for photo in photos))