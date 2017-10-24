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
 
 
var MarkSymbolizer = function(rule, options, utils) {
	this.id = 'marksymbolizer' + utils.generateUUID();
	this.well_known_name = 'circle';
	this.fill = "#000000";
	this.fill_opacity = 0.5;
	this.stroke = "#000000";
	this.stroke_width = 1;
	this.stroke_opacity = 1;
	this.stroke_dash_array = 'none';
	this.rotation = 0;
	this.order = 0;
	this.size = 10;
	this.opacity = 1;
	this.rule = rule;
	this.utils = utils;
	
	if (options) {
		$.extend(this, options);
	} else {
		if(rule && rule.symbolizers){
			this.order = rule.symbolizers.length;
		}
	}
	this.type = 'MarkSymbolizer';
};

MarkSymbolizer.prototype.getTableUI = function() {
	var ui = '';
	ui += '<tr data-rowid="' + this.id + '">';
	ui += 	'<td>'
	ui += 		'<span class="handle"> ';
	ui += 			'<i class="fa fa-ellipsis-v"></i>';
	ui += 			'<i class="fa fa-ellipsis-v"></i>';
	ui += 		'</span>';
	ui += 	'</td>';
	ui += 	'<td id="symbolizer-preview-div-' + this.id + '"></td>';	
	ui += 	'<td><a class="edit-symbolizer-link-' + this.rule.id + '" data-symbolizerid="' + this.id + '" href="javascript:void(0)"><i class="fa fa-edit text-primary"></i></a></td>';
	ui += 	'<td><a class="delete-symbolizer-link-' + this.rule.id + '" data-symbolizerid="' + this.id + '" href="javascript:void(0)"><i class="fa fa-times text-danger"></i></a></td>';
	ui += '</tr>';	
	
	return ui;
};

MarkSymbolizer.prototype.getTabMenu = function() {
	var ui = '';
	ui += '<li class="active"><a href="#graphic-tab" data-toggle="tab">' + gettext('Graphic') + '</a></li>';
	ui += '<li><a href="#fill-tab" data-toggle="tab">' + gettext('Fill') + '</a></li>';
	ui += '<li><a href="#stroke-tab" data-toggle="tab">' + gettext('Stroke') + '</a></li>';
	ui += '<li><a href="#rotation-tab" data-toggle="tab">' + gettext('Rotation') + '</a></li>';
	
	return ui;	
};

MarkSymbolizer.prototype.getGraphicTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane active" id="graphic-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Select shape') + '</label>';
	ui += 			'<select id="well-known-name" class="form-control">';
	for (var i=0; i < this.utils.shapes.length; i++) {
		if (this.utils.shapes[i].value == this.well_known_name) {
			ui += '<option value="' + this.utils.shapes[i].value + '" selected>' + this.utils.shapes[i].title + '</option>';
		} else {
			ui += '<option value="' + this.utils.shapes[i].value + '">' + this.utils.shapes[i].title + '</option>';
		}
	}
	ui += 			'</select>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Size') + '</label>';
	ui += 			'<input id="graphic-size" type="number" class="form-control" value="' + parseInt(this.size) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

MarkSymbolizer.prototype.getFillTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane" id="fill-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Fill color') + '</label>';
	ui += 			'<input id="fill-color-chooser" type="color" value="' + this.fill + '" class="form-control color-chooser">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label style="display: block;">' + gettext('Fill opacity') + '<span id="fill-opacity-output" class="margin-l-15 gol-slider-output">' + (this.fill_opacity * 100) + '%</span>' + '</label>';
	ui += 			'<div id="fill-opacity-slider"><div/>';
	ui += 		'</div>';				 
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

MarkSymbolizer.prototype.getStrokeTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane" id="stroke-tab">';
	ui += 		'<div class="row">';
	ui += 			'<div class="col-md-12 form-group">';
	ui += 				'<label>' + gettext('Stroke color') + '</label>';
	ui += 				'<input id="stroke-color-chooser" type="color" value="' + this.stroke + '" class="form-control color-chooser">';					
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 		'<div class="row">';
	ui += 			'<div class="col-md-12 form-group">';
	ui += 				'<label>' + gettext('Stroke width') + '</label>';
	ui += 				'<input id="stroke-width" type="number" class="form-control" value="' + parseInt(this.stroke_width) + '">';					
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 		'<div class="row">';
	ui += 			'<div class="col-md-12 form-group">';
	ui += 				'<label style="display: block;">' + gettext('Stroke opacity') + '<span id="stroke-opacity-output" class="margin-l-15 gol-slider-output">' + (this.stroke_opacity * 100) + '%</span>' + '</label>';
	ui += 				'<div id="stroke-opacity-slider"></div>';
	ui += 			'</div>';					 
	ui += 		'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Select pattern') + '</label>';
	ui += 			'<select id="line-dash-array" class="form-control">';
	for (var i=0; i < this.utils.linePatterns.length; i++) {
		if (this.utils.linePatterns[i].value == this.stroke_dash_array) {
			ui += '<option value="' + this.utils.linePatterns[i].value + '" data-imagesrc="' + this.utils.linePatterns[i].imgsrc + '" selected></option>';
		} else {
			ui += '<option value="' + this.utils.linePatterns[i].value + '" data-imagesrc="' + this.utils.linePatterns[i].imgsrc + '"></option>';
		}
	}
	ui += 			'</select>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

