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
 
 
var Intervals = function(featureType, layerName, utils, previewUrl) {
	this.selected = null;
	this.featureType = featureType;
	this.layerName = layerName;
	this.previewUrl = previewUrl;
	this.utils = utils;
	this.rules = new Array();
	this.label = null;
};

Intervals.prototype.showLabel = function() {
	if (this.label) {
		this.updateLabelForm();
		$('#modal-symbolizer').modal('show');
		
	} else {
		this.label = new TextSymbolizer(this.rule, null, this.utils);
		this.updateLabelForm();
		$('#modal-symbolizer').modal('show');
	}
};

Intervals.prototype.loadLabel = function(options) {
	if (this.label) {
		this.label = null;
		this.label = new TextSymbolizer(this.rule, options, this.utils);
		this.updateLabelForm();
		
	} else {
		this.label = new TextSymbolizer(this.rule, options, this.utils);
		this.updateLabelForm();
	}
};

Intervals.prototype.updateLabelForm = function() {
	$('#tab-menu').empty();
	$('#tab-content').empty();	
	
	$('#tab-menu').append(this.label.getTabMenu());
	
	$('#tab-content').append(this.label.getGeneralTabUI());
	$('#tab-content').append(this.label.getFontTabUI());
	$('#tab-content').append(this.label.getHaloTabUI());
	$('.nav-tabs a[href="#label-general-tab"]').tab('show');
	this.label.registerEvents();
	
};

Intervals.prototype.getRules = function() {
	return this.rules;
};

Intervals.prototype.getRuleById = function(id) {
	for (var i=0; i < this.rules.length; i++) {
		if (this.rules[i].id == id) {
			return this.rules[i];
		}
	}
};

Intervals.prototype.addRule = function(rule) {
	return this.rules.push(rule);
};

Intervals.prototype.deleteRule = function(id) {
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

Intervals.prototype.load = function(response, selectedField, numberOfIntervals) {
	$('#rules').empty();
	this.rules.splice(0, this.rules.length);
	
	var minMax = JSON.parse(response);
	var colors = this.utils.createColorRange('intervals', numberOfIntervals);
	
	for (var i=0; i<numberOfIntervals; i++) {
		
		var min = this.getMinValueForInterval(minMax.min, minMax.max, i, numberOfIntervals);
		var max = this.getMaxValueForInterval(minMax.min, minMax.max, i, numberOfIntervals);
		
		var fieldFilter = min + "<=" + selectedField + "<=" + max;
		var fieldName = min + "-" + max;
		
		var ruleName = min + "-" + max;
		var ruleTitle = min.toFixed(5).replace(/([0-9]+(\.[0-9]+[1-9])?)(\.?0+$)/,'$1').replace(/([0-9]+(\.[1-9]+)?)(0+$)/,'$1') + "-" + max.toFixed(5).replace(/([0-9]+(\.[0-9]+[1-9])?)(\.?0+$)/,'$1').replace(/([0-9]+(\.[1-9]+)?)(0+$)/,'$1') ;
		var rule = new Rule(i, ruleName, ruleTitle, null, this.utils);
		
		var filter = {
			type: 'is_between',
			property_name: selectedField,
			value1: min,		
			value2: max
		};
		rule.setFilter(filter);
		
		$('#rules').append(rule.getTableUI(true, 'intervals'));
		rule.addSymbolizer({fill: colors[i]});
		rule.registerEvents();
		rule.preview();
		this.addRule(rule);
	}
};

Intervals.prototype.getMinValueForInterval = function(min, max, it, numberOfIntervals){
	if(it == 0){
		return min;
	}
	var gap = (max-min)/numberOfIntervals;
	var value = min + (gap*it);
	
	return value;
}

Intervals.prototype.getMaxValueForInterval = function(min, max, it, numberOfIntervals){
	if(it == numberOfIntervals-1){
		return max;
	}
	var gap = (max-min)/numberOfIntervals;
	var value = min + (gap*(it+1));
	
	return value;
}

Intervals.prototype.loadRules = function(rules) {
	$('#rules').empty();
	this.rules.splice(0, this.rules.length);
	for (var i=0; i<rules.length; i++) {
		var rule = new Rule(rules[i].id, rules[i].name, rules[i].title, null, this.utils);
		var filter = JSON.parse(rules[i].filter);
		rule.setFilter(filter);
			
		rule.removeAllSymbolizers();
		rule.removeLabel();
		$('#rules').append(rule.getTableUI(true, 'intervals'));
		
		for (var j=0; j<rules[i].symbolizers.length; j++) {
			
			var symbolizer = JSON.parse(rules[i].symbolizers[j].json);
			var order = rules[i].symbolizers[j].order;
			var options = symbolizer[0].fields;
			options['order'] = order;
			
			if (symbolizer[0].model == 'gvsigol_symbology.textsymbolizer') {
				options['is_actived'] = true;
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

Intervals.prototype.refreshMap = function() {
	this.utils.updateMap(this, this.layerName);
};

Intervals.prototype.save = function(layerId) {
	
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
		
		if (this.label != null && this.label.is_activated()) {
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
		url: "/gvsigonline/symbology/intervals_add/" + layerId + "/",
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

Intervals.prototype.update = function(layerId, styleId) {
	
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
		
		if (this.label != null && this.label.is_activated()) {
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
			}
			
		},
	    error: function(){}
	});
};