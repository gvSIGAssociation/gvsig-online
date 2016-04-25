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
var layerTree = function(conf, map) {
	this.map = map;	
	this.conf = conf;
	this.editionBar = null;
	this.$container = $('#layer-tree-tab');
	this.createTree();
	$(".layer-tree").sortable({
		placeholder: "sort-highlight",
		handle: ".handle",
		forcePlaceholderSize: true,
		zIndex: 999999
	});
};

/**
 * TODO.
 */
layerTree.prototype.createTree = function() {
	
	var self = this;
	this.layerCount = 0;
	
	var tree = '';
	tree += '<div class="box box-primary">';
	tree += '	<div class="box-body">';
	tree += '		<ul class="layer-tree">';
	tree += '			<li class="box box-default">';
	tree += '				<div class="box-header with-border">';
	tree += '					<span class="text">' + gettext('Base layers') + '</span>';
	tree += '					<div class="box-tools pull-right">';
	tree += '						<button class="btn btn-box-tool btn-box-tool-custom" data-widget="collapse">';
	tree += '							<i class="fa fa-minus"></i>';
	tree += '						</button>';
	tree += '					</div>';
	tree += '				</div>';
	tree += '				<div class="box-body" style="display: block; font-size: 12px;">';
	tree += 					self.createBaseLayerUI(gettext('Ninguna'), false);
	tree += 					self.createBaseLayerUI('OpenStreetMap', true);
	tree += '				</div>';
	tree += '			</li>';
	if (this.conf.layerGroups) {
		for (var i=0; i<this.conf.layerGroups.length; i++) {
			var layerGroup = this.conf.layerGroups[i];
			tree += '			<li class="box box-default collapsed-box" id="' + layerGroup.groupId + '">';
			tree += '				<div class="box-header with-border">';
			tree += '					<span class="handle"> ';
			tree += '						<i class="fa fa-ellipsis-v"></i>';
			tree += '						<i class="fa fa-ellipsis-v"></i>';
			tree += '					</span>';
			tree += '					<input type="checkbox" class="layer-group" id="layergroup-' + layerGroup.groupId + '">';
			tree += '					<span class="text">' + layerGroup.groupTitle + '</span>';
			tree += '					<div class="box-tools pull-right">';
			tree += '						<button class="btn btn-box-tool btn-box-tool-custom" data-widget="collapse">';
			tree += '							<i class="fa fa-plus"></i>';
			tree += '						</button>';
			tree += '					</div>';
			tree += '				</div>';
			tree += '				<div class="box-body" style="display: none;">';
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
					} else {
						mapLayer.setVisible(false);
						layerCheckbox.checked = false;
						layerCheckbox.disabled = false;
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
	
	$(".show-attribute-table-link").on('click', function(e) {
	});
	
	
	$(".start-edition-link").on('click', function(e) {
	});
	
	$(".show-metadata-link").on('click', function(e) {
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
			if (layer.getSource().params_) {
				if (layer.getSource().getParams().LAYERS.indexOf(tocLayer.name) > -1) {
					mapLayer = layer;
				}
				
			} else {
				if (tocLayer.name == layer.layer_name) {
					mapLayer = layer;
				}
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
			if (layer.getSource().params_) {
				if (layer.getSource().getParams().LAYERS.indexOf(tocLayer.name) > -1) {
					mapLayer = layer;
				}
				
			} else {
				if (tocLayer.name == layer.layer_name) {
					mapLayer = layer;
				}
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
	ui += '<div class="box layer-box thin-border box-default collapsed-box">';
	ui += '		<div class="box-header with-border">';
	if (layer.visible) {
		ui += '		<input type="checkbox" id="' + id + '" checked>';
	} else {
		ui += '		<input type="checkbox" id="' + id + '">';
	}
	ui += '			<span class="text">' + layer.title + '</span>';
	ui += '			<div class="box-tools pull-right">';
	ui += '				<button class="btn btn-box-tool btn-box-tool-custom">';
	ui += '					<i class="fa fa-angle-up"></i>';
	ui += '				</button>';
	ui += '				<button class="btn btn-box-tool btn-box-tool-custom">';
	ui += '					<i class="fa fa-angle-down"></i>';
	ui += '				</button>';
	ui += '				<button class="btn btn-box-tool btn-box-tool-custom" data-widget="collapse">';
	ui += '					<i class="fa fa-plus"></i>';
	ui += '				</button>';
	ui += '			</div>';
	ui += '		</div>';
	ui += '		<div class="box-body" style="display: none;">';
	ui += '			<a id="show-metadata-' + id + '" class="btn btn-block btn-social btn-custom-tool show-metadata-link">';
	ui += '				<i class="fa fa-external-link"></i> ' + gettext('Layer metadata');
	ui += '			</a>';
	if (layer.queryable && layer.is_vector) {	    
	    ui += '	<a id="show-attribute-table-' + id + '" data-id="' + id + '" href="#" class="btn btn-block btn-social btn-custom-tool show-attribute-table-link">';
		ui += '		<i class="fa fa-table"></i> ' + gettext('Attribute table');
		ui += '	</a>';
    }	
	if (mapLayer.is_vector) {
    	if (mapLayer.write_roles.length >= 1) {
    		if (this.userCanWrite(mapLayer)) {
    			ui += '	<a id="start-edition-' + id + '" href="#" class="btn btn-block btn-social btn-custom-tool start-edition-link">';
    			ui += '		<i class="fa fa-edit"></i> ' + gettext('Edit layer');
    			ui += '	</a>';
    		}
    	}
    }
	ui += '		</div>';
	ui += '</div>';
	
	
	
	return ui;
};

/**
 * TODO
 */
layerTree.prototype.userCanWrite = function(layer) {
	var canWrite = false;
	for (var i=0; i<layer.write_roles.length; i++) {
		for (var k=0; k<this.conf.user.permissions.roles.length; k++) {
			if (layer.write_roles[i] == this.conf.user.permissions.roles[k]) {
				canWrite = true;
			}
		}
	}
	return canWrite;
};


/**
 * TODO
 */
layerTree.prototype.getEditionBar = function(layer) {
	return this.editionBar;
};