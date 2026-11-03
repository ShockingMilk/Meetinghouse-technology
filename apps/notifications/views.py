"""Read-only views for operational notifications."""

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, Q, When
from django.shortcuts import get_object_or_404, render

from .models import (
    Notification,
    NotificationCategory,
    NotificationEvent,
    NotificationNote,
    NotificationNoteRevision,
    NotificationPriority,
    NotificationStatus,
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
        'priority_order',
        '-last_seen_at',
        '-created_at',
    )


@login_required
def notification_list(request):
    """Display a searchable, filterable notification queue."""
    queryset = Notification.objects.select_related(
        'asset',
        'assigned_to',
        'source_content_type',
    )

    selected_status = request.GET.get('status', 'unresolved')
    selected_priority = request.GET.get('priority', '')
    selected_category = request.GET.get('category', '')
    search_query = request.GET.get('q', '').strip()

    valid_statuses = {
        value for value, _label in NotificationStatus.choices
    }
    valid_priorities = {
        value for value, _label in NotificationPriority.choices
    }
    valid_categories = {
        value for value, _label in NotificationCategory.choices
    }

    if selected_status == 'unresolved':
        queryset = queryset.filter(
            status__in=(
                NotificationStatus.OPEN,
                NotificationStatus.ACKNOWLEDGED,
            )
        )
    elif selected_status in valid_statuses:
        queryset = queryset.filter(status=selected_status)
    elif selected_status != 'all':
        selected_status = 'unresolved'
        queryset = queryset.filter(
            status__in=(
                NotificationStatus.OPEN,
                NotificationStatus.ACKNOWLEDGED,
            )
        )

    if selected_priority in valid_priorities:
        queryset = queryset.filter(priority=selected_priority)
    else:
        selected_priority = ''

    if selected_category in valid_categories:
        queryset = queryset.filter(category=selected_category)
    else:
        selected_category = ''

    if search_query:
        queryset = queryset.filter(
            Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(source_summary__icontains=search_query)
        )

    queryset = _ordered_notifications(queryset)

    paginator = Paginator(queryset, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'notifications/notification_list.html',
        {
            'page_obj': page_obj,
            'notifications': page_obj.object_list,
            'selected_status': selected_status,
            'selected_priority': selected_priority,
            'selected_category': selected_category,
            'search_query': search_query,
            'status_choices': (
                ('unresolved', 'Unresolved'),
                ('all', 'All statuses'),
                *NotificationStatus.choices,
            ),
            'priority_choices': NotificationPriority.choices,
            'category_choices': NotificationCategory.choices,
        },
    )


@login_required
def notification_detail(request, pk):
    """Display a notification and its read-only investigation history."""
    notification = get_object_or_404(
        Notification.objects.select_related(
            'asset',
            'assigned_to',
            'source_content_type',
        ),
        pk=pk,
    )

    events = NotificationEvent.objects.filter(
        notification=notification,
    ).select_related(
        'actor',
    ).order_by(
        '-created_at',
        '-pk',
    )

    notes = NotificationNote.objects.filter(
        notification=notification,
    ).select_related(
        'author',
    ).order_by(
        '-occurred_at',
        '-created_at',
    )

    revisions = NotificationNoteRevision.objects.filter(
        note__notification=notification,
    ).select_related(
        'revised_by',
        'note',
    ).order_by(
        '-created_at',
        '-pk',
    )

    return render(
        request,
        'notifications/notification_detail.html',
        {
            'notification': notification,
            'events': events,
            'notes': notes,
            'revisions': revisions,
        },
    )
