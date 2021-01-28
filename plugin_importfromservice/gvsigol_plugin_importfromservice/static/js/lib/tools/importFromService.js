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
var ImportFromService = function(conf, map) {
	var self = this;
	this.conf = conf;
	this.map = map;
	this.wmsLayers = null;

	this.id = "importfromservice";
	this.$button = $("#importfromservice");

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
ImportFromService.prototype.deactivable = true;

/**
 * @param {Event} e Browser event.
 */
ImportFromService.prototype.handler = function(e) {
	e.preventDefault();
	var self = this;

	this.createServiceForm();
};

ImportFromService.prototype.createServiceForm = function() {
	var self = this; 
	
	if(self.modal == null){
		self.modal = '';
		self.modal += '<div class="modal fade" id="modal-importfromservice-dialog" tabindex="-1" role="dialog" aria-labelledby="myModalLabel">';
		self.modal += 	'<div class="modal-dialog" role="document">';
		self.modal += 		'<div class="modal-content">';
		self.modal += 			'<div class="modal-header">';
		self.modal += 				'<h4 class="modal-title" id="myModalLabel">' + gettext('Import layer from service') + '</h4>';
		self.modal += 			'</div>';
		self.modal += 			'<div class="modal-body">';
		self.modal += 					'<form id="addvector_form" class="addlayer">'; 
		self.modal += 						'<div class="row">';
		self.modal += 							'<div class="col-md-2 form-group">';	
		self.modal += 								'<label>' + gettext('Service') + '</label>';
		self.modal += 								'<select id="servicetype" class="form-control">';
		self.modal += 									'<option value="WMS" selected>WMS</option>';
		self.modal += 									'<option value="WFS">WFS</option>';
		self.modal += 								'</select>';
		self.modal += 							'</div>';
		self.modal += 							'<div class="col-md-8 form-group">';	
		self.modal += 								'<label for="serviceurl">' + gettext('Service URL') + '</label>';
		self.modal += 								'<input class="form-control" id="serviceurl" name="serviceurl" type="text" required="required">';
		self.modal += 							'</div>';
		self.modal += 							'<div class="col-md-2 form-group">';
		self.modal += 								'<label for="button-importfromservice-connect"></label>';
		self.modal += 								'<button id="button-importfromservice-connect" type="button" class="btn btn-default">' + gettext('Connect') + '</button>';
		self.modal += 							'</div>';
		self.modal += 						'</div>';
		self.modal += 						'<div class="row">';
		self.modal += 							'<div class="col-md-12 form-group">';	
		self.modal +=								'<span id="serviceurl-error" style="display: none; color: red;">* ' + gettext('You must type a valid URL') + '</span>';
		self.modal +=								'<span id="mixedcontent-error" style="display: none; color: red;">* ' + gettext('Mixed content: The page at was loaded over HTTPS, but requested an insecure URL') + '</span>';
		self.modal += 							'</div>';
		self.modal += 						'</div>';
		self.modal += 					'</form>';
		self.modal += 					'<div class="row" style="max-height: 300px; overflow: auto; padding-right: 20px;">';
		self.modal += 						'<ul id="importfromservice-layerlist" class="products-list product-list-in-box list">';	
		self.modal += 						'</ul>';
		self.modal += 					'</div>';
		self.modal += 			'</div>';
		self.modal += 			'<div class="modal-footer">';
		self.modal += 				'<button id="button-importfromservice-cancel" type="button" class="btn btn-default" data-dismiss="modal">' + gettext('Close') + '</button>';
		self.modal += 			'</div>';
		self.modal += 		'</div>';
		self.modal += 	'</div>';
		self.modal += '</div>';
		$('body').append(self.modal);
		
		$("#modal-importfromservice-dialog").modal('show');
		
		$('#serviceurl').on('input', function(){
			$('#serviceurl-error').css('display', 'none');
			$('#mixedcontent-error').css('display', 'none');
		});
		
		$('#button-importfromservice-connect').unbind("click").click(function(e){
			e.preventDefault();
			var serviceURL = $('#serviceurl').val();
			var serviceType = $('option:selected', $('#servicetype')).val();
			var currentProtocol = window.location.href.split("/")[0];
			currentProtocol = currentProtocol.substring(0, currentProtocol.length - 1);
			var protocol = serviceURL.split("/")[0];
			protocol = protocol.substring(0, protocol.length - 1);
			if (serviceURL == '') {
				$('#serviceurl-error').css('display', 'block');
				
			} else {
				if (protocol == currentProtocol) {
					if (serviceURL.endsWith('?')) {
						serviceURL = serviceURL.substring(0, serviceURL.length - 1);
					}
					if (serviceURL.includes('?')) {
						serviceURL = serviceURL.split('?')[0];
					}
					var url = serviceURL + '?request=GetCapabilities&service=' + serviceType;
					var parser = new ol.format.WMSCapabilities();
					$.ajax(url).then(function(response) {
						if (serviceType == 'WMS') {
							var parser = new ol.format.WMSCapabilities();
							var result = parser.read(response);
							self.wmsLayers = result.Capability.Layer.Layer;
							
							$('#importfromservice-layerlist').empty();
							for (var i=0; i<self.wmsLayers.length; i++) {
								var htmlLayer = '';
								htmlLayer += '<li class="item">';
								htmlLayer += 	'<div class="product-info">';
								htmlLayer += 		'<a data-layername="' + self.wmsLayers[i].Name + '" href="" class="product-title load-wms-layer">' + self.wmsLayers[i].Name + '<span style="font-size: 100%; font-weight: 500; padding: .5em .5em .5em;" class="btn btn-default pull-right"><i class="fa fa-globe margin-r-5"></i>' + gettext('Load layer') + '</span></a>'; 
								htmlLayer += 		'<span class="product-description">' + self.wmsLayers[i].Title + '</span>';
								htmlLayer += 	'</div>';
								htmlLayer += '</li>';
								
								$('#importfromservice-layerlist').append(htmlLayer);
							}
							
							$('.load-wms-layer').on('click', function(e){
								e.preventDefault();
								var layerName = this.dataset.layername;
								for (var i=0; i<self.wmsLayers.length; i++) {
									if (self.wmsLayers[i].Name == layerName) {
										self.loadWMSLayer(serviceURL, self.wmsLayers[i]);
									}
								}
							});
							
						} else if (serviceType == 'WFS') {
							self.featureTypeList = response.getElementsByTagName("FeatureTypeList")[0];
							
							$('#importfromservice-layerlist').empty();
							for (var i=0; i<self.featureTypeList.children.length; i++) {
								var htmlLayer = '';
								htmlLayer += '<li class="item">';
								htmlLayer += 	'<div class="product-info">';
								htmlLayer += 		'<a data-layername="' + self.featureTypeList.children[i].children[0].textContent + '" href="" class="product-title load-wfs-layer">' + self.featureTypeList.children[i].children[0].textContent + '<span style="font-size: 100%; font-weight: 500; padding: .5em .5em .5em;" class="btn btn-default pull-right"><i class="fa fa-globe margin-r-5"></i>' + gettext('Load layer') + '</span></a>'; 
								htmlLayer += 		'<span class="product-description">' + self.featureTypeList.children[i].children[1].textContent + '</span>';
								htmlLayer += 	'</div>';
								htmlLayer += '</li>';
								
								$('#importfromservice-layerlist').append(htmlLayer);
							}
							
							$('.load-wfs-layer').on('click', function(e){
								e.preventDefault();
								var layerName = this.dataset.layername;
								for (var i=0; i<self.featureTypeList.children.length; i++) {
									if (self.featureTypeList.children[i].children[0].textContent == layerName) {
										self.loadWFSLayer(serviceURL, self.featureTypeList.children[i]);
									}
								}
							});
							
						} 
					}).fail(function(xhr, status, error) {
						$('#importfromservice-layerlist').empty();
						$('#serviceurl-error').css('display', 'block');
					});
					
				} else {
					$('#mixedcontent-error').css('display', 'block');
				}
				
			}
			
		});

		$('#button-importfromservice-cancel').unbind("click").click(function(){
			$("#modal-importfromservice-dialog").modal('hide');
			self.modal = null;
		});
		
	} else {
		$("#modal-importfromservice-dialog").modal('hide');
		self.modal = null;
	}
};

ImportFromService.prototype.loadWMSLayer = function(url, layer) {
	var self = this;
	var layerId = viewer.core._nextLayerId();
	
	var wmsParams = {
		'LAYERS': layer.Name,
		'FORMAT': 'image/png',
		'VERSION': '1.1.1'
	};
	var wmsSource = new ol.source.TileWMS({
		url: url,
		visible: true,
		params: wmsParams,
		serverType: 'geoserver'
	});
	wmsLayer = new ol.layer.Tile({
		id: layerId,
		source: wmsSource,
		visible: true
	});
	wmsLayer.on('change:visible', function(){
		viewer.core.getLegend().reloadLegend();
	});
	wmsLayer.baselayer = false;
	wmsLayer.layer_name = layer.Name;
	wmsLayer.wms_url = url.split('?')[0];
	wmsLayer.id = layerId;
	wmsLayer.title = layer.Title;
	wmsLayer.queryable = false;
	wmsLayer.visible = true;
	wmsLayer.is_vector = false;
	wmsLayer.setZIndex(99999999);
	wmsLayer.external = false;
	wmsLayer.imported = true;
	wmsLayer.legend = wmsLayer.wms_url + '?SERVICE=WMS&VERSION=1.1.1&layer=' + layer.Name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on';
	wmsLayer.legend_no_auth = wmsLayer.wms_url + '?SERVICE=WMS&VERSION=1.1.1&layer=' + layer.Name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on';
	
	this.map.addLayer(wmsLayer);
	this.createLayerUI(wmsLayer, layerId);
	viewer.core.getLegend().reloadLegend();
	
	$("#modal-importfromservice-dialog").modal('hide');
	self.modal = null;
	
};

ImportFromService.prototype.loadWFSLayer = function(url, layer) {
	var self = this;
	var layerId = viewer.core._nextLayerId();
	var layerName = layer.children[0].textContent;
	var layerTitle = layer.children[1].textContent;

	var style = self.getRandomStyle();
	
	var wfsLayer = new ol.layer.Vector({
		id: layerId,
		name: layerName,
		style: style,
		strategy: ol.loadingstrategy.bbox,
		source: new ol.source.Vector({
			format: new ol.format.GeoJSON(),
		    url: function(extent) {
		    	return  url + '?' +
		        		'service=WFS&' +
		        		'version=1.0.0&request=GetFeature&typename=' + layerName + '&'+
		        		'outputFormat=application/json&srsname=EPSG:3857';/* +
		        		'bbox=' + extent.join(',') + ',EPSG:3857';*/
		    }
		})
	});
	
	wfsLayer.baselayer = false;
	wfsLayer.setZIndex(99999999);
	wfsLayer.dataid = layerId;
	wfsLayer.id = layerId;
	wfsLayer.layer_name = layerName;
	wfsLayer.queryable = false;
	wfsLayer.title = layerTitle;
	wfsLayer.visible = true;
	wfsLayer.imported = true;
	wfsLayer.is_vector = true;

	self.map.addLayer(wfsLayer);
	self.createLayerUI (wfsLayer, layerId);
	$("#modal-importfromservice-dialog").modal('hide');
	self.modal = null;
};

ImportFromService.prototype.getRandomStyle = function() {
	
	var getColor = function () { return Math.floor(Math.random()*256) };	
	var r = getColor();
	var g = getColor();
	var b = getColor();
    var rgbColor = "rgb(" + r + "," + g + "," + b + ")";
    var rgbColorOpacity = "rgba(" + r + "," + g + "," + b + ", 0.3)";
	
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

ImportFromService.prototype.createLayerGroup = function() {
	var self = this;
	var groupId = 'gvsigol-importfromservice-group';

	var group = '';
	group += '			<li class="box box-default collapsed-box" id="' + groupId + '">';
	group += '				<div class="box-header with-border">';
	group += '					<i style="cursor: pointer;" class="layertree-folder-icon fa fa-folder-o"></i>';
	group += '					<span class="text">' + gettext("Imported layers") + '</span>';
	group += '					<div class="box-tools pull-right">';
	group += '						<button class="btn btn-box-tool btn-box-tool-custom group-collapsed-button" data-widget="collapse">';
	group += '							<i class="fa fa-plus"></i>';
	group += '						</button>';
	group += '					</div>';
	group += '				</div>';
	group += '				<div data-groupnumber="' + (102 * 100) + '" class="box-body layer-tree-groups importfromservice-layer-group" style="display: none;">';
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


ImportFromService.prototype.reorder = function(event,ui) {
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

ImportFromService.prototype.createLayerUI = function(layer, dataId) {
	var self = this;
	
	var groupId = "gvsigol-importfromservice-group";
	var groupEntry = $("#"+groupId);
	var zIndex = groupEntry.length;
	if(zIndex == 0){
		self.createLayerGroup();
	}

	var layerTree = viewer.core.getLayerTree();
	
	var removeLayerButtonUI = '<a id="remove-service-layer-' + dataId + '" data-layerid="' + dataId + '" class="btn btn-block btn-social btn-custom-tool remove-service-layer-btn">';
	removeLayerButtonUI +=    '	<i class="fa fa-times"></i> ' + gettext('Remove layer');
	removeLayerButtonUI +=    '</a>';
	
	var layerUI = $(layerTree.createOverlayUI(layer, false));
	layerUI.find(".box-body .zoom-to-layer").after(removeLayerButtonUI);
	$(".importfromservice-layer-group").append(layerUI);
	layerTree.setLayerEvents();

	$(".remove-service-layer-btn").unbind("click").click(function (e) {
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
ImportFromService.prototype.deactivate = function() {
};