MarkSymbolizer.prototype.getRotationTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane" id="rotation-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label style="display: block;">' + gettext('Rotation') + '<span id="rotation-output" class="margin-l-15 gol-slider-output">' + this.rotation + 'º</span>' + '</label>';
	ui += 			'<div id="rotation-slider"><div/>';
	ui += 		'</div>';			 
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

MarkSymbolizer.prototype.registerEvents = function() {
	var self = this;
	
	$("#graphic-size").on('change', function(e) {
		self.size = this.value;
		self.updatePreview();	
		self.rule.preview();
	});

	$("#well-known-name").on('change', function(e) {
		self.well_known_name = this.value;
		self.updatePreview();	
		self.rule.preview();
	});
	$( "#fill-opacity-slider" ).slider({
	    min: 0,
	    max: 100,
	    value: (self.fill_opacity * 100),
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.fill_opacity = opacity;
	    	self.updatePreview();
	    	self.rule.preview();
	    },
	    slide: function( event, ui ) {
	    	$("#fill-opacity-output").text(ui.value + '%');
	    }
	});	
	$("#fill-color-chooser").on('change', function(e) {
		self.fill = this.value;
		self.updatePreview();	
		self.rule.preview();
	});	
	$("#stroke-color-chooser").on('change', function(e) {
		self.stroke = this.value;
		self.updatePreview();	
		self.rule.preview();
	});
	$( "#stroke-opacity-slider" ).slider({
	    min: 0,
	    max: 100,
	    value: (self.stroke_opacity * 100),
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.stroke_opacity = opacity;
	    	self.updatePreview();
	    	self.rule.preview();
	    },
	    slide: function( event, ui ) {
	    	$("#stroke-opacity-output").text(ui.value + '%');
	    }
	});
	$("#stroke-width").on('change', function(e) {
		self.stroke_width = this.value;
		self.updatePreview();	
		self.rule.preview();
	});
	
	$('#line-dash-array').ddslick({
	    onSelected: function(selectedData){
	    	self.stroke_dash_array = selectedData.selectedData.value;
	    	self.updatePreview();	
			self.rule.preview();
	    }   
	});
	
	$( "#rotation-slider" ).slider({
	    min: 0,
	    max: 360,
	    value: self.rotation,
	    slide: function( event, ui ) {
	    	var rotation = ui.value;
	    	$("#rotation-output").text(rotation + 'º');
	    	self.rotation = rotation;
	    }
	});
};

MarkSymbolizer.prototype.updatePreview = function() {	
	var sldBody = this.toSLDBody();
	if(sldBody != null){
		var url = this.utils.getPreviewUrl() + '&SLD_BODY=' + encodeURIComponent(sldBody);
		var ui = '<img id="symbolizer-preview-' + this.id + '" src="' + url + '" class="symbolizer-preview-' + this.id + '"></img>';
		$("#symbolizer-preview-div-" + this.id).empty();
		$("#symbolizer-preview-div-" + this.id).append(ui);
	}
};

MarkSymbolizer.prototype.sld2 = function() {
	var rules = new Array();
	
	var style = {
			name: 'point',
			title: 'point',
			is_default:true,
			rules: rules
	};
	
	var l = {
			type: this.type,
			json: this.toJSON(),
			order: 1
	};
	var options = {
			"id" : 1,
			"name" : 'point',
			"title" : 'point',
			"abstract" : "",
			"is_default": true,
			"order" :  1
	}
	var auxrule = new Rule(1, 'point', 'point', options, this.utils);
	var rule = {
			rule: auxrule.getObject(),
			symbolizers: [l]
	};
	style.rules.push(rule);
	
	var layerId = this.utils.getLayerId();
	
	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/create_sld/",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		data: {
			type: this.utils.type,
			layer_id: layerId,
			style_data: JSON.stringify(style)
		},
		success: function(response){
			if (response.success) {
				return response.sld;
			} else {
				alert('Error');
				return null;
			}

		},
		error: function(){
			return null;
		}
	});
	return null;
};


