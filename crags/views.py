from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Area, Crag


def crag_list(request):
    crags = Crag.objects.select_related("area").all()

    query = request.GET.get("q", "").strip()
    area_id = request.GET.get("area", "")
    min_rating = request.GET.get("rating", "")

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

    return render(
        request,
        "crags/crag_list.html",
        context,
    )

def crag_detail(request, pk):
    crag = get_object_or_404(
        Crag.objects.select_related("area").prefetch_related("photos"),
        pk=pk,
    )

    return render(
        request,
        "crags/crag_detail.html",
        {
            "crag": crag,
        },
    )