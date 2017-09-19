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
var getFeatureInfo = function(map, prefix) {

	this.map = map;
	this.prefix = prefix;
	
	this.id = "get-feature-info";

	var button = document.createElement('button');
	button.setAttribute("id", this.id);
	button.setAttribute("class", "toolbar-button");
	button.setAttribute("title", gettext('Point information'));
	var icon = document.createElement('i');
	icon.setAttribute("class", "fa fa-info");
	button.appendChild(icon);
	
	this.$button = $(button);
	
	$('#toolbar').append(button);

	var this_ = this;
  
	var handler = function(e) {
		this_.handler(e);
	};

	button.addEventListener('click', handler, false);
	button.addEventListener('touchstart', handler, false);

};

/**
 * TODO
 */
getFeatureInfo.prototype.active = false;

/**
 * TODO
 */
getFeatureInfo.prototype.deactivable = true;

/**
 * TODO
 */
getFeatureInfo.prototype.resultPanelContent = null;

/**
 * TODO
 */
getFeatureInfo.prototype.source = null;

/**
 * TODO
 */
getFeatureInfo.prototype.resultLayer = null;

/**
 * TODO
 */
getFeatureInfo.prototype.mapCoordinates = null;

/**
 * TODO
 */
getFeatureInfo.prototype.popup = null;


/**
 * @param {Event} e Browser event.
 */
getFeatureInfo.prototype.handler = function(e) {
	e.preventDefault();
	if (this.active) {
		this.deactivate();
		
	} else {
		
		if (this.hasLayers()) {
			
			this.popup = new ol.Overlay.Popup();
			this.map.addOverlay(this.popup);
        	
			this.$button.addClass('button-active');
			this.active = true;
			this.$button.trigger('control-active', [this]);
	    	
	    	var self = this;

			this.map.on('click', this.clickHandler, self);		
			this.source = new ol.source.Vector();				
			this.resultLayer = new ol.layer.Vector({
				source: this.source,
			  	style: new ol.style.Style({
			    	fill: new ol.style.Fill({
			      		color: 'rgba(255, 255, 255, 0.2)'
			    	}),
			    	stroke: new ol.style.Stroke({
			      		color: '#0099ff',
			      		width: 2
			    	}),
			    	image: new ol.style.Circle({
			      		radius: 7,
			      		fill: new ol.style.Fill({
			        		color: '#0099ff'
			      		})
			    	})
			  	})
			});
			this.resultLayer.baselayer = true;
			this.map.addLayer(this.resultLayer);
			
		} else {
			messageBox.show('warning', gettext('No layers available.'));
		}
		
	}
};

/**
 * TODO
 */
getFeatureInfo.prototype.hasLayers = function() {	
	
	var hasLayers = false;
	
	var layers = this.map.getLayers().getArray();
	var queryLayers = new Array();
	for (var i=0; i<layers.length; i++) {
		if (!layers[i].baselayer) {
			if (layers[i].queryable) {
				if (layers[i].getVisible()) {
					queryLayers.push(layers[i]);
				}
			}									
		}
	}
	
	if (queryLayers.length > 0) {					
		hasLayers = true;
	}
	
	return hasLayers;
};

/**
 * Handle pointer click.
 * @param {ol.MapBrowserEvent} evt
 */
