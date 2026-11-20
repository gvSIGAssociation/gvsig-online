from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from .views import BrowserView, ExportToDatabaseView, UploadView, UploadFileView, DeleteFileView, DirectoryCreateView, UnzipFileView, download_file
from . import views
from . import api
from gvsigol_services import views as services_views

app_name="gvsigol_filemanager"
urlpatterns = [
    path('', BrowserView.as_view(), name='browser'),
    #path('pbrowser/', PopupBrowserView.as_view(), name='pbrowser'),
    path('upload/', UploadView.as_view(), name='upload'),
    path('upload/file/', UploadFileView.as_view(), name='upload-file'),
    path('delete/file/', DeleteFileView.as_view(), name='delete-file'),
    path('unzip/file/', UnzipFileView.as_view(), name='unzip-file'),
    path('create/directory/', DirectoryCreateView.as_view(), name='create-directory'),
    path('export_to_database/', ExportToDatabaseView.as_view(), name='export-to-database'),
    path('list_exports/', views.list_exports, name='list_exports'),
    
    #path('list_datastore_tables/', services_views.list_datastore_tables, name='list_datastore_tables'),

    # Deprecated urls since they have been moved under de fileserver prefix. See urls_fileserver.py
    path('download/<path:filepath>', download_file, name='fmdownload'),

    # API JSON para la interfaz nueva (ver api.py). Las URL anteriores no cambian.
    path('api/list/', api.list_directory, name='api-list'),
    path('api/mkdir/', api.make_directory, name='api-mkdir'),
    path('api/rename/', api.rename, name='api-rename'),
    path('api/move/', api.move, name='api-move'),
    path('api/copy/', api.copy, name='api-copy'),
    path('api/delete/', api.delete, name='api-delete'),
    path('api/unzip/', api.unzip, name='api-unzip'),
    path('api/download/', api.download, name='api-download'),
    path('api/trash/', api.trash_list, name='api-trash'),
    path('api/trash/restore/', api.trash_restore, name='api-trash-restore'),
    path('api/trash/delete/', api.trash_delete, name='api-trash-delete'),
    path('api/trash/empty/', api.trash_empty, name='api-trash-empty'),
    path('api/task/<str:task_id>/', api.task_status, name='api-task'),
    path('api/processes/', api.process_list, name='api-processes'),
    path('api/processes/clear/', api.process_clear, name='api-processes-clear'),
    # Ventana de subidas y procesos (sigue subiendo mientras se navega por el resto de la aplicación)
    path('processes/', views.ProcessesView.as_view(), name='processes'),
    path('api/upload/', api.upload_init, name='api-upload-init'),
    path('api/upload/<str:upload_id>/', api.upload_status, name='api-upload-status'),
    path('api/upload/<str:upload_id>/chunk/', api.upload_chunk, name='api-upload-chunk'),
    path('api/upload/<str:upload_id>/complete/', api.upload_complete, name='api-upload-complete'),
    path('api/upload/<str:upload_id>/cancel/', api.upload_cancel, name='api-upload-cancel'),
]
