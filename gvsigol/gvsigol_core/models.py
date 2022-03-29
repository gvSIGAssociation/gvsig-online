

from django.db import models
from gvsigol import settings
from gvsigol_auth.models import UserGroup
from gvsigol_services.models import LayerGroup, Layer
from django.utils.translation import ugettext as _
from gvsigol_services.models import CLONE_PERMISSION_CLONE, CLONE_PERMISSION_SKIP

def get_default_logo_image():
    return settings.STATIC_URL + 'img/logo_principal.png'

def get_default_project_image():
    return settings.STATIC_URL + 'img/no_project.png'

class Project(models.Model):
    name = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=100, null=True, blank=True)
    description = models.CharField(max_length=250, null=True, blank=True)
    # see also logo_url property
    logo = models.ImageField(upload_to='images', default='', null=True, blank=True)
    logo_link = models.CharField(max_length=250, null=True, blank=True)
    # see also image_url property
    image = models.ImageField(upload_to='images', default='', null=True, blank=True)
    center_lat = models.CharField(max_length=100)
    center_lon = models.CharField(max_length=100)
    zoom = models.IntegerField(null=False, default=10)
    extent = models.CharField(max_length=250)
    extent4326_minx = models.FloatField(null=True,blank=True)
    extent4326_miny = models.FloatField(null=True,blank=True)
    extent4326_maxx = models.FloatField(null=True,blank=True)
    extent4326_maxy = models.FloatField(null=True,blank=True)
    toc_mode = models.TextField(max_length=50, default='toc_hidden')
    toc_order = models.TextField(null=True, blank=True)
    created_by = models.CharField(max_length=100)
    is_public = models.BooleanField(default=False)
    show_project_icon = models.BooleanField(default=True)
    selectable_groups = models.BooleanField(default=False)
    restricted_extent = models.BooleanField(default=False)
    tools = models.TextField(null=True, blank=True) 
    baselayer_version = models.BigIntegerField(null=True, blank=True)
    labels =  models.CharField(max_length=250, null=True, blank=True)
    expiration_date = models.DateTimeField(auto_now_add=False, null=True, blank=True)
    
    def __str__(self):
        return self.name + ' - ' + self.description
    
    def clone(self, target_datastore, name, title, recursive=True, copy_layer_data=True, permissions=CLONE_PERMISSION_CLONE):
        old_pid = self.pk
        self.pk = None
        self.name = name
        self.title = title
        self.save()
        new_project_instance = Project.objects.get(id=self.pk)

        if recursive:
            old_project = Project.objects.get(id=old_pid)
            for prj_lg in old_project.projectlayergroup_set.all():
                prj_lg.clone(project=new_project_instance, target_datastore=target_datastore, copy_layer_data=copy_layer_data, permissions=permissions)
            
            if permissions != CLONE_PERMISSION_SKIP:
                for prj_ug in old_project.projectusergroup_set.all():
                    prj_ug.clone(project=new_project_instance)
        return new_project_instance
    
    @property
    def image_url(self):
        """
        Returns URL to the project image if defined, otherwise it returns get_default_project_image()
        otherwise. This method always returns a relative URL, such as
        '/media/images/logo_AMQtcXf.png'
        or
        '/static/img/no_project.png'.
        
        This property is recommended instead of directly using image.url because
        the default projecte image is outside media dir, so the url property does
        not build a valid URL.
        """
        if not self.image:
            return get_default_project_image()
        return self.image.url.replace(settings.BASE_URL, '')

    @property
    def logo_url(self):
        """
        Returns URL to the project logo if defined, otherwise it returns get_default_logo_image()
        otherwise. This method always returns a relative URL, such as
        '/media/images/logo_AMQtcXf.png'
        or
        '/static/img/logo_principal.png'

        This property is recommended instead of directly using logo.url because
        the default projecte logo is outside media dir, so the url property does
        not build a valid URL.
        """
        if not self.logo:
            return get_default_logo_image()
        return self.logo.url.replace(settings.BASE_URL, '')
    
class ProjectUserGroup(models.Model):
    project = models.ForeignKey(Project, default=None, on_delete=models.CASCADE)
    user_group = models.ForeignKey(UserGroup, default=None, on_delete=models.CASCADE)
    
    def __str__(self):
        return self.project.name + ' - ' + self.user_group.name
    
    def clone(self, project):
        self.pk = None
        self.project = project
        self.save()
        return ProjectUserGroup.objects.get(id=self.pk)
        
class ProjectLayerGroup(models.Model):
    project = models.ForeignKey(Project, default=None, on_delete=models.CASCADE)
    layer_group = models.ForeignKey(LayerGroup, default=None, on_delete=models.CASCADE)
    multiselect = models.BooleanField(default=True)
    baselayer_group = models.BooleanField(default=False)
    default_baselayer = models.IntegerField(null=True, blank=True)
    
    def __str__(self):
        return self.project.name + ' - ' + self.layer_group.name
    
    def clone(self, recursive=True, project=None, target_datastore=None, copy_layer_data=True, permissions=CLONE_PERMISSION_CLONE):
        if recursive:
            if not self.baselayer_group:
                self.layer_group = self.layer_group.clone(target_datastore=target_datastore, copy_layer_data=copy_layer_data,  permissions=permissions)
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
    
    def __str__(self):
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


class ProjectBaseLayerTiling(models.Model):
    project = models.ForeignKey(Project, default=None, on_delete=models.CASCADE)
    layer = models.IntegerField(null=False, default=0)
    levels = models.IntegerField(null=False, default=0)
    tilematrixset = models.CharField(max_length=50) 
    format = models.CharField(max_length=50)
    extentid = models.CharField(max_length=50)
    version = models.BigIntegerField(null=True, blank=True)
    folder_prj = models.CharField(max_length=1024)
    running = models.BooleanField(default=False)


class TilingProcessStatus(models.Model):
    layer = models.IntegerField(null=False, default=0)
    format_processed = models.CharField(max_length=50)
    processed_tiles = models.IntegerField(null=False, default=0)
    total_tiles = models.IntegerField(null=False, default=0)
    version = models.BigIntegerField(null=True, blank=True)
    time = models.CharField(max_length=150)
    active = models.CharField(max_length=10)
    stop = models.CharField(max_length=10)
    extent_processed = models.CharField(max_length=150)
    zoom_levels_processed = models.IntegerField(null=False, default=0)
    start_time = models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)

class ProjectZone(models.Model):
    title = models.CharField(max_length=50) 
    project = models.ForeignKey(Project, default=None, on_delete=models.CASCADE)
    levels = models.IntegerField(null=False, default=14)
    extent4326_minx = models.FloatField(null=True,blank=True)
    extent4326_miny = models.FloatField(null=True,blank=True)
    extent4326_maxx = models.FloatField(null=True,blank=True)
    extent4326_maxy = models.FloatField(null=True,blank=True)


class ZoneLayers(models.Model):
    zone = models.ForeignKey(ProjectZone, default=None, on_delete=models.CASCADE)
    layer = models.ForeignKey(Layer, default=None, on_delete=models.CASCADE)
    levels = models.IntegerField(null=False, default=0)
    tilematrixset = models.CharField(max_length=50) 
    format = models.CharField(max_length=50)
    extentid = models.CharField(max_length=50)
    version = models.BigIntegerField(null=True, blank=True)
    folder_prj = models.CharField(max_length=1024)
    running = models.BooleanField(default=False)
    bboxes = models.TextField(null=True, blank=True)
