/**
 * gvSIG Online.
 * Copyright (C) 2007-2015 gvSIG Association.
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
var editionBar = function(layerTree, map, featureType, selectedLayer) {
	$("body").overlay();
	
	var this_ = this;
	this.map = map;
	this.layerTree = layerTree;
	this.selectedLayer = selectedLayer;
	this.featureType = featureType;
	this.detailsTab = $('#details-tab');
	this.geometryType = null;
	for (var i=0; i<featureType.length; i++) {
		if (featureType[i].type.indexOf('gml:') > -1) {
			if (featureType[i].type == "gml:SurfacePropertyType") {
				this.geometryType = 'Polygon';
				
			} else if (featureType[i].type == "gml:MultiSurfacePropertyType") {
				this.geometryType = 'MultiPolygon';
				
			} else if (featureType[i].type == "gml:LineStringPropertyType") {
				this.geometryType = 'LineString';
				
			} else if (featureType[i].type == "gml:MultiLineStringPropertyType") {
				this.geometryType = 'MultiLineString';
				
			} else if (featureType[i].type == "gml:PointPropertyType") {
				this.geometryType = 'Point';
				
			} else if (featureType[i].type == "gml:MultiPointPropertyType") {
				this.geometryType = 'MultiPoint';
			}
		}
	}
	
	$('#map').append('<div id="editionbar" class="editionbar ol-unselectable ol-control"></div>');

	var drawControl = document.createElement('button');
	drawControl.setAttribute("id", "draw-control");
	drawControl.setAttribute("class", "toolbar-button");
	
	var icon = document.createElement('i');
	var drawHandler = null;
	if (this.geometryType == 'Point' || this.geometryType == 'MultiPoint') {
		drawControl.setAttribute("title", gettext('Add point'));
		icon.setAttribute("class", "fa fa-circle");
		drawControl.appendChild(icon);
		drawHandler = function(e) {
			this_.drawPointHandler(e);
		};
		
	} else if (this.geometryType == 'LineString' || this.geometryType == 'MultiLineString') {
		drawControl.setAttribute("title", gettext('Add line'));
		icon.setAttribute("class", "fa fa-code-fork");
		drawControl.appendChild(icon);
		drawHandler = function(e) {
			this_.drawLineHandler(e);
		};
		
	} else if (this.geometryType == 'Polygon' || this.geometryType == 'MultiPolygon') {
		drawControl.setAttribute("title", gettext('Add polygon'));
		icon.setAttribute("class", "fa fa-object-ungroup");
		drawControl.appendChild(icon);
		drawHandler = function(e) {
			this_.drawPolygonHandler(e);
		};
		
	}
	
	var modifyControl = document.createElement('button');
	modifyControl.setAttribute("id", "modify-control");
	modifyControl.setAttribute("class", "toolbar-button");
	modifyControl.setAttribute("title", gettext('Edit feature'));
	var modifyIcon = document.createElement('i');
	modifyIcon.setAttribute("class", "fa fa-pencil-square-o");
	modifyControl.appendChild(modifyIcon);
	var modHandler = function(e) {
		this_.modifyHandler(e);
	};
	
	var removeControl = document.createElement('button');
	removeControl.setAttribute("id", "remove-control");
	removeControl.setAttribute("class", "toolbar-button");
	removeControl.setAttribute("title", gettext('Remove feature'));
	var removeIcon = document.createElement('i');
	removeIcon.setAttribute("class", "fa fa-trash");
	removeControl.appendChild(removeIcon);
	var rmvHandler = function(e) {
		this_.removeHandler(e);
	};
	
	var stopEdition = document.createElement('button');
	stopEdition.setAttribute("id", "stop-edition");
	stopEdition.setAttribute("class", "toolbar-button");
	stopEdition.setAttribute("title", gettext('Stop edition'));
	var stopEditionIcon = document.createElement('i');
	stopEditionIcon.setAttribute("class", "fa fa-times");
	stopEdition.appendChild(stopEditionIcon);
	var stopHandler = function(e) {
		this_.stopEditionHandler(e);
	};
	
	this.$drawControl = $(drawControl);
	this.$modifyControl = $(modifyControl);
	this.$removeControl = $(removeControl);
	this.$stopEdition = $(stopEdition);
	
	$('#editionbar').append(drawControl);
	$('#editionbar').append(modifyControl);
	$('#editionbar').append(removeControl);
	$('#editionbar').append(stopEdition);
	
	drawControl.addEventListener('click', drawHandler, false);
	drawControl.addEventListener('touchstart', drawHandler, false);
	
	modifyControl.addEventListener('click', modHandler, false);
	modifyControl.addEventListener('touchstart', modHandler, false);
	
	removeControl.addEventListener('click', rmvHandler, false);
	removeControl.addEventListener('touchstart', rmvHandler, false);
	
	stopEdition.addEventListener('click', stopHandler, false);
	stopEdition.addEventListener('touchstart', stopHandler, false);
	
	this.formatWFS = new ol.format.WFS();
	this.formatGML = null;
	
	var uri = this.selectedLayer.namespace.split('/');
	var ws = uri[uri.length - 1];
	
	this.source = new ol.source.Vector({
		format: new ol.format.GeoJSON(),
		loader: function(extent, resolution, projection) {
			var url = this_.selectedLayer.wfs_url + '?service=WFS&' +
		        'version=1.1.0&request=GetFeature&typename=' + ws + ':' + this_.selectedLayer.layer_name +
		        '&outputFormat=json';
		    $.ajax({
		    	url: url,
		    	success: function(response) {
		    		
		    		this_.formatGML = new ol.format.GML({
		    			featureNS: this_.selectedLayer.namespace,
		    			featureType: this_.selectedLayer.layer_name,
		    			srsName: this_.selectedLayer.crs.crs
		    		});
		    		
			  		var proj = new ol.proj.Projection({
			    		code: this_.selectedLayer.crs.crs,
			    		axisOrientation: 'neu'
			    	});
			    	ol.proj.addProjection(proj);
			    	
		    		var format = new ol.format.GeoJSON();
		    		var features = format.readFeatures(response);
		    		for (var i=0; i<features.length; i++) {
		    			if (features[i].getGeometry()) {
		    				features[i].getGeometry().transform(proj, 'EPSG:3857');
		    			}
		    			
		    		}
		    		try{
		    			this_.source.addFeatures(features);
		    		} catch (e) {
		    			console.log(e);
		    		}
		    	}
		    });
		},
		strategy: function() {
			var extent = this_.map.getView().calculateExtent(this_.map.getSize()); 
	        return [extent];
	    }
	});
	
	var style = null;
	if (this.geometryType == 'Point' || this.geometryType == 'MultiPoint') {
		style = new ol.style.Style({
			image: new ol.style.Circle({
				radius: 5,
				fill: new ol.style.Fill({color: 'rgba(0,0,255, 0.5)'}),
				stroke: new ol.style.Stroke({color: 'rgba(0,0,255, 1.0)', width: 2})
			})
		});
		
	} else if (this.geometryType == 'LineString' || this.geometryType == 'MultiLineString') {
		style = new ol.style.Style({
			fill: new ol.style.Fill({color: 'rgba(0,0,255, 0.5)'}),
			stroke: new ol.style.Stroke({color: 'rgba(0,0,255, 1.0)', width: 3, lineDash: [4,4]})
		});
		
	} else if (this.geometryType == 'Polygon' || this.geometryType == 'MultiPolygon') {
		style = new ol.style.Style({
			fill: new ol.style.Fill({color: 'rgba(0,0,255, 0.5)'}),
			stroke: new ol.style.Stroke({color: 'rgba(0,0,255, 1.0)', width: 3, lineDash: [4,4]})
		});
	}

	this.wfsLayer = new ol.layer.Vector({
		source: this_.source,
		style: style
	});
	
	this.map.addLayer(this.wfsLayer);
	
	this.source.on('change', function() {
		$.overlayout();
    });

};

/**
 * TODO
 */
