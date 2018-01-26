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
	this.is_first_time = true;
	this.$container = $('#layer-tree-tab');
	this.$temporary_container = $('#temporary-tab');
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
	
	this.step_val_array = [];
	this.step_val = 1;
	this.min_val = 0;
	this.max_val = 1;
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
			tree += '						<button class="btn btn-box-tool btn-box-tool-custom group-collapsed-button" data-widget="collapse">';
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
	
	$(".show-attribute-table-link").on('click', function(e) {
		var selectedLayer = null;
		var layers = self.map.getLayers();
		layers.forEach(function(layer){
			if (layer.baselayer == false) {
				if (this.dataset.id == layer.get('id')) {
					selectedLayer = layer;
				}
			}						
		}, this);
		var dataTable = new attributeTable(selectedLayer, self.map, self.conf);
		dataTable.show();
		dataTable.registerEvents();
	});
	
	$(".show-metadata-link").on('click', function(e) {
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
	
	
	$(".symbol-to-layer").on('change', function(e) {
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
	
	
	/**
	 * TEMPORARY TAB
	 */
	

	
	var temporary_tree = '';
	temporary_tree += '<div style="background-color:#f9fafc">';
	temporary_tree += '<input type="checkbox" id="enable-temporary" class="temporary-check">'+ gettext("Habilitar características temporales")+'</input> <div id="temporary-panel">';
	temporary_tree += '	<div id="enable-temporary-error"><i class="fa fa-exclamation-triangle" aria-hidden="true"></i>&nbsp;&nbsp;&nbsp;&nbsp;' + gettext("A visible layer with temporal properties is needed") + '</div>';
	temporary_tree += '	<div class="box-body temporary-body">';
	
	var input_from = '<div class="input-group date col-md-9" id="datetimepicker-from"><input id="temporary-from" class="form-control"/><span class="input-group-addon"><span class="glyphicon glyphicon-calendar"></span></span>'+
	'<span class="input-group-addon temporal-buttons-empty-gap"></span><span class="temporal-buttons temporal-buttons-left temporal-buttons-left-from"><i class="fa fa-minus" aria-hidden="true"></i></span><span class="temporal-buttons temporal-buttons-right temporal-buttons-right-from"><i class="fa fa-plus" aria-hidden="true"></i></span></div>';
	var input_to = '<div class="input-group date col-md-9" id="datetimepicker-to"><input id="temporary-to" class="form-control"/><span class="input-group-addon"><span class="glyphicon glyphicon-calendar"></span></span>'+
	'<span class="input-group-addon temporal-buttons-empty-gap"></span><span class="temporal-buttons temporal-buttons-left temporal-buttons-left-to"><i class="fa fa-minus" aria-hidden="true"></i></span><span class="temporal-buttons temporal-buttons-right temporal-buttons-right-to"><i class="fa fa-plus" aria-hidden="true"></i></span></div>';

//	temporary_tree += '			<label style="display: block; margin-top: 8px; width: 95%;">' + gettext('Temporary range') + '</label>';
	temporary_tree += '			<div id="from_label_div" class="temporary_field"><div class="col-md-3" style="padding:0px"><span class="text" style="font-weight:bold;margin-left:3px;">' + gettext('From') + '</span></div>'+input_from+'<div style="clear:both"></div></div>';
	temporary_tree += '			<div id="to_label_div" class="temporary_field"><div class="col-md-3" style="padding:0px"><span class="text" style="font-weight:bold;margin-left:3px;" >' + gettext('To') + '</span></div>'+input_to+'<div style="clear:both"></div></div>';
	temporary_tree += '			<div id="step_label_div"><span class="text" style="font-weight:bold;margin-left:3px;" >' + gettext('Step') + '</span><div class="pull-right">'+/*'<input id="temporary-step-value" type="number" class="ui-slider-step" min=1 value="1" disabled/>'+*/'<select id="temporary-step-unit"><option value="second">' + gettext('second(s)') + '</option><option value="minute">' + gettext('minute(s)') + '</option><option value="hour">' + gettext('hour(s)') + '</option><option value="day" selected>' + gettext('day(s)') + '</option><option value="month">' + gettext('month(s)') + '</option><option value="year">' + gettext('year(s)') + '</option></select></div><div style="clear:both"></div></div>';
	temporary_tree += '			<div id="temporary-layers-slider" class="temporary-layers-slider"></div>';
	
	
	temporary_tree += '<div style="margin-left:10px;">';
	temporary_tree += 	'<input type="radio" id="temporary-single" data-value="single" name="temporary-group" checked>';
	temporary_tree += 	'<span class="text">'+gettext('Single')+'</span>';
	temporary_tree += '</div>';
	
	temporary_tree += '<div style="margin-left:10px;">';
	temporary_tree += 	'<input type="radio" id="temporary-range" data-value="range" name="temporary-group">';
	temporary_tree += 	'<span class="text">'+gettext('Range')+'</span>';
	temporary_tree += '</div>';
	
	
//	temporary_tree += '<div style="margin-left:10px;">';
//	temporary_tree += 	'<input type="radio" id="temporary-list" data-value="list" name="temporary-group">';
//	temporary_tree += 	'<span class="text"> List of values </span>';
//	temporary_tree += '</div>';
//	
//	temporary_tree += '<div style="margin-left:10px;">';
//	temporary_tree += 	'<input type="radio" id="temporary-list-range" data-value="list_range" name="temporary-group">';
//	temporary_tree += 	'<span class="text"> Range between in list of values </span>';
//	temporary_tree += '</div>';
//	
	
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
//			temporary_tree_aux += '			<li class="box box-default collapsed-box" id="' + layerGroup.groupId + '">';
//			temporary_tree_aux += '				<div class="box-header with-border">';
//			temporary_tree_aux += '					<input type="checkbox" class="templayer-group" id="layergroup-' + layerGroup.groupId + '">';
//			temporary_tree_aux += '					<span class="text">' + layerGroup.groupTitle + '</span>';
//			temporary_tree_aux += '					<div class="box-tools pull-right">';
//			temporary_tree_aux += '						<button class="btn btn-box-tool btn-box-tool-custom" data-widget="collapse">';
//			temporary_tree_aux += '							<i class="fa fa-plus"></i>';
//			temporary_tree_aux += '						</button>';
//			temporary_tree_aux += '					</div>';
//			temporary_tree_aux += '				</div>';
//			temporary_tree_aux += '				<div data-groupnumber="' + (groupCount++) * 100 + '" class="box-body layer-tree-groups" style="display: block;">';
			for (var j=0; j<layerGroup.layers.length; j++) {	
				var layer = layerGroup.layers[j];				
				var temporary_tree_aux_layer = self.createTemporaryOverlayUI(layer);
				if(temporary_tree_aux_layer != ''){
					temporary_tree_aux += temporary_tree_aux_layer;
					has_temporary_layers=true;
					has_temporary_layers_global = true;
				}
			}
//			temporary_tree_aux += '				</div>';
//			temporary_tree_aux += '			</li>';
			if(has_temporary_layers){
				temporary_tree += temporary_tree_aux;
			}
		}
	}
	
	
	temporary_tree += '	</div>';
	temporary_tree += '</div>';
	temporary_tree += '</div>';
	
	
	
	this.$temporary_container.append(temporary_tree);
	
	$(".temporary-check").click(function(){
		self.showHideTemporalPanel();
	});

	$(".temporal-buttons-left-from").unbind("click").click(function(){
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
		}catch(err){
			
		}
		
		var aux_min = self.current_min_val;
		if(self.step_val_array && self.step_val_array.length > 0){
			var index = self.step_val_array.indexOf(self.findNearest(prev_value));
			if(index > 0){
				aux_min = self.step_val_array[index-1];
			}else{
				aux_min = self.step_val_array[0];
			}
		}else{
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

//		self.refreshTemporalSlider();
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
		}catch(err){
			
		}
		
		var aux_max = self.current_max_val;
		if(self.step_val_array && self.step_val_array.length > 0){
			var index = self.step_val_array.indexOf(self.findNearest(prev_value));
			if(index < self.step_val_array.length-1 && index != -1){
				aux_max = self.step_val_array[index+1];
			}else{
				aux_max = self.step_val_array[self.step_val_array.length-1];
			}
		}else{
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
		try{
			prev_value_from = $('.temporary-layers-slider').slider("values")[0];
			prev_value = $('.temporary-layers-slider').slider("values")[1];
		}catch(err){
			
		}
		
		var aux_min = self.current_min_val;
		if(self.step_val_array && self.step_val_array.length > 0){
			var index = self.step_val_array.indexOf(self.findNearest(prev_value));
			if(index > 0){
				aux_min = self.step_val_array[index-1];
			}else{
				aux_min = self.step_val_array[0];
			}
		}else{
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
		try{
			prev_value_from = $('.temporary-layers-slider').slider("values")[0];
			prev_value = $('.temporary-layers-slider').slider("values")[1];
		}catch(err){
			
		}
		var aux_max = self.current_max_val;
		if(self.step_val_array && self.step_val_array.length > 0){
			var index = self.step_val_array.indexOf(self.findNearest(prev_value));
			if(index < self.step_val_array.length-1 && index != -1){
				aux_max = self.step_val_array[index+1];
			}else{
				aux_max = self.step_val_array[self.step_val_array.length-1];
			}
		}else{
			if(prev_value && (prev_value + self.step_val) < self.max_val){
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
	

	
//	$(".temporary-layer").change(function(){
//		
//	});
	
	$("input[name=temporary-group]").change(function (e) {
		self.refreshTemporalSlider();
	});
	
//	$(".templayer-group").change(function (e) {
//		var groupId = this.id.split('-')[1]; 
//		var checked = this.checked;
//		for (var i=0; i<self.conf.layerGroups.length; i++) {			
//			var group = self.conf.layerGroups[i];
//			if (group.groupId == groupId) {
//				for (var j=0; j<group.layers.length; j++) {
//					var layer = group.layers[j];
//					var layerCheckboxes = $(".temp-"+layer.id);
//					if(layerCheckboxes.length > 0){
//						var layerCheckbox = layerCheckboxes[0];
//						if (checked) {
//							layerCheckbox.checked = true;
//							layerCheckbox.disabled = true;
//							
//						} else {
//							layerCheckbox.checked = false;
//							layerCheckbox.disabled = false;
//						}
//						
//					}
//				}
//			}			
//		}
//		self.refreshTemporalInfo();
//	});
	
//	$("#temporary-step-value").change(function () {
//		self.refreshTemporalStep();
//	});
	
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
//		    	var userTimezoneOffset = date_from.getTimezoneOffset() * 60000;
//		    	date_from = new Date(date_from.getTime() - userTimezoneOffset);
		    	value_from = date_from.getTime()/1000;
		    	self.updateFromSlider(value_from);
		    }else{
		    	var date_from = new Date(value_from);
		    	var value_to = moment($("#temporary-to").val(), e.date._f);
		    	self.updateTemporalLayers(date_from, new Date(value_to));
//		    	var userTimezoneOffset = date_from.getTimezoneOffset() * 60000;
//		    	date_from = new Date(date_from.getTime() - userTimezoneOffset);
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
//		    var userTimezoneOffset = date_to.getTimezoneOffset() * 60000;
//		    date_to = new Date(date_to.getTime() - userTimezoneOffset);
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
				var dt_cur_from = new Date(self.max_val*1000); //.format("yyyy-mm-dd hh:ii:ss");
				var formatted = self.formatDate(dt_cur_from);
				$("#temporary-from").val(formatted);
				self.updateTemporalLayers(dt_cur_from);
				$(".temporary-layers-slider").slider('value',self.max_val);
			}
	//		self.is_first_time = false;
	//	}
	    
		}else{
			$("#enable-temporary").prop('checked', false);
			$('.temporary-body').hide();
			
			$("#enable-temporary-error").show();
		    setTimeout(function() {
		    	$("#enable-temporary-error").hide();
		    }, 7000);
		}
	} 
	else {
	    $('.temporary-body').hide();
	    self.updateTemporalLayers();
	}
}

layerTree.prototype.hasTemporaryLayersActive = function() {
	return $(".temporary-body .box-body ul.layer-tree div.temporary-layer:visible").length > 0;
}

layerTree.prototype.assignStyleToLayer = function(layer, style) {
	layer.getSource().updateParams({"STYLES":style});
	//layer.legend = "http://localhost/gs-local/pruebaandorra61/wms?SERVICE=WMS&VERSION=1.1.1&layer=proteccion_civil&REQUEST=getlegendgraphic&STYLE=pruebaandorra61_proteccion_civil_19&FORMAT=image/png";
	var url_split = layer.legend.split('&STYLE=');
	if(url_split.length > 1){
		var aux = ""
		var index = url_split[1].indexOf('&');
		if(index != -1){
			layer.legend = url_split[0] +  url_split[1].substring(index);
		}else{
			layer.legend = url_split[0];
		}
	}
	layer.legend = layer.legend + '&STYLE=' + style;
	viewer.core.legend.reloadLegend();
}

layerTree.prototype.updateFromSlider = function(value_from) {
	if($('input[name=temporary-group]:checked').attr("data-value") == "single"){
		$(".temporary-layers-slider").slider('value',value_from);
	}else{
		$(".temporary-layers-slider").slider('values', 0, value_from);
	}
}

layerTree.prototype.updateToSlider = function(value_to) {
	$(".temporary-layers-slider").slider('values', 1, value_to);
}


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
}
 
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
}

layerTree.prototype.getNewLimit = function(value, format){
	var date = new Date(value*1000);
	var formatedValue = moment(date).format(format);
    var date_from = new Date(formatedValue);
//    var userTimezoneOffset = date_from.getTimezoneOffset() * 60000;
//    date_from = new Date(date_from.getTime() + userTimezoneOffset);
    return date_from.getTime()/1000;
}

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
	  		self.refreshTemporalSlider();
		},
	  	error: function(e){
	  		alert("error");
	  		
	  	}
	});
};

