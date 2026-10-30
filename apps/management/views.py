'''Management dashboard views'''

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.inventory.models import Asset

@login_required
def dashboard(request):
    '''Display the technology management dashboard'''

    context = {
        'asset_count': Asset.objects.count(),
        'active_asset_count': Asset.objects.filter(status='active').count(),
        'unknown_ownership_count': Asset.objects.filter(ownership='unknown').count(),
    }

    return render(
        request,
        'management/dashboard.html',
        context,
    )
