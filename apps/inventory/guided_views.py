'''Views for the session-based equipment entry wizard.'''

from datetime import date, datetime
from decimal import Decimal
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    WIZARD_FORMS,
    WIZARD_STEPS,
    RoomQuickAddForm,
)
from .models import Asset, Room, RoomPriority

DRAFT_SESSION_KEY = 'inventory_wizard_drafts'


def get_drafts(request):
    '''Return the active user's session-held equipment drafts.'''
    return request.session.get(DRAFT_SESSION_KEY, {})


def get_draft_or_404(request, wizard_id):
    '''Find one draft in this browser session.'''
    draft = get_drafts(request).get(str(wizard_id))
    if draft is None:
        raise Http404('Inventory draft not found.')
    return draft


def store_draft(request, wizard_id, draft):
    '''Persist a changed draft into the Django session.'''
    drafts = get_drafts(request).copy()
    drafts[str(wizard_id)] = draft
    request.session[DRAFT_SESSION_KEY] = drafts


def delete_draft(request, wizard_id):
    '''Remove a completed or cancelled draft from the session.'''
    drafts = get_drafts(request).copy()
    drafts.pop(str(wizard_id), None)
    request.session[DRAFT_SESSION_KEY] = drafts


def serialize_value(value):
    '''Convert form values into types supported by Django's session serializer.'''
    if value is None:
        return ''
    if isinstance(value, (date, datetime, Decimal)):
        return str(value)
    if isinstance(value, Room):
        return str(value.pk)
    return str(value)


def save_cleaned_form(draft, form):
    '''Merge validated values from one wizard step into a draft.'''
    for field_name, value in form.cleaned_data.items():
        draft[field_name] = serialize_value(value)


def save_raw_form(draft, form, post_data):
    '''Keep partial user input when saving or navigating back from a step.'''
    for field_name in form.fields:
        if field_name in post_data:
            draft[field_name] = post_data.get(field_name, '')


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
    wizard_id = str(uuid.uuid4())
    store_draft(request, wizard_id, empty_draft())
    return redirect('inventory:asset_wizard_step', wizard_id=wizard_id, step=1)


@login_required
def start_asset_edit(request, pk):
    '''Start an edit draft from an existing equipment record.'''
    asset = get_object_or_404(Asset, pk=pk)
    wizard_id = str(uuid.uuid4())
    store_draft(request, wizard_id, draft_from_asset(asset))
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
    if step == 6:
        return redirect('inventory:asset_wizard_review', wizard_id=wizard_id)
    if step not in WIZARD_FORMS:
        raise Http404('Wizard step not found.')

    if request.method == 'POST':
        form = get_step_form(
            step,
            request.POST,
            asset_pk=draft.get('asset_pk') or None,
        ) if step == 3 else get_step_form(step, request.POST)
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
            if next_step == 6:
                return redirect('inventory:asset_wizard_review', wizard_id=wizard_id)
            return redirect('inventory:asset_wizard_step', wizard_id=wizard_id, step=next_step)
    else:
        form = get_step_form(
            step,
            initial=draft,
            asset_pk=draft.get('asset_pk') or None,
        ) if step == 3 else get_step_form(step, initial=draft)

    return render_step(request, wizard_id, step, draft, form)


def validate_complete_draft(draft):
    '''Validate all wizard sections before showing or saving the review.'''
    cleaned_values = {}
    for step, form_class in WIZARD_FORMS.items():
        if step == 3:
            form = form_class(data=draft, asset_pk=draft.get('asset_pk') or None)
        else:
            form = form_class(data=draft)
        if not form.is_valid():
            return step, form, None
        cleaned_values.update(form.cleaned_data)
    return None, None, cleaned_values


def make_preview_asset(draft, cleaned_values):
    '''Build an unsaved model instance to display the review summary.'''
    values = dict(cleaned_values)
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
            draft['current_step'] = 5
            store_draft(request, wizard_id, draft)
            return redirect('inventory:asset_wizard_step', wizard_id=wizard_id, step=5)
        if request.POST.get('action') == 'save':
            if draft.get('asset_pk'):
                asset = get_object_or_404(Asset, pk=draft['asset_pk'])
                for field_name, value in cleaned_values.items():
                    if field_name == 'room':
                        asset.room = value
                    else:
                        setattr(asset, field_name, value)
                asset.save()
                saved_message = 'Equipment record updated.'
            else:
                asset = Asset.objects.create(**cleaned_values)
                saved_message = 'Equipment added to the inventory.'
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
