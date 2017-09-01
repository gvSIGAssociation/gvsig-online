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
var layerTree = function(conf, map, isPublic) {
	this.map = map;	
	this.conf = conf;
	this.editionBar = null;
	this.$container = $('#layer-tree-tab');
	this.createTree();
	$(".layer-tree-groups").sortable({
		placeholder: "sort-highlight",
		handle: ".handle",
		forcePlaceholderSize: true,
		zIndex: 999999
	});
	var self = this;
	$(".layer-tree-groups").on("sortupdate", function(event, ui){
		self.reorder(event, ui);
	});
};

/**
 * TODO.
 */
layerTree.prototype.createTree = function() {
	
	var self = this;
	this.layerCount = 0;
	var groupCount = 1;
	
	var tree = '';
	tree += '<div class="box">';
	tree += '	<div class="box-body">';
	tree += '		<ul class="layer-tree">';
	tree += '			<li class="box box-default"; id="base-layers">';
	tree += '				<div class="box-header with-border">';
	tree += '					<span class="text">' + gettext('Base layers') + '</span>';
	tree += '					<div class="box-tools pull-right">';
	tree += '						<button class="btn btn-box-tool btn-box-tool-custom" data-widget="collapse">';
	tree += '							<i class="fa fa-minus"></i>';
	tree += '						</button>';
	tree += '					</div>';
	tree += '				</div>';
	tree += '				<div id="baselayers-group" class="box-body" style="display: block; font-size: 12px;">';
	tree += 					self.createBaseLayerUI(gettext('None'), false);
	for (var i=0; i<this.conf.base_layers.length; i++) {
		var base_layer = this.conf.base_layers[i];
		tree += 				self.createBaseLayerUI(gettext(base_layer['title']), base_layer['active']);
	}
	
	tree += '				</div>';
	tree += '			</li>';
	if (this.conf.layerGroups) {
		for (var i=0; i<this.conf.layerGroups.length; i++) {
			var layerGroup = this.conf.layerGroups[i];
			tree += '			<li class="box box-default collapsed-box" id="' + layerGroup.groupId + '">';
			tree += '				<div class="box-header with-border">';
			tree += '					<input type="checkbox" class="layer-group" id="layergroup-' + layerGroup.groupId + '">';
			tree += '					<span class="text">' + layerGroup.groupTitle + '</span>';
			tree += '					<div class="box-tools pull-right">';
			tree += '						<button class="btn btn-box-tool btn-box-tool-custom" data-widget="collapse">';
			tree += '							<i class="fa fa-plus"></i>';
			tree += '						</button>';
			tree += '					</div>';
			tree += '				</div>';
			tree += '				<div data-groupnumber="' + (groupCount++) * 100 + '" class="box-body layer-tree-groups" style="display: none;">';
			for (var j=0; j<layerGroup.layers.length; j++) {	
				var layer = layerGroup.layers[j];				
				tree += self.createOverlayUI(layer);
			}
			tree += '				</div>';
			tree += '			</li>';
		}
	}
	tree += '		</ul>';
	tree += '	</div>';
	tree += '</div>';
	
	this.$container.append(tree);
	
	$( ".layer-opacity-slider" ).slider({
	    min: 0,
	    max: 100,
	    value: 100,
	    slide: function( event, ui ) {
	    	var layers = self.map.getLayers();
			var id = this.dataset.layerid;
			layers.forEach(function(layer){
				if (layer.baselayer == false) {
					if (id===layer.get("id")) {
						layer.setOpacity(parseFloat(ui.value)/100);
						$("#layer-opacity-output-" + id).text(ui.value + '%');
					}
				}						
			}, this);
	    }
	});

	$("input[name=baselayers-group]:radio").change(function (e) {
		var baseLayers = self.map.getLayers();
		baseLayers.forEach(function(layer){
			if (layer.baselayer) {
				if (layer.getVisible() == true) {
					layer.setVisible(false);
				}
				if (layer.get('id') == this.id) {
					layer.setVisible(true);
				}
			}						
		}, this);
	});
	
	$("input[type=checkbox]").change(function (e) {
		var layers = self.map.getLayers();
		layers.forEach(function(layer){
			if (!layer.baselayer) {
				if (layer.get("id") === this.id) {
					if (layer.getVisible() == true) {
						layer.setVisible(false);
					} else {
						layer.setVisible(true);
					}
				}
			};
		}, this);
	});
	
	$(".layer-group").change(function (e) {
		var groupId = this.id.split('-')[1]; 
		var checked = this.checked;
		for (var i=0; i<self.conf.layerGroups.length; i++) {			
			var group = self.conf.layerGroups[i];
			if (group.groupId == groupId) {
				var mapLayer = self.getGroupLayerFromMap(group.groupName);
				if (checked) {
					mapLayer.setVisible(true);
				} else {
					mapLayer.setVisible(false);
				}
				for (var j=0; j<group.layers.length; j++) {
					var layer = group.layers[j];
					var layerCheckbox = document.getElementById(layer.id);
					var mapLayer = self.getLayerFromMap(layer);
					if (checked) {
						mapLayer.setVisible(false);
						layerCheckbox.checked = true;
						layerCheckbox.disabled = true;
						
						$(".layer-opacity-slider[data-layerid='"+layer.id+"']").slider( "option", "disabled", true );
					} else {
						mapLayer.setVisible(false);
						layerCheckbox.checked = false;
						layerCheckbox.disabled = false;
						
						$(".layer-opacity-slider[data-layerid='"+layer.id+"']").slider( "option", "disabled", false );
					}
				}
			}			
		}
	});
	
	$(".opacity-range").on('change', function(e) {
		var layers = self.map.getLayers();
		var id = this.id.split("opacity-range-")[1];
		layers.forEach(function(layer){
			if (layer.baselayer == false) {
				if (id===layer.get("id")) {
					layer.setOpacity(this.valueAsNumber/100);
				}
			}						
		}, this);
	});
	
	$(".zoom-to-layer").on('click', function(e) {
		var layers = self.map.getLayers();
		var selectedLayer = null;
		var id = this.id.split("zoom-to-layer-")[1];
		layers.forEach(function(layer){
			if (layer.baselayer == false) {
				if (id===layer.get("id")) {
					selectedLayer = layer;
				}
			}						
		}, this);
		self.zoomToLayer(selectedLayer);
	});
};


