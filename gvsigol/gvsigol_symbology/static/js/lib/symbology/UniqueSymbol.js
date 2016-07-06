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
 
 
var UniqueSymbol = function(featureType, layerName, symbologyUtils, rule_opts, previewPointUrl, previewLineUrl, previewPolygonUrl) {
	this.selected = null;
	this.featureType = featureType;
	this.layerName = layerName;
	this.previewPointUrl = previewPointUrl;
	this.previewLineUrl = previewLineUrl;
	this.previewPolygonUrl = previewPolygonUrl;
	this.symbologyUtils = symbologyUtils;
	this.rule = new Rule(0, featureType, rule_opts);
	if (rule_opts != null) {
		if (rule_opts.symbolizers != "") {
			this.loadSymbols(rule_opts.symbolizers);
		}
	}	
};

UniqueSymbol.prototype.getRule = function() {
	return this.rule;
};

UniqueSymbol.prototype.appendSymbolizer = function() {
	var self = this;
	
	var symbolizer = null;
	if (this.featureType == 'PointSymbolizer') {
		symbolizer = new PointSymbolizer(this.rule.getNextSymbolizerId(), this.rule, this.symbologyUtils, null, this.previewPointUrl);
		
	} else if (this.featureType == 'LineSymbolizer') {
		symbolizer = new LineSymbolizer(this.rule.getNextSymbolizerId(), this.rule, null, this.previewLineUrl);
		
	} else if (this.featureType == 'PolygonSymbolizer') {
		symbolizer = new PolygonSymbolizer(this.rule.getNextSymbolizerId(), this.rule, null, this.previewPolygonUrl);
	}
	
	$('#table-symbolizers tbody').append(symbolizer.getTableUI());
	
	$("#table-symbolizers-body").sortable({
		placeholder: "sort-highlight",
		handle: ".handle",
		forcePlaceholderSize: true,
		zIndex: 999999
	});
	$("#table-symbolizers-body").on("sortupdate", function(event, ui){
		/*var rows = ui.item[0].parentNode.children;
		for(var i=0; i < rows.length; i++) {
			var symbol = self.rule.getSymbolizerById(rows[i].dataset.rowid);
			symbol.order = i;
		}*/		
	});
	
	$(".edit-symbolizer-link").on('click', function(e){	
		e.preventDefault();
		self.setSelected(self.rule.getSymbolizerById(this.dataset.symbolizerid));
		self.updateForm();
		$('#modal-symbolizer').modal('show');
	});
	
	$(".delete-symbolizer-link").one('click', function(e){	
		e.preventDefault();
		self.rule.removeSymbolizer(this.dataset.symbolizerid);
	});
	
	this.rule.appendSymbolizer(symbolizer);
	symbolizer.updatePreview();

	self.setSelected(symbolizer);
	this.updateForm();
};

UniqueSymbol.prototype.appendLabel = function() {
	var self = this;
	
	var previewUrl = null;
	if (this.featureType == 'PointSymbolizer') {
		previewUrl = this.previewPointUrl;
		
	} else if (this.featureType == 'LineSymbolizer') {
		previewUrl = this.previewLineUrl;
		
	} else if (this.featureType == 'PolygonSymbolizer') {
		previewUrl = this.previewPolygonUrl;
	}
	
	var label = new TextSymbolizer(this.rule.getNextLabelId(), this.symbologyUtils, this.rule, null, previewUrl);
	$('#table-symbolizers tbody').append(label.getTableUI());
	$('#table-symbolizers-body').sortable({
		placeholder: "sort-highlight",
		handle: ".handle",
		forcePlaceholderSize: true,
		zIndex: 999999
	});
	
	$(".edit-label-link").on('click', function(e){	
		e.preventDefault();
		self.setSelected(self.rule.getLabelById(this.dataset.labelid));
		self.updateForm();
		$('#modal-symbolizer').modal('show');
	});
	
	$(".delete-label-link").one('click', function(e){	
		e.preventDefault();
		self.rule.removeLabel(this.dataset.labelid);
	});
	
	this.rule.appendLabel(label);
	label.updatePreview();
	
	self.setSelected(label);
	this.updateForm();
	
	$('#append-label-button').css('display', 'none');
};

