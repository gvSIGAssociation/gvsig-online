/**
 * gvSIG Online.
 * Copyright (C) SCOLAB.
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


var search = function(map, conf) {
	this.map = map;	
	this.conf = conf;
	this.overlay = null;	
	this.menus = null;	
	this.popup = null;
	this.popups = [];
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
			xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
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
									xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
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
									xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
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
									xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
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
									xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
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
									xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
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

				if(response.types[i] == "uy_sudir"){
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
									xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
								},
								data: {
									'coord': coordinate[0] + ","+ coordinate[1],
									'type': 'uy_sudir'
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


				if(response.types[i] == "icv"){
					self.menus.push({
						text: 'Dirección de ICV',
						classname: 'geocoding-contextmenu', // add some CSS rules
						callback: function (obj) {
							var coordinate = ol.proj.transform([parseFloat(obj.coordinate[0]), parseFloat(obj.coordinate[1])], 'EPSG:3857', 'EPSG:4258');	
							$.ajax({
								type: 'POST',
								async: false,
								url: '/gvsigonline/geocoding/get_location_address/',
								beforeSend:function(xhr){
									xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
								},
								data: {
									'coord': coordinate[0] + ","+ coordinate[1],
									'type': 'icv'
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

				if(response.types[i] == "generic"){
					self.menus.push({
						text: 'Dirección de IDE de Albacete',
						classname: 'geocoding-contextmenu', // add some CSS rules
						callback: function (obj) {
							var coordinate = ol.proj.transform([parseFloat(obj.coordinate[0]), parseFloat(obj.coordinate[1])], 'EPSG:3857', 'EPSG:4326');	
							$.ajax({
								type: 'POST',
								async: false,
								url: '/gvsigonline/geocoding/get_location_address/',
								beforeSend:function(xhr){
									xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
								},
								data: {
									'coord': coordinate[0] + ","+ coordinate[1],
									'type': 'generic'
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
									xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
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
					xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
				},
				data: {
					'address': suggestion.data
				},
				success	:function(response){
					if (response.address) {
						window.lastgeolocationsearch = response;
						
						if(window.geocoding_event != null) {
							window.geocoding_event.dispatchEvent(new Event('onnewcandidate'));
						}

						if (Array.isArray(response.address)) {
							var epsg = 'EPSG:4326'; // Por defecto
							if (response.address.srs) { 
								epsg = response.address.srs;
							}								
							self.locate(response.address, epsg, true);
							let layer = self.getSearchLayer(self.map); 

							if(response.address[0] && response.address[0].geom) {
								self.drawSearchLayer(self, response.address[0].geom, layer);
							}
						}
						else if (response.address["address"]) {
							var epsg = 'EPSG:4326'; // Por defecto
							if (response.address.srs) { 
								epsg = response.address.srs;
							}
							self.locate(response.address, epsg, true);
						} // if - else
					} // if
				},
				error: function(xhr, status, error) {
					  console.error(xhr.responseText);
				}
			});
		}

	});
};

search.prototype.drawSearchLayer = function(self, geom, layer) {
	let format = new ol.format.WKT();
	tramos = [geom]
	if(tramos.length > 0) {
		for(var i = 0; i < tramos.length; i++) {
			var feats = format.readFeatures(tramos[i], {
				dataProjection: 'EPSG:4326',
				featureProjection: 'EPSG:3857'
			});
			layer.getSource().addFeatures(feats);
		}
	}	
	self.map.addLayer(layer);
}

search.prototype.getSearchLayer = function(map) {
	for(var i = 0; i < map.getLayers().getLength(); i++) {
		let arr = map.getLayers().getArray()
		if (arr[i].get('name') === 'search') {
			arr[i].getSource().clear();
			return arr[i];
		}
	}

	var layer = new ol.layer.Vector({
	  source: new ol.source.Vector({
		  projection: 'EPSG:3857'
	  }),
	  style: new ol.style.Style({
			image: new ol.style.Circle({
	            fill: new ol.style.Fill({
	                color: 'rgba(255, 0, 00, 0.8)'
	            }),
	            stroke: new ol.style.Stroke({
		            color: 'white',
		            width: 2
		        }),
	            radius: 10,
	    	}),
	        stroke: new ol.style.Stroke({
	            color: 'rgba(255, 0, 0, 0.8)',
	            width: 3
	        })
	  })
	});
			
	layer.set('name', 'search');
	layer.setZIndex(10000);
	return layer;
};


/**
 * TODO.
 */
