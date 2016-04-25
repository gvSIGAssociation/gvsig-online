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
		
		//this.resultPanelContent.empty();	
		//window.sidebar.open('results');
		
		var viewResolution = /** @type {number} */ (this.map.getView().getResolution());
		var qLayer = null;
		var url = null;
		for (var i=0; i<queryLayers.length; i++) {
			qLayer = queryLayers[i];
			url = qLayer.getSource().getGetFeatureInfoUrl(
				evt.coordinate, 
				viewResolution, 
				this.map.getView().getProjection().getCode(),
				{'INFO_FORMAT': 'application/json', 'FEATURE_COUNT': '100'}
			);
			
			$.ajax({
				type: 'GET',
				async: false,
			  	url: url,							
			  	success	:function(response){
			  		self.appendFeature(response, qLayer);
			  	},
			  	error: function(){}
			});
		}								
	}
};


/**
 * TODO
 */
getFeatureInfo.prototype.appendFeature = function(response, layer){
	
	var self = this;
	
	if (response.features) {
		var features = response.features;	
		for (var i in features) {
			
			var fid = features[i].id;
			
			var html = '<div class="attachment-text">';
			var text = '';
			for (var key in features[i].properties) {
				if (features[i].properties[key] != null && features[i].properties[key].toString().indexOf('http') > -1) {
					text += features[i].properties[key] + ', ';
					
				} else {
					if (!key.startsWith(this.prefix)) {
						text += features[i].properties[key] + ', ';
					}
				}
			}
			html += text;
			html += '<a href="#">more</a>';
			html += '</div>';
          
			this.popup.show(self.mapCoordinates, '<div>' + html + '</div>');
			
			self.map.getView().setCenter(self.mapCoordinates);
		}		
		
	} else {
		
		var tempDiv = document.createElement('div');
		tempDiv.innerHTML = response;
		
		if (tempDiv.childNodes[4]) {
			var html = '';
			html += '<div class="row" style="margin-bottom: 0px; padding-top: 5px; background-color: #ffffff;">';
			html += 	'<div class="col s12 m12" style="padding: 0 0.50rem;">';
			html += 		'<div style="padding: 20px;">';
			html += 			'<div class="grey-text darken-2">';
			html += 				'<h5 class="blue-text">' + gettext('Cadastre') + '</h5>';
			html += 				'<ul class="collection">';
			html += 					'<li class="collection-item" style="padding-top: 10px; padding-bottom: 30px;">';
			html += 						'<div class="grey-text left"><span style="color: #383838; font-weight: bold;">' + gettext('Cadastral reference') + ': </span><a target="_blank" href="' + tempDiv.childNodes[4].childNodes[0].href + '">' + tempDiv.childNodes[4].childNodes[0].textContent + '</a></div>';
			html += 					'</li>';
			html += 				'</ul>';
			html += 			'</div>';
			html += 		'</div>';
			html += 	'</div>';
			html += '</div>'
			
			this.showResultTab();
			this.resultPanelContent.append(html);
			this.resultHeader.empty();
			this.resultHeader.append(gettext('Point information'));
			
			var hdms = ol.coordinate.toStringHDMS(ol.proj.transform(self.mapCoordinates, 'EPSG:3857', 'EPSG:4326'));
			var wgs84 = ol.proj.transform(self.mapCoordinates, 'EPSG:3857', 'EPSG:4326');
			this.popupContent.innerHTML = '' +
										  '<p>' + gettext('Selected coordinate') + '</p>' +
										  '<code>' + hdms + '</code></br>' +
										  '<code>' + gettext('Latitude') + ': ' + wgs84[1].toFixed(4) + ', ' + gettext('Longitude') + ': ' + wgs84[0].toFixed(4) + '</code>';
										  
			this.overlay.setPosition(self.mapCoordinates);
			
			self.map.getView().setCenter(self.mapCoordinates);
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
	this.active = false;
	this.hideResultTab();
	window.sidebar.close();
};

/**
 * TODO
 */
getFeatureInfo.prototype.hideResultTab = function(p,f) {
	if (!this.resultsTab.hasClass('hidden')) {
		this.resultsTab.addClass('hidden');
	}
};

/**
 * TODO
 */
getFeatureInfo.prototype.showResultTab = function(p,f) {
	if (this.resultsTab.hasClass('hidden')) {
		this.resultsTab.removeClass('hidden');
	}
};