UniqueSymbol.prototype.setSelected = function(element) {
	this.selected = element;
};

UniqueSymbol.prototype.loadSymbols = function(symbolizers) {
	$("#table-symbolizers-body").empty();
	this.rule.removeAllSymbolizers();
	this.rule.removeAllLabels();
	for (var i=0; i<symbolizers.length; i++) {
		var symbolizer = JSON.parse(symbolizers[i].json);
		if (symbolizer.type == 'TextSymbolizer') {
			this.loadTextSymbolizer(symbolizer);
		} else if (symbolizer.type == 'ExternalGraphicSymbolizer') {
			this.loadExternalGraphicSymbolizer(symbolizer);
		} else {
			this.loadSymbolizer(symbolizer);
		}		
	}
};

UniqueSymbol.prototype.loadSymbolizer = function(symbolizer_object) {
	var self = this;
	
	var symbolizer = null;
	if (this.featureType == 'PointSymbolizer') {
		symbolizer = new PointSymbolizer(this.rule.getNextSymbolizerId(), this.rule, this.symbologyUtils, symbolizer_object, this.previewPointUrl);
		
	} else if (this.featureType == 'LineSymbolizer') {
		symbolizer = new LineSymbolizer(this.rule.getNextSymbolizerId(), this.rule, symbolizer_object, this.previewLineUrl);
		
	} else if (this.featureType == 'PolygonSymbolizer') {
		symbolizer = new PolygonSymbolizer(this.rule.getNextSymbolizerId(), this.rule, symbolizer_object, this.previewPolygonUrl);
	}
	
	$('#table-symbolizers tbody').append(symbolizer.getTableUI());
	
	$("#table-symbolizers-body").sortable({
		placeholder: "sort-highlight",
		handle: ".handle",
		forcePlaceholderSize: true,
		zIndex: 999999
	});
	$("#table-symbolizers-body").on("sortupdate", function(event, ui){
		/*var rows = ui.item[0].parentNode.children;
		for(var i=0; i < rows.length; i++) {
			var symbol = self.rule.getSymbolizerById(rows[i].dataset.rowid);
			symbol.order = i;
		}*/		
	});
	
	$(".edit-symbolizer-link").on('click', function(e){	
		e.preventDefault();
		self.setSelected(self.rule.getSymbolizerById(this.dataset.symbolizerid));
		self.updateForm();
		$('#modal-symbolizer').modal('show');
	});
	
	$(".delete-symbolizer-link").one('click', function(e){	
		e.preventDefault();
		self.rule.removeSymbolizer(this.dataset.symbolizerid);
	});
	
	this.rule.appendSymbolizer(symbolizer);
	symbolizer.updatePreview();

	self.setSelected(symbolizer);
	this.updateForm();
};

UniqueSymbol.prototype.loadTextSymbolizer = function(symbolizer_object) {
	var self = this;
	
	var label = new TextSymbolizer(this.rule.getNextLabelId(), this.symbologyUtils, this.rule, symbolizer_object);
	$('#table-symbolizers tbody').append(label.getTableUI());
	$("#table-symbolizers-body").sortable({
		placeholder: "sort-highlight",
		handle: ".handle",
		forcePlaceholderSize: true,
		zIndex: 999999
	});
	$("#table-symbolizers-body").on("sortupdate", function(event, ui){
		/*var rows = ui.item[0].parentNode.children;
		for(var i=0; i < rows.length; i++) {
			var symbol = self.rule.getSymbolizerById(rows[i].dataset.rowid);
			symbol.order = i;
		}*/		
	});
	
	$(".edit-label-link").on('click', function(e){	
		e.preventDefault();
		self.setSelected(self.rule.getLabelById(this.dataset.labelid));
		self.updateForm();
		$('#modal-symbolizer').modal('show');
	});
	
	$(".delete-label-link").one('click', function(e){	
		e.preventDefault();
		self.rule.removeLabel(this.dataset.labelid);
	});
	
	this.rule.appendLabel(label);
	label.updatePreview();

	self.setSelected(label);
	this.updateForm();
};

