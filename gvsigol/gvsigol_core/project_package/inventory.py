"""
Code inventory for project package export/import (MVP).

Raster storage:
  Coverage layers use datastore types c_GeoTIFF / c_ImageMosaic (see gvsigol_services/views.py,
  backend_geoserver.py). Paths live in datastore connection_params / URL fields, not on Layer.
  Tiling models (ProjectBaseLayerTiling, ZoneLayers) use folder_prj for on-disk tile caches.

Application <-> Project:
  core.Application has no FK to Project; home ordering uses UserHomeOrder / hidden items.
  Package export lists applications only if linked elsewhere in future; MVP omits.

Symbology:
  gvsigol_symbology.models.Style, StyleLayer, Rule, Symbolizer hierarchy.
  gvsigol_symbology.services.clone_layer_styles copies DB styles + GeoServer SLD.
  MVP exports resolved SLD bytes per style entry (styles.json) and recreates Style + GeoServer on import.

Triggers:
  LayerConnectionTrigger / DB triggers are NOT imported (metadata may appear in export for audit only).

GeoServer:
  Uses geographic_servers + Server model (password stripped on export). Import targets the
  destination Server from wizard (existing DB row).
"""
