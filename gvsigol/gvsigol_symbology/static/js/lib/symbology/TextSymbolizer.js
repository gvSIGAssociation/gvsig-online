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
	this.AnchorPointX = 0.5;
	this.is_label_actived=false;
	if(options && options.anchor_point_x != null && options.anchor_point_x != ""){
		this.AnchorPointX = options.anchor_point_x;
	}
	this.AnchorPointY = -1.5;
	if(options && options.anchor_point_y != null && options.anchor_point_y != ""){
		this.AnchorPointY = options.anchor_point_y;
	}
	this.codemirror = null;
	
	this.expressions = new Array();
	this.expressions_counter = 0;
	
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
	this.type = 'TextSymbolizer';
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
	ui += 	'<td><a class="edit-label-link-' + this.id + '" data-labelid="' + this.id + '" href="javascript:void(0)"><i class="fa fa-edit text-primary"></i></a></td>';
	ui += 	'<td><a class="delete-label-link-' + this.id + '" data-labelid="' + this.id + '" href="javascript:void(0)"><i class="fa fa-times text-danger"></i></a></td>';
	ui += '</tr>';	
	
	return ui;
};

TextSymbolizer.prototype.getTabMenu = function(alwaysAllowed) {
	var ui = '';
	if(alwaysAllowed){
		this.is_actived = true;			
	}
	if(!alwaysAllowed){
		ui += '<li id="general-tab" class="active"><a href="#label-general-tab" data-toggle="tab">' + gettext('General') + '</a></li>';
	}
	ui += '<li id="font-tab"><a href="#label-font-tab" data-toggle="tab">' + gettext('Font') + '</a></li>';
	ui += '<li id="halo-tab"><a href="#label-halo-tab" data-toggle="tab">' + gettext('Halo') + '</a></li>';
	if(!alwaysAllowed){
		ui += '<li id="filter-tab"><a href="#label-filter-tab" data-toggle="tab">' + gettext('Filter') + '</a></li>';
	}
	return ui;	
};


