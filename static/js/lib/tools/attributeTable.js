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
var attributeTable = function(layer, map, conf) {	
	this.id = "data-table";
	this.map = map;
	this.conf = conf;
	this.layer = layer;	
	this.source = new ol.source.Vector();	
	this.filterCode = null;
	this.selectedType = null;
	this.resultLayer = new ol.layer.Vector({
		source: this.source,
	  	style: new ol.style.Style({
	    	fill: new ol.style.Fill({
	      		color: 'rgba(204, 255, 0, 0.4)'
	    	}),
	    	stroke: new ol.style.Stroke({
	      		color: '#CCFF00',
	      		width: 2
	    	}),
	    	image: new ol.style.Circle({
	      		radius: 7,
	      		fill: new ol.style.Fill({
	        		color: '#CCFF00'
	      		})
	    	})
	  	})
	});
	this.resultLayer.baselayer = true;
	this.resultLayer.setZIndex(99999999);
	this.map.addLayer(this.resultLayer);
	this.initialize();
};

/**
 * TODO
 */
attributeTable.prototype.initialize = function() {
	this.source.clear();
	this.createUI();
};

/**
 * TODO
 */
attributeTable.prototype.createUI = function() {
	
	var ui = '';
	
	ui += '<div class="row">';
	ui += 	'<div class="col-md-12">';
	ui += 		'<div class="nav-tabs-custom">';
	ui += 			'<ul class="nav nav-tabs">';
	ui += 				'<li class="active"><a href="#tab_data" data-toggle="tab"><i class="fa fa-table"></i></a></li>';
	ui += 				'<li><a href="#tab_filter" data-toggle="tab"><i class="fa fa-filter"></i></a></li>';
	ui +=				'<li class="pull-right"><a id="close-table" href="javascript:void(0)" class="text-muted"><i class="fa fa-times"></i></a></li>';
	ui += 			'</ul>';
	ui += 			'<div class="tab-content">';
	ui += 				'<div class="tab-pane active" id="tab_data">';
	ui += 				'</div>';
	ui += 				'<div class="tab-pane" id="tab_filter">';
	ui += 				'</div>';
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	$('.panel-content').empty();
	$('.panel-content').append(ui);
	
	var featureType = this.describeFeatureType();
	this.createTableUI(featureType);
	this.createFiltersUI(featureType);
};

/**
 * TODO
 */
