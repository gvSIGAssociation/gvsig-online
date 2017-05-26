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
 
 
var Expressions = function(featureType, layerName, utils, previewUrl) {
	this.selected = null;
	this.featureType = featureType;
	this.layerName = layerName;
	this.previewUrl = previewUrl;
	this.utils = utils;
	this.rules = new Array();
	this.label = null;
	this.expressions_counter = 0;
};

Expressions.prototype.showLabel = function() {
	if (this.label) {
		this.updateLabelForm();
		$('#modal-symbolizer').modal('show');
		
	} else {
		this.label = new TextSymbolizer(this.rule, null, this.utils);
		this.updateLabelForm();
		$('#modal-symbolizer').modal('show');
	}
};

Expressions.prototype.loadLabel = function(options) {
	if (this.label) {
		this.label = null;
		this.label = new TextSymbolizer(this.rule, options, this.utils);
		this.updateLabelForm();
		
	} else {
		this.label = new TextSymbolizer(this.rule, options, this.utils);
		this.updateLabelForm();
	}
};

Expressions.prototype.updateLabelForm = function() {
	$('#tab-menu').empty();
	$('#tab-content').empty();	
	
	$('#tab-menu').append(this.label.getTabMenu());

	$('#tab-content').append(this.label.getFontTabUI());
	$('#tab-content').append(this.label.getHaloTabUI());
	$('.nav-tabs a[href="#label-font-tab"]').tab('show');
	this.label.registerEvents();
	
};

Expressions.prototype.addNewRule = function() {
	var self = this;
	
	var id = this.rules.length;
	var name = gettext('rule') + '_' + id;
	var title = gettext('Rule') + ' ' + id;
	var rule = new Rule(id, name, title, null, this.utils);
	$('#rules').append(rule.getTableUI(true, 'expressions'));
	rule.registerEvents();
	rule.addSymbolizer();
	rule.preview();
	this.addRule(rule);
	
	$(".create-expression").on('click', function(e){
		e.preventDefault();
		self.getFilterFormUI(this.dataset.ruleid);
		$('#modal-expression').modal('show');
		$('.CodeMirror').each(function(i, el){
		    el.CodeMirror.refresh();
		});
	});
};

