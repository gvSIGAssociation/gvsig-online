from __future__ import unicode_literals

from django.db import models
from gvsigol import settings
from gvsigol_auth.models import UserGroup
from gvsigol_services.models import LayerGroup
from django.utils.translation import ugettext as _

def get_default_logo_image():
    return settings.STATIC_URL + 'img/logo_principal.png'

def get_default_project_image():
    return settings.STATIC_URL + 'img/no_project.png'

class Project(models.Model):
    name = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=100, null=True, blank=True)
    description = models.CharField(max_length=250, null=True, blank=True)
    logo = models.ImageField(upload_to='images', default=get_default_logo_image, null=True, blank=True)
    logo_link = models.CharField(max_length=250, null=True, blank=True)
    image = models.ImageField(upload_to='images', default=get_default_project_image, null=True, blank=True)
    center_lat = models.CharField(max_length=100)
    center_lon = models.CharField(max_length=100)
    zoom = models.IntegerField(null=False, default=10)
    extent = models.CharField(max_length=250)
    toc_mode = models.TextField(max_length=50, default='toc_hidden')
    toc_order = models.TextField(null=True, blank=True)
    created_by = models.CharField(max_length=100)
    is_public = models.BooleanField(default=False)
    show_project_icon = models.BooleanField(default=True)
    selectable_groups = models.BooleanField(default=False)
    restricted_extent = models.BooleanField(default=False)
    tools = models.TextField(null=True, blank=True) 
    baselayer_version = models.BigIntegerField(null=True, blank=True)
    
    def __unicode__(self):
        return self.name + ' - ' + self.description
    
    def clone(self, target_datastore, name, title, recursive=True, copy_layer_data=True):
        old_pid = self.pk
        self.pk = None
        self.name = name
        self.title = title
        self.save()
        new_project_instance = Project.objects.get(id=self.pk)

        if recursive:
            old_project = Project.objects.get(id=old_pid)
            for prj_lg in old_project.projectlayergroup_set.all():
                prj_lg.clone(project=new_project_instance, target_datastore=target_datastore, copy_layer_data=copy_layer_data)
            
            for prj_ug in old_project.projectusergroup_set.all():
                prj_ug.clone(project=new_project_instance)
            # TODO: user groups (ProjectUserGroup)
        return new_project_instance
    
class ProjectUserGroup(models.Model):
    project = models.ForeignKey(Project, default=None)
    user_group = models.ForeignKey(UserGroup, default=None)
    
    def __unicode__(self):
        return self.project.name + ' - ' + self.user_group.name
    
    def clone(self, project):
        self.pk = None
        self.project = project
        self.save()
        return ProjectUserGroup.objects.get(id=self.pk)
        
class ProjectLayerGroup(models.Model):
    project = models.ForeignKey(Project, default=None)
    layer_group = models.ForeignKey(LayerGroup, default=None)
    multiselect = models.BooleanField(default=True)
    baselayer_group = models.BooleanField(default=False)
    default_baselayer = models.IntegerField(null=True, blank=True)
    
    def __unicode__(self):
        return self.project.name + ' - ' + self.layer_group.name
    
    def clone(self, recursive=True, project=None, target_datastore=None, copy_layer_data=True):
        if recursive:
            if not self.baselayer_group:
                self.layer_group = self.layer_group.clone(target_datastore=target_datastore, copy_layer_data=copy_layer_data)
        self.pk = None
        if project:
            self.project = project
        self.save()
        return ProjectLayerGroup.objects.get(id=self.pk)

class SharedView(models.Model):
    name = models.CharField(max_length=40, unique=True)
    project_id = models.IntegerField()
    description = models.CharField(max_length=250, null=True, blank=True)
    url = models.CharField(max_length=500, null=True, blank=True)
    state = models.TextField(null=True, blank=True)
    creation_date = models.DateField(auto_now=True)
    expiration_date = models.DateField(null=False)
    created_by = models.CharField(max_length=100)
    # Internal views are only available for superuser and are not listed on shared_views
    # They are used to bookmark the map state of user requests
    internal = models.BooleanField(default=False, db_index=True)
    
    def __unicode__(self):
        return self.name

class SettingsManager(models.Manager):
    def get_value(self, plugin_name, key, default=""):
        try:
            return GolSettings.objects.get(plugin_name=plugin_name, key = key).value
        except GolSettings.DoesNotExist:
            return default
    
    def set_value(self, plugin_name, key, value):
        try:
            settings_entry = GolSettings.objects.get(plugin_name=plugin_name, key = key)
        except GolSettings.DoesNotExist:
            settings_entry = GolSettings()
            settings_entry.plugin_name = plugin_name
            settings_entry.key = key
        settings_entry.value = value
        settings_entry.save()
    
class GolSettings(models.Model):
    """
    Used to store settings (key/value pairs) that can be changed at runtime,
    so they can't be stored in settings.py
    
    To avoid key collisions, a plugin_name must also be provided to set or
    get a key/value pair. Examples:
    
    # set "link_validity" key
    GolSettings.objects.set_value(
        plugin_name="gvsigol_plugin_downloadman",
        key = "link_validity",
        value = "32")

    # get "link_validity" key
    validity = GolSettings.objects.get_value(
        plugin_name="gvsigol_plugin_downloadman",
        key = "link_validity")
        
    # get "link_validity" key and provide a default value in case this key has not been defined
    validity = GolSettings.objects.get_value(
        plugin_name="gvsigol_plugin_downloadman",
        key = "link_validity",
        default = "9")
    
    A GolSettings.DoesNotExist exception will be raised if the key is not defined and
    no default has been provided
    """
    plugin_name = models.TextField()
    key = models.TextField()
    value = models.TextField()
    objects = SettingsManager()
    class Meta:
        unique_together = ('plugin_name', 'key')