UniqueSymbol.prototype.loadExternalGraphicSymbolizer = function(symbolizer_object) {
	var self = this;
	
	var symbolizer = new ExternalGraphicSymbolizer(this.rule.getNextSymbolizerId(), symbolizer_object.name, symbolizer_object.format, symbolizer_object.size, symbolizer_object.online_resource);
	
	$('#table-symbolizers tbody').append(symbolizer.getTableUI());	
	$("#table-symbolizers-body").sortable({
		placeholder: "sort-highlight",
		handle: ".handle",
		forcePlaceholderSize: true,
		zIndex: 999999
	});
	$("#table-symbolizers-body").on("sortupdate", function(event, ui){});	
	$(".edit-eg-link").on('click', function(e){	
		e.preventDefault();
		messageBox.show('warning', gettext('Image symbols can only be edited from the library'));
	});
	$(".delete-symbolizer-link").one('click', function(e){	
		e.preventDefault();
		self.rule.removeSymbolizer(this.dataset.symbolizerid);
	});
	
	this.rule.appendSymbolizer(symbolizer);
};

UniqueSymbol.prototype.refreshMap = function() {
	this.symbologyUtils.updateMap(this.rule, this.layerName);
};

UniqueSymbol.prototype.libraryPreview = function(rid,json_symbolizers) {
	var symbolizers = new Array();
	var scount = 0;
	var previewUrl = null;
	for (var i=0; i<json_symbolizers.length; i++) {
		var symbolizer_object = JSON.parse(json_symbolizers[i].json);
		var symbolizer = null;
		if (symbolizer_object.type == 'PointSymbolizer') {
			symbolizer = new PointSymbolizer(this.count, this, this.symbologyUtils, symbolizer_object, this.previewPointUrl);
			previewUrl = this.previewPointUrl;
			
		} else if (symbolizer_object.type == 'LineSymbolizer') {
			symbolizer = new LineSymbolizer(this.count, this, symbolizer_object, this.previewLineUrl);
			previewUrl = this.previewLineUrl;
			
		} else if (symbolizer_object.type == 'PolygonSymbolizer') {
			symbolizer = new PolygonSymbolizer(this.count, this, symbolizer_object, this.previewPolygonUrl);
			previewUrl = this.previewPolygonUrl;
			
		} else if (symbolizer_object.type == 'TextSymbolizer') {
			symbolizer = new TextSymbolizer(this.count, this, symbolizer_object);
			previewUrl = this.previewPolygonUrl;
			
		}
		symbolizers.push(symbolizer);
		scount++;
	}
	symbolizers.sort(function(a, b){
		return parseInt(b.order) - parseInt(a.order);
	});
	
	var sldBody = this.symbologyUtils.getSLDBody(symbolizers);
	var url = previewUrl + '&SLD_BODY=' + encodeURIComponent(sldBody);
	var ui = '<img id="rule-preview-img" src="' + url + '" class="rule-preview"></img>';
	$("#library-symbol-preview-div-" + rid).empty();
	$("#library-symbol-preview-div-" + rid).append(ui);
};

UniqueSymbol.prototype.updateForm = function() {
	$('#tab-menu').empty();
	$('#tab-content').empty();	
	
	$('#tab-menu').append(this.selected.getTabMenu());
	if (this.selected.type == 'PointSymbolizer') {
		$('#tab-content').append(this.selected.getGraphicTabUI());
		$('#tab-content').append(this.selected.getFillTabUI());
		$('#tab-content').append(this.selected.getBorderTabUI());
		$('#tab-content').append(this.selected.getRotationTabUI());		
		$('.nav-tabs a[href="#graphic-tab"]').tab('show');
		this.registerSymbolizerEvents();
		
	} else if (this.selected.type == 'ExternalGraphicSymbolizer') {
		this.registerSymbolizerEvents();
		
	} else if (this.selected.type == 'LineSymbolizer') {
		$('#tab-content').append(this.selected.getBorderTabUI());
		$('.nav-tabs a[href="#border-tab"]').tab('show');
		this.registerSymbolizerEvents();
		
	} else if (this.selected.type == 'PolygonSymbolizer') {
		$('#tab-content').append(this.selected.getFillTabUI());
		$('#tab-content').append(this.selected.getBorderTabUI());
		$('#tab-content').append(this.selected.getRotationTabUI());
		$('.nav-tabs a[href="#fill-tab"]').tab('show');
		this.registerSymbolizerEvents();
		
	} else if (this.selected.type == 'TextSymbolizer') {
		$('#tab-content').append(this.selected.getFontTabUI());
		$('#tab-content').append(this.selected.getHaloTabUI());
		$('#tab-content').append(this.selected.getVendorTabUI());
		$('.nav-tabs a[href="#label-font-tab"]').tab('show');
		this.registerLabelEvents();
	}
};

