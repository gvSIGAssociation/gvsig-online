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
	    	
	    	/*this.resultPanelContent = $('#results .sidebar-pane-content');
	    	this.resultHeader = $('#results .sidebar-header');
	    	this.resultsTab = $('#results-tab');*/
	    	
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
			alert(gettext("No layers available"));
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
				
			ajaxRequests.push(
					$.ajax({
					type: 'GET',
					async: false,
				  	url: url,							
				  	success	:function(response){
				  		if (response.features) {
				  			for (var i in response.features) {
				  				features.push(response.features[i]);
				  			}
				  		}
				  	},
				  	error: function(){}
				})
			);
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
	for (var i in features) {
		
		var fid = features[i].id;
		
		
		html += '<li class="item">';
		html += 	'<div class="feature-info">';
		html += 		'<a href="javascript:void(0)" data-fid="' + fid + '" class="product-title item-fid" style="color: #444;">' + fid;
		html += 		'<span class="label label-info pull-right">' + gettext('More info') + '</span></a>';
		html += 	'</div>';
		html += '</li>';
		
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
		if (fid == features[i].id) {
			selectedFeature = features[i]; 
		}
	}
	var detailsTab = $('#details-tab');
	
	var ui = '';
	ui += '<div class="box box-primary">';
	ui += 	'<div class="box-header with-border" style="font-weight: bold;">';
	ui += 		'<span class="text">' + selectedFeature.id + '</span>';
	ui += 	'</div>';
	ui += 	'<div class="box-body" style="padding: 20px;">';
	ui += 		'<ul class="products-list product-list-in-box">';
	for (var key in selectedFeature.properties) {
		if (selectedFeature.properties[key] != null && selectedFeature.properties[key].toString().indexOf('http') > -1) {
			ui += '<li class="item">';
			ui += 	'<div class="feature-info">';
			ui += 		'<a href="' + selectedFeature.properties[key] + '" class="product-title">' + key;
			ui += 			'<span class="label label-warning pull-right">' + gettext('Open') + '</span>';
			ui += 		'</a>';
			ui += 		'<span class="product-description">' + selectedFeature.properties[key] + '</span>';
			ui += 	'</div>';
			ui += '</li>';
			
		} else {
			if (!key.startsWith(this.prefix)) {				
				ui += '<li class="item">';
				ui += 	'<div class="feature-info">';
				ui += 		'<a href="javascript:void(0)" class="product-title">' + key + '</a>';
				ui += 		'<span class="product-description">' + selectedFeature.properties[key] + '</span>';
				ui += 	'</div>';
				ui += '</li>';
			}
			
		}
	}
	ui += 		'</ul>';
	ui += 	'</div>';
	ui += '</div>';
	
	detailsTab.empty();
	$.gvsigOL.controlSidebar.open();
	$('.nav-tabs a[href="#details-tab"]').tab('show');
	detailsTab.append(ui);
	
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