getFeatureInfo.prototype.clickHandler = function(evt) {
	
	$("body").overlay();
	$("#jqueryEasyOverlayDiv").css("opacity", "0.5");
	$("#jqueryEasyOverlayDiv").css("display", "none");
	
	this.source.clear();
	
	var self = this;
	this.showFirst = true;
	
	this.mapCoordinates = evt.coordinate;
	
	this.source.clear();
	if (this.active) {
		var layers = this.map.getLayers().getArray();
		var queryLayers = new Array();
		var url = null;
		var auxLayer = null;
		
		for (var i=0; i<layers.length; i++) {
			if (!layers[i].baselayer) {
				if (layers[i].wms_url && layers[i].getVisible()) {
					if( layers[i].isLayerGroup){
						var parent = layers[i];
						for (var j=0; j<layers.length; j++) {
							if (!layers[j].baselayer) {
								if (layers[j].wms_url) {
									if ((typeof layers[j].parentGroup === 'string' && layers[j].parentGroup == parent.layer_name) || 
											(layers[j].parentGroup != undefined && layers[j].parentGroup.groupName == parent.layer_name)){
										queryLayers.push(layers[j]);
									}
								}
							}
						}
					}else{
						queryLayers.push(layers[i]);
					}
				}						
			}
		}
		
		var viewResolution = /** @type {number} */ (this.map.getView().getResolution());
		var qLayer = null;
		var url = null;
		var ajaxRequests = new Array();
		var features = new Array();
		
		for (var i=0; i<queryLayers.length; i++) {
			qLayer = queryLayers[i];
			url = qLayer.getSource().getGetFeatureInfoUrl(
				evt.coordinate, 
				viewResolution, 
				this.map.getView().getProjection().getCode(),
				{'INFO_FORMAT': 'application/json', 'FEATURE_COUNT': '100'}
			);
			
			var req = $.ajax({
				type: 'POST',
				async: false,
			  	url: '/gvsigonline/services/get_feature_info/',
			  	data: {
			  		url: url,
			  		query_layer: qLayer.layer_name,
			  		workspace: qLayer.workspace
			  	},
			  	success	:function(response){
			  		if (response.features && response.features.length > 0) {
			  			if (response.features[0].type == 'catastro') {
			  				features.push({
			  					type: 'catastro',
			  					text: response.features[0].text,
			  					href: response.features[0].href,
			  					layer: qLayer
			  				});
			  				
			  			} else {
			  				for (var i in response.features) {
				  				features.push({
				  					type: 'feature',
				  					crs: response.crs,
				  					feature: response.features[i],
				  					layer: qLayer
				  				});
				  			}
			  			}	  			
			  		}
			  	},
			  	error: function(){}
			});
				
			ajaxRequests.push(req);
		}
		
		$.when(undefined, ajaxRequests).then(function(){ 
		     self.showInfo(features);
		});
		
	}
};

/**
 * TODO
 */
