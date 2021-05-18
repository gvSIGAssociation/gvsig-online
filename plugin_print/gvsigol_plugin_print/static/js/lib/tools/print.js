/**
 * gvSIG Online.
 * Copyright (C) 2010-2017 SCOLAB.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

/**
 * @author: Javier Rodrigo <jrodrigo@scolab.es>
 */

/**
 * TODO
 */
var print = function(printProvider, conf, map) {
	var self = this;
	this.printProvider = printProvider;
	this.conf = conf;
	this.map = map;

	this.origin = window.location.origin;
	//this.origin = 'http://localhost:8080';

	this.id = "print";
	this.$button = $("#print");

	this.detailsTab = $('#details-tab');

	this.lastAngle = 0;
	this.extentLayer = null;
	this.capabilities = null;

	var this_ = this;
	var handler = function(e) {
		this_.handler(e);
	};

	this.$button.on('click', handler);
	this.$button.on('touchstart', handler);

};

/**
 * TODO
 */
print.prototype.active = false;

/**
 * TODO
 */
print.prototype.deactivable = true;

/**
 * @param {Event} e Browser event.
 */
print.prototype.handler = function(e) {
	e.preventDefault();
	var self = this;

	if (!this.active) {
		this.extentLayer = new ol.layer.Vector({
			source: new ol.source.Vector()
		});
		this.map.addLayer(this.extentLayer);
		this.zoomChangedFromScale = false;
		


		this.showDetailsTab();
		this.detailsTab.empty();

		this.capabilities = this.getCapabilities('a4_landscape');
		this.renderPrintExtent(this.capabilities.layouts[0].attributes[3].clientInfo);
	    var translate = new ol.interaction.Translate({
	        layers: [this.extentLayer]
	      });
	    translate.setActive(true);
	    this.map.addInteraction(translate);
		
		var currZoom = map.getView().getZoom();
		var eventKey = this.map.on('moveend', function(e) {
		  var newZoom = map.getView().getZoom();
		  if (currZoom != newZoom) {
			if (self.zoomChangedFromScale == false) {
				$('#print-scale').val('');
				$('#print-user-scale-holder').hide();
			}
			else
				self.zoomChangedFromScale = false;
		    currZoom = newZoom;
	        self.extentLayer.getSource().clear();
//	        self.extentLayer.changed();
	        self.renderPrintExtent(self.capabilities.layouts[0].attributes[3].clientInfo);
	        translate.setActive(true);	        
		  }
		});

		var templates = this.getTemplates();
		
		var scales = this.printProvider.default_scales; //this.getScales(this.capabilities);


		var ui = '';
		ui += '<div class="box box-default">';
		ui += 	'<div class="box-header with-border">';
		ui += 		'<h3 class="box-title">' + gettext('Print params') + '</h3>';
		ui += 	'</div>';
		ui += 	'<div class="box-body">';
		ui += 		'<div id="field-errors" class="row"></div>';
		ui += 		'<div class="row">';
		ui += 			'<div class="col-md-12 form-group">';
		ui += 				'<label>' + gettext('Select print template') + '</label>';
		ui += 				'<select id="print-template" class="form-control">';
		ui += 					'<option disabled selected value="empty"> -- ' + gettext('Select template') + ' -- </option>';
		// Los templates que empiezan por _ no los mostramos. Se supone que están ahí para fichas personalizadas.
		// Por defecto seleccionamos el de a4_landscape
		for (var i=0; i<templates.length; i++) {
			if (templates[i].startsWith('_'))
				continue;
		 	if (templates[i] == 'default') {				
				 continue;
			}
			if (templates[i] == 'a4_landscape') {
				ui += 	'<option value="' + templates[i] + '" selected>' + gettext(templates[i]) + '</option>';
			} else {
				ui += 	'<option value="' + templates[i] + '">' + gettext(templates[i]) + '</option>';
			}
		}
		ui += 				'</select>';
		ui += 			'</div>';
		ui += 			'<div class="col-md-12 form-group">';
		ui += 				'<label>' + gettext('Title') + '</label>';
		ui += 				'<input id="print-title" type="text" class="form-control" value="' + this.conf.project_title + '">';
		ui += 			'</div>';
		ui += 			'<div class="col-md-12 form-group">';
		ui += 				'<label>' + gettext('Scale') + '</label>';
		ui += 				'<select id="print-scale" class="form-control">';
		ui += 				'<option value="">' + gettext('AutoScale') + '</option>';
		ui += 				'<option value="user-scale">' + gettext('UserScale') + '</option>';
		if (scales) {
			for (var i=0; i<scales.length; i++) {
					ui += 	'<option value="' + scales[i] + '">1:' + scales[i].toLocaleString() + '</option>';
			}
		}

		ui += 				'</select>';
		ui += 				'<span id="print-user-scale-holder" style="display: flex;justify-content: flex-end;align-items: center;padding-top: 10px;">1: &nbsp; <input type="text" id="print-userscale" name="print-userscale" class="form-control" style="width:80px" placeholder="4000" value="4000"></span>';
		ui += 			'</div>';
		ui += 			'<div class="col-md-12 form-group">';
		ui += 				'<label>' + gettext('Resolution') + '</label>';
		ui += 				'<select id="print-dpi" class="form-control">';
		ui += 					'<option value="72">72 dpi</option>';
		ui += 					'<option selected value="96">96 dpi</option>';		
		ui += 					'<option value="128">128 dpi</option>';		
		ui += 					'<option value="180">180 dpi</option>';
		ui += 					'<option value="240">240 dpi</option>';
		ui += 					'<option value="320">320 dpi</option>';
//		ui += 					'<option value="400">400 dpi</option>';
		ui += 				'</select>';
		ui += 			'</div>';
		
		ui += 			'<div class="col-md-12 form-group">';
		ui += 				'<label>' + gettext('Rotation') + '</label>';
		ui += 				'<input id="print-rotation" type="number" step="any" class="form-control" value="0">';
		ui += 			'</div>';
		
		ui += 			'<div class="col-md-12 form-group">';
		ui += 				'<label>' + gettext('Format') + '</label>';
		ui += 				'<select id="print-format" class="form-control">';
//		ui += 					'<option value="bmp">.bmp</option>';
//		ui += 					'<option value="jpeg">.jpeg</option>';
		ui += 					'<option selected value="pdf">.pdf</option>';
		ui += 					'<option value="png">.png</option>';
		ui += 					'<option value="svg">.svg</option>';
		ui += 				'</select>';
		ui += 			'</div>';
		
		ui += 			'<div class="col-md-12 form-group">';
		ui += 				'<label>' + gettext('Legal warning') + '</label>';
		ui += 				'<textarea class="form-control" name="print-legal" id="print-legal" rows="5">' + this.printProvider.legal_advice + '</textarea>';
		ui += 			'</div>';
		ui += 		'</div>';
		ui += 	'</div>';
		ui += 	'<div class="box-footer clearfix">';
		ui += 		'<a href="javascript:void(0)" id="accept-print" class="btn btn-sm btn-primary btn-flat pull-right"><i class="fa fa-print margin-r-5"></i>' + gettext('Print') + '</a>';
		ui += 		'<a href="javascript:void(0)" id="cancel-print" class="btn btn-sm btn-danger btn-flat pull-right margin-r-10"><i class="fa fa-times margin-r-5"></i>' + gettext('Cancel') + '</a>';
		ui += 	'</div>';
		ui += '</div>';

		this.detailsTab.append(ui);
		$.gvsigOL.controlSidebar.open();

		$('#print-template').on('change', function(e) {
			var template = $('#print-template').val();
			self.capabilities = self.getCapabilities(template);

			self.extentLayer.getSource().clear();
	        self.lastAngle = 0;
	        self.renderPrintExtent(self.capabilities.layouts[0].attributes[3].clientInfo);
		});

		$('#print-rotation').on('change', function(e) {
			var feature = self.extentLayer.getSource().getFeatures()[0];
		    var center = self.map.getView().getCenter();
		    var radiansAngle = (this.value * 2 * Math.PI) / 360;
		    var radiansLastAngle = ((360-self.lastAngle) * 2 * Math.PI) / 360;
		    feature.getGeometry().rotate(radiansLastAngle, center);
			feature.getGeometry().rotate(radiansAngle, center);
			self.extentLayer.getSource().dispatchEvent('change');
			self.lastAngle = this.value;
		});
		
		$('#print-scale').on('change', function(e) {
			var scaleVal = $("#print-scale option:selected").val();
			if (scaleVal == 'user-scale') {
				$('#print-user-scale-holder').show();
				var userScaleStr = $("#print-userscale").text();
				var userScale = parseInt(userScaleStr);
				scaleVal = userScale;
			}
			else {
				$('#print-user-scale-holder').hide();
			}
			if (scaleVal) {
				self.zoomChangedFromScale = true;
				self.map.getView().setResolution(self.getResolutionForScale(scaleVal));
			}
		});

		$('#print-userscale').on('input', function(e) {
			var userScaleStr = $("#print-userscale").val();
			var userScale = parseInt(userScaleStr);
			self.zoomChangedFromScale = true;
			self.map.getView().setResolution(self.getResolutionForScale(userScale));
		});

		$('#print-user-scale-holder').hide();


		$('#accept-print').on('click', function () {
			var template = $('#print-template').val();
			if (template != null) {
				$("body").overlay();
				try {
					self.createPrintJob(template);
				}
				catch(e) {
					$.overlayout();
					messageBox.show('error', gettext('Error creating print job'));
				}
			} else {
				messageBox.show('warning', gettext('You must select a template'));
			}

		});

		$('#cancel-print').on('click', function () {
			ol.Observable.unByKey(eventKey);
			self.removeExtentLayer();
			self.showLayersTab();
			self.capabilities = null;
			self.active = false;
		});

		this.active = true;
	}
};

