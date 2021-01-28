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
 * @author: José Badía <jbadia@scolab.es>
 */

/**
 * TODO
 */
var search = function(map, conf) {
	this.map = map;	
	this.conf = conf;
	this.overlay = null;	
	this.popup = null;
	this.popupCloser = null;
	this.popupContent = null;
	this.contextmenu = null;
	this.initUI();
	this.activeContextMenu();
};

search.prototype.activeContextMenu = function(){
	if(this.contextmenu == null){
		return;
	}
	var self = this;
	
	this.map.addControl(this.contextmenu);
}

search.prototype.removeContextMenu = function(){
	if(this.contextmenu == null){
		return;
	}
	
	this.map.removeControl(this.contextmenu);
}

/**
 * TODO.
 */
search.prototype.initUI = function() {	
	var self = this;

	this.popup = new ol.Overlay.Popup();
	this.map.addOverlay(this.popup);

	$.ajax({
		type: 'POST',
		async: false,
		url: '/gvsigonline/geocoding/get_providers_activated/',
		success	:function(response){
			var menus = [];
			for(var i=0; i<response.types.length; i++){
				if(response.types[i] == "nominatim"){
					menus.push({
						text: 'Dirección de Nominatim',
						classname: 'geocoding-contextmenu', // add some CSS rules
						callback: function (obj) {
							var coordinate = ol.proj.transform([parseFloat(obj.coordinate[0]), parseFloat(obj.coordinate[1])], 'EPSG:3857', 'EPSG:4258');	
							$.ajax({
								type: 'POST',
								async: false,
								url: '/gvsigonline/geocoding/get_location_address/',
								beforeSend:function(xhr){
									xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
								},
								data: {
									'coord': coordinate[0] + ","+ coordinate[1],
									'type': 'nominatim'
								},
								success	:function(response){
									self.locate(response, 'EPSG:4258', false);
								},
								error: function(){}
							});
						}
					});
				}

				if(response.types[i] == "cartociudad"){
					menus.push({
						text: 'Dirección de CartoCiudad',
						classname: 'geocoding-contextmenu', // add some CSS rules
						callback: function (obj) {
							var coordinate = ol.proj.transform([parseFloat(obj.coordinate[0]), parseFloat(obj.coordinate[1])], 'EPSG:3857', 'EPSG:4258');	
							$.ajax({
								type: 'POST',
								async: false,
								url: '/gvsigonline/geocoding/get_location_address/',
								beforeSend:function(xhr){
									xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
								},
								data: {
									'coord': coordinate[0] + ","+ coordinate[1],
									'type': 'cartociudad'
								},
								success	:function(response){
									self.locate(response, 'EPSG:4258', false);
								},
								error: function(){}
							});
						}
					});
				}

				if(response.types[i] == "googlemaps"){
					menus.push({
						text: 'Dirección de Google Maps',
						classname: 'geocoding-contextmenu', // add some CSS rules
						callback: function (obj) {
							var coordinate = ol.proj.transform([parseFloat(obj.coordinate[0]), parseFloat(obj.coordinate[1])], 'EPSG:3857', 'EPSG:4258');	
							$.ajax({
								type: 'POST',
								async: false,
								url: '/gvsigonline/geocoding/get_location_address/',
								beforeSend:function(xhr){
									xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
								},
								data: {
									'coord': coordinate[0] + ","+ coordinate[1],
									'type': 'googlemaps'
								},
								success	:function(response){
									self.locate(response, 'EPSG:4258', false);
								},
								error: function(){}
							});
						}
					});
				}
			}

			if(menus.length > 0){
				self.contextmenu = new ContextMenu({
					width: 170,
					defaultItems: false, // defaultItems are (for now) Zoom In/Zoom Out
					items: menus,
				});
			}
		},
		error: function(){}
	});
	
	parent.$(parent.document).find('#autocomplete').autocomplete({
		serviceUrl: '/gvsigonline/geocoding/search_candidates/',
		paramName: 'q',
		params: {
			limit: 10,
			countrycodes: 'es'
		},
		groupBy: 'category',
		transformResult: function(response) {
			jsonResponse = JSON.parse(response);
			if (jsonResponse.suggestions.length > 0) {
				return {
					suggestions: $.map(jsonResponse.suggestions, function(item) {
						return { 
							value: item.address,
							type: item.type,
							data: item 
						};
					})
				};
			}else{
				return {
					suggestions: []
				}
			}

		},
		onSelect: function (suggestion) {
			$.ajax({
				type: 'POST',
				async: false,
				url: '/gvsigonline/geocoding/find_candidate/',
				beforeSend:function(xhr){
					xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
				},
				data: {
					'address': suggestion.data
				},
				success	:function(response){
					if(response.address && response.address["address"]){
						self.locate(response.address, 'EPSG:4258', true);
					}
				},
				error: function(){}
			});
		}

	});
};

/**
 * TODO.
 */
search.prototype.locate = function(address, origin_srs, fromCombo) {	
	var self = this;	
	this.map.removeOverlay(this.popup);
	this.popup = new ol.Overlay.Popup();
	this.map.addOverlay(this.popup);
	if(address != null){
		var coordinate = ol.proj.transform([parseFloat(address.lng), parseFloat(address.lat)], origin_srs, 'EPSG:3857');	
		if(fromCombo){
			this.popup.show(coordinate, '<div><p>' + parent.$(parent.document).find("#autocomplete").val() + '</p></div>');
		}else{
			if(address.source == "cartociudad"){
				var callejero = "";
				if(address.tip_via && (address.tip_via.trim() != 0)){
					callejero = address.tip_via + " ";
				}
				callejero = callejero + address.address;
				if(address.portalNumber && (address.portalNumber != 0)){
					callejero = callejero + " " + address.portalNumber;
				}
				if(address.muni && (address.muni.trim() != 0)){
					callejero = callejero + ", " + address.muni;
				}
				this.popup.show(coordinate, '<div><p>' + callejero + '</p></div>');
			}else{
				this.popup.show(coordinate, '<div><p>' + address.address + '</p></div>');
			}
		}
		this.map.getView().setCenter(coordinate);
		if(fromCombo){
			this.map.getView().setZoom(14);
		}
	}
};



