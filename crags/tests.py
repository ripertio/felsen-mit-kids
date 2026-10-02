from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Area, Crag

User = get_user_model()


def form_data(base_area, **overrides):
    data = {
        "name": "Testfels",
        "area": base_area.pk,
        "new_area": "",
        "description": "",
        "approach_minutes": "",
        "stroller_friendly": "UNKNOWN",
        "family_rating": "",
        "family_notes": "",
        "orientation": "",
        "action": "draft",
    }
    data.update(overrides)
    return data


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