UniqueSymbol.prototype.registerSymbolizerEvents = function() {
	var self = this;
	
	$("#graphic-size").on('change', function(e) {
		self.selected.size = this.value;
		self.selected.updatePreview();	
		//self.updatePreview();
	});
	$('input[type=checkbox][name=symbol-with-border]').change(function() {
		var isChecked = $('#symbol-with-border').is(":checked");
        if (isChecked) {
        	$("#border-div").css('display', 'block');
        	self.selected.with_border = true;
            
        } else {
        	$("#border-div").css('display', 'none');
        	self.selected.with_border = false;
        }
    });
	$("#shape").on('change', function(e) {
		self.selected.shape = this.value;
		self.selected.updatePreview();	
	});
	$( "#fill-opacity-slider" ).slider({
	    min: 0,
	    max: 100,
	    value: (self.selected.fill_opacity * 100),
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.selected.fill_opacity = opacity;
	    	self.selected.updatePreview();
	    },
	    slide: function( event, ui ) {
	    	$("#fill-opacity-output").text(ui.value + '%');
	    }
	});	
	$("#fill-color-chooser").on('change', function(e) {
		self.selected.fill_color = this.value;
		self.selected.updatePreview();	
	});	
	$('#symbol-with-border').on('change', function() {
		self.selected.with_border = this.checked;		
		self.selected.updatePreview();
	});
	$("#border-color-chooser").on('change', function(e) {
		self.selected.border_color = this.value;
		self.selected.updatePreview();	
	});
	$( "#border-opacity-slider" ).slider({
	    min: 0,
	    max: 100,
	    value: (self.selected.border_opacity * 100),
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.selected.border_opacity = opacity;
	    	self.selected.updatePreview();
	    },
	    slide: function( event, ui ) {
	    	$("#border-opacity-output").text(ui.value + '%');
	    }
	});
	$("#border-size").on('change', function(e) {
		self.selected.border_size = this.value;
		self.selected.updatePreview();	
	});
	$('#border-type').on('change', function() {
		self.selected.border_type = this.value;
		self.selected.updatePreview();
	});
	$( "#rotation-slider" ).slider({
	    min: 0,
	    max: 360,
	    value: self.selected.rotation,
	    slide: function( event, ui ) {
	    	var rotation = ui.value;
	    	$("#rotation-output").text(rotation + 'º');
	    	self.selected.rotation = rotation;
	    }
	});
};