MarkSymbolizer.prototype.toXML = function(){
	
	var xml = '';
	xml += '<PointSymbolizer>';
	xml += 	'<Graphic>';
	xml += 		'<Mark>';
	xml += 			'<WellKnownName>' + this.well_known_name + '</WellKnownName>';
	xml += 			'<Fill>';
	xml += 				'<CssParameter name="fill">' + this.fill + '</CssParameter>';
	xml += 				'<CssParameter name="fill-opacity">' + this.fill_opacity + '</CssParameter>';
	xml += 			'</Fill>';
	xml += 			'<Stroke>';
	xml += 				'<CssParameter name="stroke">' + this.stroke + '</CssParameter>';
	xml += 				'<CssParameter name="stroke-width">' + this.stroke_width + '</CssParameter>';
	xml += 				'<CssParameter name="stroke-opacity">' + this.stroke_opacity + '</CssParameter>';
	if (this.stroke_dash_array != 'none') {
		xml += '<CssParameter name="stroke-dasharray">' + this.stroke_dash_array + '</CssParameter>;'
	}
	xml += 			'</Stroke>';
	xml += 		'</Mark>';
	xml += 		'<Opacity>1</Opacity>';
	xml += 		'<Size>' + this.size + '</Size>';
	xml += 		'<Rotation>0</Rotation>';
	xml += 	'</Graphic>';
	xml += '</PointSymbolizer>';
	
	return xml;
};

MarkSymbolizer.prototype.toSLDBody = function(){
	
	var sld = '';
	sld += '<StyledLayerDescriptor version=\"1.0.0\" xmlns=\"http://www.opengis.net/sld\" xmlns:ogc=\"http://www.opengis.net/ogc\" ';
	sld +=  'xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" ';
	sld +=  'xsi:schemaLocation=\"http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd\">';
	sld += 	'<NamedLayer>';  
	sld +=  	'<Name>Mark</Name>';  
	sld +=      '<UserStyle>';
	sld +=          '<Name>Mark</Name>';
	sld +=          '<Title>Mark</Title>';
	sld +=          '<FeatureTypeStyle>';
	sld +=          	'<Rule>';
	sld +=          		'<Name>Mark</Name>';
	sld +=          		'<Title>Mark</Title>';
	sld += 					'<PointSymbolizer>';
	sld += 						'<Graphic>';
	sld += 							'<Mark>';
	sld += 								'<WellKnownName>' + this.well_known_name + '</WellKnownName>';
	sld += 								'<Fill>';
	sld += 									'<CssParameter name="fill">' + this.fill + '</CssParameter>';
	sld += 									'<CssParameter name="fill-opacity">' + this.fill_opacity + '</CssParameter>';
	sld += 								'</Fill>';
	sld += 								'<Stroke>';
	sld += 									'<CssParameter name="stroke">' + this.stroke + '</CssParameter>';
	sld += 									'<CssParameter name="stroke-width">' + this.stroke_width + '</CssParameter>';
	sld += 									'<CssParameter name="stroke-opacity">' + this.stroke_opacity + '</CssParameter>';
	if (this.stroke_dash_array != 'none') {
		sld += '<CssParameter name="stroke-dasharray">' + this.stroke_dash_array + '</CssParameter>;'
	}
	sld += 								'</Stroke>';
	sld += 							'</Mark>';
	sld += 							'<Opacity>1</Opacity>';
	sld += 							'<Size>' + this.size + '</Size>';
	sld += 							'<Rotation>0</Rotation>';
	sld += 						'</Graphic>';
	sld += 					'</PointSymbolizer>';
	sld +=          	'</Rule>';
	sld +=          '</FeatureTypeStyle>';
	sld +=      '</UserStyle>';
	sld += 	'</NamedLayer>';
	sld += '</StyledLayerDescriptor>';
	
	return sld;
};

MarkSymbolizer.prototype.toJSON = function(){
	
	var object = {
		id: this.id,
		type: this.type,
		well_known_name: this.well_known_name,
		fill: this.fill,
		fill_opacity: this.fill_opacity,
		stroke: this.stroke,
		stroke_width: this.stroke_width,
		stroke_opacity: this.stroke_opacity,
		stroke_dash_array: this.stroke_dash_array,
		rotation: this.rotation,
		order: this.order,
		size: this.size,
		opacity: this.opacity
	};
	
	return JSON.stringify(object);
};