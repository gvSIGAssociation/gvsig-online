from __future__ import unicode_literals
from django.utils.translation import ugettext_noop as _
from django.utils.translation import ugettext

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
import gvsigol_core
import apps
from gvsigol_core.models import GolSettings

SETTINGS_KEY_VALIDITY = 'default_link_validity'
DEFAULT_VALIDITY = 604800 # seconds = 7 days
SETTINGS_KEY_MAX_PUBLIC_DOWNLOAD_SIZE = 'max_public_download_size'
DEFAULT_MAX_PUBLIC_DOWNLOAD_SIZE = 300 # MB
SETTINGS_KEY_SHOPPING_CART_MAX_ITEMS = 'shopping_cart_max_items'
DEFAULT_SHOPPING_CART_MAX_ITEMS = 0 # means no limit

class AuthorizationRequestForm(models.Model):
    definition = models.TextField()
    current = models.BooleanField()

class DownloadRequest(models.Model):
    """
    A request to download one or several datasets. One request may have several associated resource
    locators, which describe the actual data to be included in the request
    """
    REQUEST_QUEUED_STATUS = 'RQ' # Queued for package preparation
    PROCESSING_STATUS = 'PR' # Queued for package preparation
    COMPLETED_STATUS = 'CT' # The download package was sucessfully created and notified
    COMPLETED_WITH_ERRORS = 'CE' # An error was found during preparation of the package
    REJECTED_STATUS = 'RJ' # The download package was rejected by the admins
    QUEUEING_ERROR = 'QE' # The request could not be queued

    INITIAL_NOTIFICATION_COMPLETED_STATUS = 'NI'
    NOTIFICATION_COMPLETED_STATUS = 'NC'
    NOTIFICATION_ERROR_STATUS = 'NE' # An error was found during  notification
    PERMANENT_NOTIFICATION_ERROR_STATUS = 'NP' # A permanent error was found during notification

    REQUEST_STATUS_CHOICES = (
        (REQUEST_QUEUED_STATUS, _('Request queued')),
        (PROCESSING_STATUS, _('Processing request')),
        (COMPLETED_STATUS, _('Completed')),
        (COMPLETED_WITH_ERRORS, _('Completed with errors')),
        (REJECTED_STATUS, _('Rejected')),
        (QUEUEING_ERROR, _('Error queueing request')),
    )
    NOTIFICATION_STATUS_CHOICES = (
        (INITIAL_NOTIFICATION_COMPLETED_STATUS, _('Initial notification completed')),
        (NOTIFICATION_COMPLETED_STATUS, _('Notification completed')),
        (NOTIFICATION_ERROR_STATUS, _('Notification error')),
        (PERMANENT_NOTIFICATION_ERROR_STATUS, _('Permanent notification error')),
    )
    
    #definition = models.TextField()
    requested_by_external = models.CharField(max_length=500) # the email for non authenticated users
    requested_by_user = models.CharField(max_length=500, null=True, blank=True) # the user name for authenticated users
    requested_date = models.DateTimeField(auto_now_add=True)
    # number of seconds the download link will be up since notified to the user
    validity = models.IntegerField()
    #authorization_request = models.TextField(blank=True, default='')
    request_status = models.CharField(max_length=2, default=REQUEST_QUEUED_STATUS, choices=REQUEST_STATUS_CHOICES, db_index=True)
    notification_status = models.CharField(max_length=2, null=True, choices=NOTIFICATION_STATUS_CHOICES)
    package_retry_count = models.PositiveIntegerField(default=0)
    notify_retry_count = models.PositiveIntegerField(default=0)
    request_random_id = models.TextField(db_index=True)
    json_request = models.TextField() # we keep the request as received from the client for debugging purposes
    language = models.CharField(max_length=50, blank=True)
    pending_authorization = models.BooleanField(default=False, db_index=True)
    generic_request = models.BooleanField(default=False)
    shared_view_url = models.TextField(null=True, blank=True, default='')
    @property
    def status_desc(self):
        for (choice_code, choice_desc) in DownloadRequest.REQUEST_STATUS_CHOICES:
            if self.request_status == choice_code:
                return ugettext(choice_desc)
    @property
    def status_active(self):
        if self.active:
            return self.status_desc + ' - ' + ugettext('Active')
        else:
            return self.status_desc + ' - ' +ugettext('Archived')
    @property
    def status_authorization(self):
        if self.pending_authorization:
            return self.status_desc + ' - ' + ugettext('Awaiting approval')
        else:
            return self.status_desc
    
    @property
    def active(self):
        if (self.request_status == DownloadRequest.REQUEST_QUEUED_STATUS or self.request_status == DownloadRequest.PROCESSING_STATUS) \
                and self.pending_authorization:
            return True
        now = timezone.now()
        for locator in self.resourcelocator_set.all():
            if not locator.canceled:
                # the Request is active if there is any associated ResourceLocator in the following statuses
                if locator.status in [
                        ResourceLocator.RESOURCE_QUEUED_STATUS,
                        ResourceLocator.WAITING_SPACE_STATUS,
                        ResourceLocator.TEMPORAL_ERROR_STATUS,
                        ResourceLocator.HOLD_STATUS,
                        ]:
                    return True
        for downloadLink in self.downloadlink_set.all():
            # the Request is also active if there is any associated DownloadLink which is currently valid
            if downloadLink.valid_to > now and downloadLink.status == DownloadLink.PROCESSED_STATUS:
                return True
        return False 

    @property
    def contents_desc(self):
        locators = self.resourcelocator_set.all()
        if len(locators)==1:
            return locators[0].fq_title_name
        else:
            return ugettext('Multiresource package')

    @property
    def contents_details(self):
        locators = self.resourcelocator_set.all()
        return ", ".join([ locator.fq_title_name for locator in locators ])
    
    @property
    def notification_status_desc(self):
        for (choice_code, choice_desc) in DownloadRequest.NOTIFICATION_STATUS_CHOICES:
            if self.notification_status == choice_code:
                return ugettext(choice_desc)
            
