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


/**
 * TODO
 */
var RawFilter = function(conf, map) {
	this.map = map;	
	this.conf = conf;
	this.filterTab = $('#filters-tab');
	this.initialize();
};

/**
 * TODO.
 */
RawFilter.prototype.initialize = function() {
	var self = this;
	
	var filters = this.createUI();
	this.filterTab.append(filters);
	
	this.registerEvents();
};


/**
 * TODO.
 */
RawFilter.prototype.createUI = function() {
	var self = this;
	
	var ui = '';
	ui += '<div class="box box-default">';
	ui += 	'<div class="box-header with-border">';
	ui += 		'<h3 class="box-title">' + gettext('Raw filter') + '</h3>';
	ui += 	'</div>';
	ui += 	'<div class="box-body">';
	
	ui += 		'<div class="form-group">';
	ui += 			'<label>' + gettext('Layer group') + '</label>';
	ui += 			'<select id="rawfilter-layer-group" class="form-control">';
	ui += 				'<option value="__disabled__">' + gettext('Select layer group') + ' ...</option>';
	for (var i=0; i < this.conf.layerGroups.length; i++) {
		ui += 			'<option value="' + this.conf.layerGroups[i].groupName + '">' + this.conf.layerGroups[i].groupTitle + '</option>';
	}
	ui += 			'</select>';
	ui += 		'</div>';
	
	ui += 		'<div class="form-group">';
	ui += 			'<label>' + gettext('Layer') + '</label>';
	ui += 			'<select disabled id="rawfilter-layer" class="form-control">';
	ui += 				'<option selected value="__disabled__">' + gettext('Select layer') + ' ...</option>';
	ui += 			'</select>';
	ui += 		'</div>';
	
	ui += 		'<div class="form-group">';
	ui += 			'<label>' + gettext('Field') + '</label>';
	ui += 			'<select disabled id="rawfilter-field" class="form-control">';
	ui += 				'<option selected value="__disabled__">' + gettext('Select field') + ' ...</option>';
	ui += 			'</select>';
	ui += 		'</div>';
	
	ui += 		'<div class="form-group">';
	ui += 			'<label>' + gettext('Operator') + '</label>';
	ui += 			'<select disabled id="rawfilter-operator" class="form-control">';
	ui += 				'<option selected value="__disabled__">' + gettext('Select operator') + ' ...</option>';
	ui += 				'<option value="equal_to">' + gettext('Equal to') + '</option>';
	ui += 				'<option value="smaller_than">' + gettext('Smaller than') + '</option>';
	ui += 				'<option value="greater_to">' + gettext('Greater than') + '</option>';
	ui += 			'</select>';
	ui += 		'</div>';
	
	ui += 		'<div id="rawfilter-selectvalue-div" style="display: none;" class="form-group">';
	ui += 			'<label>' + gettext('Value') + '</label>';
	ui += 			'<select disabled id="rawfilter-selectvalue" class="form-control">';
	ui += 				'<option selected value="__disabled__">' + gettext('Select value') + ' ...</option>';
	ui += 			'</select>';
	ui += 		'</div>';
	
	ui += 		'<div id="rawfilter-inputvalue-div" style="display: none;" class="form-group">';
	ui += 			'<label>' + gettext('Value') + '</label>';
	ui += 			'<input type="number" id="rawfilter-inputvalue" class="form-control">';
	ui += 		'</div>';
	
	ui += 	'</div>';
	ui += 	'<div class="box-footer">';
	ui += 		'<button type="button" id="rawfilter-apply" style="float: right;" class="btn btn-primary">' + gettext('Apply filter') + '</button>';
	ui += 		'<button type="button" id="rawfilter-clean" style="float: left;" class="btn btn-default">' + gettext('Clean filter') + '</button>';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

/**
 * TODO.
 */
RawFilter.prototype.registerEvents = function() {
	var self = this;
	
	$('#rawfilter-layer-group').change(function(e){
		$("#rawfilter-layer").prop('disabled', false);
		$("#rawfilter-field").prop('disabled', true);
		$("#rawfilter-layer").empty().append('<option selected value="__disabled__">' + gettext('Select layer') + ' ...</option>');
		$("#rawfilter-field").empty().append('<option selected value="__disabled__">' + gettext('Select field') + ' ...</option>');
		$("#rawfilter-selectvalue").prop('disabled', true);
		$("#rawfilter-selectvalue").empty().append('<option selected value="__disabled__">' + gettext('Select value') + ' ...</option>');
		$("#rawfilter-selectvalue-div").css('display', 'none');
		$("#rawfilter-inputvalue-div").css('display', 'none');
		
		var group = $('option:selected', $(this)).val();
		var layers = self.getLayers(group);
		
		var hasLayers = false;
		for (var i=0; i < layers.length; i++) {
			if (layers[i].wfs_url) {
				if (layers[i].wfs_url != '') {
					hasLayers = true;
					$("#rawfilter-layer").append('<option data-wfsurl="' + layers[i].wfs_url  + '" data-workspace="' + layers[i].workspace  + '" value="' + layers[i].name  + '">' + layers[i].title  + '</option>');
				}
			}	
		}
		
		if (!hasLayers) {
			$("#rawfilter-layer").empty().append('<option selected value="__disabled__">' + gettext('The selected layer group does not contain queryable layers') + ' ...</option>');
		}
	});
	
	$('#rawfilter-layer').change(function(e){
		$("#rawfilter-field").prop('disabled', false);
		$("#rawfilter-field").empty().append('<option selected value="__disabled__">' + gettext('Select field') + ' ...</option>');
		$("#rawfilter-selectvalue").prop('disabled', true);
		$("#rawfilter-selectvalue").empty().append('<option selected value="__disabled__">' + gettext('Select value') + ' ...</option>');
		$("#rawfilter-selectvalue-div").css('display', 'none');
		$("#rawfilter-inputvalue-div").css('display', 'none');
		
		var layer = $('option:selected', $(this)).val();
		var workspace = $('option:selected', $(this)).data('workspace');
		var fields_trans = self.describeLayerConfig(layer, workspace);

		var fields = self.getFields(layer, workspace);

		var language = $("#select-language").val();
		
		var hasFields = false;
		for (var i=0; i < fields.length; i++) {
			hasFields = true;
			if (fields[i].type != 'date' && fields[i].type != 'timestamp' && fields[i].type != 'timestamp with time zone' && fields[i].name != 'wkb_geometry' && fields[i].name != 'geometry' && fields[i].name != 'geom' && fields[i].name != 'modified_by' && fields[i].name != 'last_modification' && fields[i].name != 'feat_version_gvol' && fields[i].name != 'id') {
				
				feat_name = fields[i].name
				
				if(fields_trans != null && fields_trans["fields"] != undefined){
					var fields = fields_trans["fields"];
					for(var ix=0; ix<fields.length; ix++){
						if(fields[ix].name.toLowerCase() == feat_name){
							if("visible" in fields[ix]){
								column_shown = fields[ix].visible;
							}
							var feat_name_trans = fields[ix]["title-"+language];
							if(feat_name_trans){
								feat_name = feat_name_trans
							}
						}
					}
				}
				
				$("#rawfilter-field").append('<option data-layer="' + layer  + '" data-workspace="' + workspace  + '" data-type="' + fields[i].type  + '" value="' + fields[i].name  + '">' + feat_name  + '</option>');
			}
		}
		
		if (!hasFields) {
			$("#rawfilter-field").empty().append('<option selected value="__disabled__">' + gettext('The selected layer does not contain queryable fields') + ' ...</option>');
		}
	});
	
	$('#rawfilter-field').change(function(e){
		$("#rawfilter-operator").prop('disabled', false);
		$("#rawfilter-operator").empty().append('<option selected value="__disabled__">' + gettext('Select operator') + ' ...</option>');
		
		var type = $('option:selected', $(this)).data('type');
		
		if (type == 'numeric' || type == 'integer' || type == 'bigint' || type == 'double' || type == 'double precision') {	
			$("#rawfilter-operator").append('<option value="equal_to">' + gettext('Equal to') + '</option>');
			$("#rawfilter-operator").append('<option value="smaller_than">' + gettext('Smaller than') + '</option>');
			$("#rawfilter-operator").append('<option value="greater_than">' + gettext('Greater than') + '</option>');
			
		} else if (type == 'character varying' || type == 'enumeration'){
			$("#rawfilter-operator").append('<option value="equal_to">' + gettext('Equal to') + '</option>');
		}
	});
	
	$('#rawfilter-operator').change(function(e){
		var operator = $('option:selected', $(this)).val();
		
		if (operator == 'equal_to') {
			$("#rawfilter-inputvalue-div").css('display', 'none');
			$("#rawfilter-selectvalue-div").css('display', 'block');
			$("#rawfilter-selectvalue").prop('disabled', false);
			$("#rawfilter-selectvalue").empty().append('<option selected value="__disabled__">' + gettext('Select value') + ' ...</option>');
			
			var field = $('option:selected', $('#rawfilter-field')).val();
			var layer = $('option:selected', $('#rawfilter-field')).data('layer');
			var workspace = $('option:selected', $('#rawfilter-field')).data('workspace');
			var values = self.getUniqueValues(layer, workspace, field);
			
			var hasValues = false;
			for (var i=0; i < values.length; i++) {
				hasValues = true;
				$("#rawfilter-selectvalue").append('<option value="' + values[i]  + '">' + values[i]  + '</option>');
			}
			
			if (!hasValues) {
				$("#rawfilter-selectvalue").empty().append('<option selected value="__disabled__">' + gettext('The selected field does not contain values') + ' ...</option>');
			}
			
		} else if (operator == 'smaller_than') {
			$("#rawfilter-selectvalue-div").css('display', 'none');
			$("#rawfilter-inputvalue-div").css('display', 'block');
			
		} else if (operator == 'greater_than') {
			$("#rawfilter-selectvalue-div").css('display', 'none');
			$("#rawfilter-inputvalue-div").css('display', 'block');
		}
		
	});
	
	$('#rawfilter-apply').on('click', function(e){

		self.selectionTable = viewer.core.getSelectionTable();
		if (self.selectionTable == null) {
			self.selectionTable = new SelectionTable(self.map);
			viewer.core.setSelectionTable(self.selectionTable);
		}
		//self.selectionTable.removeTables();
		var layerGroup = $('option:selected', $('#rawfilter-layer-group')).val();
		var layer = $('option:selected', $('#rawfilter-layer')).val();
		var workspace = $('option:selected', $('#rawfilter-layer')).data('workspace');
		var wfsUrl = $('option:selected', $('#rawfilter-layer')).data('wfsurl');
		var field = $('option:selected', $('#rawfilter-field')).val();
		var fieldType = $('option:selected', $('#rawfilter-field')).data('type');
		var operator = $('option:selected', $('#rawfilter-operator')).val();

		var value = null;
		if (operator == 'equal_to') {
			value = $('option:selected', $('#rawfilter-selectvalue')).val();
			
		} else if (operator == 'smaller_than') {
			value = $('#rawfilter-inputvalue').val();
			
		} else if (operator == 'greater_than') {
			value = $('#rawfilter-inputvalue').val();
		}
		
		if (layerGroup != '__disabled__' && layer != '__disabled__' && field != '__disabled__' && operator != '__disabled__' && value != '__disabled__') {
			var features = self.getFeatures(layer, workspace, wfsUrl, field, fieldType, value, operator);
			
			if (features.length > 0) {
				self.selectionTable.addTable(features, layer, workspace, wfsUrl);
				self.selectionTable.show();
				self.selectionTable.registerEvents();
				
			} else {
				messageBox.show('warning', gettext('No results found'));
			}
			
		} else {
			messageBox.show('warning', gettext('You must fill in all fields'));
		}
		
		
		
	});
	
	$('#rawfilter-clean').on('click', function(e){
		$("#rawfilter-layer-group").prop('disabled', false);
		$("#rawfilter-layer").prop('disabled', true);
		$("#rawfilter-field").prop('disabled', true);
		$("#rawfilter-operator").prop('disabled', true);
		$("#rawfilter-selectvalue").prop('disabled', true);
		
		$("#rawfilter-layer-group option[value='__disabled__']").attr("selected", 'selected');
		$("#rawfilter-layer").empty().append('<option selected value="__disabled__">' + gettext('Select layer') + ' ...</option>');
		$("#rawfilter-field").empty().append('<option selected value="__disabled__">' + gettext('Select field') + ' ...</option>');
		$("#rawfilter-operator").empty().append('<option selected value="__disabled__">' + gettext('Select operator') + ' ...</option>');
		$("#rawfilter-selectvalue").empty().append('<option selected value="__disabled__">' + gettext('Select value') + ' ...</option>');
		
		$("#rawfilter-selectvalue-div").css('display', 'none');
		$("#rawfilter-inputvalue-div").css('display', 'none');
		
		bottomPanel.hidePanel();
		if (self.selectionTable) {
			self.selectionTable.getSource().clear();
		}
		
	});
	
};

/**
 * TODO.
 */
RawFilter.prototype.getLayers = function(group) {
	var self = this;
	
	var layers = null;
	for (var i=0; i < this.conf.layerGroups.length; i++) {
		if (group == this.conf.layerGroups[i].groupName) {
			layers = this.conf.layerGroups[i].layers;
		}
	}
	
	return layers;
};

/**
 * TODO.
 */
RawFilter.prototype.getFields = function(layer, workspace) {
	var self = this;
	
	var featureType = new Array();
	$.ajax({
		type: 'POST',
		async: false,
	  	url: '/gvsigonline/services/describeFeatureType/',
	  	data: {
	  		layer: layer,
	  		workspace: workspace,
	  		skip_pks: false
	  	},
	  	success	:function(response){
	  		if("fields" in response){
	  			featureType = response['fields'];
	  		}

		},
	  	error: function(e){
	  		console.log("Error! " + e);
	  	}
	});
	
	return featureType;
};

/**
 * TODO
 */
RawFilter.prototype.getUniqueValues = function(layer, workspace, field) {
	var self = this;
 
	var values = null;
	$.ajax({
		type: 'POST',
		async: false,
	  	url: '/gvsigonline/services/get_unique_values/',
	  	data: {
	  		'layer_name': layer,
			'layer_ws': workspace,
			'field': field
		},
	  	success	:function(response){
	  		if("values" in response){
	  			values = response['values'];
	  		}
		},
	  	error: function(){}
	});
	return values;
};

/**
 * TODO
 */
RawFilter.prototype.getFeatures = function(layer, workspace, wfsUrl, field, fieldType, value, operator) {
	var self = this;
 
	var features = null;
	$.ajax({
		type: 'POST',
		async: false,
	  	url: '/gvsigonline/services/get_feature_wfs/',
	  	data: {
	  		'layer_name': layer,
			'workspace': workspace,
			'wfs_url': wfsUrl,
			'field': field,
			'field_type': fieldType,
			'value': value,
			'operator': operator
		},
	  	success	:function(response){
	  		if("data" in response){
	  			features = response['data'];
	  		}
		},
	  	error: function(){}
	});
	return features;
};


RawFilter.prototype.describeLayerConfig = function(layer, workspace) {
	var layerConfig = {}
	$.ajax({
		type: 'POST',
		async: false,
	  	url: '/gvsigonline/services/describe_layer_config/',
	  	data: {
	  		'layer': layer,
			'workspace': workspace
		},
	  	success	:function(response){
	  		if("conf" in response['layer']){
				layerConfig = JSON.parse(response['layer']['conf'])
	  		}
		},
	  	error: function(){
		}
	});

	return layerConfig;
};
