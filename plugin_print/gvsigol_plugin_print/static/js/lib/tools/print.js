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
	this.projection = 'EPSG:3857';
	this.printOverviewLayers = [
		{
		  "name": "OSM",
		  "type": "OSM",
		  "baseURL": "http://a.tile.openstreetmap.org",
			"imageExtension": "png"		                	
		}
	  ];

	// We use this array to store the XYZ layers that we put temporaly invisible
	this.invisibleLayers = [];
	var this_ = this;
	var handler = function(e) {
		this_.handler(e);
		$('body').trigger('printtoolactivated');
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

print.prototype.applyRotation = function(rotationValue) {
	var feature = this.extentLayer.getSource().getFeatures()[0];
	var center = this.map.getView().getCenter();
	var radiansAngle = (rotationValue * 2 * Math.PI) / 360;
	var radiansLastAngle = ((360-this.lastAngle) * 2 * Math.PI) / 360;
	feature.getGeometry().rotate(radiansLastAngle, center);
	feature.getGeometry().rotate(radiansAngle, center);
	this.extentLayer.getSource().dispatchEvent('change');
	this.lastAngle = rotationValue;

}

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
		var mapAttribute = this.getAttributeByName('map');
		this.renderPrintExtent(mapAttribute.clientInfo);
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
	        self.renderPrintExtent(mapAttribute.clientInfo);
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

		// MapGrid
		ui += 			'<div id="print-ui-mapgrid" class="col-md-12 form-group">';
		ui += 				'<label>' + gettext('MapGrid') + '</label>';
		ui += 				'<select id="print-mapgrid-gridtype" class="form-control">';
		ui += 					'<option value="NOGRID" selected >' + gettext('print-mapgrid-nogrid') + '</option>';
		ui += 					'<option value="POINTS">' + gettext('print-mapgrid-point') + '</option>';
		ui += 					'<option value="LINES">' + gettext('print-mapgrid-line') + '</option>';
		ui += 				'</select>';
		ui += 				'<label>' + gettext('print-mapgrid-spacing') + '</label>';
		ui += 				'<input id="print-mapgrid-spacing" type="number" step="any" class="form-control" value="1">';
		// ui += 				'<label>' + gettext('print-mapgrid-indent') + '</label>';
		// ui += 				'<input id="print-mapgrid-indent" type="number" step="any" class="form-control" value="5">';
		ui += 			'</div>';

		// MapProjection
		ui += 			'<div id="print-ui-mapprojection" class="col-md-12 form-group">';
		ui += 				'<label>' + gettext('MapProjection') + '</label>';
		ui += 				'<select id="print-projection" class="form-control">';
		var supported_crs = Object.values(this.conf.supported_crs);
		for ( var crs of supported_crs) {
			if (crs.code == "EPSG:3857") 
		  		ui += '<option value="' + crs.code + '" selected>' + crs.title + '</option>'
	  		else 
		  		ui += '<option value="' + crs.code + '">' + crs.title + '</option>'
		}
		ui += 				'</select>';
		ui += 			'</div>';

		// MAPOVERVIEW
		self.baseLayers = [];
		// Cambio: metemos el combobox, y luego se pone invisible o no dependiendo de si soporta overview
		// if (self.supportsOverview(self.capabilities)) {			
			var layers = this.map.getLayers().getArray();
			for (var i=0; i<layers.length; i++) {
				if (layers[i].baselayer) {
					var printLayer = self.convertBaseLayerToPrintLayer(layers[i], []);
					if (printLayer) 
						self.baseLayers.push(printLayer);
				}
			}
			if (self.baseLayers.length == 0) {
				self.baseLayers = self.printOverviewLayers; // por defecto			
			}		

			ui += 			'<div id="print-ui-mapoverview" class="col-md-12 form-group">';
			ui += 				'<label>' + gettext('MapOverview') + '</label>';
			ui += 				'<select id="print-overview" class="form-control">';
		
			for ( var bId = 0; bId < self.baseLayers.length; bId++) {
				var lyr = self.baseLayers[bId];
				if (lyr.type == "OSM") 
					ui += '<option value="' + bId + '" selected>' + lyr.name + '</option>'
				else 
					ui += '<option value="' + bId + '">' + lyr.name + '</option>'
			}
			ui += 				'</select>';
			ui += 			'</div>';
		// } // supportOverview		
		ui += 			'<div class="col-md-12 form-group">';
		ui += 			'<div class="container" style="display: flex; justify-content: space-between; padding:0px; width:auto;">';
		ui += 			'	<div class="col-sm" style="width: 33%">';
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
		ui += 			'	</div>'; // col-sm		
		ui += 			'	<div class="col-sm" style="width: 33%">';
		// ui += 			'<div class="col-md-12 form-group">';
		ui += 				'<label>' + gettext('Rotation') + '</label>';
		ui += 				'<input id="print-rotation" type="number" step="any" class="form-control" value="0">';
		ui += 			'</div>';
		
		// ui += 			'<div class="col-md-12 form-group">';
		ui += 			'	<div class="col-sm" style="width: 33%">';
		ui += 				'<label>' + gettext('Format') + '</label>';
		ui += 				'<select id="print-format" class="form-control">';
//		ui += 					'<option value="bmp">.bmp</option>';
//		ui += 					'<option value="jpeg">.jpeg</option>';
		ui += 					'<option selected value="pdf">.pdf</option>';
		ui += 					'<option value="png">.png</option>';
		ui += 					'<option value="svg">.svg</option>';
		ui += 				'</select>';
		ui +=	 			'</div>'; // col-sm
		ui += 			'</div>';  // container
		ui += 			'</div>';

		var author = gettext('Author');
		if (this.conf.user && this.conf.user.username) {
			author = this.conf.user.username;
		}
		ui += 			'<div id="print-ui-author" class="col-md-12 form-group">';
		ui += 				'<label>' + gettext('Author') + '</label>';
		ui += 				'<input id="print-author" class="form-control" value="' + author + '">';
		ui += 			'</div>';

		
		ui += 			'<div id="print-ui-legal-warning" class="col-md-12 form-group">';
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
		this.updateUI();
		$.gvsigOL.controlSidebar.open();		

		$('#print-template').on('change', function(e) {
			var template = $('#print-template').val();
			self.capabilities = self.getCapabilities(template);

			self.extentLayer.getSource().clear();
	        self.lastAngle = 0;
			var mapAttribute = self.getAttributeByName('map');
			self.renderPrintExtent(mapAttribute.clientInfo);
			var rotation = $('#print-rotation').val();
			self.applyRotation(rotation);
	
			self.updateUI();
			$('#print-template').trigger('printtemplateselected');
		});

		$('#print-rotation').on('change', function(e) {
			self.applyRotation(this.value);
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

		$('#print-projection').on('change', function(e) {
			// self.zoomChangedFromScale = true;
			// self.map.getView().setResolution(self.getResolutionForScale(scaleVal));
			self.extentLayer.getSource().clear();
			self.extentLayer.getSource().dispatchEvent('change');
			var mapAttribute = self.getAttributeByName('map');
			self.renderPrintExtent(mapAttribute.clientInfo);
		});


		$('#print-userscale').on('input', function(e) {
			var userScaleStr = $("#print-userscale").val();
			var userScale = parseInt(userScaleStr);
			self.zoomChangedFromScale = true;
			self.dpi = 96;
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
			for (var l of self.invisibleLayers) {
				l.setVisible(true);
			}
			self.invisibleLayers = [];
			self.showLayersTab();
			self.capabilities = null;
			self.active = false;
			self.lastAngle = 0;
		});

		this.active = true;
	}
};

print.prototype.updateUI = function() {
	if (this.supports('mapGrid'))
		$('#print-ui-mapgrid').show();
	else
		$('#print-ui-mapgrid').hide();

	if (this.supports('author'))
		$('#print-ui-author').show();
	else
		$('#print-ui-author').hide();

	if (this.supports('overviewMap')) 
		$('#print-ui-mapoverview').show();
	else
		$('#print-ui-mapoverview').hide();

	if (this.supports('legalWarning'))
		$('#print-ui-legal-warning').show();
	else
		$('#print-ui-legal-warning').hide();

	if (this.supports('crsPermanent')) {
		$('#print-ui-mapprojection').hide();
	}
	else {
		$('#print-ui-mapprojection').show();
	}

		
};

// methods to allow personalized options from outside this tool 
// for example, from apps like tocantins, or other plugins
// In plugin or app, add an event listener to 'printtemplateselected' event like this:
// $('body').on('printtemplateselected', function(e) {
print.prototype.setDefaultTemplate = function(templateName) {
	$('#print-template option[value="' + templateName +'"]').attr('selected','selected');
	this.capabilities = this.getCapabilities(templateName);

	this.extentLayer.getSource().clear();
	// this.lastAngle = 0;
	var mapAttribute = this.getAttributeByName('map');
	this.renderPrintExtent(mapAttribute.clientInfo);

	// $('#print-template').trigger('change');
};

print.prototype.setTemplateOrder = function( orderedTemplates ) {
	$('#print-template').empty();

	for (var t of orderedTemplates) {
		if (t == 'a4_landscape') {
			$('#print-template').append('<option value="' + t + '" selected>' + gettext(t) + '</option>');
		} else {
			$('#print-template').append('<option value="' + t + '">' + gettext(t) + '</option>');
		}
	}
};

print.prototype.setDefaultProjection = function(epsg) {
	$('#print-projection option[value="' + epsg +'"]').attr('selected','selected');
	// $('#print-projection').trigger('change');
};

// examples: mapoverview, author, mapgrid, mapprojection
print.prototype.setSectionVisibility = function(section, visible) {
	var s = $('#print-ui-' + section);
	if (visible)
		s.show();
	else
		s.hide();
}

print.prototype.convertBaseLayerToPrintLayer = function(bLayer, legends) {
	if (bLayer.getSource().urls) {
		if(bLayer.getSource().getUrls()[0].indexOf('data:image/gif;base64') == -1) {
			console.log(bLayer);
			if (bLayer.getSource() instanceof ol.source.OSM) {
				return {
					"name": bLayer.getProperties().label,
					"baseURL": "http://a.tile.openstreetmap.org",
					"type": "OSM",
					"imageExtension": "png"
				};
			} else if (bLayer.getSource() instanceof ol.source.WMTS) {
				var initialScale = 559082263.950892933;
				var scale = 0;
				var matrices = new Array();
				var tileGrid = bLayer.getSource().getTileGrid();
				var lastSize = 1;
				var format = bLayer.getSource().getFormat();
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
				var url = bLayer.getSource().getUrls()[0];
				if (url.indexOf('http') == -1) {
					url = this.origin + url;
				}
				return {
					"name": bLayer.title,
					"type": "WMTS",
					"baseURL": url,
					"opacity": 1.0,
					"layer": bLayer.getSource().getLayer(),
					"version": "1.0.0",
					"requestEncoding": "KVP",
					"dimensions": null,
					"dimensionParams": {},
					"matrixSet": bLayer.getSource().getMatrixSet(),
					"matrices": matrices,
					"imageFormat": format
				};

			} else if (bLayer.getSource() instanceof ol.source.TileWMS) {
				var url = bLayer.getSource().getUrls()[0];
				if (url.indexOf('http') == -1) {
					url = self.origin + url;
				}
				return {
					"name": bLayer.title,
					"type": "WMS",
					"layers": [bLayer.getSource().getParams()['LAYERS']],
					"baseURL": url,
					"imageFormat": bLayer.getSource().getParams()['FORMAT'],
					"version": bLayer.getSource().getParams()['VERSION'],
					"customParams": {
						"TRANSPARENT": "true"
					}
				};
			} else if (bLayer.getSource() instanceof ol.source.XYZ) {
				var url = bLayer.getSource().getUrls()[0];
				if (url.indexOf('http') == -1) {
					url = self.origin + url;
				}
				return {
					"name": bLayer.getProperties().label,
					"baseURL": url,
					"type": "OSM",
					"dpi": self.dpi,
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
				};
			}		
			var legendUrl = bLayer.legend_no_auth;
			if (legendUrl) {
				if (legendUrl.indexOf('http') == -1) {
					legendUrl = self.origin + legendUrl;
				}
				legendUrl = legendUrl.replace('getlegendgraphic', 'getlegendgraphic&transparent=true');
				var legend = {
					"name": bLayer.getProperties().label,
					"icons": [legendUrl.replace('forceLabels:on', 'forceLabels:on;columnheight:800;fontAntiAliasing:true;dpi:100;fontSize:12;columns:3')]
				};
				legends.push(legend);	
			}
		}
	}
	return null;
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
	var projection = $('#print-projection').val();

	if (this.supports('crsPermanent')) {
		projection = this.getAttributeDefaultValue('crsPermanent');
	}

	var overviewLayerId = $('#print-overview').val();
	var overviewLayer = self.baseLayers[parseInt(overviewLayerId)];
	var mapgridType = $("#print-mapgrid-gridtype").val();
	var mapgridIndent = 5; //$("#print-mapgrid-indent").val();
	var mapgridSpacing = $("#print-mapgrid-spacing").val();
	var author = $("#print-author").val();

	self.projection = projection;
	self.dpi = parseInt(dpi);
	self.printOverviewLayers = [overviewLayer];

	self.checkReprojection();

	var scaleToSet = $('#print-scale').val();
	if (scaleToSet == 'user-scale') {
		var userScaleStr = $("#print-userscale").val();
		var userScale = parseInt(userScaleStr);
		scaleToSet = userScale;
	}
	var useNearestScale = true;
	if (!scaleToSet) {
		scaleToSet = self.getScaleForResolution(); // Actual scale of the view if the user has not selected a scale
		scaleToSet = scaleToSet * 0.6;
		useNearestScale = false;
	}

	var mapLayers = this.map.getLayers().getArray();
	mapLayers.sort(function(la, lb) {
		return (lb.getZIndex()-la.getZIndex());
	});	
	var printLayers = new Array();
	var spacing = parseInt(mapgridSpacing);

	var layerGrid = 
		{
			"type": "grid",
			"gridType": mapgridType,
			// "numberOfLines": [
			//   5,
			//   5
			// ],
			"origin":[0,0],
			"spacing": [spacing,spacing], 
			"renderAsSvg": true,
			// "opacity": 0.3,
			// "haloColor": "#CCFFCC",
			// "labelColor": "black",
			"labelFormat": "%1.0f %s",
			"indent": parseInt(mapgridIndent),
			"rotateLabels": false,
			// "drawLabels": true,  // New property just if we need to put labels OUTSIDE
			"labelColor": "black",
			"haloRadius": 1,
			"font": {
			  "name": [
				"Liberation Sans",
				"Helvetica",
				"Nimbus Sans L",
				"Liberation Sans",
				"FreeSans",
				"Sans-serif"
			  ],
				"size": 6,				
			//   "style": "BOLD"
			}
		  };

		// var layerGridLabels = Object.assign({},layerGrid);
		// layerGridLabels.font.size = 6;
		// layerGridLabels.gridColor = 'white';
		// layerGridLabels.labelColor = 'black';
	if (this.supports('mapGrid')) {
    	if (mapgridType != 'NOGRID')
			printLayers.push(layerGrid);
	}

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
						var geojson = self.getGeoJSON(mapLayers[i]);
						if (geojson.features.length > 0) {
							printLayers.push({
								"type": "geojson",
								"geoJson": geojson,
								"style": self.getVectorStyles(mapLayers[i])
							});
						}
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
					legendUrl = legendUrl.replace('getlegendgraphic', 'getlegendgraphic&transparent=true');
					// NOTA: Columnheight es la forma de controlar que no se salga la leyenda del mapa, si la pones dentro. 
					// TODO: Para los A4 horizontales, 800 va bien, para A3 se puede usar 1000, etc.
					var legend = {
							"name": mapLayers[i].title,
				            "icons": [legendUrl.replace('forceLabels:on', 'forceLabels:on;columnheight:800;fontAntiAliasing:true;dpi:100;fontSize:12;columns:3')]
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
				var printLayer = self.convertBaseLayerToPrintLayer(baseLayers[i], legends);
				if (printLayer != null ) {
					printLayers.push(printLayer);
				} // printLayer
			} // getVisible
		} // baseLayer
	} // for
	
	var f = self.extentLayer.getSource().getFeatures()[0];
	var bAcceptsOverview = false;
	var outputFormat = $("#print-format option:selected").val();

	var proj3857 = new ol.proj.Projection({code: 'EPSG:3857'});
	var projLayout = new ol.proj.Projection({code: self.projection});
	var geom = f.getGeometry().clone();
	var center3857 = ol.extent.getCenter(geom.getExtent());
	if (self.projection !== 'EPSG:3857') {
		geom.transform(proj3857, projLayout);
	}


	var dataToPost = {
	  		"layout": self.capabilities.layouts[0].name,
			"outputFilename": gettext(self.capabilities.layouts[0].name),
		  	"outputFormat": outputFormat,
		  	"attributes": {
		  		"title": title,
		  		"scale": '1: ' + Number.parseInt(scaleToSet).toLocaleString(),
		  		// "legalWarning": legalWarning,
		  		"map": {
					"projection": self.projection,
		  			"dpi": parseInt(dpi),
		  			// "dpiSensitiveStyle":true,
		  			"rotation": rotation,
		  			// "center": self.map.getView().getCenter(),
					"center": ol.extent.getCenter(geom.getExtent()),
		  			"scale": scaleToSet,
		  			"useNearestScale": false, //useNearestScale,
		  			"layers": printLayers,
		  			// "bbox": geom.getExtent()
		  	    },
		  	    "logo_url": self.origin + self.conf.project_image,
		  	    //"logo_url": 'http://localhost' + self.conf.project_image,
		  	    "legend": {
		  	    	"name": gettext('Legend'),
		            "classes": legends
		        },
		        "crs": self.projection
		  	}
	};

	if (self.supports('author')) {
		dataToPost.attributes.author = author;
	}

	if (self.supports('legalWarning')) {
		dataToPost.attributes.legalWarning = legalWarning;
	}

	if (self.supports('overviewMap')) {
		bAcceptsOverview = true;
		dataToPost.attributes.overviewMap = {
				// "zoomFactor":5,
				"projection": 'EPSG:3857',
				"center": center3857,
				"scale" : 20*scaleToSet,
	            "layers": self.printOverviewLayers
		    };
	}
	if (self.supports('mapGrid')) {
		var auxLayers = [];		
		if (mapgridType != 'NOGRID') {
			auxLayers.push(layerGrid);
		}
		dataToPost.attributes.mapGrid = {
			"projection": self.projection,
			"dpi": parseInt(dpi),
			"dpiSensitiveStyle":false,
			"rotation": rotation,
			"center": ol.extent.getCenter(geom.getExtent()),
			"scale": scaleToSet,
			"useNearestScale": false, //useNearestScale,
			"layers": auxLayers,
			// "bbox": f.getGeometry().getExtent() // TODO: DEFINIR EL CENTRO EN LUGAR DEL BBOX
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

print.prototype.checkReprojection = function() {
	if (this.projection != 'EPSG:3857') {
		var mapLayers = this.map.getLayers().getArray();
		for (var layer of mapLayers) {
			if (layer.getVisible()) {
				if (layer.getSource() instanceof ol.source.XYZ) {
					alert(layer.getProperties().label + ':' + gettext('layers_xyz_cant_be_reprojected'));
					layer.setVisible(false);
					this.invisibleLayers.push(layer);
				} // xyz
			} // visible			
		} // for
	}
};

print.prototype.getScales = function (capabilities) {
	// attribute 3 is 'map'
    var scales = capabilities.layouts[0].attributes[3].clientInfo.scales;
    return scales;
};

// print.prototype.supportsGridMap = function (capabilities) {
// 	// search for attribute 'mapGrid'
// 	for (var att of capabilities.layouts[0].attributes) {
// 		if (att.name == 'mapGrid') {
// 			return true;
// 		}
// 	}
//     return false;
// };

// print.prototype.supportsAuthor = function (capabilities) {
// 	// search for attribute 'author'
// 	for (var att of capabilities.layouts[0].attributes) {
// 		if (att.name == 'author') {
// 			return true;
// 		}
// 	}
//     return false;
// };


// print.prototype.supportsOverview = function (capabilities) {
// 	// search for attribute 'overviewMap'
// 	for (var att of capabilities.layouts[0].attributes) {
// 		if (att.name == 'overviewMap') {
// 			return true;
// 		}
// 	}
//     return false;
// };

print.prototype.supports = function (param) {
	// search for attribute param
	for (var att of this.capabilities.layouts[0].attributes) {
		if (att.name == param) {
			return true;
		}
	}
    return false;
};

print.prototype.getAttributeDefaultValue = function (paramName) {
	// search for attribute param
	for (var att of this.capabilities.layouts[0].attributes) {
		if (att.name == paramName) {
			return att.default;
		}
	}
    return undefined;
};

print.prototype.getAttributeByName = function (paramName) {
	// search for attribute param
	for (var att of this.capabilities.layouts[0].attributes) {
		if (att.name == paramName) {
			return att;
		}
	}
    return undefined;
};


var inchesPerMeter = 39.3700787;
var dpi = 96;

print.prototype.getResolutionForScale = function (scaleDenominator) {
  let dpiMonitor = 120; // asumimos los dpi del monitor de un portátil, no hay otra forma de hacerlo mejor.
  // Tenemos que mostrar el cuadro que muestra la zona que se va a imprimir, y eso hace que no podamos poner la 
  // resolución de la vista exactamente a la escala de impresión. Tenemos que aplicar el factor de 0.6 que 
  // usamos en el renderExtent
  let factor = 0.6;
  return scaleDenominator / inchesPerMeter / dpiMonitor / 0.6;
}

print.prototype.getScaleForResolution = function() {
	const resolution = this.map.getView().getResolution();
	const mpu = this.map.getView().getProjection().getMetersPerUnit();
	return parseFloat(resolution.toString()) * mpu * inchesPerMeter * 120;
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
				//   var body = '';
				//   body += '<div class="row">';
				//   body +=     '<center><a href="' + reportInfo.downloadURL + '" download="' + gettext('print-layout.pdf') + '" title="fichero.pdf">' + gettext('Download pdf') + '</a></center>';
				//   body += '</div>';
				  
				//   $('#float-modal .modal-body').empty();
				//   $('#float-modal .modal-body').append(body);
				  
				//   var buttons = '';
				//   buttons += '<button id="float-modal-cancel-print" type="button" class="btn btn-default" data-dismiss="modal">' + gettext('Close') + '</button>';
				  
				//   $('#float-modal .modal-footer').empty();
				//   $('#float-modal .modal-footer').append(buttons);
				  
				//   $("#float-modal").modal('show');

				//   $('#float-modal-cancel-print').on('click', function () {
				// 	$('#float-modal').modal('hide');
				// });
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
 * ancho en metros = unidades jasper * 0.35273 * denominadorEscala / 1000
 */
print.prototype.renderPrintExtent = function(clientInfo) {
    var mapComponentWidth = this.map.getSize()[0]; // en metros
    var mapComponentHeight = this.map.getSize()[1];
    var currentMapRatio = mapComponentWidth / mapComponentHeight;
    var scaleFactor = 0.6;
    var desiredPrintRatio = clientInfo.width / clientInfo.height; // en unidades jasper
    var targetWidth;
    var targetHeight;
    var geomExtent = [];
    var feat;

    if (desiredPrintRatio >= currentMapRatio) {
        targetWidth = mapComponentWidth * scaleFactor;
        targetHeight = targetWidth / desiredPrintRatio;
    } else {
        targetHeight = mapComponentHeight * scaleFactor;
        targetWidth = targetHeight * desiredPrintRatio;
    }

	var scaleToSet = $('#print-scale').val();
	if (scaleToSet == 'user-scale') {
		var userScaleStr = $("#print-userscale").val();
		var userScale = parseInt(userScaleStr);
		scaleToSet = userScale;
	}
	var useNearestScale = true;
	if (!scaleToSet) {
		scaleToSet = this.getScaleForResolution(); // Actual scale of the view if the user has not selected a scale
		scaleToSet = scaleToSet * 0.6;
		useNearestScale = false;
	}

	// Vamos a poner una resolución un poco más alejada para poder visualizar el rectángulo del mapa y poder moverlo.
	// Si pusieramos la misma escala que queremos imprimir, el usuario no podría ajustar el rectángulo arrastrando,
	// ocuparía toda la vista.

	var center = this.map.getView().getCenter();

	let anchoMetros = clientInfo.width * 0.35273 * scaleToSet / 1000.0;
	let altoMetros = clientInfo.height * 0.35273 * scaleToSet / 1000.0;
    
	let minX = center[0] - (anchoMetros/2.0);
  	let minY = center[1]- (altoMetros/2.0);
  	let maxX = center[0] + (anchoMetros/2.0);
  	let maxY = center[1] + (altoMetros/2.0);

    // geomExtent = this.map.getView().calculateExtent([
    //     targetWidth,
    //     targetHeight
    // ]);

    geomExtent = [minX, minY, maxX, maxY];

    
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