'''Training and documentation views'''

from django.shortcuts import render

def index(request):
    '''Display the training landing page'''

    return render(
        request,
        'training/index.html',
    )