editionBar.prototype.drawInteraction = null;

/**
 * TODO
 */
editionBar.prototype.modifyInteraction = null;

/**
 * TODO
 */
editionBar.prototype.selectInteraction = null;

/**
 * TODO
 */
editionBar.prototype.removeInteraction = null;



/**
 * @param {Event} e Browser event.
 */
editionBar.prototype.getSelectedLayer = function(e) {
	return this.selectedLayer;
};

/**
 * @param {Event} e Browser event.
 */
editionBar.prototype.drawPointHandler = function(e) {
	e.preventDefault();
	if (this.$drawControl.hasClass('button-active')) {
		this.deactivateControls();
	} else {
		this.deactivateControls();
		this.$drawControl.addClass('button-active');
		this.$drawControl.trigger('control-active', [this]);
		this.addDrawInteraction();
	}
	

};

/**
 * @param {Event} e Browser event.
 */
editionBar.prototype.drawLineHandler = function(e) {
	e.preventDefault();
	if (this.$drawControl.hasClass('button-active')) {
		this.deactivateControls();
	} else {
		this.deactivateControls();
		this.$drawControl.addClass('button-active');
		this.$drawControl.trigger('control-active', [this]);
		this.addDrawInteraction();
	}
};

/**
 * @param {Event} e Browser event.
 */
