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
var SelectionTable = function(map, conf, features, layerName, workspace, wfsUrl) {
	this.id = "selection-data-table";
	this.map = map;
	this.conf = conf;
	this.features = features;
	this.layerName = layerName;
	this.workspace = workspace;
	this.wfsUrl = wfsUrl;
	this.selectionTable = null;

	this.selectionTableSource = new ol.source.Vector();
	this.selectionTableLayer = new ol.layer.Vector({
		source: this.selectionTableSource,
	  	style: new ol.style.Style({
	    	fill: new ol.style.Fill({
	      		color: 'rgba(229, 121, 228, 1.0)'
	    	}),
	    	stroke: new ol.style.Stroke({
	      		color: 'rgba(229, 121, 228, 1.0)',
	      		width: 2
	    	}),
	    	image: new ol.style.Circle({
	      		radius: 7,
	      		fill: new ol.style.Fill({
	        		color: 'rgba(229, 121, 228, 1.0)'
	      		})
	    	})
	  	})
	});
	this.selectionTableLayer.baselayer = true;
	this.selectionTableLayer.setZIndex(99999999);
	this.map.addLayer(this.selectionTableLayer);

	this.initialize();
};


/**
 * TODO
 */
SelectionTable.prototype.initialize = function() {
	this.selectionTableSource.clear();
	this.createSelectionTable();
};

/**
 * TODO
 */
SelectionTable.prototype.createSelectionTable = function() {

	var ui = '';

	ui += '<div class="row">';
	ui += 	'<div class="col-md-12">';
	ui += 		'<div class="nav-tabs-custom">';
	ui += 			'<div>';
	ui += 			'<ul class="nav nav-tabs">';
	ui += 				'<li class="active"><a href="#tab_table" data-toggle="tab"><i class="fa fa-table"></i></a></li>';
	ui +=				'<li class="pull-right"><a id="close-selectiontable" href="javascript:void(0)" class="text-muted"><i class="fa fa-times"></i></a></li>';
	ui +=				'<li class="pull-right"><a id="maximize-selectiontable" href="javascript:void(0)" class="text-muted"><i class="fa fa-table"></i></a></li>';
	ui +=				'<li class="pull-right"><a id="minimize-selectiontable" href="javascript:void(0)" class="text-muted"><i class="fa fa-minus"></i></a></li>';
	ui += 			'</ul>';
	ui += 			'<div class="tab-content">';
	ui += 				'<div class="tab-pane active" id="tab_table">';
	ui += 				'</div>';
	ui += 			'</div>';
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';

	$('.panel-content').empty();
	$('.panel-content').append(ui);

	var featureType = this.describeFeatureType();
	this.createTableUI(featureType);
};

/**
 * TODO
 */
