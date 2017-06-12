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
 
var TextSymbolizer = function(rule, layerName, options, utils) {
	this.id = 'textsymbolizer' + utils.generateUUID();
	this.type = 'TextSymbolizer';
	this.is_actived = false;
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
	this.minscale = "";
	this.maxscale = "";
	this.title = null;
	this.filterCode = null;
	this.layer = null;
	this.layerName = layerName;
	this.codemirror = null;
	
	if (options) {
		$.extend(this, options);
		if(this.minscale<0){
			this.minscale = "";
		}
		if(this.maxscale<0){
			this.maxscale = "";
		}
		if(options.filter){
			this.filterCode = options.filter;
		}
	}
	
	if(this.utils){
		this.layer = this.utils.layer;
	}
	
	if(this.title == null && this.utils){
		var language = $("#select-language").val();
		var fields = this.utils.getAlphanumericFields();
		if(fields.length>0){
			if (fields[0]["title-"+language]) {
				this.title = fields[0]["title-"+language];
			}else{
				this.title = fields[0].name;
			}
		}
	}
	
	if(rule != null && rule.symbolizers){
		this.order = rule.symbolizers.length;
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
	ui += '<li id="general-tab" class="active"><a href="#label-general-tab" data-toggle="tab">' + gettext('General') + '</a></li>';
	ui += '<li id="font-tab"><a href="#label-font-tab" data-toggle="tab">' + gettext('Font') + '</a></li>';
	ui += '<li id="halo-tab"><a href="#label-halo-tab" data-toggle="tab">' + gettext('Halo') + '</a></li>';
	ui += '<li id="filter-tab"><a href="#label-filter-tab" data-toggle="tab">' + gettext('Filter') + '</a></li>';
	return ui;	
};


TextSymbolizer.prototype.getGeneralTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane active" id="label-general-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	if(this.is_actived){
		ui += 			'<input id="label-has-label" type="checkbox" class="has-label" checked>   ' + gettext('Has label') + '</input>';
	}else{
		ui += 			'<input id="label-has-label" type="checkbox" class="has-label">   ' + gettext('Has label') + '</input>';
	}
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext( 'Rule title') + '</label>';
	ui += 			'<input placeholder="' + gettext('Rules title') + '" name="text-title" id="text-title" type="text" value="'+this.title+'" class="form-control">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext( 'Minimum scale denominator') + '</label>';
	ui += 			'<input placeholder="' + gettext('No limit') + '" name="text-minscale" id="text-minscale" type="number" step="any" value="'+this.minscale+'" class="form-control">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext( 'Maximum scale denominator') + '</label>';
	ui += 			'<input placeholder="' + gettext('No limit') + '" name="text-maxscale" id="text-maxscale" type="number" step="any" value="'+this.maxscale+'" class="form-control">';					
	ui += 		'</div>';
	ui += '</div>';
	
	return ui;
};