editionBar.prototype.drawPolygonHandler = function(e) {
	e.preventDefault();
	if (this.$drawControl.hasClass('button-active')) {
		this.deactivateControls();
	} else {
		this.deactivateControls();
		this.$drawControl.addClass('button-active');
		this.$drawControl.trigger('control-active', [this]);
		this.addDrawInteraction();
	}
};

/**
 * @param {Event} e Browser event.
 */
editionBar.prototype.modifyHandler = function(e) {
	e.preventDefault();
	if (this.$modifyControl.hasClass('button-active')) {
		this.deactivateControls();
	} else {
		this.deactivateControls();
		this.$modifyControl.addClass('button-active');
		this.$modifyControl.trigger('control-active', [this]);
		this.addModifyInteraction();
	}
};

/**
 * @param {Event} e Browser event.
 */
editionBar.prototype.removeHandler = function(e) {
	e.preventDefault();
	if (this.$removeControl.hasClass('button-active')) {
		this.deactivateControls();
	} else {
		this.deactivateControls();
		this.$removeControl.addClass('button-active');
		this.$removeControl.trigger('control-active', [this]);
		this.addRemoveInteraction();
	}
};

/**
 * @param {Event} e Browser event.
 */
editionBar.prototype.stopEditionHandler = function(e) {
	e.preventDefault();
	this.deactivateControls();
	this.removeVectorLayer();
	$('#editionbar').remove();
	this.layerTree.editionBar = null;
	delete this.layerTree.editionBar;
	this.showLayersTab();
};

/**
 * TODO
 */
editionBar.prototype.addDrawInteraction = function() {
	
	var self = this;
	
	var geometryName = '';
	for (var i=0; i<this.featureType.length; i++) {
		if (this.featureType[i].type.indexOf('gml:') > -1) {
			geometryName = this.featureType[i].name;
		}
	}
	
	this.drawInteraction = new ol.interaction.Draw({
		source: this.source,
		type: (this.geometryType),
		geometryName: geometryName
	});
	this.map.addInteraction(this.drawInteraction);

	this.drawInteraction.on('drawstart',
		function(evt) {
		    console.log('Draw point start');
		}, this);

	this.drawInteraction.on('drawend',
		function(evt) {
			self.createFeatureForm(evt.feature);
		}, this);
	
};

/**
 * TODO
 */
editionBar.prototype.addModifyInteraction = function() {
	
	var self = this;
	
	this.selectInteraction = new ol.interaction.Select({
		wrapX: false
	});
	
	this.modifyInteraction = new ol.interaction.Modify({
		features: this.selectInteraction.getFeatures()
	});
	
	this.map.addInteraction(this.selectInteraction);
	this.map.addInteraction(this.modifyInteraction);
	
	this.selectInteraction.on('select',
		function(evt) {
			self.editFeatureForm(evt.selected[0]);
		}, this);
	
	this.modifyInteraction.on('modifystart',
		function(evt) {
			console.log('Modify feature start');
		}, this);
		
	this.modifyInteraction.on('modifyend',
		function(evt) {
			self.editFeatureForm(evt.features.getArray()[0]);
		}, this);
};