UniqueSymbol.prototype.registerLabelEvents = function() {
	var self = this;
	
	$('#label-field').on('change', function() {
		self.selected.field = this.value;
		self.selected.updatePreview();
	});
	
	$('#label-font-family').on('change', function() {
		self.selected.font_family = this.value;
		self.selected.updatePreview();
	});
	
	$('#label-font-size').on('change', function() {
		self.selected.font_size = this.value;
		self.selected.updatePreview();
	});
	
	$('#label-font-color').on('change', function() {
		self.selected.font_color = this.value;		
		self.selected.updatePreview();
	});
	
	$('#label-font-weight').on('change', function() {
		self.selected.font_weight = this.value;
		self.selected.updatePreview();
	});
	
	$('#label-font-style').on('change', function() {
		self.selected.font_style = this.value;
		self.selected.updatePreview();
	});
	
	$('#label-halo-color').on('change', function() {
		self.selected.halo_color = this.value;		
		self.selected.updatePreview();
	});
	
	$('#label-halo-radius').on('change', function() {
		self.selected.halo_radius = this.value;		
		self.selected.updatePreview();
	});
	
	$( "#halo-opacity-slider" ).slider({
	    min: 0,
	    max: 100,
	    value: (self.selected.halo_opacity * 100),
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.selected.halo_opacity = opacity;
	    	self.selected.updatePreview();
	    },
	    slide: function( event, ui ) {
	    	$("#halo-opacity-output").text(ui.value + '%');
	    }
	});
	
	$('#label-max-iterations').on('change', function() {
		self.selected.max_iterations = this.value;		
		self.selected.updatePreview();
	});
	
	$('#label-max-length').on('change', function() {
		self.selected.max_length = this.value;		
		self.selected.updatePreview();
	});
	
	$('#label-min-wrapper').on('change', function() {
		self.selected.min_wrapper = this.value;		
		self.selected.updatePreview();
	});
	
	$('#label-solve-overlaps').on('change', function() {
		self.selected.solve_overlaps = this.checked;		
		self.selected.updatePreview();
	});
};

UniqueSymbol.prototype.save = function(layerId) {
	
	var symbolizers = new Array();
	for (var i=0; i < this.rule.getSymbolizers().length; i++) {
		var symbolizer = {
			type: this.rule.getSymbolizers()[i].type,
			sld: this.rule.getSymbolizers()[i].toXML(),
			json: this.rule.getSymbolizers()[i].toJSON(),
			order: this.rule.getSymbolizers()[i].order
		};
		symbolizers.push(symbolizer);
	}
	
	for (var i=0; i < this.rule.getLabels().length; i++) {
		var label = {
			type: this.rule.getLabels()[i].type,
			sld: this.rule.getLabels()[i].toXML(),
			json: this.rule.getLabels()[i].toJSON(),
			order: this.rule.getLabels()[i].order
		};
		symbolizers.push(label);
	}
	
	symbolizers.sort(function(a, b){
		return parseInt(b.order) - parseInt(a.order);
	});
	
	var style = {
		name: $('#style-name').val(),
		title: $('#style-title').val(),
		is_default: $('#style-is-default').is(":checked"),
		rule: this.rule,
		symbolizers: symbolizers
	}
	
	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/unique_symbol_add/" + layerId + "/",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		data: {
			style_data: JSON.stringify(style)
		},
		success: function(response){
			if (response.success) {
				location.href = "/gvsigonline/symbology/style_layer_list/";
			} else {
				alert('Error');
			}
			
		},
	    error: function(){}
	});
};

UniqueSymbol.prototype.update = function(layerId, styleId) {
	
	var symbolizers = new Array();
	for (var i=0; i < this.rule.getSymbolizers().length; i++) {
		var symbolizer = {
			type: this.rule.getSymbolizers()[i].type,
			sld: this.rule.getSymbolizers()[i].toXML(),
			json: this.rule.getSymbolizers()[i].toJSON(),
			order: this.rule.getSymbolizers()[i].order
		};
		symbolizers.push(symbolizer);
	}
	
	for (var i=0; i < this.rule.getLabels().length; i++) {
		var label = {
			type: this.rule.getLabels()[i].type,
			sld: this.rule.getLabels()[i].toXML(),
			json: this.rule.getLabels()[i].toJSON(),
			order: this.rule.getLabels()[i].order
		};
		symbolizers.push(label);
	}
	
	var style = {
		name: $('#style-name').val(),
		title: $('#style-title').val(),
		is_default: $('#style-is-default').is(":checked"),
		rule: this.rule,
		symbolizers: symbolizers
	}
	
	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/unique_symbol_update/" + layerId + "/" + styleId + "/",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		data: {
			style_data: JSON.stringify(style)
		},
		success: function(response){
			if (response.success) {
				location.href = "/gvsigonline/symbology/style_layer_list/";
			} else {
				alert('Error');
			}
			
		},
	    error: function(){}
	});
};