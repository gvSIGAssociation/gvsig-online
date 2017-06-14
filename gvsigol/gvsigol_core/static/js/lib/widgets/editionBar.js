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
var editionBar = function(layerTree, map, featureType, selectedLayer) {
	$("body").overlay();
	
	var this_ = this;
	this.map = map;
	this.layerTree = layerTree;
	this.selectedLayer = selectedLayer;
	this.resourceManager = null;
	if (layerTree.conf.resource_manager == 'gvsigol') {
		this.resourceManager = new GvsigolResourceManager(this.selectedLayer);
	} else if (layerTree.conf.resource_manager == 'alfresco') {
		this.resourceManager = new AlfrescoResourceManager(this.selectedLayer);
	}	
	this.featureType = featureType;
	this.detailsTab = $('#details-tab');
	this.geometryType = null;
	this.geometryName = null;
	this.lastAddedFeature = null;
	this.lastEditedFeature = null;
	for (var i=0; i<featureType.length; i++) {
		if (this.isGeomType(this.featureType[i].type)) {
			if (featureType[i].type == "POLYGON") {
				this.geometryType = 'Polygon';
				this.geometryName = featureType[i].name;
			} else if (featureType[i].type == "MULTIPOLYGON") {
				this.geometryType = 'MultiPolygon';
				this.geometryName = featureType[i].name;
			} else if (featureType[i].type == "LINESTRING") {
				this.geometryType = 'LineString';
				this.geometryName = featureType[i].name;
			} else if (featureType[i].type == "MULTILINESTRING") {
				this.geometryType = 'MultiLineString';
				this.geometryName = featureType[i].name;
			} else if (featureType[i].type == "POINT") {
				this.geometryType = 'Point';
				this.geometryName = featureType[i].name;
			} else if (featureType[i].type == "MULTIPOINT") {
				this.geometryType = 'MultiPoint';
				this.geometryName = featureType[i].name;
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
	
	
	var drawInCenterControl = document.createElement('button');
	drawInCenterControl.setAttribute("id", "draw-in-center-control");
	drawInCenterControl.setAttribute("class", "toolbar-button");
	
	var icon2 = document.createElement('i');
	var drawHandler2 = null;
	if (this.geometryType == 'Point' || this.geometryType == 'MultiPoint') {
		drawInCenterControl.setAttribute("title", gettext('Add point to center'));
		icon2.setAttribute("class", "fa fa-crosshairs");
		drawInCenterControl.appendChild(icon2);
		drawHandler2 = function(e) {
			this_.drawPointInCenterHandler(e);
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
	
	this.$drawInCenterControl = $(drawInCenterControl);
	this.$drawControl = $(drawControl);
	this.$modifyControl = $(modifyControl);
	this.$removeControl = $(removeControl);
	this.$stopEdition = $(stopEdition);
	
	if (this.geometryType == 'Point' || this.geometryType == 'MultiPoint') {
		$('#editionbar').append(drawInCenterControl);
	}
	$('#editionbar').append(drawControl);
	$('#editionbar').append(modifyControl);
	$('#editionbar').append(removeControl);
	$('#editionbar').append(stopEdition);
	
	drawInCenterControl.addEventListener('click', drawHandler2, false);
	drawInCenterControl.addEventListener('touchstart', drawHandler2, false);
	
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
	this.formatGeoJSON = new ol.format.GeoJSON({geometryName: this.geometryName});
	this.mapSRS = 'EPSG:3857';
	
	this.source = new ol.source.Vector({
		format: this.formatGeoJSON,
		loader: function(extent, resolution, projection) {
			var url = this_.selectedLayer.wfs_url + '?service=WFS&' +
				'version=1.1.0&request=GetFeature&typename=' + ws + ':' + this_.selectedLayer.layer_name +
				'&outputFormat=json&srsName='+this_.mapSRS;
			$.ajax({
				url: url,
				editionBar: this_,
				success: function(response) {
					try{
						// WARNING: format.GML will automatically invert the coordinates order when required
						// if the axisOrientation is defined in the CRS definitions in OL
						this_.formatGML = new ol.format.GML({
							featureNS: this_.selectedLayer.namespace,
							featureType: this_.selectedLayer.layer_name,
							srsName: this_.mapSRS
						});
						
						var features = this_.formatGeoJSON.readFeatures(response);
						this_.source.addFeatures(features);
					} catch (e) {
						console.log(e);
						this.editionBar.stopEditionHandler();
						$.overlayout();
						messageBox.show('error', gettext('Error starting edition'));
					}
				},
				error: function(jqXHR, textStatus) {
					this.editionBar.stopEditionHandler();
					$.overlayout();
					messageBox.show('error', gettext('Error starting edition'));
					console.log(textStatus);
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
editionBar.prototype.drawInCenterInteraction = null;

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
editionBar.prototype.drawPointInCenterHandler = function(e) {
	e.preventDefault();
	if (this.$drawInCenterControl.hasClass('button-active')) {
		this.deactivateControls();
		$("#center-cursor").hide();
	} else {
		this.deactivateControls();
		$("#center-cursor").show();
		this.$drawInCenterControl.addClass('button-active');
		this.$drawInCenterControl.trigger('control-active', [this]);
		
		this.addDrawInCenterInteraction();
	}
	

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
	if (e!=null) {
		e.preventDefault();
	}
	$("#center-cursor").hide();
	this.deactivateControls();
	this.removeVectorLayer();
	$('#editionbar').remove();
	this.removeLayerLock();
	this.layerTree.editionBar = null;
	delete this.layerTree.editionBar;
	this.showLayersTab();
};

/**
 * TODO
 */
editionBar.prototype.addDrawInteraction = function() {
	
	var self = this;

	this.drawInteraction = new ol.interaction.Draw({
		source: this.source,
		type: (this.geometryType),
		geometryName: this.geometryName
	});
	this.map.addInteraction(this.drawInteraction);

	this.drawInteraction.on('drawstart',
		function(evt) {
			if (self.lastAddedFeature != null) {
				self.source.removeFeature(self.lastAddedFeature);
				self.lastAddedFeature = null;
			}
			console.log('Draw point start');
		}, this);

	this.drawInteraction.on('drawend',
		function(evt) {
			self.lastAddedFeature = evt.feature;
			self.createFeatureForm(evt.feature);
		}, this);
	
};

editionBar.prototype.addDrawInCenterInteraction = function() {
	
	var self = this;

	this.drawInCenterInteraction = new ol.interaction.Draw({
		source: this.source,
		type: (this.geometryType),
		geometryName: this.geometryName
	});
	this.map.addInteraction(this.drawInCenterInteraction);

	this.drawInCenterInteraction.on('drawstart',
		function(evt) {
			if (self.lastAddedFeature != null) {
				self.source.removeFeature(self.lastAddedFeature);
				self.lastAddedFeature = null;
			}
			console.log('Draw centered point start');
		}, this);

	this.drawInCenterInteraction.on('drawend',
		function(evt) {
			self.lastAddedFeature = evt.feature;
			
			var feature = evt.feature;
			var pos = self.map.getView().getCenter();
			var geoms = feature.getGeometry();
			geoms.flatCoordinates = pos;
			self.createFeatureForm(evt.feature);
		}, this);
	
};

/**
 * TODO
 */
editionBar.prototype.addModifyInteraction = function() {
	
	var self = this;
	
	this.selectInteraction = new ol.interaction.Select({
		wrapX: false,
		hitTolerance: 20
	});
	
	this.modifyInteraction = new ol.interaction.Modify({
		features: this.selectInteraction.getFeatures()
	});
	
	this.map.addInteraction(this.selectInteraction);
	this.map.addInteraction(this.modifyInteraction);
	
	this.selectInteraction.on('select',
		function(evt) {
			if (self.lastEditedFeature != null) {
				self.revertEditedFeature();
			}
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
	if (self.lastAddedFeature != null) {
		self.source.removeFeature(self.lastAddedFeature);
		self.lastAddedFeature = null;
	}
	this.revertEditedFeature();
	
	this.$drawInCenterControl.removeClass('button-active');
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
	$("#center-cursor").hide();
	
	this.showLayersTab();
	
	if (this.drawInCenterInteraction != null) {
		this.map.removeInteraction(this.drawInCenterInteraction);
		this.drawInCenterInteraction = null;
	}
	
	if (this.drawInteraction != null) {
		this.map.removeInteraction(this.drawInteraction);
		this.drawInteraction = null;
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
editionBar.prototype.getEnumeration = function(enumName) {	
	var enumeration = {};
	$.ajax({
		type: 'POST',
		async: false,
	  	url: "/gvsigonline/services/get_enumeration/",
	  	data: {
	  		'enum_name': enumName
		},
	  	success	:function(response){
	  		enumeration.title = response.title;
	  		enumeration.items = response.items;
		},
	  	error: function(){}
	});
	
	return enumeration;
};


editionBar.prototype.isNumericType = function(type){
	if(type == 'smallint' || type == 'integer' || type == 'bigint' || type == 'decimal' || type == 'numeric' ||
			type == 'real' || type == 'double precision' || type == 'smallserial' || type == 'serial' || type == 'bigserial' ){
		return true;
	}
	return false;
}


editionBar.prototype.getNumericProperties = function(featureType){
	var type = featureType.type;
	
	if(type == 'smallint'){
		return "min=-32768 max=32767 step=1"
	} 
	
	if(type == 'integer'){
		return "min=-2147483648 max=2147483648 step=1"
	} 
	
	if(type == 'bigint'){
		return "min=-9223372036854775808 max=9223372036854775808 step=1"
	} 
	
	
	if(type == 'smallserial'){
		return "min=1 max=32767 step=1"
	} 
	
	if(type == 'serial'){
		return "min=1 max=2147483647 step=1"
	} 
	
	if(type == 'bigserial'){
		return "min=1 max=9223372036854775808 step=1"
	} 
	
	if(type == 'real'){
		return "step=any"
	} 
	
	
	if(type == 'double precision'){
		return "step=any"
	} 
	
	if(type == 'decimal' || type == 'numeric' ){
		var min_string="0";
		for(var i=0; i<featureType.precision-featureType.scale; i++){
			if(i==0){
				min_string = "9";
			}else{
				min_string += "9";
			}
		}
		var has_decimals = true;
		var scale = ""
		for(var i=0; i<featureType.scale; i++){
			if(has_decimals){
				min_string += ".";
				scale = "0.";
				has_decimals = false;
			}
			min_string += "9";
			if(i!=0){
				scale += "0";
			}
		}
		scale += "1";
		return "min=-"+min_string+" max="+ min_string +" step="+scale;
		//return "min=-999999999999999 max=999999999999999 step=0,000000000000000000001";
	} 
	

	return "";
}


editionBar.prototype.getFeatureTypeDefinition = function(name){
	var type = "";
	var featureType = null;
	for(var i=0; i<this.featureTypes.length; i++){
		if(this.featureTypes[i].name == name){
			featureType = this.featureTypes[i];
			type = featureType.type;
		}
	}
	
	if(type == 'smallint'){
		return {
			type: 'smallint',
			min: -32768,
			max: 32767,
			step: 1
		}
	} 
	
	if(type == 'integer'){
		return {
			type: 'integer',
			min: -2147483648,
			max: 2147483647,
			step: 1
		}
	} 
	
	if(type == 'bigint'){
		return {
			type: 'bigint',
			min: -9223372036854775808,
			max: 9223372036854775808,
			step: 1
		}
	} 
	
	
	if(type == 'smallserial'){
		return {
			type: 'smallserial',
			min: 1,
			max: 32767,
			step: 1
		}
	} 
	
	if(type == 'serial'){
		return {
			type: 'serial',
			min: 1,
			max: 2147483647,
			step: 1
		}
	} 
	
	if(type == 'bigserial'){
		return {
			type: 'bigserial',
			min: 1,
			max: 9223372036854775808,
			step: 1
		}
	} 
	
	if(type == 'real'){
		return {
			type: 'real',
			min: null,
			max: null,
			step: 0.000001
		}
	} 
	
	
	if(type == 'double precision'){
		return {
			type: 'double precision',
			min: null,
			max: null,
			step: 0.000000000000001
		}
	} 
	
	if(type == 'decimal' || type == 'numeric' ){
		var min_string="0";
		for(var i=0; i<featureType.precision; i++){
			if(i!=0){
				min_string = "9";
			}else{
				min_string += "9";
			}
		}
		min_string += ".";
		var scale = "0."
		for(var i=0; i<featureType.scale; i++){
			min_string += "9";
			if(i!=0){
				scale += "0";
			}
		}
		scale += "1";
		return {
			type: type,
			min: -parseInt(min_string),
			max: parseInt(min_string),
			step: parseInt(scale)
		}
	} 
	

	return {
		type: null,
		min: null,
		max: null,
		step: null
	};
}


editionBar.prototype.isStringType = function(type){
	if(type == 'character varying' || type == 'varchar' || type == 'character' || type == 'char' || type == 'text' ){
		return true;
	}
	return false;
}

editionBar.prototype.isDateType = function(type){
	if(type == 'date' || type == 'timestamp' || type == 'time' || type == 'interval'){
		return true;
	}
	return false;
}

editionBar.prototype.isGeomType = function(type){
	if(type == 'POLYGON' || type == 'MULTIPOLYGON' || type == 'LINESTRING' || type == 'MULTILINESTRING' || type == 'POINT' || type == 'MULTIPOINT'){
		return true;
	}
	return false;
}



/**
 * @param {Event} e Browser event.
 */
editionBar.prototype.createFeatureForm = function(feature) {	
	if (feature) {
		this.showDetailsTab();
		this.detailsTab.empty();	
		var self = this;
		
		var featureProperties = '';
		featureProperties += '<div class="box">';
		featureProperties += 	'<div class="feature-div box-body no-padding">';
		
		var fields = this.selectedLayer.conf.fields;
		for (var i=0; i<this.featureType.length; i++) {
			if (!this.isGeomType(this.featureType[i].type) && this.featureType[i].name != 'id') {
				var name = '<span class="edit-feature-field">' + this.featureType[i].name + '</span>';
				var visible = true;
				if(fields){
					for(var ix =0; ix<fields.length; ix++){
						if(fields[ix].name.toLowerCase() == this.featureType[i].name){
							var lang = $("#select-language").val();
							if(fields[ix]["title-"+lang] && fields[ix]["title-"+lang] != ""){
								name = '<span class="edit-feature-field">' + fields[ix]["title-"+lang] + '</span><br /><span style="font-weight: normal;">('+name+')</span>';
							}
							if(fields[ix].editable != undefined){
								visible = fields[ix].editable;
							}
						}
					}
				}
				if(visible){
					featureProperties += '<div class="col-md-12 form-group" style="background-color: #fff;">';
					featureProperties += 	'<label style="color: #444;">' + name + '</label>';
					if (this.isNumericType(this.featureType[i].type)) {
						var numeric_conf = this.getNumericProperties(this.featureType[i]);
						featureProperties += '<input id="' + this.featureType[i].name + '" type="number" '+ numeric_conf+' class="form-control">';
						
					} else if (this.isDateType(this.featureType[i].type)) {
						featureProperties += '<input id="' + this.featureType[i].name + '" data-provide="datepicker" class="form-control" data-date-format="yyyy-mm-dd">';
						
					} else if (this.isStringType(this.featureType[i].type)) {
						if (this.featureType[i].name.startsWith("enm_")) {
							var enumeration = this.getEnumeration(this.featureType[i].name);
							featureProperties += 	'<select id="' + this.featureType[i].name + '" class="form-control">';
							for (var j=0; j<enumeration.items.length; j++) {
								featureProperties += '<option value="' + enumeration.items[j].name + '">' + enumeration.items[j].name + '</option>';
							}
							featureProperties += 	'</select>';
						} else {
							if("length" in this.featureType[i] && this.featureType[i].length>0){
								featureProperties += '<input id="' + this.featureType[i].name + '" type="text" maxlength="'+this.featureType[i].length+'" class="form-control">';
							}else{
								featureProperties += '<input id="' + this.featureType[i].name + '" type="text" class="form-control">';
							}
						}
						
					}  else if (this.featureType[i].type == 'boolean') {
						featureProperties += '<input id="' + this.featureType[i].name + '" type="checkbox" class="checkbox">';			
					}
					featureProperties += '</div>';
				}
			}
		}
		featureProperties +=       '<div class="col-md-12 form-group" id="edition-error">';
		featureProperties +=       '</div>';
		featureProperties += 	'</div>';
		featureProperties += 	'<div class="box-footer text-right">';
		featureProperties += 		'<button id="save-feature" class="btn btn-default margin-r-5">' + gettext('Save') + '</button>';
		featureProperties += 		'<button id="save-feature-cancel" class="btn btn-default">' + gettext('Cancel') + '</button>';
		featureProperties += 	'</div>';
		featureProperties += '</div>';
		
		var ui = '';
		ui += '<div class="nav-tabs-custom">';
		ui += 	'<ul class="nav nav-tabs">';
		ui += 		'<li class="active"><a href="#edit_feature_properties" data-toggle="tab" aria-expanded="true" style="font-weight: bold;">' + gettext('Feature properties') + '</a></li>';
		ui += 		'<li class=""><a href="#edit_feature_resources" data-toggle="tab" aria-expanded="false" style="font-weight: bold;">' + gettext('Feature resources') + '</a></li>';
		ui += 	'</ul>';
		ui += 	'<div class="tab-content">';
		ui += 		'<div class="tab-pane active" id="edit_feature_properties">';
		ui += 			featureProperties
		ui += 		'</div>';
		ui += 		'<div class="tab-pane" id="edit_feature_resources">';
		ui += 			this.resourceManager.getUI(feature);
		ui += 		'</div>';
		ui += 	'</div>';
		ui += '</div>';
		
		this.detailsTab.append(ui);
		$.gvsigOL.controlSidebar.open();
		this.resourceManager.registerEvents();
		
		var uploader = null;
		if (this.resourceManager.getEngine() == 'gvsigol') {
			uploader = this.resourceManager.createUploader();
		}
		
		$('#edit_feature_properties .form-control').on('blur', function (evt) {
			var props = feature.getProperties();
			props[evt.currentTarget.id] = evt.currentTarget.value;
			feature.setProperties(props);
		});
		$('#edit_feature_properties .checkbox').on('blur', function (evt) {
			var props = feature.getProperties();
			props[evt.currentTarget.id] = evt.currentTarget.checked;
			feature.setProperties(props);
		});
		

		$(".feature-div").each(self.createAllErrors);
	
		
		$('#save-feature').on('click', function () {
			if(self.showAllErrorMessages()){
			var properties = {};
			for (var i=0; i<self.featureType.length; i++) {
				if (!self.isGeomType(self.featureType[i].type) && self.featureType[i].name != 'id') {
					var field = $('#' + self.featureType[i].name)[0];
					if(field != null && field.id != null){
						if (self.featureType[i].type == 'boolean') {
							properties[field.id] = field.checked;
						}
						else if (self.isStringType(self.featureType[i].type)) {
							if (field.value != null) {
								properties[field.id] = field.value;	
							}
						} else if (field && field.value != '' && field.value != null && field.value != 'null') {
								properties[field.id] = field.value;
						}
					}
				}
				if(self.featureType[i].name == 'modified_by'){
					properties['modified_by'] = self.layerTree.conf.user.credentials.username;
				}
				if(self.featureType[i].name == 'last_modification'){
					var today = new Date();
					var dd = today.getDate();
					var mm = today.getMonth()+1; //January is 0!

					var yyyy = today.getFullYear();
					if(dd<10){
					    dd='0'+dd;
					} 
					if(mm<10){
					    mm='0'+mm;
					} 
					properties['last_modification'] = yyyy+'-'+mm+'-'+dd;
				}
			}

			feature.setProperties(properties);
			var transaction = self.transactWFS('insert', feature);
			if (transaction.success) {
				self.lastAddedFeature = null;
				if (self.resourceManager.getEngine() == 'gvsigol') {
					if (uploader.getFileCount() >= 1) {
						$("body").overlay();
						uploader.appendExtraParams({
							layer_name: self.selectedLayer.layer_name,
							workspace: self.selectedLayer.workspace,
							fid: transaction.fid
						});
						uploader.startUpload();
					}
					
				} else if (self.resourceManager.getEngine() == 'alfresco'){
					self.resourceManager.saveResource(transaction.fid);
				}
				self.selectedLayer.getSource().updateParams({"time": Date.now()});
				self.showLayersTab();
			}		
			}
		});
		
		$('#save-feature-cancel').on('click', function () {
			self.source.removeFeature(feature);
			self.lastAddedFeature = null;
			self.showLayersTab();
		});
	}

};



editionBar.prototype.showAllErrorMessages = function() {
	var form = $(".feature-div");
	$('#edition-error').empty();
	var ui = '';
	ui += '<div class="alert alert-danger alert-dismissible">';
	ui += 	'<button type="button" class="close" data-dismiss="alert" aria-hidden="true">×</button>';
	ui +=   '<h4><i class="icon fa fa-ban"></i> Error!</h4>';
	ui +=   gettext('Failed to save the new record. Please check values');
	
	var invalidFields = form.find(":invalid").each(function(index, node) {
		var label = $( "#" + node.id).parent().find("span.edit-feature-field").first(),
		// Opera incorrectly does not fill the validationMessage property.
		message = node.validationMessage || 'Invalid value.';
		ui +=    "<li><span>" + label.html() + "</span> - " + message + "</li>" ;
	});
	
	ui += '</div>';
	if(!(!invalidFields || invalidFields.length <= 0)){
		$('#edition-error').append(ui);
	}
	
	return (!invalidFields || invalidFields.length <= 0);
};


editionBar.prototype.createAllErrors = function() {
	var self = this;
	var form = $(".feature-div");
	var errorList = $("ul.errorMessages", form );

//	// Support Safari
//	form.on( "submit", function( event ) {
//		if ( this.checkValidity && !this.checkValidity() ) {
//			$( this ).find( ":invalid" ).first().focus();
//			event.preventDefault();
//		}
//	});
//	$( "#edit-feature", form ).on( "click", showAllErrorMessages);
	$( "input", form ).on( "keypress", function( event ) {
		var type = $( this ).attr( "type" );
		if ( /date|email|month|number|search|tel|text|time|url|week/.test ( type ) && event.keyCode == 13 ) {
			self.showAllErrorMessages();
		}
	});
};

/**
 * @param {Event} e Browser event.
 */
editionBar.prototype.editFeatureForm = function(feature) {	
	if (feature) {
		this.backupFeature(feature);
		this.showDetailsTab();
		this.detailsTab.empty();	
		var self = this;
		
		var featureProperties = '';
		featureProperties += '<div class="box">';
		featureProperties += 	'<div class="feature-div box-body no-padding">';
		
		var fields = this.selectedLayer.conf.fields;
		for (var i=0; i<this.featureType.length; i++) {
			if (!this.isGeomType(this.featureType[i].type) && this.featureType[i].name != 'id') {
				var name = '<span class="edit-feature-field">' + this.featureType[i].name+'</span>';
				var visible = true;
				if(fields){
					for(var ix =0; ix<fields.length; ix++){
						if(fields[ix].name.toLowerCase() == this.featureType[i].name){
							var lang = $("#select-language").val();
							if(fields[ix]["title-"+lang] && fields[ix]["title-"+lang] != ""){
								name = '<span class="edit-feature-field">' + fields[ix]["title-"+lang] + '</span><br /><span style="font-weight: normal;">('+name+')</span>';
							}
							if(fields[ix].editable != undefined){
								visible = fields[ix].editable;
							}
						}
					}
				}
				if(visible){
					var value = feature.getProperties()[this.featureType[i].name];
					featureProperties += '<div class="col-md-12 form-group" style="background-color: #fff;">';
					featureProperties += 	'<label style="color: #444;">' + name + '</label>';
					if (this.isNumericType(this.featureType[i].type)) {
						if (value==null) {
							value = "";
						}
						var numeric_conf = this.getNumericProperties(this.featureType[i]);
						featureProperties += '<input id="' + this.featureType[i].name + '" type="number" '+ numeric_conf +' class="form-control" value="' + value + '">';
					} else if (this.isDateType(this.featureType[i].type)) {
						if (value != null) {
							if (value.charAt(value.length - 1) == 'Z') {
								value = value.slice(0,-1);
							}
						} else {
							value = "";
						}
						featureProperties += '<input id="' + this.featureType[i].name + '" data-provide="datepicker" class="form-control" data-date-format="yyyy-mm-dd" value="' + value + '">';
						
					} else if (this.isStringType(this.featureType[i].type)) {				
						if (this.featureType[i].name.startsWith("enm_")) {
							var enumeration = this.getEnumeration(this.featureType[i].name);
							featureProperties += 	'<select id="' + this.featureType[i].name + '" class="form-control">';
							for (var j=0; j<enumeration.items.length; j++) {
								if (enumeration.items[j].name == value) {
									featureProperties += '<option selected value="' + enumeration.items[j].name + '">' + enumeration.items[j].name + '</option>';
								} else {
									featureProperties += '<option value="' + enumeration.items[j].name + '">' + enumeration.items[j].name + '</option>';
								}
							}
							featureProperties += 	'</select>';
						} else {
							if (value==null) {
								value = "";
							}
							if("length" in this.featureType[i] && this.featureType[i].length>0){
								featureProperties += '<input id="' + this.featureType[i].name + '" type="text" class="form-control" maxlength="'+this.featureType[i].length+'" value="' + value + '">'; 
							}else{
								featureProperties += '<input id="' + this.featureType[i].name + '" type="text" class="form-control" value="' + value + '">';
							}
						}
						
					}  else if (this.featureType[i].type == 'boolean') {
						if (value) {
							featureProperties += '<input id="' + this.featureType[i].name + '" type="checkbox" class="checkbox" checked>';
						} else {
							featureProperties += '<input id="' + this.featureType[i].name + '" type="checkbox" class="checkbox">';
						}				
					}
					featureProperties += '</div>';
				}
			}
		}
		featureProperties +=		'<div class="col-md-12 form-group" id="edition-error">';
		
		featureProperties +=      '</div>';
		featureProperties += 	'</div>';
		featureProperties += 	'<div class="box-footer text-right">';
		featureProperties += 		'<button id="edit-feature" class="btn btn-default margin-r-5">' + gettext('Save') + '</button>';
		featureProperties += 		'<button id="edit-feature-cancel" class="btn btn-default">' + gettext('Cancel') + '</button>';
		featureProperties += 	'</div>';
		featureProperties += '</div>';	
		
		var ui = '';
		ui += '<div class="nav-tabs-custom">';
		ui += 	'<ul class="nav nav-tabs">';
		ui += 		'<li class="active"><a href="#edit_feature_properties" data-toggle="tab" aria-expanded="true" style="font-weight: bold;">' + gettext('Feature properties') + '</a></li>';
		ui += 		'<li class=""><a href="#edit_feature_resources" data-toggle="tab" aria-expanded="false" style="font-weight: bold;">' + gettext('Feature resources') + '</a></li>';
		ui += 	'</ul>';
		ui += 	'<div class="tab-content">';
		ui += 		'<div class="tab-pane active" id="edit_feature_properties">';
		ui += 			featureProperties
		ui += 		'</div>';
		ui += 		'<div class="tab-pane" id="edit_feature_resources">';
		ui += 			this.resourceManager.getUI(feature);
		ui += 		'</div>';
		ui += 	'</div>';
		ui += '</div>';
		
		this.detailsTab.append(ui);
		$.gvsigOL.controlSidebar.open();
		this.resourceManager.registerEvents();

		var uploader = null;
		if (this.resourceManager.getEngine() == 'gvsigol') {
			this.resourceManager.loadResources(feature);
			uploader = this.resourceManager.createUploader();
		}
		
		$('#edit_feature_properties .form-control').on('blur', function (evt) {
			var props = feature.getProperties();
			props[evt.currentTarget.id] = evt.currentTarget.value;
			feature.setProperties(props);
		});
		$('#edit_feature_properties .checkbox').on('blur', function (evt) {
			var props = feature.getProperties();
			props[evt.currentTarget.id] = evt.currentTarget.checked;
			feature.setProperties(props);
		});
		
		


		$(".feature-div").each(self.createAllErrors);
	
		
		$('#edit-feature').on('click', function () {
			if(self.showAllErrorMessages()){
			var properties = {};
			for (var i=0; i<self.featureType.length; i++) {
				if (!self.isGeomType(self.featureType[i].type) && self.featureType[i].name != 'id') {
					var field = $('#' + self.featureType[i].name)[0];
					if(field != null && field.id != null){
						if (self.featureType[i].type == 'boolean') {
							properties[field.id] = field.checked;
						}
						else if (self.isStringType(self.featureType[i].type)) {
							if (field.value != null) {
								properties[field.id] = field.value;	
							}
						} else if (field && field.value != '' && field.value != null && field.value != 'null') {
								properties[field.id] = field.value;
						}
					}
				}
				if(self.featureType[i].name == 'modified_by'){
					properties['modified_by'] = self.layerTree.conf.user.credentials.username;
				}
				if(self.featureType[i].name == 'last_modification'){
					var today = new Date();
					var dd = today.getDate();
					var mm = today.getMonth()+1; //January is 0!

					var yyyy = today.getFullYear();
					if(dd<10){
					    dd='0'+dd;
					} 
					if(mm<10){
					    mm='0'+mm;
					} 
					properties['last_modification'] = yyyy+'-'+mm+'-'+dd;
				}
			}

			feature.setProperties(properties);
			var transaction = self.transactWFS('update', feature);
			if (transaction.success) {
				if (self.resourceManager.getEngine() == 'gvsigol') {
					if (uploader.getFileCount() >= 1) {
						$("body").overlay();
						uploader.appendExtraParams({
							layer_name: self.selectedLayer.layer_name,
							workspace: self.selectedLayer.workspace,
							fid: transaction.fid
						});
						uploader.startUpload();
					}
					
				} else if (self.resourceManager.getEngine() == 'alfresco'){
					self.resourceManager.updateResource(transaction.fid);
				}
				self.selectedLayer.getSource().updateParams({"time": Date.now()});
				self.clearFeatureBackup();
				self.selectInteraction.getFeatures().clear();
				self.showLayersTab();
			}		
			}
		});
		
		$('#edit-feature-cancel').on('click', function () {
			self.revertEditedFeature();
			self.selectInteraction.getFeatures().clear();
			self.showLayersTab();
		});
	}

};

editionBar.prototype.backupFeature = function(feature) {
	this.lastEditedFeature = feature;
	if (!feature.gol_values_orig_) {
		feature.gol_values_orig_ = feature.getProperties();
	}
	if (!feature.gol_geom_orig_) {
		feature.gol_geom_orig_ = feature.getGeometry().clone();
	}
}

editionBar.prototype.clearFeatureBackup = function() {
	if (this.lastEditedFeature!=null) {
		if (this.lastEditedFeature.gol_values_orig_) {
			delete this.lastEditedFeature.gol_values_orig_;
		}
		if (this.lastEditedFeature.gol_geom_orig_) {
			delete this.lastEditedFeature.gol_geom_orig_;
		}
		this.lastEditedFeature = null;
	}
}

editionBar.prototype.revertEditedFeature = function() {
	if (this.lastEditedFeature!=null) {
		if (this.lastEditedFeature.gol_values_orig_) {
			this.lastEditedFeature.setProperties(this.lastEditedFeature.gol_values_orig_);
			delete this.lastEditedFeature.gol_values_orig_;
		}
		if (this.lastEditedFeature.gol_geom_orig_) {
			this.lastEditedFeature.setGeometry(this.lastEditedFeature.gol_geom_orig_);
			delete this.lastEditedFeature.gol_geom_orig_;
		}
		this.lastEditedFeature = null;
	}
}


/**
 * @param {Event} e Browser event.
 */
editionBar.prototype.removeFeatureForm = function(evt, feature) {	
	
	if (feature) {
		this.showDetailsTab();
		
		this.detailsTab.empty();	
		var self = this;
		
		var ui = '';
		ui += '<div class="box">';
		ui += 		'<div class="box-header with-border">';
		ui += 			'<h3 class="box-title">' + gettext('Remove feature') + '</h3>';
		ui += 			'<div class="box-tools pull-right">';
		//ui += 				'<button type="button" class="btn btn-box-tool" data-widget="remove"><i class="fa fa-times"></i></button>';
		ui += 			'</div>';
		ui += 		'</div>';
		ui += 		'<div class="box-body no-padding">';
		for (var i=0; i<this.featureType.length; i++) {
			if (!this.isGeomType(this.featureType[i].type) && this.featureType[i].name != 'id') {
				ui += '<div class="col-md-12 form-group" style="background-color: #fff;">';
				ui += 	'<label style="color: #444;">' + this.featureType[i].name + '</label>';
				if (this.isNumericType(this.featureType[i].type)) {
					var numeric_conf = this.getNumericProperties(this.featureType[i]);
					ui += '<input disabled id="' + this.featureType[i].name + '" type="number" '+ numeric_conf+' class="form-control" value="' + feature.getProperties()[this.featureType[i].name] + '">';
					
				} else if (this.isDateType(this.featureType[i].type)) {
					var dbDate = feature.getProperties()[this.featureType[i].name];
					if (dbDate != null) {
						if (dbDate.charAt(dbDate.length - 1) == 'Z') {
							dbDate = dbDate.slice(0,-1);
						}
					} else {
						ui += '<input disabled id="' + this.featureType[i].name + '" data-provide="datepicker" class="form-control" data-date-format="yyyy-mm-dd" value="">';
					}
					
					
				} else if (this.isStringType(this.featureType[i].type)) {
					ui += '<input disabled id="' + this.featureType[i].name + '" type="text" class="form-control" value="' + feature.getProperties()[this.featureType[i].name] + '">';
				} else if (this.featureType[i].type == 'boolean') {
					if (feature.getProperties()[this.featureType[i].name]) {
						ui += '<input disabled id="' + this.featureType[i].name + '" type="checkbox" class="checkbox" checked>';
					} else {
						ui += '<input disabled id="' + this.featureType[i].name + '" type="checkbox" class="checkbox">';
					}				
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
			var transaction = self.transactWFS('delete', feature);
			if (transaction.success) {
				var deleted = self.resourceManager.deleteResources(feature);
				if (deleted) {
					self.wfsLayer.getSource().removeFeature(feature);
					self.removeInteraction.getFeatures().clear();
					self.selectedLayer.getSource().updateParams({"time": Date.now()});
					self.showLayersTab();
				}
			}		
		});
		
		$('#save-feature-cancel').on('click', function () {
			self.removeInteraction.getFeatures().clear();
			self.showLayersTab();
		});
	
	}

};


/**
 * @param {Event} e Browser event.
 */
editionBar.prototype.transactWFS = function(p,f) {
	var self = this;
	var success = false;
	var fid = null;
	var node;

	switch(p) {
		case 'delete':
			node = this.formatWFS.writeTransaction(null,null,[f],this.formatGML);
			break;
		case 'insert':
			node = this.formatWFS.writeTransaction([f],null,null,this.formatGML);
			break;
		case 'update':
			node = this.formatWFS.writeTransaction(null,[f],null,this.formatGML);
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
			if (resp.insertIds[0] == 'none') {
				fid = f.getId().split('.')[1];
			} else {
				f.setId(resp.insertIds[0]);
				fid = resp.insertIds[0].split('.')[1];
			}
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
				} catch (e) {
					// ignore errors
					console.error(e);
				}
			}
			
		} catch (err) {
			$('#edition-error').empty();
			var ui = '';
			ui += '<div class="alert alert-danger alert-dismissible">';
			ui += 	'<button type="button" class="close" data-dismiss="alert" aria-hidden="true">×</button>';
			ui +=   '<h4><i class="icon fa fa-ban"></i> Error!</h4>';
			ui +=   gettext('Failed to save the new record. Please check values');
			ui += '</div>';
			$('#edition-error').append(ui);
			success = false;
		}
		
	});
	
	return {
		success: success,
		fid: fid
	};
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
editionBar.prototype.removeLayerLock = function() {
	var self = this;
	$.ajax({
		type: 'POST',
		async: true,
	  	url: '/gvsigonline/services/remove_layer_lock/',
	  	data: {
		  	workspace: self.selectedLayer.workspace,
		  	layer: self.selectedLayer.layer_name
		},
	  	beforeSend:function(xhr){
	    	xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
	  	},
	  	success	:function(response){},
	  	error: function(){
	  		messageBox.show('error', gettext('Failed to remove layer lock'));
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