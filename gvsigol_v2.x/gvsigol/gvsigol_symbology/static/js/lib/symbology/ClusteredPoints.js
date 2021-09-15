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


var ClusteredPoints = function(featureType, layerName, utils, previewUrl) {
	this.selected = null;
	this.featureType = featureType;
	this.layerName = layerName;
	this.previewUrl = previewUrl;
	this.utils = utils;
	this.rules = new Array();
	this.label = null;
	this.rules = new Array();
	this.expressions = new Array();
	this.expressions_counter = 0;
};

ClusteredPoints.prototype.showLabel = function() {
	if (this.label) {
		this.updateLabelForm();
		$('#modal-symbolizer').modal('show');

	} else {
		this.label = new TextSymbolizer(this.rule, this.layerName, null, this.utils);
		this.updateLabelForm();
		$('#modal-symbolizer').modal('show');
	}
};

ClusteredPoints.prototype.loadLabel = function(options) {
	if (this.label) {
		this.label = null;
		this.label = new TextSymbolizer(this.rule, this.layerName, options, this.utils);
		this.updateLabelForm();

	} else {
		this.label = new TextSymbolizer(this.rule, this.layerName, options, this.utils);
		this.updateLabelForm();
	}
};

ClusteredPoints.prototype.updateLabelForm = function() {
	$('#tab-menu').empty();
	$('#tab-content').empty();	

	$('#tab-menu').append(this.label.getTabMenu());

	$('#tab-content').append(this.label.getGeneralTabUI());
	$('#tab-content').append(this.label.getFontTabUI());
	$('#tab-content').append(this.label.getHaloTabUI());
	$('#tab-content').append(this.label.getFilterTabUI());
	$('.nav-tabs a[href="#label-general-tab"]').tab('show');
	this.label.registerEvents();

};

ClusteredPoints.prototype.addNewRule = function(filter_value, filter_value2) {
	var self = this;
	this.expressions = [];
	var id = this.rules.length;
	var name = gettext('rule') + '_' + id;
	var title = gettext('Single feature');
	var minscale = $('#symbol-minscale').val();
	var maxscale = $('#symbol-maxscale').val();
	
	var filter = "";
	var is_single = true;
	if(filter_value != null && filter_value != ""){
		if(filter_value2 != null && filter_value2 != ""){
			var expression = {
					id: this.expressions_counter,
					type: 'expression',
					field: 'count',
					operation: 'is_greater_than_or_equal_to',
					value: ""+filter_value
				};
			this.expressions.push(expression);
			var filter = {
					operation: 'is_greater_than_or_equal_to',
					field: 'count',
					value: ""+filter_value
			};
			this.expressions_counter = this.expressions_counter + 1;
			
			var andOperator = {
					id: this.expressions_counter,
					type: 'and'
				};
			this.expressions.push(andOperator);
			this.expressions_counter = this.expressions_counter + 1;
			
			var expression2 = {
					id: this.expressions_counter,
					type: 'expression',
					field: 'count',
					operation: 'is_less_than',
					value: ""+filter_value2
				};
			this.expressions.push(expression2);
			var filter2 = {
					operation: 'is_less_than',
					field: 'count',
					value: ""+filter_value2
			};
			this.expressions_counter = this.expressions_counter + 1;
		}else{
			var expression = {
					id: this.expressions_counter,
					type: 'expression',
					field: 'count',
					operation: 'is_greater_than_or_equal_to',
					value: ""+filter_value
				};
			this.expressions.push(expression);
			var filter = {
					operation: 'is_greater_than_or_equal_to',
					field: 'count',
					value: ""+filter_value
			};
			
			title = gettext('Default group')+' (>= ' + filter_value + ' '+ gettext('features')+')';
			is_single = false;
		}
	}
	
	var options = {
			"id" : id,
			"name" : name,
			"title" : title,
			"abstract" : "",
			"filter" : filter,
			"minscale" : minscale,
			"maxscale" : maxscale,
			"order" :  id, 
	}

	var rule = new Rule(id, name, title, options, this.utils);
	$('#rules').append(rule.getTableUI(true, 'clusteredpoints'));
	rule.registerEvents();
	mainpoint = rule.addSymbolizer();
	rule.preview();
	this.addRule(rule);
	
	for(var i = 0; i< rule.symbolizers.length; i++){
		var sym = rule.symbolizers[i];
		sym.updatePreview();
	}

	$(".create-expression").on('click', function(e){
		e.preventDefault();
		self.getFilterFormUI(this.dataset.ruleid);
		$('#modal-expression').modal('show');
	});
	
	rule.setFilter(this.expressions);
	if(!is_single){
		mainpoint.size = 30
		textsymbolizer = rule.addTextSymbolizer(options);
		textsymbolizer.fill = "#ffffff";
		textsymbolizer.label = "count";
		textsymbolizer.AnchorPointX = 0.5;
		textsymbolizer.AnchorPointY = 0.8;
	}
};

