"""Authenticated maintenance, lifecycle, scheduling, and reporting views."""

import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .maintenance_forms import (
    MaintenanceRecordForm,
    MaintenanceReportFilterForm,
    MaintenanceResolutionForm,
    MaintenanceScheduleForm,
)
from .models import Asset, MaintenanceRecord, MaintenanceSchedule
from .services.lifecycle import lifecycle_warnings, replacement_review_needed
from .services.maintenance import default_interval_months, default_schedule_suggestion, follow_up_state, schedule_state
from .services.overview import maintenance_summary


@login_required
def dashboard(request):
    """Show computed inspection, follow-up, and lifecycle work queues."""
    summary = maintenance_summary()
    return render(request, 'inventory/maintenance_dashboard.html', summary)


@login_required
def maintenance_record_create(request, asset_pk=None):
    asset = get_object_or_404(Asset, pk=asset_pk) if asset_pk else None
    form = MaintenanceRecordForm(request.POST or None, asset=asset, initial={'asset': asset.pk} if asset else None)
    if request.method == 'POST' and form.is_valid():
        record = form.save()
        messages.success(request, 'Maintenance activity recorded. Equipment status and condition were left unchanged.')
        return redirect('inventory:maintenance_record_detail', pk=record.pk)
    return render(request, 'inventory/maintenance_record_form.html', {'form': form, 'asset': asset, 'is_edit': False})


@login_required
def maintenance_record_edit(request, pk):
    record = get_object_or_404(MaintenanceRecord.objects.select_related('asset'), pk=pk)
    form = MaintenanceRecordForm(request.POST or None, instance=record, asset=record.asset)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Maintenance record updated.')
        return redirect('inventory:maintenance_record_detail', pk=record.pk)
    return render(request, 'inventory/maintenance_record_form.html', {'form': form, 'asset': record.asset, 'record': record, 'is_edit': True})


@login_required
def maintenance_record_detail(request, pk):
    record = get_object_or_404(MaintenanceRecord.objects.select_related('asset', 'asset__room', 'schedule'), pk=pk)
    resolution_form = MaintenanceResolutionForm(request.POST or None)
    if request.method == 'POST' and request.POST.get('action') == 'reopen' and record.follow_up_required and record.resolved_at:
        record.resolved_at = None
        record.resolution_notes = ''
        record.save(update_fields=('resolved_at', 'resolution_notes'))
        messages.success(request, 'Follow-up reopened.')
        return redirect('inventory:maintenance_record_detail', pk=record.pk)
    if request.method == 'POST' and request.POST.get('action') == 'resolve' and record.follow_up_required and not record.resolved_at:
        if resolution_form.is_valid():
            record.resolved_at = resolution_form.cleaned_data['resolved_at']
            record.resolution_notes = resolution_form.cleaned_data['resolution_notes']
            record.save(update_fields=('resolved_at', 'resolution_notes'))
            messages.success(request, 'Follow-up marked resolved.')
            return redirect('inventory:maintenance_record_detail', pk=record.pk)
    return render(request, 'inventory/maintenance_record_detail.html', {
        'record': record,
        'follow_up_state': follow_up_state(record),
        'resolution_form': resolution_form,
    })


@login_required
def schedule_create(request, asset_pk=None):
    asset = get_object_or_404(Asset, pk=asset_pk) if asset_pk else None
    initial = ({'asset': asset.pk, 'interval_months': default_interval_months(asset), **default_schedule_suggestion(asset)} if asset else {})
    form = MaintenanceScheduleForm(request.POST or None, asset=asset, initial=initial)
    if request.method == 'POST' and form.is_valid():
        schedule = form.save()
        messages.success(request, f'Schedule “{schedule.name}” created. No maintenance records were generated.')
        return redirect('inventory:maintenance_dashboard')
    return render(request, 'inventory/maintenance_schedule_form.html', {'form': form, 'asset': asset, 'is_edit': False})


@login_required
def schedule_edit(request, pk):
    schedule = get_object_or_404(MaintenanceSchedule.objects.select_related('asset'), pk=pk)
    form = MaintenanceScheduleForm(request.POST or None, instance=schedule, asset=schedule.asset)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Inspection schedule updated. Its next due date remains based on the schedule and recorded completions.')
        return redirect('inventory:maintenance_dashboard')
    state = schedule_state(schedule)
    return render(request, 'inventory/maintenance_schedule_form.html', {'form': form, 'asset': schedule.asset, 'schedule': schedule, 'state': state, 'is_edit': True})


def _apply_asset_filters(queryset, filters):
    if filters.get('asset'):
        queryset = queryset.filter(pk=filters['asset'].pk)
    if filters.get('room'):
        queryset = queryset.filter(room=filters['room'])
    if filters.get('category'):
        queryset = queryset.filter(category=filters['category'])
    if filters.get('status'):
        queryset = queryset.filter(status=filters['status'])
    return queryset


def _csv_safe(value):
    text = '' if value is None else str(value)
    if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')):
        return "'" + text
    return text


