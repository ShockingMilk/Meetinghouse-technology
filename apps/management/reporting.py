"""Reusable filtered report datasets and safe CSV serialization."""

import csv

from django.http import HttpResponse
from django.db.models import Count, OuterRef, Q, Subquery
from django.utils import timezone

from apps.inventory.models import (
    Asset, AssetConnection, AssetDependency, CompatibilityVerification,
    MaintenanceRecord, MaintenanceSchedule, ReplacementCompatibilityReview,
    Room, RoomAssessment,
)
from apps.inventory.services.lifecycle import lifecycle_warnings
from apps.inventory.services.maintenance import schedule_state, with_latest_completion


REPORTS = {
    'inventory': ('Complete inventory', 'inventory'),
    'inventory-room': ('Inventory by room', 'inventory'),
    'inventory-category': ('Inventory by category', 'inventory'),
    'inventory-condition': ('Inventory by condition and status', 'inventory'),
    'stored': ('Stored and unassigned equipment', 'inventory'),
    'room-inventory': ('Room inventory', 'room_inventory'),
    'assessment-history': ('Room assessment history', 'assessment'),
    'assessment-coverage': ('Room assessment coverage', 'room'),
    'rooms-review': ('Rooms needing review', 'room_review'),
    'rooms-unassessed': ('Rooms not yet assessed', 'room_unassessed'),
    'maintenance-history': ('Maintenance history', 'maintenance'),
    'open-followups': ('Open maintenance follow-ups', 'followups'),
    'overdue-followups': ('Overdue maintenance follow-ups', 'followups'),
    'inspection-schedules': ('Inspection schedules', 'schedules'),
    'overdue-inspections': ('Overdue inspections', 'schedules'),
    'completed-inspections': ('Completed inspections', 'maintenance'),
    'warranty': ('Warranty expiration', 'lifecycle'),
    'security-support': ('Security-support expiration', 'lifecycle'),
    'end-of-life': ('End-of-life review', 'lifecycle'),
    'replacements': ('Replacement recommendations and estimates', 'replacement'),
    'missing-lifecycle': ('Missing lifecycle information', 'lifecycle'),
    'connections': ('Equipment connections', 'connections'),
    'incompatible': ('Incompatible relationships', 'relationship_status'),
    'unverified': ('Unverified relationships', 'relationship_status'),
    'dependencies': ('Operational dependencies', 'dependencies'),
    'verification-history': ('Compatibility verification history', 'verifications'),
    'replacement-reviews': ('Replacement compatibility reviews', 'reviews'),
    'ownership-fmg': ('FMG-owned equipment', 'inventory'),
    'ownership-local': ('Locally managed equipment', 'inventory'),
    'ownership-unknown': ('Equipment awaiting ownership verification', 'inventory'),
}