layerTree.prototype.adaptToStep = function(date) {
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
	if(step=="month"){
		date_string = date.getFullYear()+"-"+month;
	}
	if(step=="day"){
		date_string = date.getFullYear()+"-"+month+"-"+days;
	}
	if(step=="hour"){
		date_string = date.getFullYear()+"-"+month+"-"+days+"T"+hours+"Z";
	}
	if(step=="minute"){
		date_string = date.getFullYear()+"-"+month+"-"+days+"T"+hours+":"+minutes+"Z";
	}
	if(step=="second"){
		date_string = date.getFullYear()+"-"+month+"-"+days+"T"+hours+":"+minutes+":"+seconds+"Z";
	}
	
	return date_string;
}

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
						var start = startDate.toISOString();
						start = this.adaptToStep(startDate);
						var end = '';
						if (endDate){
							end = this.adaptToStep(endDate);
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
}

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
//			var new_max = this.max_val;
//			if(this.step_val > 1){
//				if((this.max_val - this.min_val)%this.step_val!=0){
//					var number_steps = Math.floor((this.max_val - this.min_val)/this.step_val) + 1;
//					new_max = this.min_val + (this.step_val * number_steps);
//				}
//			}
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
			    	var dt_cur_from = new Date(calculated_value*1000); //.format("yyyy-mm-dd hh:ii:ss");
			    	var values = $(".temporary-layers-slider").slider('values')
			    	if(values && values.length > 0){
			    		$(".temporary-layers-slider").slider('values', 0, calculated_value);
			    	}
			    	var formatted = self.formatDate(dt_cur_from);
			    	$("#temporary-from").val(formatted);
			    	self.updateTemporalLayers(dt_cur_from);
			    	self.updateFromSlider(calculated_value);