/**
 * TODO
 */
print.prototype.createPrintJob = function(template) {
	var self = this;
	var title = $('#print-title').val();
	var legalWarning = $('#print-legal').val();
	var rotation = $('#print-rotation').val();
	var dpi = $('#print-dpi').val();

	var scaleToSet = $('#print-scale').val();
	if (scaleToSet == 'user-scale') {
		var userScaleStr = $("#print-userscale").val();
		var userScale = parseInt(userScaleStr);
		scaleToSet = userScale;
	}
	var useNearestScale = true;
	if (!scaleToSet) {
		scaleToSet = self.getScaleForResolution(); // Actual scale of the view if the user has not selected a scale
		useNearestScale = false;
	}

	var mapLayers = this.map.getLayers().getArray();
	mapLayers.sort(function(la, lb) {
		return (lb.getZIndex()-la.getZIndex());
	});	
	var printLayers = new Array();
	var legends = new Array();
	for (var i=0; i<mapLayers.length; i++) {
		if (!mapLayers[i].baselayer && mapLayers[i].layer_name != 'plg_catastro'/* && !(mapLayers[i] instanceof ol.layer.Vector)*/) {
			if (mapLayers[i].getVisible()) {
				var layer = null;
				if (mapLayers[i].getSource() instanceof ol.source.XYZ) {
					var url = mapLayers[i].getSource().getUrls()[0];
					if (url.indexOf('http') == -1) {
						url = self.origin + url;
					}
					printLayers.push({
						"baseURL": url,
					    "type": "OSM",
					    "tileSize": [256, 256],
					    "resolutions": [156543.03390625,
				            78271.516953125,
				            39135.7584765625,
				            19567.87923828125,
				            9783.939619140625,
				            4891.9698095703125,
				            2445.9849047851562,
				            1222.9924523925781,
				            611.4962261962891,
				            305.74811309814453,
				            152.87405654907226,
				            76.43702827453613,
				            38.218514137268066,
				            19.109257068634033,
				            9.554628534317017,
				            4.777314267158508,
				            2.388657133579254,
				            1.194328566789627,
				            0.5971642833948135,
				            0.2984505969011938,
				            0.1492252984505969,
				            0.0746455354243517,
				            0.0373227677121758
				           ],
					    "imageExtension": "png"
					});
					
				} else if (mapLayers[i].getSource() instanceof ol.source.Vector) {
					if (mapLayers[i].printable) {
						printLayers.push({
						    "type": "geojson",
						    "geoJson": self.getGeoJSON(mapLayers[i]),
						    "style": self.getVectorStyles(mapLayers[i])
						});
					}	
					
				} else {
					var wms_url = mapLayers[i].wms_url_no_auth;
					if (wms_url === undefined) {
						wms_url = mapLayers[i].wms_url;
					}
					var url = wms_url;
					if (url.indexOf('http') == -1) {
						url = self.origin + url;
					}
					layer = {
							"baseURL": url,
					  	    "opacity": mapLayers[i].getOpacity(),
					  	    "type": "WMS",
				  			"imageFormat": "image/png",
				  			"customParams": {
				  				"TRANSPARENT": "true"
				  			},
							"mergeableParams": {},
				  	    };
					if(mapLayers[i].getSource() instanceof ol.source.WMTS){
						// we print WMTS layers using WMS since MapFish Print can't properly authenticate in GWC. See: #4809
						layer['layers'] = [mapLayers[i].getSource().getLayer()];
						if (mapLayers[i].getSource().getStyle()) {
							layer['styles'] = [mapLayers[i].getSource().getStyle()];
						}
					}
					else {
						if (mapLayers[i].getSource().getParams()['STYLES']) {
							layer['styles'] = [mapLayers[i].getSource().getParams()['STYLES']];
						}
						if (mapLayers[i].getSource().getParams()['TIME']) {
							layer['customParams']['TIME'] = mapLayers[i].getSource().getParams()['TIME'];
						}
						if (mapLayers[i].isLayerGroup) {
							layer['layers'] = [mapLayers[i].layer_name];
						} else if (mapLayers[i].external) {
							layer['layers'] = [mapLayers[i].getSource().getParams().LAYERS];
						} else {
							layer['layers'] = [mapLayers[i].workspace + ':' + mapLayers[i].layer_name];
						}
					}
				}

				if(layer){
					printLayers.push(layer);
				}
				var legendUrl = mapLayers[i].legend_no_auth;
				if (legendUrl) {
					if (legendUrl.indexOf('http') == -1) {
						legendUrl = self.origin + legendUrl;
					}
					var legend = {
							"name": mapLayers[i].title,
				            "icons": [legendUrl.replace('forceLabels:on', 'forceLabels:on;columnheight:1000')]
				        };
					legends.push(legend);
				}
			}
		}
	}

	console.log(window.location.hostname);

	var baseLayers = this.map.getLayers().getArray();
	for (var i=0; i<baseLayers.length; i++) {
		if (baseLayers[i].baselayer) {
			if (baseLayers[i].getVisible()) {
				if (baseLayers[i].getSource().urls) {
					if(baseLayers[i].getSource().getUrls()[0].indexOf('data:image/gif;base64') == -1) {
						console.log(baseLayers[i]);
						if (baseLayers[i].getSource() instanceof ol.source.OSM) {
							printLayers.push({
								"baseURL": "http://a.tile.openstreetmap.org",
						  	    "type": "OSM",
						  	    "imageExtension": "png"
							});

						} else if (baseLayers[i].getSource() instanceof ol.source.WMTS) {
							var initialScale = 559082263.950892933;
							var scale = 0;
							var matrices = new Array();
							var tileGrid = baseLayers[i].getSource().getTileGrid();
							var lastSize = 1;
							var format = mapLayers[i].getSource().getFormat();
							var tileSize = 256;
							if (tileGrid.getTileSize(0)) {
								tileSize = tileGrid.getTileSize();
							}

							for (var z = 0; z < tileGrid.getMatrixIds().length; ++z) {
								var matrixSize = new Array();
								if (z == 0) {
									matrixSize.push(1);
									matrixSize.push(1);
									scale = initialScale;

								} else if (z >= 1) {
									lastSize = lastSize*2;
									matrixSize.push(lastSize*2);
									matrixSize.push(lastSize*2);
									scale = scale / 2;
								}
								var tileSizeZ = 256;
								if (tileGrid.getTileSize(z)) {
									tileSizeZ = tileGrid.getTileSize(z);
								}

								matrices.push({
									"identifier": tileGrid.getMatrixIds()[z],
						            "matrixSize": matrixSize,
						            "tileSize": [tileSizeZ, tileSizeZ],
						            "scaleDenominator": scale,
						            "topLeftCorner": [-2.003750834E7, 2.0037508E7]
								});
							}
							var url = mapLayers[i].getSource().getUrls()[0];
							if (url.indexOf('http') == -1) {
								url = self.origin + url;
							}
							printLayers.push({
								"type": "WMTS",
						        "baseURL": url,
						        "opacity": 1.0,
						        "layer": baseLayers[i].getSource().getLayer(),
						        "version": "1.0.0",
						        "requestEncoding": "KVP",
						        "dimensions": null,
						        "dimensionParams": {},
						        "matrixSet": baseLayers[i].getSource().getMatrixSet(),
						        "matrices": matrices,
						        "imageFormat": format
							});

						} else if (baseLayers[i].getSource() instanceof ol.source.TileWMS) {
							var url = mapLayers[i].getSource().getUrls()[0];
							if (url.indexOf('http') == -1) {
								url = self.origin + url;
							}
							printLayers.push({
								"type": "WMS",
						        "layers": [baseLayers[i].getSource().getParams()['LAYERS']],
						        "baseURL": url,
						        "imageFormat": baseLayers[i].getSource().getParams()['FORMAT'],
						        "version": baseLayers[i].getSource().getParams()['VERSION'],
						        "customParams": {
						        	"TRANSPARENT": "true"
						        }
							});

						} else if (baseLayers[i].getSource() instanceof ol.source.XYZ) {
							var url = mapLayers[i].getSource().getUrls()[0];
							if (url.indexOf('http') == -1) {
								url = self.origin + url;
							}
							printLayers.push({
								"baseURL": url,
							    "type": "OSM",
							    "dpi": parseInt(dpi),
							    "resolutions": [156543.03390625,
						            78271.516953125,
						            39135.7584765625,
						            19567.87923828125,
						            9783.939619140625,
						            4891.9698095703125,
						            2445.9849047851562,
						            1222.9924523925781,
						            611.4962261962891,
						            305.74811309814453,
						            152.87405654907226,
						            76.43702827453613,
						            38.218514137268066,
						            19.109257068634033,
						            9.554628534317017,
						            4.777314267158508,
						            2.388657133579254,
						            1.194328566789627,
						            0.5971642833948135,
						            0.2984505969011938,
						            0.1492252984505969,
						            0.0746455354243517,
						            0.0373227677121758
						           ],		
						          "resolutionTolerance": 0.1,
							    "tileSize": [256, 256],
							    "imageExtension": "png"
							});
						}
					}
					var legendUrl = baseLayers[i].legend_no_auth;
					if (legendUrl) {
						if (legendUrl.indexOf('http') == -1) {
							legendUrl = self.origin + legendUrl;
						}
						var legend = {
							"name": baseLayers[i].title,
							"icons": [legendUrl.replace('forceLabels:on', 'forceLabels:on;columnheight:1000')]
						};
						legends.push(legend);	
					}					
				}
			}
		}
	}
	var f = self.extentLayer.getSource().getFeatures()[0];
	var bAcceptsOverview = false;
	var outputFormat = $("#print-format option:selected").val();

	var dataToPost = {
	  		"layout": self.capabilities.layouts[0].name,
		  	"outputFormat": outputFormat,
		  	"attributes": {
		  		"title": title,
		  		"scale": '1: ' + Number.parseInt(scaleToSet).toLocaleString(),
		  		"legalWarning": legalWarning,
		  		"map": {
		  			"projection": "EPSG:3857",
		  			"dpi": parseInt(dpi),
		  			"dpiSensitiveStyle":true,
		  			"rotation": rotation,
		  			// "center": self.map.getView().getCenter(),
		  			"scale": scaleToSet,
		  			"useNearestScale": false, //useNearestScale,
		  			"layers": printLayers,
		  			"bbox": f.getGeometry().getExtent()
		  	    },
		  	    "logo_url": self.origin + self.conf.project_image,
		  	    //"logo_url": 'http://localhost' + self.conf.project_image,
		  	    "legend": {
		  	    	"name": "",
		            "classes": legends
		        },
		        "crs": "EPSG:3857"
		  	}
	};
	if (self.capabilities.layouts[0].attributes[4].name == 'overviewMap') {
		bAcceptsOverview = true;
		dataToPost.attributes.overviewMap = {
				// "zoomFactor":5,
	            "layers": [
		              {
		                "type": "OSM",
						"baseURL": "http://a.tile.openstreetmap.org",
				  	    "imageExtension": "png"		                	
		              }
		            ]
		          };
	}
	$.ajax({
		type: 'POST',
		async: true,
	  	url: self.printProvider.url + '/print/' + template + '/report.' + outputFormat,
	  	processData: false,
	    contentType: 'application/json',
	  	data: JSON.stringify(dataToPost),
	  	success	:function(response){
	  		self.getReport(response);
	  	},
	  	error: function(){}
	});

};