def report_queryset(report, filters):
    """Return one filtered ORM queryset; report pages and exports share it."""
    kind = REPORTS[report][1]
    if kind == 'relationship_status':
        return relationship_status_records(report, filters)
    if kind in ('inventory', 'lifecycle', 'replacement'):
        qs = Asset.objects.select_related('room').all()
        if kind == 'lifecycle':
            field = {'warranty': 'warranty_end_date', 'security-support': 'security_support_end_date', 'end-of-life': 'end_of_life_date'}.get(report)
            if field:
                qs = qs.filter(**{f'{field}__isnull': False})
            if report == 'missing-lifecycle':
                qs = qs.filter(warranty_end_date__isnull=True) | qs.filter(security_support_end_date__isnull=True) | qs.filter(end_of_life_date__isnull=True) | qs.filter(installation_date__isnull=True) | qs.filter(last_tested__isnull=True)
        elif kind == 'replacement':
            qs = qs.exclude(replacement_recommendation='')
            if filters.get('replacement_priority'):
                qs = qs.filter(replacement_recommendation=filters['replacement_priority'])
        if report == 'stored':
            qs = qs.exclude(status='retired').filter(status='stored') | qs.exclude(status='retired').filter(room__isnull=True)
        if report.startswith('ownership-'):
            qs = qs.filter(ownership={'ownership-fmg': 'FMG', 'ownership-local': 'local', 'ownership-unknown': 'unknown'}[report])
    elif kind == 'room_inventory':
        qs = Room.objects.annotate(asset_count=Count('assets', filter=~Q(assets__status='retired'), distinct=True)).prefetch_related('assets', 'assessments').all()
    elif kind in ('room', 'room_review', 'room_unassessed'):
        latest = RoomAssessment.objects.filter(room_id=OuterRef('pk')).order_by('-assessment_date', '-created_at')
        qs = Room.objects.annotate(asset_count=Count('assets', filter=~Q(assets__status='retired'), distinct=True), latest_status=Subquery(latest.values('overall_status')[:1]), latest_follow_up=Subquery(latest.values('follow_up_required')[:1])).prefetch_related('assessments').all()
        if kind == 'room_review':
            qs = qs.filter(Q(latest_status__in=('needs_review', 'offline')) | Q(latest_follow_up=True))
        elif kind == 'room_unassessed':
            qs = qs.filter(latest_status__isnull=True)
    elif kind == 'assessment':
        qs = RoomAssessment.objects.select_related('room').all()
    elif kind in ('maintenance', 'followups'):
        qs = MaintenanceRecord.objects.select_related('asset', 'asset__room', 'schedule').all()
        if report == 'completed-inspections':
            qs = qs.filter(maintenance_type='inspection')
        if kind == 'followups':
            qs = qs.filter(follow_up_required=True, resolved_at__isnull=True)
            if report == 'overdue-followups':
                qs = qs.filter(follow_up_date__lt=timezone.localdate())
    elif kind == 'schedules':
        qs = with_latest_completion(MaintenanceSchedule.objects.select_related('asset', 'asset__room').all())
    elif kind in ('connections', 'compatibility'):
        qs = AssetConnection.objects.select_related('source', 'source__room', 'destination', 'destination__room').all()
        if report == 'incompatible':
            qs = qs.filter(compatibility='incompatible')
        elif report == 'unverified':
            qs = qs.filter(compatibility__in=('unknown', 'unverified'))
    elif kind == 'dependencies':
        qs = AssetDependency.objects.select_related('dependent_asset', 'dependent_asset__room', 'required_asset', 'required_software', 'required_software__host_asset').all()
    elif kind == 'verifications':
        qs = CompatibilityVerification.objects.select_related('asset', 'related_asset', 'connection').all()
    else:
        qs = ReplacementCompatibilityReview.objects.select_related('asset', 'asset__room').all()

    # Asset-related filters are routed through the appropriate relation path.
    if kind in ('inventory', 'lifecycle', 'replacement'):
        path = ''
    elif kind in ('room_inventory', 'room', 'room_review', 'room_unassessed', 'assessment'):
        path = 'room__'
    elif kind in ('maintenance', 'followups', 'schedules'):
        path = 'asset__'
    elif kind in ('connections', 'compatibility'):
        path = 'source__'
    elif kind == 'dependencies':
        path = 'dependent_asset__'
    elif kind == 'verifications':
        path = 'asset__'
    else:
        path = 'asset__'
    for key in ('room', 'category', 'ownership', 'status', 'condition'):
        value = filters.get(key)
        if not value:
            continue
        if key == 'room' and kind in ('room_inventory', 'room', 'room_review', 'room_unassessed'):
            qs = qs.filter(pk=value.pk)
        elif kind == 'room_inventory' and key != 'room':
            qs = qs.filter(**{f'assets__{key}': value})
        elif kind in ('connections', 'compatibility') and key != 'room':
            qs = qs.filter(**{f'{path}{key}': value}) | qs.filter(**{f'destination__{key}': value})
        elif key == 'room' and kind in ('inventory', 'lifecycle', 'replacement'):
            qs = qs.filter(room=value)
        elif key == 'room' and kind in ('maintenance', 'followups', 'schedules', 'dependencies', 'verifications', 'reviews'):
            if kind == 'dependencies':
                qs = qs.filter(Q(dependent_asset__room=value) | Q(required_asset__room=value) | Q(required_software__host_asset__room=value))
            else:
                qs = qs.filter(**{f'{path}room': value})
        elif key == 'room' and kind in ('connections', 'compatibility'):
            qs = qs.filter(Q(source__room=value) | Q(destination__room=value))
        elif key == 'room' and kind == 'assessment':
            qs = qs.filter(room=value)
        elif key != 'room':
            qs = qs.filter(**{f'{path}{key}': value})
    if kind in ('maintenance', 'followups', 'schedules', 'assessment', 'verifications'):
        start, end = filters.get('date_from'), filters.get('date_to')
        field = 'assessment_date' if kind == 'assessment' else 'performed_at__date' if kind in ('maintenance', 'followups') else 'verified_on' if kind == 'verifications' else 'created_at__date'
        if start: qs = qs.filter(**{f'{field}__gte': start})
        if end: qs = qs.filter(**{f'{field}__lte': end})
    if kind == 'lifecycle':
        field = {'warranty': 'warranty_end_date', 'security-support': 'security_support_end_date', 'end-of-life': 'end_of_life_date'}.get(report)
        if field and filters.get('date_from'): qs = qs.filter(**{f'{field}__gte': filters['date_from']})
        if field and filters.get('date_to'): qs = qs.filter(**{f'{field}__lte': filters['date_to']})
    if kind in ('maintenance', 'followups'):
        if filters.get('activity'): qs = qs.filter(maintenance_type=filters['activity'])
        if filters.get('result'): qs = qs.filter(result=filters['result'])
    if kind == 'connections' and filters.get('compatibility'):
        qs = qs.filter(compatibility=filters['compatibility'])
    if kind == 'dependencies' and filters.get('compatibility'):
        qs = qs.filter(verification_status=filters['compatibility'])
    if kind == 'verifications' and filters.get('compatibility'):
        qs = qs.filter(outcome=filters['compatibility'])
    if kind in ('inventory', 'lifecycle', 'replacement'):
        if report == 'inventory-room':
            return qs.distinct().order_by('room__name', 'inventory_number')
        if report == 'inventory-category':
            return qs.distinct().order_by('category', 'inventory_number')
        if report == 'inventory-condition':
            return qs.distinct().order_by('condition', 'status', 'inventory_number')
        return qs.distinct().order_by('inventory_number')
    if kind in ('room_inventory', 'room', 'room_review', 'room_unassessed'):
        return qs.distinct().order_by('name')
    if kind == 'assessment':
        return qs.distinct().order_by('-assessment_date', '-created_at')
    if kind in ('maintenance', 'followups'):
        return qs.distinct().order_by('-performed_at', '-created_at')
    if kind == 'schedules':
        return qs.distinct().order_by('asset__inventory_number', 'name')
    if kind in ('connections', 'compatibility'):
        return qs.distinct().order_by('source__inventory_number', 'destination__inventory_number')
    if kind == 'dependencies':
        return qs.distinct().order_by('dependent_asset__inventory_number', 'description')
    if kind == 'verifications':
        return qs.distinct().order_by('-verified_on', '-created_at')
    return qs.distinct().order_by('asset__inventory_number')


