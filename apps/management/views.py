'''Management dashboard views'''

from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.shortcuts import render

from apps.inventory.models import Asset, Room, RoomAssessment

@login_required
def dashboard(request):
    '''Display the technology management dashboard'''

    latest_assessments = RoomAssessment.objects.order_by(
        '-assessment_date',
        '-created_at',
    )
    rooms = Room.objects.prefetch_related(
        Prefetch(
            'assessments',
            queryset=latest_assessments,
            to_attr='assessment_history',
        ),
    )
    room_count = rooms.count()
    assessed_room_count = 0
    follow_up_room_count = 0
    for room in rooms:
        if room.assessment_history:
            assessed_room_count += 1
            if room.assessment_history[0].follow_up_required:
                follow_up_room_count += 1

    context = {
        'asset_count': Asset.objects.count(),
        'active_asset_count': Asset.objects.filter(status='active').count(),
        'unknown_ownership_count': Asset.objects.filter(ownership='unknown').count(),
        'room_count': room_count,
        'assessed_room_count': assessed_room_count,
        'follow_up_room_count': follow_up_room_count,
        'unassigned_asset_count': Asset.objects.filter(room__isnull=True).count(),
    }

    return render(
        request,
        'management/dashboard.html',
        context,
    )
