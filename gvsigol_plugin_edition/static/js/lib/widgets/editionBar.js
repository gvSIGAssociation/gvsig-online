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
var EditionBar = function(layerTree, map, featureType, selectedLayer) {
	$("#jqueryEasyOverlayDiv").css("opacity", "0.5");
	$("#jqueryEasyOverlayDiv").css("display", "block");

	var this_ = this;
	this.click_callback = function(evt) {
		$("#jqueryEasyOverlayDiv").css("opacity", "0.5");
		$("#jqueryEasyOverlayDiv").css("display", "block");
		//var feature = map.forEachFeatureAtPixel(evt.pixel, function(feature, layer) {
	    //    return feature;
	    //});
	    //if(!feature){
	    	this_.selectInteraction.changed();
	    //}
	};
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
				EditionBar: this_,
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
						this.EditionBar.stopEditionHandler();
						$("#jqueryEasyOverlayDiv").css("display", "none");
						messageBox.show('error', gettext('Error starting edition'));
					}
				},
				error: function(jqXHR, textStatus) {
					this.EditionBar.stopEditionHandler();
					$("#jqueryEasyOverlayDiv").css("display", "none");
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
				radius: 10,
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
		$("#jqueryEasyOverlayDiv").css("display", "none");
	});

	var controls = this.map.getControls();
	for(var i=0; i<controls.array_.length; i++){
		var control = controls.array_[i];
		if('options' in control){
			if('eventType' in control.options /*&& 'id' in control.options*/){
				var eventType = control.options['eventType'];
				//var id = control.options['id'];
				if(/*id == 'geocoding-contextmenu' && */eventType == "contextmenu"){
					$(".ol-ctx-menu-container > ul > .geocoding-contextmenu").remove();
					this.contextmenu = control;
					this.map.removeControl(this.contextmenu);
				}
			}
		}
	}
	$("#modify-control").trigger('click');
};

/**
 * TODO
 */
EditionBar.prototype.drawInCenterInteraction = null;

/**
 * TODO
 */
EditionBar.prototype.drawInteraction = null;

/**
 * TODO
 */
EditionBar.prototype.modifyInteraction = null;

/**
 * TODO
 */
EditionBar.prototype.selectInteraction = null;

/**
 * TODO
 */
EditionBar.prototype.removeInteraction = null;



/**
 * @param {Event} e Browser event.
 */
EditionBar.prototype.getSelectedLayer = function(e) {
	return this.selectedLayer;
};

/**
 * @param {Event} e Browser event.
 */
