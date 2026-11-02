"""Authenticated management screens for equipment relationships."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .models import (
    Asset, AssetConnection, AssetDependency, AssetSpecification,
    CompatibilityVerification, ReplacementCompatibilityReview,
    Room,
)
from .relationship_forms import (
    AssetConnectionForm, AssetDependencyForm, AssetSpecificationForm,
    CompatibilityVerificationForm, ReplacementReviewForm,
)
from .services.relationships import existing_dependency_cycles, replacement_impact

FORM_TYPES = {
    'connection': (AssetConnection, AssetConnectionForm),
    'dependency': (AssetDependency, AssetDependencyForm),
    'specification': (AssetSpecification, AssetSpecificationForm),
    'verification': (CompatibilityVerification, CompatibilityVerificationForm),
}


@login_required
def relationship_index(request):
    """Search connections and compatibility records across the building."""
    query = request.GET.get('q', '').strip()
    room = request.GET.get('room', '').strip()
    category = request.GET.get('category', '').strip()
    ownership = request.GET.get('ownership', '').strip()
    connection_type = request.GET.get('connection_type', '').strip()
    compatibility = request.GET.get('compatibility', '').strip()
    dependency_status = request.GET.get('dependency_status', '').strip()

    connections = AssetConnection.objects.select_related('source', 'source__room', 'destination', 'destination__room')
    dependencies = AssetDependency.objects.select_related('dependent_asset', 'dependent_asset__room', 'required_asset', 'required_asset__room', 'required_software', 'required_software__host_asset', 'required_software__host_asset__room')
    verifications = CompatibilityVerification.objects.select_related('asset', 'related_asset', 'connection')
    assets = Asset.objects.select_related('room')
    if query:
        text_filter = Q(source__name__icontains=query) | Q(source__inventory_number__icontains=query) | Q(destination__name__icontains=query) | Q(destination__inventory_number__icontains=query)
        connections = connections.filter(text_filter)
        dependencies = dependencies.filter(Q(dependent_asset__name__icontains=query) | Q(dependent_asset__inventory_number__icontains=query) | Q(required_asset__name__icontains=query) | Q(required_asset__inventory_number__icontains=query) | Q(required_software__name__icontains=query) | Q(required_software__host_asset__inventory_number__icontains=query) | Q(external_service_name__icontains=query))
        assets = assets.filter(Q(name__icontains=query) | Q(inventory_number__icontains=query))
        verifications = verifications.filter(Q(asset__name__icontains=query) | Q(asset__inventory_number__icontains=query) | Q(requirement__icontains=query) | Q(proposed_replacement__icontains=query))
    if room.isdigit():
        connections = connections.filter(Q(source__room_id=room) | Q(destination__room_id=room))
        dependencies = dependencies.filter(Q(dependent_asset__room_id=room) | Q(required_asset__room_id=room) | Q(required_software__host_asset__room_id=room))
        assets = assets.filter(room_id=room)
        verifications = verifications.filter(Q(asset__room_id=room) | Q(related_asset__room_id=room))
    if category:
        connections = connections.filter(Q(source__category=category) | Q(destination__category=category))
        dependencies = dependencies.filter(Q(dependent_asset__category=category) | Q(required_asset__category=category) | Q(required_software__host_asset__category=category))
        assets = assets.filter(category=category)
        verifications = verifications.filter(Q(asset__category=category) | Q(related_asset__category=category))
    if ownership:
        connections = connections.filter(Q(source__ownership=ownership) | Q(destination__ownership=ownership))
        dependencies = dependencies.filter(Q(dependent_asset__ownership=ownership) | Q(required_asset__ownership=ownership) | Q(required_software__host_asset__ownership=ownership))
        assets = assets.filter(ownership=ownership)
        verifications = verifications.filter(Q(asset__ownership=ownership) | Q(related_asset__ownership=ownership))
    if connection_type:
        connections = connections.filter(connection_type=connection_type)
    if compatibility:
        connections = connections.filter(compatibility=compatibility)
        verifications = verifications.filter(outcome=compatibility)
    if dependency_status:
        dependencies = dependencies.filter(verification_status=dependency_status)

    # Keep this building-wide review queue independent of relationship filters:
    # cross-room assets can still have gaps worth filling during a room review.
    missing_specifications = Asset.objects.select_related('room').exclude(specifications__isnull=False)
    missing_specifications = missing_specifications.distinct()
    awaiting_reviews = ReplacementCompatibilityReview.objects.select_related('asset').exclude(status__in=('compatible', 'limited', 'incompatible'))
    if room.isdigit():
        awaiting_reviews = awaiting_reviews.filter(asset__room_id=room)
    if category:
        awaiting_reviews = awaiting_reviews.filter(asset__category=category)
    if ownership:
        awaiting_reviews = awaiting_reviews.filter(asset__ownership=ownership)
    cycle_ids = existing_dependency_cycles()
    cycle_assets = {asset.pk: asset for asset in Asset.objects.filter(pk__in={item for cycle in cycle_ids for item in cycle})}
    dependency_cycles = [[cycle_assets[item] for item in cycle if item in cycle_assets] for cycle in cycle_ids]
    return render(request, 'inventory/relationship_index.html', {
        'connections': connections,
        'dependencies': dependencies,
        'verifications': verifications,
        'missing_specifications': missing_specifications,
        'awaiting_reviews': awaiting_reviews,
        'dependency_cycles': dependency_cycles,
        'rooms': Room.objects.order_by('name'),
        'categories': Asset._meta.get_field('category').choices,
        'ownership_choices': Asset._meta.get_field('ownership').choices,
        'connection_types': AssetConnection._meta.get_field('connection_type').choices,
        'compatibility_choices': AssetConnection._meta.get_field('compatibility').choices,
        'dependency_choices': AssetDependency._meta.get_field('verification_status').choices,
        'filters': {'q': query, 'room': room, 'category': category, 'ownership': ownership, 'connection_type': connection_type, 'compatibility': compatibility, 'dependency_status': dependency_status},
    })


@login_required
def relationship_form(request, kind, pk=None, asset_pk=None):
    """Create or edit one relationship record through a constrained form map."""
    if kind == 'review':
        asset = get_object_or_404(Asset, pk=asset_pk or pk)
        instance = ReplacementCompatibilityReview.objects.filter(asset=asset).first()
        form = ReplacementReviewForm(request.POST or None, instance=instance)
        if request.method == 'POST' and form.is_valid():
            review = form.save(commit=False)
            review.asset = asset
            review.save()
            messages.success(request, 'Replacement compatibility review saved. This does not approve a purchase or change inventory status.')
            return redirect('inventory:asset_detail', pk=asset.pk)
        return render(request, 'inventory/relationship_form.html', {'form': form, 'title': 'Replacement compatibility review', 'asset': asset})

    model, form_class = FORM_TYPES.get(kind, (None, None))
    if not model:
        return redirect('inventory:relationship_index')
    instance = get_object_or_404(model, pk=pk) if pk else None
    asset = get_object_or_404(Asset, pk=asset_pk) if asset_pk else None
    if kind == 'specification':
        form = form_class(request.POST or None, instance=instance, asset=asset)
    elif kind == 'verification':
        form = form_class(request.POST or None, instance=instance, asset=asset)
    else:
        form = form_class(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        item = form.save()
        messages.success(request, f'{kind.title()} saved.')
        item_asset_id = asset.pk if asset else (
            getattr(item, 'asset_id', None)
            or getattr(item, 'dependent_asset_id', None)
            or getattr(item, 'source_id', None)
        )
        return redirect('inventory:asset_detail', pk=item_asset_id) if item_asset_id else redirect('inventory:relationship_index')
    return render(request, 'inventory/relationship_form.html', {
        'form': form,
        'title': f'{"Edit" if instance else "Add"} {kind.replace("_", " ").title()}',
        'asset': asset,
        'kind': kind,
    })


@login_required
def replacement_review(request, asset_pk):
    asset = get_object_or_404(Asset.objects.select_related('room'), pk=asset_pk)
    impact = replacement_impact(asset)
    review = ReplacementCompatibilityReview.objects.filter(asset=asset).first()
    return render(request, 'inventory/replacement_review.html', {'asset': asset, 'impact': impact, 'review': review})
