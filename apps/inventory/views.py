'''Inventory views'''
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import RoomAssessmentForm
from .models import (
    Asset,
    AssetDraft,
    AssetCategory,
    AssetOwnership,
    Room,
    RoomAssessment,
    MaintenanceRecord,
    MaintenanceSchedule,
    AssetConnection,
    AssetDependency,
    VideoWorkflow,
)
from django.db.models import Q
from .services.lifecycle import lifecycle_warnings
from .services.maintenance import follow_up_state, schedule_state
from .services.relationships import relationship_impact, replacement_impact
from .models import ReplacementCompatibilityReview

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
    step_names = {1: 'Room', 2: 'Category', 3: 'Equipment details', 4: 'Connections', 5: 'Review and save'}
    for record in AssetDraft.objects.filter(created_by=request.user):
        draft = record.draft_data
        drafts.append({
            'wizard_id': record.pk,
            'name': draft.get('name') or 'New equipment',
            'inventory_number': draft.get('inventory_number', ''),
            'current_step': draft.get('current_step', 1),
            'step_name': step_names.get(draft.get('current_step', 1), 'Room'),
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
            Prefetch(
                'assets',
                queryset=Asset.objects.select_related('room').prefetch_related(
                    Prefetch('maintenance_records', queryset=MaintenanceRecord.objects.order_by('-performed_at', '-created_at'), to_attr='maintenance_history'),
                    Prefetch('maintenance_schedules', queryset=MaintenanceSchedule.objects.select_related('asset').prefetch_related(
                        Prefetch('completed_records', queryset=MaintenanceRecord.objects.order_by('-performed_at')),
                    ), to_attr='enabled_schedules'),
                ).order_by('inventory_number'),
            ),
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
    assets = list(room.assets.all())
    room_connections = AssetConnection.objects.filter(Q(source__room=room) | Q(destination__room=room)).select_related('source', 'source__room', 'destination', 'destination__room').distinct()
    room_dependencies = AssetDependency.objects.filter(Q(dependent_asset__room=room) | Q(required_asset__room=room) | Q(required_software__host_asset__room=room)).select_related('dependent_asset', 'dependent_asset__room', 'required_asset', 'required_asset__room', 'required_software', 'required_software__host_asset', 'required_software__host_asset__room').distinct()
    training_guides = room.training_guides.filter(published_revision__isnull=False).exclude(status='archived').select_related('published_revision').order_by('published_revision__title')[:6]
    for asset in assets:
        asset.latest_maintenance = asset.maintenance_history[0] if asset.maintenance_history else None
        for record in asset.maintenance_history:
            record.follow_up_state = follow_up_state(record)
        asset.open_followups = [record for record in asset.maintenance_history if record.follow_up_required and not record.resolved_at]
        asset.schedule_items = []
        for schedule in asset.enabled_schedules:
            state = schedule_state(schedule)
            asset.schedule_items.append({'schedule': schedule, **state})
        asset.lifecycle_summary = lifecycle_warnings(asset)

    return render(
        request,
        'inventory/room_detail.html',
        {
            'room': room,
            'assets': assets,
            'assessments': assessments,
            'latest_assessment': assessments[0] if assessments else None,
            'room_connections': room_connections,
            'room_dependencies': room_dependencies,
            'training_guides': training_guides,
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
            Prefetch('maintenance_records', queryset=MaintenanceRecord.objects.order_by('-performed_at', '-created_at'), to_attr='maintenance_history'),
            Prefetch('maintenance_schedules', queryset=MaintenanceSchedule.objects.prefetch_related(
                Prefetch('completed_records', queryset=MaintenanceRecord.objects.order_by('-performed_at')),
            ), to_attr='enabled_schedules'),
            'software_installations',
            'camera_presets',
        ),
        pk=pk,
    )
    lifecycle = lifecycle_warnings(asset)
    relationship_summary = relationship_impact(asset)
    replacement_summary = replacement_impact(asset)
    replacement_review_record = ReplacementCompatibilityReview.objects.filter(asset=asset).first()
    workflows = VideoWorkflow.objects.filter(Q(computer=asset) | Q(camera=asset) | Q(transmitter=asset) | Q(receiver=asset)).select_related('computer', 'camera', 'transmitter', 'receiver', 'obs_software').distinct()
    training_guides = asset.training_guides.filter(published_revision__isnull=False).exclude(status='archived').select_related('published_revision').order_by('published_revision__title')[:6]
    for record in asset.maintenance_history:
        record.follow_up_state = follow_up_state(record)
    schedule_items = []
    for schedule in asset.enabled_schedules:
        state = schedule_state(schedule)
        schedule_items.append({'schedule': schedule, **state})
    return render(
        request,
        'inventory/asset_detail.html',
        {
            'asset': asset,
            'lifecycle': lifecycle,
            'schedule_items': schedule_items,
            'today': timezone.localdate(),
            'lifecycle_warning_days': settings.LIFECYCLE_WARNING_DAYS,
            'relationship_summary': relationship_summary,
            'replacement_summary': replacement_summary,
            'replacement_review_record': replacement_review_record,
            'video_workflows': workflows,
            'training_guides': training_guides,
        },
    )


@login_required
def asset_label(request, pk: int):
    """Render a print-friendly reference label for one asset."""
    asset = get_object_or_404(Asset.objects.select_related('room'), pk=pk)
    return render_label_page(request, [asset])


@login_required
@require_POST
def asset_labels(request):
    """Render labels for selected assets without changing their records."""
    asset_ids = [value for value in request.POST.getlist('asset_ids') if value.isdigit()]
    assets = list(Asset.objects.select_related('room').filter(pk__in=asset_ids).order_by('inventory_number'))
    if not assets:
        messages.info(request, 'Select at least one equipment item to prepare labels.')
        return render_label_page(request, [], empty_selection=True)
    return render_label_page(request, assets)


def render_label_page(request, assets, *, empty_selection=False):
    """Share print layout and label text between individual and batch views."""
    labels = []
    for asset in assets:
        heading = asset.room.name if asset.room else settings.ASSET_LABEL_SITE_HEADING
        heading = heading[:24].rstrip() + ('…' if len(heading) > 24 else '')
        # Keep the device identifier intact while shortening unusually long names.
        name_limit = max(8, 39 - len(asset.inventory_number))
        label_name = asset.name if len(asset.name) <= name_limit else asset.name[:name_limit - 1].rstrip() + '…'
        labels.append({'asset': asset, 'heading': heading, 'label_name': label_name})
    return render(
        request,
        'inventory/asset_labels.html',
        {'labels': labels, 'empty_selection': empty_selection},
    )
