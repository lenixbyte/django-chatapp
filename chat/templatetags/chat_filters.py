from django import template
from django.utils import timezone
from datetime import datetime
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='smart_time')
def smart_time(value):
    if not isinstance(value, (datetime, timezone.datetime)):
        value = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f%z')
    
    now = timezone.now()
    
    # If it's today, return the time
    # if value.date() == now.date():
    #     return value.strftime("%-I:%M %p")  # Returns like "3:45 PM"
    
    # For all other cases, return ISO format with current server time
    return mark_safe(
        f'<span class="moment-fromnow" data-timestamp="{value.isoformat()}" data-server-now="{now.isoformat()}">'
        f'{value.isoformat()}'
        f'</span>'
    ) 