TextSymbolizer.prototype.getFontTabUI = function() {
	
	var language = $("#select-language").val();
	var fields = this.utils.getAlphanumericFields();
	var fonts = this.utils.getFonts();
	var fontWeights = this.utils.getFontWeights();
	var fontStyles = this.utils.getFontStyles();
	
	var ui = '';
	ui += '<div class="tab-pane" id="label-font-tab">';
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


TextSymbolizer.prototype.getFilterTabUI2 = function() {
	var self = this;
	
	var fields = this.utils.getAlphanumericFields();
	var language = $("#select-language").val();
	
	var ui = '';
	ui += '<div class="tab-pane" id="label-filter-tab">';
	ui += 			'<div class="box-body">';
	ui += 				'<div class="row">';
	ui += 					'<div class="col-md-12">';
	ui += 						'<textarea id="cql_filter">';
	ui += 						'</textarea>';
	ui += 					'</div><br /><br />';
	ui += 					'<div class="col-md-12">';
	ui += 						'<div id="calculator">';
	ui += 							'<div class="form-group">';	
	ui += 								'<label>' + gettext('Select field') + '</label>';
	ui += 								'<select id="filter-field-select" class="form-control">';
	ui += 									'<option value="" selected disabled>--</option>';
	
	
	for (var i in fields) {
		var field_name = fields[i].name;
		var field_name_trans = fields[i]["title-"+language];
		if(!field_name_trans){
			field_name_trans = field_name;
		}
		if (this.rule && this.rule.filter.property_name && this.rule.filter.property_name == fields[i].name) {
			ui += 						'<option selected value="' + fields[i].binding + '" data-orig="' + field_name + '" value="' + field_name + '">' + field_name_trans + '</option>';
			dataType = fields[i].binding;
		} else {
			ui += 						'<option value="' + fields[i].binding + '" data-orig="' + field_name + '" value="' + field_name + '">' + field_name_trans + '</option>';
		}
	}
	ui += 								'</select>';
	ui += 							'</div>';
	ui += 							'<div class="form-group">';	
	ui += 								'<label>' + gettext('Select value') + '</label>';
	ui += 								'<select id="filter-value-select" class="form-control">';
	ui += 									'<option value="" selected disabled>--</option>';
	ui += 								'</select>';
	ui += 							'</div>';
	ui += 							'<div class="keys">';
	ui += 								'<span>=</span>';
	ui += 								'<span><></span>';
	ui += 								'<span><</span>';
	ui += 								'<span><=</span>';
	ui += 								'<span>></span>';
	ui += 								'<span>>=</span>';
	ui += 								'<span class="weight">AND</span>';
	ui += 								'<span class="weight">OR</span>';
	ui += 								'<span class="weight">NOT</span>';
	ui += 								'<span class="weight">IN</span>';
	ui += 								'<span>(</span>';
	ui += 								'<span>)</span>';
	ui += 								'<span>[</span>';
	ui += 								'<span>]</span>';
	ui += 								'<span>{</span>';
	ui += 								'<span>}</span>';
	ui += 							'</div>';
	ui += 							'<div class="bottom-selects">';
	ui += 							'</div>';
	ui += 						'</div>';
	ui += 					'</div>';
	ui += 				'</div>';
	ui += 			'</div>';

	ui += '</div>';
	
	
	
	return ui;
	
};

TextSymbolizer.prototype.getFilterTabUI = function() {
	var self = this;
	var language = $("#select-language").val();
	$('#modal-expression-content').empty();

	var operations = this.utils.getFilterOperations();
	var fields = this.utils.getAlphanumericFields();

	var dataType = '';

	var ui = '';
	ui += '<div class="tab-pane" id="label-filter-tab">';
	ui += 		'<div id="expressions-list" class="expressions-list">';

	ui += 					'<div class="row">';
	ui += 						'<div class="col-md-6 form-group">';
	ui += 							'<label>' + gettext('Select field') + '</label>';
	ui += 							'<select id="expression-field" class="form-control">';
	ui += 								'<option disabled selected value> -- ' + gettext('Select field') + ' -- </option>';
	for (var i in fields) {
		var field_name = fields[i].name;
		var field_name_trans = fields[i]["title-"+language];
		if(!field_name_trans){
			field_name_trans = field_name;
		}
		if (this.filterCode && this.filterCode.property_name && this.filterCode.property_name == fields[i].name) {
			ui += 						'<option selected data-type="' + fields[i].binding + '" value="' + field_name + '">' + field_name_trans + '</option>';
			dataType = fields[i].binding;
		} else {
			ui += 						'<option data-type="' + fields[i].binding + '" value="' + field_name + '">' + field_name_trans + '</option>';
		}

	}	
	ui += 							'</select>';
	ui += 						'</div>';
	ui += 						'<div class="col-md-6 form-group">';
	ui += 							'<label>' + gettext('Select operation') + '</label>';
	ui += 							'<select id="expression-operation" class="form-control">';
	ui += 								'<option disabled selected value> -- ' + gettext('Select operation') + ' -- </option>';
	for (var i in operations) {
		if (this.filterCode && this.filterCode.type && this.filterCode.type == operations[i].value) {
			ui += 						'<option selected value="' + operations[i].value + '">' + operations[i].title + '</option>';
		} else {
			ui += 						'<option value="' + operations[i].value + '">' + operations[i].title + '</option>';
		}
	}	
	ui += 							'</select>';
	ui += 						'</div>';
	ui += 					'</div>';
	ui += 					'<div id="expression-values" class="row">';
	ui += 					'</div>';

	ui += 		'</div>';
	ui += 		'<div class="row">';
	ui += 			'<div class="col-md-12 form-group">';
	ui += 				'<label>' + gettext('Filter preview') + '</label>';
	ui += 				'<textarea id="filter-output" name="code">	';					
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 	'</div>';

	return ui;

};

TextSymbolizer.prototype.getFilterInputs = function(type, twoValues) {
	var inputs = '';

	if (type.indexOf('java.math') > -1 || type.indexOf('java.lang.Double') > -1){
		if (twoValues) {
			inputs += '<div id="expression-values" class="col-md-6 form-group">';
			inputs += 	'<label>' + gettext('Value 1') + '</label>';
			inputs += 	'<input name="expresion-value-1" id="expresion-value-1" type="number" step="any" value="0" class="form-control">';
			inputs += '</div>';
			inputs += '<div id="expression-values" class="col-md-6 form-group">';
			inputs += 	'<label>' + gettext('Value 2') + '</label>';
			inputs += 	'<input name="expresion-value-2" id="expresion-value-2" type="number" step="any" value="0" class="form-control">';
			inputs += '</div>';

		} else {
			inputs += '<div id="expression-values" class="col-md-12 form-group">';
			inputs += 	'<label>' + gettext('Value') + '</label>';
			inputs += 	'<input name="expresion-value-1" id="expresion-value-1" type="number" step="any" value="0" class="form-control">';
			inputs += '</div>';
		}

	} else if (type == 'java.lang.String'){
		if (twoValues) {
			inputs += '<div id="expression-values" class="col-md-6 form-group">';
			inputs += 	'<label>' + gettext('Value 1') + '</label>';
			inputs += 	'<input name="expresion-value-1" id="expresion-value-1" type="text" class="form-control">';
			inputs += '</div>';
			inputs += '<div id="expression-values" class="col-md-6 form-group">';
			inputs += 	'<label>' + gettext('Value 2') + '</label>';
			inputs += 	'<input name="expresion-value-2" id="expresion-value-2" type="text" class="form-control">';
			inputs += '</div>';

		} else {

			inputs += '<div id="expression-values" class="col-md-12 form-group">';
			inputs += 	'<label>' + gettext('Value') + '</label>';
			inputs += 	'<input name="expresion-value-1" id="expresion-value-1" type="text" class="form-control">';
			inputs += '</div>';
		}
	}

	return inputs;
};

TextSymbolizer.prototype.getFilterOutput = function(field, operation, value1, value2) {
	var filterOutputContentcode = '';
	if (operation == 'is_equal_to') {
		filterOutputContentcode = '\t' + field + ' = ' + value1;

	} else if (operation == 'is_null') {
		filterOutputContentcode = '\t' + field + ' = null';

	} else if (operation == 'is_like') {
		filterOutputContentcode = '\t' + field + ' ' + gettext('contains') + ' ' + value1;

	} else if (operation == 'is_not_equal') {
		filterOutputContentcode = '\t' + field + ' <> ' + value1;

	} else if (operation == 'is_greater_than') {
		filterOutputContentcode = '\t' + field + ' > ' + value1;

	} else if (operation == 'is_greater_than_or_equal_to') {
		filterOutputContentcode = '\t' + field + ' >= ' + value1;

	} else if (operation == 'is_less_than') {
		filterOutputContentcode = '\t' + field + ' < ' + value1;

	} else if (operation == 'is_less_than_or_equal_to') {
		filterOutputContentcode = '\t' + field + ' <= ' + value1;

	} else if (operation == 'is_between') {
		filterOutputContentcode = '\t' + value1 + ' <= ' + field + ' <= ' + value2;

	}
	return filterOutputContentcode;
};



/**
 * TODO
 */
TextSymbolizer.prototype.describeFeatureType = function() {
	var featureType = new Array();
	if(this.layerName){
		var layer_conf = this.layerName.split(":");
		if(layer_conf.length > 1){
			$.ajax({
				type: 'POST',
				async: false,
			  	url: '/gvsigonline/services/describeFeatureType/',
			  	data: {
			  		'layer': layer_conf[1],
					'workspace': layer_conf[0]
				},
			  	success	:function(response){
			  		if("fields" in response){
			  			featureType = response['fields'];
			  		}
				},
			  	error: function(){}
			});
		}
	}
	return featureType;
};


TextSymbolizer.prototype.isGeomType = function(type){
	if(type == 'POLYGON' || type == 'MULTIPOLYGON' || type == 'LINESTRING' || type == 'MULTILINESTRING' || type == 'POINT' || type == 'MULTIPOINT'){
		return true;
	}
	return false;
}

TextSymbolizer.prototype.isNumericType = function(type){
	if(type == 'smallint' || type == 'integer' || type == 'bigint' || type == 'decimal' || type == 'numeric' ||
			type == 'real' || type == 'double precision' || type == 'smallserial' || type == 'serial' || type == 'bigserial' ){
		return true;
	}
	return false;
}

TextSymbolizer.prototype.isStringType = function(type){
	if(type == 'java.lang.String' ){
		return true;
	}
	return false;
}

TextSymbolizer.prototype.isDateType = function(type){
	if(type == 'date' || type == 'timestamp' || type == 'time' || type == 'interval'){
		return true;
	}
	return false;
}


TextSymbolizer.prototype.loadUniqueValues = function(field) {
	var self = this;
	if(this.layerName){
		var layer_conf = this.layerName.split(":");
		if(layer_conf.length > 1){
			$.ajax({
				type: 'POST',
				async: false,
			  	url: '/gvsigonline/services/get_unique_values/',
			  	data: {
			  		'layer_name': layer_conf[1],
					'layer_ws': layer_conf[0],
					'field': field
				},
			  	success	:function(response){
			  		$("#filter-value-select").empty();
			  		$emptyOpt = $("<option></option>").attr("value", "").attr("selected", true).attr("disabled", true).text("---");
			  		$("#filter-value-select").append($emptyOpt);
			  		$.each(response.values, function(index, option) {
			  			$option = $("<option></option>").attr("value", option).text(option);
			  			$("#filter-value-select").append($option);
			  	    });
				},
			  	error: function(){}
			});
		}
	}
};


TextSymbolizer.prototype.registerEvents = function() {
	var self = this;

	
	$('#label-has-label').on('change', function() {
		self.is_actived = $(this).is(':checked');
		self.initializeForm();
	});
	
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
	
	$("#text-minscale").on('change', function(e){
		self.minscale = this.value;
	});
	
	$("#text-maxscale").on('change', function(e){
		self.maxscale = this.value;
	});
	
	$("#text-title").on('change', function(e){
		self.title = this.value;
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
	
	var filterOutput = document.getElementById('filter-output');
	this.codemirror = CodeMirror.fromTextArea(filterOutput, {
		value: "",
		mode:  "javascript",
		theme: "xq-dark",
		lineNumbers: true
	});

	if (this.filterCode && this.filterCode.type) {
		var filterOutputContentcode = '';
		var dataType = $('#expression-field option:selected').attr("data-type");
		if (this.filterCode.type == 'is_between') {
			var inputs = self.getFilterInputs(dataType, true);
			$('#expression-values').empty();
			$('#expression-values').append(inputs);
			$('#expresion-value-1').val(this.filterCode.value1);
			$('#expresion-value-2').val(this.filterCode.value2);

			this.codemirror.setValue('');
			filterOutputContentcode = this.getFilterOutput(this.filterCode.property_name, this.filterCode.type, this.filterCode.value1, this.filterCode.value2);
			this.codemirror.setValue(filterOutputContentcode);

		} else {
			var inputs = self.getFilterInputs(dataType, false);
			$('#expression-values').empty();
			$('#expression-values').append(inputs);
			$('#expresion-value-1').val(this.filterCode.value1);

			this.codemirror.setValue('');
			filterOutputContentcode = this.getFilterOutput(this.filterCode.property_name, this.filterCode.type, this.filterCode.value1, this.filterCode.value2);
			this.codemirror.setValue(filterOutputContentcode);

		}
	}
	
	$('#expresion-value-1').on('change paste keyup', function(){
		var value1 = $('#expresion-value-1').val();
		var value2 = $('#expresion-value-2').val();
		var field = $('#expression-field').val();
		var operation = $('#expression-operation').val();

		self.codemirror.setValue('');
		var filterOutputContentcode = self.getFilterOutput(field, operation, value1, value2);
		self.codemirror.setValue(filterOutputContentcode);
	});

	$('#expresion-value-2').on('change paste keyup', function(){
		var value1 = $('#expresion-value-1').val();
		var value2 = $('#expresion-value-2').val();
		var field = $('#expression-field').val();
		var operation = $('#expression-operation').val();

		self.codemirror.setValue('');
		var filterOutputContentcode = self.getFilterOutput(field, operation, value1, value2);
		self.codemirror.setValue(filterOutputContentcode);
	});

	$('#expression-field').on('change', function(e) {

		var twoValues = false;
		if ( $('#expression-operation').val() == 'is_between' ) {
			twoValues = true;
		}
		var type = this.selectedOptions[0].dataset.type;

		var inputs = self.getFilterInputs(type, twoValues);

		$('#expression-values').empty();
		$('#expression-values').append(inputs);

		$('#expresion-value-1').on('change paste keyup', function(){
			var value1 = $('#expresion-value-1').val();
			var value2 = $('#expresion-value-2').val();
			var field = $('#expression-field').val();
			var operation = $('#expression-operation').val();

			self.codemirror.setValue('');
			var filterOutputContentcode = self.getFilterOutput(field, operation, value1, value2);
			self.codemirror.setValue(filterOutputContentcode);
		});

		$('#expresion-value-2').on('change paste keyup', function(){
			var value1 = $('#expresion-value-1').val();
			var value2 = $('#expresion-value-2').val();
			var field = $('#expression-field').val();
			var operation = $('#expression-operation').val();

			self.codemirror.setValue('');
			var filterOutputContentcode = self.getFilterOutput(field, operation, value1, value2);
			self.codemirror.setValue(filterOutputContentcode);
		});

	});

	$('#expression-operation').on('change', function(e) {

		var twoValues = false;
		if ( this.value == 'is_between' ) {
			twoValues = true;
		}
		var type = $('#expression-field')[0].selectedOptions[0].dataset.type;

		var inputs = self.getFilterInputs(type, twoValues);

		$('#expression-values').empty();
		$('#expression-values').append(inputs);

		$('#expresion-value-1').on('change paste keyup', function(){
			self.saveFilter();
		});

		$('#expresion-value-2').on('change paste keyup', function(){
			self.saveFilter();
		});

	});

	self.initializeForm();
};

TextSymbolizer.prototype.saveFilter = function() {
	var value1 = $('#expresion-value-1').val();
	var value2 = $('#expresion-value-2').val();
	var field = $('#expression-field').val();
	var operation = $('#expression-operation').val();

	this.codemirror.setValue('');
	var filterOutputContentcode = this.getFilterOutput(field, operation, value1, value2);
	this.codemirror.setValue(filterOutputContentcode);
	
	var filter = {
			type: operation,
			property_name: field,
			value1: value1
	};
	if (operation == 'is_between') {
		filter['value2'] = value2;
	}
	
	this.filterCode = filter;
}

TextSymbolizer.prototype.initializeForm = function() {
	if(!this.is_actived) {
	    $("#font-tab a").removeAttr("data-toggle");
	    $("#halo-tab a").removeAttr("data-toggle");
	    $("#filter-tab a").removeAttr("data-toggle");
	    $("#text-title").prop("disabled",true);
	    $("#text-minscale").prop("disabled",true);
	    $("#text-maxscale").prop("disabled",true);
	} else {
		$("#font-tab a").attr("data-toggle", "tab");
		$("#halo-tab a").attr("data-toggle", "tab");
	    $("#filter-tab a").attr("data-toggle", "tab");
		$("#text-title").prop("disabled",false);
	    $("#text-minscale").prop("disabled",false);
	    $("#text-maxscale").prop("disabled",false);
	}
};

TextSymbolizer.prototype.is_activated = function() {
	return this.is_actived;
}

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


TextSymbolizer.prototype.change_alias_from_cql_filter = function(cql_filter) {
	var fields_trans = this.layer.conf;
	var language = $("#select-language").val();
	
	if(fields_trans != null && fields_trans["fields"] != undefined){
		var fields = fields_trans["fields"];
		for(var ix=0; ix<fields.length; ix++){
			var feat_name = fields[ix]["name"];
			var feat_name_trans = fields[ix]["title-"+language];
			if(feat_name_trans && feat_name){
				var filter_string =  new RegExp("("+feat_name_trans+")([^\\w'\"]+)","g");
				cql_filter = cql_filter.replace(filter_string, feat_name+"$2")
			}
			
		}
	}
	return cql_filter;
};


TextSymbolizer.prototype.toXML = function(){
	
	var xml = '';
	if(this.is_actived){
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
	}
	return xml;
};

TextSymbolizer.prototype.toJSON = function(){
	var minscale = -1;
	if(this.minscale != "" && this.minscale >= 0){
		minscale = this.minscale;
	}
	
	var maxscale = -1;
	if(this.maxscale != "" && this.maxscale >= 0){
		maxscale = this.maxscale;
	}
	
	var filter_cql = this.filterCode;
	
	
	var object = {
		id: this.id,
		type: this.type,
		is_actived: this.is_actived,
		label: this.label,
		title: this.title,
		font_family: this.font_family,
		font_size: this.font_size,
		font_weight: this.font_weight,
		font_style: this.font_style,
		fill: this.fill,
		fill_opacity: this.fill_opacity,
		halo_fill: this.halo_fill,
		halo_fill_opacity: this.halo_fill_opacity,
		halo_radius: this.halo_radius,
		minscale: minscale,
		maxscale: maxscale,
		filter : filter_cql,
		order: this.order
	};
	
	return JSON.stringify(object);
};