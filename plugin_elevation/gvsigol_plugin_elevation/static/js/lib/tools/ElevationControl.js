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
var ElevationControl = function(map, zLayer) {
	
	this.id = "elevation-control";
	this.map = map;
	this.zLayer = zLayer;

	this.$button = $("#elevation-control");

	var this_ = this;
	var handler = function(e) {
		this_.handler(e);
	};

	this.$button.on('click', handler);
	this.$button.on('touchstart', handler);
	
	this.profilControl = null;
	this.point = null;
	
	this.drawStyle = [	
		new ol.style.Style({	
			image: new ol.style.Circle({	
				radius: 10,
				fill: new ol.style.Fill({ color: '#f15511' })
			}),
			stroke: new ol.style.Stroke({	
				color: '#f15511',
				width: 2
			}),
			fill: new ol.style.Fill({	
				color: 'rgba(241, 85, 17, 0.3)'
			})
		})
	];
	
	this.source2D = new ol.source.Vector();
	this.layer2D = new ol.layer.Vector({
		source: this.source2D,
		style: this.drawStyle
	});
	this.layer2D.setZIndex(99999999);
	map.addLayer(this.layer2D);
	
	this.source3D = new ol.source.Vector();
	this.layer3D = new ol.layer.Vector({
		source: this.source3D,
		style: this.drawStyle
	});
	this.layer3D.setZIndex(99999999);
	map.addLayer(this.layer3D);
	
	this.drawInteraction = new ol.interaction.Draw({
		source: this.layer2D.getSource(),
		type: 'LineString'
	});
	
	var ui = '';
	ui += '<div id="floating-modal-elevation">';
	ui += 	'<div class="box box-default">';
	ui += 		'<div class="box-body floating-modal-elevation-body">';
	ui += 		'</div>';
	ui += 		'<div class="box-footer">';
	ui += 			'<button id="elevation-close-button" type="button" class="btn btn-default pull-right elevation-close-button">' + gettext('Close') + '</button>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	$('body').append(ui);
	
	$('#floating-modal-elevation').dialog({
		width: 500,
		resizable: false,
		autoOpen: false,
		open: function (event, ui) {
		    $('#floating-modal-elevation').css('overflow', 'hidden');
		},
		close: function( event, ui ) {
			this_.deactivate();
		}
	});
	
	$('.elevation-close-button').on('click', function(){
		this_.deactivate();
	});

};

/**
 * TODO
 */
ElevationControl.prototype.active = false;

/**
 * TODO
 */
ElevationControl.prototype.deactivable = true;

/**
 * @param {Event} e Browser event.
 */
ElevationControl.prototype.handler = function(e) {
	e.preventDefault();
	var self = this;
	
	
	if (this.active) {
		this.deactivate();

	} else {
		this.$button.addClass('button-active');
		this.active = true;
		this.$button.trigger('control-active', [this]);
		
		for (var i=0; i<this.map.tools.length; i++){
			if (this.map.tools[i].deactivable == true) {
				this.map.tools[i].deactivate();
			}
		}
		
		$('#get-feature-info').attr("disabled", true);
		$('#get-feature-info').css("cursor", "not-allowed");

		this.map.addInteraction(this.drawInteraction);
		this.drawInteraction.on('drawend', function(evt) {
			$('body').overlay();
			setTimeout(function() {
				self.calculateElevation(evt.feature);
			}, 2000);
		}, this);

		
	}
};


/**
 * TODO
 */
