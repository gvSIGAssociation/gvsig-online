from django.urls import path
from gvsigol_symbology import views as symbology_views

urlpatterns = [    
    path('style_layer_list/', symbology_views.style_layer_list, name='style_layer_list'),
    path('style_layer_update/<int:layer_id>/<int:style_id>/', symbology_views.style_layer_update, name='style_layer_update'),
    path('style_layer_delete/', symbology_views.style_layer_delete, name='style_layer_delete'),
    path('select_legend_type/<int:layer_id>/', symbology_views.select_legend_type, name='select_legend_type'),
    path('sld_import/<int:layer_id>/', symbology_views.sld_import, name='sld_import'),
    
    path('unique_symbol_add/<int:layer_id>/', symbology_views.unique_symbol_add, name='unique_symbol_add'),
    path('unique_symbol_update/<int:layer_id>/<int:style_id>/', symbology_views.unique_symbol_update, name='unique_symbol_update'),
    
    path('unique_values_add/<int:layer_id>/', symbology_views.unique_values_add, name='unique_values_add'),
    path('unique_values_update/<int:layer_id>/<int:style_id>/', symbology_views.unique_values_update, name='unique_values_update'),
    path('get_unique_values/', symbology_views.get_unique_values, name='get_unique_values'),
    
    path('intervals_add/<int:layer_id>/', symbology_views.intervals_add, name='intervals_add'),
    path('intervals_update/<int:layer_id>/<int:style_id>/', symbology_views.intervals_update, name='intervals_update'),
    path('update_preview/<int:layer_id>/', symbology_views.update_preview, name='update_preview'),
    path('remove_temporal_preview/', symbology_views.remove_temporal_preview, name='remove_temporal_preview'),
    path('get_minmax_values/', symbology_views.get_minmax_values, name='get_minmax_values'),
    
    path('expressions_add/<int:layer_id>/', symbology_views.expressions_add, name='expressions_add'),
    path('expressions_update/<int:layer_id>/<int:style_id>/', symbology_views.expressions_update, name='expressions_update'),
    
    path('custom_add/<int:layer_id>/', symbology_views.custom_add, name='custom_add'),
    path('custom_update/<int:layer_id>/<int:style_id>/', symbology_views.custom_update, name='custom_update'),
    
    path('create_sld/', symbology_views.create_sld, name='create_sld'),
    
    path('clustered_points_add/<int:layer_id>/', symbology_views.clustered_points_add, name='clustered_points_add'),
    path('clustered_points_update/<int:layer_id>/<int:style_id>/', symbology_views.clustered_points_update, name='clustered_points_update'),
    
    path('color_table_add/<int:layer_id>/', symbology_views.color_table_add, name='color_table_add'),
    path('color_table_update/<int:layer_id>/<int:style_id>/', symbology_views.color_table_update, name='color_table_update'),
    
    path('color_ramp_list/<int:color_ramp_folder_id>/', symbology_views.color_ramp_list, name='color_ramp_list'),
    path('color_ramp_add/<int:color_ramp_folder_id>/', symbology_views.color_ramp_add, name='color_ramp_add'),
    path('color_ramp_update/<int:color_ramp_id>/', symbology_views.color_ramp_update, name='color_ramp_update'),
    path('color_ramp_delete/<int:color_ramp_id>/', symbology_views.color_ramp_delete, name='color_ramp_delete'),
    path('color_ramp_library_list/', symbology_views.color_ramp_library_list, name='color_ramp_library_list'),
    path('color_ramp_library_add/', symbology_views.color_ramp_library_add, name='color_ramp_library_add'),
    path('color_ramp_library_update/<int:color_ramp_library_id>/', symbology_views.color_ramp_library_update, name='color_ramp_library_update'),
    path('color_ramp_library_import/', symbology_views.color_ramp_library_import, name='color_ramp_library_import'),
    path('color_ramp_library_export/<int:color_ramp_library_id>/', symbology_views.color_ramp_library_export, name='color_ramp_library_export'),
    path('color_ramp_library_delete/<int:color_ramp_library_id>/', symbology_views.color_ramp_library_delete, name='color_ramp_library_delete'),   
    path('color_ramp_folder_add/<int:color_ramp_library_id>/', symbology_views.color_ramp_folder_add, name='color_ramp_folder_add'),
    path('color_ramp_folder_update/<int:color_ramp_folder_id>/', symbology_views.color_ramp_folder_update, name='color_ramp_folder_update'),
    path('color_ramp_folder_delete/<int:color_ramp_folder_id>/', symbology_views.color_ramp_folder_delete, name='color_ramp_folder_delete'),   
    
    
    path('library_list/', symbology_views.library_list, name='library_list'),
    path('library_add/', symbology_views.library_add, name='library_add'),
    path('library_update/<int:library_id>/', symbology_views.library_update, name='library_update'),
    path('library_import/', symbology_views.library_import, name='library_import'),
    path('library_export/<int:library_id>/', symbology_views.library_export, name='library_export'),
    path('library_delete/<int:library_id>/', symbology_views.library_delete, name='library_delete'),   
    path('symbol_add/<int:library_id>/<symbol_type>/', symbology_views.symbol_add, name='symbol_add'),
    path('symbol_update/<int:symbol_id>/', symbology_views.symbol_update, name='symbol_update'),
    path('symbol_delete/', symbology_views.symbol_delete, name='symbol_delete'),
    path('get_symbols_from_library/', symbology_views.get_symbols_from_library, name='get_symbols_from_library'),
    path('get_folders_from_library/', symbology_views.get_folders_from_library, name='get_folders_from_library'),
    path('get_ramps_from_folder/', symbology_views.get_ramps_from_folder, name='get_ramps_from_folder'),
    
    path('get_wfs_style/', symbology_views.get_wfs_style, name='get_wfs_style'),

    #path('style_label_update/<int:layer_id>/<int:style_id>/', symbology_views.style_label_update, name='style_label_update'),
    #path('create_style/', symbology_views.create_style, name='create_style'),
    #path('delete_style/<int:style_id>/', symbology_views.delete_style, name='delete_style'),
    #path('get_library_symbols/<int:library_id>/', symbology_views.get_library_symbols, name='get_library_symbols'),
    #path('get_libraries/', symbology_views.get_libraries, name='get_libraries'),   
    #path('symbol_library_add/<int:library_id>/((?P<symbol_id>\w+)/)?$', symbology_views.symbol_library_add, name='symbol_library_add'),
    #path('symbol_library_update/(?P<symbol_library_id>[0-9]+)/', symbology_views.symbol_library_update, name='symbol_library_update'),
    #path('symbol_library_delete/(?P<symbol_library_id>[0-9]+)/', symbology_views.symbol_library_delete, name='symbol_library_delete'),
    #path('get_sld_style/<int:layer_id>/<int:style_id>/', symbology_views.get_sld_style, name='get_sld_style'),
    #path('get_sld_style2/<int:layer_id>/<int:style_id>/', 'gvsigol_symbology.sld_tools.get_sld_style2, name='get_sld_style2'),
    #path('set_default_style/<int:layer_id>/<int:style_id>/', symbology_views.set_default_style, name='set_default_style'),
    #path('save_legend/<int:layer_id>/<int:style_id>/', symbology_views.save_legend, name='save_legend'),   
    #path('get_layer_field_description/<int:layer_id>/', symbology_views.get_layer_field_description, name='get_layer_field_description'),
    #path('get_unique_values/<int:layer_id>/(?P<field>\w+)/', symbology_views.get_unique_values, name='get_unique_values'),
    #path('get_minmax_values/<int:layer_id>/(?P<field>\w+)/', symbology_views.get_minmax_values, name='get_minmax_values'),
    #path('get_minmax_rastervalues/<int:layer_id>/<int:style_id>/', symbology_views.get_minmax_rastervalues, name='get_minmax_rastervalues'),
    #path('style_layer_add/<int:layer_id>/((?P<style_id>\w+)/)?$', symbology_views.style_layer_add, name='style_layer_add'),
    #path('style_layer_change/<int:layer_id>/((?P<style_id>\w+)/)?$', symbology_views.style_layer_change, name='style_layer_change'),
    #path('style_layer_update/<int:layer_id>/<int:style_id>/', symbology_views.style_layer_update, name='style_layer_update'),
    #path('symbol_upload/', symbology_views.symbol_upload, name='symbol_upload'),
    #path('load_rmf/', symbology_views.load_rmf, name='load_rmf'),
    
    path('get_raster_statistics/<int:layer_id>/', symbology_views.get_raster_statistics, name='get_raster_statistics'),
    
    
]