print.prototype.getScales = function (capabilities) {
	// attribute 3 is 'map'
    var scales = capabilities.layouts[0].attributes[3].clientInfo.scales;
    return scales;
};


var inchesPerMeter = 39.3700787;
var dpi = 96;

print.prototype.getResolutionForScale = function (scaleDenominator) {
  return scaleDenominator / inchesPerMeter / dpi;
}

print.prototype.getScaleForResolution = function() {
	const resolution = this.map.getView().getResolution();
	const mpu = this.map.getView().getProjection().getMetersPerUnit();
	return parseFloat(resolution.toString()) * mpu * inchesPerMeter * dpi;
}

print.prototype.getCurrentScale = function (dpi) {
    var resolution = this.map.getView().getResolution();
    var units = this.map.getView().getProjection().getUnits();
    var mpu = ol.proj.METERS_PER_UNIT[units];
    var scale = resolution * mpu * 39.37 * dpi;
    return Math.round(scale);
};

/**
 * TODO
 */
print.prototype.getReport = function(reportInfo) {
	var self = this;
	$.ajax({
		type: 'GET',
		async: false,
	  	url: self.printProvider.url + reportInfo.statusURL,
	  	success	:function(response){
	  		if (response.done) {
	  			$.overlayout();
	  			window.open(self.printProvider.url + reportInfo.downloadURL);
	  		} else {
				window.setTimeout(function() {
					self.getReport(reportInfo)
				}, 3000);
			}	  							
	  	},
	  	error: function(){}
	});
};