ElevationControl.prototype.calculateElevation = function(feat) {
	var self = this;
	var format = new ol.format.GeoJSON();
	var line2D = feat;
	
	var newCoords = new Array();
	var currentCoords = line2D.getGeometry().getCoordinates();
	var length = line2D.getGeometry().getLength();
	for (i=0; i<currentCoords.length-1; i++) {
		var startPoint = ol.proj.transform(currentCoords[i], 'EPSG:3857', 'EPSG:4326');
		var endPoint = ol.proj.transform(currentCoords[i+1], 'EPSG:3857', 'EPSG:4326');
		var segment = new ol.Feature({
			geometry: new ol.geom.LineString([startPoint, endPoint], 'XY')
		});
		
		var turfSegment = format.writeFeatureObject(segment);
		var segmentLength = turf.length(turfSegment, {units: 'kilometers'});
		var alongDistance = segmentLength / 3;
		
		var tPoint1 = turf.along(turfSegment, alongDistance, {units: 'kilometers'});
		var tPoint2 = turf.along(turfSegment, alongDistance * 2, {units: 'kilometers'});
		
		var midPoint1 = format.readFeature(tPoint1);
		var midPoint2 = format.readFeature(tPoint2);

		newCoords.push(ol.proj.transform(startPoint, 'EPSG:4326', 'EPSG:3857')); 
		newCoords.push(ol.proj.transform(midPoint1.getGeometry().getCoordinates(), 'EPSG:4326', 'EPSG:3857'));
		newCoords.push(ol.proj.transform(midPoint2.getGeometry().getCoordinates(), 'EPSG:4326', 'EPSG:3857'));
		newCoords.push(ol.proj.transform(endPoint, 'EPSG:4326', 'EPSG:3857')); 
	}
	line2D.getGeometry().setCoordinates(newCoords);
	
	var coordinates2D = line2D.getGeometry().getCoordinates();
	
	var coordinates3D = new Array();
	var zArray = [];
	for (var i=0; i<coordinates2D.length; i++) {
		var z = self.getElevation(coordinates2D[i]);
		coordinates3D.push([coordinates2D[i][0], coordinates2D[i][1], z]);
		zArray.push(z);
	}
	var geomLine3D = new ol.geom.LineString(coordinates3D, 'XYZ');
	var line3D = new ol.Feature();
	line3D.setGeometry(geomLine3D);
	self.source2D.clear();
	self.source3D.addFeature(line3D);
	this.point = null;
	this.point = new ol.Feature(new ol.geom.Point([0,0]));
	this.point.setStyle([]);
	self.source3D.addFeature(this.point);
	$("#floating-modal-elevation").dialog("open");
	self.addProfilControl(line3D, zArray, length);
	self.map.removeInteraction(self.drawInteraction);
	
	$.overlayout();
};

/**
 * TODO
 */
ElevationControl.prototype.addProfilControl = function(feat, zArray, length) {
	zArray.sort(function (a, b) { return a-b; });
	var self = this;
	if (this.profilControl != null) {
		this.profilControl = null;
		$(".floating-modal-elevation-body").empty();
	}
	this.profilControl = new ol.control.Profil({	
		target: document.querySelector(".floating-modal-elevation-body"),
		width:400, 
		height:200,
		info: {
			"zmin": "Zmin",
			"zmax": "Zmax",
			"ytitle": "Altitud (m)",
			"xtitle": "Distancia (km)",
			"time": " ",
			"altitude": "Altitud",
			"distance": "Distancia",
			"altitudeUnits": "m",
			"distanceUnitsM": "m",
			"distanceUnitsKM": "km",
		}
	});
	this.map.addControl(this.profilControl);
	
	var altMax = zArray[zArray.length - 1];
	this.profilControl.setGeometry(feat, {	
		graduation:50,
		amplitude:altMax,
		zmin: parseFloat('0')
	});
	
	var magnification = (length/altMax)/2;
	
	var magnificationHtml = '';
	magnificationHtml += '<div>';
	magnificationHtml += '<span><b>Exageración vertical: </b>' + Math.round(magnification) + 'x</span>';
	magnificationHtml += '</div>';
	$('.floating-modal-elevation-body').prepend(magnificationHtml);
	
	function drawPoint(e) {
		if (!self.point) return;
		if (e.type=="over"){
			self.point.setGeometry(new ol.geom.Point(e.coord));
			self.point.setStyle(null);
			
		} else {
			self.point.setStyle([]);
		}
	};
	
	this.profilControl.on(["over","out"], drawPoint);
};

/**
 * TODO
 */
ElevationControl.prototype.drawPoint = function(e) {
	if (!this.point) return;
	if (e.type=="over"){
		this.point.setGeometry(new ol.geom.Point(e.coord));
		this.point.setStyle(null);
		
	} else {
		this.point.setStyle([]);
	}
};

/**
 * TODO
 */
ElevationControl.prototype.getElevation = function(coordinates){
	var self = this;
	var elevation = 0.0;
	
	var featureInfoUrl = this.zLayer.getSource().getGetFeatureInfoUrl(
    	coordinates,
		this.map.getView().getResolution(),
		this.map.getView().getProjection().getCode(),
		{'INFO_FORMAT': 'text/html'}
	);
    
	$.ajax({
		type: 'GET',
		async: false,
	  	url: featureInfoUrl,
	  	success	:function(response){
	  		elevation = response.replace('↵', '');
	  		elevation = parseFloat(elevation).toFixed(2);
		},
	  	error: function(){}
	});

	return elevation;
};

/**
 * TODO
 */
ElevationControl.prototype.getZLayer = function() {
	return this.zLayer;
};

/**
 * TODO
 */
ElevationControl.prototype.deactivate = function() {
	this.$button.removeClass('button-active');
	this.active = false;
	this.source2D.clear();
	this.source3D.clear();
	$(".floating-modal-elevation-body").empty();
	$("#floating-modal-elevation").dialog("close");
	this.map.removeControl(this.profilControl);
	this.profilControl = null;
	$('#get-feature-info').attr("disabled", false);
	$('#get-feature-info').css("cursor", "pointer");
};