def report_rows(report, objects, filters=None):
    """Build printable/exportable cell sets from a page of records."""
    title = REPORTS[report][0]
    filters = filters or {}
    rows = []
    for obj in objects:
        if isinstance(obj, dict) and obj.get('record_kind') == 'connection':
            connection = obj['record']
            rows.append({'primary': f'{connection.source.inventory_number} → {connection.destination.inventory_number}',
                         'cells': ['Connection', connection.source.inventory_number, connection.source.name,
                                   connection.destination.inventory_number, connection.destination.name,
                                   connection.get_compatibility_display(), 'Required' if connection.is_required else 'Optional', connection.last_verified or ''],
                         'url': 'inventory:asset_detail', 'pk': connection.source_id})
        elif isinstance(obj, dict) and obj.get('record_kind') == 'dependency':
            dependency = obj['record']
            target = dependency.required_asset or dependency.required_software or dependency.external_service_name
            target_number = getattr(target, 'inventory_number', '')
            rows.append({'primary': f'{dependency.dependent_asset.inventory_number} requires {target}',
                         'cells': ['Dependency', dependency.dependent_asset.inventory_number, dependency.dependent_asset.name,
                                   target_number, str(target), dependency.get_verification_status_display(),
                                   'Required' if dependency.is_required else 'Optional', dependency.last_verified or ''],
                         'url': 'inventory:asset_detail', 'pk': dependency.dependent_asset_id})
        elif isinstance(obj, Asset):
            data = [obj.inventory_number, obj.name, obj.room.name if obj.room else 'Unassigned', obj.get_category_display(), obj.get_ownership_display(), obj.get_status_display(), obj.get_condition_display()]
            if report in ('warranty', 'security-support', 'end-of-life'):
                field = {'warranty': obj.warranty_end_date, 'security-support': obj.security_support_end_date, 'end-of-life': obj.end_of_life_date}[report]
                warning_key = {'warranty': 'Warranty', 'security-support': 'Security support', 'end-of-life': 'End of life'}[report]
                warning = next(item for item in lifecycle_warnings(obj)['warnings'] if item['key'] == warning_key)
                data += [field or 'Not recorded', warning['state'].replace('_', ' ').title()]
            elif report == 'replacements': data += [obj.get_replacement_recommendation_display(), obj.replacement_estimate or '', obj.recommended_action]
            elif report == 'missing-lifecycle': data.append(', '.join(lifecycle_warnings(obj)['missing_fields']))
            rows.append({'primary': f'{obj.inventory_number} · {obj.name}', 'cells': data, 'url': 'inventory:asset_detail', 'pk': obj.pk})
        elif isinstance(obj, Room):
            latest = obj.assessments.first() if hasattr(obj, 'assessments') else None
            room_assets = list(obj.assets.all()) if report == 'room-inventory' else []
            room_assets = [asset for asset in room_assets if all(not filters.get(key) or getattr(asset, key) == filters[key] for key in ('category', 'ownership', 'status', 'condition'))]
            cells = [obj.name, obj.room_number, len(room_assets) if report == 'room-inventory' else getattr(obj, 'asset_count', 0), latest.assessment_date if latest else 'Not assessed', latest.get_overall_status_display() if latest else 'Not assessed']
            rows.append({'primary': obj.name, 'cells': cells, 'url': 'inventory:room_detail', 'pk': obj.pk})
        elif isinstance(obj, RoomAssessment):
            rows.append({'primary': f'{obj.room.name} · {obj.assessment_date}', 'cells': [obj.room.name, obj.assessment_date, obj.get_overall_status_display(), 'Yes' if obj.follow_up_required else 'No', obj.assessed_by], 'url': 'inventory:room_detail', 'pk': obj.room_id})
        elif isinstance(obj, MaintenanceRecord):
            rows.append({'primary': f'{obj.asset.inventory_number} · {obj.asset.name}', 'cells': [obj.performed_at, obj.asset.inventory_number, obj.asset.name, obj.asset.room.name if obj.asset.room else 'Unassigned', obj.get_maintenance_type_display(), obj.get_result_display(), obj.follow_up_date or '', obj.resolved_at or ''], 'url': 'inventory:maintenance_record_detail', 'pk': obj.pk})
        elif isinstance(obj, MaintenanceSchedule):
            state = schedule_state(obj)
            if report == 'overdue-inspections' and state['state'] != 'overdue': continue
            rows.append({'primary': f'{obj.asset.inventory_number} · {obj.name}', 'cells': [obj.asset.inventory_number, obj.asset.name, obj.asset.room.name if obj.asset.room else 'Unassigned', obj.name, state['state'], state.get('due_date') or '', obj.interval_months], 'url': 'inventory:maintenance_schedule_edit', 'pk': obj.pk})
        elif isinstance(obj, AssetConnection):
            rows.append({'primary': f'{obj.source.inventory_number} → {obj.destination.inventory_number}', 'cells': [obj.source.inventory_number, obj.source.name, obj.destination.inventory_number, obj.destination.name, obj.get_connection_type_display(), obj.get_connection_medium_display(), obj.get_compatibility_display(), obj.last_verified or ''], 'url': 'inventory:asset_detail', 'pk': obj.source_id})
        elif isinstance(obj, AssetDependency):
            target = obj.required_asset or obj.required_software or obj.external_service_name
            rows.append({'primary': f'{obj.dependent_asset.inventory_number} · {obj.description}', 'cells': [obj.dependent_asset.inventory_number, obj.dependent_asset.name, str(target), obj.get_dependency_type_display(), 'Required' if obj.is_required else 'Optional', obj.get_verification_status_display()], 'url': 'inventory:asset_detail', 'pk': obj.dependent_asset_id})
        elif isinstance(obj, CompatibilityVerification):
            rows.append({'primary': f'{obj.asset.inventory_number} · {obj.requirement}', 'cells': [obj.asset.inventory_number, obj.asset.name, obj.requirement, obj.get_outcome_display(), obj.get_method_display(), obj.verified_on or '', obj.evidence_reference], 'url': 'inventory:asset_detail', 'pk': obj.asset_id})
        else:
            rows.append({'primary': f'{obj.asset.inventory_number} · {obj.asset.name}', 'cells': [obj.asset.inventory_number, obj.asset.name, obj.asset.room.name if obj.asset.room else 'Unassigned', obj.proposed_name, obj.proposed_model, obj.get_status_display(), obj.updated_at], 'url': 'inventory:replacement_review', 'pk': obj.asset_id})
    return rows