/**
 * TODO
 */
editionBar.prototype.addRemoveInteraction = function() {
	
	var self = this;
	
	this.removeInteraction = new ol.interaction.Select({
		wrapX: false
	});
	
	this.map.addInteraction(this.removeInteraction);
	
	this.removeInteraction.on('select',
	    function(evt) {
			self.removeFeatureForm(evt, evt.selected[0]);
	   	}, this);
};


/**
 * @param {Event} e Browser event.
 */
editionBar.prototype.deactivateControls = function() {
	var self = this;
	
	this.$drawControl.removeClass('button-active');
	this.$modifyControl.removeClass('button-active');
	this.$removeControl.removeClass('button-active');
	
	$('#editionbar').on( "control-active", function(e) {
		for (var i=0; i<self.map.tools.length; i++){
			if (e.target.id != self.map.tools[i].id) {
				if (self.map.tools[i].deactivable == true) {
					if (self.map.tools[i].active) {
						self.map.tools[i].deactivate();
					}
				}
			}
		}
	});
	
	this.showLayersTab();
	
	if (this.drawInteraction != null) {
		this.map.removeInteraction(this.drawInteraction);
		this.drawInteraction = null;
		this.source.clear();
	}
	
	if (this.modifyInteraction != null) {
		this.map.removeInteraction(this.modifyInteraction);
		this.modifyInteraction = null;
	}
	
	if (this.selectInteraction != null) {
		this.map.removeInteraction(this.selectInteraction);
		this.selectInteraction = null;
	}
	
	if (this.removeInteraction != null) {
		this.map.removeInteraction(this.removeInteraction);
		this.removeInteraction = null;
	}

};


/**
 * @param {Event} e Browser event.
 */
editionBar.prototype.removeVectorLayer = function() {	
	this.source.clear();
	this.map.removeLayer(this.wfsLayer);

};



/**
 * @param {Event} e Browser event.
 */
editionBar.prototype.createFeatureForm = function(feature) {	
	
	this.showDetailsTab();
	
	this.detailsTab.empty();	
	var self = this;
	
	var ui = '';
	ui += '<div class="box box-success">';
	ui += 		'<div class="box-header with-border">';
	ui += 			'<h3 class="box-title">' + gettext('New feature') + '</h3>';
	ui += 			'<div class="box-tools pull-right">';
	//ui += 				'<button type="button" class="btn btn-box-tool" data-widget="remove"><i class="fa fa-times"></i></button>';
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 		'<div class="box-body no-padding">';
	ui += 			'<div id="col-md-12 form-group form-error" style="color:#ff0000;">';
	ui += 			'</div>';
	for (var i=0; i<this.featureType.length; i++) {
		if ((this.featureType[i].type.indexOf('gml:') == -1) && this.featureType[i].name != 'id') {
			ui += '<div class="col-md-12 form-group">';
			ui += 	'<label style="color: #3c8dbc;">' + this.featureType[i].name + '</label>';
			if (this.featureType[i].type == 'xsd:double' || this.featureType[i].type == 'xsd:decimal' || this.featureType[i].type == 'xsd:integer' || this.featureType[i].type == 'xsd:int' || this.featureType[i].type == 'xsd:long') {
				ui += '<input id="' + this.featureType[i].name + '" type="number" step="any" class="form-control">';
				
			} else if (this.featureType[i].type == 'xsd:date') {
				ui += '<input id="' + this.featureType[i].name + '" type="text" class="form-control" placeholder="yyyy-mm-dd">';
				
			} else if (this.featureType[i].type == 'xsd:string') {
				ui += '<input id="' + this.featureType[i].name + '" type="text" class="form-control">';
				
			}  else if (this.featureType[i].type == 'xsd:boolean') {
				ui += '<input id="' + this.featureType[i].name + '" type="checkbox" class="checkbox">';			
			}
			ui += '</div>';
		}
	}
	ui += 		'</div>';
	ui += 		'<div class="box-footer text-right">';
	ui += 			'<button id="save-feature" class="btn btn-default margin-r-5">' + gettext('Save') + '</button>';
	ui += 			'<button id="save-feature-cancel" class="btn btn-default">' + gettext('Cancel') + '</button>';
	ui += 		'</div>';
	ui += '</div>';
	
	this.detailsTab.append(ui);
	$.gvsigOL.controlSidebar.open();
	
	$('#save-feature').on('click', function () {
		var properties = {};
		for (var i=0; i<self.featureType.length; i++) {
			if ((self.featureType[i].type.indexOf('gml:') == -1) && self.featureType[i].name != 'id') {
				var field = $('#' + self.featureType[i].name)[0];
				if (self.featureType[i].type == 'xsd:boolean') {
					properties[field.id] = field.checked;
				} else {
					properties[field.id] = field.value;
				}				
			}
		}
		feature.setProperties(properties);
		if (self.transactWFS('insert', feature)) {
			self.selectedLayer.getSource().updateParams({"time": Date.now()});
			self.showLayersTab();
		}		
	});
	
	$('#save-feature-cancel').on('click', function () {
		self.source.removeFeature(feature);
		self.showLayersTab();
	});

};


