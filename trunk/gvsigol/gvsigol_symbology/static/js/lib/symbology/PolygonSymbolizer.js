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
 
 
var PolygonSymbolizer = function(rule, options, utils) {
	this.id = 'polygonsymbolizer' + utils.generateUUID();
	this.fill = "#000000";
	this.fill_opacity = 0.5;
	this.stroke = "#000000";
	this.stroke_width = 1;
	this.stroke_opacity = 1;
	this.stroke_dash_array = 'none';
	this.order = 0;
	this.rule = rule;
	this.utils = utils;
	
	if (options) {
		$.extend(this, options);
	} else {
		if(rule && rule.symbolizers){
			this.order = rule.symbolizers.length;
		}
	}
	this.type = 'PolygonSymbolizer';
};

PolygonSymbolizer.prototype.getTableUI = function() {
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

PolygonSymbolizer.prototype.getTabMenu = function() {
	var ui = '';
	ui += '<li class="active"><a href="#fill-tab" data-toggle="tab">' + gettext('Fill') + '</a></li>';
	ui += '<li><a href="#stroke-tab" data-toggle="tab">' + gettext('Stroke') + '</a></li>';
	
	return ui;	
};

PolygonSymbolizer.prototype.getFillTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane active" id="fill-tab">';
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

PolygonSymbolizer.prototype.getStrokeTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane" id="stroke-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Stroke color') + '</label>';
	ui += 			'<input id="stroke-color-chooser" type="color" value="' + this.stroke + '" class="form-control color-chooser">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Stroke width') + '</label>';
	ui += 			'<input id="stroke-width" type="number" class="form-control" value="' + parseInt(this.stroke_width) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label style="display: block;">' + gettext('Stroke opacity') + '<span id="stroke-opacity-output" class="margin-l-15 gol-slider-output">' + (this.stroke_opacity * 100) + '%</span>' + '</label>';
	ui += 			'<div id="stroke-opacity-slider"></div>';
	ui += 		'</div>';					 
	ui += 	'</div>';
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

PolygonSymbolizer.prototype.registerEvents = function() {
	var self = this;

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
};

PolygonSymbolizer.prototype.updatePreview = function() {	
	var sldBody = this.toSLDBody();
	if(sldBody != null){
		var url = this.utils.getPreviewUrl() + '&SLD_BODY=' + encodeURIComponent(sldBody);
		var ui = '<img id="symbolizer-preview-' + this.id + '" src="' + url + '" class="symbolizer-preview-' + this.id + '"></img>';
		$("#symbolizer-preview-div-" + this.id).empty();
		$("#symbolizer-preview-div-" + this.id).append(ui);
	}
};

PolygonSymbolizer.prototype.sld = function() {
	var rules = new Array();
	
	var style = {
			name: 'polygon',
			title: 'polygon',
			rules: rules
	};
	
	var l = {
			type: this.type,
			json: this.toJSON(),
			order: 1
	};
	var options = {
			"id" : 1,
			"name" : 'polygon',
			"title" : 'polygon',
			"abstract" : "",
			"order" :  1
	}
	var auxrule = new Rule(1, 'polygon', 'polygon', options, this.utils);
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
			xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
		},
		data: {
			type: 'EX',
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


PolygonSymbolizer.prototype.toSLDBody = function(){
	
	var sld = '';
	sld += '<StyledLayerDescriptor version=\"1.0.0\" xmlns=\"http://www.opengis.net/sld\" xmlns:ogc=\"http://www.opengis.net/ogc\" ';
	sld +=  'xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" ';
	sld +=  'xsi:schemaLocation=\"http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd\">';
	sld += 	'<NamedLayer>';  
	sld +=  	'<Name>polygon</Name>';  
	sld +=      '<UserStyle>';
	sld +=          '<Name>polygon</Name>';
	sld +=          '<Title>polygon</Title>';
	sld +=          '<FeatureTypeStyle>';
	sld +=          	'<Rule>';
	sld +=          		'<Name>polygon</Name>';
	sld +=          		'<Title>polygon</Title>';
	sld += 					'<PolygonSymbolizer>';
	sld += 						'<Fill>';
	sld += 							'<CssParameter name="fill">' + this.fill + '</CssParameter>';
	sld += 							'<CssParameter name="fill-opacity">' + this.fill_opacity + '</CssParameter>';
	sld += 						'</Fill>';
	sld += 						'<Stroke>';
	sld += 							'<CssParameter name="stroke">' + this.stroke + '</CssParameter>';
	sld += 							'<CssParameter name="stroke-width">' + this.stroke_width + '</CssParameter>';
	sld += 							'<CssParameter name="stroke-opacity">' + this.stroke_opacity + '</CssParameter>';
	if (this.stroke_dash_array != 'none') {
		sld += '<CssParameter name="stroke-dasharray">' + this.stroke_dash_array + '</CssParameter>;'
	}
	sld += 						'</Stroke>';
	sld += 					'</PolygonSymbolizer>';
	sld +=          	'</Rule>';
	sld +=          '</FeatureTypeStyle>';
	sld +=      '</UserStyle>';
	sld += 	'</NamedLayer>';
	sld += '</StyledLayerDescriptor>';
	
	return sld;
};

PolygonSymbolizer.prototype.toXML = function(){
	
	var xml = '';
	xml += '<PolygonSymbolizer>';
	xml += 	'<Fill>';
	xml += 		'<CssParameter name="fill">' + this.fill + '</CssParameter>';
	xml += 		'<CssParameter name="fill-opacity">' + this.fill_opacity + '</CssParameter>';
	xml += 	'</Fill>';
	xml += 	'<Stroke>';
	xml += 		'<CssParameter name="stroke">' + this.stroke + '</CssParameter>';
	xml += 		'<CssParameter name="stroke-width">' + this.stroke_width + '</CssParameter>';
	xml += 		'<CssParameter name="stroke-opacity">' + this.stroke_opacity + '</CssParameter>';
	if (this.stroke_dash_array != 'none') {
		xml += '<CssParameter name="stroke-dasharray">' + this.stroke_dash_array + '</CssParameter>;'
	}
	xml += 	'</Stroke>';
	xml += '</PolygonSymbolizer>';
	
	return xml;
};

PolygonSymbolizer.prototype.toJSON = function(){
	
	var object = {
		id: this.id,
		type: this.type,
		fill: this.fill,
		fill_opacity: this.fill_opacity,
		stroke: this.stroke,
		stroke_width: this.stroke_width,
		stroke_opacity: this.stroke_opacity,
		stroke_dash_array: this.stroke_dash_array,
		order: this.order
	};
	
	return JSON.stringify(object);
};