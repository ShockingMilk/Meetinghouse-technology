'''Inventory views'''
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404, redirect, render

from .forms import RoomAssessmentForm
from .models import (
    Asset,
    AssetCategory,
    AssetOwnership,
    Room,
    RoomAssessment,
)

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

    room_filter = request.GET.get('room', '')
    if room_filter == 'unassigned':
        assets = assets.filter(room__isnull=True)
    elif room_filter.isdigit():
        room_filter = int(room_filter)
        assets = assets.filter(room_id=room_filter)
    elif room_filter:
        room_filter = ''

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
            'room_choices': Room.objects.order_by('name'),
            'room_filter': room_filter,
            'unassigned_asset_count': Asset.objects.filter(room__isnull=True).count(),
            'result_count': assets.count(),
            'drafts': drafts,
        },
    )


@login_required
def room_list(request):
    '''Show room equipment counts and each room's latest assessment.'''
    assessment_history = RoomAssessment.objects.order_by(
        '-assessment_date',
        '-created_at',
    )
    rooms = Room.objects.annotate(
        asset_count=Count('assets', distinct=True),
    ).prefetch_related(
        Prefetch(
            'assessments',
            queryset=assessment_history,
            to_attr='assessment_history',
        ),
    )
    room_data = [
        {
            'room': room,
            'asset_count': room.asset_count,
            'latest_assessment': (
                room.assessment_history[0]
                if room.assessment_history
                else None
            ),
        }
        for room in rooms
    ]

    return render(
        request,
        'inventory/room_list.html',
        {
            'room_data': room_data,
            'unassigned_asset_count': Asset.objects.filter(
                room__isnull=True,
            ).count(),
        },
    )


@login_required
def room_detail(request, pk: int):
    '''Show room details, equipment, current assessment, and history.'''
    room = get_object_or_404(
        Room.objects.prefetch_related(
            'assets',
            Prefetch(
                'assessments',
                queryset=RoomAssessment.objects.order_by(
                    '-assessment_date',
                    '-created_at',
                ),
                to_attr='assessment_history',
            ),
        ),
        pk=pk,
    )
    assessments = room.assessment_history

    return render(
        request,
        'inventory/room_detail.html',
        {
            'room': room,
            'assets': room.assets.all(),
            'assessments': assessments,
            'latest_assessment': assessments[0] if assessments else None,
        },
    )


@login_required
def room_assessment_create(request, pk: int):
    '''Create an append-only technology assessment for a room.'''
    room = get_object_or_404(Room, pk=pk)
    if request.method == 'POST':
        form = RoomAssessmentForm(request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.room = room
            assessment.save()
            messages.success(request, f'Assessment saved for {room.name}.')
            return redirect('inventory:room_detail', pk=room.pk)
    else:
        form = RoomAssessmentForm()

    return render(
        request,
        'inventory/room_assessment_form.html',
        {'room': room, 'form': form},
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