ClusteredPoints.prototype.getFilterFormUI = function(ruleid) {
	var self = this;

	$('#modal-expression-content').empty();
	this.expressions = [];
	this.expressions_counter = 0;
	
	var ui = '';
	ui += '<div class="box">';
	ui += 	'<div class="box-header with-border">';
	ui += 		'<h3 class="box-title">' + gettext('Expressions') + '</h3>';
	ui += 		'<div class="box-tools pull-right">';
	ui += 			'<div class="btn-group">';
	ui += 				'<button type="button" class="btn btn-sm btn-success">'+gettext("Add")+'</button>';
	ui += 				'<button type="button" class="btn btn-sm btn-success margin-r-5 dropdown-toggle" data-toggle="dropdown" aria-expanded="false">';
	ui += 					'<span class="caret"></span>';
	ui += 					'<span class="sr-only">Toggle Dropdown</span>';
	ui += 				'</button>';
	ui += 				'<ul class="dropdown-menu" role="menu">';
	ui += 					'<li><a id="add-and" data-ruleid="' + ruleid + '" href="#">'+gettext("AND expression")+'</a></li>';
	ui += 					'<li><a id="add-or" data-ruleid="' + ruleid + '" href="#">'+gettext("OR expression")+'</a></li>';
	ui += 				'</ul>';
	ui += 			'</div>';
	ui += 			'<button id="save-filter" data-ruleid="' + ruleid + '" class="btn btn-sm btn-default save-filter"><i class="fa fa-floppy-o margin-r-5"></i> ' + gettext('Save filter') + '</button>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="box-body">';
	ui += 		'<div id="expressions-list" class="expressions-list">';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';

	$('#modal-expression-content').append(ui);
	
	var r = this.getRuleById(ruleid);
	if (r.filter && r.filter.length > 0){
		for (var i=0; i<r.filter.length; i++) {
			if (r.filter[i].type == 'expression') {
				var expression = {
					id: self.expressions_counter,
					type: 'expression',
					field: r.filter[i].field,
					operation: r.filter[i].operation,
					value: r.filter[i].value
				};
				self.expressions.push(expression);
				$('#expressions-list').append(self.addExpression(expression));
				var inputs = '';
				inputs += '<div class="col-md-12 form-group">';
				inputs += 	'<label>' + gettext('Value') + '</label>';
				inputs += 	'<input type="text" id="expression-value-select'+expression.id+'" class="form-control filter-component" list="expression-value-list'+expression.id+'">';
				inputs += 	'<datalist id="expression-value-list'+expression.id+'">';
				inputs += 	'</datalist>';
				inputs += '</div>';
				
				$('#expression-value'+expression.id).empty();
				$('#expression-value'+expression.id).append(inputs);
				self.loadUniqueValues(expression.field, expression.id);
				$('#remove-expression' + self.expressions_counter).on('click', function(e){
					e.preventDefault();
					self.deleteExpression(this.dataset.expressionid);
					this.parentNode.parentNode.parentNode.remove();
					self.expressions_counter = self.expressions_counter - 1;
				});
				self.registerFilterEvents(self.expressions_counter);
				self.expressions_counter = self.expressions_counter + 1;
				
			} else if (r.filter[i].type == 'and') {
				var andOperator = {
					id: self.expressions_counter,
					type: 'and'
				};
				self.expressions.push(andOperator);
				$('#expressions-list').append(self.addAndOperator(r));	
				$('#remove-and' + self.expressions_counter).on('click', function(e){
					e.preventDefault();
					self.removeOperatorExpression(this.dataset.expressionid, $(this));
				});
				self.registerFilterEvents(self.expressions_counter);
				self.expressions_counter = self.expressions_counter + 1;
				
			} else if (r.filter[i].type == 'or') {
				var orOperator = {
					id: self.expressions_counter,
					type: 'or'
				};
				self.expressions.push(orOperator);
				$('#expressions-list').append(self.addOrOperator(r));
				$('#remove-or' + self.expressions_counter).on('click', function(e){
					e.preventDefault();
					self.removeOperatorExpression(this.dataset.expressionid, $(this));
				});
				self.registerFilterEvents(self.expressions_counter);
				self.expressions_counter = self.expressions_counter + 1;
			}
		}
	}else{
		self.addNewExpression(ruleid);
	}
	
	for(var ix = 0; ix< self.expressions.length; ix++){
		if(self.expressions[ix].type == "expression"){
			$('#remove-expression' + self.expressions[ix].id).css("display", "none");
		}
	}
	$('#save-filter').on('click', function(){
		var ruleid = this.dataset.ruleid;
		var rule = self.getRuleById(ruleid);

		if(self.expressions.length > 1 || 
				(self.expressions.length >0 && self.expressions[0].field != "" && self.expressions[0].operation != "" )){
			rule.setFilter(self.expressions);
		}
		$('#modal-expression').modal('hide');
	});
	
	$('#add-new-expression').on('click', function(){
		self.addNewExpression(this.dataset.ruleid);
	});
	
	$('#add-and').on('click', function(){
		self.addANDExpression(this.dataset.ruleid);
		self.addNewExpression(this.dataset.ruleid);
	});
	
	$('#add-or').on('click', function(){
		self.addORExpression(this.dataset.ruleid);
		self.addNewExpression(this.dataset.ruleid);
	});

};

