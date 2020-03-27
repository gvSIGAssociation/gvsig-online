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
	this.menus = null;	
	this.popup = null;
	this.popupCloser = null;
	this.popupContent = null;
	this.contextmenu = null;
	this.initUI();
	this.loadTool();
};

search.prototype.loadTool = function(){

	this.id = "inverse-geocoding";
	
	var button = document.createElement('button');
	button.setAttribute("id", this.id);
	button.setAttribute("class", "toolbar-button");
	button.setAttribute("title", gettext('Inverse geocoding'));
	var icon = document.createElement('i');
	icon.setAttribute("class", "icon-reverse-geocoding");
	icon.setAttribute("aria-hidden", "true");
	button.appendChild(icon);
	
	this.$button = $(button);
	
	$('#viewer-search-form-input').append(button);
	
	var this_ = this;
	
	var handler = function(e) {
		this_.handler(e);
	};
	
	button.addEventListener('click', handler, false);
	button.addEventListener('touchstart', handler, false);
	
	this.map.tools.push(this);
};

/**
* TODO
*/
search.prototype.active = false;

/**
* TODO
*/
search.prototype.deactivable = true;

search.prototype.handler = function(e) {
	e.preventDefault();
	if (this.active) {
		this.deactivate();

	} else {
		for (var i=0; i<this.map.tools.length; i++){
			if (this.id != this.map.tools[i].id) {
				if (this.map.tools[i].deactivable == true) {
					this.map.tools[i].deactivate();
				}
			}
		}

		this.$button.addClass('button-active');
		this.active = true;
		this.activeContextMenu();
	}
};

search.prototype.deactivate = function() {			
	this.$button.removeClass('button-active');
	this.active = false;
	this.removeContextMenu();
};


search.prototype.activeContextMenu = function(){
	var self = this;
//	this.contextmenu = new ContextMenu({
//		width: 170,
//		defaultItems: false, // defaultItems are (for now) Zoom In/Zoom Out
//		items: this.menus,
//	});
//	
//	this.map.addControl(this.contextmenu);
	this.map.on('click', this.clickHandler, self);
	
	
	
}

search.prototype.clickHandler = function(evt, aux){
	var self = this;
	
	if(this.contextmenu == null){
		this.contextmenu = new ol.Overlay.Popup();
		this.map.addOverlay(this.contextmenu);
	}
	var mapCoordinates = evt.coordinate;
	
	if(this.menus.length > 1){
		var html = '<ul>'
		for(var i=0; i<this.menus.length; i++){
			html += '<li name="'+ this.menus[i].classname +'" class="inverse-geocoding-type">'+ this.menus[i].text +'</li>';
		}
		html += '</ul>';
		
		this.contextmenu.show(mapCoordinates, '<div class="popup-wrapper getfeatureinfo-popup">'+html+'</div>');	
		
		$(".inverse-geocoding-type").unbind("click").click(function(){
			var name = $(this).text();
			for(var i=0; i<self.menus.length; i++){
				if(self.menus[i].text == name){
					self.menus[i].callback(evt);
					self.contextmenu.hide();
				}
			}
		})
	}else{
		if(this.menus.length == 1){
			this.menus[0].callback(evt);
		}
		if(this.menus.length == 0){
			html = gettext('There is no active geocoder');
			this.contextmenu.show(mapCoordinates, '<div class="popup-wrapper getfeatureinfo-popup">'+html+'</div>');	
		}
	}	
	
}

