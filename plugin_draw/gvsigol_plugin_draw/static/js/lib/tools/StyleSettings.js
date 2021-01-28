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
var StyleSettings = function(drawBar) {
	var self = this;
	this.drawBar = drawBar;
	this.style = {
		point: {
			well_known_name: 'circle',
			size: 8,
			fill_color: '#ffcc33',
			fill_opacity: 1.0,
			stroke_color: '#ffcc33',
			stroke_width: 2/*,
			stroke_opacity: 1.0*/
		},
		line: {
			stroke_color: '#ffcc33',
			stroke_width: 2,
			//stroke_opacity: 1.0,
			stroke_dash_array: 'none'
		},
		arrow: {
			stroke_color: '#ffcc33',
			stroke_width: 2,
			//stroke_opacity: 1.0,
			stroke_dash_array: 'none'
		},
		polygon: {
			fill_color: '#ffcc33',
			fill_opacity: 1.0,
			stroke_color: '#ffcc33',
			stroke_width: 2/*,
			stroke_opacity: 1.0*/
		},
		text: {
			font_size: 16,
			fill_color: '#f15511',
			fill_opacity: 1.0,
			stroke_color: '#ffffff',
			stroke_width: 4,
			text: gettext('Insert text')
		}
	};
	this.pointPrintStyles = {
		"version" : "2",
		"[style_name='point_style_0']" : {
			"symbolizers" : [{
				"type" : "point",
				"fillColor": "#ffcc33",
				"fillOpacity": 1.0,
				"graphicName": "circle",
				"pointRadius": 8,
				"strokeColor": "#ffcc33",
				"strokeWidth": 2
			}
		]}
	};
	this.linePrintStyles = {
		"version" : "2",
		"[style_name='line_style_0']" : {
			"symbolizers" : [{
				"type" : "line",
				"strokeColor":"#ffcc33",
				"strokeWidth":5
			}
		]}
	};
	this.arrowPrintStyles = {
		"version" : "2",
		"[style_name='arrow_style_0']" : {
			"symbolizers" : [{
				"type" : "line",
				"strokeColor":"#ffcc33",
				"strokeWidth":5
			}
		]}
	};
	this.polygonPrintStyles = {
		"version" : "2",
		"[style_name='polygon_style_0']" : {
			"symbolizers" : [{
				"type" : "polygon",
				"fillColor": "#ffcc33",
				"fillOpacity": 0.1,
				"strokeColor": "#ffcc33",
				"strokeWidth": 2
			}
		]}
	};
	this.textPrintStyles = {
		"version" : "2",
		"[style_name='text_style_0']" : {
			"symbolizers" : [{
				"type" : "text",
				"fontColor": '#f15511',
				"haloColor": '#ffffff',
			    "haloRadius": 4,
				"fontFamily": "sans-serif",
				"fontSize": "16px",
				"fontStyle": "normal",
				"label": '[text]'
			}]
		}
	};
	
	this.createModal();
	
	this.control = new ol.control.Toggle({	
		html: '<i class="fa fa-cogs" ></i>',
		className: "edit",
		title: gettext('Style settings'),
		onToggle: function(active){
			self.show();
			this.toggle();
		}
	});
	this.drawBar.addControl(this.control);
};

StyleSettings.prototype.deactivable = false;

StyleSettings.prototype.shapes = [
	{value: 'circle', title: gettext('Circle')},
	{value: 'square', title: gettext('Square')},
	{value: 'triangle', title: gettext('Triangle')},
	{value: 'star', title: gettext('Star')},
	{value: 'cross', title: gettext('Cross')},
	{value: 'x', title: 'X'}
];

StyleSettings.prototype.linePatterns = [
	{value: 'none', imgsrc: IMG_PATH + 'default-symbol.png'},
	{value: '5 10', imgsrc: IMG_PATH + '5_10.png'},
	{value: '10 5', imgsrc: IMG_PATH + '10_5.png'},
	{value: '5 1', imgsrc: IMG_PATH + '5_1.png'},
	{value: '1 5', imgsrc: IMG_PATH + '1_5.png'},
	{value: '15 10 5 10', imgsrc: IMG_PATH + '15_10_5_10.png'},
	{value: '5 5 1 5', imgsrc: IMG_PATH + '5_5_1_5.png'},
];

