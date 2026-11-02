'''Views for the guided equipment entry wizard.'''

from datetime import date, datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    WIZARD_FORMS,
    WIZARD_STEPS,
    RoomQuickAddForm,
)
from .models import Asset, AssetConnection, AssetDraft, Room, RoomPriority


def get_drafts(request):
    '''Return persistent drafts owned by the signed-in user.'''
    return {str(obj.pk): obj.draft_data for obj in AssetDraft.objects.filter(created_by=request.user)}


def get_draft_or_404(request, wizard_id):
    '''Find one draft owned by the signed-in user.'''
    try:
        obj = AssetDraft.objects.get(pk=wizard_id, created_by=request.user)
    except (AssetDraft.DoesNotExist, ValueError):
        raise Http404('Inventory draft not found.')
    return obj.draft_data


def store_draft(request, wizard_id, draft):
    '''Persist a changed draft owned by the active user.'''
    record = AssetDraft.objects.get(pk=wizard_id, created_by=request.user)
    record.draft_data = draft
    record.save(update_fields=('draft_data', 'updated_at'))


def delete_draft(request, wizard_id):
    '''Remove a completed or cancelled persistent draft.'''
    AssetDraft.objects.filter(pk=wizard_id, created_by=request.user).delete()


def serialize_value(value):
    '''Convert form values into JSON-compatible draft data.'''
    if value is None:
        return ''
    if isinstance(value, (date, datetime, Decimal)):
        return str(value)
    if isinstance(value, Room):
        return str(value.pk)
    if hasattr(value, 'values_list'):
        return [str(item) for item in value.values_list('pk', flat=True)]
    if isinstance(value, (list, tuple)):
        return [str(item.pk if hasattr(item, 'pk') else item) for item in value]
    return str(value)


def save_cleaned_form(draft, form):
    '''Merge validated values from one wizard step into a draft.'''
    for field_name, value in form.cleaned_data.items():
        draft[field_name] = serialize_value(value)


def save_raw_form(draft, form, post_data):
    '''Keep partial user input when saving or navigating back from a step.'''
    for field_name in form.fields:
        if field_name in post_data:
            draft[field_name] = post_data.getlist(field_name) if hasattr(form.fields[field_name].widget, 'allow_multiple_selected') and form.fields[field_name].widget.allow_multiple_selected else post_data.get(field_name, '')


def empty_draft():
    '''Create a new session-safe draft using the asset model's defaults.'''
    return {
        'asset_pk': '',
        'current_step': 1,
        'created_at': timezone.now().isoformat(),
        'room': '',
        'category': 'other',
        'inventory_number': '',
        'name': '',
        'manufacturer': '',
        'model_number': '',
        'serial_number': '',
        'physical_location': '',
        'installation_date': '',
        'warranty_end_date': '',
        'end_of_life_date': '',
        'security_support_end_date': '',
        'last_tested': '',
        'documentation_url': '',
        'funding_route': '',
        'approval_status': '',
        'replacement_estimate': '',
        'recommended_action': '',
        'specification': '',
        'dependencies': '',
        'notes': '',
        'ownership': 'unknown',
        'condition': 'unknown',
        'status': 'unknown',
        'responsible_party': '',
        'connected_assets': [],
        'connection_direction': 'outgoing',
        'connection_type': 'other',
        'connection_medium': 'other',
        'interface': '',
        'compatibility': 'unknown',
        'connection_notes': '',
    }


def draft_from_asset(asset):
    '''Copy editable asset fields into a draft without changing the database.'''
    draft = empty_draft()
    draft['asset_pk'] = str(asset.pk)
    editable_fields = (
        'room', 'category', 'inventory_number', 'name', 'manufacturer',
        'model_number', 'serial_number', 'physical_location', 'installation_date',
        'warranty_end_date', 'end_of_life_date', 'security_support_end_date',
        'last_tested', 'documentation_url', 'funding_route', 'approval_status',
        'replacement_estimate', 'recommended_action', 'specification',
        'dependencies', 'notes', 'ownership', 'condition', 'status',
        'responsible_party',
    )
    for field_name in editable_fields:
        value = getattr(asset, f'{field_name}_id') if field_name == 'room' else getattr(asset, field_name)
        draft[field_name] = serialize_value(value)
    return draft


