from django.db import models
from django.urls import reverse
from gvsigol import settings
from gvsigol_auth.models import UserGroup
from gvsigol_services.models import LayerGroup, Layer
from django.utils.translation import gettext_noop as _
from gvsigol.basetypes import CloneConf
from gvsigol_auth import auth_backend
from django.contrib.auth.models import User
from urllib.parse import quote, urlparse, urljoin
import json
import logging

LOG_NAME = 'gvsigol'

def get_default_logo_image():
    return settings.STATIC_URL + 'img/logo_principal.png'

def get_default_project_image():
    return settings.STATIC_URL + 'img/no_project.png'

def get_default_application_image():
    return settings.STATIC_URL + 'img/no_project.png'

def _get_spa_project_url(projectid):
    return urljoin(settings.FRONTEND_BASE_URL + "/viewer/", quote(str(projectid) + "/"))

def _get_spa_mobileproject_url(projectid):
    return urljoin(settings.FRONTEND_BASE_URL + "/viewer/mobile/", quote(str(projectid) + "/"))


class Project(models.Model):
    REACT_SPA_UI='react_spa_ui'
    REACT_SPA_UI_TITLE=_('Current (React)')
    BOOTSTRAP_UI = 'bootstrap_ui'
    BOOTSTRAP_UI_TITLE=_('Classic (Bootstrap)')
    VIEWER_UI_CHOICES = [
        (REACT_SPA_UI, REACT_SPA_UI_TITLE),
        (BOOTSTRAP_UI, BOOTSTRAP_UI_TITLE),
    ]
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
    custom_overview = models.BooleanField(default=False)
    layer_overview = models.CharField(max_length=250, null=True, blank=True, default=None)
    viewer_default_crs = models.CharField(max_length=250, null=True, blank=True, default='EPSG:3857')
    viewer_preferred_ui = models.TextField(choices=VIEWER_UI_CHOICES, blank=True, default="")
    
    def __str__(self):
        return self.name + ' - ' + self.description
    
    def clone(self, target_datastore, name, title, clone_conf=None):
        if not clone_conf:
            clone_conf = CloneConf()
        old_pid = self.pk
        self.pk = None
        self.name = name
        self.title = title
        self.save()
        new_project_instance = Project.objects.get(id=self.pk)

        try:
            new_toc = json.loads(new_project_instance.toc_order)
        except:
            new_toc = {}
        if clone_conf.recursive:
            old_project = Project.objects.get(id=old_pid)
            for prj_lg in old_project.projectlayergroup_set.all():
                new_prj_lg = prj_lg.clone(project=new_project_instance, target_datastore=target_datastore, clone_conf=clone_conf)
                try:
                    group_order = new_toc[new_prj_lg.layer_group._cloned_from_name]
                    group_order["name"] = new_prj_lg.layer_group._cloned_from_name
                    #for lname in group_order["layers"]:
                    for lname, lorder in group_order["layers"].copy().items():
                        #lorder = group_order["layers"][lname]
                        try:
                            new_lyr_name = new_prj_lg.layer_group._cloned_lyr_name_map[lname]
                            del group_order["layers"][lname]
                            lorder["name"] = new_lyr_name
                            group_order["layers"][new_lyr_name] = lorder
                        except KeyError:
                            pass
                        except:
                            logging.getLogger(LOG_NAME).exception(f"Error cloning layer order in toc: {lname}")
                    del new_toc[new_prj_lg.layer_group._cloned_from_name]
                    new_toc[new_prj_lg.layer_group.name] = group_order
                except AttributeError:
                    #if not new_toc[new_prj_lg.layer_group.name]:
                    #    del 
                    pass
                except:
                    logging.getLogger(LOG_NAME).exception("Error cloning toc order")
            
            if clone_conf.permissions != CloneConf.PERMISSION_SKIP:
                for prj_ur in old_project.projectrole_set.all():
                    prj_ur.clone(project=new_project_instance)
        new_project_instance.toc_order = json.dumps(new_toc)
        new_project_instance.save()
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
    
    
    def can_read(self, request_or_user):
        """
        Checks whether the user is allowed to load this project

        Parameters
        ----------
        request_or_user: Request | HttpRequest | User
            A Django Request object | A DRF HttpRequest object | A Django User object

        Returns
        -------
        True if the user is allowed to load this project, False otherwise
        """
        if self.is_public:
            return True
        if isinstance(request_or_user, User):
            user = request_or_user
        else:
            user = request_or_user.user
        if user.is_superuser:
            return True
        elif user.username == self.created_by:
            return True
        user_roles = auth_backend.get_roles(request_or_user)
        return self.projectrole_set.filter(permission=ProjectRole.PERM_READ, role__in=user_roles).exists()

    def can_manage(self, request_or_user):
        """
        Checks whether the user is allowed to manage (modify settings, set permissions, etc) this project.

        Parameters
        ----------
        request_or_user: Request | HttpRequest | User
            A Django Request object | A DRF HttpRequest object | A Django User object

        Returns
        -------
        True if the user is allowed to manage this project, False otherwise
        """
        if isinstance(request_or_user, User):
            user = request_or_user
        else:
            user = request_or_user.user
        if user.is_superuser:
            return True
        elif user.is_staff:
            if user.username == self.created_by:
                return True
            user_roles = auth_backend.get_roles(request_or_user)
            return self.projectrole_set.filter(permission=ProjectRole.PERM_MANAGE, role__in=user_roles).exists()

    @property
    def url(self):
        if self.viewer_preferred_ui == Project.REACT_SPA_UI:
            return _get_spa_project_url(self.id)
        else:
            return settings.BASE_URL + reverse('load', kwargs={'project_name': self.name})
    
    @property
    def mobile_url(self):
        if self.viewer_preferred_ui == Project.REACT_SPA_UI:
            return _get_spa_mobileproject_url(self.id)
        else:
            return settings.BASE_URL + reverse('load', kwargs={'project_name': self.name})