StyleSettings.prototype.createModal = function(e) {
	var ui = '';
	
	ui += '<div class="nav-tabs-custom">';
	ui += 	'<ul id="tab-menu" class="nav nav-tabs">';	
	ui += 		'<li class="active"><a href="#point-tab" data-toggle="tab">' + gettext('Point') + '</a></li>';
	ui += 		'<li><a href="#line-tab" data-toggle="tab">' + gettext('Line') + '</a></li>';
	ui += 		'<li><a href="#arrow-tab" data-toggle="tab">' + gettext('Arrow') + '</a></li>';
	ui += 		'<li><a href="#polygon-tab" data-toggle="tab">' + gettext('Polygon') + '</a></li>';
	ui += 		'<li><a href="#text-tab" data-toggle="tab">' + gettext('Text') + '</a></li>';
	ui += 	'</ul>';
	ui += 	'<div id="tab-content" class="tab-content">';
	ui += 		this.getPointTabUI();
	ui += 		this.getLineTabUI();
	ui += 		this.getArrowTabUI();
	ui += 		this.getPolygonTabUI();
	ui += 		this.getTextTabUI();
	ui += 	'</div>';
	ui += '</div>';
	
	$('#float-draw-modal .modal-body').empty();
	$('#float-draw-modal .modal-body').append(ui);
	
	this.registerEvents();

};

StyleSettings.prototype.getPointTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane active" id="point-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Select shape') + '</label>';
	ui += 			'<select id="well-known-name" class="form-control">';
	for (var i=0; i < this.shapes.length; i++) {
		if (this.shapes[i].value == this.style.point.well_known_name) {
			ui += '<option value="' + this.shapes[i].value + '" selected>' + this.shapes[i].title + '</option>';
		} else {
			ui += '<option value="' + this.shapes[i].value + '">' + this.shapes[i].title + '</option>';
		}
	}
	ui += 			'</select>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Size') + '</label>';
	ui += 			'<input id="graphic-size" type="number" class="form-control" value="' + parseInt(this.style.point.size) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Fill color') + '</label>';
	ui += 			'<input id="point-fill-color" type="color" value="' + this.style.point.fill_color + '" class="form-control color-chooser">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label style="display: block;">' + gettext('Fill opacity') + '<span id="point-fill-opacity-output" class="margin-l-15 gol-slider-output">' + (this.style.point.fill_opacity * 100) + '%</span>' + '</label>';
	ui += 			'<div id="point-fill-opacity"></div>';
	ui += 		'</div>';				 
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Stroke color') + '</label>';
	ui += 			'<input id="point-stroke-color" type="color" value="' + this.style.point.stroke_color + '" class="form-control color-chooser">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Stroke width') + '</label>';
	ui += 			'<input id="point-stroke-width" type="number" class="form-control" value="' + parseInt(this.style.point.stroke_width) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	//ui += 	'<div class="row">';
	//ui += 		'<div class="col-md-12 form-group">';
	//ui += 			'<label style="display: block;">' + gettext('Stroke opacity') + '<span id="point-stroke-opacity-output" class="margin-l-15 gol-slider-output">' + (this.style.point.stroke_opacity * 100) + '%</span>' + '</label>';
	//ui += 			'<div id="point-stroke-opacity"></div>';
	//ui += 		'</div>';					 
	//ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