ClusteredPoints.prototype.addNewExpression = function(ruleid) {
	var self = this;
	
	var rule = self.getRuleById(ruleid);
	var expression = {
		id: self.expressions_counter,
		type: 'expression',
		field: '',
		operation: '',
		value: ''
	};
	self.expressions.push(expression);
	$('#expressions-list').append(self.addExpression(expression));
	$('#remove-expression' + self.expressions_counter).css("display", "none");
	$('#remove-expression' + self.expressions_counter).on('click', function(e){
		e.preventDefault();
		self.deleteExpression(this.dataset.expressionid);
		this.parentNode.parentNode.parentNode.remove();
		self.expressions_counter = self.expressions_counter - 1;
	});
	self.registerFilterEvents(self.expressions_counter);
	self.expressions_counter = self.expressions_counter + 1;
};



ClusteredPoints.prototype.addANDExpression = function(ruleid) {
	var self = this;
	
	var rule = self.getRuleById(ruleid);
	var andOperator = {
		id: self.expressions_counter,
		type: 'and'
	};
	self.expressions.push(andOperator);
	$('#expressions-list').append(self.addAndOperator(rule));	
	$('#remove-and' + self.expressions_counter).on('click', function(e){
		e.preventDefault();
		self.removeOperatorExpression(this.dataset.expressionid, $(this));
	});
	self.registerFilterEvents(self.expressions_counter);
	self.expressions_counter = self.expressions_counter + 1;
};