getFeatureInfo.prototype.showInfo = function(features){
	
	var self = this;

	var html = '<ul class="products-list product-list-in-box">';
	
	var wgs84 = ol.proj.transform(self.mapCoordinates, 'EPSG:3857', 'EPSG:4326')
	html += '<li class="item">';
	html += 	'<div class="feature-info">';
	html += 		'<span style="font-size: 12px;">' + gettext('Coordinates') + ':</span>' + '<br /><span style="font-weight: bold; font-size: 12px;"> ' + wgs84[0].toFixed(5).replace(/0{0,2}$/, "")+ ', '+ wgs84[1].toFixed(5).replace(/0{0,2}$/, "") + '</span>';	
	html += 	'</div>';
	html += '</li>';
	
	for (var i in features) {
		if (features[i].type == 'feature' && features[i].feature.type == 'raster') {
			var feature_id = "<span style=\"font-weight:normal; margin-right:5px;\">"+features[i].layer.title+ "</span>";
			feature_id += "<br />";
			
			for(key in features[i].feature.properties){
				feature_id += "<span  style=\"font-weight:normal;\">" + key + "</span><span class=\"pull-right\">"+ features[i].feature.properties[key] + "</span><br />";
			}
			
			html += '<li class="item feature-item" style="min-width:300px;">';
			html += 	'<div class="feature-info">';
			html += 		'<a href="javascript:void(0)" data-fid="' + fid + '" class="product-title item-fid" style="color: #444;">' + feature_id + '</a>';
			html += 	'</div>';
			html += '</li>';
		}
		else{ 
			if (features[i].type == 'feature') {
		
			var fid = features[i].feature.id;
			var is_first_configured = true;
			var item_shown = false;
			var selectedLayer = features[i].layer;
			
			var feature_id = "<span style=\"font-weight:normal; margin-right:5px;\">"+features[i].layer.title +"."+features[i].feature.feature + "</span>";
			feature_id += 		'<div class="feature-buttons"><span class="label feature-info-button feature-info-label-info " title="'+gettext('More element info')+'"><i class="fa fa-list-ul" aria-hidden="true"></i></span>';
			feature_id += 		'<span class="label feature-info-button feature-info-label-resource" title="'+gettext('Multimedia resources')+'"><i class="fa fa-picture-o" aria-hidden="true"></i></span></div><br />';
			feature_id += "<br />";
			
			var language = $("#select-language").val();
			if (selectedLayer != null) {
				if (selectedLayer.conf != null) {
					var fields_trans = selectedLayer.conf;
					if(fields_trans["fields"]){
						var fields = fields_trans["fields"];
						var feature_id2 = "<span style=\"font-weight:normal; margin-right:5px;\">"+selectedLayer.title + "</span>";
						feature_id2 += 		'<div class="feature-buttons"><span class="label feature-info-button feature-info-label-info "><i class="fa fa-list-ul" aria-hidden="true"></i></span>';
						feature_id2 += 		'<span class="label feature-info-button feature-info-label-resource"><i class="fa fa-picture-o" aria-hidden="true"></i></span></div><div style=\"clear:both\"></div>';

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
							if(item_shown && key && features[i].feature.properties && (typeof features[i].feature.properties[key] == 'boolean' || features[i].feature.properties[key])){
								var text = features[i].feature.properties[key];
								
								if(typeof features[i].feature.properties[key] == 'boolean' && text == true){
									text = "<input type='checkbox' checked onclick=\"return false;\">";
								}else{
									if(typeof features[i].feature.properties[key] == 'boolean' && text == false){
										text = "<input type='checkbox' onclick=\"return false;\">";
									}
								}
								feature_fields += "<span>" + text + "</span><br />";
								feature_fields2 += "<span  style=\"font-weight:normal;\">" + key_trans + "</span><span class=\"pull-right\">"+ text + "</span><br />";
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
			
			html += '<li class="item feature-item" style="min-width:300px;">';
			html += 	'<div class="feature-info">';
			html += 		'<a href="javascript:void(0)" data-fid="' + fid + '" class="product-title item-fid" style="color: #444;">' + feature_id + '</a>';
			html += 	'</div>';
			html += '</li>';
			
			if (features[i].crs) {
				var newFeature = new ol.Feature();
		  		var sourceCRS = 'EPSG:' + features[i].crs.properties.name.split('::')[1];
		  		var projection = new ol.proj.Projection({
		    		code: sourceCRS,
		    	});
		    	ol.proj.addProjection(projection);
		    	if (features[i].feature.geometry.type == 'Point') {
		    		newFeature.setGeometry(new ol.geom.Point(features[i].feature.geometry.coordinates));				
		    	} else if (features[i].feature.geometry.type == 'MultiPoint') {
		    		newFeature.setGeometry(new ol.geom.Point(features[i].feature.geometry.coordinates[0]));				
		    	} else if (features[i].feature.geometry.type == 'LineString' || features[i].feature.geometry.type == 'MultiLineString') {
		    		newFeature.setGeometry(new ol.geom.MultiLineString([features[i].feature.geometry.coordinates[0]]));
		    	} else if (features[i].feature.geometry.type == 'Polygon' || features[i].feature.geometry.type == 'MultiPolygon') {
		    		newFeature.setGeometry(new ol.geom.MultiPolygon(features[i].feature.geometry.coordinates));
		    	}
		    	newFeature.setProperties(features[i].feature.properties);
				newFeature.setId(fid);
						
				newFeature.getGeometry().transform(projection, 'EPSG:3857');
				this.source.addFeature(newFeature);
			}
			
		} else if (features[i].type == 'catastro') {
			html += '<li class="item">';
			html += 	'<div class="feature-info">';
			html += 		'Ref. Catastral: <a target="_blank" href="' + features[i].href + '" class="product-title item-fid" style="color: #00c0ef;">' + features[i].text;	
			html += 	'</div>';
			html += '</li>';
		}	
		}
	}	
	html += '</ul>';
	this.popup.show(self.mapCoordinates, '<div class="popup-wrapper getfeatureinfo-popup">' + html + '</div>');	
	$(".getfeatureinfo-popup").parent().parent().children(".ol-popup-closer").unbind("click").click(function() {
		var detailsTab = $('#details-tab');
	 	detailsTab.empty();
	 	$('.nav-tabs a[href="#layer-tree-tab"]').tab('show');
	 	return false;
	});
	self.map.getView().setCenter(self.mapCoordinates);
	$('.item-fid .feature-info-label-info').click(function(){
		self.showMoreInfo(this.parentNode.parentNode.dataset.fid, features, 'features');
	});
	
	$('.item-fid .feature-info-label-resource').click(function(){
		self.showMoreInfo(this.parentNode.parentNode.dataset.fid, features, 'resources');
	});

	$.overlayout();
	$("#jqueryEasyOverlayDiv").css("display", "none");
};

/**
 * TODO
 */
getFeatureInfo.prototype.showMoreInfo = function(fid, features, tab_opened){
	var selectedFeature = null;
	var selectedLayer = null;
	for (var i in features) {
		if (features[i].type == 'feature') {
			if (fid == features[i].feature.id) {
				selectedFeature = features[i].feature; 
				selectedLayer = features[i].layer;
			}
		}
	}
	
	if (selectedFeature != null && selectedLayer != null) {
		if (selectedFeature.type.toLowerCase() == 'feature') {
			var detailsTab = $('#details-tab');
			var infoContent = '';
			infoContent += '<div class="box box-default">';
			infoContent += 	'<div class="box-header with-border">';
			infoContent += 		'<span class="text">' + selectedLayer.title + '</span>';
			infoContent += 	'</div>';
			infoContent += 	'<div class="box-body" style="padding: 20px;">';
			infoContent += 		'<ul class="products-list product-list-in-box">';
			
			var language = $("#select-language").val();
			var featureType = this.describeFeatureType(selectedLayer);
			for (var i=0; i<featureType.length; i++) {
				if (!this.isGeomType(featureType[i].type)) {
				var key = featureType[i].name;
				var value = selectedFeature.properties[key];
				if (value == "null" || value == null) {
					value = "";
				}
				if(featureType[i].type == "boolean"){
					if(value == true){
						value = "<input type='checkbox' checked onclick=\"return false;\">";
					}else {
						value = "<input type='checkbox' onclick=\"return false;\">";
					}
				}
				if (!key.startsWith(this.prefix)) {	
					var item_shown = true;
					if (selectedLayer != null) {
						if (selectedLayer.conf != null) {
							var fields_trans = selectedLayer.conf;
							if(fields_trans["fields"]){
								var fields = fields_trans["fields"];
								for(var ix=0; ix<fields.length; ix++){
									if(fields[ix].name.toLowerCase() == key){
										if(fields[ix]["visible"] != null){
											item_shown = fields[ix]["visible"];
										}
										var feat_name_trans = fields[ix]["title-"+language];
										if(feat_name_trans){
											key = feat_name_trans;
										}
									}
								}
							}
						}
					}	
					if(item_shown){
						infoContent += '<li class="item">';
						infoContent += 	'<div class="feature-info">';
						if (!value.toString().startsWith('http')) {
							infoContent += 		'<span class="product-description">' + key + '</span>';
							infoContent += 		'<a href="javascript:void(0)" class="product-title">' + value + '</a>';
							
						} else {
							infoContent += 		'<span class="product-description">' + key + '</span>';
							infoContent += 		'<a href="' + value + '" style="color: #00c0ef !important;" target="_blank" class="product-description">' + value + '</a>';
						}
						infoContent += 	'</div>';
						infoContent += '</li>';
					}
				}
				}
			}
			infoContent += 		'</ul>';
			infoContent += 	'</div>';
			infoContent += '</div>';
			
			if (selectedFeature.resources && (selectedFeature.resources.length > 0)) {
				var resourcesContent = '';
				resourcesContent += '<div class="box box-default">';
				resourcesContent += 	'<div class="box-body" style="padding: 20px;">';
				resourcesContent += 		'<ul style="list-style: none;">';
				for (var i=0; i<selectedFeature.resources.length; i++) {
					if (selectedFeature.resources[i].type == 'image') {	
						resourcesContent += '<li style="padding: 20px;">';
						resourcesContent += '<a href="' + selectedFeature.resources[i].url + '" data-toggle="lightbox" data-gallery="example-gallery">';
						resourcesContent += '	<img src="' + selectedFeature.resources[i].url + '" class="img-fluid adjust-image">';
						resourcesContent += '</a>';
						resourcesContent += '</li>';
						
					} else if  (selectedFeature.resources[i].type == 'pdf') {
						resourcesContent += '<li style="padding: 20px;">';
						resourcesContent += '<a href="' + selectedFeature.resources[i].url + '" target="_blank">';
						resourcesContent += 	'<i style="font-size:24px;" class="fa fa-file-pdf-o margin-r-5"></i>';
						resourcesContent += 	'<span style="color:#00c0ef;">' + selectedFeature.resources[i].name + '</span>';
						resourcesContent += '</a>';
						resourcesContent += '</li>';
						
					} else if  (selectedFeature.resources[i].type == 'video') {
						resourcesContent += '<li style="padding: 20px;">';
						resourcesContent += '<a href="' + selectedFeature.resources[i].url + '" target="_blank">';
						resourcesContent += 	'<i style="font-size:24px;" class="fa fa-file-video-o margin-r-5"></i>';
						resourcesContent += 	'<span style="color:#00c0ef;">' + selectedFeature.resources[i].name + '</span>';
						resourcesContent += '</a>';
						resourcesContent += '</li>';
						
					} else if  (selectedFeature.resources[i].type == 'file') {
						resourcesContent += '<li style="padding: 20px;">';
						resourcesContent += '<a href="' + selectedFeature.resources[i].url + '" target="_blank">';
						resourcesContent += 	'<i style="font-size:24px;" class="fa fa-file margin-r-5"></i>';
						resourcesContent += 	'<span style="color:#00c0ef;">' + selectedFeature.resources[i].name + '</span>';
						resourcesContent += '</a>';
						resourcesContent += '</li>';
						
					} else if (selectedFeature.resources[i].type == 'alfresco_dir') {
						
						var resourcePath = selectedFeature.resources[i].url.split('|')[1]
						var splitedPath = resourcePath.split('/')
						var folderName = splitedPath[splitedPath.length-1]
						
						resourcesContent += '<li>';
						resourcesContent += '<div class="box box-primary">';
						resourcesContent += 	'<div class="box-body">';
						resourcesContent += 		'<ul class="products-list product-list-in-box">';
						resourcesContent += 			'<li class="item">';
						resourcesContent += 				'<div class="product-img">';
						resourcesContent += 					'<i style="font-size: 48px; color: #f39c12 !important;" class="fa fa-folder-open"></i>';
						resourcesContent += 				'</div>';
						resourcesContent += 				'<div class="product-info">';
						resourcesContent += 					'<a id="resource-title" href="javascript:void(0)" class="product-title">' + folderName + '</a>';
						resourcesContent += 					'<span id="resource-description" class="product-description">' + resourcePath + '</span>';
						resourcesContent += 				'</div>';
						resourcesContent += 			'</li>';
						resourcesContent += 		'</ul>';
						resourcesContent += 	'</div>';
						resourcesContent += 	'<div class="box-footer text-center">';
						resourcesContent += 		'<a id="view-resources" data-url="' + selectedFeature.resources[i].url + '" href="javascript:void(0)" style="margin-right: 10px;"><i class="fa fa-eye"></i> ' + gettext('View resources') + '</a>';
						resourcesContent += 	'</div>';
						resourcesContent += '</div>';
						resourcesContent += '</li>';
					}
				}
				resourcesContent += 		'</ul>';
				resourcesContent += 	'</div>';
				resourcesContent += '</div>';
			}
			
			var ui = '';
			ui += '<div class="nav-tabs-custom">';
			ui += '<ul class="nav nav-tabs">';
			ui += 		'<li class="active"><a href="#tab_info_content" data-toggle="tab" aria-expanded="true" style="font-weight: bold;">' + gettext('Feature info') + '</a></li>';
			if (selectedFeature.resources && (selectedFeature.resources.length > 0)) {
				ui += 	'<li id="resources-tab" class=""><a href="#tab_resources_content" data-toggle="tab" aria-expanded="false" style="font-weight: bold;">' + gettext('Multimedia resources') + '</a></li>';
			}
			ui += '</ul>';
			ui += '<div class="tab-content">';
			ui += '<div class="tab-pane active" id="tab_info_content">';
			ui += infoContent;
			ui += '</div>';
			if (selectedFeature.resources && (selectedFeature.resources.length > 0)) {
				ui += '<div class="tab-pane" id="tab_resources_content">';
				ui += resourcesContent;
				ui += '</div>';
			}
			ui += '</div>';
			ui += '</div>';
			
			detailsTab.empty();
			$.gvsigOL.controlSidebar.open();
			$('.nav-tabs a[href="#details-tab"]').tab('show');
			detailsTab.append(ui);
			
			$('#view-resources').on('click', function (e) {
				e.preventDefault();
				var url = this.dataset.url
				if (url != '#') {
					window.open(url,'_blank','width=780,height=600,left=150,top=200,toolbar=0,status=0');
				}
			});
		}
	}
	
	if(tab_opened=='resources'){
		$('.nav-tabs a[href="#tab_resources_content"]').tab('show');
	}
};

getFeatureInfo.prototype.isGeomType = function(type){
	if(type == 'POLYGON' || type == 'MULTIPOLYGON' || type == 'LINESTRING' || type == 'MULTILINESTRING' || type == 'POINT' || type == 'MULTIPOINT'){
		return true;
	}
	return false;
}

getFeatureInfo.prototype.describeFeatureType = function(layer) {
	
	var featureType = new Array();
	
	$.ajax({
		type: 'POST',
		async: false,
	  	url: '/gvsigonline/services/describeFeatureType/',
	  	data: {
	  		'layer': layer.layer_name,
			'workspace': layer.workspace
		},
	  	success	:function(response){
	  		if("fields" in response){
	  			featureType = response['fields'];
	  		}
		},
	  	error: function(){}
	});
	
	return featureType;
};


/**
 * TODO
 */
getFeatureInfo.prototype.getLayerTitle = function(feature){
	
	var layerTitle = null;
	var layerName = feature.id.split('.')[0];
	
	var layers = this.map.getLayers().getArray();
	for (var i=0; i<layers.length; i++) {
		if (!layers[i].baselayer) {
			if (layers[i].layer_name && layers[i].title) {
				if (layers[i].layer_name == layerName) {
					layerTitle = layers[i].title;
				}
			}						
		}
	}
	
	return layerTitle;
};

/**
 * TODO
 */
getFeatureInfo.prototype.deactivate = function() {			
	this.$button.removeClass('button-active');
	this.source.clear();
	this.map.removeLayer(this.resultLayer);
	this.map.un('click', this.clickHandler, this);
	this.active = false;
	this.hideResultTab();
	this.popup.hide();
};

/**
 * TODO
 */
getFeatureInfo.prototype.hideResultTab = function(p,f) {
};

/**
 * TODO
 */
getFeatureInfo.prototype.showResultTab = function(p,f) {
	if (this.resultsTab.hasClass('hidden')) {
		this.resultsTab.removeClass('hidden');
	}
};