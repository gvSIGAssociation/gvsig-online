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
 
 
var ColorMapEntry = function(rule, options, utils) {
	this.id = 'colormapentry' + utils.generateUUID();
	this.type = 'ColorMapEntry';
	this.color = '#383838';
	this.quantity = 0;
	this.label = 'label';
	this.opacity = 0.5;
	this.order = 0;
	this.rule = rule;
	this.utils = utils;
	
	if (options) {
		$.extend(this, options);
	}
};

ColorMapEntry.prototype.getTableUI = function() {
	var ui = '';
	ui += '<tr data-rowid="' + this.id + '">';
	ui += 	'<td>'
	ui += 		'<span class="handle"> ';
	ui += 			'<i class="fa fa-ellipsis-v"></i>';
	ui += 			'<i class="fa fa-ellipsis-v"></i>';
	ui += 		'</span>';
	ui += 	'</td>';
	ui += 	'<td id="color-map-entry-preview-div-' + this.id + '"></td>';
	ui += 	'<td id="color-map-entry-preview-quantity-' + this.id + '">' + this.quantity + '</td>';
	ui += 	'<td id="color-map-entry-preview-label-' + this.id + '">' + this.label + '</td>';
	ui += 	'<td id="color-map-entry-preview-opacity-' + this.id + '">' + this.opacity + '</td>';
	ui += 	'<td><a class="edit-color-map-entry-link-' + this.rule.id + '" data-colormapentryid="' + this.id + '" href="javascript:void(0)"><i class="fa fa-edit text-primary"></i></a></td>';
	ui += 	'<td><a class="delete-color-map-entry-link-' + this.rule.id + '" data-colormapentryid="' + this.id + '" href="javascript:void(0)"><i class="fa fa-times text-danger"></i></a></td>';
	ui += '</tr>';	
	
	return ui;
};

ColorMapEntry.prototype.getTabMenu = function() {
	var ui = '';
	ui += '<li class="active"><a href="#color-map-entry-tab" data-toggle="tab">' + gettext('Color map entry') + '</a></li>';
	
	return ui;	
};

ColorMapEntry.prototype.getColorMapEntryTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane active" id="color-map-entry-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Color') + '</label>';
	ui += 			'<input id="color-chooser" type="color" value="' + this.color + '" class="form-control color-chooser">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Quantity') + '</label>';
	ui += 			'<input id="quantity" type="number" class="form-control" value="' + parseInt(this.quantity) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Label') + '</label>';
	ui += 			'<input id="entry-label" type="text" class="form-control" value="' + this.label + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label style="display: block;">' + gettext('Opacity') + '<span id="opacity-output" class="margin-l-15 gol-slider-output">' + (this.opacity * 100) + '%</span>' + '</label>';
	ui += 			'<div id="opacity-slider"><div/>';
	ui += 		'</div>';				 
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

ColorMapEntry.prototype.registerEvents = function() {
	var self = this;

	$("#color-chooser").on('change', function(e) {
		self.color = this.value;
		self.updatePreview();	
	});	
	
	$( "#opacity-slider" ).slider({
	    min: 0,
	    max: 100,
	    value: (self.opacity * 100),
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.opacity = opacity;
	    	$("#color-map-entry-preview-opacity-" + self.id).text(opacity);
	    	self.updatePreview();
	    },
	    slide: function( event, ui ) {
	    	$("#opacity-output").text(ui.value + '%');
	    }
	});	
	
	$("#quantity").on('change', function(e) {
		self.quantity = this.value;
		$("#color-map-entry-preview-quantity-" + self.id).text(this.value);
		self.updatePreview();	
	});
	
	$("#entry-label").on('change', function(e) {
		self.label = this.value;
		$("#color-map-entry-preview-label-" + self.id).text(this.value);
		self.updatePreview();	
	});
};

ColorMapEntry.prototype.updatePreview = function() {	
	var sldBody = this.toSLDBody();
	var url = this.utils.getPreviewUrl() + '&SLD_BODY=' + encodeURIComponent(sldBody);
	var ui = '<img id="color-map-entry-preview-' + this.id + '" src="' + url + '" class="symbolizer-preview-' + this.id + '"></img>';
	$("#color-map-entry-preview-div-" + this.id).empty();
	$("#color-map-entry-preview-div-" + this.id).append(ui);
};

ColorMapEntry.prototype.toSLDBody = function(){
	
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
	sld += 							'<CssParameter name="fill">' + this.color + '</CssParameter>';
	sld += 							'<CssParameter name="fill-opacity">' + this.opacity + '</CssParameter>';
	sld += 						'</Fill>';
	sld += 						'<Stroke>';
	sld += 							'<CssParameter name="stroke">' + this.color + '</CssParameter>';
	sld += 							'<CssParameter name="stroke-width">1</CssParameter>';
	sld += 							'<CssParameter name="stroke-opacity">' + this.opacity + '</CssParameter>';
	sld += 						'</Stroke>';
	sld += 					'</PolygonSymbolizer>';
	sld +=          	'</Rule>';
	sld +=          '</FeatureTypeStyle>';
	sld +=      '</UserStyle>';
	sld += 	'</NamedLayer>';
	sld += '</StyledLayerDescriptor>';
	
	return sld;
};

ColorMapEntry.prototype.toJSON = function(){
	
	var object = {
		id: this.id,
		type: this.type,
		order: this.order,
		color: this.color,
		quantity: this.quantity,
		label: this.label,
		opacity: this.opacity
	};
	
	return JSON.stringify(object);
};