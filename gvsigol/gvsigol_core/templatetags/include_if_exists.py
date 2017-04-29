from django import template
from django.template.loader_tags import do_include
from django.template.defaulttags import CommentNode
register = template.Library()

@register.tag('include_if_exists')
def do_include_if_exists(parser, token):
    bits = token.split_contents()
    if len(bits) < 2:
        raise template.TemplateSyntaxError(
            "%r tag takes at least one argument: "
            "the name of the template to be included." % bits[0])

    try:
        silent_node = do_include(parser, token)
    except template.TemplateDoesNotExist:
        #return CommentNode()
        return ''

    _orig_render = silent_node.render
    def wrapped_render(*args, **kwargs):
        try:
            return _orig_render(*args, **kwargs)
        except template.TemplateDoesNotExist:
            #return CommentNode()
            return ''
    silent_node.render = wrapped_render
    return silent_node