ClusteredPoints.prototype.addORExpression = function(ruleid) {
	var self = this;
	
	var rule = self.getRuleById(ruleid);
	var orOperator = {
		id: self.expressions_counter,
		type: 'or'
	};
	self.expressions.push(orOperator);
	$('#expressions-list').append(self.addOrOperator(rule));
	$('#remove-or' + self.expressions_counter).on('click', function(e){
		e.preventDefault();
		self.removeOperatorExpression(this.dataset.expressionid, $(this));
	});
	self.registerFilterEvents(self.expressions_counter);
	self.expressions_counter = self.expressions_counter + 1;
};

ClusteredPoints.prototype.removeOperatorExpression = function(expressionid, component) {
	var self = this;
	
	var parent = component.parent().parent().parent();
	var next = parent.next();
	var nextbutton = next.find("button.btn-box-tool").first();
	nextxpressionid = nextbutton.attr("data-expressionid");
	self.removeExpression(expressionid, $(component));
	self.removeExpression(nextxpressionid, nextbutton);
};

ClusteredPoints.prototype.removeExpression = function(expressionid, component) {
	var self = this;
	
	self.deleteExpression(expressionid);
	component.parent().parent().parent().remove();
	self.expressions_counter = self.expressions_counter - 1;
};

ClusteredPoints.prototype.getExpressionById = function(id) {
	for (var i=0; i < this.expressions.length; i++) {
		if (this.expressions[i].id == id) {
			return this.expressions[i];
		}
	}
};

ClusteredPoints.prototype.updateExpression = function(id, field, operation, value) {
	for (var i=0; i < this.expressions.length; i++) {
		if (this.expressions[i].id == id) {
			this.expressions[i].field = field;
			this.expressions[i].operation = operation;
			this.expressions[i].value = value;
		}
	}
};

ClusteredPoints.prototype.deleteExpression = function(id) {
	for (var i=0; i < this.expressions.length; i++) {
		if (this.expressions[i].id == id) {
			this.expressions.splice(i, 1);
		}
	}
};