/**
 * @param {Event} e Browser event.
 */
editionBar.prototype.editFeatureForm = function(feature) {	
	
	this.showDetailsTab();
	
	this.detailsTab.empty();	
	var self = this;
	
	var ui = '';
	ui += '<div class="box box-success">';
	ui += 		'<div class="box-header with-border">';
	ui += 			'<h3 class="box-title">' + gettext('Edit feature') + '</h3>';
	ui += 			'<div class="box-tools pull-right">';
	//ui += 				'<button type="button" class="btn btn-box-tool" data-widget="remove"><i class="fa fa-times"></i></button>';
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 		'<div class="box-body no-padding">';
	ui += 			'<div id="col-md-12 form-group form-error" style="color:#ff0000;">';
	ui += 			'</div>';
	for (var i=0; i<this.featureType.length; i++) {
		if ((this.featureType[i].type.indexOf('gml:') == -1) && this.featureType[i].name != 'id') {
			ui += '<div class="col-md-12 form-group">';
			ui += 	'<label style="color: #3c8dbc;">' + this.featureType[i].name + '</label>';
			if (this.featureType[i].type == 'xsd:double' || this.featureType[i].type == 'xsd:decimal' || this.featureType[i].type == 'xsd:integer' || this.featureType[i].type == 'xsd:int' || this.featureType[i].type == 'xsd:long') {
				ui += '<input id="' + this.featureType[i].name + '" type="number" step="any" class="form-control" value="' + feature.getProperties()[this.featureType[i].name] + '">';
				
			} else if (this.featureType[i].type == 'xsd:date') {
				ui += '<input id="' + this.featureType[i].name + '" type="text" class="form-control" placeholder="yyyy-mm-dd" value="' + feature.getProperties()[this.featureType[i].name] + '">';
				
			} else if (this.featureType[i].type == 'xsd:string') {
				ui += '<input id="' + this.featureType[i].name + '" type="text" class="form-control" value="' + feature.getProperties()[this.featureType[i].name] + '">';
				
			}  else if (this.featureType[i].type == 'xsd:boolean') {
				var checked = feature.getProperties()[this.featureType[i].name];
				if (checked) {
					ui += '<input id="' + this.featureType[i].name + '" type="checkbox" class="checkbox" checked>';
				} else {
					ui += '<input id="' + this.featureType[i].name + '" type="checkbox" class="checkbox">';
				}				
			}
			ui += '</div>';
		}
	}
	ui += 		'</div>';
	ui += 		'<div class="box-footer text-right">';
	ui += 			'<button id="edit-feature" class="btn btn-default margin-r-5">' + gettext('Save') + '</button>';
	ui += 			'<button id="edit-feature-cancel" class="btn btn-default">' + gettext('Cancel') + '</button>';
	ui += 		'</div>';
	ui += '</div>';
	
	this.detailsTab.append(ui);
	$.gvsigOL.controlSidebar.open();
	
	$('#edit-feature').on('click', function () {
		var properties = {};
		for (var i=0; i<self.featureType.length; i++) {
			if (self.featureType[i].type.indexOf('gml:') == -1) {
				if (self.featureType[i].name != 'id') {
					var field = $('#' + self.featureType[i].name)[0];
					if (self.featureType[i].type == 'xsd:boolean') {
						properties[field.id] = field.checked;
					} else {
						properties[field.id] = field.value;
					}
				}
			}
		}
		feature.setProperties(properties);
		if (self.transactWFS('update', feature)) {
			self.selectedLayer.getSource().updateParams({"time": Date.now()});
			self.selectInteraction.getFeatures().clear();
			self.showLayersTab();
		}		
	});
	
	$('#edit-feature-cancel').on('click', function () {
		self.selectInteraction.getFeatures().clear();
		self.showLayersTab();
	});

};