//			    	console.log('selectedTime: ' + calculated_value +', current Time: '+ ui.value + ", date: "+ formatted);
			    },
				stop: function( event, ui ) {
//					console.log("Acabó en "+ui.value);
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
//			var new_max = this.max_val;
//			if(this.step_val > 1){
//				if((this.max_val - this.min_val)%this.step_val!=0){
//					var number_steps = Math.floor((this.max_val - this.min_val)/this.step_val) + 1;
//					new_max = this.min_val + (this.step_val * number_steps);
//				}
//			}
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
//					console.log("Acabó en "+ui.value);
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
		
//		if(input.attr("data-value") == "list"){
//			var valMap = [min_val,max_val,min_val,max_val,min_val,max_val];
//			$("#to_label_div").css("display","none");
//			if($(".temporary-layers-slider").data("slider")){
//				$(".temporary-layers-slider").slider( "destroy" );
//			}
//			$(".temporary-layers-slider").slider({
//		         min: 0,
//		         max: valMap.length - 1,
//		         value: min_val,
//		         range: false,
//		         step: 1,
//		         slide: function(event, ui) {
//		          var dt_cur_to = new Date(valMap[ui.value]*1000)
//		          var formatted = self.formatDate(dt_cur_from);
//		          $("#temporary-from").val(formatted);
//		         }
//		     });
//		}
//		
//		if(input.attr("data-value") == "list_range"){
//			var valMap = [min_val,max_val,min_val,max_val,min_val,max_val];
//			$("#to_label_div").css("display","block");
//			if($(".temporary-layers-slider").data("slider")){
//				$(".temporary-layers-slider").slider( "destroy" );
//			}
//			$(".temporary-layers-slider").slider({
//		         min: 0,
//		         max: valMap.length - 1,
//		         value: min_val,
//		         step: 1,
//		         range: true,
//		         slide: function(event, ui) {
//		        	 var dt_cur_from = new Date(valMap[ui.values[0]]*1000)
//		        	 var formatted = self.formatDate(dt_cur_from);
//				     $("#temporary-from").val(formatted);
//		        	 var dt_cur_to = new Date(valMap[ui.values[1]]*1000)
//		        	 var formatted = self.formatDate(dt_cur_to);
//				    $("#temporary-to").val(formatted);
//		         }
//		     });
//		}
		
		if(update_min && self.min_val){
			var dt_cur_from = new Date(self.min_val*1000); //.format("yyyy-mm-dd hh:ii:ss");
			var formatted = self.formatDate(dt_cur_from);
			$("#temporary-from").val(formatted);
			self.updateTemporalLayers(dt_cur_from);
		}
	
}

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
	}


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