# class DownmanConfig(models.Model):
    # number of seconds the download link will be up since notified to the user
    #default_validity  = models.IntegerField()
    #default_validation_form = models.ForeignKey('ValidationForm', null=True, on_delete=models.SET_NULL)
    #direct_download_threshold_kb  = models.IntegerField()

#class ResourceSettings(models.Model):
#    layer_uuid = models.TextField(unique=True)
#    restricted = models.BooleanField()

FORMAT_PARAM_NAME = 'format'
SPATIAL_FILTER_TYPE_PARAM_NAME = 'spatial_filter_type'
SPATIAL_FILTER_GEOM_PARAM_NAME = 'spatial_filter_geom'
SPATIAL_FILTER_BBOX_PARAM_NAME = 'spatial_filter_bbox'


class DownloadLink(models.Model):
    PROCESSED_STATUS = 'PR'
    USER_CANCELED_STATUS = 'UC'
    ADMIN_CANCELED_STATUS = 'AC'

    STATUS_CHOICES = (
        (PROCESSED_STATUS, _('Processed #sing#')),
        (USER_CANCELED_STATUS, _('Cancelled by the user')),
        (ADMIN_CANCELED_STATUS, _('Cancelled by the administrator')),
    )
    @property
    def active(self):
        if self.valid_to > timezone.now() and self.status == DownloadLink.PROCESSED_STATUS:
            return True
        return False
    @property
    def status_desc(self):
        for (choice_code, choice_desc) in DownloadLink.STATUS_CHOICES:
            if self.status == choice_code:
                return ugettext(choice_desc)
    @property
    def status_active(self):
        if self.status == DownloadLink.PROCESSED_STATUS:
            status_txt = ugettext('Processed')
        else:
            status_txt = ugettext('Canceled')
        if not self.is_valid:
            return status_txt + " - " + ugettext('Expired')
        return status_txt
    
    @property
    def is_valid(self):
        if self.valid_to > timezone.now():
            return True
        return False
    
    @property
    def contents_details(self):
        if self.is_auxiliary:
            locators = self.resourcelocator_set.all()
            return ", ".join([ locator.fq_title + u" [" + self.name + u"]" for locator in locators ])
        else:
            locators = self.resourcelocator_set.all()
            return ", ".join([ locator.fq_title_name for locator in locators ])
    
    request = models.ForeignKey('DownloadRequest', on_delete=models.CASCADE, db_index=False)
    prepared_download_path = models.TextField(null=True, blank=True)
    resolved_url = models.TextField(null=True, blank=True, default=None)
    valid_to=models.DateTimeField(db_index=True)
    link_random_id = models.TextField(db_index=True, unique=True)
    status = models.CharField(max_length=2, default=PROCESSED_STATUS, choices=STATUS_CHOICES)
    name = models.TextField(null=True, default=None)
    is_auxiliary = models.BooleanField(default=False)
    is_temporary = models.BooleanField(default=False)
    download_count = models.PositiveIntegerField(default=0)
    class Meta:
        indexes = [
            models.Index(fields=['request', 'valid_to', 'status']),
            ]