search.prototype.locate = function(address, origin_srs, fromCombo) {	
	var self = this;	
	this.map.removeOverlay(this.popup);
	for (var i=0; i < this.popups.length; i++) {
		this.map.removeOverlay(this.popups[i]);
	}
	this.poups = [];
	this.popup = new ol.Overlay.Popup();
	this.map.addOverlay(this.popup);
	if(address != null && !(address instanceof Array)){
		if(fromCombo){			
			var coordinate = ol.proj.transform([parseFloat(address.lng), parseFloat(address.lat)], origin_srs, 'EPSG:3857');
			var txtPopup = $("#autocomplete").val();
			if (address.source == "ide_uy" || address.source == "uy_sudir") {
				if(address.state && (address.state == 2)){
					txtPopup += '<br> (Aproximado)';
				}
			}
			if (address.localidad)
			{
				txtPopup += '<br>Localidad: ' + address.localidad;				
			}
			if (address.departamento)
			{
				txtPopup += '<br>Departamento:' + address.departamento;				
			}
			if (address.olc)
			{
				txtPopup += '<br>OLC: ' + address.olc;				
			}
			if (address.olc_Asignado)
			{
				txtPopup += '<br>OLC Asignado: ' + address.olc_Asignado;				
			}
			
			this.popup.show(coordinate, '<div><p>' + txtPopup + '</p></div>');
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
				if (address.source == "ide_uy" || address.source == "uy_sudir") {
					var coordinate = ol.proj.transform([parseFloat(address.lng), parseFloat(address.lat)], 'EPSG:4326', 'EPSG:3857');	
					var callejero = "";
					if(address.tip_via && (address.tip_via.trim() != 0)){
						callejero = address.tip_via + " ";
					}
					if(address.address && (address.address.trim() != 0)){
						callejero = callejero + address.address;
					}
					if ((address.localidad) && (address.type !== 'LOCALIDAD'))
					{
						callejero += '<br>Localidad: ' + address.localidad;				
					}
					if ((address.departamento) && (address.type !== 'LOCALIDAD'))
					{
						callejero += '<br>Departamento:' + address.departamento;				
					}
					if (address.olc)
					{
						callejero += '<br><span style="color:grey">OLC: ' + address.olc + '</span> <button onclick="navigator.clipboard.writeText(\''
						 + address.olc + '\');">Copiar</button>' ;				
					}
					if (address.olc_Asignado)
					{
						callejero += '<br>OLC Asignado: ' + address.olc_Asignado;				
					}					
					
					this.popup.show(coordinate, '<div><p>' + callejero + '</p></div>');	
				} else if (address.source == "generic") {
					var coordinate = ol.proj.transform([parseFloat(address.lng), parseFloat(address.lat)], 'EPSG:4326', 'EPSG:3857');
					var txtPopup = "";
					if(address.address && (address.address.trim() != 0)) {
						txtPopup = address.address;
					}
					if (address.olc) {
						txtPopup += '<br><span style="color:grey">OLC: ' + address.olc + '</span> <button onclick="navigator.clipboard.writeText(\'' + address.olc + '\');">Copiar</button>' ;	
						txtPopup += '&nbsp;<button onclick="window.open(\'https://www.google.com/maps/place/' + address.olc.replace('+', '%2B') + '\',\'_blank\');">Google</button>' ;				
					}
					this.popup.show(coordinate, '<div><p>' + txtPopup + '</p></div>');	
					let layer = this.getSearchLayer(this.map); 

					if(address.geom) {
						this.drawSearchLayer(this, address.geom, layer);
					}
				} else {
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
	else
	{
		if (address instanceof Array) {
			var mCoord = [0, 0];

			for (var i=0; i < address.length; i++)
			{
				var a = address[i];
//				console.log('Llega ' + a.address + ' -> latlon:[' + a.lat + ',' + a.lng + ']');
				var coordinate = ol.proj.transform([parseFloat(a.lng), parseFloat(a.lat)], a.srs, 'EPSG:3857');
				var nPopup = new ol.Overlay.Popup();
				this.popups.push(nPopup); 
				this.map.addOverlay(nPopup);
				// TODO: MIRAR SI VIENE DEL COMBO? => 	var txtPopup = $("#autocomplete").val();
				var txtPopup = a.address;
				if (a.source == "ide_uy" || a.source == 'uy_sudir') {
					if(a.state && (a.state == 2)){
						txtPopup += '<br> (Aproximado)';
					}
					if ((a.localidad) && (a.type !== 'LOCALIDAD'))
					{
						txtPopup += '<br>Localidad: ' + a.localidad;				
				}
					if ((a.departamento) && (a.type !== 'LOCALIDAD'))
					{
						txtPopup += '<br>Departamento:' + a.departamento;				
					}
					if (a.olc)
					{
						txtPopup += '<br><span style="color:grey">OLC: ' + a.olc + '</span> <button onclick="navigator.clipboard.writeText(\''
						 + a.olc + '\');">Copiar</button>' ;				
					}
					if (a.olc_Asignado)
					{
						txtPopup += '<br>OLC Asignado: ' + a.olc_Asignado;				
					}					
				}
				if (a.source == "generic") {
					if(a.state && (a.state == 2)){
						txtPopup += '<br> (Aproximado)';
					}
					if (a.olc)
					{
						txtPopup += '<br><span style="color:grey">OLC: ' + a.olc + '</span> <button onclick="navigator.clipboard.writeText(\'' + a.olc + '\');">Copiar</button>' ;	
						txtPopup += '&nbsp;<button onclick="window.open(\'https://www.google.com/maps/place/' + a.olc.replace('+', '%2B') + '\',\'_blank\');">Google</button>' ;				
					}
					if (a.olc_Asignado)
					{
						txtPopup += '<br>OLC Asignado: ' + a.olc_Asignado;				
					}			
					
				}

				nPopup.show(coordinate, txtPopup);
				mCoord[0] = mCoord[0] + coordinate[0];
				mCoord[1] = mCoord[1] + coordinate[1];
				if (a.source == "generic") {
					$(".ol-popup-left").find(".closeBox").click(function() {
						for(var i = 0; i < map.getLayers().getLength(); i++) {
							let arr = map.getLayers().getArray()
							if (arr[i].get('name') === 'search') {
								arr[i].getSource().clear();
							}
						}
					});	
				}
			}
			mCoord[0] = mCoord[0] / address.length;
			mCoord[1] = mCoord[1] / address.length;
			this.map.getView().setCenter(mCoord);
			this.map.getView().setZoom(17);			
		}
	}			

};



