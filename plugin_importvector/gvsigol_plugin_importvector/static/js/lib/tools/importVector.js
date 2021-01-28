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
var ImportVector = function(conf, map) {
	var self = this;
	this.conf = conf;
	this.map = map;

	this.id = "importvector";
	this.$button = $("#importvector");

	var handler = function(e) {
		self.handler(e);
	};
	
	for (var crs in this.conf.supported_crs) {
		proj4.defs(this.conf.supported_crs[crs].code, this.conf.supported_crs[crs].definition);	
	}

	this.$button.on('click', handler);
	this.$button.on('touchstart', handler);

};

/**
 * TODO
 */
ImportVector.prototype.deactivable = true;

/**
 * @param {Event} e Browser event.
 */
ImportVector.prototype.handler = function(e) {
	e.preventDefault();
	var self = this;

	this.createUploadForm();
};

ImportVector.prototype.createUploadForm = function() {
	var self = this; 
	
	if(self.modal == null){
		self.modal = '';
		self.modal += '<div class="modal fade" id="modal-importvector-dialog" tabindex="-1" role="dialog" aria-labelledby="myModalLabel">';
		self.modal += 	'<div class="modal-dialog" role="document">';
		self.modal += 		'<div class="modal-content">';
		self.modal += 			'<div class="modal-header">';
		self.modal += 				'<h4 class="modal-title" id="myModalLabel">' + gettext('Import vector file') + '</h4>';
		self.modal += 			'</div>';
		self.modal += 			'<div class="modal-body">';
		self.modal += 					'<form id="addvector_form" class="addlayer">'; 
		self.modal += 						'<div class="row">';
		self.modal += 							'<div class="col-md-12 form-group">';	
		self.modal += 								'<label for="vectorfile">' + gettext('Vector file') + ' (shp.zip, *.kml, .json)</label>';
		self.modal += 								'<input class="form-control" id="vectorfile" name="vectorfile" type="file"  required="required" accept=".zip,.kml,.json">';
		self.modal +=								'<span id="vectorfile-error" style="display: none; color: red;">* ' + gettext('You must select a file') + '</span>';
		self.modal +=								'<span id="vectorfilesize-error" style="display: none; color: red;">* ' + gettext('The file is too large. You can publish it from the administrator') + '</span>';
		self.modal += 							'</div>';
		self.modal += 						'</div>';
		self.modal += 						'<div class="row">';
		self.modal += 							'<div class="col-md-12 form-group">';	
		self.modal += 								'<label for="vectortitle">' + gettext('Layer title in TOC') + '</label>';
		self.modal += 								'<input class="form-control" id="vectortitle" name="vectortitle" type="text">';
		self.modal +=								'<span id="vectortitle-error" style="display: none; color: red;">* ' + gettext('You must indicate a title for the layer') + '</span>'
		self.modal += 							'</div>';
		self.modal += 						'</div>'; 
		self.modal += 					'</form>';
		self.modal += 			'</div>';
		self.modal += 			'<div class="modal-footer">';
		self.modal += 				'<button id="button-importvector-cancel" type="button" class="btn btn-default" data-dismiss="modal">' + gettext('Close') + '</button>';
		self.modal += 				'<button id="button-importvector-accept" type="button" class="btn btn-default">' + gettext('Accept') + '</button>';
		self.modal += 			'</div>';
		self.modal += 		'</div>';
		self.modal += 	'</div>';
		self.modal += '</div>';
		$('body').append(self.modal);
		
		$("#modal-importvector-dialog").modal('show');
		
		$('#vectortitle').on('input', function(){
			$('#vectortitle-error').css('display', 'none');
		});
		
		$('#vectorfile').on('input', function(){
			$('#vectorfile-error').css('display', 'none');
			$('#vectorfilesize-error').css('display', 'none');
		});
		
		$('#button-importvector-accept').unbind("click").click(function(e){
			e.preventDefault();
			var title = $('#vectortitle').val();
			if (title == '') {
				$('#vectortitle-error').css('display', 'block');
				
			} else {
				$('body').overlay();
				var form = document.getElementById('addvector_form');
				var file = form[0].files[0];   
				if (file) {
					var size = file.size / 1024;
					if (size < 20000) {
						var currentProj = self.map.getView().getProjection();    
						var fr = new FileReader();   
						var sourceFormat = null;
						var source = new ol.source.Vector();
						var layerId = viewer.core._nextLayerId();
						var name = file.name.split('.')[0];
						var extension = file.name.split('.')[1];

						var style = self.getRandomStyle();	
						
						var vectorLayer = new ol.layer.Vector({
							id: layerId,
							source: source,
							name: name,
							style: style,
							strategy: ol.loadingstrategy.bbox
						});
						
						var geomType = null;
						if (extension == 'zip') {
							sourceFormat = new ol.format.GeoJSON();
							
							fr.onload = function (evt) {  
								var vectorData = evt.target.result;
								var dataProjection = sourceFormat.readProjection(vectorData) || currentProj;        
								shp(vectorData).then(function (geojson) {   
									geomType = geojson.features[0].geometry.type;
									vectorLayer.randomStyle = self.getVectorStyle(geomType);
									source.addFeatures(sourceFormat.readFeatures(geojson,  {                
										dataProjection: dataProjection,                
										featureProjection: currentProj            
									}));   
									$.overlayout();
								});
								
								
							};    
							fr.readAsArrayBuffer(file);
							
						} else if (extension == 'kml') {
							sourceFormat = new ol.format.KML({
								extractStyles: false,
					            extractAttributes: true
							});
							
							fr.onload = function (evt) {       
								var vectorData = evt.target.result;   
								var dataProjection = sourceFormat.readProjection(vectorData) || currentProj;        
								source.addFeatures(sourceFormat.readFeatures(vectorData,  {                
									dataProjection: dataProjection,                
									featureProjection: currentProj            
								}));
								geomType = 'LineString';
								if (vectorData.indexOf('<Point') > -1 || vectorData.indexOf('<MultiPoint') > -1) {
									geomType = 'Point';
									
								} else if (vectorData.indexOf('<LineString') > -1 || vectorData.indexOf('<MultiLineString') > -1) {
									geomType = 'LineString';
									
								} else if (vectorData.indexOf('<Polygon') > -1 || vectorData.indexOf('<MultiPolygon') > -1) {
									geomType = 'Polygon';
								}
								vectorLayer.randomStyle = self.getVectorStyle(geomType);
								$.overlayout();
								
								
							};    
							fr.readAsText(file);
							
						} else if (extension == 'json') {
							sourceFormat = new ol.format.GeoJSON();
							
							fr.onload = function (evt) {       
								var vectorData = evt.target.result;
								var jsonVectorData = JSON.parse(vectorData);
								var dataProjection = 'EPSG:4326';
								if (jsonVectorData.crs) {
									if (jsonVectorData.crs.properties) {
										if (jsonVectorData.crs.properties.name) {
											var crsName = jsonVectorData.crs.properties.name.split('::');
											if (crsName.length > 1) {
												dataProjection = 'EPSG:' + jsonVectorData.crs.properties.name.split('::')[1];
											}
										}
									} 
								}
								       
								source.addFeatures(sourceFormat.readFeatures(vectorData,  {                
									dataProjection: dataProjection,                
									featureProjection: currentProj            
								}));
								geomType = jsonVectorData.features[0].geometry.type;
								vectorLayer.randomStyle = self.getVectorStyle(geomType);
								$.overlayout();
								
								
							};    
							fr.readAsText(file);
						} 
						
						vectorLayer.baselayer = false;
						vectorLayer.setZIndex(99999999);
						vectorLayer.dataid = layerId;
						vectorLayer.id = layerId;
						vectorLayer.layer_name = name;
						vectorLayer.queryable = false;
						vectorLayer.title = title;
						vectorLayer.visible = true;
						vectorLayer.imported = true;
						vectorLayer.is_vector = true;
						vectorLayer.printable = true;

						self.map.addLayer(vectorLayer);
						self.createVectorLayerUI (vectorLayer, layerId);
						$("#modal-importvector-dialog").modal('hide');
						self.modal = null;
						
					} else {
						$('#vectorfilesize-error').css('display', 'block');
						$.overlayout();
					}
					
				} else {
					$('#vectorfile-error').css('display', 'block');
					$.overlayout();
				}
				
			}
			
		});

		$('#button-importvector-cancel').unbind("click").click(function(){
			$("#modal-importvector-dialog").modal('hide');
			self.modal = null;
		});
		
	} else {
		$("#modal-importvector-dialog").modal('hide');
		self.modal = null;
	}
};