SelectionTable.prototype.createTableUI = function(featureType) {

	var self = this;

	var properties = new Array();
	var propertiesWithType = new Array();
	var columns = new Array();
	
	featureType.sort(function(a, b) {
	    var textA = a.name.toUpperCase();
	    var textB = b.name.toUpperCase();
	    return (textA < textB) ? -1 : (textA > textB) ? 1 : 0;
	});

	var table = $("<table>", {id: 'table-' + this.layerName, class: 'stripe nowrap cell-border hover', style: "width: 100%; padding: 10px;"});
	var thead = $("<thead>", {style: "width: 100%;"});
	var trow = $("<tr>");
	for (var i=0; i<featureType.length; i++) {
		if (!this.isGeomType(featureType[i].type)) {
			var featName = featureType[i].name;
			var featType = featureType[i].type;

			var visible = true;
			if (featName == 'id' || featName == 'featureid') {
				visible = false;
			}
			columns.push({
				data: featName,
				render: function ( data, type, full, meta ) {
					var value = data;
					if (data == "null" || data == null) {
						value = "";
					}
					if(typeof data == 'boolean' && data == true){
						value = "<input type='checkbox' checked onclick=\"return false;\">";
					}
					if(typeof data == 'boolean' && data == false){
						value = "<input type='checkbox' onclick=\"return false;\">";
					}
					return value;
				 },
				 visible: visible
			});

			var th = $("<th>", {text: featName});
			trow.append(th);
		}
	}
	thead.append(trow);
	table.append(thead);

	$('#tab_table').empty();
	$('#tab_table').append(table);
	
	var orderedColumns = columns.sort(function(a, b) {
	    var textA = a.data.toUpperCase();
	    var textB = b.data.toUpperCase();
	    return (textA < textB) ? -1 : (textA > textB) ? 1 : 0;
	});
	
	
	var rows = [];
	for (var i=0; i<this.features.length; i++) {
		var arrayFeats = this.features;
		var row = [];
		var sorted = Object.keys(arrayFeats[i])
	    .sort()
	    .reduce(function (acc, k) { 
	        acc[k] = arrayFeats[i][k];
	        return acc;
	    }, {});
		rows.push(sorted);
	}
	
	var tableButtons = new Array();
	tableButtons.push({
		extend: 'csvHtml5',
		text: '<i class="fa fa-file-text-o margin-r-5"></i> CSV',
		exportOptions: {
            format: {
                body: function ( data, row, column, node ) {
                	if(node == null || node.firstChild == null){
                		return "";
                	}
                	if(node.firstChild.type == "checkbox"){
                		return node.firstChild.checked;
                	}
                    return node.textContent;
                }
            }
        }
	});
	tableButtons.push({
   	 	extend: 'excelHtml5',
   	 	text: '<i class="fa fa-file-excel-o margin-r-5"></i> Excel',
		exportOptions: {
            format: {
                body: function ( data, row, column, node ) {
                	if(node == null || node.firstChild == null){
                		return "";
                	}
                	if(node.firstChild.type == "checkbox"){
                		return node.firstChild.checked;
                	}
                    return node.textContent;
                }
            }
        }

	});

	var self = this;
	this.selectionTable = $('#table-' + this.layerName).DataTable({
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
            style: 'single',
            items: 'row'
        },
        "sCharSet": "utf-8",
        "scrollX": true,
        scrollY: '50vh',
        scrollCollapse: true,
        columns: orderedColumns,
        data: rows,
        dom: 'Bfrtp<"top"l><"bottom"i>',
        "bSort" : false,
	    "lengthMenu": [[10, 25, 50, 100, 500, 1000], [10, 25, 50, 100, 500, 1000]],
	    buttons: tableButtons,
	    "drawCallback": function(settings, json) {
	        self.getFeatures();
	    }
    });
	
	this.selectionTable.on('select', function(e, dt, type, indexes) {
	    if (type === 'row') {
	    	var selected = dt.rows({selected: true});
	    	if ( selected.count() == 1 ) {
	    		var featureid = dt.rows(selected[0]).data()[0]['featureid'];
	    		 
		        for (var i=0; i<self.selectionTableLayer.getSource().getFeatures().length; i++) {
					if (self.selectionTableLayer.getSource().getFeatures()[i].getId() == featureid) {	
						var feature = self.selectionTableLayer.getSource().getFeatures()[i];											
			
						var featExtent = feature.getGeometry().getExtent();
						self.map.getView().fit(featExtent, self.map.getSize());
					}
				}
		        
	    	}	   
	        
	    }
	});
};

/**
 * TODO
 */
SelectionTable.prototype.show = function() {
	bottomPanel.showPanel();
};

/**
 * TODO
 */
SelectionTable.prototype.registerEvents = function() {
	var self = this;
	$("#close-selectiontable").on('click', function(){
		bottomPanel.hidePanel();
		self.selectionTableSource.clear();
	});

	$("#minimize-selectiontable").on('click', function(){
		bottomPanel.minimizePanel();
	});

	$("#maximize-selectiontable").on('click', function(){
		bottomPanel.maximizePanel();
	});
};

/**
 * TODO
 */
SelectionTable.prototype.getSource = function() {
	return this.selectionTableSource;
};

/**
 * TODO
 */
SelectionTable.prototype.describeFeatureType = function() {
	var featureType = new Array();
	$.ajax({
		type: 'POST',
		async: false,
	  	url: '/gvsigonline/services/describeFeatureType/',
	  	data: {
	  		'layer': this.layerName,
			'workspace': this.workspace,
			'skip_pks': false
		},
	  	success	:function(response){
	  		if("fields" in response){
	  			featureType = response['fields'];
	  		}
	  		featureType.push({
	  			length: 255,
	  			name: "featureid",
	  			nullable: "NO",
	  			type: "character varying"
	  		});
		},
	  	error: function(){}
	});

	return featureType;
};

SelectionTable.prototype.isGeomType = function(type){
	if(type == 'POLYGON' || type == 'MULTIPOLYGON' || type == 'LINESTRING' || type == 'MULTILINESTRING' || type == 'POINT' || type == 'MULTIPOINT'){
		return true;
	}
	return false;
};

SelectionTable.prototype.isNumericType = function(type){
	if(type == 'smallint' || type == 'integer' || type == 'bigint' || type == 'decimal' || type == 'numeric' ||
			type == 'real' || type == 'double precision' || type == 'smallserial' || type == 'serial' || type == 'bigserial' ){
		return true;
	}
	return false;
};

SelectionTable.prototype.isStringType = function(type){
	if(type == 'character varying' || type == 'varchar' || type == 'character' || type == 'char' || type == 'text' ){
		return true;
	}
	return false;
};

SelectionTable.prototype.isDateType = function(type){
	if(type == 'date' || type.startsWith('timestamp') || type.startsWith('time') || type == 'interval'){
		return true;
	}
	return false;
};