/**
 * TODO
 */
print.prototype.getTemplates = function() {
	var templates = null;
	$.ajax({
		type: 'GET',
		async: false,
	  	url: this.printProvider.url + '/print/apps.json',
	  	success	:function(response){
	  		templates = response;
	  	},
	  	error: function(){}
	});
	return templates;
};

/**
 * TODO
 */
print.prototype.getCapabilities = function(template) {
	var capabilities = null;
	$.ajax({
		type: 'GET',
		async: false,
	  	url: this.printProvider.url + '/print/' + template + '/capabilities.json',
	  	success	:function(response){
	  		capabilities = response;
	  	},
	  	error: function(){}
	});
	return capabilities;
};

/**
 * TODO
 */
print.prototype.renderPrintExtent = function(clientInfo) {
    var mapComponentWidth = this.map.getSize()[0];
    var mapComponentHeight = this.map.getSize()[1];
    var currentMapRatio = mapComponentWidth / mapComponentHeight;
    var scaleFactor = 0.6;
    var desiredPrintRatio = clientInfo.width / clientInfo.height;
    var targetWidth;
    var targetHeight;
    var geomExtent;
    var feat;

    if (desiredPrintRatio >= currentMapRatio) {
        targetWidth = mapComponentWidth * scaleFactor;
        targetHeight = targetWidth / desiredPrintRatio;
    } else {
        targetHeight = mapComponentHeight * scaleFactor;
        targetWidth = targetHeight * desiredPrintRatio;
    }
    
    geomExtent = this.map.getView().calculateExtent([
        targetWidth,
        targetHeight
    ]);
    
    feat = new ol.Feature(ol.geom.Polygon.fromExtent(geomExtent));
    this.extentLayer.getSource().addFeature(feat);
    this.extentLayer.setZIndex(this.map.getLayers().length);
    this.extentLayer.changed();
    return feat;
};

