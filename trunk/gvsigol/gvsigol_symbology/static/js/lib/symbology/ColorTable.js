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
	this.json_data = null;
	this.legendFiles = null;
	
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

ColorTable.prototype.setLegendFiles = function(files) {
	this.legendFiles = files;
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
	this.json_data = json_data;
	for(var j=0; j<this.rule.entries.length; j++){
		var entry = this.rule.entries[j];
		var current = entry["quantity"]
		var colr = this.utils.getColorFromRamp(json_data, min, max, current);
		var colr_aux = this.utils.rgba2hex(colr);
		entry["color"] = colr_aux["color"];
		entry["opacity"] = colr_aux["alpha"];
		$("#color-map-entry-preview-opacity-" + entry["id"]).text(colr_aux["alpha"]);
		entry.updatePreview();
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
	style = this.getStyleDef();
	
	
	var formData = new FormData();
	if(document.getElementById('has-custom-legend').checked) {
		formData.append('has_custom_legend', true);
		formData.append('style_data', JSON.stringify(style));
		if ($("#legend-file")[0].files.length > 0) {
			formData.append('file', $("#legend-file")[0].files[0]);
			
			$.ajax({
				type: "POST",
				async: false,
				cache: false,
		     	contentType: false,
		     	enctype: 'multipart/form-data',
		     	processData: false,	
				url: "/gvsigonline/symbology/color_table_add/" + layerId + "/",
				beforeSend:function(xhr){
					xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
				},
				data: formData,
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
			
		} else {
			messageBox.show('warning', gettext('You must select a image'));
			$.overlayout();
		}

		
	} else {
		formData.append('has_custom_legend', false);
		formData.append('style_data', JSON.stringify(style));
		
		$.ajax({
			type: "POST",
			async: false,
			cache: false,
	     	contentType: false,
	     	enctype: 'multipart/form-data',
	     	processData: false,	
			url: "/gvsigonline/symbology/color_table_add/" + layerId + "/",
			beforeSend:function(xhr){
				xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
			},
			data: formData,
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
	}
};

ColorTable.prototype.load = function(min_raster, max_raster, numberOfIntervals) {
	$("#table-entries-body-" + this.rule.id).empty();
	this.rule.removeAllEntries();
	var colors = this.utils.createColorRange('intervals', numberOfIntervals);

	for (var i=0; i<numberOfIntervals; i++) {
		var min = this.getMinValueForInterval(min_raster, max_raster, i, numberOfIntervals-1);
		this.rule.addColorMapEntry({quantity: min, color: colors[i]});
	}
	if(this.json_data != null){
		this.applyRampColor(this.json_data, min_raster, max_raster);
	}
};

ColorTable.prototype.getStyleDef = function() {
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
	
	return style;
}


ColorTable.prototype.update = function(layerId, styleId) {
	style = this.getStyleDef();
	
	var formData = new FormData();
	if(document.getElementById('has-custom-legend').checked) {
		formData.append('has_custom_legend', true);
		formData.append('style_data', JSON.stringify(style));
		
		var file_to_upload = null;
		var previous_image_loaded = false;
		if ($("#legend-file")[0].files.length > 0) {
			file_to_upload = $("#legend-file")[0].files[0];
		}else{
			if ($("#legend-file").attr("value").length > 0) {
				file_to_upload = $("#legend-file").attr("value");
				previous_image_loaded = true;
			}
		}
		if (file_to_upload != null || previous_image_loaded) {
			if(!previous_image_loaded){			
				formData.append('file', file_to_upload);
			}
			$.ajax({
				type: "POST",
				async: false,
				cache: false,
		     	contentType: false,
		     	enctype: 'multipart/form-data',
		     	processData: false,	
				url: "/gvsigonline/symbology/color_table_update/" + layerId + "/" + styleId + "/",
				beforeSend:function(xhr){
					xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
				},
				data: formData,
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
			
		} else {
			messageBox.show('warning', gettext('You must select a image'));
			$.overlayout();
		}

		
	} else {
		formData.append('has_custom_legend', false);
		formData.append('style_data', JSON.stringify(style));
		
		$.ajax({
			type: "POST",
			async: false,
			cache: false,
	     	contentType: false,
	     	enctype: 'multipart/form-data',
	     	processData: false,	
			url: "/gvsigonline/symbology/color_table_update/" + layerId + "/" + styleId + "/",
			beforeSend:function(xhr){
				xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
			},
			data: formData,
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
	}
};


ColorTable.prototype.updatePreview = function(layerId) {
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
			style: 'CT'
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