class ResourceLocator(models.Model):
    GEONETWORK_UUID = 'GN'
    GVSIGOL_LAYER_ID = 'GV'
    
    GVSIGOL_DATA_SOURCE_TYPE = 'GVSIGOL_DATA_SOURCE'
    GEONETWORK_CATALOG_DATA_SOURCE_TYPE = 'GEONET_DATA_SOURCE'
    
    OGC_WFS_RESOURCE_TYPE = 'OGC_WFS_RESOURCE_TYPE'
    OGC_WCS_RESOURCE_TYPE = 'OGC_WCS_RESOURCE_TYPE'
    HTTP_LINK_RESOURCE_TYPE = 'HTTP_LINK_TYPE' # TODO: rename to URL_RESOURCE_TYPE ??
    
    ID_TYPES = (
        (GEONETWORK_UUID, GEONETWORK_CATALOG_DATA_SOURCE_TYPE),
        (GVSIGOL_LAYER_ID, GVSIGOL_DATA_SOURCE_TYPE)
    )
    
    RESOURCE_QUEUED_STATUS = 'QD' # Queued for package preparation
    WAITING_SPACE_STATUS = 'SP' # Queued for package preparation
    PROCESSED_STATUS = 'PD' # The download package was sucessfully created
    HOLD_STATUS = 'HO' # Set on hold by admins    
    TEMPORAL_ERROR_STATUS = 'TE' # An error was found during preparation of the package
    PERMANENT_ERROR_STATUS = 'PE' # A permanent error was found during preparation

    REQUEST_STATUS_CHOICES = (
        (RESOURCE_QUEUED_STATUS, _('Resource queued')),
        (WAITING_SPACE_STATUS, _('Queued, waiting for free space')),
        (PROCESSED_STATUS, _('Processed')),
        (HOLD_STATUS, _('On hold')),
        (TEMPORAL_ERROR_STATUS, _('Temporal error')),
        (PERMANENT_ERROR_STATUS, _('Permanent error')),
    )
    
    AUTHORIZATION_NOT_PROCESSED = 0
    AUTHORIZATION_PENDING = 1
    AUTHORIZATION_ACCEPTED = 2
    AUTHORIZATION_REJECTED = 3
    AUTHORIZATION_NOT_REQUIRED = 4
    AUTHORIZATION_CHOICES = (
        (AUTHORIZATION_NOT_PROCESSED, _('Not processed')),
        (AUTHORIZATION_NOT_REQUIRED, _('Not required')),
        (AUTHORIZATION_PENDING, _('Pending')),
        (AUTHORIZATION_ACCEPTED, _('Accepted')),
        (AUTHORIZATION_REJECTED, _('Rejected')),
        )
    
    @property
    def status_desc(self):
        for (choice_code, choice_desc) in ResourceLocator.REQUEST_STATUS_CHOICES:
            if self.status == choice_code:
                return ugettext(choice_desc)
    @property
    def status_canceled(self):
        if self.canceled:
            return self.status_desc + " + " + ugettext('Canceled')
        return self.status_desc
    @property
    def authorization_desc(self):
        for (choice_code, choice_desc) in ResourceLocator.AUTHORIZATION_CHOICES:
            if self.authorization == choice_code:
                return ugettext(choice_desc)
    
    @property
    def status_detail(self):
        return self.status_canceled + " - " + ugettext('Approval: ') + self.authorization_desc
    
    # res_einternal_id = models.PositiveIntegerField()
    #ds_type = models.CharField(max_length=3, choices=RESOURCE_TYPES_CHOICES)
    data_source  = models.TextField() # description of the layer data source and download params
    layer_id = models.TextField(null=True, blank=True)
    layer_id_type = models.CharField(max_length=2, choices=ID_TYPES)
    name = models.TextField()
    title = models.TextField()
    layer_name = models.TextField()
    layer_title = models.TextField()
    @property
    def fq_name(self):
        return self.layer_name + u" - " + self.name
    @property
    def fq_title(self):
        if self.layer_title == self.title:
            return self.title
        return self.layer_title + u" - " + self.title
    @property
    def fq_title_name(self):
        if self.layer_title == self.title:
            return self.layer_title + u" [" + self.name + u"]"
        return self.layer_title + u" - " + self.title + u" [" + self.name + u"]"
    authorization = models.PositiveSmallIntegerField(default=AUTHORIZATION_NOT_PROCESSED, choices=AUTHORIZATION_CHOICES)
    status = models.CharField(max_length=2, default=RESOURCE_QUEUED_STATUS, choices=REQUEST_STATUS_CHOICES)
    download_count = models.PositiveIntegerField(default=0)
    resolved_url =  models.TextField(null=True, blank=True)
    is_dynamic = models.BooleanField(default=False)
    canceled = models.BooleanField(default=False)
    #download_link = models.ForeignKey('DownloadLink', on_delete=models.CASCADE, null=True)
    download_links = models.ManyToManyField('DownloadLink')
    request = models.ForeignKey('DownloadRequest', on_delete=models.CASCADE, db_index=False)
    #mime_type = models.CharField(max_length=255)
    class Meta:
        indexes = [
            models.Index(fields=['request', 'canceled', 'status', 'authorization',]),
            ]
    