TextSymbolizer.prototype.getGeneralTabUI = function(alwaysAllowed) {
	var ui = '';
	ui += '<div class="tab-pane active" id="label-general-tab">';
	if(!alwaysAllowed){
		ui += 	'<div class="row">';
		ui += 		'<div class="col-md-12 form-group">';
		if(this.is_actived){
			ui += 			'<input id="label-has-label" type="checkbox" class="has-label" checked>   ' + gettext('Has label') + '</input>';
		}else{
			ui += 			'<input id="label-has-label" type="checkbox" class="has-label">   ' + gettext('Has label') + '</input>';
		}
		ui += 		'</div>';
		ui += 	'</div>';
	}else{
		this.is_actived = true;		
	}
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


TextSymbolizer.prototype.getFontTabUI = function(isClusteredPoint) {
	
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
	if(!isClusteredPoint){
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
	}else{
		ui += '<option value="count" selected>' + gettext('Count features') + '</option>';
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


TextSymbolizer.prototype.getFilterTabUI = function() {
	var self = this;

	this.expressions = [];
	this.expressions_counter = 0;
	
	var ui = '';
	ui += '<div class="tab-pane" id="label-filter-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	if(this.is_label_actived){
		ui += 			'<input id="label-has-label-on" type="checkbox" class="has-label" checked>   ' + gettext('Show labels') + '</input>';
	}else{
		ui += 			'<input id="label-has-label-on" type="checkbox" class="has-label">   ' + gettext('Show labels') + '</input>';
	}
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '<div class="box">';
	ui += 	'<div class="box-header with-border">';
	ui += 		'<h3 class="box-title">' + gettext('Label filter expressions') + '</h3>';
	ui += 		'<div class="box-tools pull-right">';
	ui += 			'<div class="btn-group">';
	ui += 				'<button type="button" class="btn btn-sm btn-success">'+gettext("Add")+'</button>';
	ui += 				'<button type="button" class="btn btn-sm btn-success margin-r-5 dropdown-toggle" data-toggle="dropdown" aria-expanded="false">';
	ui += 					'<span class="caret"></span>';
	ui += 					'<span class="sr-only">Toggle Dropdown</span>';
	ui += 				'</button>';
	ui += 				'<ul class="dropdown-menu" role="menu">';
	ui += 					'<li><a id="add-and-label" data-ruleid="label-text" href="#">'+gettext("AND expression")+'</a></li>';
	ui += 					'<li><a id="add-or-label" data-ruleid="label-text" href="#">'+gettext("OR expression")+'</a></li>';
	ui += 				'</ul>';
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="box-body">';
	ui += 		'<div id="label-list" class="expressions-list">';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	ui += '</div>';
	
	return ui;
};


TextSymbolizer.prototype.addNewExpression = function() {
	var self = this;
	
	var rule = self.rule;
	var expression = {
		id: self.expressions_counter,
		type: 'expression',
		field: '',
		operation: '',
		value: ''
	};
	self.expressions.push(expression);
	$('#label-list').append(self.addExpression(expression));
	$('#remove-label' + self.expressions_counter).css("display", "none");
	$('#remove-label' + self.expressions_counter).on('click', function(e){
		e.preventDefault();
		self.deleteExpression(this.dataset.labelid);
		this.parentNode.parentNode.parentNode.remove();
		self.expressions_counter = self.expressions_counter - 1;
	});
	self.registerFilterEvents(self.expressions_counter);
	self.expressions_counter = self.expressions_counter + 1;
};



TextSymbolizer.prototype.addANDExpression = function() {
	var self = this;
	
	var rule = self.rule;
	var andOperator = {
		id: self.expressions_counter,
		type: 'and'
	};
	self.expressions.push(andOperator);
	$('#label-list').append(self.addAndOperator());	
	$('#remove-and-label' + self.expressions_counter).on('click', function(e){
		e.preventDefault();
		self.removeOperatorExpression(this.dataset.labelid, $(this));
	});
	self.registerFilterEvents(self.expressions_counter);
	self.expressions_counter = self.expressions_counter + 1;
};


TextSymbolizer.prototype.addORExpression = function(ruleid) {
	var self = this;
	
	var rule = self.rule;
	var orOperator = {
		id: self.expressions_counter,
		type: 'or'
	};
	self.expressions.push(orOperator);
	$('#label-list').append(self.addOrOperator());
	$('#remove-or-label' + self.expressions_counter).on('click', function(e){
		e.preventDefault();
		self.removeOperatorExpression(this.dataset.labelid, $(this));
	});
	self.registerFilterEvents(self.expressions_counter);
	self.expressions_counter = self.expressions_counter + 1;
};

TextSymbolizer.prototype.removeOperatorExpression = function(expressionid, component) {
	var self = this;
	
	var parent = component.parent().parent().parent();
	var next = parent.next();
	var nextbutton = next.find("button.btn-box-tool").first();
	var nextxpressionid = nextbutton.attr("data-labelid");
	self.removeExpression(nextxpressionid, nextbutton);
	self.removeExpression(expressionid, $(component));
	self.saveFilter();
};

TextSymbolizer.prototype.removeExpression = function(expressionid, component) {
	var self = this;
	
	self.deleteExpression(expressionid);
	component.parent().parent().parent().remove();
	self.expressions_counter = self.expressions_counter - 1;
};

TextSymbolizer.prototype.addExpression = function(expression) {
	var self = this;
	var count = this.expressions_counter;
	var language = $("#select-language").val();
	var operations = this.utils.getFilterOperations();
	var fields = this.utils.getAlphanumericFields();
	var dataType = '';
	
	var ui = '';
	ui += '<div class="box">';
	ui += 	'<div class="box-header" style="padding: 18px;">';
	ui += 		'<div class="box-tools pull-right">';
	ui += 			'<button data-labelid="'+count+'" id="remove-label'+count+'" class="btn btn-box-tool" style="color:red;" data-widget="collapse">';
	ui += 				'<i class="fa fa-times"></i>';
	ui += 			'</button>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="box-body">';
	ui += 		'<div class="row">';
	ui += 			'<div class="col-md-6 form-group">';
	ui += 				'<label>' + gettext('Select field') + '</label>';
	ui += 				'<select data-data-labelidid="'+count+'" id="label-field'+count+'" class="form-control expression-field filter-component">';
	ui += 					'<option disabled selected value> -- ' + gettext('Select field') + ' -- </option>';
	for (var i in fields) {
		var field_name = fields[i].name;
		var field_name_trans = fields[i]["title-"+language];
		if(!field_name_trans){
			field_name_trans = field_name;
		}
		if (expression.field == fields[i].name) {
			ui += 			'<option selected data-type="' + fields[i].binding + '" value="' + field_name + '">' + field_name_trans + '</option>';
			dataType = fields[i].binding;
		} else {
			ui += 			'<option data-type="' + fields[i].binding + '" value="' + field_name + '">' + field_name_trans + '</option>';
		}

	}	
	ui += 				'</select>';
	ui += 			'</div>';
	ui += 			'<div class="col-md-6 form-group">';
	ui += 				'<label>' + gettext('Select operation') + '</label>';
	ui += 				'<select data-labelid="'+count+'" id="label-operation'+count+'" class="form-control expression-operation filter-component">';
	ui += 					'<option disabled selected value>  -- ' + gettext('Select operation') + ' -- </option>';
	for (var i in operations) {
		if (operations[i].value != 'is_between' && operations[i].value != 'is_null') {
			if (expression.operation == operations[i].value) {
				ui += 			'<option selected value="' + operations[i].value + '">' + operations[i].title + '</option>';
			} else {
				ui += 			'<option value="' + operations[i].value + '">' + operations[i].title + '</option>';
			}
		}	
	}	
	ui += 				'</select>';
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 		'<div data-labelid="'+count+'" id="label-value'+count+'" class="row">';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

TextSymbolizer.prototype.updateExpression = function(id, field, operation, value) {
	for (var i=0; i < this.expressions.length; i++) {
		if (this.expressions[i].id == id) {
			this.expressions[i].field = field;
			this.expressions[i].operation = operation;
			this.expressions[i].value = value;
			this.saveFilter();
		}
	}
};

TextSymbolizer.prototype.deleteExpression = function(id) {
	for (var i=0; i < this.expressions.length; i++) {
		if (this.expressions[i].id == id) {
			this.expressions.splice(i, 1);
			this.saveFilter();
		}
	}
};

TextSymbolizer.prototype.registerFilterEvents = function(expressionId) {

	var self = this;

	$('#label-field'+expressionId).on('change', function(e) {
		var inputs = '';
		inputs += '<div class="col-md-12 form-group">';
		inputs += 	'<label>' + gettext('Value') + '</label>';
		inputs += 	'<input type="text" id="label-value-select'+expressionId+'" class="form-control filter-component" list="label-value-list'+expressionId+'">';
		inputs += 	'<datalist id="label-value-list'+expressionId+'">';
		inputs += 	'</datalist>';
		inputs += '</div>';
		
		$('#label-value'+expressionId).empty();
		$('#label-value'+expressionId).append(inputs);

		var value = $('#label-value-select'+expressionId).val();
		var field = $('#label-field'+expressionId).val();
		var operation = $('#label-operation'+expressionId).val();
		self.updateExpression(expressionId, field, operation, value);

		var value_orig = $('option:selected', $('#label-field'+expressionId)).val();
		self.loadUniqueValues(value_orig, expressionId);
	});

	$('#label-operation'+expressionId).on('change', function(e) {
		var inputs = '';
		inputs += '<div class="col-md-12 form-group">';
		inputs += 	'<label>' + gettext('Value') + '</label>';
		inputs += 	'<input type="text" id="label-value-select'+expressionId+'" class="form-control filter-component" list="label-value-list'+expressionId+'">';
		inputs += 	'<datalist id="label-value-list'+expressionId+'">';
		inputs += 	'</datalist>';
		inputs += '</div>';
		
		$('#label-value'+expressionId).empty();
		$('#label-value'+expressionId).append(inputs);

		var value = $('#label-value-select'+expressionId).val();
		var field = $('#label-field'+expressionId).val();
		var operation = $('#label-operation'+expressionId).val();
		self.updateExpression(expressionId, field, operation, value);

		var value_orig = $('option:selected', $('#label-field'+expressionId)).val();
		self.loadUniqueValues(value_orig, expressionId);
	});

};

TextSymbolizer.prototype.addAndOperator = function() {
	var count = this.expressions_counter;
	
	var andOperator = '';
	andOperator += '<div class="box">';
	andOperator += 	'<div class="box-header" style="text-align: center; padding: 18px;">';
	andOperator += 		'AND';
	andOperator += 		'<div class="box-tools pull-right">';
	andOperator += 			'<button data-labelid="'+count+'" id="remove-and-label'+count+'" class="btn btn-box-tool" style="color:red;" data-widget="collapse">';
	andOperator += 				'<i class="fa fa-times"></i>';
	andOperator += 			'</button>';
	andOperator += 		'</div>';
	andOperator += 	'</div>';
	andOperator += '</div>';
	
	return andOperator;
};

TextSymbolizer.prototype.addOrOperator = function() {
	var count = this.expressions_counter;
	
	var orOperator = '';
	orOperator += '<div class="box">';
	orOperator += 	'<div class="box-header" style="text-align: center; padding: 18px;">';
	orOperator += 		'OR';
	orOperator += 		'<div class="box-tools pull-right">';
	orOperator += 			'<button data-labelid="'+count+'" id="remove-or-label'+count+'" class="btn btn-box-tool" style="color:red;" data-widget="collapse">';
	orOperator += 				'<i class="fa fa-times"></i>';
	orOperator += 			'</button>';
	orOperator += 		'</div>';
	orOperator += 	'</div>';
	orOperator += '</div>';
	
	return orOperator;
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

TextSymbolizer.prototype.getExpressionById = function(id) {
	for (var i=0; i < this.expressions.length; i++) {
		if (this.expressions[i].id == id) {
			return this.expressions[i];
		}
	}
};


TextSymbolizer.prototype.loadUniqueValues = function(field, expressionId) {
	var self = this;
	var expression = self.getExpressionById(expressionId);
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
			  		$("#label-value-list"+expressionId).empty();
			  		$("#label-value-select"+expressionId).val(expression.value);
			  		$.each(response.values, function(index, option) {
			  			if (expression.value == option) {
			  				$option = $("<option selected></option>").attr("value", option).text(option);
				  			$("#label-value-list"+expressionId).append($option);
			  			} else {
			  				$option = $("<option></option>").attr("value", option).text(option);
				  			$("#label-value-list"+expressionId).append($option);
			  			}
			  			
			  	    });
			  		
			  		$('#label-value-select'+expressionId).on('change', function(){
			  			var value =  $('#label-value-select'+expressionId).val();
			  			var field = $('#label-field'+expressionId).val();
			  			var operation = $('#label-operation'+expressionId).val();
			  			self.updateExpression(expressionId, field, operation, value);
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

	$('#label-has-label-on').on('change', function() {
		self.is_label_actived = $(this).is(':checked');
		self.is_actived=false;
		if (!self.is_label_actived){
			$('#label-field0').prop("disabled",true);
			$('#label-operation0').prop("disabled",true);
			$('#label-value-select0').prop("disabled",true);			
			$('#label-has-label-on').prop('checked', false);
			$("#font-tab a").removeAttr("data-toggle");
			$("#halo-tab a").removeAttr("data-toggle");
			$("#filter-tab a").removeAttr("data-toggle");
			$("#text-title").prop("disabled",true);
			$("#text-minscale").prop("disabled",true);
			$("#text-maxscale").prop("disabled",true);
		
		}else{
			$('#label-field0').prop("disabled",false);
			$('#label-operation0').prop("disabled",false);
			$('#label-value-select0').prop("disabled",false);
			$("#font-tab a").attr("data-toggle", "tab");
			$("#halo-tab a").attr("data-toggle", "tab");
			$("#filter-tab a").attr("data-toggle", "tab");
			$("#text-title").prop("disabled",false);
			$("#text-minscale").prop("disabled",false);
			$('#label-has-label-on').prop('checked', true);
			$("#font-tab a").attr("data-toggle", "tab");		
	    	$("#text-maxscale").prop("disabled",false);	
			self.is_actived=true;				
		}
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
		
	var r = this.rule;
//	if (r && r.filter && r.filter.length > 0){
//		for (var i=0; i<r.filter.length; i++) {
//			var filter = r.filter[i];
	
	if (this.filterCode && this.filterCode.length > 0){
		for (var i=0; i<this.filterCode.length; i++) {
			var filter = this.filterCode[i];	
			if (filter.type == 'expression') {
				var expression = {
					id: self.expressions_counter,
					type: 'expression',
					field: filter.field,
					operation: filter.operation,
					value: ""+filter.value
				};
				self.expressions.push(expression);
				$('#label-list').append(self.addExpression(expression));
				var inputs = '';
				inputs += '<div class="col-md-12 form-group">';
				inputs += 	'<label>' + gettext('Value') + '</label>';
				inputs += 	'<input type="text" id="label-value-select'+expression.id+'" class="form-control filter-component" list="label-value-list'+expression.id+'">';
				inputs += 	'<datalist id="label-value-list'+expression.id+'">';
				inputs += 	'</datalist>';
				inputs += '</div>';
				
				$('#label-value'+expression.id).empty();
				$('#label-value'+expression.id).append(inputs);
				self.loadUniqueValues(expression.field, expression.id);
				$('#remove-label' + self.expressions_counter).on('click', function(e){
					e.preventDefault();
					self.deleteExpression(this.dataset.labelid);
					this.parentNode.parentNode.parentNode.remove();
					self.expressions_counter = self.expressions_counter - 1;
				});
				self.registerFilterEvents(self.expressions_counter);
				self.expressions_counter = self.expressions_counter + 1;
				
			} else if (filter.type == 'and') {
				var andOperator = {
					id: self.expressions_counter,
					type: 'and'
				};
				self.expressions.push(andOperator);
				$('#label-list').append(self.addAndOperator());	
				$('#remove-and-label' + self.expressions_counter).on('click', function(e){
					e.preventDefault();
					self.removeOperatorExpression(this.dataset.labelid, $(this));
				});
				self.registerFilterEvents(self.expressions_counter);
				self.expressions_counter = self.expressions_counter + 1;
				
			} else if (filter.type == 'or') {
				var orOperator = {
					id: self.expressions_counter,
					type: 'or'
				};
				self.expressions.push(orOperator);
				$('#label-list').append(self.addOrOperator());
				$('#remove-or-label' + self.expressions_counter).on('click', function(e){
					e.preventDefault();
					self.removeOperatorExpression(this.dataset.labelid, $(this));
				});
				self.registerFilterEvents(self.expressions_counter);
				self.expressions_counter = self.expressions_counter + 1;
			}
		}
	}else{
		self.addNewExpression();
	}

	
	for(var ix = 0; ix< self.expressions.length; ix++){
		if(self.expressions[ix].type == "expression"){
			$('#remove-label' + self.expressions[ix].id).css("display", "none");
		}
	}
//	$('#save-filter').on('click', function(){
//		var ruleid = this.dataset.ruleid;
//		var rule = self.rule
//
//		if(self.expressions.length > 1 || 
//				(self.expressions.length >0 && self.expressions[0].field != "" && self.expressions[0].operation != "" )){
//			self.filterCode = self.expressions;
//		}
//		$('#modal-label').modal('hide');
//	});
	
	$('#add-new-label').on('click', function(){
		self.addNewExpression(this.dataset.ruleid);
	});
	
	$('#add-and-label').on('click', function(){
		self.addANDExpression(this.dataset.ruleid);
		self.addNewExpression(this.dataset.ruleid);
	});
	
	$('#add-or-label').on('click', function(){
		self.addORExpression(this.dataset.ruleid);
		self.addNewExpression(this.dataset.ruleid);
	});
	
	$('.filter-component').on('change', function(){
		self.saveFilter();
	});

	self.initializeForm();
};

TextSymbolizer.prototype.saveFilter = function() {
	if(this.expressions.length > 1 || 
			(this.expressions.length >0 && this.expressions[0].field != "" && this.expressions[0].operation != "" )){
		this.filterCode = this.expressions;
	}
}

TextSymbolizer.prototype.initializeForm = function() {
	if(!this.is_actived) {
	    $("#font-tab a").removeAttr("data-toggle");
	    $("#halo-tab a").removeAttr("data-toggle");
	    $("#filter-tab a").removeAttr("data-toggle");
	    $("#text-title").prop("disabled",true);
	    $("#text-minscale").prop("disabled",true);
	    $("#text-maxscale").prop("disabled",true);
		//$('#label-has-label-on').prop('checked', false)
	} else {
		$("#font-tab a").attr("data-toggle", "tab");
		$("#halo-tab a").attr("data-toggle", "tab");
	    $("#filter-tab a").attr("data-toggle", "tab");
		$("#text-title").prop("disabled",false);
	    $("#text-minscale").prop("disabled",false);
	    $("#text-maxscale").prop("disabled",false);
		$('#label-has-label-on').prop('checked', true)
	}
};

TextSymbolizer.prototype.is_activated = function() {
	return this.is_actived;
}

TextSymbolizer.prototype.is_label_actived = function() {
	return this.is_label_actived;
}

TextSymbolizer.prototype.updatePreview = function() {
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
};


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
		xml += 				'<AnchorPointY>0.5</AnchorPointY>';
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
		is_label_actived: this.is_label_actived,
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
		anchor_point_x: this.AnchorPointX,
		anchor_point_y: this.AnchorPointY,
		filter : filter_cql,
		order: this.order
	};
	
	return JSON.stringify(object);
};