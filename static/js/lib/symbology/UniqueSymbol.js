/**
 * gvSIG Online.
 * Copyright (C) 2007-2015 gvSIG Association.
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
 
 
var UniqueSymbol = function(layerName, utils, rule_opts) {
	this.layerName = layerName;
	this.utils = utils;
	this.rule = null;
	this.label = null;
	
	if (rule_opts != null) {
		if (rule_opts.symbolizers != "") {
			this.rule = new Rule(0, $("#style-name").val(), $("#style-name").val(), rule_opts, this.utils);
			$('#rules').append(this.rule.getTableUI(true, 'unique'));
			this.rule.registerEvents();
			this.rule.preview();
			this.loadRule(rule_opts.symbolizers);
		}
	}	
};

UniqueSymbol.prototype.addDefault = function() {
	this.rule = new Rule(0, $("#style-name").val(), $("#style-name").val(), null, this.utils);
	$('#rules').append(this.rule.getTableUI(true, 'unique'));
	this.rule.registerEvents();
	this.rule.addSymbolizer();
	this.rule.preview();
};

UniqueSymbol.prototype.getRule = function() {
	return this.rule;
};

UniqueSymbol.prototype.showLabel = function() {
	if (this.label) {
		this.updateLabelForm();
		$('#modal-symbolizer').modal('show');
		
	} else {
		this.label = new TextSymbolizer(this.rule, null, this.utils);
		this.updateLabelForm();
		$('#modal-symbolizer').modal('show');
	}
};

UniqueSymbol.prototype.loadRule = function(symbolizers) {
	
	$("#table-symbolizers-body").empty();
	this.rule.removeAllSymbolizers();
	this.rule.removeLabel();
	
	for (var i=0; i<symbolizers.length; i++) {
		
		var symbolizer = JSON.parse(symbolizers[i].json);
		var order = symbolizers[i].order;
		var options = symbolizer[0].fields;
		options['order'] = order;
		
		if (symbolizer[0].model == 'gvsigol_symbology.textsymbolizer') {
			this.loadLabel(options);
			
		} else if (symbolizer[0].model == 'gvsigol_symbology.externalgraphicsymbolizer') {
			this.rule.addExternalGraphicSymbolizer(options);
			
		} else {
			this.rule.addSymbolizer(options);
		}	
		
	}
	this.rule.preview();
};

UniqueSymbol.prototype.loadLabel = function(options) {
	if (this.label) {
		this.label = null;
		this.label = new TextSymbolizer(this.rule, options, this.utils);
		this.updateLabelForm();
		
	} else {
		this.label = new TextSymbolizer(this.rule, options, this.utils);
		this.updateLabelForm();
	}
};

UniqueSymbol.prototype.refreshMap = function() {
	this.utils.updateMap(this, this.layerName);
};

UniqueSymbol.prototype.updateLabelForm = function() {
	$('#tab-menu').empty();
	$('#tab-content').empty();	
	
	$('#tab-menu').append(this.label.getTabMenu());

	$('#tab-content').append(this.label.getFontTabUI());
	$('#tab-content').append(this.label.getHaloTabUI());
	$('.nav-tabs a[href="#label-font-tab"]').tab('show');
	this.label.registerEvents();
	
};

UniqueSymbol.prototype.save = function(layerId) {
	
	$("body").overlay();
	
	var symbolizers = new Array();
	for (var i=0; i < this.rule.getSymbolizers().length; i++) {
		var symbolizer = {
			type: this.rule.getSymbolizers()[i].type,
			json: this.rule.getSymbolizers()[i].toJSON(),
			order: this.rule.getSymbolizers()[i].order
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
	
	var style = {
		name: $('#style-name').val(),
		title: $('#style-title').val(),
		is_default: $('#style-is-default').is(":checked"),
		rule: this.rule.getObject(),
		symbolizers: symbolizers
	}
	
	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/unique_symbol_add/" + layerId + "/",
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

UniqueSymbol.prototype.update = function(layerId, styleId) {
	
	$("body").overlay();
	
	var symbolizers = new Array();
	for (var i=0; i < this.rule.getSymbolizers().length; i++) {
		var symbolizer = {
			type: this.rule.getSymbolizers()[i].type,
			json: this.rule.getSymbolizers()[i].toJSON(),
			order: this.rule.getSymbolizers()[i].order
		};
		symbolizers.push(symbolizer);
	}
	
	if (this.label != null){
		var l = {
			type: this.label.type,
			json: this.label.toJSON(),
			order: this.label.order
		};
		symbolizers.push(l);
	}
	
	var style = {
		name: $('#style-name').val(),
		title: $('#style-title').val(),
		is_default: $('#style-is-default').is(":checked"),
		rule: this.rule.getObject(),
		symbolizers: symbolizers
	}
	
	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/unique_symbol_update/" + layerId + "/" + styleId + "/",
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