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

/**
 * TODO
 */
var attributeTable = function(layer, map, prefix) {	
	this.id = "data-table";
	this.map = map;
	this.layer = layer;	
	this.prefix = prefix;
	this.source = new ol.source.Vector();				
	this.resultLayer = new ol.layer.Vector({
		source: this.source,
	  	style: new ol.style.Style({
	    	fill: new ol.style.Fill({
	      		color: 'rgba(255, 255, 255, 0.2)'
	    	}),
	    	stroke: new ol.style.Stroke({
	      		color: '#0099ff',
	      		width: 2
	    	}),
	    	image: new ol.style.Circle({
	      		radius: 7,
	      		fill: new ol.style.Fill({
	        		color: '#0099ff'
	      		})
	    	})
	  	})
	});
	this.resultLayer.baselayer = true;
	this.map.addLayer(this.resultLayer);
	this.initialize();
};

/**
 * TODO
 */
attributeTable.prototype.initialize = function() {
	this.source.clear();
	this.createTable(this.describeFeatureType());
};

/**
 * TODO
 */
attributeTable.prototype.describeFeatureType = function() {
	
	var featureType = new Array();
	$.ajax({
		type: 'POST',
		async: false,
	  	url: this.layer.wfs_url,
	  	data: {
	  		'service': 'WFS',
			'version': '1.1.0',
			'request': 'describeFeatureType',
			'typeName': this.layer.workspace + ":" + this.layer.layer_name, 
			'outputFormat': 'text/xml; subtype=gml/3.1.1'
		},
	  	success	:function(response){
	  		var elements = null;
			try {
				elements = response.getElementsByTagName('sequence')[0].children;
		    } catch(err) {
		    	elements = response.getElementsByTagName('xsd:sequence')[0].children;
		    }
			
			for (var i=0; i<elements.length; i++) {
				var element = {
					'name': elements[i].attributes[2].nodeValue,
					'type': elements[i].attributes[4].nodeValue
				};
				featureType.push(element);
			}
		},
	  	error: function(){}
	});
	
	return featureType;
};

/**
 * TODO
 */
attributeTable.prototype.createTable = function(featureType) {
	
	var self = this;
	
	var properties = new Array();
	var propertiesWithType = new Array();
	var columns = new Array();
	
	var table = $("<table>", {id: 'table-' + this.layer.get("id")});
	var thead = $("<thead>");
	var trow = $("<tr>");
	for (var i=0; i<featureType.length; i++) {
		if (featureType[i].type.indexOf('gml:') == -1) {
			if (!featureType[i].name.startsWith(this.prefix)) {
				properties.push(featureType[i].name);
				propertiesWithType.push(featureType[i].name + '|' + featureType[i].type);
				columns.push({
					"data": featureType[i].name
				});
				var th = $("<th>", {text: featureType[i].name});
				trow.append(th);
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
	
	$('#float-modal .modal-body').empty();
	$('#float-modal .modal-body').append(table);
	
	$('#table-' + this.layer.get("id")).DataTable({
		language: {
    		processing		: gettext("Processing request") + "...",
	        search			: gettext("Search") + "&nbsp;:",
	        lengthMenu		: gettext("Showing") + " _MENU_ " + gettext("registers"),
	        info			: gettext("Showing from") + " _START_ " + gettext("to") + " _END_",// + gettext("de") + " _TOTAL_ " + gettext("registros"),
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
	            sortAscending:  ": " + gettext("Sort Ascending"),
	            sortDescending: ": " + gettext("Sort Descending")
	        }
	    },
		select: true,
        "processing": true,
        "serverSide": true,
        "sCharSet": "utf-8",
        "scrollX": true,
        "ajax": {
            "url": "/gvsigonline/services/get_datatable_data/",
            "type": "POST",
            "data": function ( d ) {
                d.wfs_url = self.layer.wfs_url;
                d.layer_name = self.layer.layer_name;
                d.property_name = properties.toString();
                d.properties_with_type = propertiesWithType.toString();
            }
        },
        "columns": columns,
        "dom": '<"table-toolbar">frtip',
        "bSort" : false,
	    "bLengthChange": false
    });
	
	var htmlButtons = '';
	htmlButtons += 	'<div>';
	htmlButtons += 		'<a href="#" id="zoom-to-selection-button" style="margin-right: 20px;" class="btn btn-primary">' + gettext('Zoom to selection');
	htmlButtons += 		'<a href="#" id="clear-selection-button" class="btn btn-primary">' + gettext('Clear selection');
	htmlButtons += 	'</div>';
	$("div.table-toolbar").html(htmlButtons);
	$("#zoom-to-selection-button").click(function(){
    	var t = $('#table-' + self.layer.get("id")).DataTable();
    	var selected = t.row('.selected').data();
    	self.zoomToFeature(selected.featureid);
	});
	
	$("#clear-selection-button").click(function(){
    	self.source.clear()
	});

};


/**
 * TODO
 */
/**
 * TODO
 */
attributeTable.prototype.zoomToFeature = function(fid) {
	var self = this;
	var typename = fid.split('.')[0];
	
	$.ajax({
		type: 'POST',
		async: false,
	  	url: this.layer.wfs_url,							
	  	data: {
	  		'service': 'WFS',
			'version': '1.1.0',
			'request': 'GetFeature',
			'typename': this.layer.workspace + ':' + typename, 
			//'srsname': 'EPSG:4326',
			'outputFormat': 'application/json',
			'featureId': fid
	  	},
	  	success	:function(response){
	  		var newFeature = new ol.Feature();
	  		var sourceCRS = 'EPSG:' + response.crs.properties.name.split('::')[1];
	  		var projection = new ol.proj.Projection({
	    		code: sourceCRS,
	    	});
	    	ol.proj.addProjection(projection);
	    	if (response.features[0].geometry.type == 'Point') {
	    		newFeature.setGeometry(new ol.geom.Point(response.features[0].geometry.coordinates));				
	    	} else if (response.features[0].geometry.type == 'MultiPoint') {
	    		newFeature.setGeometry(new ol.geom.Point(response.features[0].geometry.coordinates[0]));				
	    	} else if (response.features[0].geometry.type == 'LineString' || response.features[0].geometry.type == 'MultiLineString') {
	    		newFeature.setGeometry(new ol.geom.MultiLineString([response.features[0].geometry.coordinates[0]]));
	    	} else if (response.features[0].geometry.type == 'Polygon' || response.features[0].geometry.type == 'MultiPolygon') {
	    		newFeature.setGeometry(new ol.geom.MultiPolygon(response.features[0].geometry.coordinates));
	    	}
	    	newFeature.setProperties(response.features[0].properties);
			newFeature.setId(response.features[0].id);
			
			
			newFeature.getGeometry().transform(projection, 'EPSG:3857');
			
			self.source.clear();
			self.source.addFeature(newFeature);
			
			var view = self.map.getView();			
			if (response.features[0].geometry.type == 'Point' || response.features[0].geometry.type == 'MultiPoint') {
				view.setCenter(newFeature.getGeometry().getFirstCoordinate());
				view.setZoom(14);
			} else {
				view.fit(newFeature.getGeometry().getExtent(), self.map.getSize());
			}
	  	},
	  	error: function(){}
	});
};


/**
 * TODO
 */
attributeTable.prototype.show = function() {
	$("#float-modal").modal('show');          
};