ClusteredPoints.prototype.addExpression = function(expression) {
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
	ui += 			'<button data-expressionid="'+count+'" id="remove-expression'+count+'" class="btn btn-box-tool" style="color:red;" data-widget="collapse">';
	ui += 				'<i class="fa fa-times"></i>';
	ui += 			'</button>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="box-body">';
	ui += 		'<div class="row">';
	ui += 			'<div class="col-md-6 form-group">';
	ui += 				'<label>' + gettext('Select field') + '</label>';
	ui += 				'<select data-expressionid="'+count+'" id="expression-field'+count+'" class="form-control expression-field">';
	ui += 					'<option selected value="count">' + gettext('Count features') + '</option>';
//	for (var i in fields) {
//		var field_name = fields[i].name;
//		var field_name_trans = fields[i]["title-"+language];
//		if(!field_name_trans){
//			field_name_trans = field_name;
//		}
//		if (expression.field == fields[i].name) {
//			ui += 			'<option selected data-type="' + fields[i].binding + '" value="' + field_name + '">' + field_name_trans + '</option>';
//			dataType = fields[i].binding;
//		} else {
//			ui += 			'<option data-type="' + fields[i].binding + '" value="' + field_name + '">' + field_name_trans + '</option>';
//		}
//
//	}	
	ui += 				'</select>';
	ui += 			'</div>';
	ui += 			'<div class="col-md-6 form-group">';
	ui += 				'<label>' + gettext('Select operation') + '</label>';
	ui += 				'<select data-expressionid="'+count+'" id="expression-operation'+count+'" class="form-control expression-operation">';
	ui += 					'<option disabled selected value> -- ' + gettext('Select operation') + ' -- </option>';
	for (var i in operations) {
		if (operations[i].value != 'is_like' && operations[i].value != 'is_between' && operations[i].value != 'is_null') {
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
	ui += 		'<div data-expressionid="'+count+'" id="expression-value'+count+'" class="row">';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

ClusteredPoints.prototype.addAndOperator = function(rule) {
	var count = this.expressions_counter;
	
	var andOperator = '';
	andOperator += '<div class="box">';
	andOperator += 	'<div class="box-header" style="text-align: center; padding: 18px;">';
	andOperator += 		'AND';
	andOperator += 		'<div class="box-tools pull-right">';
	andOperator += 			'<button data-expressionid="'+count+'" id="remove-and'+count+'" class="btn btn-box-tool" style="color:red;" data-widget="collapse">';
	andOperator += 				'<i class="fa fa-times"></i>';
	andOperator += 			'</button>';
	andOperator += 		'</div>';
	andOperator += 	'</div>';
	andOperator += '</div>';
	
	return andOperator;
};

ClusteredPoints.prototype.addOrOperator = function(rule) {
	var count = this.expressions_counter;
	
	var orOperator = '';
	orOperator += '<div class="box">';
	orOperator += 	'<div class="box-header" style="text-align: center; padding: 18px;">';
	orOperator += 		'OR';
	orOperator += 		'<div class="box-tools pull-right">';
	orOperator += 			'<button data-expressionid="'+count+'" id="remove-or'+count+'" class="btn btn-box-tool" style="color:red;" data-widget="collapse">';
	orOperator += 				'<i class="fa fa-times"></i>';
	orOperator += 			'</button>';
	orOperator += 		'</div>';
	orOperator += 	'</div>';
	orOperator += '</div>';
	
	return orOperator;
};

ClusteredPoints.prototype.loadUniqueValues = function(field, expressionId) {
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
			  		$("#expression-value-list"+expressionId).empty();
			  		$("#expression-value-select"+expressionId).val(expression.value);
			  		$.each(response.values, function(index, option) {
			  			if (expression.value == option) {
			  				$option = $("<option selected></option>").attr("value", option).text(option);
				  			$("#expression-value-list"+expressionId).append($option);
			  			} else {
			  				$option = $("<option></option>").attr("value", option).text(option);
				  			$("#expression-value-list"+expressionId).append($option);
			  			}
			  			
			  	    });
			  		
			  		$('#expression-value-select'+expressionId).on('change', function(){
			  			var value = $('#expression-value-select'+expressionId).val();
			  			var field = $('#expression-field'+expressionId).val();
			  			var operation = $('#expression-operation'+expressionId).val();
			  			self.updateExpression(expressionId, field, operation, value);
			  		});
				},
			  	error: function(){}
			});
		}
	}
};


ClusteredPoints.prototype.registerFilterEvents = function(expressionId) {

	var self = this;

	$('#expression-field'+expressionId).on('change', function(e) {
		var inputs = '';
		inputs += '<div class="col-md-12 form-group">';
		inputs += 	'<label>' + gettext('Value') + '</label>';
		inputs += 	'<input type="text" id="expression-value-select'+expressionId+'" class="form-control filter-component" list="expression-value-list'+expressionId+'">';
		inputs += 	'<datalist id="expression-value-list'+expressionId+'">';
		inputs += 	'</datalist>';
		inputs += '</div>';
		
		$('#expression-value'+expressionId).empty();
		$('#expression-value'+expressionId).append(inputs);

		var value = $('#expression-value-select'+expressionId).val();
		var field = $('#expression-field'+expressionId).val();
		var operation = $('#expression-operation'+expressionId).val();
		self.updateExpression(expressionId, field, operation, value);

		var value_orig = $('#expression-field'+expressionId).val();
		self.loadUniqueValues(value_orig, expressionId);
	});

	$('#expression-operation'+expressionId).on('change', function(e) {
		var inputs = '';
		inputs += '<div class="col-md-12 form-group">';
		inputs += 	'<label>' + gettext('Value') + '</label>';
		inputs += 	'<input type="text" id="expression-value-select'+expressionId+'" class="form-control filter-component" list="expression-value-list'+expressionId+'">';
		inputs += 	'<datalist id="expression-value-list'+expressionId+'">';
		inputs += 	'</datalist>';
		inputs += '</div>';
		
		$('#expression-value'+expressionId).empty();
		$('#expression-value'+expressionId).append(inputs);

		var value = $('#expression-value-select'+expressionId).val();
		var field = $('#expression-field'+expressionId).val();
		var operation = $('#expression-operation'+expressionId).val();
		self.updateExpression(expressionId, field, operation, value);

		var value_orig = $('#expression-field'+expressionId).val();
		self.loadUniqueValues(value_orig, expressionId);
	});

};