StyleSettings.prototype.getLineTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane" id="line-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Stroke color') + '</label>';
	ui += 			'<input id="line-stroke-color" type="color" value="' + this.style.line.stroke_color + '" class="form-control color-chooser">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Stroke width') + '</label>';
	ui += 			'<input id="line-stroke-width" type="number" class="form-control" value="' + parseInt(this.style.line.stroke_width) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	//ui += 	'<div class="row">';
	//ui += 		'<div class="col-md-12 form-group">';
	//ui += 			'<label style="display: block;">' + gettext('Stroke opacity') + '<span id="line-stroke-opacity-output" class="margin-l-15 gol-slider-output">' + (this.style.line.stroke_opacity * 100) + '%</span>' + '</label>';
	//ui += 			'<div id="line-stroke-opacity"></div>';
	//ui += 		'</div>';					 
	//ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Select pattern') + '</label>';
	ui += 			'<select id="line-dash-array" class="form-control">';
	for (var i=0; i < this.linePatterns.length; i++) {
		if (this.linePatterns[i].value == this.style.line.stroke_dash_array) {
			ui += '<option value="' + this.linePatterns[i].value + '" data-imagesrc="' + this.linePatterns[i].imgsrc + '" selected></option>';
		} else {
			ui += '<option value="' + this.linePatterns[i].value + '" data-imagesrc="' + this.linePatterns[i].imgsrc + '"></option>';
		}
	}
	ui += 			'</select>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

StyleSettings.prototype.getArrowTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane" id="arrow-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Stroke color') + '</label>';
	ui += 			'<input id="arrow-stroke-color" type="color" value="' + this.style.arrow.stroke_color + '" class="form-control color-chooser">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Stroke width') + '</label>';
	ui += 			'<input id="arrow-stroke-width" type="number" class="form-control" value="' + parseInt(this.style.arrow.stroke_width) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	//ui += 	'<div class="row">';
	//ui += 		'<div class="col-md-12 form-group">';
	//ui += 			'<label style="display: block;">' + gettext('Stroke opacity') + '<span id="arrow-stroke-opacity-output" class="margin-l-15 gol-slider-output">' + (this.style.arrow.stroke_opacity * 100) + '%</span>' + '</label>';
	//ui += 			'<div id="arrow-stroke-opacity"></div>';
	//ui += 		'</div>';					 
	//ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Select pattern') + '</label>';
	ui += 			'<select id="arrow-dash-array" class="form-control">';
	for (var i=0; i < this.linePatterns.length; i++) {
		if (this.linePatterns[i].value == this.style.arrow.stroke_dash_array) {
			ui += '<option value="' + this.linePatterns[i].value + '" data-imagesrc="' + this.linePatterns[i].imgsrc + '" selected></option>';
		} else {
			ui += '<option value="' + this.linePatterns[i].value + '" data-imagesrc="' + this.linePatterns[i].imgsrc + '"></option>';
		}
	}
	ui += 			'</select>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

StyleSettings.prototype.getPolygonTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane" id="polygon-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Fill color') + '</label>';
	ui += 			'<input id="polygon-fill-color" type="color" value="' + this.style.polygon.fill_color + '" class="form-control color-chooser">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label style="display: block;">' + gettext('Fill opacity') + '<span id="polygon-fill-opacity-output" class="margin-l-15 gol-slider-output">' + (this.style.polygon.fill_opacity * 100) + '%</span>' + '</label>';
	ui += 			'<div id="polygon-fill-opacity"></div>';
	ui += 		'</div>';				 
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Stroke color') + '</label>';
	ui += 			'<input id="polygon-stroke-color" type="color" value="' + this.style.polygon.stroke_color + '" class="form-control color-chooser">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Stroke width') + '</label>';
	ui += 			'<input id="polygon-stroke-width" type="number" class="form-control" value="' + parseInt(this.style.polygon.stroke_width) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	//ui += 	'<div class="row">';
	//ui += 		'<div class="col-md-12 form-group">';
	//ui += 			'<label style="display: block;">' + gettext('Stroke opacity') + '<span id="polygon-stroke-opacity-output" class="margin-l-15 gol-slider-output">' + (this.style.polygon.stroke_opacity * 100) + '%</span>' + '</label>';
	//ui += 			'<div id="polygon-stroke-opacity"></div>';
	//ui += 		'</div>';					 
	//ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