attributeTable.prototype.createTableUI = function(featureType) {
	
	var self = this;
	
	var properties = new Array();
	var propertiesWithType = new Array();
	var columns = new Array();
	
	var table = $("<table>", {id: 'table-' + this.layer.get("id"), class: 'stripe nowrap cell-border hover', style: "width: 100%;"});
	var thead = $("<thead>", {style: "width: 100%;"});
	var trow = $("<tr>");
	var fields_trans = this.layer.conf;
	var language = $("#select-language").val();
	for (var i=0; i<featureType.length; i++) {
		if (!this.isGeomType(featureType[i].type)) {
			if (!featureType[i].name.startsWith(this.prefix)) {
				var column_shown = true;
				var feat_name = featureType[i].name;
				if(fields_trans != null && fields_trans["fields"] != undefined){
					var fields = fields_trans["fields"];
					for(var ix=0; ix<fields.length; ix++){
						if(fields[ix].name.toLowerCase() == feat_name){
							if("visible" in fields[ix]){
								column_shown = fields[ix].visible;
							}
							var feat_name_trans = fields[ix]["title-"+language];
							if(feat_name_trans){
								feat_name = feat_name_trans + "<br /><span class=\"subname\">(" + feat_name + ")</span>";
							}
						}
					}
				}
				
				if(column_shown){
					properties.push(featureType[i].name);
					propertiesWithType.push(featureType[i].name + '|' + featureType[i].type);
					columns.push({
						"data": featureType[i].name,
						"render": function ( data, type, full, meta ) {
							var value = data;
							if (data == "null" || data == null) {
								value = "";
							}
							return value;
						 }
					});
					
					var th = $("<th>", {html: feat_name});
					trow.append(th);
				}
			}
		}
	}
	var th = $("<th>", {text: 'featureid'});
	trow.append(th);
	columns.push({
		"data": 'featureid',
		"visible": false
	});
	thead.append(trow);
	table.append(thead);
	
	$('#tab_data').empty();
	$('#tab_data').append(table);
	
	var tableButtons = new Array();
	tableButtons.push({
		extend: 'csv',
		text: '<i class="fa fa-file-text-o margin-r-5"></i> CSV'
	});
	tableButtons.push({
   	 	extend: 'excel',
   	 	text: '<i class="fa fa-file-excel-o margin-r-5"></i> Excel'
	});
	tableButtons.push({
   	 	extend: 'print',
		text: '<i class="fa fa-file-pdf-o margin-r-5"></i> Pdf',
		title: self.conf.project_name
	});
	tableButtons.push({
    	text: '<i class="fa fa-search-plus margin-r-5"></i> ' + gettext('Zoom to selection'),
        action: function ( e, dt, node, config ) {
        	var t = $('#table-' + self.layer.get("id")).DataTable();
        	var selectedRows = t.rows('.selected').data();
	    	if (selectedRows.length > 0){	
	    		self.zoomToSelection(selectedRows);
	    		
	    	} else {
	    		messageBox.show('warning', gettext('You must select at least one row'));
	    	}
        	
        }
    });
	tableButtons.push({
   	 	extend: 'selectAll',
		text: '<i class="fa fa-list margin-r-5"></i> ' + gettext('Select all')
	});
	tableButtons.push({
		extend: 'selectNone',
        text: '<i class="fa fa-eraser margin-r-5"></i> ' + gettext('Clear selection')
    });
	
	var dt = $('#table-' + this.layer.get("id")).DataTable({
		language: {
    		processing		: gettext("Processing request") + "...",
	        search			: gettext("Search") + "&nbsp;:",
	        lengthMenu		: gettext("Showing") + " _MENU_ " + gettext("registers"),
	        info			: gettext("Showing from") + " _START_ " + gettext("to") + " _END_" + gettext(" of") + " _TOTAL_ " + gettext("registers"),
	        infoEmpty		: gettext("Showing from") + " 0 " + gettext("to") + " 0, " + gettext("of") + " 0 " + gettext("registers"),
	        infoFiltered	: "(" + gettext("Filtering") + " _MAX_ " + gettext("registers") + ")",
	        infoPostFix		: "",
	        loadingRecords	: gettext("Loading") + "...",
	        zeroRecords		: gettext("No records available"),
	        emptyTable		: gettext("No records available"),
	        paginate: {
	            first		: gettext("First"),
	            previous	: gettext("Previous"),
	            next		: gettext("Next"),
	            last		: gettext("Last")
	        },
	        aria: {
	            sortAscending:  ": " + gettext("Sort ascending"),
	            sortDescending: ": " + gettext("Sort descending")
	        }
	    },
	    select: {
            style: 'multi'
        },
        stateSave: true,
        "processing": true,
        "searching": this.showSearch,
        "serverSide": true,
        "sCharSet": "utf-8",
        "scrollX": true,
        scrollY: '50vh',
        scrollCollapse: true,
        "ajax": {
            "url": "/gvsigonline/services/get_datatable_data/",
            "type": "POST",
            "data": function ( d ) {
                d.wfs_url = self.layer.wfs_url;
                d.layer_name = self.layer.layer_name;
                d.workspace = self.layer.workspace;
                d.property_name = properties.toString();
                d.properties_with_type = propertiesWithType.toString();
                var cql_filter = '';
                if (self.filterCode != null) {
                	cql_filter = self.filterCode.getValue();
                	cql_filter = self.change_alias_from_cql_filter(cql_filter);
                }
                d.cql_filter = cql_filter;
            }
        },
        "columns": columns,
        dom: 'Bfrtp<"top"l><"bottom"i>',
        "bSort" : false,
	    "lengthMenu": [[10, 25, 50, 100, 500, 1000], [10, 25, 50, 100, 500, 1000]],
	    buttons: tableButtons
    });
};

attributeTable.prototype.change_alias_from_cql_filter = function(cql_filter) {
	var fields_trans = this.layer.conf;
	var language = $("#select-language").val();
	
	if(fields_trans != null && fields_trans["fields"] != undefined){
		var fields = fields_trans["fields"];
		for(var ix=0; ix<fields.length; ix++){
			var feat_name = fields[ix]["name"];
			var feat_name_trans = fields[ix]["title-"+language];
			if(feat_name_trans && feat_name){
				var filter_string =  new RegExp("("+feat_name_trans+")([^\\w'\"]+)","g");
				cql_filter = cql_filter.replace(filter_string, feat_name+"$2")
			}
			
		}
	}
	
	return cql_filter;
};

