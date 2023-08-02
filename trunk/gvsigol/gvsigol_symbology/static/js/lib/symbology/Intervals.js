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
	this.json_data = null;
};

Intervals.prototype.showLabel = function() {
	if (this.label) {
		this.updateLabelForm();
		$('#modal-symbolizer').modal('show');

	} else {
		this.label = new TextSymbolizer(this.rule, this.layerName, null, this.utils);
		this.updateLabelForm();
		$('#modal-symbolizer').modal('show');
	}
};

Intervals.prototype.loadLabel = function(options) {
	if (this.label) {
		this.label = null;
		this.label = new TextSymbolizer(this.rule, this.layerName, options, this.utils);
		this.updateLabelForm();

	} else {
		this.label = new TextSymbolizer(this.rule, this.layerName, options, this.utils);
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
	$('#tab-content').append(this.label.getFilterTabUI());
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

Intervals.prototype.applyRampColor = function(json_data) {
	this.json_data = json_data;
	var min = null;
	var max = null;
	for(var i=0; i<this.rules.length; i++){
		var rule = this.rules[i];
		if(rule.filter){
			if(!min || min > rule.filter["value1"]){
				min = rule.filter["value1"]
			}
			if(!max || max < rule.filter["value2"]){
				max = rule.filter["value2"]
			}
		}
	}
	
	if(min != null && max != null){
		for(var i=0; i<this.rules.length; i++){
			var rule = this.rules[i];
			for(var j=0; j<rule.symbolizers.length; j++){
				var symbolizer = rule.symbolizers[j];
				if(rule.filter){
					var current = rule.filter["value1"]
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
				operation: 'is_between',
				field: selectedField,
				value1: min,		
				value2: max
		};
		rule.setFilter(filter);
		$('#rules').append(rule.getTableUI(true, 'intervals'));
		rule.addSymbolizer({fill: colors[i]});
		rule.registerEvents("intervals");
		rule.preview();
		this.addRule(rule);
	}
	
	if(this.json_data != null){
		this.applyRampColor(this.json_data);
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
			$('#rules').append(rule.getTableUI(true, 'intervals'));
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

		rule.registerEvents("intervals");
		rule.preview();
		this.addRule(rule);

	}
};

Intervals.prototype.refreshMap = function() {
	this.utils.updateMap(this, this.layerName);
};

Intervals.prototype.save = function(layerId) {

	$("body").overlay();
	style = this.getStyleDef();

	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/intervals_add/" + layerId + "/",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
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

Intervals.prototype.getStyleDef = function(){
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

Intervals.prototype.update = function(layerId, styleId) {

	$("body").overlay();
	style = this.getStyleDef();

	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/intervals_update/" + layerId + "/" + styleId + "/",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
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

Intervals.prototype.updatePreview = function(layerId) {
	var self = this;
	//$("body").overlay();
	style = this.getStyleDef();

	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/update_preview/" + layerId +  "/",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
		},
		data: {
			style_data: JSON.stringify(style),
			style: 'IN'
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