SelectionTable.prototype.getFeatures = function(){
	var self = this;

	var typename = this.features[0].featureid.split('.')[0];
	var fids = new Array();
	for (var i=0; i<this.features.length; i++) {
		fids.push(this.features[i].featureid);
	}

	$.ajax({
		type: 'POST',
		async: false,
	  	url: this.wfsUrl,
	  	data: {
	  		'service': 'WFS',
			'version': '1.1.0',
			'request': 'GetFeature',
			'typename': this.workspace + ':' + typename,
			'srsname': 'EPSG:3857',
			'outputFormat': 'application/json',
			'featureId': fids.toString()
	  	},
	  	success	:function(response){
	    	self.selectionTableSource.clear();

	    	if (response.features.length > 0 ) {
	    		for (var i=0; i<response.features.length; i++) {
		    		var newFeature = new ol.Feature();
			    	if (response.features[i].geometry.type == 'Point') {
			    		newFeature.setGeometry(new ol.geom.Point(response.features[i].geometry.coordinates));
			    	} else if (response.features[i].geometry.type == 'MultiPoint') {
			    		newFeature.setGeometry(new ol.geom.MultiPoint(response.features[i].geometry.coordinates));
			    	} else if (response.features[i].geometry.type == 'LineString') {
			    		newFeature.setGeometry(new ol.geom.LineString(response.features[i].geometry.coordinates));
			    	} else if (response.features[i].geometry.type == 'MultiLineString') {
			    		newFeature.setGeometry(new ol.geom.MultiLineString(response.features[i].geometry.coordinates));
			    	} else if (response.features[i].geometry.type == 'Polygon') {
			    		newFeature.setGeometry(new ol.geom.Polygon(response.features[i].geometry.coordinates));
			    	} else if (response.features[i].geometry.type == 'MultiPolygon') {
			    		newFeature.setGeometry(new ol.geom.MultiPolygon(response.features[i].geometry.coordinates));
			    	}
			    	newFeature.setProperties(response.features[i].properties);
					newFeature.setId(response.features[i].id);
					self.selectionTableSource.addFeature(newFeature);
		    	}

		    	var extent = self.selectionTableSource.getExtent();
		    	self.map.getView().fit(extent, self.map.getSize());

	    	} else {
	    		messageBox.show('warning', gettext('Invalid identifier. Unable to get requested geometry'));
	    	}

	  	},
	  	error: function(){}
	});

};

/**
 * TODO
 */
SelectionTable.prototype.zoomToSelection = function(rows) {
	var self = this;

	var typename = rows[0].featureid.split('.')[0];
	var fids = new Array();
	for (var i=0; i<rows.length; i++) {
		fids.push(rows[i].featureid);
	}

	$.ajax({
		type: 'POST',
		async: false,
	  	url: this.wfsUrl,
	  	data: {
	  		'service': 'WFS',
			'version': '1.1.0',
			'request': 'GetFeature',
			'typename': this.workspace + ':' + typename,
			'srsname': 'EPSG:3857',
			'outputFormat': 'application/json',
			'featureId': fids.toString()
	  	},
	  	success	:function(response){
	    	self.selectionTableSource.clear();

	    	if (response.features.length > 0 ) {
	    		for (var i=0; i<response.features.length; i++) {
		    		var newFeature = new ol.Feature();
			    	if (response.features[i].geometry.type == 'Point') {
			    		newFeature.setGeometry(new ol.geom.Point(response.features[i].geometry.coordinates));
			    	} else if (response.features[i].geometry.type == 'MultiPoint') {
			    		newFeature.setGeometry(new ol.geom.MultiPoint(response.features[i].geometry.coordinates));
			    	} else if (response.features[i].geometry.type == 'LineString') {
			    		newFeature.setGeometry(new ol.geom.LineString(response.features[i].geometry.coordinates));
			    	} else if (response.features[i].geometry.type == 'MultiLineString') {
			    		newFeature.setGeometry(new ol.geom.MultiLineString(response.features[i].geometry.coordinates));
			    	} else if (response.features[i].geometry.type == 'Polygon') {
			    		newFeature.setGeometry(new ol.geom.Polygon(response.features[i].geometry.coordinates));
			    	} else if (response.features[i].geometry.type == 'MultiPolygon') {
			    		newFeature.setGeometry(new ol.geom.MultiPolygon(response.features[i].geometry.coordinates));
			    	}
			    	newFeature.setProperties(response.features[i].properties);
					newFeature.setId(response.features[i].id);
					self.selectionTableSource.addFeature(newFeature);
		    	}

		    	var extent = self.selectionTableSource.getExtent();
		    	self.map.getView().fit(extent, self.map.getSize());

	    	} else {
	    		messageBox.show('warning', gettext('Invalid identifier. Unable to get requested geometry'));
	    	}

	  	},
	  	error: function(){}
	});

};