ClusteredPoints.prototype.getRules = function() {
	return this.rules;
};

ClusteredPoints.prototype.getRuleById = function(id) {
	for (var i=0; i < this.rules.length; i++) {
		if (this.rules[i].id == id) {
			return this.rules[i];
		}
	}
};

ClusteredPoints.prototype.addRule = function(rule) {
	return this.rules.push(rule);
};

ClusteredPoints.prototype.deleteRule = function(id) {
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

ClusteredPoints.prototype.load = function(selectedField, values) {
	$('#rules').empty();
	this.rules.splice(0, this.rules.length);
	for (var i=0; i<values.length; i++) {
		var ruleName = "rule_" + i;
		var ruleTitle = values[i];
		var minscale = $('#symbol-minscale').val();
		var maxscale = $('#symbol-maxscale').val();

		var options = {
				"id" : this.rules.length,
				"name" : ruleName,
				"title" : ruleTitle,
				"abstract" : "",
				"filter" : "",
				"minscale" : minscale,
				"maxscale" : maxscale,
				"order" :  i
		}

		var rule = new Rule(i, ruleName, ruleTitle, options, this.utils);
		var filter = {
				operation: 'is_equal',
				field: selectedField,
				value: values[i]
		};
		rule.setFilter(filter);
		$('#rules').append(rule.getTableUI(true, 'clusteredpoints'));
		rule.registerEvents();
		var colors = this.utils.createColorRange('random', values.length);
		rule.addSymbolizer({fill: colors[i]});
		rule.preview();
		this.addRule(rule);
	}
};

ClusteredPoints.prototype.loadRules = function(rules) {
	var self = this;
	$('#rules').empty();
	this.rules.splice(0, this.rules.length);
	for (var i=0; i<rules.length; i++) {
		var filter = "";
		if(rules[i].filter != ""){
			filter = JSON.parse(rules[i].filter);
		}
		var options = {
				"id" : rules[i].id,
				"name" : rules[i].name,
				"title" : rules[i].title,
				"abstract" : "",
				"filter" : filter,
				"minscale" : rules[i].minscale,
				"maxscale" : rules[i].maxscale,
				"order" : rules[i].order
		}

		var rule = new Rule(rules[i].id, rules[i].name, rules[i].title, options, this.utils);
		if(rules[i].filter != ""){
			var filter = JSON.parse(rules[i].filter);
			rule.setFilter(filter);
		}
		rule.removeAllSymbolizers();
		rule.removeLabel();

		if(!rules[i].name.endsWith("_text")){
			$('#rules').append(rule.getTableUI(true, 'clusteredpoints'));
		}

		for (var j=0; j<rules[i].symbolizers.length; j++) {
			var symbolizer = JSON.parse(rules[i].symbolizers[j].json);
			var order = rules[i].symbolizers[j].order;
			var options = symbolizer[0].fields;
			options['order'] = order;

			if (symbolizer[0].model == 'gvsigol_symbology.textsymbolizer' && rules[i].name.endsWith("_text")) {
				options['is_actived'] = true;
				options['title'] = rules[i].title;
				options['minscale'] = rules[i].minscale;
				options['maxscale'] = rules[i].maxscale;
				options['filter'] = "";
				if(rules[i].filter && rules[i].filter.length>0){
					options['filter'] = JSON.parse(rules[i].filter);
				}
				this.loadLabel(options);

			} else if (symbolizer[0].model == 'gvsigol_symbology.externalgraphicsymbolizer') {
				rule.addExternalGraphicSymbolizer(options);

			} else {
				if (symbolizer[0].model == 'gvsigol_symbology.textsymbolizer') {
					textsymbolizer = rule.addTextSymbolizer(options);
//					textsymbolizer.fill = "#ffffff";
//					textsymbolizer.label = "count";
//					textsymbolizer.AnchorPointX = 0.5;
//					textsymbolizer.AnchorPointY = 0.8;

				}else{
					rule.addSymbolizer(options);
				}
			}	

		}

		rule.registerEvents();
		rule.preview();
		this.addRule(rule);
		
		for(var k = 0; k< rule.symbolizers.length; k++){
			var sym = rule.symbolizers[k];
			sym.updatePreview();
		}

		$(".create-expression").on('click', function(e){
			e.preventDefault();
			self.getFilterFormUI(this.dataset.ruleid);
			$('#modal-expression').modal('show');
		});
	}
};

ClusteredPoints.prototype.refreshMap = function() {
	this.utils.updateMap(this, this.layerName);
};

ClusteredPoints.prototype.save = function(layerId) {
	$("body").overlay();
	style = this.getStyleDef();

	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/clustered_points_add/" + layerId + "/",
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
				$("body").overlayout();
			}

		},
		error: function(){}
	});
};