@login_required
def start_asset_creation(request):
    '''Start a new equipment draft and open its first step.'''
    draft = empty_draft()
    room_id = request.GET.get('room', '')
    if room_id:
        room = get_object_or_404(Room, pk=room_id)
        draft['room'] = str(room.pk)
    record = AssetDraft.objects.create(created_by=request.user, draft_data=draft)
    wizard_id = str(record.pk)
    return redirect('inventory:asset_wizard_step', wizard_id=wizard_id, step=1)


@login_required
def start_asset_edit(request, pk):
    '''Start an edit draft from an existing equipment record.'''
    asset = get_object_or_404(Asset, pk=pk)
    record = AssetDraft.objects.create(created_by=request.user, draft_data=draft_from_asset(asset))
    wizard_id = str(record.pk)
    return redirect('inventory:asset_wizard_step', wizard_id=wizard_id, step=1)


def get_step_form(step, *args, **kwargs):
    '''Instantiate the form assigned to a wizard step.'''
    form_class = WIZARD_FORMS.get(step)
    if form_class is None:
        raise Http404('Wizard step not found.')
    return form_class(*args, **kwargs)


def render_step(request, wizard_id, step, draft, form):
    '''Render one step with progress and the equipment draft context.'''
    return render(
        request,
        'inventory/asset_wizard_step.html',
        {
            'wizard_id': wizard_id,
            'step': step,
            'step_name': WIZARD_STEPS[step],
            'step_names': WIZARD_STEPS,
            'form': form,
            'draft': draft,
            'is_edit': bool(draft.get('asset_pk')),
        },
    )


@login_required
def asset_wizard_step(request, wizard_id, step):
    '''Display, validate, and navigate equipment draft steps.'''
    draft = get_draft_or_404(request, wizard_id)
    if step == 5:
        return redirect('inventory:asset_wizard_review', wizard_id=wizard_id)
    if step not in WIZARD_FORMS:
        raise Http404('Wizard step not found.')

    if request.method == 'POST':
        form = get_step_form(
            step,
            request.POST,
            asset_pk=draft.get('asset_pk') or None,
            **({'category': draft.get('category')} if step == 3 else {}),
        ) if step in (3, 4) else get_step_form(step, request.POST)
        action = request.POST.get('action', 'next')

        if action == 'save_draft':
            save_raw_form(draft, form, request.POST)
            draft['current_step'] = step
            store_draft(request, wizard_id, draft)
            messages.success(request, 'Draft saved. You can resume it from the inventory page.')
            return redirect('inventory:asset_wizard_step', wizard_id=wizard_id, step=step)

        if action == 'previous':
            if form.is_valid():
                save_cleaned_form(draft, form)
            else:
                save_raw_form(draft, form, request.POST)
            previous_step = max(1, step - 1)
            draft['current_step'] = previous_step
            store_draft(request, wizard_id, draft)
            return redirect('inventory:asset_wizard_step', wizard_id=wizard_id, step=previous_step)

        if form.is_valid():
            save_cleaned_form(draft, form)
            next_step = step + 1
            draft['current_step'] = next_step
            store_draft(request, wizard_id, draft)
            if next_step == 5:
                return redirect('inventory:asset_wizard_review', wizard_id=wizard_id)
            return redirect('inventory:asset_wizard_step', wizard_id=wizard_id, step=next_step)
    else:
        form = get_step_form(
            step,
            initial=draft,
            asset_pk=draft.get('asset_pk') or None,
            **({'category': draft.get('category')} if step == 3 else {}),
        ) if step in (3, 4) else get_step_form(step, initial=draft)

    return render_step(request, wizard_id, step, draft, form)


def validate_complete_draft(draft):
    '''Validate all wizard sections before showing or saving the review.'''
    cleaned_values = {}
    for step, form_class in WIZARD_FORMS.items():
        if step in (3, 4):
            form = form_class(data=draft, asset_pk=draft.get('asset_pk') or None, category=draft.get('category')) if step == 3 else form_class(data=draft, asset_pk=draft.get('asset_pk') or None)
        else:
            form = form_class(data=draft)
        if not form.is_valid():
            return step, form, None
        cleaned_values.update(form.cleaned_data)
    return None, None, cleaned_values


