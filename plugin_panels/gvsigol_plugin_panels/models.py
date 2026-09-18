# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils.translation import gettext_noop as _
from gvsigol_auth import auth_backend
from gvsigol_core.models import Project
from gvsigol_services.models import Layer

try:
    from django.db.models import JSONField
except ImportError:
    from django_jsonfield_backport.models import JSONField


class Panel(models.Model):
    project = models.ForeignKey(
        Project, null=True, blank=True, on_delete=models.SET_NULL, related_name='panels')
    name = models.CharField(max_length=150, blank=True)
    title = models.CharField(max_length=150)
    description = models.CharField(max_length=500, null=True, blank=True)
    image = models.ImageField(upload_to='images', default='', null=True, blank=True)
    # El panel se abre siempre en /panel/<slug>/, con proyecto o sin él, así que
    # el slug identifica al panel en toda la instalación.
    slug = models.SlugField(max_length=160, unique=True)
    layout = JSONField(default=dict, blank=True)
    is_public = models.BooleanField(default=False)
    created_by = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return '%s (%s)' % (
            self.title,
            self.project.name if self.project_id else 'standalone',
        )

    @property
    def image_url(self):
        if not self.image:
            return settings.STATIC_URL + 'panels/panel.svg'
        return self.image.url.replace(settings.BASE_URL, '')

    def can_read(self, request_or_user):
        user = request_or_user if isinstance(request_or_user, User) else request_or_user.user
        if self.is_public:
            return True
        if not user.is_authenticated:
            return False
        if user.is_superuser or user.username == self.created_by:
            return True
        if self.project_id and self.project.can_manage(request_or_user):
            return True
        roles = auth_backend.get_roles(request_or_user)
        return self.panelrole_set.filter(
            permission__in=(PanelRole.PERM_READ, PanelRole.PERM_MANAGE),
            role__in=roles,
        ).exists()

    def can_manage(self, request_or_user):
        user = request_or_user if isinstance(request_or_user, User) else request_or_user.user
        if not user.is_authenticated:
            return False
        if user.is_superuser or user.username == self.created_by:
            return True
        if self.project_id and self.project.can_manage(request_or_user):
            return True
        roles = auth_backend.get_roles(request_or_user)
        return self.panelrole_set.filter(
            permission=PanelRole.PERM_MANAGE,
            role__in=roles,
        ).exists()


class PanelRole(models.Model):
    PERM_READ = 'read'
    PERM_MANAGE = 'manage'
    PERMISSION_CHOICES = [
        (PERM_READ, PERM_READ),
        (PERM_MANAGE, PERM_MANAGE),
    ]

    panel = models.ForeignKey(Panel, on_delete=models.CASCADE)
    role = models.TextField()
    permission = models.TextField(choices=PERMISSION_CHOICES, default=PERM_READ)

    class Meta:
        indexes = [
            models.Index(
                fields=['panel', 'permission', 'role'],
                name='gvsigol_plu_panel_i_b182b1_idx',
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['panel', 'permission', 'role'],
                name='unique_permission_role_and_panel',
            ),
        ]

    def __str__(self):
        return '%s - %s - %s' % (self.panel.title, self.role, self.permission)


class PanelDataset(models.Model):
    SOURCE_WFS = 'wfs_layer'
    SOURCE_SHEET = 'spreadsheet'
    SOURCE_REST = 'rest'
    SOURCE_CHOICES = [
        (SOURCE_WFS, 'wfs_layer'),
        (SOURCE_SHEET, 'spreadsheet'),
        (SOURCE_REST, 'rest'),
    ]

    project = models.ForeignKey(
        Project, null=True, blank=True, on_delete=models.CASCADE, related_name='panel_datasets')
    panel = models.ForeignKey(
        Panel, null=True, blank=True, on_delete=models.CASCADE, related_name='datasets')
    name = models.CharField(max_length=150)
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_WFS)
    layer = models.ForeignKey(Layer, null=True, blank=True, on_delete=models.SET_NULL)
    file = models.FileField(upload_to='panels/datasets', null=True, blank=True)
    column_mapping = JSONField(default=dict, blank=True)
    rows = JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(project__isnull=False) | Q(panel__isnull=False),
                name='panel_dataset_has_scope',
            ),
        ]

    def __str__(self):
        return self.name


class PanelWidget(models.Model):
    TYPE_CHOICES = [
        ('map', 'map'),
        ('table', 'table'),
        ('list', 'list'),
        ('bar', 'bar'),
        ('bar_horizontal', 'bar_horizontal'),
        ('line', 'line'),
        ('pie', 'pie'),
        ('kpi', 'kpi'),
    ]
    FILTER_INDEPENDENT = 'independent'
    FILTER_LINKED = 'linked'
    FILTER_CHOICES = [
        (FILTER_INDEPENDENT, 'independent'),
        (FILTER_LINKED, 'linked'),
    ]

    panel = models.ForeignKey(Panel, on_delete=models.CASCADE, related_name='widgets')
    layer = models.ForeignKey(
        Layer, null=True, blank=True, on_delete=models.SET_NULL, related_name='panel_widgets')
    widget_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    name = models.CharField(max_length=150, blank=True)
    title = models.CharField(max_length=150, blank=True)
    description = models.CharField(max_length=500, blank=True)
    x = models.IntegerField(default=0)
    y = models.IntegerField(default=0)
    w = models.IntegerField(default=6)
    h = models.IntegerField(default=4)
    config = JSONField(default=dict, blank=True)
    filter_mode = models.CharField(max_length=20, choices=FILTER_CHOICES, default=FILTER_LINKED)
    dataset = models.ForeignKey(PanelDataset, null=True, blank=True, on_delete=models.SET_NULL)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.title or self.name or self.widget_type


def translations_placeholder():
    # do not remove — used by project tools i18n
    _ = _("gvsigol_plugin_panels manual title")
    _ = _("gvsigol_plugin_panels manual desc")
