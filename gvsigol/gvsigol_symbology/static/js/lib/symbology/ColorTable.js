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
 
 
var ColorTable = function(layerName, utils, rule_opts) {
	this.layerName = layerName;
	this.utils = utils;
	this.rule = null;
	
	if (rule_opts != null) {
		if (rule_opts.entries.length > 0) {
			this.rule = new Rule(0, $("#style-name").val(), $("#style-name").val(), rule_opts, this.utils);
			$('#rules').append(this.rule.getColorMapEntryUI());
			this.rule.registerCMEEvents();
			this.rule.previewRaster();
			this.loadRule(rule_opts.entries);
			
		} else {
			this.rule = new Rule(0, $("#style-name").val(), $("#style-name").val(), rule_opts, this.utils);
			$('#rules').append(this.rule.getColorMapEntryUI());
			this.rule.registerCMEEvents();
			this.rule.previewRaster();
			//this.rule.addColorMapEntry();
		}
	}	
};

ColorTable.prototype.addDefaultEntries = function() {
	this.rule = new Rule(0, $("#style-name").val(), $("#style-name").val(), null, this.utils);
	$('#rules').append(this.rule.getColorMapEntryUI());
	this.rule.registerCMEEvents();
//	this.rule.addColorMapEntry();
	this.rule.previewRaster();
};

ColorTable.prototype.getRule = function() {
	return this.rule;
};

ColorTable.prototype.loadRule = function(entries) {
	$("#table-entries-body-" + this.rule.id).empty();
	this.rule.removeAllEntries();
	
	for (var i=0; i<entries.length; i++) {
		var entry = JSON.parse(entries[i]);
		var options = entry[0].fields;
		this.rule.addColorMapEntry(options);	
	}
};

ColorTable.prototype.refreshMap = function() {
	this.utils.updateMap(this, this.layerName);
};

ColorTable.prototype.applyRampColor = function(json_data, min, max) {
	for(var j=0; j<this.rule.entries.length; j++){
		var entry = this.rule.entries[j];
		var current = entry["quantity"]
		var colr = this.utils.getColorFromRamp(json_data, min, max, current);
		var colr_aux = this.utils.rgba2hex(colr);
		entry["color"] = colr_aux["color"];
		entry["opacity"] = colr_aux["alpha"];
	}
};

ColorTable.prototype.getMinValueForInterval = function(min, max, it, numberOfIntervals){
	if(it == 0){
		return min;
	}
	var gap = (max-min)/numberOfIntervals;
	var value = min + (gap*it);

	return value;
}

ColorTable.prototype.save = function(layerId) {
	$("body").overlay();
	
	var entries = new Array();
	for (var i=0; i < this.rule.getEntries().length; i++) {
		var entry = {
			json: this.rule.getEntries()[i].toJSON(),
			order: i
		};
		entries.push(entry);
	}
	
	var style = {
		name: $('#style-name').val(),
		title: $('#style-title').val(),
		is_default: $('#style-is-default').is(":checked"),
		rule: this.rule.getObject(),
		entries: entries
	}
	
	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/color_table_add/" + layerId + "/",
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

ColorTable.prototype.load = function(min_raster, max_raster, numberOfIntervals) {
	$("#table-entries-body-" + this.rule.id).empty();
	this.rule.removeAllEntries();
	var colors = this.utils.createColorRange('intervals', numberOfIntervals);

	for (var i=0; i<numberOfIntervals; i++) {
		var min = this.getMinValueForInterval(min_raster, max_raster, i, numberOfIntervals);
		this.rule.addColorMapEntry({quantity: min, color: colors[i]});
	}
};

ColorTable.prototype.update = function(layerId, styleId) {
	
	$("body").overlay();
	
	var entries = new Array();
	for (var i=0; i < this.rule.getEntries().length; i++) {
		var entry = {
			json: this.rule.getEntries()[i].toJSON(),
			order: i
		};
		entries.push(entry);
	}
	
	var style = {
		name: $('#style-name').val(),
		title: $('#style-title').val(),
		is_default: $('#style-is-default').is(":checked"),
		rule: this.rule.getObject(),
		entries: entries
	}
	
	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/color_table_update/" + layerId + "/" + styleId + "/",
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