def make_preview_asset(draft, cleaned_values):
    '''Build an unsaved model instance to display the review summary.'''
    values = dict(cleaned_values)
    for field_name in ('connected_assets', 'connection_direction', 'connection_type', 'connection_medium', 'interface', 'compatibility', 'connection_notes'):
        values.pop(field_name, None)
    room = values.pop('room', None)
    asset = Asset(**values)
    if room:
        asset.room_id = room.pk
    if draft.get('asset_pk'):
        asset.pk = draft['asset_pk']
    return asset


@login_required
def asset_wizard_review(request, wizard_id):
    '''Review all entered equipment details before committing an asset.'''
    draft = get_draft_or_404(request, wizard_id)
    invalid_step, _, cleaned_values = validate_complete_draft(draft)
    if invalid_step:
        messages.warning(request, 'Finish this step before reviewing the equipment record.')
        draft['current_step'] = invalid_step
        store_draft(request, wizard_id, draft)
        return redirect('inventory:asset_wizard_step', wizard_id=wizard_id, step=invalid_step)

    asset = make_preview_asset(draft, cleaned_values)
    room = Room.objects.filter(pk=cleaned_values['room'].pk).first() if cleaned_values['room'] else None
    if request.method == 'POST':
        if request.POST.get('action') == 'previous':
            draft['current_step'] = 4
            store_draft(request, wizard_id, draft)
            return redirect('inventory:asset_wizard_step', wizard_id=wizard_id, step=4)
        if request.POST.get('action') == 'save':
            values = dict(cleaned_values)
            selected_assets = values.pop('connected_assets', [])
            connection_direction = values.pop('connection_direction', '') or 'outgoing'
            connection_type = values.pop('connection_type', '')
            connection_medium = values.pop('connection_medium', '')
            interface = values.pop('interface', '')
            compatibility = values.pop('compatibility', '')
            connection_notes = values.pop('connection_notes', '')
            try:
                with transaction.atomic():
                    if draft.get('asset_pk'):
                        asset = get_object_or_404(Asset, pk=draft['asset_pk'])
                        for field_name, value in values.items():
                            setattr(asset, field_name, value)
                        asset.save()
                        saved_message = 'Equipment record updated.'
                    else:
                        asset = Asset.objects.create(**values)
                        saved_message = 'Equipment added to the inventory.'
                    if selected_assets:
                        AssetConnection.objects.bulk_create([
                            AssetConnection(
                                source=asset if connection_direction == 'outgoing' else related,
                                destination=related if connection_direction == 'outgoing' else asset,
                                connection_type=connection_type or 'other',
                                connection_medium=connection_medium or 'other',
                                interface=interface,
                                compatibility=compatibility or 'unknown',
                                notes=connection_notes,
                            )
                            for related in selected_assets
                        ])
            except IntegrityError:
                messages.error(request, 'A duplicate inventory number or connection was found. Review the details and try again.')
                return redirect('inventory:asset_wizard_step', wizard_id=wizard_id, step=4)
            delete_draft(request, wizard_id)
            messages.success(request, saved_message)
            return redirect('inventory:asset_detail', pk=asset.pk)

    return render(
        request,
        'inventory/asset_wizard_review.html',
        {
            'wizard_id': wizard_id,
            'draft': draft,
            'asset': asset,
            'room': room,
            'connected_assets': cleaned_values.get('connected_assets', []),
            'is_edit': bool(draft.get('asset_pk')),
            'step_names': WIZARD_STEPS,
        },
    )


@login_required
def room_quick_add(request, wizard_id):
    '''Save a room independently and select it on the active equipment draft.'''
    draft = get_draft_or_404(request, wizard_id)
    if request.method == 'POST':
        form = RoomQuickAddForm(request.POST)
        if form.is_valid():
            room = form.save()
            draft['room'] = str(room.pk)
            draft['current_step'] = 1
            store_draft(request, wizard_id, draft)
            messages.success(request, f'{room.name} was added and selected for this draft.')
            return redirect('inventory:asset_wizard_step', wizard_id=wizard_id, step=1)
    else:
        form = RoomQuickAddForm(initial={'priority': RoomPriority.UNKNOWN})

    return render(
        request,
        'inventory/room_quick_add.html',
        {'form': form, 'wizard_id': wizard_id},
    )


@login_required
@require_POST
def cancel_asset_draft(request, wizard_id):
    '''Discard a draft while keeping any separately created room.'''
    get_draft_or_404(request, wizard_id)
    delete_draft(request, wizard_id)
    messages.info(request, 'Equipment draft discarded. Any room you added remains in the room list.')
    return redirect('inventory:asset_list')