StyleSettings.prototype.getTextTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane" id="text-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Font size') + '</label>';
	ui += 			'<input id="text-font-size" type="number" class="form-control" value="' + parseInt(this.style.text.font_size) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Fill color') + '</label>';
	ui += 			'<input id="text-fill-color" type="color" value="' + this.style.text.fill_color + '" class="form-control color-chooser">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Stroke color') + '</label>';
	ui += 			'<input id="text-stroke-color" type="color" value="' + this.style.text.stroke_color + '" class="form-control color-chooser">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Stroke width') + '</label>';
	ui += 			'<input id="text-stroke-width" type="number" class="form-control" value="' + parseInt(this.style.text.stroke_width) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

StyleSettings.prototype.registerEvents = function() {
	var self = this;
	
	$("#graphic-size").on('change', function(e) {
		self.style.point.size = this.value;
	});

	$("#well-known-name").on('change', function(e) {
		self.style.point.well_known_name = this.value;
	});
	$( "#point-fill-opacity" ).slider({
	    min: 0,
	    max: 100,
	    value: (self.style.point.fill_opacity * 100),
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.style.point.fill_opacity = opacity;
	    },
	    slide: function( event, ui ) {
	    	$("#point-fill-opacity-output").text(ui.value + '%');
	    }
	});	
	$("#point-fill-color").on('change', function(e) {
		self.style.point.fill_color = this.value;
	});	
	$("#point-stroke-color").on('change', function(e) {
		self.style.point.stroke_color = this.value;
	});
	/*$( "#point-stroke-opacity" ).slider({
	    min: 0,
	    max: 100,
	    value: (self.style.point.stroke_opacity * 100),
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.style.point.stroke_opacity = opacity;
	    },
	    slide: function( event, ui ) {
	    	$("#point-stroke-opacity-output").text(ui.value + '%');
	    }
	});*/
	$("#point-stroke-width").on('change', function(e) {
		self.style.point.stroke_width = this.value;
	});
	
	
	
	
	$("#line-stroke-color").on('change', function(e) {
		self.style.line.stroke_color = this.value;
	});
	/*$( "#line-stroke-opacity" ).slider({
	    min: 0,
	    max: 100,
	    value: (self.style.line.stroke_opacity * 100),
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.style.line.stroke_opacity = opacity;
	    },
	    slide: function( event, ui ) {
	    	$("#line-stroke-opacity-output").text(ui.value + '%');
	    }
	});*/
	$("#line-stroke-width").on('change', function(e) {
		self.style.line.stroke_width = this.value;
	});
	$('#line-dash-array').ddslick({
	    onSelected: function(selectedData){
	    	self.style.line.stroke_dash_array = selectedData.selectedData.value;
	    }   
	});
	
	
	
	$("#arrow-stroke-color").on('change', function(e) {
		self.style.arrow.stroke_color = this.value;
	});
	/*$( "#arrow-stroke-opacity" ).slider({
	    min: 0,
	    max: 100,
	    value: (self.style.arrow.stroke_opacity * 100),
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.style.arrow.stroke_opacity = opacity;
	    },
	    slide: function( event, ui ) {
	    	$("#arrow-stroke-opacity-output").text(ui.value + '%');
	    }
	});*/
	$("#arrow-stroke-width").on('change', function(e) {
		self.style.arrow.stroke_width = this.value;
	});
	$('#arrow-dash-array').ddslick({
	    onSelected: function(selectedData){
	    	self.style.arrow.stroke_dash_array = selectedData.selectedData.value;
	    }   
	});
	
	
	
	$( "#polygon-fill-opacity" ).slider({
	    min: 0,
	    max: 100,
	    value: (self.style.polygon.fill_opacity * 100),
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.style.polygon.fill_opacity = opacity;
	    },
	    slide: function( event, ui ) {
	    	$("#polygon-fill-opacity-output").text(ui.value + '%');
	    }
	});	
	$("#polygon-fill-color").on('change', function(e) {
		self.style.polygon.fill_color = this.value;
	});	
	$("#polygon-stroke-color").on('change', function(e) {
		self.style.polygon.stroke_color = this.value;
	});
	/*$( "#polygon-stroke-opacity" ).slider({
	    min: 0,
	    max: 100,
	    value: (self.style.polygon.stroke_opacity * 100),
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.style.polygon.stroke_opacity = opacity;
	    },
	    slide: function( event, ui ) {
	    	$("#polygon-stroke-opacity-output").text(ui.value + '%');
	    }
	});*/
	$("#polygon-stroke-width").on('change', function(e) {
		self.style.polygon.stroke_width = this.value;
	});
	
	
	$("#text-font-size").on('change', function(e) {
		self.style.text.font_size = this.value;
	});	
	$("#text-fill-color").on('change', function(e) {
		self.style.text.fill_color = this.value;
	});	
	$("#text-stroke-color").on('change', function(e) {
		self.style.text.stroke_color = this.value;
	});
	$("#text-stroke-width").on('change', function(e) {
		self.style.text.stroke_width = this.value;
	});
};

