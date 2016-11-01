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
var search = function(map, conf) {
	this.map = map;	
	this.conf = conf;
	this.overlay = null;	
	this.popup = null;
	this.popupCloser = null;
	this.popupContent = null;
	this.initUI();
};

/**
 * TODO.
 */
search.prototype.initUI = function() {	
	var self = this;
	
	this.popup = new ol.Overlay.Popup();
	this.map.addOverlay(this.popup);
	
	$('#autocomplete').autocomplete({
		//serviceUrl: '/gvsigonline/geocoding/search_candidates/',
		serviceUrl: self.conf.candidates_url,
		paramName: 'q',
		params: {
			limit: 10,
			countrycodes: 'es'
		},
		transformResult: function(response) {
	        jsonResponse = JSON.parse(response);
	        // don't forget to handle errors because of a bad json
	        if (jsonResponse.length > 0) {
	        	return {
		            suggestions: $.map(jsonResponse, function(item) {
		                return { 
		                	value: item.address, 
		                	type: item.type,
		                	data: item 
		                };
		            })
		        };
	        }
	        
	    },
	    onSelect: function (suggestion) {
	        $.ajax({
				type: 'GET',
				async: false,
			  	url: self.conf.find_url,
			  	beforeSend:function(xhr){
			    	xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
			  	},
			  	data: {
			  		'q': suggestion.data.address,
			  		'type': suggestion.data.type,
			  		'tip_via': suggestion.data.tip_via,
			  		'id': suggestion.data.id,
			  		'portal': suggestion.data.portalNumber
				},
			  	success	:function(response){
			  		self.locate(response);
				},
			  	error: function(){}
			});
	    }
	});
};


/**
 * TODO.
 */
search.prototype.locate = function(loc) {	
	var self = this;
	$.ajax({
		type: 'GET',
		async: false,
	  	url: self.conf.reverse_url,
	  	beforeSend:function(xhr){
	    	xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
	  	},
	  	data: {
	  		'lon': loc.lng,
	  		'lat': loc.lat
		},
	  	success	:function(response){
	  		var tipVia = '';
	  		if (response.tip_via != null) {
	  			tipVia = response.tip_via;
	  		}
	  		var coordinate = ol.proj.transform([parseFloat(response.lng), parseFloat(response.lat)], 'EPSG:4326', 'EPSG:3857');	
	  		self.popup.show(coordinate, '<div><p>' + tipVia + ' ' + response.address + ' ' + response.portalNumber + ',' + response.muni + ' ,' + response.postalCode + ' (' + response.province + ')' + '</p></div>');
	  		self.map.getView().setCenter(coordinate);
	  		self.map.getView().setZoom(14);
		},
	  	error: function(){}
	});
};