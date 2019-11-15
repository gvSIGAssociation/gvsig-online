from __future__ import unicode_literals
from django.utils.translation import ugettext_noop as _

from django.db import models


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
    QUEUEING_ERROR = 'QE' # The request could not be queued

    NOTIFICATION_COMPLETED_STATUS = 'NC'
    NOTIFICATION_ERROR_STATUS = 'NE' # An error was found during  notification
    PERMANENT_NOTIFICATION_ERROR_STATUS = 'NP' # A permanent error was found during notification

    REQUEST_STATUS_CHOICES = (
        (REQUEST_QUEUED_STATUS, _('Request queued')),
        (PROCESSING_STATUS, _('Processing request')),
        (COMPLETED_STATUS, _('Completed')),
        (COMPLETED_WITH_ERRORS, _('Completed with errors')),
        (QUEUEING_ERROR, _('Error queueing request')),
    )
    NOTIFICATION_STATUS_CHOICES = (
        (NOTIFICATION_COMPLETED_STATUS, _('Notification completed')),
        (NOTIFICATION_ERROR_STATUS, _('Notification error')),
        (PERMANENT_NOTIFICATION_ERROR_STATUS, _('Permanent notification error')),
    )
    
    #definition = models.TextField()
    requested_by_external = models.CharField(max_length=500)
    requested_by_user = models.CharField(max_length=500, null=True, blank=True)
    requested_date = models.DateTimeField(auto_now_add=True)
    # number of seconds the download link will be up since notified to the user
    validity = models.IntegerField()
    authorization_request = models.TextField()
    # status: 
    # - pending authorization, queued for preparation, ready for download,
    # cancelled, on hold, requeued for preparation, error...
    request_status = models.CharField(max_length=2, default=REQUEST_QUEUED_STATUS, choices=REQUEST_STATUS_CHOICES, db_index=True)
    notification_status = models.CharField(max_length=2, null=True, choices=NOTIFICATION_STATUS_CHOICES)
    package_retry_count = models.PositiveIntegerField(default=0)
    notify_retry_count = models.PositiveIntegerField(default=0)
    request_random_id = models.TextField(db_index=True)
    json_request = models.TextField() # we keep the request as received from the client for debugging purposes
    language = models.CharField(max_length=50, blank=True)

# class DownmanConfig(models.Model):
    # number of seconds the download link will be up since notified to the user
    #default_validity  = models.IntegerField()
    #default_validation_form = models.ForeignKey('ValidationForm', null=True, on_delete=models.SET_NULL)
    #direct_download_threshold_kb  = models.IntegerField()

#class ResourceSettings(models.Model):
#    layer_uuid = models.TextField(unique=True)
#    restricted = models.BooleanField()

FORMAT_PARAM_NAME = 'format'


class DownloadLink(models.Model):
    PROCESSED_STATUS = 'PR'
    USER_CANCELLED_STATUS = 'UC'
    ADMIN_CANCELLED_STATUS = 'AC'

    STATUS_CHOICES = (
        (PROCESSED_STATUS, _('Processed')),
        (USER_CANCELLED_STATUS, _('Cancelled by the user')),
        (ADMIN_CANCELLED_STATUS, _('Cancelled by the administrator')),
    )
    request = models.ForeignKey('DownloadRequest', on_delete=models.CASCADE)
    prepared_download_path = models.TextField(null=True, blank=True)
    valid_to=models.DateTimeField(db_index=True)
    link_random_id = models.TextField(db_index=True, unique=True)
    status = models.CharField(max_length=2, default=PROCESSED_STATUS, choices=STATUS_CHOICES, db_index=True)

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
    
    PENDING_AUTHORIZATION_STATUS = 'AU'
    PACKAGE_QUEUED_STATUS = 'QP' # Queued for package preparation
    WAITING_SPACE_STATUS = 'SP' # Queued for package preparation
    PROCESSING_STATUS = 'PG' # Queued for package preparation
    PROCESSED_STATUS = 'PD' # The download package was sucessfully created
    REJECTED_STATUS = 'RE' # Rejected or cancelled by the admins
    HOLD_STATUS = 'HO' # Set on hold by admins    
    CANCELLED_STATUS = 'CL' # Cancelled by the user
    PACKAGING_ERROR_STATUS = 'ER' # An error was found during preparation of the package
    PERMANENT_PACKAGE_ERROR_STATUS = 'PE' # A permanent error was found during preparation

    REQUEST_STATUS_CHOICES = (
        (PENDING_AUTHORIZATION_STATUS, _('Pending authorization')),
        (PACKAGE_QUEUED_STATUS, _('Package queued')),
        (PROCESSING_STATUS, _('Processing resource')),
        (WAITING_SPACE_STATUS, _('Queued, waiting for free space')),
        (PROCESSED_STATUS, _('Processed')),
        (REJECTED_STATUS, _('Rejected')),
        (HOLD_STATUS, _('On hold')),
        (CANCELLED_STATUS, _('Cancelled')),
        (PACKAGING_ERROR_STATUS, _('Packaging error')),
        (PERMANENT_PACKAGE_ERROR_STATUS, _('Permanent packaging error')),
    )
    
    # res_einternal_id = models.PositiveIntegerField()
    #ds_type = models.CharField(max_length=3, choices=RESOURCE_TYPES_CHOICES)
    data_source  = models.TextField() # description of the layer data source and download params
    layer_id = models.TextField(null=True, blank=True)
    layer_id_type = models.CharField(max_length=2, choices=ID_TYPES)
    name = models.TextField()
    title = models.TextField()
    layer_name = models.TextField()
    layer_title = models.TextField()
    pending_authorization = models.BooleanField(default=False)
    status = models.CharField(max_length=2, default=PACKAGE_QUEUED_STATUS, choices=REQUEST_STATUS_CHOICES, db_index=True)
    download_count = models.PositiveIntegerField(default=0)
    resolved_url =  models.TextField(null=True, blank=True)
    is_dynamic = models.BooleanField(default=False)
    download_link = models.ForeignKey('DownloadLink', on_delete=models.CASCADE, null=True)
    request = models.ForeignKey('DownloadRequest', on_delete=models.CASCADE)
    #mime_type = models.CharField(max_length=255)
    

class DownloadLog(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    resource = models.ForeignKey('ResourceLocator', on_delete=models.CASCADE)

def get_default_validity():
    # TODO: we could get it for a settings entry, or a settings table in DB
    return 604800  # = 7 days


def get_packaging_max_retry_time():
    # TODO: we could get it for a settings entry, or a settings table in DB
    return 518400  # = 6 days


def get_mail_max_retry_time():
    # TODO: we could get it for a settings entry, or a settings table in DB
    return 518400  # = 6 days