def _csv_response(report_type, rows):
    headers = {
        'history': ('Date performed', 'Inventory number', 'Equipment', 'Room', 'Activity', 'Result', 'Recorded by', 'Description', 'Action taken', 'Follow-up', 'Follow-up due', 'Resolved date'),
        'followups': ('Inventory number', 'Equipment', 'Room', 'Issue', 'Date reported', 'Due date', 'State', 'Maintenance record'),
        'overdue': ('Inventory number', 'Equipment', 'Room', 'Schedule', 'Activity', 'Interval months', 'Next due'),
        'lifecycle': ('Inventory number', 'Equipment', 'Room', 'Lifecycle review', 'Warranty end', 'Security support end', 'End of life', 'Recommendation'),
        'replacement': ('Inventory number', 'Equipment', 'Room', 'Recommendation', 'Estimated replacement cost', 'Recommended action'),
    }[report_type]
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{report_type}-report.csv"'
    writer = csv.writer(response)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_csv_safe(cell) for cell in row])
    return response


@login_required
def reports(request):
    form = MaintenanceReportFilterForm(request.GET or None)
    if request.GET:
        valid = form.is_valid()
    else:
        form = MaintenanceReportFilterForm(initial={'report': 'history'})
        valid = True
    report_type = (form.cleaned_data.get('report') or 'history') if valid else 'history'
    filters = form.cleaned_data if valid else {}
    today = timezone.localdate()
    rows = []
    display_rows = []

    if report_type in ('history', 'followups'):
        records = MaintenanceRecord.objects.select_related('asset', 'asset__room').all()
        records = records.filter(asset__in=_apply_asset_filters(Asset.objects.all(), filters))
        if filters.get('date_from'):
            records = records.filter(performed_at__date__gte=filters['date_from'])
        if filters.get('date_to'):
            records = records.filter(performed_at__date__lte=filters['date_to'])
        if report_type == 'followups':
            records = records.filter(follow_up_required=True, resolved_at__isnull=True)
        for record in records.order_by('-performed_at', '-created_at'):
            if report_type == 'history':
                row = (timezone.localtime(record.performed_at).strftime('%Y-%m-%d %H:%M'), record.asset.inventory_number, record.asset.name, record.asset.room.name if record.asset.room else '', record.get_maintenance_type_display(), record.get_result_display(), record.performed_by, record.description, record.action_taken, record.follow_up_notes, record.follow_up_date, record.resolved_at)
            else:
                state = follow_up_state(record, as_of=today)
                row = (record.asset.inventory_number, record.asset.name, record.asset.room.name if record.asset.room else '', record.follow_up_notes, timezone.localtime(record.performed_at).date(), record.follow_up_date, state.replace('_', ' ').title(), record.pk)
            rows.append(row)
            display_rows.append({'record': record, 'state': follow_up_state(record, as_of=today) if report_type == 'followups' else ''})

    elif report_type == 'overdue':
        schedules = MaintenanceSchedule.objects.filter(enabled=True).select_related('asset', 'asset__room').prefetch_related(
            Prefetch('completed_records', queryset=MaintenanceRecord.objects.order_by('-performed_at')),
        )
        asset_filters = _apply_asset_filters(Asset.objects.all(), filters)
        schedules = schedules.filter(asset__in=asset_filters)
        for schedule in schedules:
            state = schedule_state(schedule, as_of=today)
            due = state['due_date']
            if state['state'] == 'overdue' and (not filters.get('date_from') or due >= filters['date_from']) and (not filters.get('date_to') or due <= filters['date_to']):
                rows.append((schedule.asset.inventory_number, schedule.asset.name, schedule.asset.room.name if schedule.asset.room else '', schedule.name, schedule.get_activity_type_display(), schedule.interval_months, due))
                display_rows.append({'schedule': schedule, 'due_date': due})

    else:
        assets = _apply_asset_filters(Asset.objects.select_related('room').all(), filters)
        for asset in assets:
            lifecycle = lifecycle_warnings(asset, as_of=today)
            if report_type == 'lifecycle' and lifecycle['needs_review']:
                descriptions = ', '.join(f"{item['label']}: {item['state']}" for item in lifecycle['warnings'] if item['state'] != 'current')
                rows.append((asset.inventory_number, asset.name, asset.room.name if asset.room else '', descriptions or 'Missing lifecycle information', asset.warranty_end_date, asset.security_support_end_date, asset.end_of_life_date, asset.replacement_recommendation))
                display_rows.append({'asset': asset, 'lifecycle': lifecycle})
            elif report_type == 'replacement' and replacement_review_needed(asset):
                rows.append((asset.inventory_number, asset.name, asset.room.name if asset.room else '', asset.get_replacement_recommendation_display(), asset.replacement_estimate, asset.recommended_action))
                display_rows.append({'asset': asset})

    if request.GET.get('csv') == '1' and valid:
        return _csv_response(report_type, rows)
    return render(request, 'inventory/maintenance_reports.html', {
        'form': form,
        'report_type': report_type,
        'display_rows': display_rows,
        'result_count': len(display_rows),
        'today': today,
    })
