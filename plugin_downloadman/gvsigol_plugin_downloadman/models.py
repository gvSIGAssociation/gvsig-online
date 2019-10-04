from __future__ import unicode_literals
from django.utils.translation import ugettext as _

from django.db import models

# Create your models here.
#Job

def define_translations():
    PENDING_AUTHORIZATION_STATUS = _('Pending authorization')
    """
        (PENDING_INITIAL_NOTIFICATION_STATUS, 'Initial notification pending', _('Initial notification pending')),
        (PENDING_FINAL_NOTIFICATION_STATUS, 'Final notification pending', _('Initial notification pending')),
        (PACKAGE_QUEUED_STATUS, 'Package queued', _('Package qeued')),
        (PACKAGED_STATUS, 'Packaged', _('Packaged')),
        (COMPLETED_STATUS, 'Completed', _('Completed')),
        (REJECTED_STATUS, 'Rejected', _('Rejected')),
        (HOLD_STATUS, 'On hold', _('On hold')),
        (CANCELLED_STATUS, 'Cancelled', _('Cancelled')),
        (PACKAGING_ERROR_STATUS, 'Packaging error', _('Packaging error')),
        (PERMANENT_PACKAGE_ERROR_STATUS, 'Permanent packaging error', _('Permanent packaging error')),
        (NOTIFICATION_ERROR_STATUS, 'Notification error', _('Notification error')),
        (PERMANENT_NOTIFICATION_ERROR_STATUS, 'Permanent notification error', _('Permanent notification error')),
    """

class AuthorizationRequestForm(models.Model):
    definition = models.TextField()
    current = models.BooleanField()

class DownloadRequest(models.Model):
    """
    A request to download one or several datasets. One request may have several associated resource
    locators, which describe the actual data to be included in the request
    """
    REGISTERED_REQUEST_NOTIFICATION_QUEUED = 'RG' # Queued for first user notification (request registered)
    READY_REQUEST_NOTIFICATION_QUEUED = 'RY' # Queued for user notification
    REJECTED_REQUEST_NOTIFICATION_QUEUED = 'RJ' # Queued for user notification
    FAILED_REQUEST_NOTIFICATION_QUEUED = 'FA' # Queued for user notification
    
    PENDING_AUTHORIZATION_STATUS = 'AU'
    PACKAGE_QUEUED_STATUS = 'QP' # Queued for package preparation
    PACKAGED_STATUS = 'CT' # The download package was sucessfully created
    COMPLETED_STATUS = 'CT' # The download package was sucessfully created and notified
    REJECTED_STATUS = 'RE' # Rejected or cancelled by the admins
    HOLD_STATUS = 'HO' # Set on hold by admins    
    CANCELLED_STATUS = 'CL' # Cancelled by the user
    PACKAGING_ERROR_STATUS = 'ER' # An error was found during preparation of the package
    PERMANENT_PACKAGE_ERROR_STATUS = 'PE' # A permanent error was found during preparation
    NOTIFICATION_COMPLETED_STATUS = 'NC'
    NOTIFICATION_ERROR_STATUS = 'NE' # An error was found during  notification
    PERMANENT_NOTIFICATION_ERROR_STATUS = 'NP' # A permanent error was found during notification

    REQUEST_STATUS_CHOICES = (
        (PENDING_AUTHORIZATION_STATUS, 'Pending authorization'),
        (PACKAGE_QUEUED_STATUS, 'Package queued'),
        (PACKAGED_STATUS, 'Packaged'),
        (COMPLETED_STATUS, 'Completed'),
        (REJECTED_STATUS, 'Rejected'),
        (HOLD_STATUS, 'On hold'),
        (CANCELLED_STATUS, 'Cancelled'),
        (PACKAGING_ERROR_STATUS, 'Packaging error'),
        (PERMANENT_PACKAGE_ERROR_STATUS, 'Permanent packaging error'),
    )
    NOTIFICATION_STATUS_CHOICES = (
        (NOTIFICATION_COMPLETED_STATUS, 'Notification completed'),
        (NOTIFICATION_ERROR_STATUS, 'Notification error'),
        (PERMANENT_NOTIFICATION_ERROR_STATUS, 'Permanent notification error'),
    )
    
    #definition = models.TextField()
    requested_by_external = models.CharField(max_length=500)
    requested_by_user = models.CharField(max_length=500, null=True, blank=True)
    requested_date = models.DateTimeField(auto_now_add=True)
    # number of seconds the download link will be up since notified to the user
    validity = models.IntegerField()
    authorization_request = models.TextField()
    pending_authorization = models.BooleanField()
    # status: 
    # - pending authorization, queued for preparation, ready for download,
    # cancelled, on hold, requeued for preparation, error...
    request_status = models.CharField(max_length=2, choices=REQUEST_STATUS_CHOICES)
    notification_status = models.CharField(max_length=2, null=True, choices=NOTIFICATION_STATUS_CHOICES)
    package_retry_count = models.PositiveIntegerField(default=0)
    notify_retry_count = models.PositiveIntegerField(default=0)
    request_random_id = models.TextField(db_index=True)
    json_request = models.TextField() # we keep the request as received from the client for debugging purposes
    language = models.CharField(max_length=50, blank=True)

