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
var CalculateClosedControl = function(map) {

	this.map = map;
	
	this.id = "calculate-closed-control";

	var button = document.createElement('button');
	button.setAttribute("id", this.id);
	button.setAttribute("class", "toolbar-button");
	button.setAttribute("title", gettext('Calculate closed'));
	var icon = document.createElement('i');
	icon.setAttribute("class", "icon-disconnect");
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
CalculateClosedControl.prototype.active = false;

/**
 * TODO
 */
CalculateClosedControl.prototype.deactivable = true;

/**
 * TODO
 */
CalculateClosedControl.prototype.source = null;

/**
 * TODO
 */
CalculateClosedControl.prototype.resultLayer = null;

/**
 * TODO
 */
CalculateClosedControl.prototype.mapCoordinates = null;


/**
 * @param {Event} e Browser event.
 */
CalculateClosedControl.prototype.handler = function(e) {
	e.preventDefault();
	if (this.active) {
		this.deactivate();
		
	} else {
		
		this.$button.addClass('button-active');
		this.active = true;
		this.$button.trigger('control-active', [this]);

		this.map.on('click', this.clickHandler, this);	
		
		this.source = new ol.source.Vector(); 
		
		var defaultStyle = {
			'Point': [new ol.style.Style({
				image: new ol.style.Circle({
					fill: new ol.style.Fill({
						color: 'rgba(255,255,0,0.7)'
					}),
					radius: 8,
					stroke: new ol.style.Stroke({
						color: '#ff0',
						width: 3
					})
				})
			})],
			'LineString': [new ol.style.Style({
				stroke: new ol.style.Stroke({
					color: '#f00',
					width: 5
				})
			})],
			'Polygon': [new ol.style.Style({
				fill: new ol.style.Fill({
					color: 'rgba(0,255,255,0.5)'
				}),
				stroke: new ol.style.Stroke({
					color: '#0ff',
					width: 1
				})
			})],
			'MultiPoint': [new ol.style.Style({
				image: new ol.style.Circle({
					fill: new ol.style.Fill({
						color: 'rgba(255,0,255,0.5)'
					}),
					radius: 5,
					stroke: new ol.style.Stroke({
						color: '#f0f',
						width: 1
					})
				})
			})],
			'MultiLineString': [new ol.style.Style({
				stroke: new ol.style.Stroke({
					color: '#0f0',
					width: 3
				})
			})],
			'MultiPolygon': [new ol.style.Style({
				fill: new ol.style.Fill({
					color: 'rgba(0,0,255,0.5)'
				}),
				stroke: new ol.style.Stroke({
					color: '#00f',
					width: 1
				})
			})]
		};

		var styleCache = {
			'V': [new ol.style.Style({
				image: new ol.style.Circle({
					fill: new ol.style.Fill({
						color: 'rgba(255,255,0,0.5)'
					}),
					radius: 8,
					stroke: new ol.style.Stroke({
						color: '#f00',
						width: 3
					})
				})
			})],
			'D': [new ol.style.Style({
				image: new ol.style.Circle({
					fill: new ol.style.Fill({
						color: 'rgba(255,100,60,0.7)'
					}),
					radius: 8,
					stroke: new ol.style.Stroke({
						color: '#AA0',
						width: 3
					})
				})
			})],
			'T': [new ol.style.Style({
				stroke: new ol.style.Stroke({
					color: '#f00',
					width: 5
				})
			})],
			'A': [new ol.style.Style({
				stroke: new ol.style.Stroke({
					color: '#AB0',
					width: 4
				})
			})],
			'I': [new ol.style.Style({
				image: new ol.style.Circle({
					fill: new ol.style.Fill({
						color: 'rgba(255,255,0,0.7)'
					}),
					radius: 3,
					stroke: new ol.style.Stroke({
						color: '#0f0',
						width: 3
					})
				})
			})],
		};
		
		this.resultLayer = new ol.layer.Image({
			source: new ol.source.ImageVector({
				source: this.source,
				style: function(feature, resolution) {		  		 
			  		var tipo = feature.get('tipo');
			  		var style = styleCache[tipo];
			  		return style;
			  	}
			}),
			visible: true
		  	
		});
		this.resultLayer.baselayer = true;
		this.map.addLayer(this.resultLayer);
		
	}
};


/**
 * @param {Event} e Browser event.
 */
CalculateClosedControl.prototype.clickHandler = function(evt) {
	evt.preventDefault();
	var self = this;
	this.mapCoordinates = evt.coordinate;
	
	var x = this.mapCoordinates[0].toString().replace(".",",");
	var y = this.mapCoordinates[1].toString().replace(".",",");
	
	//var x = '-48345,586635243046';
	//var y = '4743970,267098098';
	
	this.getClosed(x, y);
};


/**
 * Handle pointer click.
 * @param {ol.MapBrowserEvent} evt
 */
CalculateClosedControl.prototype.getClosed = function(x, y) {
	var self = this;
	//this.source.clear();
	$.support.cors = true;
	$.ajax({
		type: 'GET',
		//url: '/gvsigonline/proxy/?url=' + "http://gismovil.aguasdevalencia.es/Proxy.svc/GetCerrada/" + x + "/" + y,
		url: '/gvsigonline/proxy/?url=' + 'https://aguas.gvsigonline.com/Proxy.svc/GetCerrada/' + x + "/" + y,
		contentType: 'text/plain',
		xhrFields: {
			withCredentials: false
		},
		headers: {},
		success: function(response){
			var reader = new ol.format.GeoJSON();
			var normalized = response.toString().replace('<string xmlns="http://schemas.microsoft.com/2003/10/Serialization/">','');
			normalized = normalized.toString().replace('</string>','');
			var data = JSON.parse(normalized);
			var features = reader.readFeatures(data);
			if (features.length > 0){
				self.source.addFeatures(features);
				var view2D = self.map.getView();
				view2D.fit(self.source.getExtent(), self.map.getSize());
				
			} else{
				alert("Punto no posicionado sobre la red.");
			}
	  	},
		error: function(response){}
	});
	
};


/**
 * TODO
 */
CalculateClosedControl.prototype.deactivate = function() {			
	this.$button.removeClass('button-active');
	this.source.clear();
	this.map.removeLayer(this.resultLayer);
	this.active = false;
	this.map.un('click', this.clickHandler, this);
};