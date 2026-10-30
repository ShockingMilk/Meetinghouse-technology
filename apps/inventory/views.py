'''Inventory views'''
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Asset

@login_required
def asset_list(request):
    '''Display the building technology inventory'''

    assets = Asset.objects.select_related('room').all()

    category = request.GET.get('category')
    if category:
        assets = assets.filter(category=category)

    ownership = request.GET.get('ownership')
    if ownership:
        assets = assets.filter(ownership=ownership)

    search = request.GET.get('q', '').strip()
    if search:
        assets = assets.filter(name__icontains=search) | assets.filter(inventory_number__icontains=search)

    return render(
        request,
        'inventory/asset_list.html',
        {
            'assets': assets,
            'search': search,
        },
    )

@login_required
def asset_detail(request, pk: int):
    '''Display asset detail and associated records'''

    asset = get_object_or_404(
        Asset.objects.select_related('room').prefetch_related(
            'outgoing_connections__destination',
            'incoming_connections__source',
            'maintenance_records',
            'software_installations',
            'camera_presets',
        ),
        pk=pk,
    )

    return render(
        request,
        'inventory/asset_detail.html',
        {
            'asset': asset,
        },
    )
