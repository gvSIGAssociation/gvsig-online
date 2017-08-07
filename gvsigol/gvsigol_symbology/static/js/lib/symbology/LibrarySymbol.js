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
 
 
var LibrarySymbol = function(previewPointUrl, previewLineUrl, previewPolygonUrl, symbologyUtils) {
	this.count = 0;
	this.selected = null;
	this.featureType = null;
	this.previewPointUrl = previewPointUrl;
	this.previewLineUrl = previewLineUrl;
	this.previewPolygonUrl = previewPolygonUrl;
	this.symbologyUtils = symbologyUtils;
	this.rules = new Array();
};

LibrarySymbol.prototype.addRule = function(rule) {
	this.rules.push(rule);
};

LibrarySymbol.prototype.addDefault = function(rule) {
	
	var rule = new Rule(1, "rule_1", "Rule 1", null, this.symbologyUtils);
	$('#rules').append(rule.getTableUI(false, 'unique'));
	this.addRule(rule);
	rule.registerEvents();
	rule.addSymbolizer();
	rule.preview();
};

LibrarySymbol.prototype.loadRule = function(options, symbolizers) {
	var rule = new Rule(options.id, options.name, options.title, null, this.symbologyUtils);
	$('#rules').append(rule.getTableUI(false, 'unique'));
	this.addRule(rule);
	rule.registerEvents();
	for (var i=0; i<symbolizers.length; i++) {
		var json = JSON.parse(symbolizers[i].json);
		var order = symbolizers[i].order;

		var options = json[0].fields;
		options['order'] = order;
		
		rule.addSymbolizer(options);
	}
	rule.preview();
};

LibrarySymbol.prototype.libraryPreview = function(featureType, rule, json_symbolizers) {
	var symbolizers = new Array();
	var previewUrl = null;
	for (var i=0; i<json_symbolizers.length; i++) {
		
		var json = JSON.parse(json_symbolizers[i].json);
		var order = json_symbolizers[i].order;
		
		var options = json[0].fields;
		options['order'] = order;
		
		var symbolizer = null;
		if (featureType == 'MarkSymbolizer') {
			var utils = new LibraryUtils(this.previewPointUrl);
			symbolizer = new MarkSymbolizer(rule, options, utils);
			previewUrl = this.previewPointUrl;
			
		} else if (featureType == 'LineSymbolizer') {
			var utils = new LibraryUtils(this.previewLineUrl);
			symbolizer = new LineSymbolizer(rule, options, utils);
			previewUrl = this.previewLineUrl;
			
		} else if (featureType == 'PolygonSymbolizer') {
			var utils = new LibraryUtils(this.previewPolygonUrl);
			symbolizer = new PolygonSymbolizer(rule, options, utils);
			previewUrl = this.previewPolygonUrl;
			
		}
		symbolizers.push(symbolizer);
	}
	symbolizers.sort(function(a, b){
		return parseInt(b.order) - parseInt(a.order);
	});
	
	var sldBody = this.symbologyUtils.getSLDBody(symbolizers);
	var url = previewUrl + '&SLD_BODY=' + encodeURIComponent(sldBody);
	var ui = '<img id="rule-preview-img" src="' + url + '" class="rule-preview"></img>';
	$("#library-symbol-preview-div-" + rule.id).empty();
	$("#library-symbol-preview-div-" + rule.id).append(ui);
};

LibrarySymbol.prototype.save = function(libraryid, name, title, filter) {
	
	var symbolizers = new Array();
	this.rules[0].getSymbolizers().sort(function(a, b) {
	    return a.order - b.order;
	});
	for (var i=0; i < this.rules[0].getSymbolizers().length; i++) {
		var symbolizer = {
			type: this.rules[0].getSymbolizers()[i].type,
			json: this.rules[0].getSymbolizers()[i].toJSON(),
			order: this.rules[0].getSymbolizers()[i].order
		};
		symbolizers.push(symbolizer);
	}
	
	var symbol = {
		name: name,
		title: title,
		order: 0,
		minscale: -1,
		maxscale: -1,
		symbolizers: symbolizers
	};
	
	$.ajax({
		type: "POST",
		async: false,
		//contentType: false,
	    enctype: 'multipart/form-data',
		url: "/gvsigonline/symbology/symbol_add/" + libraryid + "/" + this.symbologyUtils.getFeatureType() + "/",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		data: {
			file: $("#eg-file")[0],
			rule: JSON.stringify(symbol)
		},
		success: function(response){
			if (response.success) {
				location.href = "/gvsigonline/symbology/library_update/" + libraryid + "/";
			} else {
				$("#form-error").append('<p>*' + response.message + '</p>');
			}
			
		},
	    error: function(){}
	});
};

LibrarySymbol.prototype.update = function(id, name, title, filter) {
	
	var symbolizers = new Array();
	this.rules[0].getSymbolizers().sort(function(a, b) {
	    return a.order - b.order;
	});
	for (var i=0; i < this.rules[0].getSymbolizers().length; i++) {
		var symbolizer = {
			type: this.rules[0].getSymbolizers()[i].type,
			json: this.rules[0].getSymbolizers()[i].toJSON(),
			order: this.rules[0].getSymbolizers()[i].order
		};
		symbolizers.push(symbolizer);
	}
	
	var symbol = {
		name: name,
		title: title,
		order: 0,
		minscale: -1,
		maxscale: -1,
		symbolizers: symbolizers
	};
	
	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/symbol_update/" + id + "/",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		data: {
			rule: JSON.stringify(symbol)
		},
		success: function(response){
			if (response.success) {
				location.href = "/gvsigonline/symbology/library_update/" + response.library_id + "/";
			} else {
				$("#form-error").append('<p>*' + response.message + '</p>');
			}
			
		},
	    error: function(){}
	});
};