/**
 * TODO
 */
attributeTable.prototype.createFiltersUI = function(featureType) {
	var self = this;
	
	var fields_trans = this.layer.conf;
	var language = $("#select-language").val();
	
	var ui = '';
	ui += '<div style="background: #f6f6f6;" class="row">';
	ui += 	'<div class="col-md-12">';
	ui += 		'<div class="box box-default">';
	ui += 			'<div class="box-header with-border">';
	ui += 				'<h3 class="box-title">' + gettext('Advanced filter') + '</h3>';
	ui += 			'</div>';
	ui += 			'<div class="box-body">';
	ui += 				'<div class="row">';
	ui += 					'<div class="col-md-7">';
	ui += 						'<textarea id="cql_filter">';
	ui += 						'</textarea>';
//	ui += 						'<table>';
//	ui +=							'<tr>';
//	ui += 								'<td style="font-weight: bold; padding: 5px; width: 40%;">Expression = | <> | < | <= | > | >= Expression</td>';
//	ui += 								'<td>Comparison operations</td>';
//	ui +=							'</tr>';
//	ui +=							'<tr>';
//	ui += 								'<td style="font-weight: bold; padding: 5px; width: 40%;">Expression [ NOT ] BETWEEN Expression AND Expression</td>';
//	ui += 								'<td>Tests whether a value lies in or outside a range (inclusive)</td>';
//	ui +=							'</tr>';
//	ui +=							'<tr>';
//	ui += 								'<td style="font-weight: bold; padding: 5px; width: 40%;">Expression [ NOT ] LIKE | ILIKE like-pattern</td>';
//	ui += 								'<td>Simple pattern matching. like-pattern uses the % character as a wild-card for any number of characters. ILIKE does case-insensitive matching.</td>';
//	ui +=							'</tr>';
//	ui +=							'<tr>';
//	ui += 								'<td style="font-weight: bold; padding: 5px; width: 40%;">Expression [ NOT ] IN ( Expression { ,Expression } )</td>';
//	ui += 								'<td>Tests whether an expression value is (not) in a set of values</td>';
//	ui +=							'</tr>';
//	ui +=							'<tr>';
//	ui += 								'<td colspan="2" style="font-weight: bold; padding: 5px;">An expression specifies a attribute, literal, or computed value. The type of the value is determined by the nature of the expression.</td>';
//	ui +=							'</tr>';
//	ui += 						'</table>';
	ui += 					'</div>';
	ui += 					'<div class="col-md-5">';
	ui += 						'<div id="calculator">';
	ui += 							'<div class="form-group">';	
	ui += 								'<label>' + gettext('Select field') + '</label>';
	ui += 								'<select id="filter-field-select" class="form-control">';
	ui += 									'<option value="" selected disabled>--</option>';
	for (var i=0; i<featureType.length; i++) {
		if (!this.isGeomType(featureType[i].type)) {
			var feat_name = featureType[i].name;
			if(fields_trans != null && fields_trans["fields"] != undefined){
				var fields = fields_trans["fields"];
				for(var ix=0; ix<fields.length; ix++){
					if(fields[ix].name.toLowerCase() == feat_name){
						if("visible" in fields[ix]){
							column_shown = fields[ix].visible;
						}
						var feat_name_trans = fields[ix]["title-"+language];
						if(feat_name_trans){
							feat_name = feat_name_trans;
						}
					}
				}
			}
			
			
			
			ui += '<option class="filter-field-option" data-orig="' + featureType[i].name + '" value="' + featureType[i].type + '">' + feat_name + '</option>';
		}
	}
	ui += 								'</select>';
	ui += 							'</div>';
	ui += 							'<div class="form-group">';	
	ui += 								'<label>' + gettext('Select value') + '</label>';
	ui += 								'<select id="filter-value-select" class="form-control">';
	ui += 									'<option value="" selected disabled>--</option>';
	ui += 								'</select>';
	ui += 							'</div>';
	ui += 							'<div class="keys">';
	ui += 								'<span>=</span>';
	ui += 								'<span><></span>';
	ui += 								'<span><</span>';
	ui += 								'<span><=</span>';
	ui += 								'<span>></span>';
	ui += 								'<span>>=</span>';
	ui += 								'<span class="weight">AND</span>';
	ui += 								'<span class="weight">OR</span>';
	ui += 								'<span class="weight">NOT</span>';
	ui += 								'<span class="weight">IN</span>';
	ui += 								'<span>(</span>';
	ui += 								'<span>)</span>';
	ui += 								'<span>[</span>';
	ui += 								'<span>]</span>';
	ui += 								'<span>{</span>';
	ui += 								'<span>}</span>';
	ui += 							'</div>';
	ui += 							'<div class="bottom-selects">';
	ui += 							'</div>';
	ui += 						'</div>';
	ui += 					'</div>';
	ui += 				'</div>';
	ui += 			'</div>';
	ui += 			'<div class="box-footer clearfix">';
	ui += 				'<a id="apply-filter" href="javascript:void(0)" class="btn btn-default btn-flat pull-right"><i class="fa fa-check margin-r-5"></i>' + gettext('Apply filter') + '</a>';
	ui += 				'<a id="clear-filter" href="javascript:void(0)" class="btn btn-default btn-flat pull-right margin-r-5"><i class="fa fa-times margin-r-5"></i>' + gettext('Clear filter') + '</a>';
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	$('#tab_filter').empty();
	$('#tab_filter').append(ui);
	
	var filterElement = document.getElementById('cql_filter');
	this.filterCode = CodeMirror.fromTextArea(filterElement, {
		value: "",
		mode:  "javascript",
		theme: "xq-dark",
		lineNumbers: true,
		lineWrapping: true
	});
	
	// Add onclick event to all the keys and perform operations
	var keys = document.querySelectorAll('#calculator span');
	for(var i = 0; i < keys.length; i++) {
		keys[i].onclick = function(e) {
			var btnVal = this.innerText;
			var currentFilter = self.filterCode.getValue();
			currentFilter += btnVal + ' ';
			self.filterCode.setValue(currentFilter);		
		} 
	}
	
};