/**
 * @param {Event} e Browser event.
 */
editionBar.prototype.removeFeatureForm = function(evt, feature) {	
	
	this.showDetailsTab();
	
	this.detailsTab.empty();	
	var self = this;
	
	var ui = '';
	ui += '<div class="box box-success">';
	ui += 		'<div class="box-header with-border">';
	ui += 			'<h3 class="box-title">' + gettext('Remove feature') + '</h3>';
	ui += 			'<div class="box-tools pull-right">';
	//ui += 				'<button type="button" class="btn btn-box-tool" data-widget="remove"><i class="fa fa-times"></i></button>';
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 		'<div class="box-body no-padding">';
	ui += 			'<div id="col-md-12 form-group form-error" style="color:#ff0000;">';
	ui += 			'</div>';
	for (var i=0; i<this.featureType.length; i++) {
		if ((this.featureType[i].type.indexOf('gml:') == -1) && this.featureType[i].name != 'id') {
			ui += '<div class="col-md-12 form-group">';
			ui += 	'<label style="color: #3c8dbc;">' + this.featureType[i].name + '</label>';
			if (this.featureType[i].type == 'xsd:double' || this.featureType[i].type == 'xsd:decimal' || this.featureType[i].type == 'xsd:integer' || this.featureType[i].type == 'xsd:int' || this.featureType[i].type == 'xsd:long') {
				ui += '<input disabled id="' + this.featureType[i].name + '" type="number" step="any" class="form-control" value="' + feature.getProperties()[this.featureType[i].name] + '">';
				
			} else if (this.featureType[i].type == 'xsd:date') {
				ui += '<input disabled id="' + this.featureType[i].name + '" type="text" class="form-control" placeholder="yyyy-mm-dd" value="' + feature.getProperties()[this.featureType[i].name] + '">';
				
			} else if (this.featureType[i].type == 'xsd:string') {
				ui += '<input disabled id="' + this.featureType[i].name + '" type="text" class="form-control" value="' + feature.getProperties()[this.featureType[i].name] + '">';
			}
			ui += '</div>';
		}
	}
	ui += 		'</div>';
	ui += 		'<div class="box-footer text-right">';
	ui += 			'<button id="remove-feature" class="btn btn-default margin-r-5">' + gettext('remove') + '</button>';
	ui += 			'<button id="save-feature-cancel" class="btn btn-default">' + gettext('Cancel') + '</button>';
	ui += 		'</div>';
	ui += '</div>';
	
	this.detailsTab.append(ui);
	$.gvsigOL.controlSidebar.open();
	
	$('#remove-feature').on('click', function () {
		if (self.transactWFS('delete', feature)) {
			self.wfsLayer.getSource().removeFeature(feature);
			self.removeInteraction.getFeatures().clear();
			self.selectedLayer.getSource().updateParams({"time": Date.now()});
			self.showLayersTab();
		}		
	});
	
	$('#save-feature-cancel').on('click', function () {
		self.removeInteraction.getFeatures().clear();
		self.showLayersTab();
	});

};