class ProjectRole(models.Model):
    PERM_READ='read'
    PERM_MANAGE = 'manage'
    PERMISSION_CHOICES = [
        (PERM_READ, PERM_READ),
        (PERM_MANAGE, PERM_MANAGE),
    ]
    project = models.ForeignKey(Project, default=None, on_delete=models.CASCADE)
    role = models.TextField()
    permission = models.TextField(choices=PERMISSION_CHOICES, default=PERM_READ)
    
    class Meta:
        indexes = [
            models.Index(fields=['project', 'permission', 'role']),
        ]
        constraints = [
           models.UniqueConstraint(fields=['project', 'permission', 'role'], name='unique_permission_role_and_project')
        ]
    
    def __str__(self):
        return self.project.name + ' - ' + self.role
    
    def clone(self, project):
        self.pk = None
        self.project = project
        self.save()
        return ProjectRole.objects.get(id=self.pk)

class ProjectLayerGroup(models.Model):
    project = models.ForeignKey(Project, default=None, on_delete=models.CASCADE)
    layer_group = models.ForeignKey(LayerGroup, default=None, on_delete=models.CASCADE)
    multiselect = models.BooleanField(default=True)
    baselayer_group = models.BooleanField(default=False)
    default_baselayer = models.IntegerField(null=True, blank=True)
    
    def __str__(self):
        return self.project.name + ' - ' + self.layer_group.name
    
    def clone(self, project=None, target_datastore=None, clone_conf=None):
        if not clone_conf:
            clone_conf = CloneConf()
        if not clone_conf.recursive:
            return
        if self.baselayer_group:
            if clone_conf.base_lyrgroup == CloneConf.LYRGROUP_SKIP:
                return
        else: # non base layer groups are always cloned
            self.layer_group = self.layer_group.clone(target_datastore=target_datastore, clone_conf=clone_conf)
        
        self.pk = None
        if project:
            self.project = project
        self.save()
        new_instance = ProjectLayerGroup.objects.get(id=self.pk)
        new_instance.layer_group = self.layer_group # to include _cloned_from_name, _cloned_from_instance, _cloned_lyr_name_map, _cloned_lyr_instance_map
        return new_instance

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
    pkgassigned = models.CharField(max_length=50, null=True)


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
    pkgassigned = models.CharField(max_length=50, null=True)

class Application(models.Model):
    name = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=100, null=True, blank=True)
    description = models.CharField(max_length=250, null=True, blank=True)
    url = models.CharField(max_length=250, null=True, blank=True)
    # see also image_url property
    image = models.ImageField(upload_to='images', default='', null=True, blank=True)
    conf = models.TextField(null=True, blank=True)
    is_public = models.BooleanField(default=False)
    created_by = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name + ' - ' + self.description
    
    @property
    def image_url(self):
        """
        Returns URL to the application image if defined, otherwise it returns get_default_application_image()
        otherwise. This method always returns a relative URL, such as
        '/media/images/logo_AMQtcXf.png'
        or
        '/static/img/no_project.png'.
        
        This property is recommended instead of directly using image.url because
        the default application image is outside media dir, so the url property does
        not build a valid URL.
        """
        if not self.image:
            return get_default_application_image()
        return self.image.url.replace(settings.BASE_URL, '')
    
    @property
    def absurl(self):
        app_url = self.url.format(id=quote(str(self.id), safe=''), name=quote(self.name, safe=''))
        parsed = urlparse(app_url)
        if parsed.netloc:
            return app_url
        elif parsed.path.startswith('/'):  # absolute path reference, ignore path from FRONTEND_BASE_URL
            return urljoin(settings.FRONTEND_BASE_URL + "/", quote(app_url))
        else:
            return urljoin(settings.FRONTEND_BASE_URL + "/", quote(app_url))
    
class ApplicationRole(models.Model):
    application = models.ForeignKey(Application, default=None, on_delete=models.CASCADE)
    role = models.TextField()
    
    class Meta:
        indexes = [
            models.Index(fields=['application', 'role']),
        ]
    
    def __str__(self):
        return self.application.name + ' - ' + self.role
