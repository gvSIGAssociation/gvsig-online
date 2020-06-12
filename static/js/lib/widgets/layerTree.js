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
var layerTree = function(conf, map, viewer, isPublic) {
	this.map = map;	
	this.conf = conf;
	this.viewer = viewer;
	this.editionBar = null;
	this.is_first_time = true;
	this.baseLayerIndex = 1;
	this.$container = $('#layer-tree-tab');
	this.$temporary_container = $('#temporary-tab');
	this.createTree();
	
	this.step_val_array = [];
	this.step_val = 1;
	this.min_val = 0;
	this.max_val = 1;
	this.mosaic_values = {};
	this.state = {
		base_layers: this.conf.base_layers,
		layerGroups: this.conf.layerGroups
	};
	
};

/**
 * TODO.
 */
layerTree.prototype.refreshSlider = function() {
	var slider = $("#temporary-layers-slider");
	var input = $("input[name=temporary-group]:checked");
	if(input.attr("data-value") == "single"){
		slider.slider('option', 'slide').call(slider, slider, {value: slider.slider('option','value')});
	}
	if(input.attr("data-value") == "range"){
		var slider_values = [slider.slider('option','values')[0], slider.slider('option','values')[1]];
		slider.slider('option', 'slide').call(slider, slider, {values: slider_values});
	}
};

