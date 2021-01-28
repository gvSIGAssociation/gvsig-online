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
 
 
var ColorRamp = function(name, rule_opts) {
	this.name = name;
	this.rule = null;
	this.utils = new SymbologyUtils();
	
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

ColorRamp.prototype.addDefaultEntries = function() {
	this.addColorRamp(0, "#ffffff", 1);
	this.addColorRamp(100, "#ff0000", 1);
	
	this.refreshPreview();
};


ColorRamp.prototype.getColorRampTableUI = function() {
	var ui = '<table id="colorramp-table" style="width:100%; text-align:center">';
	ui += '<tr>';
	ui += 	'<th>'
	ui += 	'</th>';
	ui += 	'<th>ID</th>';
	ui += 	'<th>'+gettext('Percentaje')+'</th>';
	ui += 	'<th>'+gettext('Color')+'</th>';
	ui += 	'<th>'+gettext('Transparencia')+'</th>';
	ui += 	'<th>'+gettext('Delete')+'</th>';
	ui += '</tr></table>';	
	
	return ui;
};


ColorRamp.prototype.addColorRamp = function(percentaje, color, alpha){
	if(!alpha){
		alpha = 1;
	}
	var id = 0;
	$("#colorramp-table tr.color-ramp-data").each(function(){
		var current_id_str = $(this).attr("data-rowid");
		var current_id = parseInt(current_id_str);
		if(current_id >= id){
			id = current_id + 1;
		}
	});
	
	var rule_entry = {
			id: id,
			quantity: percentaje,
			color: color,
			alpha: alpha
	}
	$("#colorramp-table").append(this.getColorRampUI(rule_entry));
	
	this.updateEvents();
}

ColorRamp.prototype.getColorRampUI = function(rule_entry) {
	var ui = '';
	ui += '<tr class="color-ramp-data" data-rowid="' + rule_entry.id + '">';
	ui += 	'<td>'
	ui += 		'<span class="handle"> ';
	ui += 			'<i class="fa fa-ellipsis-v"></i>';
	ui += 			'<i class="fa fa-ellipsis-v"></i>';
	ui += 		'</span>';
	ui += 	'</td>';
	ui += 	'<td id="color-map-entry-preview-div-' + rule_entry.id + '">' + rule_entry.id + '</td>';
	ui += 	'<td id="color-map-entry-preview-quantity-' + rule_entry.id + '"><input class="form-control percentaje-chooser" type="number" min="0" max="100" step="1" value="' + rule_entry.quantity + '" oninput="if(this.value>100)this.value=100;if(this.value<0)this.value=0"/></td>';
	ui += 	'<td id="color-map-entry-preview-color-' + rule_entry.id + '"><input type="color" value="' + rule_entry.color + '" class="form-control color-chooser"></td>';
	ui += 	'<td id="color-map-entry-preview-alpha-' + rule_entry.id + '"><input type="number" value="' + rule_entry.alpha + '" min=0 max=1 step=0.01 class="form-control alpha-chooser" oninput="if(this.value>1)this.value=1;if(this.value<0)this.value=0"></td>';
	ui += 	'<td><a class="delete-color-map-entry delete-color-map-entry-link-' + rule_entry.id + '" data-colormapentryid="' + rule_entry.id + '" href="javascript:void(0)"><i class="fa fa-times text-danger"></i></a></td>';
	ui += '</tr>';	
	
	return ui;
};

ColorRamp.prototype.getRule = function() {
	return this.rule;
};

ColorRamp.prototype.loadRule = function(entries) {
	
	$("#table-entries-body-" + this.rule.id).empty();
	this.rule.removeAllEntries();
	
	for (var i=0; i<entries.length; i++) {
		
		var entry = JSON.parse(entries[i]);
		var options = entry[0].fields;
		
		this.rule.addColorMapEntry(options);	
		
	}
};

ColorRamp.prototype.updateEvents = function() {
	var self = this;
	$(".color-chooser").unbind("change").change(function(){
		self.refreshPreview();
	});
	$(".percentaje-chooser").unbind("change").change(function(){
		self.refreshPreview();
	});
	$(".alpha-chooser").unbind("change").change(function(){
		self.refreshPreview();
	});
	
	$(".delete-color-map-entry").unbind("click").click(function(){
		$(this).parent().parent().remove();
		self.refreshPreview();
	});
};


ColorRamp.prototype.refreshPreview = function() {
	var css_string1 = "";
	var css_string2 = "";
	
	var sortable = [];
	$("#colorramp-table tr.color-ramp-data").each(function(){
		var id = $(this).attr("data-rowid");
		var quatity = $("#color-map-entry-preview-quantity-" + id + " input").val();
		var color = $("#color-map-entry-preview-color-" + id + " input").val();
		var alpha = $("#color-map-entry-preview-alpha-" + id + " input").val();
		sortable.push([quatity, color, alpha]);
	});
	
	sortable.sort(function(a, b) {
	    return a[0].quantity - b[0].quantity;
	});
	
	
	if(sortable.length > 0){
		for(var i=0; i<sortable.length; i++){
			var rgba_color_aux = this.utils.convertHex(sortable[i][1]);
			var rgba_color = "rgba(" + rgba_color_aux.red + ","+ rgba_color_aux.green + ","+ rgba_color_aux.blue + ","+ sortable[i][2] + ")"
			css_string1 = css_string1 + ", " + rgba_color + " " + sortable[i][0] +"%";
			css_string2 = css_string2 + ", color-stop(" + sortable[i][0] + "%," + rgba_color +")";
		}
		
		var rgba_color_ini_aux = this.utils.convertHex(sortable[0][1]);
		var rgba_color_ini = "rgba(" + rgba_color_aux.red + ","+ rgba_color_aux.green + ","+ rgba_color_aux.blue + ","+ sortable[0][2] + ")"
		var ini_color = rgba_color_ini;
		
		var rgba_color_fin_aux = this.utils.convertHex(sortable[sortable.length-1][1]);
		var rgba_color_fin = "rgba(" + rgba_color_aux.red + ","+ rgba_color_aux.green + ","+ rgba_color_aux.blue + ","+ sortable[sortable.length-1][2] + ")"
		var end_color = rgba_color_fin;
		
		var style = "";
		style = style + "background-color:"+ini_color+";";
		style = style + "filter:progid:DXImageTransform.Microsoft.gradient(GradientType=1,startColorstr="+ini_color+", endColorstr="+end_color+");";
		style = style + "background-image:-moz-linear-gradient(left"+css_string1+");";
		style = style + "background-image:linear-gradient(left"+css_string1+");";
		style = style + "background-image:-webkit-linear-gradient(left"+css_string1+");";
		style = style + "background-image:-o-linear-gradient(left"+css_string1+");";
		style = style + "background-image:-ms-linear-gradient(left"+css_string1+");";
		style = style + "background-image:-webkit-gradient(linear, left bottom, right bottom"+css_string2+");}";
		
		$(".preview-ramp-color").attr("style", style);
		
	}
	
};


ColorRamp.prototype.getStyleForPreview = function(json_data) {
	var style = "";
	
	var css_string1 = "";
	var css_string2 = "";
	
	var sortable = [];
	if('definition' in json_data){
		for(var i = 0; i<json_data['definition'].length; i++){
			var quatity = json_data['definition'][i]['quantity'];
			var color = json_data['definition'][i]['color'];
			var alpha = json_data['definition'][i]['alpha'];
			sortable.push([quatity, color, alpha]);
		}
	}
	
	sortable.sort(function(a, b) {
	    return a[0].quantity - b[0].quantity;
	});
	
	
	if(sortable.length > 0){
		for(var i=0; i<sortable.length; i++){
			var rgba_color_aux = this.utils.convertHex(sortable[i][1]);
			var rgba_color = "rgba(" + rgba_color_aux.red + ","+ rgba_color_aux.green + ","+ rgba_color_aux.blue + ","+ sortable[i][2] + ")"
			css_string1 = css_string1 + ", " + rgba_color + " " + sortable[i][0] +"%";
			css_string2 = css_string2 + ", color-stop(" + sortable[i][0] + "%," + rgba_color +")";
		}
		
		var rgba_color_ini_aux = this.utils.convertHex(sortable[0][1]);
		var rgba_color_ini = "rgba(" + rgba_color_aux.red + ","+ rgba_color_aux.green + ","+ rgba_color_aux.blue + ","+ sortable[0][2] + ")"
		var ini_color = rgba_color_ini;
		
		var rgba_color_fin_aux = this.utils.convertHex(sortable[sortable.length-1][1]);
		var rgba_color_fin = "rgba(" + rgba_color_aux.red + ","+ rgba_color_aux.green + ","+ rgba_color_aux.blue + ","+ sortable[sortable.length-1][2] + ")"
		var end_color = rgba_color_fin;
		
		style = style + "background-color:"+ini_color+";";
		style = style + "filter:progid:DXImageTransform.Microsoft.gradient(GradientType=1,startColorstr="+ini_color+", endColorstr="+end_color+");";
		style = style + "background-image:-moz-linear-gradient(left"+css_string1+");";
		style = style + "background-image:linear-gradient(left"+css_string1+");";
		style = style + "background-image:-webkit-linear-gradient(left"+css_string1+");";
		style = style + "background-image:-o-linear-gradient(left"+css_string1+");";
		style = style + "background-image:-ms-linear-gradient(left"+css_string1+");";
		style = style + "background-image:-webkit-gradient(linear, left bottom, right bottom"+css_string2+");}";
	}
	
	return style;
}

ColorRamp.prototype.refreshComponentPreview = function(component_id, json_data, attribute) {
	$("#"+component_id).attr(attribute, this.getStyleForPreview(json_data));
};

//ColorRamp.prototype.save = function(layerId) {
//	
//	$("body").overlay();
//	
//	var entries = new Array();
//	for (var i=0; i < this.rule.getEntries().length; i++) {
//		var entry = {
//			json: this.rule.getEntries()[i].toJSON(),
//			order: i
//		};
//		entries.push(entry);
//	}
//	
//	var style = {
//		name: $('#style-name').val(),
//		title: $('#style-title').val(),
//		is_default: $('#style-is-default').is(":checked"),
//		rule: this.rule.getObject(),
//		entries: entries
//	}
//	
//	$.ajax({
//		type: "POST",
//		async: false,
//		url: "/gvsigonline/symbology/color_table_add/" + layerId + "/",
//		beforeSend:function(xhr){
//			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
//		},
//		data: {
//			style_data: JSON.stringify(style)
//		},
//		success: function(response){
//			if (response.success) {
//				location.href = "/gvsigonline/symbology/style_layer_list/";
//			} else {
//				alert('Error');
//			}
//			
//		},
//	    error: function(){}
//	});
//};
//
//ColorRamp.prototype.update = function(layerId, styleId) {
//	
//	$("body").overlay();
//	
//	var entries = new Array();
//	for (var i=0; i < this.rule.getEntries().length; i++) {
//		var entry = {
//			json: this.rule.getEntries()[i].toJSON(),
//			order: i
//		};
//		entries.push(entry);
//	}
//	
//	var style = {
//		name: $('#style-name').val(),
//		title: $('#style-title').val(),
//		is_default: $('#style-is-default').is(":checked"),
//		rule: this.rule.getObject(),
//		entries: entries
//	}
//	
//	$.ajax({
//		type: "POST",
//		async: false,
//		url: "/gvsigonline/symbology/color_table_update/" + layerId + "/" + styleId + "/",
//		beforeSend:function(xhr){
//			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
//		},
//		data: {
//			style_data: JSON.stringify(style)
//		},
//		success: function(response){
//			if (response.success) {
//				location.href = "/gvsigonline/symbology/style_layer_list/";
//			} else {
//				alert('Error');
//			}
//			
//		},
//	    error: function(){}
//	});
//};