/**
 * TODO
 */
layerTree.prototype.getLayerFromMap = function(tocLayer) {
	var layers = this.map.getLayers();
	var mapLayer = null;
	layers.forEach(function(layer){
		if (layer.baselayer == false) {
			if (layer.get('id')==tocLayer.id) {
				mapLayer = layer;
			}
			
		}
	}, this);
	return mapLayer;
};

/**
 * TODO
 */
layerTree.prototype.getGroupLayerFromMap = function(tocLayer) {
	var layers = this.map.getLayers();
	var mapLayer = null;
	layers.forEach(function(layer){
		if (layer.baselayer == false) {
			if (layer.get('id')==tocLayer) {
				mapLayer = layer;
			}
		}
	}, this);
	return mapLayer;
};

layerTree.prototype.createBaseLayerUI = function(name, checked) {
	var count = this.layerCount++;
	var id = "gol-layer-" + count;		    
    
	var ui = '';
	ui += '<div style="margin-left:20px;">';
	if (checked) {
		ui += 	'<input type="radio" id="' + id + '" name="baselayers-group" checked>';
	} else {
		ui += 	'<input type="radio" id="' + id + '" name="baselayers-group">';
	}
	ui += 		'<span class="text">' + name + '</span>';
	ui += '</div>';
	
	return ui;
};


layerTree.prototype.createOverlayUI = function(layer) {
	
	var mapLayer = this.getLayerFromMap(layer);
	var id = layer.id;
	
	var ui = '';
	ui += '<div data-layerid="' + id + '" data-zindex="' + mapLayer.getZIndex() + '" class="box layer-box thin-border box-default collapsed-box">';
	ui += '		<div class="box-header with-border">';
	ui += '			<span class="handle"> ';
	ui += '				<i class="fa fa-ellipsis-v"></i>';
	ui += '				<i class="fa fa-ellipsis-v"></i>';
	ui += '			</span>';
	if (layer.visible) {
		ui += '		<input type="checkbox" id="' + id + '" checked>';
	} else {
		ui += '		<input type="checkbox" id="' + id + '">';
	}
	ui += '			<span class="text">' + layer.title + '</span>';
	ui += '			<div class="box-tools pull-right">';
	ui += '				<button class="btn btn-box-tool btn-box-tool-custom" data-widget="collapse">';
	ui += '					<i class="fa fa-plus"></i>';
	ui += '				</button>';
	ui += '			</div>';
	ui += '		</div>';
	ui += '		<div class="box-body" style="display: none;">';
	ui += '			<a id="zoom-to-layer-' + id + '" href="#" class="btn btn-block btn-social btn-custom-tool zoom-to-layer">';
	ui += '				<i class="fa fa-search" aria-hidden="true"></i> ' + gettext('Zoom to layer');
	ui += '			</a>';
	ui += '			<label style="display: block; margin-top: 8px; width: 95%;">' + gettext('Opacity') + '<span id="layer-opacity-output-' + layer.id + '" class="margin-l-15 gol-slider-output">%</span></label>';
	ui += '			<div id="layer-opacity-slider" data-layerid="' + layer.id + '" class="layer-opacity-slider"></div>';
	ui += '		</div>';
	ui += '</div>';
	
	
	
	return ui;
};

layerTree.prototype.zoomToLayer = function(layer) {
	var self = this;
	var layer_name = layer.layer_name;

	var url = layer.wms_url+'?request=GetCapabilities&service=WMS';
	var parser = new ol.format.WMSCapabilities();
	$.ajax(url).then(function(response) {
		   var result = parser.read(response);
		   var Layers = result.Capability.Layer.Layer; 
		   var extent;
		   for (var i=0, len = Layers.length; i<len; i++) {
		     var layerobj = Layers[i];
		     if (layerobj.Name == layer_name) {
		         extent = layerobj.EX_GeographicBoundingBox;
		         break;
		     }
		   }
		   if((extent[0]==0 && extent[1]==0 && extent[2]==-1 && extent[3]==-1 )||
			   (extent[0]==-1 && extent[1]==-1 && extent[2]==0 && extent[3]==0 )){
			   return;
		   }
		   var ext = ol.proj.transformExtent(extent, ol.proj.get('EPSG:4326'), ol.proj.get('EPSG:3857'));
		   self.map.getView().fit(ext, self.map.getSize());
		});
}


/**
 * TODO
 */
layerTree.prototype.getEditionBar = function(layer) {
	return this.editionBar;
};

/**
 * TODO
 */
layerTree.prototype.setEditionBar = function(editionbar) {
	this.editionBar = editionbar;
};


/**
 * TODO
 */
layerTree.prototype.reorder = function(event,ui) {
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
