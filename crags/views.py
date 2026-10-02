from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CragForm
from .models import Area, Crag


def visible_crags(user):
    """Who may SEE which crags."""
    qs = Crag.objects.select_related("area")
    if user.is_staff:
        return qs
    if user.is_authenticated:
        return qs.filter(Q(status=Crag.Status.PUBLISHED) | Q(created_by=user))
    return qs.published()


def editable_crags(user):
    """Who may CHANGE which crags."""
    if user.is_staff:
        return Crag.objects.all()
    return Crag.objects.filter(created_by=user)


def crag_list(request):
    crags = Crag.objects.select_related("area").published()

    query = request.GET.get("q", "").strip()
    area_id = request.GET.get("area", "")
    min_rating = request.GET.get("rating", "")

    # Ignore non-numeric input instead of crashing
    if not area_id.isdecimal():
        area_id = ""
    if not min_rating.isdecimal():
        min_rating = ""

    if query:
        crags = crags.filter(
            Q(name__icontains=query)
            | Q(area__name__icontains=query)
            | Q(description__icontains=query)
        )

    if area_id:
        crags = crags.filter(area_id=area_id)

    if min_rating:
        crags = crags.filter(family_rating__gte=min_rating)

    crags = crags.order_by("name")
    areas = Area.objects.order_by("name")

    context = {
        "crags": crags,
        "areas": areas,
        "query": query,
        "selected_area": area_id,
        "selected_rating": min_rating,
    }
    return render(request, "crags/crag_list.html", context)


def crag_detail(request, pk):
    crag = get_object_or_404(
        visible_crags(request.user).prefetch_related("photos"),
        pk=pk,
    )
    can_edit = request.user.is_authenticated and (
        request.user.is_staff or crag.created_by_id == request.user.id
    )
    return render(
        request,
        "crags/crag_detail.html",
        {"crag": crag, "can_edit": can_edit},
    )


@login_required
def crag_mine(request):
    crags = (
        Crag.objects.filter(created_by=request.user)
        .select_related("area")
        .order_by("-updated_at")
    )
    return render(request, "crags/crag_mine.html", {"crags": crags})


@login_required
def crag_create(request):
    if request.method == "POST":
        form = CragForm(request.POST)
        if form.is_valid():
            crag = form.save(commit=False)
            crag.created_by = request.user
            if request.POST.get("action") == "submit":
                crag.status = Crag.Status.PENDING
                messages.success(request, "Eingereicht. Wir prüfen den Eintrag.")
            else:
                crag.status = Crag.Status.DRAFT
                messages.success(request, "Entwurf gespeichert.")
            crag.save()
            return redirect("crags:detail", pk=crag.pk)
    else:
        form = CragForm()

    return render(
        request,
        "crags/crag_form.html",
        {"form": form, "title": "Neuen Felsen eintragen", "note": ""},
    )


@login_required
def crag_edit(request, pk):
    crag = get_object_or_404(editable_crags(request.user), pk=pk)

    if request.method == "POST":
        form = CragForm(request.POST, instance=crag)
        if form.is_valid():
            crag = form.save(commit=False)
            if not request.user.is_staff:
                if request.POST.get("action") == "submit":
                    crag.status = Crag.Status.PENDING
                elif crag.status == Crag.Status.PUBLISHED:
                    # any change to a published crag needs a new review
                    crag.status = Crag.Status.PENDING
            crag.save()
            messages.success(request, "Gespeichert.")
            return redirect("crags:detail", pk=crag.pk)
    else:
        form = CragForm(instance=crag)

    note = ""
    if crag.status == Crag.Status.PUBLISHED and not request.user.is_staff:
        note = "Änderungen an veröffentlichten Felsen werden erneut geprüft."

    return render(
        request,
        "crags/crag_form.html",
        {"form": form, "title": f"{crag.name} bearbeiten", "note": note},
    )