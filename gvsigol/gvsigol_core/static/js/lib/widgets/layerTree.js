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
						if($("#layer-"+layer.get("id")).length){
							$("#layer-"+layer.get("id")).css("display", "none");
							self.refreshTemporalInfo();	
							self.updateTemporalLayers();
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
	
	
	/**
	 * TEMPORARY TAB
	 */
	

	
	var temporary_tree = '';
	temporary_tree += '<div style="background-color:#f9fafc">';
	temporary_tree += '	<div class="box-body">';
	
	var input_from = '<div class="input-group date col-md-9" id="datetimepicker-from"><input id="temporary-from" class="form-control"/><span class="input-group-addon"><span class="glyphicon glyphicon-calendar"></span></span></div>';
	var input_to = '<div class="input-group date col-md-9" id="datetimepicker-to"><input id="temporary-to" class="form-control"/><span class="input-group-addon"><span class="glyphicon glyphicon-calendar"></span></span></div>';

//	temporary_tree += '			<label style="display: block; margin-top: 8px; width: 95%;">' + gettext('Temporary range') + '</label>';
	temporary_tree += '			<div id="from_label_div" class="temporary_field"><div class="col-md-3" style="padding:0px"><span class="text" style="font-weight:bold;margin-left:3px;">' + gettext('From') + '</span></div>'+input_from+'<div style="clear:both"></div></div>';
	temporary_tree += '			<div id="to_label_div" class="temporary_field"><div class="col-md-3" style="padding:0px"><span class="text" style="font-weight:bold;margin-left:3px;" >' + gettext('To') + '</span></div>'+input_to+'<div style="clear:both"></div></div>';
	temporary_tree += '			<div id="step_label_div"><span class="text" style="font-weight:bold;margin-left:3px;" >' + gettext('Step') + '</span><div class="pull-right"><input id="temporary-step-value" type="number" class="ui-slider-step" min=1 value="1"/><select id="temporary-step-unit"><option value="minute">' + gettext('minute(s)') + '</option><option value="hour">' + gettext('hour(s)') + '</option><option value="day" selected>' + gettext('day(s)') + '</option><option value="month">' + gettext('month(s)') + '</option><option value="year">' + gettext('year(s)') + '</option></select></div><div style="clear:both"></div></div>';
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
	temporary_tree += '<div class="box" style="border-top:45px solid #e8ecf4;">';
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
	
	
	
	this.$temporary_container.append(temporary_tree);
	

	
	var self = this;
	
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
	
	$("#temporary-step-value").change(function () {
		self.refreshTemporalStep();
	});
	
	$("#temporary-step-unit").change(function () {
		self.refreshTemporalStep();
	});
	
	if(!has_temporary_layers_global){
		$(".temporary-tab").css("display","none");
	}
	
	$('#datetimepicker-from').datetimepicker({
		format: 'DD-MM-YYYY HH:mm:ss',
		showClose: true
	});
	
	$('#datetimepicker-to').datetimepicker({
		format: 'DD-MM-YYYY HH:mm:ss',
		showClose: true
	});
	
	self.refreshTemporalInfo()
	self.refreshTemporalStep();
	
	self.updateTemporalLayers();
	
	
	$('#datetimepicker-from').on('dp.change', function(e){ 
	    var formatedValue = e.date.format(e.date._f);
	    var value_from = moment(formatedValue, "DD-MM-YYYY HH:mm:ss")/1000;
	    if($('input[name=temporary-group]:checked').attr("data-value") == "single"){
	    	$(".temporary-layers-slider").slider('value',value_from);
	    	self.updateTemporalLayers(new Date(value_from*1000));
	    }else{
	    	var value_to = moment($("#temporary-to").val(), "DD-MM-YYYY HH:mm:ss")/1000;
	    	$(".temporary-layers-slider").slider('values', 0, value_from);
	    	self.updateTemporalLayers(new Date(value_from*1000), new Date(value_to*1000));
	    }
	    
	});
	
	$('#datetimepicker-to').on('dp.change', function(e){ 
		var formatedValue = e.date.format(e.date._f);
		var value_from = moment($("#temporary-from").val(), "DD-MM-YYYY HH:mm:ss")/1000;
	    var value_to = moment(formatedValue, "DD-MM-YYYY HH:mm:ss")/1000;
	    $(".temporary-layers-slider").slider('values', 1, value_to);
	    self.updateTemporalLayers(new Date(value_from*1000), new Date(value_to*1000));
	});
	
	self.refreshTemporalSlider();
	
	if(self.min_val){
		var dt_cur_from = new Date(self.min_val*1000); //.format("yyyy-mm-dd hh:ii:ss");
		var formatted = self.formatDate(dt_cur_from);
		$("#temporary-from").val(formatted);
		self.updateTemporalLayers(dt_cur_from);
	}
};