def csv_response(title, headers, rows):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="meetinghouse-{title.lower().replace(" ", "-")}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Report generated', timezone.localtime().strftime('%Y-%m-%d %H:%M %Z')])
    writer.writerow(headers)
    for row in rows:
        writer.writerow([csv_safe(value) for value in row])
    return response


def csv_safe(value):
    value = '' if value is None else str(value)
    return "'" + value if value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else value


def report_headers(report):
    if report in ('inventory', 'inventory-room', 'inventory-category', 'inventory-condition', 'stored') or report.startswith('ownership-'):
        return ['Inventory number', 'Equipment', 'Room', 'Category', 'Ownership', 'Status', 'Condition']
    if report in ('warranty', 'security-support', 'end-of-life'):
        return ['Inventory number', 'Equipment', 'Room', 'Category', 'Ownership', 'Status', 'Condition', 'Lifecycle date', 'Date state']
    if report == 'replacements': return ['Inventory number', 'Equipment', 'Room', 'Category', 'Ownership', 'Status', 'Condition', 'Recommendation', 'Estimated replacement cost', 'Recommended action']
    if report == 'missing-lifecycle': return ['Inventory number', 'Equipment', 'Room', 'Category', 'Ownership', 'Status', 'Condition', 'Missing fields']
    if report in ('incompatible', 'unverified'): return ['Record type', 'Asset number', 'Equipment', 'Related number', 'Related equipment or service', 'Verification', 'Required/optional', 'Last verified']
    if report.startswith('room-') or report.startswith('rooms-') or report == 'assessment-coverage': return ['Room', 'Room number', 'Asset count', 'Latest assessment', 'Assessment status']
    if report == 'assessment-history': return ['Room', 'Assessment date', 'Overall status', 'Follow-up required', 'Assessed by']
    if report in ('maintenance-history', 'completed-inspections', 'open-followups', 'overdue-followups'): return ['Date', 'Inventory number', 'Equipment', 'Room', 'Activity', 'Result', 'Follow-up due', 'Resolved date']
    if report in ('inspection-schedules', 'overdue-inspections'): return ['Inventory number', 'Equipment', 'Room', 'Schedule', 'Schedule state', 'Next due', 'Interval months']
    if report in ('connections', 'incompatible', 'unverified'): return ['Source number', 'Source equipment', 'Destination number', 'Destination equipment', 'Type', 'Medium', 'Compatibility', 'Last verified']
    if report == 'dependencies': return ['Dependent number', 'Dependent equipment', 'Required target', 'Type', 'Required/optional', 'Verification']
    if report == 'verification-history': return ['Inventory number', 'Equipment', 'Requirement', 'Outcome', 'Method', 'Verified on', 'Evidence reference']
    return ['Inventory number', 'Equipment', 'Room', 'Proposed replacement', 'Model', 'Review status', 'Updated']