search.prototype.removeContextMenu = function(){
	var self = this;
	if(this.contextmenu == null){
		return;
	}
//	this.map.removeControl(this.contextmenu);
	this.map.removeOverlay(this.contextmenu);
	this.contextmenu = null;
	this.map.un('click', this.clickHandler, self);
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
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		success	:function(response){
			self.menus = [];
			for(var i=0; i<response.types.length; i++){
				if(response.types[i] == "nominatim"){
					self.menus.push({
						text: 'Dirección de Nominatim',
						classname: 'geocoding-contextmenu', // add some CSS rules
						callback: function (obj) {
							var coordinate = ol.proj.transform([parseFloat(obj.coordinate[0]), parseFloat(obj.coordinate[1])], 'EPSG:3857', 'EPSG:4326');	
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
									self.locate(response, response.srs, false);
								},
								error: function(){}
							});
						}
					});
				}
				
				if(response.types[i] == "new_cartociudad"){
					self.menus.push({
						text: 'Dirección de CartoCiudad (Nuevo)',
						classname: 'geocoding-contextmenu', // add some CSS rules
						callback: function (obj) {
							var coordinate = ol.proj.transform([parseFloat(obj.coordinate[0]), parseFloat(obj.coordinate[1])], 'EPSG:3857', 'EPSG:4326');	
							$.ajax({
								type: 'POST',
								async: false,
								url: '/gvsigonline/geocoding/get_location_address/',
								beforeSend:function(xhr){
									xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
								},
								data: {
									'coord': coordinate[0] + ","+ coordinate[1],
									'type': 'new_cartociudad'
								},
								success	:function(response){
									self.locate(response, response.srs, false);
								},
								error: function(xhr, status, error) {
									  console.error(xhr.responseText);
								}
							});
						}
					});
				}

				if(response.types[i] == "cartociudad"){
					self.menus.push({
						text: 'Dirección de CartoCiudad',
						classname: 'geocoding-contextmenu', // add some CSS rules
						callback: function (obj) {
							var coordinate = ol.proj.transform([parseFloat(obj.coordinate[0]), parseFloat(obj.coordinate[1])], 'EPSG:3857', 'EPSG:4326');	
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
									self.locate(response, response.srs, false);
								},
								error: function(){}
							});
						}
					});
				}

				if(response.types[i] == "googlemaps"){
					self.menus.push({
						text: 'Dirección de Google Maps',
						classname: 'geocoding-contextmenu', // add some CSS rules
						callback: function (obj) {
							var coordinate = ol.proj.transform([parseFloat(obj.coordinate[0]), parseFloat(obj.coordinate[1])], 'EPSG:3857', 'EPSG:4326');	
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
									self.locate(response, response.srs, false);
								},
								error: function(){}
							});
						}
					});
				}
				
				if(response.types[i] == "ide_uy"){
					self.menus.push({
						text: 'Dirección de IDE Uruguay',
						classname: 'geocoding-contextmenu', // add some CSS rules
						callback: function (obj) {
							var coordinate = ol.proj.transform([parseFloat(obj.coordinate[0]), parseFloat(obj.coordinate[1])], 'EPSG:3857', 'EPSG:4326');	
							$.ajax({
								type: 'POST',
								async: false,
								url: '/gvsigonline/geocoding/get_location_address/',
								beforeSend:function(xhr){
									xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
								},
								data: {
									'coord': coordinate[0] + ","+ coordinate[1],
									'type': 'ide_uy'
								},
								success	:function(response){
									self.locate(response, response.srs, false);
								},
								error: function(xhr, status, error) {
									  console.error(xhr.responseText);
								}
							});
						}
					});
				}
				if(response.types[i] == "postgres"){
					self.menus.push({
						text: 'Dirección Simple',
						classname: 'geocoding-contextmenu', // add some CSS rules
						callback: function (obj) {
							var coordinate = ol.proj.transform([parseFloat(obj.coordinate[0]), parseFloat(obj.coordinate[1])], 'EPSG:3857', 'EPSG:4326');	
							$.ajax({
								type: 'POST',
								async: false,
								url: '/gvsigonline/geocoding/get_location_address/',
								beforeSend:function(xhr){
									xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
								},
								data: {
									'coord': coordinate[0] + ","+ coordinate[1],
									'type': 'postgres'
								},
								success	:function(response){
									self.locate(response, response.srs, false);
								},
								error: function(xhr, status, error) {
									  console.error(xhr.responseText);
								}
							});
						}
					});
				}
				
			}

			if(self.menus.length > 0){
//				self.contextmenu = new ContextMenu({
//					width: 170,
//					defaultItems: false, // defaultItems are (for now) Zoom In/Zoom Out
//					items: self.menus,
//				});
			}
		},
		error: function(xhr, status, error) {
			  console.error(xhr.responseText);
		}
	});

	$('#autocomplete').autocomplete({
		serviceUrl: '/gvsigonline/geocoding/search_candidates/',
		paramName: 'q',
		params: {
			limit: 10,
			countrycodes: 'es'
		},
		groupBy: 'category',
		transformResult: function(response) {
			jsonResponse = JSON.parse(response);
			window.lastcandidatestring = jsonResponse.query;
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
					if(response.address && response.address["address"]) {
						window.lastgeolocationsearch = response;
						var epsg = 'EPSG:4326'; // Por defecto
						if (response.address.srs) { 
							epsg = response.address.srs;
						}
						self.locate(response.address, epsg, true);
					}
				},
				error: function(xhr, status, error) {
					  console.error(xhr.responseText);
				}
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
	if(address != null && !(address instanceof Array && address.length == 0)){
		if(fromCombo){
			var coordinate = ol.proj.transform([parseFloat(address.lng), parseFloat(address.lat)], origin_srs, 'EPSG:3857');
			this.popup.show(coordinate, '<div><p>' + $("#autocomplete").val() + '</p></div>');
		}else{			
			if(address.source == "cartociudad" || address.source == "new_cartociudad"){
				var coordinate = ol.proj.transform([parseFloat(address.lng), parseFloat(address.lat)], origin_srs, 'EPSG:3857');	
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
				if (address.source == "ide_uy") {
					var coordinate = ol.proj.transform([parseFloat(address.lng), parseFloat(address.lat)], origin_srs, 'EPSG:3857');	
					var callejero = "";
					if(address.tip_via && (address.tip_via.trim() != 0)){
						callejero = address.tip_via + " ";
					}
					if(address.address && (address.address.trim() != 0)){
						callejero = callejero + address.address;
					}
//					if(address.portalNumber && (address.portalNumber != 0)){
//						callejero = callejero + " " + address.portalNumber;
//					}
//					if(address.localidad && (address.localidad.trim() != 0)){
//						if (callejero.trim() != 0)
//							callejero = callejero + ", " + address.localidad;
//						else
//							callejero = address.localidad;
//					}
//					if(address.departamento && (address.departamento.trim() != 0)){
//						callejero = callejero + " (" + address.departamento + ")";
//					}					
					this.popup.show(coordinate, '<div><p>' + callejero + '</p></div>');					
				}
				else
				{
					if (address instanceof Array) {
						for (var i=0; i < address.length; i++)
						{
							var a = address[i];
							var coordinate = ol.proj.transform([parseFloat(a.lng), parseFloat(a.lat)], a.srs, 'EPSG:3857');
							this.popup.show(coordinate, '<div><p>' + a.address + '</p></div>');
						}
					}
					else
					{
						var coordinate = ol.proj.transform([parseFloat(address.lng), parseFloat(address.lat)], address.srs, 'EPSG:3857');
						this.popup.show(coordinate, '<div><p>' + address.address + '</p></div>');
					}
				}
			}
		}
		this.map.getView().setCenter(coordinate);
		if(fromCombo){
			this.map.getView().setZoom(14);
		}
	}
};