ImportVector.prototype.getVectorStyle = function(gtype) {
	if (gtype == 'Point' || gtype == 'MultiPoint') {
		return {
			"version" : "2",
			"*" : {
				"symbolizers" : [{
					"type" : "point",
					"fillColor": this.vectorRandomStyle.fill_color,
					"fillOpacity": this.vectorRandomStyle.fill_opacity,
					"graphicName": "circle",
					"pointRadius": this.vectorRandomStyle.radius,
					"strokeColor": this.vectorRandomStyle.stroke_color,
					"strokeWidth": this.vectorRandomStyle.stroke_width
				}
			]}
		};
		
	} else if (gtype == 'LineString' || gtype == 'MultiLineString') {
		return {
			"version" : "2",
			"*" : {
				"symbolizers" : [{
					"type" : "line",
					"strokeColor": this.vectorRandomStyle.stroke_color,
					"strokeWidth": this.vectorRandomStyle.stroke_width
				}
			]}
		};
		
	} else if (gtype == 'Polygon' || gtype == 'MultiPolygon') {
		return {
			"version" : "2",
			"*" : {
				"symbolizers" : [{
					"type" : "polygon",
					"fillColor": this.vectorRandomStyle.fill_color,
					"fillOpacity": this.vectorRandomStyle.fill_opacity,
					"strokeColor": this.vectorRandomStyle.stroke_color,
					"strokeWidth": this.vectorRandomStyle.stroke_width
				}
			]}
		};
		
	}
};