/**
 * TODO
 */
print.prototype.deactivate = function() {
	this.$button.removeClass('button-active');
	this.active = false;
};

/**
 * TODO
 */
print.prototype.showDetailsTab = function(p,f) {
	$('.nav-tabs a[href="#details-tab"]').tab('show');
};

/**
 * @param {Event} e Browser event.
 */
print.prototype.removeExtentLayer = function() {
	this.extentLayer.getSource().clear();
	this.map.removeLayer(this.extentLayer);

};

/**
 * TODO
 */
print.prototype.showLayersTab = function(p,f) {
	this.detailsTab.empty();
	$('.nav-tabs a[href="#layer-tree-tab"]').tab('show');
};

/**
 * TODO
 */
print.prototype.getGeoJSON = function(layer) {
	var format = new ol.format.GeoJSON();
    var geojsonStr = format.writeFeatures(layer.getSource().getFeatures());
    return JSON.parse(geojsonStr);
};

/**
 * TODO
 */
print.prototype.getVectorStyles = function(layer) {
	var styles = null;
	
	if (layer.drawStyleSettings) {
		if (layer.drawType == 'point') {
			styles = layer.drawStyleSettings.getPointPrintStyles();
			
		} else if (layer.drawType == 'line') {
			styles = layer.drawStyleSettings.getLinePrintStyles();
			
		} else if (layer.drawType == 'arrow') {
			styles = layer.drawStyleSettings.getArrowPrintStyles();
			
		} else if (layer.drawType == 'polygon') {
			styles = layer.drawStyleSettings.getPolygonPrintStyles();
			
		} else if (layer.drawType == 'text') {
			styles = layer.drawStyleSettings.getTextPrintStyles();
			
		}
		
	} else if (layer.randomStyle){
		styles = layer.randomStyle;
	}
	
	return styles;
};