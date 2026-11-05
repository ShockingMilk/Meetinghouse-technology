"""Views for operational notifications and their workflows."""

from datetime import datetime

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, Q, When
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    Notification,
    NotificationCategory,
    NotificationEvent,
    NotificationNote,
    NotificationNoteRevision,
    NotificationPriority,
    NotificationStatus,
)
from .services import (
    acknowledge_notification,
    assign_notification,
    reopen_notification,
    resolve_notification_manually,
    snooze_notification,
    unsnooze_notification,
)

PAGE_SIZE = 25


def _ordered_notifications(queryset):
    """Order notifications by operational severity, then most recently seen."""
    priority_order = Case(
        When(priority=NotificationPriority.CRITICAL, then=0),
        When(priority=NotificationPriority.HIGH, then=1),
        When(priority=NotificationPriority.MEDIUM, then=2),
        When(priority=NotificationPriority.LOW, then=3),
        When(priority=NotificationPriority.INFORMATIONAL, then=4),
        default=5,
        output_field=IntegerField(),
    )

    return queryset.annotate(
        priority_order=priority_order,
    ).order_by(
        "priority_order",
        "-last_seen_at",
        "-created_at",
    )


def _notification_detail_redirect(notification):
    """Return the detail page for a notification."""
    return redirect(
        "notifications:detail",
        pk=notification.pk,
    )


def _parse_local_datetime(value):
    """
    Convert a datetime-local form value into an aware datetime.

    HTML datetime-local values contain no timezone information, so they
    are interpreted using Django's currently configured timezone.
    """
    if not value:
        raise ValidationError("Select a date and time for the snooze.")

    try:
        parsed_datetime = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValidationError("Enter a valid snooze date and time.")

    if timezone.is_naive(parsed_datetime):
        try:
            parsed_datetime = timezone.make_aware(parsed_datetime)
        except (TypeError, ValueError, OverflowError):
            raise ValidationError(
                "That date and time is not valid in the configured timezone."
            )

    return parsed_datetime


@login_required
def notification_list(request):
    """Display a searchable, filterable notification queue."""
    queryset = Notification.objects.select_related(
        "asset",
        "assigned_to",
        "source_content_type",
    )

    selected_status = request.GET.get("status", "unresolved")
    selected_priority = request.GET.get("priority", "")
    selected_category = request.GET.get("category", "")
    selected_snooze = request.GET.get("snooze", "all")
    search_query = request.GET.get("q", "").strip()

    valid_statuses = {value for value, _label in NotificationStatus.choices}
    valid_priorities = {value for value, _label in NotificationPriority.choices}
    valid_categories = {value for value, _label in NotificationCategory.choices}

    if selected_status == "unresolved":
        queryset = queryset.filter(
            status__in=(
                NotificationStatus.OPEN,
                NotificationStatus.ACKNOWLEDGED,
            )
        )
    elif selected_status in valid_statuses:
        queryset = queryset.filter(status=selected_status)
    elif selected_status != "all":
        selected_status = "unresolved"
        queryset = queryset.filter(
            status__in=(
                NotificationStatus.OPEN,
                NotificationStatus.ACKNOWLEDGED,
            )
        )

    if selected_priority in valid_priorities:
        queryset = queryset.filter(priority=selected_priority)
    else:
        selected_priority = ""

    if selected_category in valid_categories:
        queryset = queryset.filter(category=selected_category)
    else:
        selected_category = ""

    # Treat only future snooze timestamps as actively snoozed.
    current_time = timezone.now()

    if selected_snooze == "snoozed":
        queryset = queryset.filter(
            snoozed_until__gt=current_time,
        )
    elif selected_snooze == "not_snoozed":
        queryset = queryset.filter(
            Q(snoozed_until__isnull=True) | Q(snoozed_until__lte=current_time)
        )
    elif selected_snooze != "all":
        selected_snooze = "all"

    if search_query:
        queryset = queryset.filter(
            Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(source_summary__icontains=search_query)
        )

    queryset = _ordered_notifications(queryset)

    paginator = Paginator(queryset, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "notifications/notification_list.html",
        {
            "page_obj": page_obj,
            "notifications": page_obj.object_list,
            "selected_status": selected_status,
            "selected_priority": selected_priority,
            "selected_category": selected_category,
            "selected_snooze": selected_snooze,
            "search_query": search_query,
            "status_choices": (
                ("unresolved", "Unresolved"),
                ("all", "All statuses"),
                *NotificationStatus.choices,
            ),
            "priority_choices": NotificationPriority.choices,
            "category_choices": NotificationCategory.choices,
            "snooze_choices": (
                ("all", "All snooze states"),
                ("not_snoozed", "Not snoozed"),
                ("snoozed", "Snoozed"),
            ),
        },
    )