class LayerProxy(models.Model):
    """
    A reference to a layer, to be used in download statistics.
    Statistics are calculated based on model instances.
    Since there is no model for catalog layers, we need to create proxy log tables
    """
    layer_id = models.TextField()
    layer_id_type = models.CharField(max_length=2, choices=ResourceLocator.ID_TYPES)
    name = models.TextField()
    title = models.TextField()
    title_name = models.TextField()
    class Meta:
        indexes = [
            models.Index(fields=['layer_id', 'layer_id_type']),
            ]

class LayerResourceProxy(models.Model):
    """
    A reference to a layer resource, i.e., any file attached to the layer in the metadata
    OnlineResource, such as a downloadable version of the layer, a PDF, etc.
    
    Statistics are calculated based on model instances.
    Since there is no model for catalog layers, we need to create proxy log tables
    """
    name = models.TextField()
    title = models.TextField()
    fq_name = models.TextField()
    fq_title = models.TextField()
    fq_title_name = models.TextField()
    layer = models.ForeignKey('LayerProxy', on_delete=models.CASCADE)

def get_default_validity():
    return GolSettings.objects.get_value(apps.PLUGIN_NAME, SETTINGS_KEY_VALIDITY, DEFAULT_VALIDITY)

def get_max_public_download_size():
    return GolSettings.objects.get_value(apps.PLUGIN_NAME, SETTINGS_KEY_MAX_PUBLIC_DOWNLOAD_SIZE, DEFAULT_MAX_PUBLIC_DOWNLOAD_SIZE)

def get_shopping_cart_max_items():
    return int(GolSettings.objects.get_value(apps.PLUGIN_NAME, SETTINGS_KEY_SHOPPING_CART_MAX_ITEMS, DEFAULT_SHOPPING_CART_MAX_ITEMS))

def get_packaging_max_retry_time():
    # TODO: we could get it for a settings entry, or a settings table in DB
    return 518400  # = 6 days


def get_mail_max_retry_time():
    # TODO: we could get it for a settings entry, or a settings table in DB
    return 518400  # = 6 days