EditionBar.prototype.drawPointInCenterHandler = function(e) {
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
EditionBar.prototype.drawPointHandler = function(e) {
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
EditionBar.prototype.drawLineHandler = function(e) {
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
EditionBar.prototype.drawPolygonHandler = function(e) {
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
EditionBar.prototype.modifyHandler = function(e) {
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
EditionBar.prototype.removeHandler = function(e) {
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

EditionBar.prototype.stopEdition = function() {
	$("#center-cursor").hide();
	this.deactivateControls();
	this.removeVectorLayer();
	$('#editionbar').remove();
	this.removeLayerLock();
	this.layerTree.editionBar = null;
	delete this.layerTree.editionBar;
	if(this.contextmenu){
		this.map.addControl(this.contextmenu);
	}
	this.showLayersTab();

}

EditionBar.prototype.stopEditionHandler = function(e) {
	var self = this;
	var is_in_edition= false;
	if (e!=null) {
		e.preventDefault();
	}

	var selectedTab = $(".nav-tabs li.active").children("a");
	if(selectedTab){
		var href = selectedTab.prop("href");
		var href_parts = href.split("#");
		if(href_parts.length > 1){
			if(href_parts[1] == 'details-tab'){
				is_in_edition = true;
				$('#modal-end-edition').modal('show');

				$('#button-end-edition-accept').unbind("click").click(function() {
					$('#modal-end-edition').modal('hide');
					self.stopEdition();
				});
				$('#button-end-edition-cancel').unbind("click").click(function() {
					$('#modal-end-edition').modal('hide');
//					alert("Guardo");
//					$('save-feature').trigger('click');
//					$('edit-feature').trigger('click');
//					self.stopEdition();
				});
			}
		}
	}
	if(!is_in_edition){
		self.stopEdition();
	}
};

/**
 * TODO
 */
EditionBar.prototype.addDrawInteraction = function() {

	var self = this;

	this.drawInteraction = new ol.interaction.Draw({
		source: this.source,
		type: (this.geometryType),
		geometryName: this.geometryName,
		style: new ol.style.Style({
	        image:
		        new ol.style.Circle({
		            fill: new ol.style.Fill({
		                color: '#0099ff'
		            }),
		            stroke: new ol.style.Stroke({
			            color: 'white',
			            width: 2
			        }),
		            radius: 10,
		        }),
		        stroke: new ol.style.Stroke({
		            color: '#0099ff',
		            width: 5
		        })
		    })
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

EditionBar.prototype.addDrawInCenterInteraction = function() {

	var self = this;

	this.drawInCenterInteraction = new ol.interaction.Draw({
		source: this.source,
		type: (this.geometryType),
		geometryName: this.geometryName,
		style: new ol.style.Style({
	        image:
		        new ol.style.Circle({
		            fill: new ol.style.Fill({
		                color: '#0099ff'
		            }),
		            stroke: new ol.style.Stroke({
			            color: 'white',
			            width: 2
			        }),
		            radius: 10,
		        }),
		        stroke: new ol.style.Stroke({
		            color: '#0099ff',
		            width: 5
		        })
		    })
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



EditionBar.prototype.showInfo = function(layer, features){

	var self = this;
	this.popup = new ol.Overlay.Popup();
	this.map.addOverlay(this.popup);

	var html = '<ul class="products-list product-list-in-box">';

	var srs = $("#custom-mouse-position-projection").val();
	var unit =  $('#custom-mouse-position-projection option:selected').attr('data-attr');

	var wgs84 = ol.proj.transform(evt.mapBrowserEvent.coordinate, 'EPSG:3857', srs)

	var coord_1 = wgs84[1].toFixed(5).replace(/0{0,2}$/, "");
	var coord_2 = wgs84[0].toFixed(5).replace(/0{0,2}$/, "");

	if(unit == "degrees"){
		if(wgs84[1]<0){
			coord_1 = Math.abs(wgs84[1]).toFixed(5).replace(/0{0,2}$/, "") + "S";
		}else{
			coord_1 = wgs84[1].toFixed(5).replace(/0{0,2}$/, "") + "N";
		}

		if(wgs84[0]<0){
			coord_2 = Math.abs(wgs84[0]).toFixed(5).replace(/0{0,2}$/, "") + "W";
		}else{
			coord_2 = wgs84[0].toFixed(5).replace(/0{0,2}$/, "") + "E";
		}

		var aux = coord_2;
		coord_2 = coord_1;
		coord_1 = aux;
	}
	html += '<li class="item">';
	html += 	'<div class="feature-info">';
	html += 		'<span style="font-size: 12px;">' + gettext('Coordinates') + ' ('+srs+'):</span>' + '<br /><span style="font-weight: bold; font-size: 12px;"> ' + coord_2 + ', '+ coord_1 + '</span>';
	html += 	'</div>';
	html += '</li>';

	for (var i in features) {

			var fid = features[i].id;
			var is_first_configured = true;
			var item_shown = false;
			var selectedLayer = layer;

			var feature_id = "<span style=\"font-weight:bold; color:#0b6bd1; margin:0px 5px;\">"+selectedLayer.title +"."+features[i].id + "</span>";
			feature_id += 		'<div class="feature-buttons" style="margin-right:-10px;"><span class="label feature-info-button feature-info-label-info " title="'+gettext('More element info')+'"><i class="fa fa-list-ul" aria-hidden="true"></i></span></div><br />';
			feature_id += "<br />";

			var language = $("#select-language").val();
			if (selectedLayer != null) {
				if (selectedLayer.conf != null) {
					var fields_trans = selectedLayer.conf;
					if(fields_trans["fields"]){
						var fields = fields_trans["fields"];
						var feature_id2 = "<span style=\"font-weight:bold; color:#0b6bd1; margin:0px 5px;\">"+selectedLayer.title + "</span>";
						feature_id2 += 		'<div class="feature-buttons" style="margin-right:-10px;"><span class="label feature-info-button feature-info-label-info " title="'+gettext("Detalles de atributos")+'"><i class="fa fa-list-ul" aria-hidden="true"></i></span></div><div style=\"clear:both; margin-bottom:10px;\"></div>';

						var feature_added = 0;

						var feature_fields = "";
						var feature_fields2 = "";
						for(var ix=0; ix<fields.length; ix++){
							if(fields[ix]["infovisible"] != null){
								item_shown = fields[ix]["infovisible"];
								if(item_shown){
									feature_added ++;
								}
							}
							var key = fields[ix]["name"];
							var key_trans = fields[ix]["title-"+language];
							if(key_trans.length == 0){
								key_trans = key;
							}
							if(item_shown && key && features[i].getProperties() && (typeof features[i].getProperties()[key] == 'boolean' || features[i].getProperties()[key])){
								var text = features[i].getProperties()[key];

								if(typeof features[i].getProperties()[key] == 'boolean' && text == true){
									text = "<input type='checkbox' checked onclick=\"return false;\">";
								}else{
									if(typeof features[i].getProperties()[key] == 'boolean' && text == false){
										text = "<input type='checkbox' onclick=\"return false;\">";
									}
								}

								var complex_data = false;
								if(key.startsWith("cd_json_")){
									try{
										complex_data = true;
										var data_json = JSON.parse(text);
										for(nkey in data_json){
											var aux_text = data_json[nkey];
											if(aux_text.length > 45){
												aux_text = aux_text.substring(0,45) + "...";
											}
											if (!aux_text.toString().startsWith('http')) {
												feature_fields += "<span  style=\"font-weight:normal;\">" + nkey + "</span><span class=\"pull-right\">"+ aux_text + "</span><div style=\"clear:both\"></div>";
												feature_fields2 += "<span  style=\"font-weight:normal;\">" + nkey + "</span><span class=\"pull-right\">"+ aux_text + "</span><div style=\"clear:both\"></div>";
											} else {
												feature_fields += "<span  style=\"font-weight:normal;\">" + nkey + "</span><span class=\"pull-right\"><a href=\"" + data_json[nkey] + "\" style=\"color: #00c0ef !important;\" target=\"_blank\" class=\"product-description\">"+ aux_text + "</a></span><div style=\"clear:both\"></div>";
												feature_fields2 += "<span  style=\"font-weight:normal;\">" + nkey + "</span><span class=\"pull-right\"><a href=\"" + data_json[nkey] + "\" style=\"color: #00c0ef !important;\" target=\"_blank\" class=\"product-description\">"+ aux_text + "</a></span><div style=\"clear:both\"></div>";
											}
										}
									}catch(err){
										complex_data = false;
									}
								}

								if(!complex_data){
									var aux_text = text;
									var datetime_format = /^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(.[0-9]{3})?Z$/i;
									if(datetime_format.test(text)){
										var match = datetime_format.exec(text);
										aux_text = match[3]+"/"+match[2]+"/"+match[1]+" "+match[4]+":"+match[5]+":"+match[6];
										if(match.length > 7){
											//aux_text += match[7];
										}
									}
									var date_format = /^([0-9]{4})-([0-9]{2})-([0-9]{2})Z$/i;
									if(date_format.test(text)){
										var match = date_format.exec(text);
										aux_text = match[3]+"/"+match[2]+"/"+match[1];
									}
									var time_format = /^([0-9]{2}):([0-9]{2}):([0-9]{2})(.[0-9]{3})?Z$/i;
									if(time_format.test(text)){
										var match = time_format.exec(text);
										aux_text = match[3]+":"+match[2]+":"+match[1];
									}
									if(text.length > 45){
										aux_text = text.substring(0,45) + "...";
									}
									if (!text.toString().startsWith('http')) {
										feature_fields += "<span>" + aux_text + "</span><div style=\"clear:both\"></div>";
										feature_fields2 += "<span  style=\"font-weight:normal;\">" + key_trans + "</span><span class=\"pull-right\">"+ aux_text + "</span><div style=\"clear:both\"></div>";
									} else {
										feature_fields += "<span><a href=\"" + text + "\" style=\"color: #00c0ef !important;\" target=\"_blank\" class=\"product-description\">" + aux_text + "</a></span><div style=\"clear:both\"></div>";
										feature_fields2 += "<span  style=\"font-weight:normal;\">" + key_trans + "</span><span class=\"pull-right\"><a href=\"" + text + "\" style=\"color: #00c0ef !important;\" target=\"_blank\" class=\"product-description\">"+ aux_text + "</a></span><div style=\"clear:both\"></div>";
									}
								}

							}
						}

						if(feature_added > 0){
							if(feature_added > 1){
								feature_id2 += feature_fields2;
							}
							else{
								feature_id2 += feature_fields;
							}
							feature_id = feature_id2;
						}

					}
				}
			}

			html += '<li class="item feature-item show_info">';
			html += 	'<div class="feature-info">';
			html += 		'<div href="javascript:void(0)" data-fid="' + fid + '" class="product-title item-fid" style="color: #444;padding: 5px;">' + feature_id + '</div>';
			html += 	'</div>';
			html += '</li>';

//			if (features[i].crs) {
//				var newFeature = new ol.Feature();
//		  		var sourceCRS = 'EPSG:' + features[i].crs.properties.name.split('::')[1];
//		  		var projection = new ol.proj.Projection({
//		    		code: sourceCRS,
//		    	});
//		    	ol.proj.addProjection(projection);
//		    	if (features[i].feature.geometry.type == 'Point') {
//		    		newFeature.setGeometry(new ol.geom.Point(features[i].feature.geometry.coordinates));
//		    	} else if (features[i].feature.geometry.type == 'MultiPoint') {
//		    		newFeature.setGeometry(new ol.geom.Point(features[i].feature.geometry.coordinates[0]));
//		    	} else if (features[i].feature.geometry.type == 'LineString' || features[i].feature.geometry.type == 'MultiLineString') {
//		    		newFeature.setGeometry(new ol.geom.MultiLineString([features[i].feature.geometry.coordinates[0]]));
//		    	} else if (features[i].feature.geometry.type == 'Polygon' || features[i].feature.geometry.type == 'MultiPolygon') {
//		    		newFeature.setGeometry(new ol.geom.MultiPolygon(features[i].feature.geometry.coordinates));
//		    	}
//		    	newFeature.setProperties(features[i].feature.properties);
//				newFeature.setId(fid);
//
//				newFeature.getGeometry().transform(projection, 'EPSG:3857');
//				this.source.addFeature(newFeature);
//			}

	}
	html += '</ul>';
	this.popup.show(evt.mapBrowserEvent.coordinate, '<div class="popup-wrapper getfeatureinfo-popup">' + html + '</div>');
	$(".getfeatureinfo-popup").parent().parent().children(".ol-popup-closer").unbind("click").click(function() {
	 	return false;
	});

	self.map.getView().setCenter(evt.mapBrowserEvent.coordinate);
	$('.item-fid .feature-info-label-info').click(function(){
		console.log("self.showMoreInfo("+this.parentNode.parentNode.dataset.fid+", features, 'features');");
		var feat_aux = null;
		for(var i=0; i<features.length; i++){
			if(features[i].id == this.parentNode.parentNode.dataset.fid){
				feat_aux = features[i];
			}
		}
		if(feat_aux){
			self.editFeatureForm(feat_aux);
		}
	});


	$.overlayout();
	$("#jqueryEasyOverlayDiv").css("display", "none");
};


/**
 * TODO
 */
EditionBar.prototype.addModifyInteraction = function() {

	var self = this;

	//this.map.un('click', this.click_callback);
	this.map.on('click', this.click_callback);

	this.selectInteraction = new ol.interaction.Select({
		wrapX: false,
		hitTolerance: 20,
		condition: ol.events.condition.click,
		style: new ol.style.Style({
	        image:
		        new ol.style.Circle({
		            fill: new ol.style.Fill({
		                color: '#FDF709'
		            }),
		            stroke: new ol.style.Stroke({
			            color: 'white',
			            width: 2
			        }),
		            radius: 10,
		        }),
		        stroke: new ol.style.Stroke({
		            color: '#FDF709',
		            width: 5
		        })
		    })
	});

	this.modifyInteraction = new ol.interaction.Modify({
		features: this.selectInteraction.getFeatures(),
		style: new ol.style.Style({
	        image:
		        new ol.style.Circle({
		            fill: new ol.style.Fill({
		                color: '#FDF709'
		            }),
		            stroke: new ol.style.Stroke({
			            color: 'white',
			            width: 2
			        }),
		            radius: 10,
		        }),
		        stroke: new ol.style.Stroke({
		            color: '#0099ff',
		            width: 5
		        })
		    })
	});

	this.map.addInteraction(this.selectInteraction);
	this.map.addInteraction(this.modifyInteraction);

	this.selectInteraction.on('select',
			function(evt) {
				if (self.lastEditedFeature != null) {
					self.revertEditedFeature();
				}

				self.showInfo(self.selectedLayer, evt.selected)
				//self.editFeatureForm(evt.selected[0]);
				$("#jqueryEasyOverlayDiv").css("display", "none");
			}, this);

	this.selectInteraction.on('change',
			function(evt) {
				$("#jqueryEasyOverlayDiv").css("display", "none");
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
EditionBar.prototype.addRemoveInteraction = function() {

	var self = this;

	this.removeInteraction = new ol.interaction.Select({
		wrapX: false,
		style: new ol.style.Style({
	        image:
		        new ol.style.Circle({
		            fill: new ol.style.Fill({
		                color: '#FDF709'
		            }),
		            stroke: new ol.style.Stroke({
			            color: 'white',
			            width: 2
			        }),
		            radius: 10,
		        }),
		        stroke: new ol.style.Stroke({
		            color: '#FDF709',
		            width: 5
		        })
		    })
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
EditionBar.prototype.deactivateControls = function() {
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
		this.map.un('click', this.click_callback);
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
EditionBar.prototype.removeVectorLayer = function() {
	this.source.clear();
	this.map.removeLayer(this.wfsLayer);

};


/**
 * @param {Event} e Browser event.
 */
EditionBar.prototype.getEnumeration = function(enumName) {
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

EditionBar.prototype.getEnumerations = function(enumNames) {
	var enumerations = [];
	$.ajax({
		type: 'POST',
		async: false,
	  	url: "/gvsigonline/services/get_enumeration/",
	  	data: {
	  		'enum_names': enumNames.toString()
		},
	  	success	:function(response){
	  		var enms = response.enumerations;
	  		for(var i=0; i<enms.length; i++){
	  			var enm = enms[i];
		  		var enumeration = {};
		  		enumeration.title = enm.title;
		  		enumeration.name = enm.name;
		  		enumeration.items = enm.items;
		  		enumerations.push(enumeration);
	  		}
		},
	  	error: function(){}
	});

	return enumerations;
};


EditionBar.prototype.isNumericType = function(type){
	if(type == 'smallint' || type == 'integer' || type == 'bigint' || type == 'decimal' || type == 'numeric' ||
			type == 'real' || type == 'double precision' || type == 'smallserial' || type == 'serial' || type == 'bigserial' ){
		return true;
	}
	return false;
}


EditionBar.prototype.getNumericProperties = function(featureType){
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


EditionBar.prototype.getFeatureTypeDefinition = function(name){
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


EditionBar.prototype.isStringType = function(type){
	if(type == 'character varying' || type == 'varchar' || type == 'character' || type == 'char' || type == 'text' ){
		return true;
	}
	return false;
}

EditionBar.prototype.isDateType = function(type){
	if(type == 'date' || type.startsWith('timestamp ') || type.startsWith('time ') || type == 'interval'){
		return true;
	}
	return false;
}


EditionBar.prototype.getDateProperties = function(featureType){
	var type = featureType.type;

	if(type == 'date'){
		return 'DD-MM-YYYY';
	}

	if(type.startsWith('timestamp ')){
		return 'DD-MM-YYYY HH:mm:ss';
	}

	if(type.startsWith('time ')){
		return 'HH:mm:ss';
	}
}

EditionBar.prototype.isGeomType = function(type){
	if(type == 'POLYGON' || type == 'MULTIPOLYGON' || type == 'LINESTRING' || type == 'MULTILINESTRING' || type == 'POINT' || type == 'MULTIPOINT'){
		return true;
	}
	return false;
}



/**
 * @param {Event} e Browser event.
 */
EditionBar.prototype.createFeatureForm = function(feature) {
	if (feature) {
		this.showDetailsTab();
		this.detailsTab.empty();
		var self = this;
		var datetimearray = [];
		var enumeration_names = [];

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
						var dateformat = this.getDateProperties(this.featureType[i]);
						datetimearray.push({
							'name': this.featureType[i].name,
							'format': dateformat
						});
						featureProperties += '<div id="datetimepicker-' + this.featureType[i].name + '"><input id="' + this.featureType[i].name + '" class="form-control"/></div>';
						//featureProperties += '<input id="' + this.featureType[i].name + '" data-provide="datepicker" class="form-control" data-date-format="'+dateformat+'">';
					} else if (this.isStringType(this.featureType[i].type)) {
						if (this.featureType[i].name.startsWith("enm_") || this.featureType[i].name.startsWith("enmm_")) {
							var name = this.featureType[i].name;
							var has_multiple = false;
							if(this.featureType[i].name.startsWith("enmm_")){
								has_multiple = this.featureType[i].name.startsWith("enmm_");
								//name = name.replace("enmm_", "enm_");
								//var enumeration = this.getEnumeration(name);
								enumeration_names.push(this.featureType[i].name);
								featureProperties += '<div id="div-' + this.featureType[i].name + '" data-type="multiple"></div>';
							}else{
								//var enumeration = this.getEnumeration(name);
								enumeration_names.push(this.featureType[i].name);
								featureProperties += '<div id="div-' + this.featureType[i].name + '" data-type="single"></div>';
							}
						} else if (this.featureType[i].name.startsWith("form_")) {
							featureProperties += '<br/><a target="_blank" class="form-link form-link-open form-control" href="" data-orig="'+ this.featureType[i].name +'" data-value=""><i class="fa fa-check-square-o" aria-hidden="true"></i>&nbsp;&nbsp;' + gettext("Show form") + '</a>';
							featureProperties += '<input id="' + this.featureType[i].name + '" type="hidden" value="">';
						} else if (this.featureType[i].name.startsWith("cd_json_")) {
							featureProperties += '<textarea id="' + this.featureType[i].name + '" rows="4" class="form-control"></textarea>';
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
		ui += 		'<div class="box-footer text-right">';
		ui += 			'<button id="save-feature" class="btn btn-default margin-r-5">' + gettext('Save') + '</button>';
		ui += 			'<button id="save-feature-cancel" class="btn btn-default">' + gettext('Cancel') + '</button>';
		ui += 		'</div>';
		ui += 	'</div>';
		ui += '</div>';

		this.detailsTab.append(ui);

		var enums = this.getEnumerations(enumeration_names);
		for(var i=0; i<enums.length; i++){
			var enumeration = enums[i];

			var enum_html = '';

			if(enumeration && enumeration.items){
				var has_multiple = $("#div-"+enumeration.name).attr("data-type");
				if(has_multiple!="multiple"){
					enum_html += '<select id="' + enumeration.name + '" class="form-control">';
				}else{
					enum_html += '<select id="' + enumeration.name + '" class="form-control multipleSelect" multiple="multiple">';
				}

				for (var j=0; j<enumeration.items.length; j++) {
					enum_html += '<option value="' + enumeration.items[j].name + '">' + enumeration.items[j].name + '</option>';
				}
				enum_html += 	'</select>';
			}else{
				enum_html += '<input id="' + enumeration.name + '" type="text" class="form-control">';
			}

			$("#div-"+enumeration.name).html(enum_html);
		}


		$.gvsigOL.controlSidebar.open();
		this.resourceManager.registerEvents();

		var uploader = null;
		if (this.resourceManager.getEngine() == 'gvsigol') {
			uploader = this.resourceManager.createUploader();
		}

		for(var ixx=0; ixx < datetimearray.length; ixx++){
			$('#'+datetimearray[ixx].name).datetimepicker({
				format: datetimearray[ixx].format, //'DD-MM-YYYY HH:mm:ss',
				showClose: true
			});
		}

		$('#edit_feature_properties .form-control').on('blur', function (evt) {
			if(evt.currentTarget.value == ""){
				delete feature.values_[evt.currentTarget.id];
			}else{
				var props = feature.getProperties();
				props[evt.currentTarget.id] = evt.currentTarget.value;
				feature.setProperties(props);
			}
		});
		$('#edit_feature_properties .checkbox').on('blur', function (evt) {
			var props = feature.getProperties();
			props[evt.currentTarget.id] = evt.currentTarget.checked;
			feature.setProperties(props);
		});


		$(".feature-div").each(self.createAllErrors);

		$('.form-link-open').each(function () {
			var field_name = $(this).attr("data-orig");
			var feature_id = $(this).attr("data-value");
			var self = $(this);
			$.getJSON("/gvsigonline/forms/get_form_link/",
					{
					'field_name': field_name,
					'feature_id': feature_id
					}, function(data){
						if("token" in data && data["token"].length > 0){
							$("#"+field_name).val(data["token"]);
							self.attr("data-value", data["token"]);

						}
						if("url" in data && data["url"].length > 0){
							self.attr("href", data["url"]);
						}

			}).fail(function() {
			});
		});

		 $('.form-link-open').on('click', function () {
			 if($(this).attr("data-value") == null || $(this).attr("href") == null ||
		    		 $(this).attr("data-value") == "" || $(this).attr("href") == ""){
				 messageBox.show('warning', gettext('No hay ninguna encuesta activa para ser rellenada. Para responder encuesta, por favor activarla en Limesurvey'));
		    	 return false;
		     }
		 });

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
						else {
							if(self.isDateType(self.featureType[i].type)){
								if(field.value != ""){
									properties[field.id] = self.getDateTime(field.value);
								}
							}else{
								if (self.isStringType(self.featureType[i].type)) {
									if(self.featureType[i].name.startsWith("enmm_")){
										value = "";
										for(var ix=0; ix<field.selectedOptions.length; ix++){
											var option = field.selectedOptions[ix];
											if(ix != 0){
												value = value + ";";
											}
											value = value + option.value;
										}
										properties[field.id] = value;
									}else if(self.featureType[i].name.startsWith("form_")){
										properties[field.id] = field.value;
									}else{
										if (field.value != null) {
											properties[field.id] = field.value;
										}
									}
								} else if (field && field.value != '' && field.value != null && field.value != 'null') {
										properties[field.id] = field.value;
								}
							}
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
						$("#jqueryEasyOverlayDiv").css("opacity", "0.5");
						$("#jqueryEasyOverlayDiv").css("display", "block");
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
			var geojson_obj = new ol.format.GeoJSON();
			var stringjson = geojson_obj.writeFeature(feature);
			parent.$("body").trigger("feature-edition", stringjson);
			}
		});

		$('#save-feature-cancel').on('click', function () {
			$('.form-link-open').each(function () {
				$.getJSON("/gvsigonline/forms/delete_form_link/",
						{
						'field_name': $(this).attr("data-orig"),
						'feature_id': $(this).attr("data-value")
						}, function(data){

				}).fail(function() {
				});
			});
			self.source.removeFeature(feature);
			self.lastAddedFeature = null;
			self.showLayersTab();
		});

		$('.multipleSelect').fastselect();
	}

};



EditionBar.prototype.showAllErrorMessages = function() {
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

	var self = this;
	var nullable_error = false;
	for (var i=0; i<self.featureType.length; i++) {
		if (!self.isGeomType(self.featureType[i].type) && self.featureType[i].name != 'id') {
			var field = $('#' + self.featureType[i].name)[0];
			if(field != null && field.id != null){
				var value = null;
				if (self.featureType[i].type == 'boolean') {
					value = field.checked;
				}
				else if (self.isStringType(self.featureType[i].type)) {
					if(self.featureType[i].name.startsWith("enmm_")){
						value = "";
						for(var ix=0; ix<field.selectedOptions.length; ix++){
							var option = field.selectedOptions[ix];
							if(ix != 0){
								value = value + ";";
							}
							value = value + option.value;
						}
					}else if(self.featureType[i].name.startsWith("form_")){
						value = field.value;
					}else{
						if (field.value != null) {
							value = field.value;
						}
					}
				} else if (field && field.value != '' && field.value != null && field.value != 'null') {
						value = field.value;
				}
				if(self.featureType[i].nullable == 'NO' && (value == null || value == "")){
					nullable_error = true;
					ui  +=    "<li><span>" + self.featureType[i].name + "</span> - " + gettext("can't be null") + "</li>" ;
				}
			}
		}
	}

	ui += '</div>';
	if(!(!invalidFields || invalidFields.length <= 0) || nullable_error){
		$('#edition-error').append(ui);
		return false;
	}

	return true;
};


EditionBar.prototype.createAllErrors = function() {
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
EditionBar.prototype.getDateTime = function(time) {
	if(time == ""){
		return null;
	}
	time_array = time.split(" ");
	time_date_array = time_array[0].split("-");
	if(time_date_array.length == 3){
		time = time_date_array[2]+'-'+ time_date_array[1] +'-' +time_date_array[0];
	}
	if(time_array.length > 1){
		time = time + 'T' + time_array[1];
	}
	time=time+'Z';

	return time
}

EditionBar.prototype.modifyDateTime = function(time) {
	if(time == ""){
		return null;
	}
	time = time.replace("Z", "");
	time = time.replace("T", " ");

	time_array = time.split(" ");
	time_date_array = time_array[0].split("-");
	if(time_date_array.length == 3){
		time = time_date_array[2]+'-'+ time_date_array[1] +'-' +time_date_array[0];
	}
	if(time_array.length > 1){
		time = time + ' ' + time_array[1];
	}

	return time
}


EditionBar.prototype.editFeatureForm = function(feature) {
	if (feature) {
		this.backupFeature(feature);
		this.showDetailsTab();
		this.detailsTab.empty();
		var self = this;
		var datetimearray = [];
		var enumeration_names = [];

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
							value = this.modifyDateTime(value);
						} else {
							value = "";
						}
						var dateformat = this.getDateProperties(this.featureType[i]);
						datetimearray.push({
							'name': this.featureType[i].name,
							'format': dateformat
						});
						featureProperties += '<div id="datetimepicker-' + this.featureType[i].name + '"><input id="' + this.featureType[i].name + '" class="form-control"  value="' + value + '"/></div>';
						//featureProperties += '<input id="' + this.featureType[i].name + '" data-provide="datepicker" class="form-control" data-date-format="'+dateformat+'" value="' + value + '">';

					} else if (this.isStringType(this.featureType[i].type)) {
						if (this.featureType[i].name.startsWith("enm_") || this.featureType[i].name.startsWith("enmm_")) {
							var name = this.featureType[i].name;
							var has_multiple = false;
							if(this.featureType[i].name.startsWith("enmm_")){
								has_multiple = this.featureType[i].name.startsWith("enmm_");
								//name = name.replace("enmm_", "enm_");
								//var enumeration = this.getEnumeration(name);
								enumeration_names.push(this.featureType[i].name);
								featureProperties += '<div id="div-' + this.featureType[i].name + '" data-type="multiple" data-value="'+value+'"></div>';
							}else{
								//var enumeration = this.getEnumeration(name);
								enumeration_names.push(this.featureType[i].name);
								featureProperties += '<div id="div-' + this.featureType[i].name + '" data-type="single" data-value="'+value+'"></div>';
							}
						} else if (this.featureType[i].name.startsWith("form_")) {
							featureProperties += '<br/><a target="_blank" class="form-link form-link-open form-control" href="" data-orig="'+ this.featureType[i].name +'" data-value="' + value + '"><i class="fa fa-check-square-o" aria-hidden="true"></i>&nbsp;&nbsp;' + gettext("Show form") + '</a>';
							featureProperties += '<input id="' + this.featureType[i].name + '" type="hidden" value="' + value + '">';
						} else if (this.featureType[i].name.startsWith("cd_json_")) {
							featureProperties += '<textarea id="' + this.featureType[i].name + '" rows="4" class="form-control">' + value + '</textarea>';
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
		ui += 		'<div class="box-footer text-right">';
		ui += 			'<button id="edit-feature" class="btn btn-default margin-r-5">' + gettext('Save') + '</button>';
		ui += 			'<button id="edit-feature-cancel" class="btn btn-default">' + gettext('Cancel') + '</button>';
		ui += 		'</div>';
		ui += 	'</div>';
		ui += '</div>';

		this.detailsTab.append(ui);

		var enums = this.getEnumerations(enumeration_names);
		for(var i=0; i<enums.length; i++){
			var enumeration = enums[i];

			var enum_html = '';

			if(enumeration && enumeration.items){
				var has_multiple = $("#div-"+enumeration.name).attr("data-type");
				var enum_value = $("#div-"+enumeration.name).attr("data-value");
				if(has_multiple!="multiple"){
					enum_html += '<select id="' + enumeration.name + '" class="form-control">';
				}else{
					enum_html += '<select id="' + enumeration.name + '" class="form-control multipleSelect" multiple="multiple">';
				}
				enum_value = ";" + enum_value + ";";
				for (var j=0; j<enumeration.items.length; j++) {
					var enum_item_name = ";"+enumeration.items[j].name+";";
					if (enum_value.indexOf(enum_item_name) !== -1) {
						enum_html += '<option selected value="' + enumeration.items[j].name + '">' + enumeration.items[j].name + '</option>';
					} else {
						enum_html += '<option value="' + enumeration.items[j].name + '">' + enumeration.items[j].name + '</option>';
					}
				}
				enum_html += 	'</select>';
			}else{
				enum_html += '<input id="' + enumeration.name + '" type="text" class="form-control">';
			}
			$("#div-"+enumeration.name).html(enum_html);
		}

		$.gvsigOL.controlSidebar.open();
		this.resourceManager.registerEvents();

		var uploader = null;
		if (this.resourceManager.getEngine() == 'gvsigol') {
			this.resourceManager.loadResources(feature);
			uploader = this.resourceManager.createUploader();
		}

		$('#edit_feature_properties .form-control').on('blur', function (evt) {
			var props = feature.getProperties();
//			if(evt.currentTarget.type == "number" && evt.currentTarget.value == ""){
//				delete props[evt.currentTarget.id];
//				feature.setProperties(props);
//			}else{
				props[evt.currentTarget.id] = evt.currentTarget.value;
				feature.setProperties(props);
//			}
		});
		$('#edit_feature_properties .checkbox').on('blur', function (evt) {
			var props = feature.getProperties();
			props[evt.currentTarget.id] = evt.currentTarget.checked;
			feature.setProperties(props);
		});

		for(var ixx=0; ixx < datetimearray.length; ixx++){
			$('#'+datetimearray[ixx].name).datetimepicker({
				format: datetimearray[ixx].format, //'DD-MM-YYYY HH:mm:ss',
				showClose: true
			});
		}



		$(".feature-div").each(self.createAllErrors);

		$('.form-link-open').each(function () {
			var field_name = $(this).attr("data-orig");
			var feature_id = $(this).attr("data-value");
			var self = $(this);
			$.getJSON("/gvsigonline/forms/get_form_link/",
					{
					'field_name': field_name,
					'feature_id': feature_id
					}, function(data){
						if("token" in data && data["token"].length > 0){
							$("#"+field_name).val(data["token"]);
							self.attr("data-value", data["token"]);

						}
						if("url" in data && data["url"].length > 0){
							self.attr("href", data["url"]);
						}

			}).fail(function() {
			});
		});

		$('.form-link-open').on('click', function () {
		     if($(this).attr("data-value") == null || $(this).attr("href") == null ||
		    		 $(this).attr("data-value") == "" || $(this).attr("href") == ""){
		    	 messageBox.show('warning', gettext('No hay ninguna encuesta activa para ser rellenada. Para responder encuesta, por favor activarla en Limesurvey'));
		    	 return false;
		     }
		 });


		$('#edit-feature').on('click', function () {
			if(self.showAllErrorMessages()){
			var properties = {};
			for (var i=0; i<self.featureType.length; i++) {
				if (!self.isGeomType(self.featureType[i].type) && self.featureType[i].name != 'id') {
					var field = $('#' + self.featureType[i].name)[0];
					if(field != null && field.id != null){
						if (self.featureType[i].type == 'boolean') {
							properties[field.id] = field.checked;
						}else{
							if(self.isDateType(self.featureType[i].type)){
								if(field.value != ""){
									properties[field.id] = self.getDateTime(field.value);
								}
							}else{
								if (self.isStringType(self.featureType[i].type)) {
									if(self.featureType[i].name.startsWith("enmm_")){
										value = "";
										for(var ix=0; ix<field.selectedOptions.length; ix++){
											var option = field.selectedOptions[ix];
											if(ix != 0){
												value = value + ";";
											}
											value = value + option.value;
										}
										properties[field.id] = value;
									}else if(self.featureType[i].name.startsWith("form_")){
										properties[field.id] = field.value;
									}else{
										if (field.value != null) {
											properties[field.id] = field.value;
										}
									}
								} else if (field && field.value != '' && field.value != null && field.value != 'null') {
										properties[field.id] = field.value;
								}
							}
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
						$("#jqueryEasyOverlayDiv").css("opacity", "0.5");
						$("#jqueryEasyOverlayDiv").css("display", "block");
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

			var geojson_obj = new ol.format.GeoJSON();
			var stringjson = geojson_obj.writeFeature(feature);
			parent.$("body").trigger("feature-edition", stringjson);
			}
		});

		$('#edit-feature-cancel').on('click', function () {
			self.revertEditedFeature();
			self.selectInteraction.getFeatures().clear();
			self.showLayersTab();
		});

		$('.multipleSelect').fastselect();
	}

};


EditionBar.prototype.backupFeature = function(feature) {
	this.lastEditedFeature = feature;
	if (!feature.gol_values_orig_) {
		feature.gol_values_orig_ = feature.getProperties();
	}
	if (!feature.gol_geom_orig_) {
		feature.gol_geom_orig_ = feature.getGeometry().clone();
	}
}

EditionBar.prototype.clearFeatureBackup = function() {
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

EditionBar.prototype.revertEditedFeature = function() {
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
EditionBar.prototype.removeFeatureForm = function(evt, feature) {

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
						var dateformat = this.getDateProperties(this.featureType[i]);
						ui += '<input disabled id="' + this.featureType[i].name + '" data-provide="datepicker" class="form-control" data-date-format="'+dateformat+'" value="">';
					}


				} else if (this.isStringType(this.featureType[i].type)) {
					var value = feature.getProperties()[this.featureType[i].name];
					if (this.featureType[i].name.startsWith("form_")) {
						ui += '<br/><a target="_blank" class="form-link form-link-open form-control" href="" data-orig="'+ this.featureType[i].name +'" data-value="'+value+'"><i class="fa fa-check-square-o" aria-hidden="true"></i>&nbsp;&nbsp;' + gettext("Show form") + '</a>';
					} else{
						ui += '<input disabled id="' + this.featureType[i].name + '" type="text" class="form-control" value="' + value + '">';
					}
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

		$('.form-link-open').each(function () {
			var field_name = $(this).attr("data-orig");
			var feature_id = $(this).attr("data-value");
			var self = $(this);
			$.getJSON("/gvsigonline/forms/get_form_link/",
					{
					'field_name': field_name,
					'feature_id': feature_id
					}, function(data){
						if("token" in data && data["token"].length > 0){
							$("#"+field_name).val(data["token"]);
							self.attr("data-value", data["token"]);

						}
						if("url" in data && data["url"].length > 0){
							self.attr("href", data["url"]);
						}

			}).fail(function() {
			});
		});

		$('#remove-feature').on('click', function () {
			var transaction = self.transactWFS('delete', feature);
			if (transaction.success) {
				var deleted = self.resourceManager.deleteResources(feature);
				if (deleted) {
					$('.form-link-open').each(function () {
						$.getJSON("/gvsigonline/forms/delete_form_link/",
								{
								'field_name': $(this).attr("data-orig"),
								'feature_id': $(this).attr("data-value")
								}, function(data){

						}).fail(function() {
						});
					});
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
EditionBar.prototype.transactWFS = function(p,f) {
	var self = this;
	var success = false;
	var fid = null;
	var node;

	var feat = this.verifyGeometryField(f);

	switch(p) {
		case 'delete':
			node = this.formatWFS.writeTransaction(null,null,[feat],this.formatGML);
			break;
		case 'insert':
			node = this.formatWFS.writeTransaction([feat],null,null,this.formatGML);
			break;
		case 'update':
			node = this.formatWFS.writeTransaction(null,[feat],null,this.formatGML);
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
				fid = feat.getId().split('.')[1];
			} else {
				feat.setId(resp.insertIds[0]);
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
			if('responseXML' in request){
				var errors = $(request.responseXML).find("ExceptionText");
				var get_error = false;
				if(errors.length > 0){
					var error = errors[0].textContent;
					if(error != null || error != ""){
						ui +=   gettext(error);
						get_error = true;
					}
				}
				if(!get_error){
					ui +=   gettext('Failed to save the new record. Please check values');
				}
			}else{
				ui +=   gettext('Failed to save the new record. Please check values');
			}
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
EditionBar.prototype.updateServiceBoundingBox = function(workspace,layerName) {
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
EditionBar.prototype.removeLayerLock = function() {
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
EditionBar.prototype.showDetailsTab = function(p,f) {
	$('.nav-tabs a[href="#details-tab"]').tab('show');
};

/**
 * TODO
 */
EditionBar.prototype.showLayersTab = function(p,f) {
	this.detailsTab.empty();
	$('.nav-tabs a[href="#layer-tree-tab"]').tab('show');
};

/**
 * TODO
 */
EditionBar.prototype.verifyGeometryField = function(feature) {
	var featureTypeGeometryName = 'wkt_geometry';
	for (var i = 0; i < this.featureType.length; i++) {
		if (this.isGeomType(this.featureType[i].type)) {
			featureTypeGeometryName = this.featureType[i].name;
		}

	}

	if (feature.getGeometryName() == featureTypeGeometryName) {
		return feature;

	} else {
		var props = feature.getProperties();
		props[featureTypeGeometryName] = props[feature.getGeometryName()];
    	delete props[feature.getGeometryName()];
    	delete feature.values_[feature.getGeometryName()];
    	feature.setProperties(props);
	}
	feature.setGeometryName(featureTypeGeometryName);

	return feature;
};