/**
 * TODO
 */
attributeTable.prototype.describeFeatureType = function(layer) {
	var featureType = new Array();
	$.ajax({
		type: 'POST',
		async: false,
	  	url: '/gvsigonline/services/describeFeatureType/',
	  	data: {
	  		'layer': layer.layer_name,
			'workspace': layer.workspace
		},
	  	success	:function(response){
	  		if("fields" in response){
	  			featureType = response['fields'];
	  		}
		},
	  	error: function(){}
	});
	
	return featureType;
};

attributeTable.prototype.isGeomType = function(type){
	if(type == 'POLYGON' || type == 'MULTIPOLYGON' || type == 'LINESTRING' || type == 'MULTILINESTRING' || type == 'POINT' || type == 'MULTIPOINT'){
		return true;
	}
	return false;
}

attributeTable.prototype.isNumericType = function(type){
	if(type == 'smallint' || type == 'integer' || type == 'bigint' || type == 'decimal' || type == 'numeric' ||
			type == 'real' || type == 'double precision' || type == 'smallserial' || type == 'serial' || type == 'bigserial' ){
		return true;
	}
	return false;
}

attributeTable.prototype.isStringType = function(type){
	if(type == 'character varying' || type == 'varchar' || type == 'character' || type == 'char' || type == 'text' ){
		return true;
	}
	return false;
}

attributeTable.prototype.isDateType = function(type){
	if(type == 'date' || type == 'timestamp' || type == 'time' || type == 'interval'){
		return true;
	}
	return false;
}

/**
 * TODO
 */
attributeTable.prototype.loadUniqueValues = function(field) {
	var self = this;
	
	$.ajax({
		type: 'POST',
		async: false,
	  	url: '/gvsigonline/services/get_unique_values/',
	  	data: {
	  		'layer_name': self.layer.layer_name,
			'layer_ws': self.layer.workspace,
			'field': field
		},
	  	success	:function(response){
	  		$("#filter-value-select").empty();
	  		$emptyOpt = $("<option></option>").attr("value", "").attr("selected", true).attr("disabled", true).text("---");
	  		$("#filter-value-select").append($emptyOpt);
	  		$.each(response.values, function(index, option) {
	  			$option = $("<option></option>").attr("value", option).text(option);
	  			$("#filter-value-select").append($option);
	  	    });
		},
	  	error: function(){}
	});
};

