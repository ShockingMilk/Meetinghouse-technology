"""Authenticated building overview and reporting views."""

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils import timezone

from .forms import BuildingReportFilterForm
from .reporting import REPORTS, csv_response, report_headers, report_queryset, report_rows
from .services import building_dashboard
from apps.inventory.services.maintenance import schedule_state
from apps.notifications.services import notification_dashboard

@login_required
def dashboard(request):
    """Display the building-wide operational summary."""
    context = building_dashboard()
    context.update(notification_dashboard())
    return render(request, 'management/dashboard.html', context)


@login_required
def reports(request):
    """Show a validated, paginated report and export its same filtered dataset."""
    params = request.GET if request.GET else {'report': 'inventory'}
    form = BuildingReportFilterForm(params, report=request.GET.get('report', 'inventory'))
    valid = form.is_valid()
    report = form.cleaned_data.get('report', 'inventory') if valid else 'inventory'
    filters = form.cleaned_data if valid else {}
    queryset = report_queryset(report, filters)
    title = REPORTS[report][0]
    if request.GET.get('csv') == '1' and valid:
        objects = list(queryset)
        rows = report_rows(report, objects, filters)
        return csv_response(title, report_headers(report), [row['cells'] for row in rows])

    # Derived schedule state is calculated from existing completions. Filter
    # before pagination for overdue inspection reports so counts/pages agree.
    if report == 'overdue-inspections':
        queryset = [schedule for schedule in queryset if schedule_state(schedule)['state'] == 'overdue']
    page = Paginator(queryset, 50).get_page(request.GET.get('page'))
    rows = report_rows(report, page.object_list, filters)
    applied_filters = [(form.fields[name].label or name.replace('_', ' ').title(), str(filters[name]))
                       for name in form.fields if name != 'report' and filters.get(name)]
    coverage = None
    if report == 'assessment-coverage':
        total = queryset.count()
        assessed_count = queryset.exclude(latest_status__isnull=True).exclude(latest_status='unknown').count()
        coverage = {'total': total, 'assessed': assessed_count, 'unknown': queryset.filter(latest_status='unknown').count(),
                    'not_assessed': queryset.filter(latest_status__isnull=True).count(),
                    'percent': round(assessed_count * 100 / total) if total else 0}
    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_params.pop('csv', None)
    return render(request, 'management/reports.html', {
        'form': form, 'report': report, 'report_title': title, 'report_choices': REPORTS,
        'headers': report_headers(report), 'rows': rows, 'page': page,
        'result_count': page.paginator.count, 'generated_at': timezone.now(),
        'applied_filters': applied_filters, 'query_without_page': query_params.urlencode(), 'coverage': coverage,
    })
