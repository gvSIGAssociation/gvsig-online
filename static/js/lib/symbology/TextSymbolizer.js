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
 
var TextSymbolizer = function(rule, options, utils) {
	this.id = 'textsymbolizer' + utils.generateUUID();
	this.type = 'TextSymbolizer';
	this.label = '';
	this.font_family = 'Arial';
	this.font_size= 12;
	this.font_weight = "normal";
	this.font_style = "normal";
	this.fill = "#000000";
	this.fill_opacity = 1.0;
	this.halo_fill = "#ffffff";
	this.halo_fill_opacity = 0;
	this.halo_radius = 1;
	this.order = 0;
	this.utils = utils;
	this.rule = rule;
	
	if (options) {
		$.extend(this, options);
	}
};

TextSymbolizer.prototype.getTableUI = function() {
	var ui = '';
	ui += '<tr data-rowid="' + this.id + '">';
	ui += 	'<td>'
	ui += 		'<span class="handle"> ';
	ui += 			'<i class="fa fa-ellipsis-v"></i>';
	ui += 			'<i class="fa fa-ellipsis-v"></i>';
	ui += 		'</span>';
	ui += 	'</td>';
	ui += 	'<td id="label-preview"><svg id="label-preview-' + this.id + '" class="label-preview-svg"></svg></td>';	
	ui += 	'<td><a class="edit-label-link" data-labelid="' + this.id + '" href="javascript:void(0)"><i class="fa fa-edit text-primary"></i></a></td>';
	ui += 	'<td><a class="delete-label-link" data-labelid="' + this.id + '" href="javascript:void(0)"><i class="fa fa-times text-danger"></i></a></td>';
	ui += '</tr>';	
	
	return ui;
};

TextSymbolizer.prototype.getTabMenu = function() {
	var ui = '';
	ui += '<li class="active"><a href="#label-font-tab" data-toggle="tab">' + gettext('Font') + '</a></li>';
	ui += '<li><a href="#label-halo-tab" data-toggle="tab">' + gettext('Halo') + '</a></li>';
	
	return ui;	
};

TextSymbolizer.prototype.getFontTabUI = function() {
	
	var language = $("#select-language").val();
	var fields = this.utils.getAlphanumericFields();
	var fonts = this.utils.getFonts();
	var fontWeights = this.utils.getFontWeights();
	var fontStyles = this.utils.getFontStyles();
	
	var ui = '';
	ui += '<div class="tab-pane active" id="label-font-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Label field') + '</label>';
	ui += 			'<select id="label-label" class="form-control">';
	for (var i=0; i < fields.length; i++) {
		if (this.label == '') {
			this.label = fields[i].name;
		}
		var field_name = fields[i].name;
		var field_name_trans = fields[i]["title-"+language];
		if(!field_name_trans){
			field_name_trans = field_name;
		}
		
		if (fields[i].name == this.label) {
			ui += '<option value="' + field_name + '" selected>' + field_name_trans + '</option>';
		} else {
			ui += '<option value="' + field_name + '">' + field_name_trans + '</option>';
		}		
	}	
	ui += 			'</select>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Font family') + '</label>';
	ui += 			'<select id="label-font-family" class="form-control">';
	for (var font in fonts) {
		if (font == this.font_family) {
			ui += '<option value="' + font + '" selected>' + font + '</option>';
		} else {
			ui += '<option value="' + font + '">' + font + '</option>';
		}
	}	
	ui += 			'</select>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Font size') + '</label>';
	ui += 			'<input id="label-font-size" type="number" class="form-control" value="' + parseInt(this.font_size) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Font color') + '</label>';
	ui += 			'<input id="label-fill" type="color" value="' + this.fill + '" class="form-control color-chooser">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Font weight') + '</label>';
	ui += 			'<select id="label-font-weight" class="form-control">';
	for (var i=0; i < fontWeights.length; i++) {
		if (fontWeights[i].value == this.font_weight) {
			ui += '<option value="' + fontWeights[i].value + '" selected>' + fontWeights[i].title + '</option>';
		} else {
			ui += '<option value="' + fontWeights[i].value + '">' + fontWeights[i].title + '</option>';
		}
	}
	ui += 			'</select>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Font style') + '</label>';
	ui += 			'<select id="label-font-style" class="form-control">';
	for (var i=0; i < fontStyles.length; i++) {
		if (fontStyles[i].value == this.font_style) {
			ui += '<option value="' + fontStyles[i].value + '" selected>' + fontStyles[i].title + '</option>';
		} else {
			ui += '<option value="' + fontStyles[i].value + '">' + fontStyles[i].title + '</option>';
		}
	}
	ui += 			'</select>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

TextSymbolizer.prototype.getHaloTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane" id="label-halo-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Halo color') + '</label>';
	ui += 			'<input id="label-halo-fill" type="color" value="' + this.halo_fill + '" class="form-control color-chooser">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label style="display: block;">' + gettext('Halo opacity') + '<span id="halo-fill-opacity-output" class="margin-l-15 gol-slider-output">' + (this.halo_fill_opacity * 100) + '%</span>' + '</label>';
	ui += 			'<div id="halo-fill-opacity-slider"></div>';
	ui += 		'</div>';					 
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Halo radius') + '</label>';
	ui += 			'<input id="label-halo-radius" type="number" class="form-control" value="' + parseInt(this.halo_radius) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