@login_required
def notification_detail(request, pk):
    """Display a notification and its investigation history."""
    notification = get_object_or_404(
        Notification.objects.select_related(
            "asset",
            "assigned_to",
            "source_content_type",
        ),
        pk=pk,
    )

    events = (
        NotificationEvent.objects.filter(
            notification=notification,
        )
        .select_related("actor")
        .order_by("-created_at", "-pk")
    )

    notes = (
        NotificationNote.objects.filter(
            notification=notification,
        )
        .select_related("author")
        .order_by("-occurred_at", "-created_at")
    )

    revisions = (
        NotificationNoteRevision.objects.filter(
            note__notification=notification,
        )
        .select_related("revised_by", "note")
        .order_by("-created_at", "-pk")
    )

    user_model = get_user_model()
    assignable_users = user_model.objects.filter(
        is_active=True,
    ).order_by("pk")

    return render(
        request,
        "notifications/notification_detail.html",
        {
            "notification": notification,
            "events": events,
            "notes": notes,
            "revisions": revisions,
            "assignable_users": assignable_users,
        },
    )


@login_required
@require_POST
def notification_acknowledge(request, pk):
    """Acknowledge an open notification and record the action."""
    notification = get_object_or_404(Notification, pk=pk)

    try:
        acknowledge_notification(
            notification_id=notification.pk,
            actor=request.user,
        )
    except ValidationError as error:
        messages.error(request, error.messages[0])
    else:
        messages.success(request, "Notification acknowledged.")

    return _notification_detail_redirect(notification)


@login_required
@require_POST
def notification_assign(request, pk):
    """Assign or unassign an unresolved notification."""
    notification = get_object_or_404(Notification, pk=pk)

    assignee_id = request.POST.get("assignee_id", "").strip()
    assignee = None

    if assignee_id:
        user_model = get_user_model()

        try:
            normalized_id = user_model._meta.pk.to_python(assignee_id)
            assignee = user_model.objects.get(
                pk=normalized_id,
                is_active=True,
            )
        except (
            ValidationError,
            TypeError,
            ValueError,
            user_model.DoesNotExist,
        ):
            messages.error(
                request,
                "Select a valid active user for this assignment.",
            )
            return _notification_detail_redirect(notification)

    try:
        assign_notification(
            notification_id=notification.pk,
            actor=request.user,
            assignee=assignee,
        )
    except ValidationError as error:
        messages.error(request, error.messages[0])
    else:
        if assignee is None:
            messages.success(request, "Notification assignment removed.")
        else:
            messages.success(
                request,
                f"Notification assigned to {assignee.get_username()}.",
            )

    return _notification_detail_redirect(notification)


@login_required
@require_POST
def notification_snooze(request, pk):
    """Snooze a notification until the submitted local date and time."""
    notification = get_object_or_404(Notification, pk=pk)

    try:
        until = _parse_local_datetime(request.POST.get("snoozed_until", "").strip())
        snooze_notification(
            notification_id=notification.pk,
            actor=request.user,
            until=until,
        )
    except ValidationError as error:
        messages.error(request, error.messages[0])
    else:
        messages.success(
            request,
            f"Notification snoozed until "
            f"{timezone.localtime(until).strftime('%b %d, %Y %I:%M %p')}.",
        )

    return _notification_detail_redirect(notification)


@login_required
@require_POST
def notification_unsnooze(request, pk):
    """Remove an existing notification snooze."""
    notification = get_object_or_404(Notification, pk=pk)

    try:
        unsnooze_notification(
            notification_id=notification.pk,
            actor=request.user,
        )
    except ValidationError as error:
        messages.error(request, error.messages[0])
    else:
        messages.success(request, "Notification snooze removed.")

    return _notification_detail_redirect(notification)


@login_required
@require_POST
def notification_resolve(request, pk):
    """Manually resolve a notification with a required explanation."""
    notification = get_object_or_404(Notification, pk=pk)

    try:
        resolve_notification_manually(
            notification_id=notification.pk,
            actor=request.user,
            resolution_note=request.POST.get("resolution_note", ""),
        )
    except ValidationError as error:
        messages.error(request, error.messages[0])
    else:
        messages.success(request, "Notification manually resolved.")

    return _notification_detail_redirect(notification)


@login_required
@require_POST
def notification_reopen(request, pk):
    """Reopen a resolved notification with a required reason."""
    notification = get_object_or_404(Notification, pk=pk)

    try:
        reopen_notification(
            notification_id=notification.pk,
            actor=request.user,
            reason=request.POST.get("reason", ""),
        )
    except ValidationError as error:
        messages.error(request, error.messages[0])
    else:
        messages.success(request, "Notification reopened.")

    return _notification_detail_redirect(notification)