/**
 * TODO
 */
attributeTable.prototype.zoomToSelection = function(rows) {
	var self = this;

	var typename = rows[0].featureid.split('.')[0];
	var fids = new Array();
	for (var i=0; i<rows.length; i++) {
		fids.push(rows[i].featureid);
	}
	
	$.ajax({
		type: 'POST',
		async: false,
	  	url: this.layer.wfs_url,							
	  	data: {
	  		'service': 'WFS',
			'version': '1.1.0',
			'request': 'GetFeature',
			'typename': this.layer.workspace + ':' + typename, 
			'srsname': 'EPSG:3857',
			'outputFormat': 'application/json',
			'featureId': fids.toString()
	  	},
	  	success	:function(response){
	    	self.source.clear();
	    	
	    	for (var i=0; i<response.features.length; i++) {
	    		var newFeature = new ol.Feature();
		    	if (response.features[i].geometry.type == 'Point') {
		    		newFeature.setGeometry(new ol.geom.Point(response.features[i].geometry.coordinates));				
		    	} else if (response.features[i].geometry.type == 'MultiPoint') {
		    		newFeature.setGeometry(new ol.geom.Point(response.features[i].geometry.coordinates[0]));				
		    	} else if (response.features[i].geometry.type == 'LineString' || response.features[i].geometry.type == 'MultiLineString') {
		    		newFeature.setGeometry(new ol.geom.MultiLineString([response.features[i].geometry.coordinates[0]]));
		    	} else if (response.features[i].geometry.type == 'Polygon' || response.features[i].geometry.type == 'MultiPolygon') {
		    		newFeature.setGeometry(new ol.geom.MultiPolygon(response.features[i].geometry.coordinates));
		    	}
		    	newFeature.setProperties(response.features[i].properties);
				newFeature.setId(response.features[i].id);
				self.source.addFeature(newFeature);
	    	}
	    	
	    	var extent = self.source.getExtent();
	    	self.map.getView().fit(extent, map.getSize());
	  	},
	  	error: function(){}
	});

};


/**
 * TODO
 */
attributeTable.prototype.show = function() {
	bottomPanel.showPanel();
};

/**
 * TODO
 */
attributeTable.prototype.registerEvents = function() {
	var self = this;
	$("a[href='#tab_filter']").on('shown.bs.tab', function(e) {
		self.filterCode.refresh();
	 });
	
	$("#filter-field-select").on('change', function(){
		self.selectedType = $('option:selected', $(this)).val();
		var value = $('option:selected', $(this)).text();
    	var currentFilter = self.filterCode.getValue();
		currentFilter += value + ' ';
		self.filterCode.setValue(currentFilter);
		var value_orig = $('option:selected', $(this)).attr("data-orig");
		self.loadUniqueValues(value_orig);
	});
	
	$("#close-table").on('click', function(){
		bottomPanel.hidePanel();
	});
	
	$("#filter-value-select").on('change', function(){
		var currentFilter = self.filterCode.getValue();
		if (self.isStringType(self.selectedType)) {
			currentFilter += "'" + this.value + "' ";
			
		} else if (self.isDateType(self.selectedType)) {
			currentFilter += this.value + " ";
			
		}  else if (self.selectedType == 'xsd:boolean') {
			currentFilter += "'" + this.value + "' ";
			
		} else {
			currentFilter += this.value + ' ';
		}
		self.filterCode.setValue(currentFilter);
		$("#filter-field-select").prop('selectedIndex', 0);
	});
	
	$("#apply-filter").on('click', function(){
		var t = $('#table-' + self.layer.get("id")).DataTable();
		$('.nav-tabs a[href="#tab_data"]').tab('show');
		t.ajax.reload();
	});
	
	$("#clear-filter").on('click', function(){
		self.filterCode.setValue('');
		var t = $('#table-' + self.layer.get("id")).DataTable();
		$('.nav-tabs a[href="#tab_data"]').tab('show');
		t.ajax.reload();
	});
	
	
};