layerTree.prototype.createTemporaryOverlayUI = function(layer) {
	
	var mapLayer = this.getLayerFromMap(layer);
	var id = layer.id;
	
	var ui = '';
	if (layer.time_enabled && layer.is_vector) {	
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
	
//		ui += '		<input type="checkbox" class="temporary-layer temp-'+id+'" id="' + id + '" data-id="'+layer.ref+'">';
	
		ui += '			<span class="text">' + layer.title + '</span>';
		ui += '			<div class="box-tools pull-right">';
		ui += '				<button class="btn btn-box-tool btn-box-tool-custom" data-widget="collapse">';
		ui += '					<i class="fa fa-plus"></i>';
		ui += '				</button>';
		ui += '			</div>';
		ui += '		</div>';
		ui += '		<div class="box-body" style="display: none;">';
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
		
		ui += '		</div>';
		ui += '</div>';
	}
	
	
	return ui;
};


layerTree.prototype.createOverlayUI = function(layer) {
	
	var mapLayer = this.getLayerFromMap(layer);
	var id = layer.id;
	
	var ui = '';
	ui += '<div id="layer-box-' + id + '" data-layerid="' + id + '" data-zindex="' + mapLayer.getZIndex() + '" class="box layer-box thin-border box-default collapsed-box">';
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
	ui += '			<a id="show-metadata-' + id + '" class="btn btn-block btn-social btn-custom-tool show-metadata-link">';
	ui += '				<i class="fa fa-external-link"></i> ' + gettext('Layer metadata');
	ui += '			</a>';
	if (layer.queryable && layer.is_vector) {	    
	    ui += '	<a id="show-attribute-table-' + id + '" data-id="' + id + '" class="btn btn-block btn-social btn-custom-tool show-attribute-table-link">';
		ui += '		<i class="fa fa-table"></i> ' + gettext('Attribute table');
		ui += '	</a>';
    }	

	ui += '	<a id="zoom-to-layer-' + id + '" href="#" class="btn btn-block btn-social btn-custom-tool zoom-to-layer">';
	ui += '		<i class="fa fa-search" aria-hidden="true"></i> ' + gettext('Zoom to layer');
	ui += '	</a>';
	
	if(layer.styles){
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
	}
	ui += '	</select></div>';
	
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
layerTree.prototype.showMetadata = function(layer) {
	
	$('#float-modal .modal-title').empty();
	$('#float-modal .modal-title').append(gettext('Layer metadata'));
	
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
	if (layer.metadata != '') {
		buttons += '<button id="float-modal-show-metadata" type="button" class="btn btn-default">' + gettext('Show in geonetwork') + '</button>';
	}
	
	$('#float-modal .modal-footer').empty();
	$('#float-modal .modal-footer').append(buttons);
	
	$("#float-modal").modal('show');
	
	var self = this;	
	$('#float-modal-show-metadata').on('click', function () {
		var win = window.open(layer.metadata, '_blank');
		  win.focus();
		
		$('#float-modal').modal('hide');
	});
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
