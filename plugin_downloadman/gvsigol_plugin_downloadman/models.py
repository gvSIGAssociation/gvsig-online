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
    PENDING_INITIAL_NOTIFICATION_STATUS = 'IN'
    PENDING_FINAL_NOTIFICATION_STATUS = 'FN'
    PACKAGE_QUEUED_STATUS = 'QP' # Queued for package preparation
    PACKAGED_STATUS = 'CT' # The download package was sucessfully created
    COMPLETED_STATUS = 'CT' # The download package was sucessfully created and notified
    REJECTED_STATUS = 'RE' # Rejected or cancelled by the admins
    HOLD_STATUS = 'HO' # Set on hold by admins    
    CANCELLED_STATUS = 'CL' # Cancelled by the user
    PACKAGING_ERROR_STATUS = 'RE' # An error was found during preparation of the package
    PERMANENT_PACKAGE_ERROR_STATUS = 'RE' # A permanent error was found during preparation
    NOTIFICATION_ERROR_STATUS = 'RE' # An error was found during  notification
    PERMANENT_NOTIFICATION_ERROR_STATUS = 'RE' # A permanent error was found during notification

    REQUEST_STATUS_CHOICES = (
        (PENDING_AUTHORIZATION_STATUS, 'Pending authorization'),
        (PENDING_INITIAL_NOTIFICATION_STATUS, 'Initial notification pending'),
        (PENDING_FINAL_NOTIFICATION_STATUS, 'Final notification pending'),
        (PACKAGE_QUEUED_STATUS, 'Package queued'),
        (PACKAGED_STATUS, 'Packaged'),
        (COMPLETED_STATUS, 'Completed'),
        (REJECTED_STATUS, 'Rejected'),
        (HOLD_STATUS, 'On hold'),
        (CANCELLED_STATUS, 'Cancelled'),
        (PACKAGING_ERROR_STATUS, 'Packaging error'),
        (PERMANENT_PACKAGE_ERROR_STATUS, 'Permanent packaging error'),
        (NOTIFICATION_ERROR_STATUS, 'Notification error'),
        (PERMANENT_NOTIFICATION_ERROR_STATUS, 'Permanent notification error'),
    )
    
    """
    Notifications are queued, we need to know
    """
    NOTIFICATION_STATUS_CHOICES = (
        (REGISTERED_REQUEST_NOTIFICATION_QUEUED, 'Registered request notification has been queued'),
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
    retry_count = models.PositiveIntegerField(default=0)
    request_random_id = models.TextField(db_index=True)
    json_request = models.TextField() # we keep the request as received from the client for debugging purposes

class DownloadLink(models.Model):
    contents = models.ForeignKey('DownloadRequest', on_delete=models.CASCADE)
    prepared_download = models.FileField() # the path to the file to download
    download_count = models.PositiveIntegerField(default=0)
    valid_to=models.DateTimeField(db_index=True)
    request_random_id = models.TextField(db_index=True)

# class DownmanConfig(models.Model):
    # number of seconds the download link will be up since notified to the user
    #default_validity  = models.IntegerField()
    #default_validation_form = models.ForeignKey('ValidationForm', null=True, on_delete=models.SET_NULL)
    #direct_download_threshold_kb  = models.IntegerField()

class ResourceSettings(models.Model):
    layer_uuid = models.TextField(unique=True)
    restricted = models.BooleanField()

class ResourceLocator(models.Model):
    CATALOG_SOURCE_TYPE = 'CT'
    GVSIGOL_LAYER = 'GV'
    GEOSERVER_SOURCE_TYPE = 'GS'
    FILEPATH_SOURCE_TYPE = 'FI'
    FOLDERPATH_SOURCE_TYPE = 'FD'
    HTTP_LINK_SOURCE_TYPE = 'HT'
    
    GEONETWORK_UUID = 'GN'
    GVSIGOL_LAYER_ID = 'GV'
    
    RESOURCE_TYPES_CHOICES = (
        (CATALOG_SOURCE_TYPE, 'Catalog'),
        (GVSIGOL_LAYER, 'gvSIGOL Layer'),
        (GEOSERVER_SOURCE_TYPE, 'Geoserver'),
        (FILEPATH_SOURCE_TYPE, 'File Path'),
        (FOLDERPATH_SOURCE_TYPE, 'Folder Path'),
        (HTTP_LINK_SOURCE_TYPE, 'Http Link'),
    )
    
    ID_TYPES = (
        (GEONETWORK_UUID, 'GEONETWORK_UUID'),
        (GVSIGOL_LAYER_ID, 'GVSIGOL_LAYER_ID')
    )
    
    # res_internal_id = models.PositiveIntegerField()
    ds_type = models.CharField(max_length=2, choices=RESOURCE_TYPES_CHOICES)
    data_source  = models.TextField() # description of the layer data source and download params
    layer_id = models.TextField(null=True, blank=True)
    laye_id_type = models.CharField(max_length=2, choices=ID_TYPES)
    #resolved_layer_url = models.TextField(null=True, blank=True)
    name = models.TextField()
    title = models.TextField()
    #mime_type = models.CharField(max_length=255)
    request = models.ForeignKey('DownloadRequest', on_delete=models.CASCADE)

class DownloadLog(models.Model):
    layer_id = models.TextField(null=True, blank=True)
    laye_id_type = models.CharField(max_length=2, choices=ResourceLocator.ID_TYPES)
    date = models.DateTimeField(auto_now_add=True)
    request = models.ForeignKey('DownloadRequest', on_delete=models.CASCADE)

def get_default_validity():
    # TODO: we could get it for a settings entry, or a settings table in DB
    return 604800  # = 7 days


def get_packaging_max_retry_time():
    # TODO: we could get it for a settings entry, or a settings table in DB
    return 518400  # = 6 days