Expressions.prototype.getFilterFormUI = function(ruleid) {
	var self = this;
	var language = $("#select-language").val();
	$('#modal-expression-content').empty();
	
	var operations = this.utils.getFilterOperations();
	var fields = this.utils.getAlphanumericFields();
	
	var rule = this.getRuleById(ruleid);
	var dataType = '';
	
	var ui = '';
	ui += '<div class="box">';
	ui += 	'<div class="box-header with-border">';
	ui += 		'<h3 class="box-title">' + gettext('Expressions') + '</h3>';
	ui += 		'<div class="box-tools pull-right">';
	//ui += 			'<button id="add-new-expression" class="btn btn-sm btn-success margin-r-5"><i class="fa fa-plus margin-r-5"></i> ' + gettext('Add expression') + '</button>';
	ui += 			'<button id="save-filter" data-ruleid="' + ruleid + '" class="btn btn-sm btn-default save-filter"><i class="fa fa-floppy-o margin-r-5"></i> ' + gettext('Save filter') + '</button>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="box-body">';
	ui += 		'<div id="expressions-list" class="expressions-list">';
	ui += 			'<div class="box">';
	ui += 				'<div class="box-header">';
	ui += 					'<div class="box-tools pull-right">';
	ui += 						'<button class="btn btn-box-tool btn-box-tool-custom" data-widget="collapse">';
	ui += 							'<i class="fa fa-minus"></i>';
	ui += 						'</button>';
	ui += 					'</div>';
	ui += 				'</div>';
	ui += 				'<div class="box-body">';
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
		if (rule.filter.property_name && rule.filter.property_name == fields[i].name) {
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
		if (rule.filter.type && rule.filter.type == operations[i].value) {
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
	ui += 				'</div>';
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 		'<div class="row">';
	ui += 			'<div class="col-md-12 form-group">';
	ui += 				'<label>' + gettext('Filter preview') + '</label>';
	ui += 				'<textarea id="filter-output" name="code">	';					
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	$('#modal-expression-content').append(ui);
	
	var filterOutput = document.getElementById('filter-output');
	this.codemirror = CodeMirror.fromTextArea(filterOutput, {
		value: "",
		mode:  "javascript",
		theme: "xq-dark",
		lineNumbers: true
	});
	
	if (rule.filter.type) {
		var filterOutputContentcode = '';
		if (rule.filter.type == 'is_between') {
			var inputs = self.getFilterInputs(dataType, true);
			$('#expression-values').empty();
			$('#expression-values').append(inputs);
			$('#expresion-value-1').val(rule.filter.value1);
			$('#expresion-value-2').val(rule.filter.value2);
			
			this.codemirror.setValue('');
			filterOutputContentcode = this.getFilterOutput(rule.filter.property_name, rule.filter.type, rule.filter.value1, rule.filter.value2);
			this.codemirror.setValue(filterOutputContentcode);
			
		} else {
			var inputs = self.getFilterInputs(dataType, false);
			$('#expression-values').empty();
			$('#expression-values').append(inputs);
			$('#expresion-value-1').val(rule.filter.value1);
			
			this.codemirror.setValue('');
			filterOutputContentcode = this.getFilterOutput(rule.filter.property_name, rule.filter.type, rule.filter.value1, rule.filter.value2);
			this.codemirror.setValue(filterOutputContentcode);
			
		}
	}
	
	this.registerFilterEvents();
	
};

Expressions.prototype.getFilterInputs = function(type, twoValues) {
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

Expressions.prototype.getFilterOutput = function(field, operation, value1, value2) {
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

Expressions.prototype.registerFilterEvents = function() {
	
	var self = this;
	
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
	
	$('.save-filter').on('click', function(){
		var ruleid = this.dataset.ruleid;
		var rule = self.getRuleById(ruleid);
		
		var value1 = $('#expresion-value-1').val();
		var value2 = $('#expresion-value-2').val();
		var field = $('#expression-field').val();
		var operation = $('#expression-operation').val();
		
		var filterOutputContentcode = self.getFilterOutput(field, operation, value1, value2);
		
		var filter = {
			type: operation,
			property_name: field,
			value1: value1
		};
		if (operation == 'is_between') {
			filter['value2'] = value2;
		}
		rule.setFilter(filter);
		rule.title = filterOutputContentcode.replace('\t', '');
		
		$('#rule-title-' + ruleid).text(filterOutputContentcode);
		$('#modal-expression').modal('hide');
	});
};

Expressions.prototype.getRules = function() {
	return this.rules;
};

Expressions.prototype.getRuleById = function(id) {
	for (var i=0; i < this.rules.length; i++) {
		if (this.rules[i].id == id) {
			return this.rules[i];
		}
	}
};

Expressions.prototype.addRule = function(rule) {
	return this.rules.push(rule);
};

Expressions.prototype.deleteRule = function(id) {
	for (var i=0; i < this.rules.length; i++) {
		if (this.rules[i].id == id) {
			this.rules.splice(i, 1);
		}
	}
	var htmlRules = document.getElementById("rules");
	for (var i=0; i<htmlRules.children.length; i++) {
		if(htmlRules.children[i].dataset.ruleid == id) {
			htmlRules.removeChild(htmlRules.children[i]);
		}
	}
};

Expressions.prototype.load = function(selectedField, values) {
	$('#rules').empty();
	this.rules.splice(0, this.rules.length);
	for (var i=0; i<values.length; i++) {
		var ruleName = "rule_" + i;
		var ruleTitle = values[i];
		var rule = new Rule(i, ruleName, ruleTitle, null, this.utils);
		var filter = {
			type: 'is_equal',
			property_name: selectedField,
			value1: values[i]
		};
		rule.setFilter(filter);
		$('#rules').append(rule.getTableUI(true, 'expressions'));
		rule.registerEvents();
		var colors = this.utils.createColorRange('random', values.length);
		rule.addSymbolizer({fill: colors[i]});
		rule.preview();
		this.addRule(rule);
	}
};

Expressions.prototype.loadRules = function(rules) {
	var self = this;
	$('#rules').empty();
	this.rules.splice(0, this.rules.length);
	for (var i=0; i<rules.length; i++) {
		var rule = new Rule(rules[i].id, rules[i].name, rules[i].title, null, this.utils);
		if (rules[i].filter != '') {
			var filter = JSON.parse(rules[i].filter);
			rule.setFilter(filter);
		}
			
		rule.removeAllSymbolizers();
		rule.removeLabel();
		$('#rules').append(rule.getTableUI(true, 'expressions'));
		
		for (var j=0; j<rules[i].symbolizers.length; j++) {
			
			var symbolizer = JSON.parse(rules[i].symbolizers[j].json);
			var order = rules[i].symbolizers[j].order;
			var options = symbolizer[0].fields;
			options['order'] = order;
			
			if (symbolizer[0].model == 'gvsigol_symbology.textsymbolizer') {
				this.loadLabel(options);
				
			} else if (symbolizer[0].model == 'gvsigol_symbology.externalgraphicsymbolizer') {
				rule.addExternalGraphicSymbolizer(options);
				
			} else {
				rule.addSymbolizer(options);
			}	
			
		}
		
		rule.registerEvents();
		rule.preview();
		this.addRule(rule);
		
		$(".create-expression").on('click', function(e){
			e.preventDefault();
			self.getFilterFormUI(this.dataset.ruleid);
			$('#modal-expression').modal('show');
			$('.CodeMirror').each(function(i, el){
			    el.CodeMirror.refresh();
			});
		});
	}
};

Expressions.prototype.refreshMap = function() {
	this.utils.updateMap(this, this.layerName);
};

Expressions.prototype.save = function(layerId) {
	
	$("body").overlay();
	
	var style = {
		name: $('#style-name').val(),
		title: $('#style-title').val(),
		is_default: $('#style-is-default').is(":checked"),
		rules: new Array()
	};
	
	for (var i=0; i<this.rules.length; i++) {
		var symbolizers = new Array();
		for (var j=0; j < this.rules[i].getSymbolizers().length; j++) {
			var symbolizer = {
				type: this.rules[i].getSymbolizers()[j].type,
				json: this.rules[i].getSymbolizers()[j].toJSON(),
				order: this.rules[i].getSymbolizers()[j].order
			};
			symbolizers.push(symbolizer);
		}
		
		if (this.label != null) {
			var l = {
				type: this.label.type,
				json: this.label.toJSON(),
				order: this.label.order
			};
			symbolizers.push(l);
		}
		
		symbolizers.sort(function(a, b){
			return parseInt(b.order) - parseInt(a.order);
		});
		
		var rule = {
			rule: this.rules[i].getObject(),
			symbolizers: symbolizers
		};
		style.rules.push(rule);
	}
	
	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/expressions_add/" + layerId + "/",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		data: {
			style_data: JSON.stringify(style)
		},
		success: function(response){
			if (response.success) {
				location.href = "/gvsigonline/symbology/style_layer_list/";
			} else {
				alert('Error');
			}
			
		},
	    error: function(){}
	});
};

Expressions.prototype.update = function(layerId, styleId) {
	
	$("body").overlay();
	
	var style = {
		name: $('#style-name').val(),
		title: $('#style-title').val(),
		is_default: $('#style-is-default').is(":checked"),
		rules: new Array()
	};
	
	for (var i=0; i<this.rules.length; i++) {
		var symbolizers = new Array();
		for (var j=0; j < this.rules[i].getSymbolizers().length; j++) {
			var symbolizer = {
				type: this.rules[i].getSymbolizers()[j].type,
				json: this.rules[i].getSymbolizers()[j].toJSON(),
				order: this.rules[i].getSymbolizers()[j].order
			};
			symbolizers.push(symbolizer);
		}
		
		if (this.label != null) {
			var l = {
				type: this.label.type,
				json: this.label.toJSON(),
				order: this.label.order
			};
			symbolizers.push(l);
		}
		
		symbolizers.sort(function(a, b){
			return parseInt(b.order) - parseInt(a.order);
		});
		
		var rule = {
			rule: this.rules[i].getObject(),
			symbolizers: symbolizers
		};
		style.rules.push(rule);
	}
	
	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/expressions_update/" + layerId + "/" + styleId + "/",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		data: {
			style_data: JSON.stringify(style)
		},
		success: function(response){
			if (response.success) {
				location.href = "/gvsigonline/symbology/style_layer_list/";
			} else {
				alert('Error');
			}
			
		},
	    error: function(){}
	});
};