TextSymbolizer.prototype.registerEvents = function() {
	var self = this;
	
	$('#label-label').on('change', function() {
		self.label = this.value;
		//self.updatePreview();
	});
	
	$('#label-font-family').on('change', function() {
		self.font_family = this.value;
		//self.updatePreview();
	});
	
	$('#label-font-size').on('change', function() {
		self.font_size = this.value;
		//self.updatePreview();
	});
	
	$('#label-font-weight').on('change', function() {
		self.font_weight = this.value;
		//self.updatePreview();
	});
	
	$('#label-font-style').on('change', function() {
		self.font_style = this.value;
		//self.updatePreview();
	});
	
	$('#label-fill').on('change', function() {
		self.fill = this.value;
		//self.updatePreview();
	});
	
	$('#label-fill-opacity').on('change', function() {
		self.fill_opacity = this.value;
		//self.updatePreview();
	});
	
	$('#label-halo-fill').on('change', function() {
		self.halo_fill = this.value;		
		//self.updatePreview();
	});
	
	$('#label-halo-fill-opacity').on('change', function() {
		self.halo_fill_opacity = this.value;
		//self.updatePreview();
	});
	
	$('#label-halo-radius').on('change', function() {
		self.halo_radius = this.value;		
		//self.updatePreview();
	});
	
	$( "#halo-fill-opacity-slider" ).slider({
	    min: 0,
	    max: 100,
	    value: (self.halo_fill_opacity * 100),
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.halo_fill_opacity = opacity;
	    	//self.updatePreview();
	    },
	    slide: function( event, ui ) {
	    	$("#halo-fill-opacity-output").text(ui.value + '%');
	    }
	});
};

/*TextSymbolizer.prototype.updatePreview = function() {
	var preview = null;
	$("#label-preview-" + this.id).empty();
	var previewElement = Snap("#label-preview-" + this.id);
	
	var f_Shadow = previewElement.filter(Snap.filter.shadow(0, 0, 4, this.halo_fill, parseFloat(this.halo_fill_opacity)));
	
	var attributes = {
		fontSize: this.font_size, 
		fontFamily: this.font_family,
		fill: this.fill,
		fontWeight: this.font_weight,
		fontStyle: this.font_style
	}

	preview = previewElement.text(10,20, "Text");
	preview.attr(attributes);
};*/

TextSymbolizer.prototype.toXML = function(){
	
	var xml = '';
	xml += '<TextSymbolizer>';
	xml += 	'<Label>';
	xml += 		'<ogc:PropertyName>' + this.label + '</ogc:PropertyName>';
	xml +=  '</Label>';
	xml += 	'<Font>';
	xml += 		'<CssParameter name="font-family">' + this.font_family + '</CssParameter>';
	xml += 		'<CssParameter name="font-size">' + this.font_size + '</CssParameter>';
	xml += 		'<CssParameter name="font-style">' + this.font_style + '</CssParameter>';
	xml += 		'<CssParameter name="font-weight">' + this.font_weight + '</CssParameter>';
	xml += 	'</Font>';
	xml += 	'<LabelPlacement>';
	xml += 		'<PointPlacement>';
	xml += 			'<AnchorPoint>';
	xml += 				'<AnchorPointX>0.5</AnchorPointX>';
	xml += 				'<AnchorPointY>0.0</AnchorPointY>';
	xml += 			'</AnchorPoint>';
	xml += 		'</PointPlacement>';
	xml += 	'</LabelPlacement>';
	xml += 	'<Fill>';
	xml += 		'<CssParameter name="fill">' + this.fill + '</CssParameter>';
	xml += 		'<CssParameter name="fill-opacity">' + this.fill_opacity + '</CssParameter>';
	xml += 	'</Fill>';
	xml += 	'<Halo>';
	xml += 		'<Radius>' + this.halo_radius + '</Radius>';
	xml += 		'<Fill>';
	xml += 			'<CssParameter name="fill">' + this.halo_fill + '</CssParameter>';
	xml += 			'<CssParameter name="fill-opacity">' + this.halo_fill_opacity + '</CssParameter>';
	xml += 		'</Fill>';
	xml += 	'</Halo>';
	xml += '</TextSymbolizer>';
	
	return xml;
};

TextSymbolizer.prototype.toJSON = function(){
	
	var object = {
		id: this.id,
		type: this.type,
		label: this.label,
		font_family: this.font_family,
		font_size: this.font_size,
		font_weight: this.font_weight,
		font_style: this.font_style,
		fill: this.fill,
		fill_opacity: this.fill_opacity,
		halo_fill: this.halo_fill,
		halo_fill_opacity: this.halo_fill_opacity,
		halo_radius: this.halo_radius,
		order: this.order
	};
	
	return JSON.stringify(object);
};