ImportVector.prototype.getRandomStyle = function() {
	
	var getColor = function () { return Math.floor(Math.random()*256) };	
	var r = getColor();
	var g = getColor();
	var b = getColor();
    var rgbColor = "rgb(" + r + "," + g + "," + b + ")";
    var rgbColorOpacity = "rgba(" + r + "," + g + "," + b + ", 0.3)";
    var hexColor = this.rgbToHex(r,g,b);
    	
    this.vectorRandomStyle = {
    	fill_color: hexColor,
    	fill_opacity: 0.3,
    	stroke_color: hexColor,
    	stroke_width: 2,
    	radius: 7
    };
	
	var style = new ol.style.Style({
    	fill: new ol.style.Fill({
      		color: rgbColorOpacity
    	}),
    	stroke: new ol.style.Stroke({
      		color: rgbColor,
      		width: 2
    	}),
    	image: new ol.style.Circle({
      		radius: 7,
      		stroke: new ol.style.Stroke({
          		color: rgbColor,
          		width: 2
        	}),
      		fill: new ol.style.Fill({
      			color: rgbColorOpacity
      		})
    	})
  	});
	return style;
};

ImportVector.prototype.rgbToHex = function(r, g, b) {
	return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
};

ImportVector.prototype.createLayerGroup = function() {
	var self = this;
	var groupId = 'gvsigol-importvector-group';

	var group = '';
	group += '			<li class="box box-default collapsed-box" id="' + groupId + '">';
	group += '				<div class="box-header with-border">';
	group += '					<i style="cursor: pointer;" class="layertree-folder-icon fa fa-folder-o"></i>';
	group += '					<span class="text">' + gettext("Imported vector files") + '</span>';
	group += '					<div class="box-tools pull-right">';
	group += '						<button class="btn btn-box-tool btn-box-tool-custom group-collapsed-button" data-widget="collapse">';
	group += '							<i class="fa fa-plus"></i>';
	group += '						</button>';
	group += '					</div>';
	group += '				</div>';
	group += '				<div data-groupnumber="' + (101 * 100) + '" class="box-body layer-tree-groups importvector-layer-group" style="display: none;">';
	group += '				</div>';
	group += '			</li>';

	$(".layer-tree").append(group);
	
	$(".layertree-folder-icon").click(function(){
		if (this.parentNode.parentNode.className == 'box box-default') {
			this.parentNode.parentNode.className = 'box box-default collapsed-box';
			$(this.parentNode.parentNode.children[1]).css('display', 'none');
			this.parentNode.parentNode.children[0].children[0].className = "layertree-folder-icon fa fa-folder-o";
			if (this.parentNode.parentNode.children[0].children[2].children[0].children[0].className == "fa fa-minus") {
				this.parentNode.parentNode.children[0].children[2].children[0].children[0].className = "fa fa-plus";
			} else if (this.parentNode.parentNode.children[0].children[2].children[0].children[0].className == "fa fa-plus"){
				this.parentNode.parentNode.children[0].children[2].children[0].children[0].className = "fa fa-minus";
			}
		} else if (this.parentNode.parentNode.className == 'box box-default collapsed-box') {
			this.parentNode.parentNode.className = 'box box-default';
			$(this.parentNode.parentNode.children[1]).css('display', 'block');
			this.parentNode.parentNode.children[0].children[2].children[0].children[0].className = "fa fa-plus";
			this.parentNode.parentNode.children[0].children[0].className = "layertree-folder-icon fa fa-folder-open-o";
			if (this.parentNode.parentNode.children[0].children[2].children[0].children[0].className == "fa fa-minus") {
				this.parentNode.parentNode.children[0].children[2].children[0].children[0].className = "fa fa-plus";
			} else if (this.parentNode.parentNode.children[0].children[2].children[0].children[0].className == "fa fa-plus"){
				this.parentNode.parentNode.children[0].children[2].children[0].children[0].className = "fa fa-minus";
			}
		}
	});
	
	$("[data-widget='collapse']").click(function(){
		if (this.parentNode.parentNode.children[0].className == 'layertree-folder-icon fa fa-folder-o') {
			this.parentNode.parentNode.children[0].className = 'layertree-folder-icon fa fa-folder-open-o';
		} else if (this.parentNode.parentNode.children[0].className == 'layertree-folder-icon fa fa-folder-open-o') {
			this.parentNode.parentNode.children[0].className = 'layertree-folder-icon fa fa-folder-o';
		}
	});
}


