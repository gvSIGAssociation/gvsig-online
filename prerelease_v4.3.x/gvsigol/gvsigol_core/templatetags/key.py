from django import template
register = template.Library()

@register.filter
def key(d, key_name):
    try:
        return d.get(key_name, '')
    except:
        return ''