/**
 * @param {Event} e Browser event.
 */
editionBar.prototype.transactWFS = function(p,f) {
	var self = this;
	var success = false;

	var cloned = f.clone();	
	cloned.getGeometry().transform('EPSG:3857',this.selectedLayer.crs.crs);
	cloned.setId(f.getId());
	
	switch(p) {
		case 'insert':			
			node = this.formatWFS.writeTransaction([cloned],null,null,this.formatGML);
			break;
		case 'update':
			var geometryName = '';
			for (var i=0; i<this.featureType.length; i++) {
				if (this.featureType[i].type.indexOf('gml:') > -1) {
					geometryName = this.featureType[i].name;
				}
			}
			var properties = cloned.getProperties();
			if (geometryName != 'geometry') {
				properties[geometryName] = cloned.getGeometry();
			}
			var coordinates = cloned.getGeometry().getCoordinates();
			/*if (this.geometryType == 'point') {
				coordinates[0].reverse();
				
			} else if (this.geometryType == 'line'){
				for (var j=0; j<coordinates[0].length; j++) {
					coordinates[0][j].reverse();
				}
				
			} else if (this.geometryType == 'polygon'){
				for (var j=0; j<coordinates[0][0].length; j++) {
					coordinates[0][0][j].reverse();
				}
			}*/
			
			cloned.getGeometry().setCoordinates(coordinates);
			cloned.setGeometryName(geometryName);
			
			if (geometryName != 'geometry') {
				properties['geometry'] = null;
				delete properties['geometry'];
			}
			
			var feature = new ol.Feature();
			feature.setGeometry(cloned.getGeometry());				
			feature.setProperties(properties);
			feature.setId(f.getId());
			
			node = this.formatWFS.writeTransaction(null,[feature],null,this.formatGML);
			break;
		case 'delete':
			node = this.formatWFS.writeTransaction(null,null,[cloned],this.formatGML);
			break;
	}
	s = new XMLSerializer();
	str = s.serializeToString(node);
	$.ajax(this.selectedLayer.wfs_url,{
		type: 'POST',
		async: false,
	    dataType: 'xml',
	    processData: false,
	    contentType: 'text/xml',
	    data: str
	}).success(function(response, status, request) {
		try {
			var resp = self.formatWFS.readTransactionResponse(response);
			f.setId(resp.insertIds[0]);
			success = true;
			if (p=="insert"||p=="update") {
				/* Trigger a bounding box recalculating after insertions or
				 * updates to ensure the bounding box of the service covers
				 * all the layer geometries.
				 * 
				 * Avoid using it on deletions as triggering
				 * an update on an empty layer will produce incorrect
				 * bounding boxes.
				 */
				try {
					self.updateServiceBoundingBox(self.selectedLayer.workspace, self.selectedLayer.layer_name);
				} catch (e) {} // ignore errors
			}
			
		} catch (err) {
			$('#form-error').empty();
			$('#form-error').append('<p> * ' + gettext('Failed to save the new record. Please check values') + '</p>');
			success = false;
		}
		
	});
	
	return success;
};

/**
 * Triggers an update of the bounding box of the service.
 * 
 */
editionBar.prototype.updateServiceBoundingBox = function(workspace,layerName) {
	$.ajax({
		type: 'POST',
		async: true,
	  	url: '/gvsigonline/services/layer_boundingbox_from_data/',
	  	data: {
		  	workspace: workspace,
		  	layer: layerName
		},
	  	beforeSend:function(xhr){
	    	xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
	  	}
	});
};

/**
 * TODO
 */
editionBar.prototype.showDetailsTab = function(p,f) {
	$('.nav-tabs a[href="#details-tab"]').tab('show');
};

/**
 * TODO
 */
editionBar.prototype.showLayersTab = function(p,f) {
	this.detailsTab.empty();
	$('.nav-tabs a[href="#layer-tree-tab"]').tab('show');
};