layerTree.prototype.refreshTemporalStep = function() {
	var value = $("#temporary-step-value").val();
	var unit = $("#temporary-step-unit option:selected").val();
	
	if(unit=="second"){
		this.step_val = value;
	}
	if(unit=="minute"){
		this.step_val = value*60;
	}
	if(unit=="hour"){
		this.step_val = value*60*60;
	}
	if(unit=="day"){
		this.step_val = value*60*60*24;
	}
	if(unit=="month"){
		this.step_val = value*60*60*24*30;
	}
	if(unit=="year"){
		this.step_val = value*60*60*365;
	}
	
	this.refreshTemporalSlider();
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
		date_string = date.toISOString();
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
		}
	}
}

layerTree.prototype.refreshTemporalSlider = function() {
	var self = this;
	var input = $("input[name=temporary-group]:checked");
		if(input.attr("data-value") == "single"){
			$("#to_label_div").css("display","none");
			if($(".temporary-layers-slider").hasClass("ui-slider")){
				$(".temporary-layers-slider").slider( "destroy" );
			}
			var new_max = this.max_val;
			if(this.step_val > 1){
				if((this.max_val - this.min_val)%this.step_val!=0){
					var number_steps = Math.floor((this.max_val - this.min_val)/this.step_val) + 1;
					new_max = this.min_val + (this.step_val * number_steps);
				}
			}
			$(".temporary-layers-slider").slider({
			    min: this.min_val,
			    max: new_max,
			    value: this.min_val,
			    step: this.step_val,
			    range: false,
			    slide: function(event, ui) {
			    	var dt_cur_from = new Date(ui.value*1000); //.format("yyyy-mm-dd hh:ii:ss");
			    	var formatted = self.formatDate(dt_cur_from);
			    	$("#temporary-from").val(formatted);
			    	self.updateTemporalLayers(dt_cur_from);
			    }
			});
		}
		
		if(input.attr("data-value") == "range"){
			$("#to_label_div").css("display","block");
			if($(".temporary-layers-slider").hasClass("ui-slider")){
				$(".temporary-layers-slider").slider( "destroy" );
			}
			var new_max = this.max_val;
			if(this.step_val > 1){
				if((this.max_val - this.min_val)%this.step_val!=0){
					var number_steps = Math.floor((this.max_val - this.min_val)/this.step_val) + 1;
					new_max = this.min_val + (this.step_val * number_steps);
				}
			}
			$(".temporary-layers-slider").slider({
				min: this.min_val,
			    max: new_max,
			    value: this.min_val,
		        step: this.step_val,
			    range: true,
			    slide: function( event, ui ) {
			    	var dt_cur_from = new Date(ui.values[0]*1000); //.format("yyyy-mm-dd hh:ii:ss");
			    	var formatted = self.formatDate(dt_cur_from);
			    	$("#temporary-from").val(formatted);

			        var dt_cur_to = new Date(ui.values[1]*1000); //.format("yyyy-mm-dd hh:ii:ss");                
			        var formatted = self.formatDate(dt_cur_to);
			    	$("#temporary-to").val(formatted);
			        
			        self.updateTemporalLayers(dt_cur_from, dt_cur_to);
			    }
			});
		}
		
		if(input.attr("data-value") == "list"){
			var valMap = [min_val,max_val,min_val,max_val,min_val,max_val];
			$("#to_label_div").css("display","none");
			if($(".temporary-layers-slider").data("slider")){
				$(".temporary-layers-slider").slider( "destroy" );
			}
			$(".temporary-layers-slider").slider({
		         min: 0,
		         max: valMap.length - 1,
		         value: min_val,
		         range: false,
		         step: 1,
		         slide: function(event, ui) {
		          var dt_cur_to = new Date(valMap[ui.value]*1000)
		          var formatted = self.formatDate(dt_cur_from);
		          $("#temporary-from").val(formatted);
		         }
		     });
		}
		
		if(input.attr("data-value") == "list_range"){
			var valMap = [min_val,max_val,min_val,max_val,min_val,max_val];
			$("#to_label_div").css("display","block");
			if($(".temporary-layers-slider").data("slider")){
				$(".temporary-layers-slider").slider( "destroy" );
			}
			$(".temporary-layers-slider").slider({
		         min: 0,
		         max: valMap.length - 1,
		         value: min_val,
		         step: 1,
		         range: true,
		         slide: function(event, ui) {
		        	 var dt_cur_from = new Date(valMap[ui.values[0]]*1000)
		        	 var formatted = self.formatDate(dt_cur_from);
				     $("#temporary-from").val(formatted);
		        	 var dt_cur_to = new Date(valMap[ui.values[1]]*1000)
		        	 var formatted = self.formatDate(dt_cur_to);
				    $("#temporary-to").val(formatted);
		         }
		     });
		}
		
		if(self.min_val){
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
	  return days + "-" + month + "-" + date.getFullYear() + "  " + strTime;
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