ImportVector.prototype.reorder = function(event,ui) {
	var groupNumber = ui.item[0].parentNode.dataset.groupnumber;
	var groupLayers = ui.item[0].parentNode.children;
	var mapLayers = this.map.getLayers();

	var zindex = parseInt(groupNumber);
	var mapLayers_length = mapLayers.getLength();

	for (var i=0; i<groupLayers.length; i++) {
		var layerid = groupLayers[i].dataset.layerid;
		mapLayers.forEach(function(layer){
			if (layer.get('id') == layerid) {
				layer.setZIndex(parseInt(zindex) + mapLayers_length);
				mapLayers_length--;
			}
		}, this);
	}
};

ImportVector.prototype.createVectorLayerUI = function(vectorLayer, dataId) {
	var self = this;
	
	var groupId = "gvsigol-importvector-group";
	var groupEntry = $("#"+groupId);
	var zIndex = groupEntry.length;
	if(zIndex == 0){
		self.createLayerGroup();
	}

	var layerTree = viewer.core.getLayerTree();
	
	var removeLayerButtonUI = '<a id="remove-vector-layer-' + dataId + '" data-layerid="' + dataId + '" class="btn btn-block btn-social btn-custom-tool remove-vector-layer-btn">';
	removeLayerButtonUI +=    '	<i class="fa fa-times"></i> ' + gettext('Remove layer');
	removeLayerButtonUI +=    '</a>';
	
	var vectorLayerUI = $(layerTree.createOverlayUI(vectorLayer, $("#"+groupId).is(":checked")));
	vectorLayerUI.find(".box-body .zoom-to-layer").after(removeLayerButtonUI);
	$(".importvector-layer-group").append(vectorLayerUI);
	layerTree.setLayerEvents();

	$(".remove-vector-layer-btn").unbind("click").click(function (e) {
		var id = $(this).attr("data-layerid");
		var layers = self.map.getLayers();
		layers.forEach(function(layer){
			if (!layer.baselayer && !layer.external) {
				if (layer.get("id") === id) {
					layer.setVisible(false);
					self.map.removeLayer([layer]);
					$("#layer-box-" + id).remove();
				}
			};
		}, this);
	});
};

/**
 * TODO
 */
ImportVector.prototype.deactivate = function() {
};