layerTree.prototype.createTree = function() {
	
	var self = this;
	this.layerCount = 0;
	var groupCount = 1;
	
	var baseGroup = null;
	if (this.conf.layerGroups) {
		for (var i=0; i<this.conf.layerGroups.length; i++) {
			if (this.conf.layerGroups[i].basegroup) {
				baseGroup = this.conf.layerGroups[i];
			}
		}
	}
	
	var tree = '';
	tree += '<div class="box">';
	tree += '	<div class="box-body">';
	tree += '		<ul class="layer-tree">';
	if (baseGroup != null) {
		tree += '			<li class="box box-default"; id="base-layers">';
		tree += '				<div class="box-header with-border">';
		tree += '					<span class="text">' + baseGroup.groupTitle + '</span>';
		tree += '					<div class="box-tools pull-right">';
		tree += '						<button class="btn btn-box-tool btn-box-tool-custom" data-widget="collapse">';
		tree += '							<i class="fa fa-minus"></i>';
		tree += '						</button>';
		tree += '					</div>';
		tree += '				</div>';
		tree += '				<div id="baselayers-group" class="box-body" style="display: block; font-size: 12px;">';
		for (var j=0; j<baseGroup.layers.length; j++) {	
			var layer = baseGroup.layers[j];				
			tree += 				self.createBaseLayerUI(layer);
		}
		tree += 					self.createEmptyBaseLayerUI();
		tree += '				</div>';
		tree += '			</li>';
	}
	if (this.conf.layerGroups) {
		for (var i=0; i<this.conf.layerGroups.length; i++) {
			var layerGroup = this.conf.layerGroups[i];
			if (!layerGroup.basegroup) {
				tree += '			<li class="box box-default collapsed-box" id="' + layerGroup.groupId + '">';
				tree += '				<div class="box-header with-border">';
				if (this.conf.selectable_groups) {
					if (layerGroup.visible) {
						tree += '					<input type="checkbox" class="layer-group" id="layergroup-' + layerGroup.groupId + '" checked>';
					} else {
						tree += '					<input type="checkbox" class="layer-group" id="layergroup-' + layerGroup.groupId + '">';
					}
				}
				tree += '					<i style="cursor: pointer;" class="layertree-folder-icon fa fa-folder-o"></i>';
				tree += '					<span class="text">' + layerGroup.groupTitle + '</span>';
				tree += '					<div class="box-tools pull-right">';
				tree += '						<button class="btn btn-box-tool btn-box-tool-custom group-collapsed-button" data-widget="collapse">';
				tree += '							<i class="fa fa-plus"></i>';
				tree += '						</button>';
				tree += '					</div>';
				tree += '				</div>';
				tree += '				<div data-grouporder="' + layerGroup.groupOrder + '" data-groupnumber="' + (groupCount++) * 100 + '" class="box-body layer-tree-groups" style="display: none;">';
				for (var j=0; j<layerGroup.layers.length; j++) {	
					var layer = layerGroup.layers[j];				
					tree += self.createOverlayUI(layer, layerGroup.visible);
				}
				tree += '				</div>';
				tree += '			</li>';
			}
		}
	}
	tree += '		</ul>';
	tree += '	</div>';
	tree += '</div>';
	
	this.$container.append(tree);
	
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
	
	$(".layer-group").unbind("change").change(function (e) {
		var groupId = this.id.split('-')[1]; 
		var checked = this.checked;
		for (var i=0; i<self.conf.layerGroups.length; i++) {			
			var group = self.conf.layerGroups[i];
			if (group.groupId == groupId) {
				if (group.allows_getmap) {
					var mapLayer = self.getGroupLayerFromMap(group.groupName);
					if (mapLayer) {
						if (checked) {
							mapLayer.setVisible(true);
							self.changeState(group, 'layergroup', 'set-visibility', true);
						} else {
							mapLayer.setVisible(false);
							self.changeState(group, 'layergroup', 'set-visibility', false);
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
					
				} else {
					if (checked) {
						self.changeState(group, 'layergroup', 'set-visibility', true);
					} else {
						self.changeState(group, 'layergroup', 'set-visibility', false);
					}
					for (var j=0; j<group.layers.length; j++) {
						var layer = group.layers[j];
						var layerCheckbox = document.getElementById(layer.id);
						var mapLayer = self.getLayerFromMap(layer);
						if (checked) {
							mapLayer.setVisible(true);
							layerCheckbox.checked = true;
							
						} else {
							mapLayer.setVisible(false);
							layerCheckbox.checked = false;
						}
					}
				}
				
				
			}			
		}
	});
	
	this.setLayerEvents();
	this.createTemporaryTab();

};

layerTree.prototype.setLayerEvents = function() {
	var self = this;
	$( ".layer-opacity-slider" ).slider({
	    min: 0,
	    max: 100,
	    //value: 100,
	    create: function( event, ui ) {
	    	var layers = self.map.getLayers();
			var id = this.dataset.layerid;
			layers.forEach(function(layer){
				if (layer.baselayer == false) {
					if (id===layer.get("id")) {
						$(this).slider( "value", layer.getOpacity() * 100);
						$("#layer-opacity-output-" + id).text((layer.getOpacity() * 100).toString() + '%');
					}
				}						
			}, this);
	    },
	    slide: function( event, ui ) {
	    	var layers = self.map.getLayers();
			var id = this.dataset.layerid;
			layers.forEach(function(layer){
				if (layer.baselayer == false) {
					if (id===layer.get("id")) {
						var opacity = parseFloat(ui.value)/100;
						layer.setOpacity(opacity);
						$("#layer-opacity-output-" + id).text(ui.value + '%');
						self.changeState(layer, 'layer', 'change-opacity', opacity);
					}
				}						
			}, this);
	    }
	});

	$( ".layer-swipe-slider" ).slider({
	    min: 0,
	    max: 100,
	    range: true,
	    values: [0,100],
	    slide: function( event, ui ) {
	    	var layers = self.map.getLayers();
			var id = this.dataset.layerid;
			layers.forEach(function(layer){
				if (layer.baselayer == false) {
					if (id===layer.get("id")) {
						$("#layer-swipe-output-" + id).text(ui.values[0] + '% - ' + ui.values[1] + '%');
						layer["swipe-min"] = ui.values[0];
						layer["swipe-max"] = ui.values[1];

						self.map.render();
					}
				}
			}, this);
	    }
	});

	$("input[name=baselayers-group]:radio").unbind("change").change(function (e) {
		var baseLayers = self.map.getLayers();
		baseLayers.forEach(function(layer){
			if (layer.baselayer) {
				if (layer.getVisible() == true) {
					layer.setVisible(false);
					self.changeState(layer, 'layer', 'change-baselayer', false);
				}
				if (layer.get('id') == this.id) {
					layer.setVisible(true);
					self.changeState(layer, 'layer', 'change-baselayer', true);
				}
			}						
		}, this);
	});
	
	$(".layer-box input[type=checkbox]").unbind("change").change(function (e) {
		var layers = self.map.getLayers();
		layers.forEach(function(layer){
			if (!layer.baselayer) {
				if (layer.get("id") === this.id) {
					if (layer.getVisible() == true) {
						layer.setVisible(false);
						self.changeState(layer, 'layer', 'set-visibility', false);
						if($("#layer-"+layer.get("id")).length){
							$("#layer-"+layer.get("id")).css("display", "none");
							if(self.hasTemporaryLayersActive()){
								self.refreshTemporalInfo();	
								self.updateTemporalLayers();
							}else{
								$("#enable-temporary").prop('checked', false);
								self.showHideTemporalPanel();
							}
						}
					} else {
						layer.setVisible(true);
						self.changeState(layer, 'layer', 'set-visibility', true);
						if($("#layer-"+layer.get("id")).length){
							$("#layer-"+layer.get("id")).css("display", "block");
							self.refreshTemporalInfo();	
							self.updateTemporalLayers();
						}
					}
				}
			};
		}, this);
	});

	$(".opacity-range").unbind("change").on('change', function(e) {
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
	
	$(".show-attribute-table-link").unbind("click").on('click', function(e) {
		var selectedLayer = null;
		var layers = self.map.getLayers();
		layers.forEach(function(layer){
			if (layer.baselayer == false) {
				if (this.dataset.id == layer.get('id')) {
					selectedLayer = layer;
				}
			}						
		}, this);
		var dataTable = new attributeTable(selectedLayer, self.map, self.conf, self.viewer);
		dataTable.show();
		dataTable.registerEvents();
	});
	
	$(".show-metadata-link").unbind("click").on('click', function(e) {
		var layers = self.map.getLayers();
		var selectedLayer = null;
		var id = this.id.split("show-metadata-")[1];
		layers.forEach(function(layer){
			if (layer.baselayer == false) {
				if (id===layer.get("id")) {
					selectedLayer = layer;
				}
			}						
		}, this);
		self.showMetadata(selectedLayer);
	});
	
	$(".detailed-info-link").unbind("click").on('click', function(e) {
		var layers = self.map.getLayers();
		var selectedLayer = null;
		var id = this.id.split("detailed-info-")[1];
		layers.forEach(function(layer){
			if (layer.baselayer == false) {
				if (id===layer.get("id")) {
					selectedLayer = layer;
				}
			}						
		}, this);
		self.detailedInfo(selectedLayer);
	});
	
	$(".layer-downloads-link").unbind("click").on('click', function(e) {
		var layers = self.map.getLayers();
		var selectedLayer = null;
		var id = this.id.split("layer-downloads-")[1];
		layers.forEach(function(layer){
			if (layer.baselayer == false) {
				if (id===layer.get("id")) {
					selectedLayer = layer;
				}
			}
		}, this);
		self.layerDownloads(selectedLayer);
	});
	
	$(".zoom-to-layer").unbind("click").on('click', function(e) {
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
	
	
	$(".symbol-to-layer").unbind("change").on('change', function(e) {
		var layers = self.map.getLayers();
		var comp_id = $(this).attr("id");
		var selectedLayer = null;
		var style = null;
		var id = this.id.split("symbol-to-layer-")[1];
		layers.forEach(function(layer){
			if (layer.baselayer == false) {
				if (id===layer.get("id")) {
					selectedLayer = layer;
					style = $( "#"+comp_id+" option:selected" ).val();
				}
			}						
		}, this);
		if(selectedLayer != null){
			self.assignStyleToLayer(selectedLayer, style);
		}
	});
	
	$(".layer-tree-groups").sortable({
		placeholder: "sort-highlight",
		handle: ".handle",
		forcePlaceholderSize: true,
		zIndex: 999999
	});
	$(".layer-tree-groups").on("sortupdate", function(event, ui){
		self.reorder(event, ui);
	});
}


layerTree.prototype.createTemporaryTab = function() {
	var self = this;
	var temporary_tree = '';
	temporary_tree += '<div style="background-color:#f9fafc">';
	temporary_tree += '<input type="checkbox" id="enable-temporary" class="temporary-check">'+ gettext("Enable temporary features")+'</input> <div id="temporary-panel">';
	temporary_tree += '	<div id="enable-temporary-error"><i class="fa fa-exclamation-triangle" aria-hidden="true"></i>&nbsp;&nbsp;&nbsp;&nbsp;' + gettext("A visible layer with temporal properties is needed") + '</div>';
	temporary_tree += '	<div class="box-body temporary-body">';
	
	var input_from = '<div class="col-md-1" style="padding: 0px 7px;">';
	if(this.conf.temporal_advanced_parameters){
		input_from += '<input type="radio" id="from-date-value" class="temporal-type-radio" name="from-date-value" checked>';
	}
	input_from += '</div><div class="input-group date col-md-9" id="datetimepicker-from">'+
		'<input id="temporary-from" class="form-control from-date-value"/>'+
		'<span class="input-group-addon from-date-value">'+
			'<span class="glyphicon glyphicon-calendar from-date-value"></span>'+
		'</span>'+
		'<span class="input-group-addon temporal-buttons-empty-gap"></span>'+
		'<span class="temporal-buttons temporal-buttons-left temporal-buttons-left-from from-date-value">'+
			'<i class="fa fa-minus" aria-hidden="true"></i>'+
		'</span>'+
		'<span class="temporal-buttons temporal-buttons-right temporal-buttons-right-from from-date-value">'+
			'<i class="fa fa-plus" aria-hidden="true"></i>'+
		'</span>'+
	'</div>';
	
	if(this.conf.temporal_advanced_parameters){
		input_from += '<div class="col-md-2" style="margin-top:5px"></div>'+
		'<div class="col-md-1" style="padding: 0px 7px;margin-top:5px">'+
			'<input type="radio" id="from-custom-date-value" class="temporal-type-radio" name="from-date-value">'+
		'</div>'+
		'<div class="input-group date col-md-9" style="margin-top:5px">'+
			'<input id="from-custom-value" class="form-control" style="width:100%" value="PRESENT" disabled>'+
			'<span class="temporal-buttons temporal-buttons-disabled temporal-buttons-left from-custom-definition-button from-custom-date-value">'+
				'<i class="fa fa-edit" aria-hidden="true"></i>'+
			'</span>'+
		'</div>';
	}
	
	input_from += '<div class="col-md-3"></div>'+
	'<div id="from-custom-definition-panel" class="input-group date col-md-9" style="background-color:#eee; display:none;">'+
		'<span class="text input-group-date-label">' + gettext('year(s)') + '</span>'+
		'<input id="from-custom-value-year" class="form-control" style="width:50%" type="number" value="0"><br/>'+
		
		'<span class="text input-group-date-label">'+ gettext('month(s)') + '</span>'+
		'<input id="from-custom-value-month" class="form-control" style="width:50%" type="number" value="0"><br/>'+
		
		'<span class="text input-group-date-label">' + gettext('day(s)') + '</span>'+
		'<input id="from-custom-value-day" class="form-control" style="width:50%" type="number" value="0"><br/>'+
		
		'<span class="text input-group-date-label">' + gettext('hour(s)') + '</span>'+
		'<input id="from-custom-value-hour" class="form-control" style="width:50%" type="number" value="0"><br/>'+
		
		'<span class="text input-group-date-label">' + gettext('minute(s)') + '</span>'+
		'<input id="from-custom-value-minute" class="form-control" style="width:50%" type="number" value="0"><br/>'+
		
		'<span class="text input-group-date-label">' + gettext('second(s)') + '</span>'+
		'<input id="from-custom-value-second" class="form-control" style="width:50%" type="number" value="0"><br/>'+
	
		'<span class="temporal-buttons temporal-buttons-left from-input-group-date-apply-present date col-md-9" style="width: 50%;">'+
			gettext('Clear')+
		'</span>'+
		'<span class="temporal-buttons temporal-buttons-left from-input-group-date-apply date col-md-9" style="width: 50%;">'+
			gettext('apply relative date')+
		'</span>'+
	'</div>';
	
	
	var input_to = '<div class="col-md-1" style="padding: 0px 7px;">';
	if(this.conf.temporal_advanced_parameters){
		input_to += '<input type="radio" id="to-date-value" class="temporal-type-radio" name="to-date-value" checked>';
	}
	
	input_to += '</div><div class="input-group date col-md-9" id="datetimepicker-to"><input id="temporary-to" class="form-control to-date-value"/><span class="input-group-addon to-date-value"><span class="glyphicon glyphicon-calendar to-date-value"></span></span>'+
	'<span class="input-group-addon temporal-buttons-empty-gap"></span><span class="temporal-buttons temporal-buttons-left temporal-buttons-left-to to-date-value"><i class="fa fa-minus" aria-hidden="true"></i></span><span class="temporal-buttons temporal-buttons-right temporal-buttons-right-to to-date-value"><i class="fa fa-plus" aria-hidden="true"></i></span></div>';
	
	if(this.conf.temporal_advanced_parameters){
		input_to += '<div class="col-md-2" style="margin-top:5px"></div>'+
		'<div class="col-md-1" style="padding: 0px 7px;margin-top:5px">'+
			'<input type="radio" id="to-custom-date-value" class="temporal-type-radio" name="to-date-value">'+
		'</div>'+
		'<div class="input-group date col-md-9" style="margin-top:5px">'+
			'<input id="to-custom-value" class="form-control" style="width:100%" value="PRESENT" disabled>'+
			'<span class="temporal-buttons temporal-buttons-disabled temporal-buttons-left to-custom-definition-button to-custom-date-value">'+
				'<i class="fa fa-edit" aria-hidden="true"></i>'+
			'</span>'+
		'</div>';
	}
	
	input_to += '<div class="col-md-3"></div>'+
	'<div id="to-custom-definition-panel" class="input-group date col-md-9" style="background-color:#eee; display:none;">'+
		'<span class="text input-group-date-label">' + gettext('year(s)') + '</span>'+
		'<input id="to-custom-value-year" class="form-control" style="width:50%" type="number" value="0"><br/>'+
		
		'<span class="text input-group-date-label">'+ gettext('month(s)') + '</span>'+
		'<input id="to-custom-value-month" class="form-control" style="width:50%" type="number" value="0"><br/>'+
		
		'<span class="text input-group-date-label">' + gettext('day(s)') + '</span>'+
		'<input id="to-custom-value-day" class="form-control" style="width:50%" type="number" value="0"><br/>'+
		
		'<span class="text input-group-date-label">' + gettext('hour(s)') + '</span>'+
		'<input id="to-custom-value-hour" class="form-control" style="width:50%" type="number" value="0"><br/>'+
		
		'<span class="text input-group-date-label">' + gettext('minute(s)') + '</span>'+
		'<input id="to-custom-value-minute" class="form-control" style="width:50%" type="number" value="0"><br/>'+
		
		'<span class="text input-group-date-label">' + gettext('second(s)') + '</span>'+
		'<input id="to-custom-value-second" class="form-control" style="width:50%" type="number" value="0"><br/>'+
	
		'<span class="temporal-buttons temporal-buttons-left to-input-group-date-apply-present date col-md-9" style="width: 50%;">'+
			gettext('Clear')+
		'</span>'+
		'<span class="temporal-buttons temporal-buttons-left to-input-group-date-apply date col-md-9" style="width: 50%;">'+
			gettext('apply relative date')+
		'</span>'+
	'</div>';

//	temporary_tree += '			<label style="display: block; margin-top: 8px; width: 95%;">' + gettext('Temporary range') + '</label>';
	temporary_tree += '			<div id="from_label_div" class="temporary_field"><div class="col-md-2" style="padding:0px"><span class="text" style="font-weight:bold;margin-left:3px;">' + gettext('From') + '</span></div>'+input_from+'<div style="clear:both"></div></div>';
	temporary_tree += '			<div id="to_label_div" class="temporary_field"><div class="col-md-2" style="padding:0px"><span class="text" style="font-weight:bold;margin-left:3px;" >' + gettext('To') + '</span></div>'+input_to+'<div style="clear:both"></div></div>';
	temporary_tree += '			<div id="step_label_div"><span class="text" style="font-weight:bold;margin-left:3px;" >' + gettext('Step') + '</span><div class="pull-right">'+/*'<input id="temporary-step-value" type="number" class="ui-slider-step" min=1 value="1" disabled/>'+*/'<select id="temporary-step-unit"><option value="second">' + gettext('second(s)') + '</option><option value="minute">' + gettext('minute(s)') + '</option><option value="hour">' + gettext('hour(s)') + '</option><option value="day" selected>' + gettext('day(s)') + '</option><option value="month">' + gettext('month(s)') + '</option><option value="year">' + gettext('year(s)') + '</option></select></div><div style="clear:both"></div></div>';
	temporary_tree += '			<div id="temporary-layers-slider" class="temporary-layers-slider"></div>';
	
	
	temporary_tree += '<div style="margin-left:10px;">';
	temporary_tree += 	'<input type="radio" id="temporary-single" data-value="single" name="temporary-group" checked>';
	temporary_tree += 	'<span class="text" style="vertical-align: super;margin-left:10px">'+gettext('Single')+'</span>';
	temporary_tree += '</div>';
	
	temporary_tree += '<div style="margin-left:10px;">';
	temporary_tree += 	'<input type="radio" id="temporary-range" data-value="range" name="temporary-group">';
	temporary_tree += 	'<span class="text" style="vertical-align: super;margin-left:10px">'+gettext('Range')+'</span>';
	temporary_tree += '</div>';
	
	temporary_tree += '	</div>';
	temporary_tree += '</div>';
	temporary_tree += '<div class="box temporary-body" style="border-top:45px solid #e8ecf4;">';
	temporary_tree += ' <h4 class="temporary_text">' + gettext('Temporary layers') + '</h4>';
	temporary_tree += '	<div class="box-body">';
	temporary_tree += '		<ul class="layer-tree">';
	
	var has_temporary_layers_global = false;
	if (this.conf.layerGroups) {
		for (var i=0; i<this.conf.layerGroups.length; i++) {
			var has_temporary_layers = false;
			var layerGroup = this.conf.layerGroups[i];
			var temporary_tree_aux = '';
			for (var j=0; j<layerGroup.layers.length; j++) {	
				var layer = layerGroup.layers[j];				
				var temporary_tree_aux_layer = self.createTemporaryOverlayUI(layer);
				if(temporary_tree_aux_layer != ''){
					temporary_tree_aux += temporary_tree_aux_layer;
					has_temporary_layers=true;
					has_temporary_layers_global = true;
				}
			}
			
			if(has_temporary_layers){
				temporary_tree += temporary_tree_aux;
			}
		}
	}
	
	
	temporary_tree += '	</div>';
	temporary_tree += '</div>';
	temporary_tree += '</div>';
	
	
	
	this.$temporary_container.append(temporary_tree);
	
	$(".temporal-type-radio").unbind("change").change(function(){
		$(".temporal-type-radio").each(function(){
			var value =  $(this).is(':checked');
			var name = $(this).attr("id");
			
			$("input."+name+"").each(function(){
				$(this).attr("disabled",!value);
			});
			$("select."+name+"").each(function(){
				$(this).attr("disabled",!value);
			});
			if(value){
				$("span."+name+"").each(function(){
					$(this).removeClass("temporal-buttons-disabled");
				});
			}else{
				$("span."+name+"").each(function(){
					$(this).addClass("temporal-buttons-disabled");
				});
			}
		});
		self.refreshSlider();
	});
	
	$(".from-input-group-date-apply-present").unbind("click").click(function(){
		$("#from-custom-value-year").val(0);
		$("#from-custom-value-month").val(0);
		$("#from-custom-value-day").val(0);
		$("#from-custom-value-hour").val(0);
		$("#from-custom-value-minute").val(0);
		$("#from-custom-value-second").val(0);
		
		$("#from-custom-value").val("PRESENT");
		$("#from-custom-definition-panel").slideUp();

		self.refreshSlider();
	});
	
	$(".from-input-group-date-apply").unbind("click").click(function(){
		var year = $("#from-custom-value-year").val();
		var month = $("#from-custom-value-month").val();
		var day = $("#from-custom-value-day").val();
		var hour = $("#from-custom-value-hour").val();
		var minute = $("#from-custom-value-minute").val();
		var second = $("#from-custom-value-second").val();
		
		if(year == 0 && month == 0 && day == 0 && hour == 0 && minute == 0 && second == 0){
			$("#from-custom-value").val("PRESENT");
		}else{
			var result = "P";
			if(!(year == 0 && month == 0 && day == 0)){
				if(year != 0){
					result += (year + "Y");
				}
				if(month != 0){
					result += (month + "M");
				}
				if(day != 0){
					result += (day + "D");
				}
			}
			if(!(hour == 0 && minute == 0 && second == 0)){
				result += "T";
				if(hour != 0){
					result += (hour + "H");
				}
				if(minute != 0){
					result += (minute + "M");
				}
				if(second != 0){
					result += (second + "S");
				}
			}
			if($("#temporary-range").is(":checked")){
				if($("#to-date-value").is(":checked") || $("#to-custom-value").val() == "PRESENT"){
					$("#from-custom-value").val(result);
				}else{
					alert(gettext("Only relative intervals can be defined if the other field is PRESENT or a concrete date."));
				}
			}else{
				alert(gettext("Only PRESENT is available in Instant mode. You need to define a RANGE to use relative intervals"));
			}
		}
		$("#from-custom-definition-panel").slideUp();

		self.refreshSlider();
	});
	
	$(".from-custom-definition-button").unbind("click").click(function(){
		if($("#temporary-range").is(":checked")){
			$("#from-custom-definition-panel").slideDown();
		}else{
			alert(gettext("Only PRESENT is available in Instant mode. You need to define a RANGE to use relative intervals"));
		}
	});
	
	
	$(".to-input-group-date-apply-present").unbind("click").click(function(){
		$("#to-custom-value-year").val(0);
		$("#to-custom-value-month").val(0);
		$("#to-custom-value-day").val(0);
		$("#to-custom-value-hour").val(0);
		$("#to-custom-value-minute").val(0);
		$("#to-custom-value-second").val(0);
		
		$("#to-custom-value").val("PRESENT");
		$("#to-custom-definition-panel").slideUp();
		
		self.refreshSlider();
	});
	
	$(".to-input-group-date-apply").unbind("click").click(function(){
		var year = $("#to-custom-value-year").val();
		var month = $("#to-custom-value-month").val();
		var day = $("#to-custom-value-day").val();
		var hour = $("#to-custom-value-hour").val();
		var minute = $("#to-custom-value-minute").val();
		var second = $("#to-custom-value-second").val();
		
		if(year == 0 && month == 0 && day == 0 && hour == 0 && minute == 0 && second == 0){
			$("#to-custom-value").val("PRESENT");
		}else{
			var result = "P";
			if(!(year == 0 && month == 0 && day == 0)){
				if(year != 0){
					result += (year + "Y");
				}
				if(month != 0){
					result += (month + "M");
				}
				if(day != 0){
					result += (day + "D");
				}
			}
			if(!(hour == 0 && minute == 0 && second == 0)){
				result += "T";
				if(hour != 0){
					result += (hour + "H");
				}
				if(minute != 0){
					result += (minute + "M");
				}
				if(second != 0){
					result += (second + "S");
				}
			}
			
			if($("#temporary-range").is(":checked")){
				if($("#from-date-value").is(":checked") || $("#from-custom-value").val() == "PRESENT"){
					$("#to-custom-value").val(result);
				}else{
					alert(gettext("Only relative intervals can be defined if the other field is PRESENT or a concrete date."));
				}
			}else{
				alert(gettext("Only PRESENT is available in Instant mode. You need to define a RANGE to use relative intervals"));
			}
		}
		$("#to-custom-definition-panel").slideUp();

		self.refreshSlider();
	});
	
	$(".to-custom-definition-button").unbind("click").click(function(){
		$("#to-custom-definition-panel").slideDown();
	});
	
	
	
	$(".temporary-check").unbind("click").click(function(){
		self.showHideTemporalPanel();
	});

	$(".temporal-buttons-left-from").unbind("click").click(function(){
		if(self.hasTemporaryLayersActive()) {
			var prev_value = null;
			var input = $("input[name=temporary-group]:checked");
			try {
				if(input.attr("data-value") == "range"){
					prev_value = $('.temporary-layers-slider').slider("values")[0];
					prev_value_to = $('.temporary-layers-slider').slider("values")[1];
				}
				
				if(input.attr("data-value") == "single"){
					prev_value = $('.temporary-layers-slider').slider("value");
				}
				
			} catch (err){}
		
			var aux_min = self.current_min_val;
			if(self.step_val_array && self.step_val_array.length > 0){
				var index = self.step_val_array.indexOf(self.findNearest(prev_value));
				if (index > 0){
					aux_min = self.step_val_array[index-1];
					
				} else {
					aux_min = self.step_val_array[0];
				}
				
			} else {
				if(prev_value && (prev_value - self.step_val) > self.current_min_val){
					aux_min = (prev_value - self.step_val);
				}
			}
			
			if(input.attr("data-value") == "single"){
				$(".temporary-layers-slider").slider('value',aux_min);
			}
			
			if(input.attr("data-value") == "range"){
				$(".temporary-layers-slider").slider('values',0,aux_min);
			}
			
			var dt_cur_from = new Date(aux_min*1000);
			var formatted = self.formatDate(dt_cur_from);
			$("#temporary-from").val(formatted);
    	
	    	if(input.attr("data-value") == "single"){
	    		self.updateTemporalLayers(dt_cur_from);
			}
	    	
			if(input.attr("data-value") == "range"){
				var dt_cur_to = new Date(prev_value_to*1000);
				self.updateTemporalLayers(dt_cur_from, dt_cur_to);
			}
		}
		
	});
	
	$(".temporal-buttons-right-from").unbind("click").click(function(){
		if(self.hasTemporaryLayersActive()){
			var prev_value = null;
			var input = $("input[name=temporary-group]:checked");
			try{
				if(input.attr("data-value") == "range"){
					prev_value = $('.temporary-layers-slider').slider("values")[0];
					prev_value_to = $('.temporary-layers-slider').slider("values")[1];
					
				}
				
				if(input.attr("data-value") == "single"){
					prev_value = $('.temporary-layers-slider').slider("value");
				}
				
			} catch(err){}
			
			var aux_max = self.current_max_val;
			if(self.step_val_array && self.step_val_array.length > 0){
				var index = self.step_val_array.indexOf(self.findNearest(prev_value));
				if(index < self.step_val_array.length-1 && index != -1){
					aux_max = self.step_val_array[index+1];
					
				} else {
					aux_max = self.step_val_array[self.step_val_array.length-1];
				}
				
			} else {
				if(prev_value && (prev_value + self.step_val) < self.max_val){
					aux_max = (prev_value + self.step_val);
				}
				
			}
			
			if(input.attr("data-value") == "single"){
				$(".temporary-layers-slider").slider('value',aux_max);
			}
			
			if(input.attr("data-value") == "range"){
				$(".temporary-layers-slider").slider('values',0,aux_max);
			}
			
			var dt_cur_from = new Date(aux_max*1000);
			var formatted = self.formatDate(dt_cur_from);
	    	$("#temporary-from").val(formatted);
	
	    	if(input.attr("data-value") == "single"){
	    		self.updateTemporalLayers(dt_cur_from);
			}
	    	
			if(input.attr("data-value") == "range"){
				var dt_cur_to = new Date(prev_value_to*1000);
				self.updateTemporalLayers(dt_cur_from, dt_cur_to);
			}
		}
	});
	
	
	$(".temporal-buttons-left-to").unbind("click").click(function(){
		if(self.hasTemporaryLayersActive()){
			var prev_value = null;
			try {
				prev_value_from = $('.temporary-layers-slider').slider("values")[0];
				prev_value = $('.temporary-layers-slider').slider("values")[1];
				
			} catch(err){
			
			}
		
			var aux_min = self.current_min_val;
			if(self.step_val_array && self.step_val_array.length > 0){
				var index = self.step_val_array.indexOf(self.findNearest(prev_value));
				if(index > 0){
					aux_min = self.step_val_array[index-1];
				} else {
					aux_min = self.step_val_array[0];
				}
				
			} else {
				if(prev_value && (prev_value - self.step_val) > self.min_val){
					aux_min = (prev_value - self.step_val);
				}
			}
			var dt_cur_from = new Date(prev_value_from*1000);
			var dt_cur_to = new Date(aux_min*1000);
			var formatted = self.formatDate(dt_cur_to);
			$("#temporary-to").val(formatted);
		
			$(".temporary-layers-slider").slider('values',1,aux_min);
			self.updateTemporalLayers(dt_cur_from, dt_cur_to);
		}
	});
	
	$(".temporal-buttons-right-to").unbind("click").click(function(){
		if(self.hasTemporaryLayersActive()){
			var prev_value = null;
			try {
				prev_value_from = $('.temporary-layers-slider').slider("values")[0];
				prev_value = $('.temporary-layers-slider').slider("values")[1];
				
			} catch(err){}
			
			var aux_max = self.current_max_val;
			if(self.step_val_array && self.step_val_array.length > 0){
				var index = self.step_val_array.indexOf(self.findNearest(prev_value));
				if (index < self.step_val_array.length-1 && index != -1){
					aux_max = self.step_val_array[index+1];
					
				} else {
					aux_max = self.step_val_array[self.step_val_array.length-1];
				}
				
			} else {
				if (prev_value && (prev_value + self.step_val) < self.max_val){
					aux_max = (prev_value + self.step_val);
				}
			}
			
			var dt_cur_from = new Date(prev_value_from*1000);
			var dt_cur_to = new Date(aux_max*1000);
			var formatted = self.formatDate(dt_cur_to);
			$("#temporary-to").val(formatted);
		
			$(".temporary-layers-slider").slider('values',1,aux_max);
			self.updateTemporalLayers(dt_cur_from, dt_cur_to);
		}
	});
	
	$("input[name=temporary-group]").change(function (e) {
		self.refreshTemporalSlider();
	});
	
	$("#temporary-step-unit").change(function () {
		self.refreshTemporalStep();
	});
	
	if(!has_temporary_layers_global){
		$(".temporary-tab").css("display","none");
	}
	
	$('#datetimepicker-from').datetimepicker({
		format: 'DD-MM-YYYY HH:mm:ss',
		showClose: false
	});
	
	$('#datetimepicker-to').datetimepicker({
		format: 'DD-MM-YYYY HH:mm:ss',
		showClose: false
	});
	

	
	
	$('#datetimepicker-from').on('dp.change', function(e){ 
		if(e){
		    var formatedValue = e.date.format(e.date._f);
		    var value_from = moment(formatedValue, e.date._f);
		    if($('input[name=temporary-group]:checked').attr("data-value") == "single"){
		    	var date_from = new Date(value_from);
		    	self.updateTemporalLayers(date_from);
		    	value_from = date_from.getTime()/1000;
		    	self.updateFromSlider(value_from);
		    }else{
		    	var date_from = new Date(value_from);
		    	var value_to = moment($("#temporary-to").val(), e.date._f);
		    	self.updateTemporalLayers(date_from, new Date(value_to));
		    	value_from = date_from.getTime()/1000;
		    	self.updateFromSlider(value_from);
		    }
		}
	});
	
	$('#datetimepicker-to').on('dp.change', function(e){ 
		if(e){
			var formatedValue = e.date.format(e.date._f);
			var value_from = moment($("#temporary-from").val(), e.date._f);
		    var value_to = moment(formatedValue, e.date._f);
		    var date_to = new Date(value_to);
		    self.updateTemporalLayers(new Date(value_from), new Date(value_to));
	    	value_to = date_to.getTime()/1000;
		    self.updateToSlider(value_to);
		}
	});
	
	document.getElementById('temporary-from').addEventListener('keyup',function(e){
	    if (e.which == 13) this.blur();
	});
	
	document.getElementById('temporary-to').addEventListener('keyup',function(e){
	    if (e.which == 13) this.blur();
	});
	

};


layerTree.prototype.showHideTemporalPanel = function() {
	var self = this;
	if ( $("#enable-temporary").is(':checked') ) {
		$('.temporary-body').show();
		if(self.hasTemporaryLayersActive()){
			self.refreshTemporalInfo()
			self.refreshTemporalStep();
			
			self.updateTemporalLayers();
			
			self.refreshTemporalSlider();
			
			if(self.max_val){
				var dt_cur_from = new Date(self.max_val*1000);
				var formatted = self.formatDate(dt_cur_from);
				$("#temporary-from").val(formatted);
				self.updateTemporalLayers(dt_cur_from);
				$(".temporary-layers-slider").slider('value',self.max_val);
			}
	    
		} else {
			$("#enable-temporary").prop('checked', false);
			$('.temporary-body').hide();
			
			$("#enable-temporary-error").show();
		    setTimeout(function() {
		    	$("#enable-temporary-error").hide();
		    }, 7000);
		}
		
	} else {
	    $('.temporary-body').hide();
	    self.updateTemporalLayers();
	}
};

layerTree.prototype.hasTemporaryLayersActive = function() {
	return $(".temporary-body .box-body ul.layer-tree div.temporary-layer:visible").length > 0;
};

layerTree.prototype.assignStyleToLayer = function(layer, style) {
	if(!(layer.getSource() instanceof ol.source.WMTS)){
		layer.getSource().updateParams({"STYLES":style});
		
	} else {
		var ignSource3 = new ol.source.WMTS({
			layer: layer.getSource()['layer_'],
			url: layer.getSource()['urls'][0],
			projection: layer.getSource()['projection_'],
			matrixSet: layer.getSource()['matrixSet_'],
			format:'image/png',
			tileGrid: layer.getSource()['tileGrid'],
			crossOrigin: 'anonymous',
			style: style,
			wrapX: true
		});

		layer.setSource(ignSource3);
	}
	var selectedStyle = null;
	for (var i=0; i<layer.styles.length; i++) {
		if (layer.styles[i].name == style) {
			selectedStyle = layer.styles[i];
		}
	}
	if (selectedStyle.has_custom_legend) {
		layer.legend = selectedStyle.custom_legend_url;

	} else {
		var url_split = layer.legend_graphic.split('&STYLE=');
		if(url_split.length > 1){
			var aux = ""
			var index = url_split[1].indexOf('&');
			if(index != -1){
				layer.legend = url_split[0] +  url_split[1].substring(index);
			}else{
				layer.legend = url_split[0];
			}
		} else {
			layer.legend = layer.legend_graphic;
		}
		layer.legend = layer.legend + '&STYLE=' + style;
		layer.legend_no_auth = layer.legend;
	}

	viewer.core.legend.reloadLegend();
};

layerTree.prototype.updateFromSlider = function(value_from) {
	if($('input[name=temporary-group]:checked').attr("data-value") == "single"){
		$(".temporary-layers-slider").slider('value',value_from);
	}else{
		$(".temporary-layers-slider").slider('values', 0, value_from);
	}
};

layerTree.prototype.updateToSlider = function(value_to) {
	$(".temporary-layers-slider").slider('values', 1, value_to);
};


layerTree.prototype.refreshTemporalStep = function() {
	var value = "1";//$("#temporary-step-value").val();
	var unit = $("#temporary-step-unit option:selected").val();
	
	if(unit=="second"){
		this.step_val = value*1;
		$('#datetimepicker-from').datetimepicker().data('DateTimePicker').format('DD-MM-YYYY HH:mm:ss');
		$('#datetimepicker-to').datetimepicker().data('DateTimePicker').format('DD-MM-YYYY HH:mm:ss');
		this.current_min_val = this.getNewLimit(this.min_val,'YYYY-MM-DDTHH:mm:ssZ');
		this.current_max_val = this.getNewLimit(this.max_val,'YYYY-MM-DDTHH:mm:ssZ');
		this.step_val_array = [];
	}
	if(unit=="minute"){
		this.step_val = value*60;
		$('#datetimepicker-from').datetimepicker().data('DateTimePicker').format('DD-MM-YYYY HH:mm');
		$('#datetimepicker-to').datetimepicker().data('DateTimePicker').format('DD-MM-YYYY HH:mm');
		this.current_min_val = this.getNewLimit(this.min_val,'YYYY-MM-DDTHH:mm:00Z');
		this.current_max_val = this.getNewLimit(this.max_val,'YYYY-MM-DDTHH:mm:00Z');
		this.step_val_array = [];
	}
	if(unit=="hour"){
		this.step_val = value*60*60;
		$('#datetimepicker-from').datetimepicker().data('DateTimePicker').format('DD-MM-YYYY HH:00');
		$('#datetimepicker-to').datetimepicker().data('DateTimePicker').format('DD-MM-YYYY HH:00');
		this.current_min_val = this.getNewLimit(this.min_val,'YYYY-MM-DDTHH:00:00Z');
		this.current_max_val = this.getNewLimit(this.max_val,'YYYY-MM-DDTHH:00:00Z');
		this.step_val_array = [];
	}
	if(unit=="day"){
		this.step_val = value*60*60*24;
		$('#datetimepicker-from').datetimepicker().data('DateTimePicker').format('DD-MM-YYYY');
		$('#datetimepicker-to').datetimepicker().data('DateTimePicker').format('DD-MM-YYYY');
		this.current_min_val = this.getNewLimit(this.min_val,'YYYY-MM-DD');
		this.current_max_val = this.getNewLimit(this.max_val,'YYYY-MM-DD');
		this.step_val_array = [];
	}
	if(unit=="month"){
		this.step_val = 1;
		$('#datetimepicker-from').datetimepicker().data('DateTimePicker').format('MM-YYYY');
		$('#datetimepicker-to').datetimepicker().data('DateTimePicker').format('MM-YYYY');
		this.current_min_val = this.getNewLimit(this.min_val,'YYYY-MM');
		this.current_max_val = this.getNewLimit(this.max_val,'YYYY-MM');
		var current_min_date = new Date(this.current_min_val*1000);
		var current_max_date = new Date(this.current_max_val*1000);
		this.step_val_array = [];
		while((current_min_date.getFullYear() < current_max_date.getFullYear()) || 
				(current_min_date.getFullYear() == current_max_date.getFullYear() && 
				current_min_date.getMonth() <= current_max_date.getMonth())){
			this.step_val_array.push(current_min_date.getTime()/1000);
			current_min_date.setMonth(current_min_date.getMonth()+parseInt(value));
		}
	}
	if(unit=="year"){
		this.step_val = 1;
		$('#datetimepicker-from').datetimepicker().data('DateTimePicker').format('YYYY');
		$('#datetimepicker-to').datetimepicker().data('DateTimePicker').format('YYYY');
		this.current_min_val = this.getNewLimit(this.min_val,'YYYY');
		this.current_max_val = this.getNewLimit(this.max_val,'YYYY');
		var current_min_date = new Date(this.current_min_val*1000);
		var current_max_date = new Date(this.current_max_val*1000);
		this.step_val_array = [];
		while(current_min_date.getFullYear() <= current_max_date.getFullYear()){
			this.step_val_array.push(current_min_date.getTime()/1000);
			current_min_date.setFullYear(current_min_date.getFullYear()+parseInt(value));
		}
	}
	
	this.refreshTemporalSlider();
};
 
layerTree.prototype.findNearest = function(value) {
	var nearest = null;
	var diff = null;
	for (var i = 0; i < this.step_val_array.length; i++) {
		var newDiff = Math.abs(value - this.step_val_array[i]);
		if (diff == null || newDiff < diff) {
			nearest = this.step_val_array[i];
			diff = newDiff;
		}
	}
	return nearest;
};

layerTree.prototype.getNewLimit = function(value, format){
	var date = new Date(value*1000);
	var formatedValue = moment(date).format(format);
    var date_from = new Date(formatedValue);
    return date_from.getTime()/1000;
};

layerTree.prototype.refreshTemporalInfo = function() {
	var layers = [];
	$(".temporary-layer").each(function(){
		if($(this).css("display") == "block"){
			layers.push($(this).attr("data-id"));
		}
	});
	
	var methodx = "Hola";//$("input[name=temporary-group]:checked").val();
	var self = this;
	
	$.ajax({
		type: 'POST',
		async: false,
	  	url: '/gvsigonline/services/layers_get_temporal_properties/',
	  	data: {
	  		'layers': JSON.stringify(layers),
			'methodx': methodx
		},
	  	success	:function(response){
	  		var dt_from = response['min_value'];
	  		if(dt_from == ""){
	  			self.min_val = 0;
	  		}else{
	  			self.min_val = Date.parse(dt_from)/1000;
	  		}
	  		var dt_to = response['max_value'];
	  		if(dt_to == ""){
	  			self.max_val = 0;
	  		}else{
	  			self.max_val = Date.parse(dt_to)/1000;
	  		}
	  		
	  		try{
	  			self.mosaic_values = JSON.parse(response['mosaic_values'].replace(/'/g, "\""));
	  		}catch (err){
	  		
	  		}
	  		
	  		self.refreshTemporalSlider();
		},
	  	error: function(e){
	  		alert("error");
	  		
	  	}
	});
};

layerTree.prototype.getStepMax = function(layer_step, combo_step) {
	if(layer_step == null){
		return combo_step;
	}
	
	if(layer_step == "year"){
		return layer_step
	}
	
	if(layer_step == "month"){
		if(combo_step == "year"){
			return combo_step;
		}
		else{
			return layer_step;
		}
	}
	
	if(layer_step == "day"){
		if(combo_step == "year" || combo_step == "month"){
			return combo_step;
		}
		else{
			return layer_step;
		}
	}
	
	if(layer_step == "hour"){
		if(combo_step == "year" || combo_step == "month" || combo_step == "day"){
			return combo_step;
		}
		else{
			return layer_step;
		}
	}
	
	if(layer_step == "minute"){
		if(combo_step == "year" || combo_step == "month" || combo_step == "day" || combo_step == "hour"){
			return combo_step;
		}
		else{
			return layer_step;
		}
	}
	
	if(layer_step == "second"){
		if(combo_step == "year" || combo_step == "month" || combo_step == "day" || combo_step == "hour" || combo_step == "minute"){
			return combo_step;
		}
		else{
			return layer_step;
		}
	}
	
	return combo_step;
	
};

layerTree.prototype.adaptToStep = function(layer, date) {
	var hours = date.getHours();
	var minutes = date.getMinutes();
	var seconds = date.getSeconds();
	hours = hours < 10 ? '0'+hours : hours;
	minutes = minutes < 10 ? '0'+minutes : minutes;
	seconds = seconds < 10 ? '0'+seconds : seconds;
	var days = date.getDate();
	var month = date.getMonth()+1;
	days = days < 10 ? '0'+days : days;
	month = month < 10 ? '0'+month : month;
	
	var date_string = date.getFullYear();
	var step = $("#temporary-step-unit").val();
	
	var step_value = this.getStepMax(layer.time_resolution, step);
	
	if(step_value=="year"){
		date_string = date.getFullYear();
	}
	if(step_value=="month"){
		date_string = date.getFullYear()+"-"+month;
	}
	if(step_value=="day"){
		date_string = date.getFullYear()+"-"+month+"-"+days;
	}
	if(step_value=="hour"){
		date_string = date.getFullYear()+"-"+month+"-"+days+"T"+hours+"Z";
	}
	if(step_value=="minute"){
		date_string = date.getFullYear()+"-"+month+"-"+days+"T"+hours+":"+minutes+"Z";
	}
	if(step_value=="second"){
		date_string = date.getFullYear()+"-"+month+"-"+days+"T"+hours+":"+minutes+":"+seconds+"Z";
	}
	
	return date_string;
};


layerTree.prototype.parseISOString = function(s) {
	  var b = s.split(/\D+/);
	  return new Date(Date.UTC(b[0], --b[1], b[2], b[3], b[4], b[5], b[6]));
};

layerTree.prototype.updateTemporalLayers = function(startDate, endDate) {
	var layers = [];
	$(".temporary-layer").each(function(){
		if($(this).css("display") == "block"){
			layers.push($(this).attr("data-layerid"));
		}
	});
	
	var maplayers = this.map.getLayers();
	if(maplayers.getArray() != null){
		for(var i=0; i<maplayers.getArray().length; i++){
			var maplayer = maplayers.getArray()[i];
			if((jQuery.inArray(maplayer.get("id"), layers)>-1)){
				if($(".temporary-check").is(':checked')){
					if(startDate){
						var start = '';
						var end = '';
						
						
						if($("#from-custom-date-value").is(':checked')){
							start = $("#from-custom-value").val();
						}else{
							start = startDate.toISOString();
							start = this.adaptToStep(maplayer, startDate);
						}
						
						if (endDate){
							if($("#to-custom-date-value").is(':checked')){
								end = $("#to-custom-value").val();
							}else{
								end = this.adaptToStep(maplayer, endDate);
							}

							start = start + "/" + end;
						}
						
						maplayer.getSource().updateParams({'TIME': start});
					}
				}else{
					if(maplayer.getSource() != null && typeof maplayer.getSource().updateParams === 'function'){
						var params = maplayer.getSource().getParams();
						maplayer.getSource().updateParams({'TIME': ""});
						delete params['TIME'];
					}
				}
			}else{
				if(maplayer.getSource() != null && typeof maplayer.getSource().updateParams === 'function'){
					var params = maplayer.getSource().getParams();
					maplayer.getSource().updateParams({'TIME': ""});
					delete params['TIME'];
				}
			}
		}
	}
};

layerTree.prototype.refreshTemporalSlider = function() {
	var self = this;
	var update_min = true;
	var input = $("input[name=temporary-group]:checked");
		if(input.attr("data-value") == "single"){
			var prev_value = null;
			try{
				prev_value = $('.temporary-layers-slider').slider("values")[0];
				if(!prev_value){
					prev_value = $('.temporary-layers-slider').slider("value");
				}
			}catch(err){
				
			}
			$("#to_label_div").css("display","none");
			if($(".temporary-layers-slider").hasClass("ui-slider")){
				$(".temporary-layers-slider").slider( "destroy" );
			}

			$(".temporary-layers-slider").slider({
			    min: this.current_min_val,
			    max: this.current_max_val,
			    value: this.current_max_val,
			    step: this.step_val,
			    range: false,
			    slide: function(event, ui) {
			    	var calculated_value = ui.value;
			    	if(self.step_val_array && self.step_val_array.length > 0){
			    		calculated_value = self.findNearest(ui.value);
			    	}
			    	ui.value = calculated_value;
			    	var dt_cur_from = new Date(calculated_value*1000);
			    	var values = $(".temporary-layers-slider").slider('values')
			    	if(values && values.length > 0){
			    		$(".temporary-layers-slider").slider('values', 0, calculated_value);
			    	}
			    	var formatted = self.formatDate(dt_cur_from);
			    	$("#temporary-from").val(formatted);
			    	self.updateTemporalLayers(dt_cur_from);
			    	self.updateFromSlider(calculated_value);
			    },
				stop: function( event, ui ) {
					var calculated_value = ui.value;
			    	if(self.step_val_array && self.step_val_array.length > 0){
			    		calculated_value = self.findNearest(ui.value);
			    	}
			    	self.updateFromSlider(calculated_value);
				}
			});
			
			if(prev_value){
				var dt_cur_from = new Date(prev_value*1000);
				var formatted = self.formatDate(dt_cur_from);
		    	$("#temporary-from").val(formatted);
		    	$(".temporary-layers-slider").slider('value',prev_value);
		    	self.updateTemporalLayers(dt_cur_from);
		    	update_min = false;
			}
		}
		
		if(input.attr("data-value") == "range"){
			var prev_value = $('.temporary-layers-slider').slider("value");
			$("#to_label_div").css("display","block");
			if($(".temporary-layers-slider").hasClass("ui-slider")){
				$(".temporary-layers-slider").slider( "destroy" );
			}

			$(".temporary-layers-slider").slider({
				min: this.current_min_val,
			    max: this.current_max_val,
			    value: this.current_max_val,
		        step: this.step_val,
			    range: true,
			    slide: function( event, ui ) {
			    	var calculated_values = ui.values;
			    	if(self.step_val_array && self.step_val_array.length > 0){
			    		calculated_values[0] = self.findNearest(ui.values[0]);
			    		calculated_values[1] = self.findNearest(ui.values[1]);
			    	}
			    	ui.values = calculated_values;
			    	var dt_cur_from = new Date(ui.values[0]*1000); //.format("yyyy-mm-dd hh:ii:ss");
			    	$(".temporary-layers-slider").slider('value', dt_cur_from);
			    	var formatted = self.formatDate(dt_cur_from);
			    	$("#temporary-from").val(formatted);

			        var dt_cur_to = new Date(ui.values[1]*1000); //.format("yyyy-mm-dd hh:ii:ss");                
			        var formatted = self.formatDate(dt_cur_to);
			    	$("#temporary-to").val(formatted);
			        
			        self.updateTemporalLayers(dt_cur_from, dt_cur_to);
			        self.updateFromSlider(calculated_values[0]);
			        self.updateToSlider(calculated_values[1]);
			    },
				stop: function( event, ui ) {
					var calculated_values = ui.values;
			    	if(self.step_val_array && self.step_val_array.length > 0){
			    		calculated_values[0] = self.findNearest(ui.values[0]);
			    		calculated_values[1] = self.findNearest(ui.values[1]);
			    	}
			    	self.updateFromSlider(calculated_values[0]);
				    self.updateToSlider(calculated_values[1]);
				}
			});
			
	    	var dt_cur_to = new Date(this.current_max_val*1000);
			var formatted = self.formatDate(dt_cur_to);
	    	$("#temporary-to").val(formatted);
	    	
			var dt_cur_from = new Date(prev_value*1000);
			var formatted = self.formatDate(dt_cur_from);
	    	$("#temporary-from").val(formatted);
			
	    	$(".temporary-layers-slider").slider('values',1,this.current_max_val); // sets first handle (index 0) to 50
	    	$(".temporary-layers-slider").slider('values',0,prev_value);
	    	
	    	self.updateTemporalLayers(dt_cur_from, dt_cur_to);
	    	update_min = false;
		}
		
		if(update_min && self.min_val){
			var dt_cur_from = new Date(self.min_val*1000); //.format("yyyy-mm-dd hh:ii:ss");
			var formatted = self.formatDate(dt_cur_from);
			$("#temporary-from").val(formatted);
			self.updateTemporalLayers(dt_cur_from);
		}
	
};

layerTree.prototype.formatDate = function(date) {
	  var hours = date.getHours();
	  var minutes = date.getMinutes();
	  var seconds = date.getSeconds();
	  minutes = minutes < 10 ? '0'+minutes : minutes;
	  seconds = seconds < 10 ? '0'+seconds : seconds;
	  var days = date.getDate();
	  var month = date.getMonth()+1;
	  days = days < 10 ? '0'+days : days;
	  month = month < 10 ? '0'+month : month;

	  var strTime = hours + ':' + minutes + ':' + seconds;
	  var result = days + "-" + month + "-" + date.getFullYear() + "  " + strTime;

	  var unit = $("#temporary-step-unit option:selected").val();
	  if(unit=="second"){
		  strTime = hours + ':' + minutes + ':' + seconds;
		  result = days + "-" + month + "-" + date.getFullYear() + "  " + strTime;
		  return result;
	  }
	  if(unit=="minute"){
		  strTime = hours + ':' + minutes;
		  result = days + "-" + month + "-" + date.getFullYear() + "  " + strTime;
		  return result;
	  }
	  if(unit=="hour"){
		  strTime = hours + ':00';
		  result = days + "-" + month + "-" + date.getFullYear() + "  " + strTime;
		  return result;
	  }
	  if(unit=="day"){
		  result = days + "-" + month + "-" + date.getFullYear();
		  return result;
	  }
	  if(unit=="month"){
		  result = month + "-" + date.getFullYear();
		  return result;
	  }
	  if(unit=="year"){
		  result = date.getFullYear();
		  return result;
	  }

	  return result;
};


layerTree.prototype.zeroPad = function(num, places) {
	  var zero = places - num.toString().length + 1;
	  return Array(+(zero > 0 && zero)).join("0") + num;
};

layerTree.prototype.formatDT = function(__dt) {
	    var year = __dt.getFullYear();
	    var month = this.zeroPad(__dt.getMonth()+1, 2);
	    var date = this.zeroPad(__dt.getDate(), 2);
	    var hours = this.zeroPad(__dt.getHours(), 2);
	    var minutes = this.zeroPad(__dt.getMinutes(), 2);
	    var seconds = this.zeroPad(__dt.getSeconds(), 2);
	    return year + '-' + month + '-' + date + ' ' + hours + ':' + minutes + ':' + seconds;
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
layerTree.prototype.getBaseLayerFromMap = function(tocLayer) {
	var layers = this.map.getLayers();
	var mapLayer = null;
	layers.forEach(function(layer){
		if (layer.get('id')==tocLayer.id) {
			mapLayer = layer;
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

layerTree.prototype.createBaseLayerUI = function(layer) {	
	var mapLayer = this.getBaseLayerFromMap(layer);
	var id = layer.id;
    
	var ui = '';
	if (mapLayer) {
		mapLayer.setZIndex(this.baseLayerIndex);
		this.baseLayerIndex++;
		
		ui += '<div style="margin-left:20px;">';
		if (layer['default_baselayer']) {
			ui += 	'<input type="radio" id="' + id + '" data-origin="'+layer['name']+'" name="baselayers-group" checked>';
		} else {
			ui += 	'<input type="radio" id="' + id + '" data-origin="'+layer['name']+'" name="baselayers-group">';
		}
		ui += 		'<span class="text">' + layer['title'] + '</span>';
		ui += '</div>';
	}
	
	
	return ui;
};

layerTree.prototype.createEmptyBaseLayerUI = function() {	
	var ui = '';
	ui += '<div style="margin-left:20px;">';
	ui += 	'<input type="radio" id="gol-layer-empty" data-origin="empty" name="baselayers-group">';
	ui += 	'<span class="text">' + gettext('No layer') + '</span>';
	ui += '</div>';
	
	return ui;
};



layerTree.prototype.createTemporaryOverlayUI = function(layer) {
	
	var mapLayer = this.getLayerFromMap(layer);
	var id = layer.id;
	
	var ui = '';
	if (mapLayer) {
		if (layer.time_enabled) {	
			var language = $("#select-language").val();
		
			var conf = JSON.parse(layer.conf);
			var fields = conf.fields;
			var time_field = layer.time_enabled_field;
			for(var i=0; i<fields.length; i++){
				if(fields[i].name == time_field && fields[i]["title-"+language] != ""){
					time_field = fields[i]["title-"+language];
				}
			}
			
			var visibility = 'style="display: none;"';
			if(layer.visible){
				visibility = 'style="display: block;"';
			}
			
			ui += '<div id="layer-' + id + '" data-layerid="' + id + '" data-id="'+layer.ref+'" data-zindex="' + mapLayer.getZIndex() + '" class="temporary-layer box thin-border box-default collapsed-box" '+visibility+'>';
			ui += '		<div class="box-header with-border">';		
			ui += '			<span class="text">' + layer.title + '</span>';
			ui += '			<div class="box-tools pull-right">';
			ui += '				<button class="btn btn-box-tool btn-box-tool-custom" data-widget="collapse">';
			ui += '					<i class="fa fa-plus"></i>';
			ui += '				</button>';
			ui += '			</div>';
			ui += '		</div>';
			ui += '		<div class="box-body" style="display: none;">';
			
			if(fields.length > 0){
				ui +=  			gettext('temporary_field') + '<span class="pull-right" style="font-weight:bold;">'+time_field+'</span><div style="clear:both"></div>';
				
				if(layer.time_enabled_endfield != null && layer.time_enabled_endfield != ""){
					var time_endfield = layer.time_enabled_endfield;
					for(var i=0; i<fields.length; i++){
						if(fields[i].name == time_endfield && fields[i]["title-"+language] != ""){
							time_endfield = fields[i]["title-"+language];
						}
					}
					ui +=  			gettext('temporary_endfield') + '<span class="pull-right" style="font-weight:bold;">'+time_endfield+'</span><div style="clear:both"></div>';
				}
			
			}else{
				ui +=  			'<span class="pull-right" style="font-weight:bold;">'+gettext('Image Mosaic')+'</span><div style="clear:both"></div>';
				
			}
			
			ui += '		</div>';
			ui += '</div>';
		}
	}
	
	
	
	return ui;
};


layerTree.prototype.createOverlayUI = function(layer, group_visible) {
	
	var mapLayer = this.getLayerFromMap(layer);
	
	var ui = '';
	if (mapLayer) {
		mapLayer.on('precompose', function(event) {
			var min = 0;
			var max = 100;
			if(event.target.hasOwnProperty("swipe-min")){
				min = event.target["swipe-min"]
			}
			if(event.target.hasOwnProperty("swipe-max")){
				max = event.target["swipe-max"]
			}

	        var ctx = event.context;
	        var width = ctx.canvas.width * (min / 100);
	        var width2 = ctx.canvas.width * (max / 100);

	        ctx.save();
	        ctx.beginPath();
	        ctx.rect(width, 0, ctx.canvas.width - (ctx.canvas.width - width2) - width, ctx.canvas.height);
	        ctx.clip();
	      });

		mapLayer.on('postcompose', function(event) {
	        var ctx = event.context;
	        ctx.restore();
	      });

		var id = layer.id;
		
		ui += '<div id="layer-box-' + id + '" data-layerid="' + id + '" data-zindex="' + mapLayer.getZIndex() + '" class="box layer-box thin-border box-default collapsed-box">';
		ui += '		<div class="box-header with-border">';
		
		if(layer.icon) {
			ui += '			<span class="handle" style="margin-left:-1px"> ';
			ui += '			<image class="layer-icon" src="' + layer.icon + '" width=16px height=16px"/>';
			ui += '			</span>';
		} else {
			ui += '			<span class="handle"> ';
			ui += '				<i class="fa fa-ellipsis-v"></i>';
			ui += '				<i class="fa fa-ellipsis-v"></i>';
			ui += '			</span>';
		}
		
		if (group_visible) {
			ui += '		<input type="checkbox" id="' + id + '" disabled checked>';
		}else{
			if (layer.visible) {
				ui += '		<input type="checkbox" id="' + id + '" checked>';
			} else {
				ui += '		<input type="checkbox" id="' + id + '">';
			}
		}
		ui += '			<span class="text">' + layer.title + '</span>';
		ui += '			<div class="box-tools pull-right">';
		ui += '				<button class="btn btn-box-tool btn-box-tool-custom" data-widget="collapse">';
		ui += '					<i class="fa fa-plus"></i>';
		ui += '				</button>';
		ui += '			</div>';
		ui += '		</div>';
		ui += '		<div class="box-body" style="display: none;">';
		if (!layer.external){
			if( layer.queryable && layer.is_vector) {	    
				ui += '	<a id="show-attribute-table-' + id + '" data-id="' + id + '" class="btn btn-block btn-social btn-custom-tool show-attribute-table-link">';
				ui += '		<i class="fa fa-table"></i> ' + gettext('Attribute table');
				ui += '	</a>';
			}
		}
		if (layer.allow_download && (viewer.core.getDownloadManager().isManagerEnabled() || (layer.wfs_url || layer.wcs_url))) {
			ui += '	<a id="layer-downloads-' + id + '" class="btn btn-block btn-social btn-custom-tool layer-downloads-link">';
			ui += '		<i class="fa fa-download"></i> ' + gettext('Downloads');
			ui += '	</a>';
		}
		if (layer.metadata || (!layer.external)) {
			if (!layer.imported) {
				ui += '	<a id="show-metadata-' + id + '" href="#" class="btn btn-block btn-social btn-custom-tool show-metadata-link">';
				ui += '		<i class="fa fa-newspaper-o" aria-hidden="true"></i> ' + gettext('Metadata');
				ui += '	</a>';
			}
		}
		if (layer.detailed_info_enabled) {
			ui += '	<a id="detailed-info-' + id + '" href="#" class="btn btn-block btn-social btn-custom-tool detailed-info-link">';
			ui += '		<i class="fa fa-info-circle" aria-hidden="true"></i> ' + layer.detailed_info_button_title;
			ui += '	</a>';
		}
		if (!layer.external) {
			ui += '	<a id="zoom-to-layer-' + id + '" href="#" class="btn btn-block btn-social btn-custom-tool zoom-to-layer">';
			ui += '		<i class="fa fa-search" aria-hidden="true"></i> ' + gettext('Zoom to layer');
			ui += '	</a>';
		}
		
		if(layer.styles){
			if (layer.styles.length > 1) {
				ui += '		<div class="btn btn-block btn-social btn-select btn-custom-tool"><i class="fa fa-map-marker" aria-hidden="true"></i><select id="symbol-to-layer-' + id + '" class="symbol-to-layer btn btn-block btn-custom-tool">';
				for(var i=0; i<layer.styles.length; i++){
					var ttitle = layer.styles[i].title;
					if(!ttitle || ttitle.length == 0){
						ttitle = layer.styles[i].name;
					}
					
					if(layer.styles[i].is_default){
						ui += '		<option value="'+layer.styles[i].name+'" selected><i class="fa fa-search" aria-hidden="true"></i>'+ ttitle +'</option>';
					}else{
						ui += '		<option value="'+layer.styles[i].name+'"><i class="fa fa-search" aria-hidden="true"></i>'+ ttitle +'</option>';
					}
				}
				ui += '	</select></div>';
			}
		}
		
		ui += '			<label style="display: block; margin-top: 8px; width: 95%;">' + gettext('Opacity') + '<span id="layer-opacity-output-' + layer.id + '" class="margin-l-15 gol-slider-output">%</span></label>';
		ui += '			<div id="layer-opacity-slider" data-layerid="' + layer.id + '" class="layer-opacity-slider"></div>';
		ui += '			<label style="display: block; margin-top: 8px; width: 95%;">' + gettext('Swipe') + '<span id="layer-swipe-output-' + layer.id + '" class="margin-l-15 gol-slider-output">0% - 100%</span></label>';
		ui += '			<div id="layer-swipe-slider" data-layerid="' + layer.id + '" class="layer-swipe-slider"></div>';
		ui += '		</div>';
		ui += '</div>';
	}
	return ui;
};

layerTree.prototype.zoomToLayer = function(layer) {
	var self = this;
	if (Array.isArray(layer.latlong_extent) && layer.latlong_extent.length==4) { // use extent from metadata if available
		var extent = ol.proj.transformExtent(layer.latlong_extent, ol.proj.get('EPSG:4326'), ol.proj.get('EPSG:3857'));
		self.map.getView().fit(extent, self.map.getSize());
		return;
		
	} else if (layer.imported && layer.is_vector) {
		self.map.getView().fit(layer.getSource().getExtent(), self.map.getSize());
		return;
	}
	
	var layer_name = layer.layer_name;

	var url = layer.wms_url+'?request=GetCapabilities&service=WMS';
	var parser = new ol.format.WMSCapabilities();
	$.ajax(url).then(function(response) {
		   var result = parser.read(response);
		   var Layers = result.Capability.Layer.Layer; 
		   var extent = null;
		   for (var i=0, len = Layers.length; i<len; i++) {
		     var layerobj = Layers[i];
		     if (layerobj.Name == layer_name) {
		         extent = layerobj.EX_GeographicBoundingBox;
		         break;
		     }
		   }
		   if((extent===null || extent[0]==0 && extent[1]==0 && extent[2]==-1 && extent[3]==-1 )||
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
layerTree.prototype.layerDownloads = function(layer) {
	viewer.core.getDownloadManager().layerDownloads(layer);
};

/**
 * TODO
 */
layerTree.prototype.showMetadata = function(layer) {
	$('#float-modal .modal-title').empty();
	$('#float-modal .modal-title').append(layer.title);
	
	var body = '';
	body += '<div class="row">';
	body += 	'<div class="col-md-12">';
	body += 		'<p>' + layer.abstract + '</p>';				
	body += 	'</div>';
	body += '</div>';
	
	$('#float-modal .modal-body').empty();
	$('#float-modal .modal-body').append(body);
	
	var buttons = '';
	buttons += '<button id="float-modal-cancel-metadata" type="button" class="btn btn-default" data-dismiss="modal">' + gettext('Cancel') + '</button>';
	if (layer.metadata_url != '') {
		buttons += '<button id="float-modal-show-metadata" type="button" class="btn btn-default">' + gettext('Show in geonetwork') + '</button>';
	}
	
	$('#float-modal .modal-footer').empty();
	$('#float-modal .modal-footer').append(buttons);
	
	$("#float-modal").modal('show');
	
	var self = this;	
	$('#float-modal-show-metadata').on('click', function () {
		var win = window.open(layer.metadata_url, '_blank');
		  win.focus();
		
		$('#float-modal').modal('hide');
	});
	return;
};

/**
 * TODO
 */
layerTree.prototype.detailedInfo = function(layer) {
	var body = '';
	body += '<div class="row">';
	body += 	layer.detailed_info_html;
	body += '</div>';
	
	$('#float-modal .modal-body').empty();
	$('#float-modal .modal-body').append(body);
	
	var buttons = '';
	buttons += '<button id="float-modal-cancel-metadata" type="button" class="btn btn-default" data-dismiss="modal">' + gettext('Cancel') + '</button>';
	
	$('#float-modal .modal-footer').empty();
	$('#float-modal .modal-footer').append(buttons);
	
	$("#float-modal").modal('show');
};

/**
 * TODO
 */
layerTree.prototype.reorder = function(event,ui) {
	var self = this;
	var groupOrder = ui.item[0].parentNode.dataset.grouporder;
	var groupLayers = ui.item[0].parentNode.children;
	var mapLayers = this.map.getLayers();
	
	var zindex = parseInt(groupOrder);
	var mapLayers_length = mapLayers.getLength();
	
	for (var i=0; i<groupLayers.length; i++) {
		var layerid = groupLayers[i].dataset.layerid;
		mapLayers.forEach(function(layer){
			if (layer.get('id') == layerid) {
				var order = zindex + mapLayers_length;
				layer.setZIndex(order);
				if (!layer.imported) {
					self.changeState(layer, 'layer', 'change-order', order);
				}
				mapLayers_length--;
			}
		}, this);
	}
};

/**
 * TODO
 */
layerTree.prototype.changeState = function(object, objectType, action, value) {
	
	if (objectType == 'layer') {
		for (var i=0; i<this.state.layerGroups.length; i++) {
			for (var j=0; j<this.state.layerGroups[i].layers.length; j++) {	
				if (this.state.layerGroups[i].layers[j].id == object.get('id')) {
					if (action == 'change-opacity') {
						this.state.layerGroups[i].layers[j].opacity = value;
						
					} else if (action == 'set-visibility') {
						this.state.layerGroups[i].layers[j].visible = value;
						if (value) {
							this.registerAction(this.state.layerGroups[i].layers[j]);
						}
						
						
					} else if (action == 'change-order') {
						this.state.layerGroups[i].layers[j].order = value;
						
					} else if (action == 'change-baselayer') {
						this.state.layerGroups[i].layers[j].default_baselayer = value;
						if (value) {
							this.registerAction(this.state.layerGroups[i].layers[j]);
						}
					}
				}				
				
			}
		}
		
	} else if (objectType == 'layergroup') {
		for (var i=0; i<this.state.layerGroups.length; i++) {
			if (this.state.layerGroups[i].groupName == object.groupName) {
				if (action == 'set-visibility') {
					this.state.layerGroups[i].visible = value;
					
				}
			}				
		}
	}
	
};

/**
 * TODO
 */
layerTree.prototype.getState = function() {
	return this.state;
};

layerTree.prototype.registerAction = function(layer) {
	var self = this;
	
	$.ajax({
		type: 'POST',
		async: true,
	  	url: '/gvsigonline/services/register_action/',
	  	data: {
	  		'layer_name': layer.name,
			'workspace': layer.workspace
		},
	  	success	:function(response){
	  		console.log('Layer action registered');
		},
	  	error: function(e){
	  		console.log('Error registering layer action');
	  		
	  	}
	});
};