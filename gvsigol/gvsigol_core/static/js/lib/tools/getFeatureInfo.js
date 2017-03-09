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
					queryLayers.push(layers[i]);
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
			
			var req = null;
			if (qLayer.layer_name == 'plg_catastro') {
				req = $.ajax({
					type: 'POST',
					async: false,
				  	url: url,
				  	success	:function(response){
				  		var tempDiv = document.createElement('div');
						tempDiv.innerHTML = response;
						if (tempDiv.childNodes[4]) {
							features.push({
			  					type: 'catastro',
			  					text: tempDiv.childNodes[4].childNodes[0].textContent,
			  					href: tempDiv.childNodes[4].childNodes[0].href
			  				});
						}
				  	},
				  	error: function(){}
				});
				
			} else {
				req = $.ajax({
					type: 'POST',
					async: false,
				  	url: '/gvsigonline/services/get_feature_info/',
				  	data: {
				  		url: url,
				  		query_layer: qLayer.layer_name,
				  		workspace: qLayer.workspace
				  	},
				  	success	:function(response){
				  		if (response.features) {
				  			for (var i in response.features) {
				  				features.push({
				  					type: 'feature',
				  					crs: response.crs,
				  					feature: response.features[i]
				  				});
				  			}
				  		}
				  	},
				  	error: function(){}
				});
			}
				
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
	html += 		'<span style="font-weight: bold; font-size: 12px;">' + gettext('Coordinates') + ':</span>' + ' <span>' + wgs84 + '</span>';	
	html += 	'</div>';
	html += '</li>';
	
	for (var i in features) {
		if (features[i].type == 'feature') {
			var fid = features[i].feature.id;
			html += '<li class="item">';
			html += 	'<div class="feature-info">';
			html += 		'<a href="javascript:void(0)" data-fid="' + fid + '" class="product-title item-fid" style="color: #444;">' + fid;
			html += 		'<span class="label label-info pull-right">' + gettext('More info') + '</span></a>';
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
	html += '</ul>';
	this.popup.show(self.mapCoordinates, '<div class="popup-wrapper">' + html + '</div>');	
	self.map.getView().setCenter(self.mapCoordinates);
	$('.item-fid').click(function(){
		self.showMoreInfo(this.dataset.fid, features);
	});

	$.overlayout();
			
};

/**
 * TODO
 */
getFeatureInfo.prototype.showMoreInfo = function(fid, features){
	var selectedFeature = null;
	for (var i in features) {
		if (features[i].type == 'feature') {
			if (fid == features[i].feature.id) {
				selectedFeature = features[i].feature; 
			}
		}
	}
	
	if (selectedFeature != null) {
		if (selectedFeature.type.toLowerCase() == 'feature') {
			var detailsTab = $('#details-tab');
			var infoContent = '';
			infoContent += '<div class="box box-default">';
			infoContent += 	'<div class="box-header with-border">';
			infoContent += 		'<span class="text">' + selectedFeature.id + '</span>';
			infoContent += 	'</div>';
			infoContent += 	'<div class="box-body" style="padding: 20px;">';
			infoContent += 		'<ul class="products-list product-list-in-box">';
			for (var key in selectedFeature.properties) {
				var value = selectedFeature.properties[key];
				if (value == "null" || value == null) {
					value = "";
				}
				if (!key.startsWith(this.prefix)) {	
					infoContent += '<li class="item">';
					infoContent += 	'<div class="feature-info">';
					infoContent += 		'<a href="javascript:void(0)" class="product-title">' + key + '</a>';
					infoContent += 		'<span class="product-description">' + value + '</span>';
					infoContent += 	'</div>';
					infoContent += '</li>';
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
				ui += 	'<li class=""><a href="#tab_resources_content" data-toggle="tab" aria-expanded="false" style="font-weight: bold;">' + gettext('Multimedia resources') + '</a></li>';
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