StyleSettings.prototype.getStyle = function() {
	return this.style;
};

StyleSettings.prototype.addPointPrintStyle = function(point, styleName) {
	this.pointPrintStyles["[style_name='" + styleName + "']"] = {
		symbolizers: [{
			"type" : "point",
			"fillColor": point.fill_color,
			"fillOpacity": point.fill_opacity,
			"graphicName": point.well_known_name,
			"pointRadius": point.size,
			"strokeColor": point.stroke_color,
			"strokeWidth": point.stroke_width
		}]
	};
};

StyleSettings.prototype.addLinePrintStyle = function(line, styleName) {
	this.linePrintStyles["[style_name='" + styleName + "']"] = {
		symbolizers: [{
			"type" : "line",
			"strokeColor": line.stroke_color,
			"strokeWidth": line.stroke_width,
		}]
	};
};

StyleSettings.prototype.addArrowPrintStyle = function(arrow, styleName) {
	this.arrowPrintStyles["[style_name='" + styleName + "']"] = {
		symbolizers: [{
			"type" : "line",
			"strokeColor": arrow.stroke_color,
			"strokeWidth": arrow.stroke_width,
		}]
	};
};

StyleSettings.prototype.addPolygonPrintStyle = function(polygon, styleName) {
	this.polygonPrintStyles["[style_name='" + styleName + "']"] = {
		symbolizers: [{
			"type" : "polygon",
			"fillColor": polygon.fill_color,
			"fillOpacity": polygon.fill_opacity,
			"strokeColor": polygon.stroke_color,
			"strokeWidth": polygon.stroke_width,
		}]
	};
};

StyleSettings.prototype.addTextPrintStyle = function(text, styleName) {
	this.textPrintStyles["[style_name='" + styleName + "']"] = {
		symbolizers: [{
			"type" : "text",
			"fontColor": text.fill_color,
			"haloColor": text.stoke_color,
		    "haloRadius": text.stroke_width,
			"fontFamily": "sans-serif",
			"fontSize": text.font_size + "px",
			"fontStyle": "normal",
			"label": '[text]',
		}]
	};
};

StyleSettings.prototype.getPointPrintStyles = function() {
	return this.pointPrintStyles;
};

StyleSettings.prototype.getLinePrintStyles = function() {
	return this.linePrintStyles;
};

StyleSettings.prototype.getArrowPrintStyles = function() {
	return this.arrowPrintStyles;
};

StyleSettings.prototype.getPolygonPrintStyles = function() {
	return this.polygonPrintStyles;
};

StyleSettings.prototype.getTextPrintStyles = function() {
	return this.textPrintStyles;
};

StyleSettings.prototype.show = function() {
	$("#float-draw-modal").modal('show');
};

StyleSettings.prototype.hide = function() {
	$("#float-draw-modal").modal('hide');
};