ClusteredPoints.prototype.update = function(layerId, styleId) {
	$("body").overlay();
	style = this.getStyleDef();


	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/clustered_points_update/" + layerId + "/" + styleId + "/",
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
				$("body").overlayout();
			}

		},
		error: function(){}
	});
};


ClusteredPoints.prototype.getStyleDef = function() {

	var minscale = $('#symbol-minscale').val();
	if(minscale == "" || minscale < 0){
		minscale = -1;
	}

	var maxscale = $('#symbol-maxscale').val();
	if(maxscale == "" || maxscale < 0){
		maxscale = -1;
	}


	var style = {
			name: $('#style-name').val(),
			title: $('#style-title').val(),
			minscale: minscale,
			maxscale: maxscale,
			is_default: $('#style-is-default').is(":checked"),
			rules: new Array()
	};

	for (var i=0; i<this.rules.length; i++) {
		if(!this.rules[i].name.endsWith("_text")){
			var symbolizers = new Array();
			for (var j=0; j < this.rules[i].getSymbolizers().length; j++) {
				var symbolizer = {
						type: this.rules[i].getSymbolizers()[j].type,
						json: this.rules[i].getSymbolizers()[j].toJSON(),
						order: this.rules[i].getSymbolizers()[j].order
				};
				symbolizers.push(symbolizer);
			}

			symbolizers.sort(function(a, b){
				return parseInt(a.order) - parseInt(b.order);
			});

			var rule = {
					rule: this.rules[i].getObject(),
					symbolizers: symbolizers
			};
			style.rules.push(rule);
		}
	}


	if (this.label != null && this.label.is_activated()) {
		var ruleName = "rule_" + this.rules.length +"_text";
		var ruleTitle = this.label.title;
		var l = {
				type: this.label.type,
				json: this.label.toJSON(),
				order: this.label.order
		};

		var options = {
				"id" : this.rules.length,
				"name" : ruleName,
				"title" : ruleTitle,
				"abstract" : "",
				"filter" : this.label.filterCode,
				"minscale" : this.label.minscale,
				"maxscale" :  this.label.maxscale,
				"order" :  this.label.order
		}
		var rl = new Rule(i, ruleName, ruleTitle, options, this.utils);
		var rule = {
				rule: rl.getObject(),
				symbolizers: [l]
		};
		style.rules.push(rule);
	}
	return style;
	
}


ClusteredPoints.prototype.updatePreview = function(layerId) {
	var self = this;
	//$("body").overlay();
	style = this.getStyleDef();

	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/update_preview/" + layerId +  "/",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		data: {
			style_data: JSON.stringify(style),
			style: 'CP'
		},
		success: function(response){
			if (response.success) {
				self.utils.reloadLayerPreview($('#style-name').val())
			} else {
				alert('Error');
			}

		},
		error: function(){}
	});
};

