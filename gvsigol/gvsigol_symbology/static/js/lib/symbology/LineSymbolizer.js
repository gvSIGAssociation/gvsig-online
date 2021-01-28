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
 
 
var LineSymbolizer = function(rule, options, utils) {
	this.id = 'linesymbolizer' + utils.generateUUID();
	this.stroke = "#000000";
	this.stroke_width = 1;
	this.stroke_dash_array = 'none';
	this.stroke_opacity = 1;
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
	this.type = 'LineSymbolizer';
};

LineSymbolizer.prototype.getTableUI = function() {
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

LineSymbolizer.prototype.getTabMenu = function() {
	var ui = '';
	ui += '<li class="active"><a href="#stroke-tab" data-toggle="tab">' + gettext('Stroke') + '</a></li>';
	
	return ui;	
};

LineSymbolizer.prototype.getStrokeTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane active" id="stroke-tab">';
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

LineSymbolizer.prototype.registerEvents = function() {
	var self = this;
	
	$('#line-dash-array').ddslick({
	    onSelected: function(selectedData){
	    	self.stroke_dash_array = selectedData.selectedData.value;
	    	self.updatePreview();	
			self.rule.preview();
	    }   
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
};

LineSymbolizer.prototype.updatePreview = function() {	
	var sldBody = this.toSLDBody();
	var url = this.utils.getPreviewUrl() + '&SLD_BODY=' + encodeURIComponent(sldBody);
	var ui = '<img id="symbolizer-preview-' + this.id + '" src="' + url + '" class="symbolizer-preview-' + this.id + '"></img>';
	$("#symbolizer-preview-div-" + this.id).empty();
	$("#symbolizer-preview-div-" + this.id).append(ui);
};

LineSymbolizer.prototype.toXML = function(){
	
	var xml = '';
	xml += '<LineSymbolizer>';
	xml += 	'<Stroke>';
	xml += 		'<CssParameter name="stroke">' + this.stroke + '</CssParameter>';
	xml += 		'<CssParameter name="stroke-width">' + this.stroke_width + '</CssParameter>';
	xml += 		'<CssParameter name="stroke-opacity">' + this.stroke_opacity + '</CssParameter>';
	if (this.stroke_dash_array != 'none') {
		xml += '<CssParameter name="stroke-dasharray">' + this.stroke_dash_array + '</CssParameter>;'
	}
	xml += 	'</Stroke>';
	xml += '</LineSymbolizer>';
	
	return xml;
};

LineSymbolizer.prototype.toSLDBody = function(){
	
	var sld = '';
	sld += '<StyledLayerDescriptor version=\"1.0.0\" xmlns=\"http://www.opengis.net/sld\" xmlns:ogc=\"http://www.opengis.net/ogc\" ';
	sld +=  'xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" ';
	sld +=  'xsi:schemaLocation=\"http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd\">';
	sld += 	'<NamedLayer>';  
	sld +=  	'<Name>Line</Name>';  
	sld +=      '<UserStyle>';
	sld +=          '<Name>Line</Name>';
	sld +=          '<Title>Line</Title>';
	sld +=          '<FeatureTypeStyle>';
	sld +=          	'<Rule>';
	sld +=          		'<Name>Line</Name>';
	sld +=          		'<Title>Line</Title>';
	sld += 					'<LineSymbolizer>';
	sld += 						'<Stroke>';
	sld += 							'<CssParameter name="stroke">' + this.stroke + '</CssParameter>';
	sld += 							'<CssParameter name="stroke-width">' + this.stroke_width + '</CssParameter>';
	sld += 							'<CssParameter name="stroke-opacity">' + this.stroke_opacity + '</CssParameter>';
	if (this.stroke_dash_array != 'none') {
		sld += '<CssParameter name="stroke-dasharray">' + this.stroke_dash_array + '</CssParameter>;'
	}
	sld += 						'</Stroke>';
	sld += 					'</LineSymbolizer>';
	sld +=          	'</Rule>';
	sld +=          '</FeatureTypeStyle>';
	sld +=      '</UserStyle>';
	sld += 	'</NamedLayer>';
	sld += '</StyledLayerDescriptor>';
	
	return sld;
};

LineSymbolizer.prototype.toJSON = function(){
	
	var object = {
		id: this.id,
		type: this.type,
		stroke: this.stroke,
		stroke_width: this.stroke_width,
		stroke_opacity: this.stroke_opacity,
		stroke_dash_array: this.stroke_dash_array,
		order: this.order
	};
	
	return JSON.stringify(object);
};