def relationship_status_records(report, filters):
    """Combine connection and dependency rows for the building-wide status reports."""
    status_connection = 'incompatible' if report == 'incompatible' else None
    connection_qs = AssetConnection.objects.select_related('source', 'source__room', 'destination', 'destination__room')
    dependency_qs = AssetDependency.objects.select_related('dependent_asset', 'dependent_asset__room', 'required_asset', 'required_software', 'required_software__host_asset')
    if status_connection:
        connection_qs = connection_qs.filter(compatibility='incompatible')
        dependency_qs = dependency_qs.filter(verification_status='incompatible')
    else:
        connection_qs = connection_qs.filter(compatibility__in=('unknown', 'unverified'))
        dependency_qs = dependency_qs.filter(verification_status__in=('unknown', 'needs_review'))
    room = filters.get('room')
    if room:
        connection_qs = connection_qs.filter(Q(source__room=room) | Q(destination__room=room))
        dependency_qs = dependency_qs.filter(Q(dependent_asset__room=room) | Q(required_asset__room=room) | Q(required_software__host_asset__room=room))
    for key in ('category', 'ownership'):
        value = filters.get(key)
        if value:
            connection_qs = connection_qs.filter(Q(**{f'source__{key}': value}) | Q(**{f'destination__{key}': value}))
            dependency_qs = dependency_qs.filter(Q(**{f'dependent_asset__{key}': value}) | Q(**{f'required_asset__{key}': value}) | Q(**{f'required_software__host_asset__{key}': value}))
    records = ([{'record_kind': 'connection', 'record': item} for item in connection_qs]
               + [{'record_kind': 'dependency', 'record': item} for item in dependency_qs])
    records.sort(key=lambda item: ((item['record'].source.inventory_number if item['record_kind'] == 'connection' else item['record'].dependent_asset.inventory_number), item['record_kind']))
    return records
