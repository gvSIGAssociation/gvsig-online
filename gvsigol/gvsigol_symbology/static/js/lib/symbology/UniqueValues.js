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


var UniqueValues = function(featureType, layerName, utils, previewUrl) {
	this.selected = null;
	this.featureType = featureType;
	this.layerName = layerName;
	this.previewUrl = previewUrl;
	this.utils = utils;
	this.rules = new Array();
	this.label = null;
	this.json_data = null;
};

UniqueValues.prototype.showLabel = function() {
	if (this.label) {
		this.updateLabelForm();
		$('#modal-symbolizer').modal('show');

	} else {
		this.label = new TextSymbolizer(this.rule, this.layerName, null, this.utils);
		this.updateLabelForm();
		$('#modal-symbolizer').modal('show');
	}
};

UniqueValues.prototype.loadLabel = function(options) {
	if (this.label) {
		this.label = null;
		this.label = new TextSymbolizer(this.rule, this.layerName, options, this.utils);
		this.updateLabelForm();

	} else {
		this.label = new TextSymbolizer(this.rule, this.layerName, options, this.utils);
		this.updateLabelForm();
	}
};

UniqueValues.prototype.updateLabelForm = function() {
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

UniqueValues.prototype.getRules = function() {
	return this.rules;
};

UniqueValues.prototype.getRuleById = function(id) {
	for (var i=0; i < this.rules.length; i++) {
		if (this.rules[i].id == id) {
			return this.rules[i];
		}
	}
};

UniqueValues.prototype.applyRampColor = function(json_data) {
	this.json_data = json_data;
	var min = 0;
	var max = this.rules.length;
	
	for(var i=0; i<this.rules.length; i++){
		var rule = this.rules[i];
		for(var j=0; j<rule.symbolizers.length; j++){
			var symbolizer = rule.symbolizers[j];
			var current = i;
			var colr = this.utils.getColorFromRamp(json_data, min, max, current);
			var colr_aux = this.utils.rgba2hex(colr);
			symbolizer["fill"] = colr_aux["color"];
			symbolizer["fill_opacity"] = colr_aux["alpha"];
			symbolizer["stroke"] = colr_aux["color"];
			symbolizer["stroke_opacity"] = colr_aux["alpha"];
			symbolizer.updatePreview();
		}
		rule.preview();
	}
	
};

UniqueValues.prototype.addRule = function(rule) {
	return this.rules.push(rule);
};

UniqueValues.prototype.deleteRule = function(id) {
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

UniqueValues.prototype.load = function(selectedField, values) {
	$('#rules').empty();
	this.rules.splice(0, this.rules.length);
	var colors = this.utils.createColorRange('random', values.length +1);
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
				operation: 'is_equal_to',
				field: selectedField,
				value: values[i]
		};
		rule.setFilter(filter);
		$('#rules').append(rule.getTableUI(true, 'unique_values'));
		rule.registerEvents();
		rule.addSymbolizer({fill: colors[i], stroke: colors[i]});
		rule.preview();
		this.addRule(rule);
	}
	
	var ruleName = "rule_" + i;
	var ruleTitle = gettext("null_value");
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
			operation: 'is_null',
			field: selectedField
	};
	rule.setFilter(filter);
	$('#rules').append(rule.getTableUI(true, 'unique_values'));
	rule.registerEvents();
	rule.addSymbolizer({fill: colors[i], stroke: colors[i]});
	rule.preview();
	this.addRule(rule);
	
	
	if(this.json_data != null){
		this.applyRampColor(this.json_data);
	}
};

UniqueValues.prototype.loadRules = function(rules) {
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
			$('#rules').append(rule.getTableUI(true, 'unique_values'));
		}

		for (var j=0; j<rules[i].symbolizers.length; j++) {
			var symbolizer = JSON.parse(rules[i].symbolizers[j].json);
			var order = rules[i].symbolizers[j].order;
			var options = symbolizer[0].fields;
			options['order'] = order;

			if (symbolizer[0].model == 'gvsigol_symbology.textsymbolizer') {
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
				rule.addSymbolizer(options);
			}	

		}

		rule.registerEvents();
		rule.preview();
		this.addRule(rule);

	}
};

UniqueValues.prototype.refreshMap = function() {
	this.utils.updateMap(this, this.layerName);
};

UniqueValues.prototype.save = function(layerId) {
	$("body").overlay();
	style = this.getStyleDef();

	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/unique_values_add/" + layerId + "/",
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

UniqueValues.prototype.update = function(layerId, styleId) {
	$("body").overlay();
	style = this.getStyleDef();

	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/unique_values_update/" + layerId + "/" + styleId + "/",
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


UniqueValues.prototype.getStyleDef = function(layerId) {
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
};


UniqueValues.prototype.updatePreview = function(layerId) {
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
			style: 'UV'
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