class DownloadLink(models.Model):
    contents = models.OneToOneField(
        DownloadRequest,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    prepared_download_path = models.FilePathField(max_length=1000) # the path to the file to download
    download_count = models.PositiveIntegerField(default=0)
    valid_to=models.DateTimeField(db_index=True)
    link_random_id = models.TextField(db_index=True)

# class DownmanConfig(models.Model):
    # number of seconds the download link will be up since notified to the user
    #default_validity  = models.IntegerField()
    #default_validation_form = models.ForeignKey('ValidationForm', null=True, on_delete=models.SET_NULL)
    #direct_download_threshold_kb  = models.IntegerField()

class ResourceSettings(models.Model):
    layer_uuid = models.TextField(unique=True)
    restricted = models.BooleanField()

FORMAT_PARAM_NAME = 'format'


class ResourceLocator(models.Model):
    GEONETWORK_UUID = 'GN'
    GVSIGOL_LAYER_ID = 'GV'
    
    GVSIGOL_DATA_SOURCE_TYPE = 'GVSIGOL_DATA_SOURCE'
    GEONETWORK_CATALOG_DATA_SOURCE_TYPE = 'GEONET_DATA_SOURCE'
    
    OGC_WFS_RESOURCE_TYPE = 'OGC_WFS_RESOURCE_TYPE'
    OGC_WCS_RESOURCE_TYPE = 'OGC_WCS_RESOURCE_TYPE'
    HTTP_LINK_RESOURCE_TYPE = 'HTTP_LINK_TYPE'
    
    ID_TYPES = (
        (GEONETWORK_UUID, GEONETWORK_CATALOG_DATA_SOURCE_TYPE),
        (GVSIGOL_LAYER_ID, GVSIGOL_DATA_SOURCE_TYPE)
    )
    
    # res_einternal_id = models.PositiveIntegerField()
    #ds_type = models.CharField(max_length=3, choices=RESOURCE_TYPES_CHOICES)
    data_source  = models.TextField() # description of the layer data source and download params
    layer_id = models.TextField(null=True, blank=True)
    layer_id_type = models.CharField(max_length=2, choices=ID_TYPES)
    #resolved_layer_url = models.TextField(null=True, blank=True)
    name = models.TextField()
    title = models.TextField()
    #mime_type = models.CharField(max_length=255)
    request = models.ForeignKey('DownloadRequest', on_delete=models.CASCADE)

class DownloadLog(models.Model):
    layer_id = models.TextField(null=True, blank=True)
    layer_id_type = models.CharField(max_length=2, choices=ResourceLocator.ID_TYPES)
    date = models.DateTimeField(auto_now_add=True)
    request = models.ForeignKey('DownloadRequest', on_delete=models.CASCADE)

def get_default_validity():
    # TODO: we could get it for a settings entry, or a settings table in DB
    return 604800  # = 7 days


def get_packaging_max_retry_time():
    # TODO: we could get it for a settings entry, or a settings table in DB
    return 518400  # = 6 days


def get_mail_max_retry_time():
    # TODO: we could get it for a settings entry, or a settings table in DB
    return 518400  # = 6 days