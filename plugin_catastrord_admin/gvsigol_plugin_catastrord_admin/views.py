from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required

def catastrord_admin(request):
    """
    Vista principal del panel de Catastro RD.
    """
    return render(request, 'catastrord_admin.html', {})