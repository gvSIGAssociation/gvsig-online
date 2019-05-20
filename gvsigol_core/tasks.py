from models import SharedView
from django.utils import timezone
    
def clean_shared_views():
    now = timezone.now()
    SharedView.objects.filter(expiration_date__lt=now).delete()