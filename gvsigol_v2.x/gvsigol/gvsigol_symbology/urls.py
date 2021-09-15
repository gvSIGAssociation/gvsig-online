from django.conf.urls import url
from gvsigol_symbology import views as symbology_views

urlpatterns = [    
    url(r'^style_layer_list/$', symbology_views.style_layer_list, name='style_layer_list'),
    url(r'^style_layer_update/(?P<layer_id>[0-9]+)/(?P<style_id>[0-9]+)/$', symbology_views.style_layer_update, name='style_layer_update'),
    url(r'^style_layer_delete/$', symbology_views.style_layer_delete, name='style_layer_delete'),
    url(r'^select_legend_type/(?P<layer_id>[0-9]+)/$', symbology_views.select_legend_type, name='select_legend_type'),
    url(r'^sld_import/(?P<layer_id>[0-9]+)/$', symbology_views.sld_import, name='sld_import'),
    
    url(r'^unique_symbol_add/(?P<layer_id>[0-9]+)/$', symbology_views.unique_symbol_add, name='unique_symbol_add'),
    url(r'^unique_symbol_update/(?P<layer_id>[0-9]+)/(?P<style_id>[0-9]+)/$', symbology_views.unique_symbol_update, name='unique_symbol_update'),
    
    url(r'^unique_values_add/(?P<layer_id>[0-9]+)/$', symbology_views.unique_values_add, name='unique_values_add'),
    url(r'^unique_values_update/(?P<layer_id>[0-9]+)/(?P<style_id>[0-9]+)/$', symbology_views.unique_values_update, name='unique_values_update'),
    url(r'^get_unique_values/$', symbology_views.get_unique_values, name='get_unique_values'),
    
    url(r'^intervals_add/(?P<layer_id>[0-9]+)/$', symbology_views.intervals_add, name='intervals_add'),
    url(r'^intervals_update/(?P<layer_id>[0-9]+)/(?P<style_id>[0-9]+)/$', symbology_views.intervals_update, name='intervals_update'),
    url(r'^update_preview/(?P<layer_id>[0-9]+)/$', symbology_views.update_preview, name='update_preview'),
    url(r'^remove_temporal_preview/$', symbology_views.remove_temporal_preview, name='remove_temporal_preview'),
    url(r'^get_minmax_values/$', symbology_views.get_minmax_values, name='get_minmax_values'),
    
    url(r'^expressions_add/(?P<layer_id>[0-9]+)/$', symbology_views.expressions_add, name='expressions_add'),
    url(r'^expressions_update/(?P<layer_id>[0-9]+)/(?P<style_id>[0-9]+)/$', symbology_views.expressions_update, name='expressions_update'),
    
    url(r'^custom_add/(?P<layer_id>[0-9]+)/$', symbology_views.custom_add, name='custom_add'),
    url(r'^custom_update/(?P<layer_id>[0-9]+)/(?P<style_id>[0-9]+)/$', symbology_views.custom_update, name='custom_update'),
    
    url(r'^create_sld/$', symbology_views.create_sld, name='create_sld'),
    
    url(r'^clustered_points_add/(?P<layer_id>[0-9]+)/$', symbology_views.clustered_points_add, name='clustered_points_add'),
    url(r'^clustered_points_update/(?P<layer_id>[0-9]+)/(?P<style_id>[0-9]+)/$', symbology_views.clustered_points_update, name='clustered_points_update'),
    
    url(r'^color_table_add/(?P<layer_id>[0-9]+)/$', symbology_views.color_table_add, name='color_table_add'),
    url(r'^color_table_update/(?P<layer_id>[0-9]+)/(?P<style_id>[0-9]+)/$', symbology_views.color_table_update, name='color_table_update'),
    
    url(r'^color_ramp_list/((?P<color_ramp_folder_id>[0-9]+)/)?$', symbology_views.color_ramp_list, name='color_ramp_list'),
    url(r'^color_ramp_add/((?P<color_ramp_folder_id>[0-9]+)/)?$', symbology_views.color_ramp_add, name='color_ramp_add'),
    url(r'^color_ramp_update/(?P<color_ramp_id>[0-9]+)/$', symbology_views.color_ramp_update, name='color_ramp_update'),
    url(r'^color_ramp_delete/(?P<color_ramp_id>[0-9]+)/$', symbology_views.color_ramp_delete, name='color_ramp_delete'),
    url(r'^color_ramp_library_list/$', symbology_views.color_ramp_library_list, name='color_ramp_library_list'),
    url(r'^color_ramp_library_add/$', symbology_views.color_ramp_library_add, name='color_ramp_library_add'),
    url(r'^color_ramp_library_update/((?P<color_ramp_library_id>[0-9]+)/)?$', symbology_views.color_ramp_library_update, name='color_ramp_library_update'),
    url(r'^color_ramp_library_import/$', symbology_views.color_ramp_library_import, name='color_ramp_library_import'),
    url(r'^color_ramp_library_export/((?P<color_ramp_library_id>[0-9]+)/)?$', symbology_views.color_ramp_library_export, name='color_ramp_library_export'),
    url(r'^color_ramp_library_delete/((?P<color_ramp_library_id>[0-9]+)/)?$', symbology_views.color_ramp_library_delete, name='color_ramp_library_delete'),   
    url(r'^color_ramp_folder_add/((?P<color_ramp_library_id>[0-9]+)/)?$', symbology_views.color_ramp_folder_add, name='color_ramp_folder_add'),
    url(r'^color_ramp_folder_update/((?P<color_ramp_folder_id>[0-9]+)/)?$', symbology_views.color_ramp_folder_update, name='color_ramp_folder_update'),
    url(r'^color_ramp_folder_delete/((?P<color_ramp_folder_id>[0-9]+)/)?$', symbology_views.color_ramp_folder_delete, name='color_ramp_folder_delete'),   
    
    
    url(r'^library_list/$', symbology_views.library_list, name='library_list'),
    url(r'^library_add/((?P<library_id>[0-9]+)/)?$', symbology_views.library_add, name='library_add'),
    url(r'^library_update/((?P<library_id>[0-9]+)/)?$', symbology_views.library_update, name='library_update'),
    url(r'^library_import/$', symbology_views.library_import, name='library_import'),
    url(r'^library_export/((?P<library_id>[0-9]+)/)?$', symbology_views.library_export, name='library_export'),
    url(r'^library_delete/((?P<library_id>[0-9]+)/)?$', symbology_views.library_delete, name='library_delete'),   
    url(r'^symbol_add/(?P<library_id>[0-9]+)/(?P<symbol_type>\w+)/$', symbology_views.symbol_add, name='symbol_add'),
    url(r'^symbol_update/(?P<symbol_id>[0-9]+)/$', symbology_views.symbol_update, name='symbol_update'),
    url(r'^symbol_delete/$', symbology_views.symbol_delete, name='symbol_delete'),
    url(r'^get_symbols_from_library/$', symbology_views.get_symbols_from_library, name='get_symbols_from_library'),
    url(r'^get_folders_from_library/$', symbology_views.get_folders_from_library, name='get_folders_from_library'),
    url(r'^get_ramps_from_folder/$', symbology_views.get_ramps_from_folder, name='get_ramps_from_folder'),
    
    url(r'^get_wfs_style/$', symbology_views.get_wfs_style, name='get_wfs_style'),

    #url(r'^style_label_update/(?P<layer_id>[0-9]+)/(?P<style_id>[0-9]+)/$', symbology_views.style_label_update, name='style_label_update'),
    #url(r'^create_style/$', symbology_views.create_style, name='create_style'),
    #url(r'^delete_style/(?P<style_id>[0-9]+)/$', symbology_views.delete_style, name='delete_style'),
    #url(r'^get_library_symbols/(?P<library_id>[0-9]+)/$', symbology_views.get_library_symbols, name='get_library_symbols'),
    #url(r'^get_libraries/$', symbology_views.get_libraries, name='get_libraries'),   
    #url(r'^symbol_library_add/(?P<library_id>[0-9]+)/((?P<symbol_id>\w+)/)?$', symbology_views.symbol_library_add, name='symbol_library_add'),
    #url(r'^symbol_library_update/(?P<symbol_library_id>[0-9]+)/$', symbology_views.symbol_library_update, name='symbol_library_update'),
    #url(r'^symbol_library_delete/(?P<symbol_library_id>[0-9]+)/$', symbology_views.symbol_library_delete, name='symbol_library_delete'),
    #url(r'^get_sld_style/(?P<layer_id>[0-9]+)/(?P<style_id>[0-9]+)/$', symbology_views.get_sld_style, name='get_sld_style'),
    #url(r'^get_sld_style2/(?P<layer_id>[0-9]+)/(?P<style_id>[0-9]+)/$', 'gvsigol_symbology.sld_tools.get_sld_style2, name='get_sld_style2'),
    #url(r'^set_default_style/(?P<layer_id>[0-9]+)/(?P<style_id>[0-9]+)/$', symbology_views.set_default_style, name='set_default_style'),
    #url(r'^save_legend/(?P<layer_id>[0-9]+)/(?P<style_id>[0-9]+)/$', symbology_views.save_legend, name='save_legend'),   
    #url(r'^get_layer_field_description/(?P<layer_id>[0-9]+)/$', symbology_views.get_layer_field_description, name='get_layer_field_description'),
    #url(r'^get_unique_values/(?P<layer_id>[0-9]+)/(?P<field>\w+)/$', symbology_views.get_unique_values, name='get_unique_values'),
    #url(r'^get_minmax_values/(?P<layer_id>[0-9]+)/(?P<field>\w+)/$', symbology_views.get_minmax_values, name='get_minmax_values'),
    #url(r'^get_minmax_rastervalues/(?P<layer_id>[0-9]+)/(?P<style_id>[0-9]+)/$', symbology_views.get_minmax_rastervalues, name='get_minmax_rastervalues'),
    #url(r'^style_layer_add/(?P<layer_id>[0-9]+)/((?P<style_id>\w+)/)?$', symbology_views.style_layer_add, name='style_layer_add'),
    #url(r'^style_layer_change/(?P<layer_id>[0-9]+)/((?P<style_id>\w+)/)?$', symbology_views.style_layer_change, name='style_layer_change'),
    #url(r'^style_layer_update/(?P<layer_id>[0-9]+)/(?P<style_id>[0-9]+)/$', symbology_views.style_layer_update, name='style_layer_update'),
    #url(r'^symbol_upload/$', symbology_views.symbol_upload, name='symbol_upload'),
    #url(r'^load_rmf/$', symbology_views.load_rmf, name='load_rmf'),
    
    url(r'^get_raster_statistics/(?P<layer_id>[0-9]+)/$', symbology_views.get_raster_statistics, name='get_raster_statistics'),
    
    
]