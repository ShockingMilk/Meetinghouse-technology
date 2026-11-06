"""On-demand building management summaries built from inventory records."""

from datetime import datetime, time, timedelta

from django.db.models import Count, OuterRef, Prefetch, Q, Subquery
from django.utils import timezone

from apps.inventory.models import (
    Asset,
    AssetConnection,
    AssetDependency,
    CompatibilityVerification,
    MaintenanceRecord,
    MaintenanceSchedule,
    ReplacementCompatibilityReview,
    Room,
    RoomAssessment,
)
from apps.inventory.services.lifecycle import (
    lifecycle_warnings,
    replacement_review_needed,
)
from apps.inventory.services.maintenance import (
    follow_up_state,
    schedule_state,
    with_latest_completion,
)


def building_dashboard():
    """Calculate dashboard counts and bounded attention/activity lists at load time."""
    today = timezone.localdate()
    latest_result = MaintenanceRecord.objects.filter(asset_id=OuterRef("pk")).order_by(
        "-performed_at", "-created_at"
    )
    active = Asset.objects.exclude(status="retired").annotate(
        latest_maintenance_result=Subquery(latest_result.values("result")[:1])
    )
    assets = list(active.select_related("room"))
    active_assets = [asset for asset in assets if asset.status == "active"]
    rooms = list(
        Room.objects.annotate(
            asset_count=Count(
                "assets", filter=~Q(assets__status="retired"), distinct=True
            )
        ).prefetch_related(
            Prefetch(
                "assessments",
                queryset=RoomAssessment.objects.order_by(
                    "-assessment_date", "-created_at"
                ),
                to_attr="assessment_history",
            ),
        )
    )

    # Only a current assessment counts toward coverage; unknown and not-applicable
    # are recorded but do not claim that the room was assessed as working.
    assessed = [
        room
        for room in rooms
        if room.assessment_history
        and room.assessment_history[0].overall_status != "unknown"
    ]
    not_assessed_rooms = [room for room in rooms if not room.assessment_history]
    unknown_rooms = [
        room
        for room in rooms
        if room.assessment_history
        and room.assessment_history[0].overall_status == "unknown"
    ]
    needs_review_rooms = [
        room
        for room in rooms
        if room.assessment_history
        and (
            room.assessment_history[0].overall_status in ("needs_review", "offline")
            or room.assessment_history[0].follow_up_required
        )
    ]
    for room in rooms:
        room.latest_assessment = (
            room.assessment_history[0] if room.assessment_history else None
        )
        room.assessment_state = (
            "not_assessed"
            if not room.latest_assessment
            else (
                "needs_review"
                if room in needs_review_rooms
                else (
                    "unknown"
                    if room.latest_assessment.overall_status == "unknown"
                    else "assessed"
                )
            )
        )
        if (
            room.latest_assessment
            and room.latest_assessment.overall_status == "offline"
        ):
            attention_item = {
                "priority": "critical",
                "label": "Room technology reported offline",
                "detail": room.latest_assessment.assessment_date,
                "url_name": "inventory:room_detail",
                "pk": room.pk,
                "asset": None,
                "room": room,
            }
            # Added after the main attention list is initialized below.
            room.dashboard_attention_item = attention_item
        elif room.latest_assessment and room.latest_assessment.follow_up_required:
            room.dashboard_attention_item = {
                "priority": "high",
                "label": "Room assessment follow-up open",
                "detail": room.latest_assessment.follow_up_notes or room.name,
                "url_name": "inventory:room_detail",
                "pk": room.pk,
                "asset": None,
                "room": room,
            }

    attention = []
    attention.extend(
        room.dashboard_attention_item
        for room in rooms
        if hasattr(room, "dashboard_attention_item")
    )
    result_labels = dict(MaintenanceRecord._meta.get_field("result").choices)
    for asset in assets:
        if asset.condition == "failed" or asset.latest_maintenance_result == "offline":
            attention.append(
                _item(
                    "critical",
                    "Equipment reported failed or offline",
                    (
                        asset.get_condition_display()
                        if asset.condition == "failed"
                        else result_labels.get(
                            asset.latest_maintenance_result, "Offline"
                        )
                    ),
                    "inventory:asset_detail",
                    asset.pk,
                    asset,
                )
            )
        elif asset.status == "under_repair":
            attention.append(
                _item(
                    "high",
                    "Equipment currently under repair",
                    asset.name,
                    "inventory:asset_detail",
                    asset.pk,
                    asset,
                )
            )
        lifecycle = lifecycle_warnings(asset, as_of=today)
        for warning in lifecycle["warnings"]:
            if warning["state"] == "approaching":
                attention.append(
                    _item(
                        "medium",
                        f"{warning['label']} approaching",
                        warning["date"],
                        "inventory:asset_detail",
                        asset.pk,
                        asset,
                    )
                )
            elif warning["state"] == "expired":
                attention.append(
                    _item(
                        "medium",
                        f"{warning['label']} date passed",
                        warning["date"],
                        "inventory:asset_detail",
                        asset.pk,
                        asset,
                    )
                )
        if replacement_review_needed(asset):
            attention.append(
                _item(
                    "medium",
                    "Replacement planning requires review",
                    asset.get_replacement_recommendation_display(),
                    "inventory:asset_detail",
                    asset.pk,
                    asset,
                )
            )
        elif lifecycle["missing_fields"]:
            attention.append(
                _item(
                    "informational",
                    "Lifecycle information incomplete",
                    ", ".join(lifecycle["missing_fields"]),
                    "inventory:asset_detail",
                    asset.pk,
                    asset,
                )
            )

    overdue_by_room = {}
    due_soon_by_room = {}
    for schedule in with_latest_completion(
        MaintenanceSchedule.objects.filter(enabled=True).select_related(
            "asset", "asset__room"
        )
    ):
        state = schedule_state(schedule, as_of=today)
        if state["state"] == "due_soon" and schedule.asset.room_id:
            due_soon_by_room[schedule.asset.room_id] = (
                due_soon_by_room.get(schedule.asset.room_id, 0) + 1
            )
        if state["state"] == "due_soon":
            attention.append(
                _item(
                    "informational",
                    "Inspection due soon",
                    f"{schedule.name} · due {state['due_date']}",
                    "inventory:maintenance_schedule_edit",
                    schedule.pk,
                    schedule.asset,
                )
            )
        if state["state"] == "overdue":
            attention.append(
                _item(
                    "high",
                    "Inspection overdue",
                    f"{schedule.name} · due {state['due_date']}",
                    "inventory:maintenance_schedule_edit",
                    schedule.pk,
                    schedule.asset,
                )
            )
            if schedule.asset.room_id:
                overdue_by_room[schedule.asset.room_id] = (
                    overdue_by_room.get(schedule.asset.room_id, 0) + 1
                )
    followups = (
        MaintenanceRecord.objects.filter(
            follow_up_required=True, resolved_at__isnull=True
        )
        .select_related("asset", "asset__room")
        .order_by("follow_up_date", "-performed_at")
    )
    for record in followups.filter(
        follow_up_date__isnull=False,
        follow_up_date__lt=today,
    )[:20]:
        state = follow_up_state(record, as_of=today)
        if state == "overdue":
            attention.append(
                _item(
                    "high",
                    "Maintenance follow-up overdue",
                    record.follow_up_notes or record.asset.name,
                    "inventory:maintenance_record_detail",
                    record.pk,
                    record.asset,
                )
            )
    for record in followups.filter(result__in=("offline", "attention"))[:20]:
        attention.append(
            _item(
                "high" if record.result == "offline" else "medium",
                "Unresolved maintenance issue",
                record.asset.name,
                "inventory:maintenance_record_detail",
                record.pk,
                record.asset,
            )
        )

    incompatible_connections = AssetConnection.objects.filter(
        compatibility="incompatible"
    ).count()
    unknown_connections = AssetConnection.objects.filter(
        compatibility__in=("unknown", "unverified")
    ).count()
    incompatible_dependencies = AssetDependency.objects.filter(
        verification_status="incompatible"
    ).count()
    unknown_dependencies = AssetDependency.objects.filter(
        verification_status__in=("unknown", "needs_review")
    ).count()
    incompatible_verifications = CompatibilityVerification.objects.filter(
        outcome="incompatible"
    ).count()
    unknown_verifications = CompatibilityVerification.objects.filter(
        outcome="unknown"
    ).count()
    for verification in CompatibilityVerification.objects.filter(
        outcome="incompatible"
    ).select_related("asset")[:20]:
        attention.append(
            _item(
                "critical",
                "Confirmed compatibility issue",
                verification.requirement,
                "inventory:asset_detail",
                verification.asset_id,
                verification.asset,
            )
        )
    for connection in AssetConnection.objects.filter(
        compatibility="incompatible"
    ).select_related("source", "source__room", "destination")[:20]:
        priority = "critical" if connection.is_required else "medium"
        attention.append(
            _item(
                priority,
                "Incompatible equipment connection",
                f"{connection.source.name} → {connection.destination.name}",
                "inventory:asset_detail",
                connection.source_id,
                connection.source,
            )
        )
    for dependency in AssetDependency.objects.filter(
        verification_status="incompatible"
    ).select_related("dependent_asset", "dependent_asset__room", "required_asset")[:20]:
        priority = "critical" if dependency.is_required else "medium"
        attention.append(
            _item(
                priority,
                "Incompatible operational dependency",
                dependency.description,
                "inventory:asset_detail",
                dependency.dependent_asset_id,
                dependency.dependent_asset,
            )
        )
    for review in ReplacementCompatibilityReview.objects.exclude(
        status__in=("compatible", "limited", "incompatible")
    ).select_related("asset")[:20]:
        attention.append(
            _item(
                "medium",
                "Replacement review awaiting a decision",
                review.asset.name,
                "inventory:replacement_review",
                review.asset_id,
                review.asset,
            )
        )
    attention.sort(
        key=lambda item: (
            ("critical", "high", "medium", "informational").index(item["priority"]),
            str(item["label"]),
        )
    )

    maintenance_records = list(
        MaintenanceRecord.objects.select_related("asset", "asset__room").order_by(
            "-performed_at"
        )[:10]
    )
    recent = []
    for asset in Asset.objects.select_related("room").order_by("-created_at")[:10]:
        recent.append(
            (
                asset.created_at,
                "Equipment added",
                asset,
                "inventory:asset_detail",
                asset.pk,
            )
        )
    for assessment in RoomAssessment.objects.select_related("room").order_by(
        "-created_at"
    )[:10]:
        recent.append(
            (
                assessment.created_at,
                "Room assessment completed",
                assessment.room,
                "inventory:room_detail",
                assessment.room_id,
            )
        )
    for record in maintenance_records:
        action = (
            "Inspection completed"
            if record.maintenance_type == "inspection"
            else "Maintenance activity recorded"
        )
        recent.append(
            (
                record.created_at,
                action,
                record,
                "inventory:maintenance_record_detail",
                record.pk,
            )
        )
        if record.resolved_at:
            resolved_moment = timezone.make_aware(
                datetime.combine(record.resolved_at, time.min)
            )
            recent.append(
                (
                    resolved_moment,
                    "Maintenance follow-up resolved",
                    record,
                    "inventory:maintenance_record_detail",
                    record.pk,
                )
            )
    for verification in CompatibilityVerification.objects.select_related(
        "asset"
    ).order_by("-created_at")[:10]:
        recent.append(
            (
                verification.created_at,
                "Compatibility verification recorded",
                verification.asset,
                "inventory:asset_detail",
                verification.asset_id,
            )
        )
    for asset in (
        Asset.objects.filter(status="retired")
        .select_related("room")
        .order_by("-updated_at")[:10]
    ):
        recent.append(
            (
                asset.updated_at,
                "Equipment retired",
                asset,
                "inventory:asset_detail",
                asset.pk,
            )
        )
    for asset in (
        Asset.objects.filter(updated_at__gt=timezone.now() - timedelta(days=30))
        .exclude(status="retired")
        .select_related("room")
        .order_by("-updated_at")[:10]
    ):
        if asset.updated_at - asset.created_at > timedelta(minutes=1):
            recent.append(
                (
                    asset.updated_at,
                    "Equipment information updated",
                    asset,
                    "inventory:asset_detail",
                    asset.pk,
                )
            )
    for review in ReplacementCompatibilityReview.objects.select_related(
        "asset"
    ).order_by("-updated_at")[:10]:
        recent.append(
            (
                review.updated_at,
                "Replacement planning updated",
                review.asset,
                "inventory:replacement_review",
                review.asset_id,
            )
        )
    recent.sort(key=lambda row: row[0], reverse=True)
    recent_items = [
        {"date": date, "action": action, "object": obj, "url_name": url, "pk": pk}
        for date, action, obj, url, pk in recent[:12]
    ]

    category_counts = _choice_counts(active_assets, "category")
    ownership_counts = _choice_counts(active_assets, "ownership")
    status_counts = _choice_counts(assets, "status")
    condition_counts = _choice_counts(active_assets, "condition")
    inspections = [item for item in attention if item["label"] == "Inspection overdue"]
    open_followup_count = followups.count()
    overdue_followup_count = MaintenanceRecord.objects.filter(
        follow_up_required=True, resolved_at__isnull=True, follow_up_date__lt=today
    ).count()
    open_followups = list(followups[:100])
    for record in open_followups:
        record.dashboard_follow_up_state = follow_up_state(record, as_of=today)
    lifecycle_items = []
    replacement_estimate = 0
    for asset in assets:
        status = lifecycle_warnings(asset, as_of=today)
        if status["needs_review"]:
            lifecycle_items.append({"asset": asset, **status})
        if replacement_review_needed(asset) and asset.replacement_estimate:
            replacement_estimate += asset.replacement_estimate
    open_by_room = dict(
        MaintenanceRecord.objects.filter(
            follow_up_required=True,
            resolved_at__isnull=True,
            asset__room__isnull=False,
        )
        .values("asset__room_id")
        .annotate(total=Count("pk"))
        .values_list("asset__room_id", "total")
    )
    for room in rooms:
        room.open_issue_count = open_by_room.get(room.pk, 0)
        room.overdue_inspection_count = overdue_by_room.get(room.pk, 0)
        room.upcoming_inspection_count = due_soon_by_room.get(room.pk, 0)

    compatibility_by_room = {}
    for connection in AssetConnection.objects.filter(
        compatibility="incompatible"
    ).values_list("source__room_id", "destination__room_id"):
        for room_id in set(connection):
            if room_id:
                compatibility_by_room[room_id] = (
                    compatibility_by_room.get(room_id, 0) + 1
                )
    for dependency in AssetDependency.objects.filter(
        verification_status="incompatible"
    ).values_list(
        "dependent_asset__room_id",
        "required_asset__room_id",
        "required_software__host_asset__room_id",
    ):
        for room_id in set(dependency):
            if room_id:
                compatibility_by_room[room_id] = (
                    compatibility_by_room.get(room_id, 0) + 1
                )
    for room in rooms:
        room.compatibility_issue_count = compatibility_by_room.get(room.pk, 0)
        room.lifecycle_concern_count = sum(
            1 for item in lifecycle_items if item["asset"].room_id == room.pk
        )

    return {
        "today": today,
        "asset_count": len(assets),
        "active_asset_count": len(active_assets),
        "category_counts": category_counts,
        "ownership_counts": ownership_counts,
        "status_counts": status_counts,
        "condition_counts": condition_counts,
        "stored_count": sum(a.status == "stored" for a in assets),
        "unassigned_count": sum(a.room_id is None for a in assets),
        "under_repair_count": sum(a.status == "under_repair" for a in assets),
        "room_count": len(rooms),
        "assessed_room_count": len(assessed),
        "unassessed_room_count": len(not_assessed_rooms),
        "unknown_room_count": len(unknown_rooms),
        "coverage_percent": round(len(assessed) * 100 / len(rooms)) if rooms else 0,
        "follow_up_room_count": len(needs_review_rooms),
        "rooms": rooms,
        "attention_items": attention[:18],
        "attention_count": len(attention),
        "recent_items": recent_items,
        "overdue_inspection_count": len(inspections),
        "open_followups": open_followups,
        "open_followup_count": open_followup_count,
        "overdue_followup_count": overdue_followup_count,
        "incompatible_count": incompatible_connections
        + incompatible_dependencies
        + incompatible_verifications,
        "unverified_count": unknown_connections
        + unknown_dependencies
        + unknown_verifications,
        "lifecycle_items": lifecycle_items[:12],
        "replacement_estimate": replacement_estimate,
    }


def _choice_counts(objects, field):
    counts = {}
    for obj in objects:
        key = getattr(obj, field)
        counts[key] = counts.get(key, 0) + 1
    choices = dict(obj_choices(objects, field)) if objects else {}
    return [
        {
            "value": key,
            "label": choices.get(key, key.replace("_", " ").title()),
            "count": count,
        }
        for key, count in sorted(counts.items(), key=lambda item: item[0])
    ]


def obj_choices(objects, field):
    # Use the model field choices so labels follow the underlying domain model.
    model = objects[0].__class__ if objects else Asset
    return model._meta.get_field(field).choices


def _item(priority, label, detail, url_name, pk, asset):
    return {
        "priority": priority,
        "label": label,
        "detail": detail,
        "url_name": url_name,
        "pk": pk,
        "asset": asset,
        "room": getattr(asset, "room", None),
    }
