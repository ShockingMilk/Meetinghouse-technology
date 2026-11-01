'''Inventory views'''
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Asset, AssetCategory, AssetOwnership

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

    drafts = []
    for wizard_id, draft in request.session.get('inventory_wizard_drafts', {}).items():
        drafts.append({
            'wizard_id': wizard_id,
            'name': draft.get('name') or 'New equipment',
            'inventory_number': draft.get('inventory_number', ''),
            'current_step': draft.get('current_step', 1),
            'step_name': {
                1: 'Room',
                2: 'Category',
                3: 'Equipment details',
                4: 'Technical details',
                5: 'Responsibility',
                6: 'Review and save',
            }.get(draft.get('current_step', 1), 'Room'),
        })

    return render(
        request,
        'inventory/asset_list.html',
        {
            'assets': assets,
            'search': search,
            'category': category or '',
            'ownership': ownership or '',
            'categories': AssetCategory.choices,
            'ownership_choices': AssetOwnership.choices,
            'result_count': assets.count(),
            'drafts': drafts,
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
