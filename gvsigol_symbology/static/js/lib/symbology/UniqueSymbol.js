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
 
 
var UniqueSymbol = function(featureType, symbologyUtils) {
	this.count = 0;
	this.selected = null;
	this.featureType = featureType;
	this.symbologyUtils = symbologyUtils;
	this.rule = new Rule(this.count, featureType);
};

UniqueSymbol.prototype.getRule = function() {
	return this.rule;
};

UniqueSymbol.prototype.appendSymbolizer = function() {
	var self = this;
	
	var symbolizer = null;
	if (this.featureType == 'PointSymbolizer') {
		symbolizer = new PointSymbolizer(this.count, this.rule);
		
	} else if (this.featureType == 'LineSymbolizer') {
		symbolizer = new LineSymbolizer(this.count, this.rule);
		
	} else if (this.featureType == 'PolygonSymbolizer') {
		symbolizer = new PolygonSymbolizer(this.count, this.rule);
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
	
	this.count++;
	self.setSelected(symbolizer);
	this.updateForm();
};

UniqueSymbol.prototype.appendLabel = function() {
	var self = this;
	
	var label = new TextSymbolizer(this.count, this.symbologyUtils, this.rule);
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
	
	this.count++;
	self.setSelected(label);
	this.updateForm();
};

UniqueSymbol.prototype.setSelected = function(element) {
	this.selected = element;
};

UniqueSymbol.prototype.loadSymbols = function(symbolizers) {
	$("#table-symbolizers-body").empty();
	this.symbols.splice(0, this.symbols.length);
	for (var i=0; i<symbolizers.length; i++) {
		var symbolizer = JSON.parse(symbolizers[i].json);
		this.loadSymbol(symbolizer, symbolizers[i].type);
	}
};

UniqueSymbol.prototype.loadSymbol = function(symbolizer, featureType) {
	var self = this;
	
	this.featureType = featureType;
	
	var symbol = symbolizer;
	
	var ui = '';
	ui += '<tr data-rowid="' + symbol.id + '">';
	ui += 	'<td>'
	ui += 		'<span class="handle"> ';
	ui += 			'<i class="fa fa-ellipsis-v"></i>';
	ui += 			'<i class="fa fa-ellipsis-v"></i>';
	ui += 		'</span>';
	ui += 	'</td>';
	ui += 	'<td><a class="symbol-link" data-symid="' + symbol.id + '" href="javascript:void(0)">' + symbol.name + '</a></td>';
	ui += 	'<td id="symbolizer-preview"><svg id="symbolizer-preview-' + symbol.id + '" class="preview-svg"></svg></td>';	
	ui += 	'<td><a class="delete-symbol-link" data-symid="' + symbol.id + '" href="javascript:void(0)"><i class="fa fa-times" style="color: #ff0000;"></i></a></td>';
	ui += '</tr>';	
	$('#table-symbolizers tbody').append(ui);
	
	$("#table-symbolizers-body").sortable({
		placeholder: "sort-highlight",
		handle: ".handle",
		forcePlaceholderSize: true,
		zIndex: 999999
	});
	$("#table-symbolizers-body").on("sortupdate", function(event, ui){
		var rows = ui.item[0].parentNode.children;
		for(var i=0; i < rows.length; i++) {
			var symbol = self.getSymbolById(rows[i].dataset.rowid);
			symbol.order = i;
			console.log(symbol.name + ' -> ' + symbol.order);
		}		
	});
	
	$(".symbol-link").on('click', function(e){	
		e.preventDefault();
		self.setSelected(self.getSymbolById(this.dataset.symid));
		self.updateForm();
	});
	
	$(".delete-symbol-link").one('click', function(e){	
		e.preventDefault();
		self.deleteSymbol(this.dataset.symid);
	});
	
	symbol.preview = this.renderSymbolPreview(symbol);
	
	this.symbols.push(symbol);
	this.count++;
	self.setSelected(symbol);
	this.updateForm();
};

UniqueSymbol.prototype.createPreview = function(rid,symbolizers) {
	
	$("#symbolizer-preview-" + rid).empty();
	var previewElement = Snap("#symbolizer-preview-" + rid);
	var previewGroup = previewElement.g();
	
	for (var i=0; i<symbolizers.length; i++) {
		var symbolizer = JSON.parse(symbolizers[i].json);
		var preview = this.addSymbolizer(previewElement, symbolizer, symbolizers[i].type);
		previewGroup.add(preview);
	}
};

UniqueSymbol.prototype.addSymbolizer = function(previewElement, symbol, stype) {
	
	var attributes = {
		fill: symbol.fill_color,
		fillOpacity: parseFloat(symbol.fill_opacity),
		stroke: symbol.border_color,
		strokeOpacity: symbol.border_opacity,
		strokeWidth: symbol.border_size
	}
	if (symbol.border_type == 'dotted') {
		attributes.strokeDasharray= "1 1";
	} else if (symbol.border_type == 'stripped') {
		attributes.strokeDasharray= "4 4";
	}
	
	var preview = null;
	if (stype == 'PointSymbolizer') {
		if (symbol.shape == 'circle') {
			preview = previewElement.circle(10, 10, 10);
			preview.attr(attributes);
			
		} else if (symbol.shape == 'square') {
			preview = previewElement.polygon(0, 0, 20, 0, 20, 20, 0, 20);
			preview.attr(attributes);
			
		} else if (symbol.shape == 'triangle') {
			preview = previewElement.path('M 12.462757,7.4046606 -2.6621031,7.3865562 4.9160059,-5.7029049 z');
			preview.transform( 't5,8');
			preview.attr(attributes);
			
		}  else if (symbol.shape == 'star') {
			preview = previewElement.path('M 7.0268739,7.8907968 2.2616542,5.5298295 -2.3847299,8.1168351 -1.6118504,2.8552628 -5.5080506,-0.76428228 -0.2651651,-1.6551455 1.9732348,-6.479153 4.4406368,-1.7681645 9.7202441,-1.13002 6.0022969,2.6723943 z');
			preview.transform( 't8,9');
			preview.attr(attributes);
			
		} else if (symbol.shape == 'cross') {
			preview = previewElement.path('M 7.875 0.53125 L 7.875 7.40625 L 0.59375 7.40625 L 0.59375 11.3125 L 7.875 11.3125 L 7.875 19.46875 L 11.78125 19.46875 L 11.78125 11.28125 L 19.5625 11.28125 L 19.53125 7.375 L 11.78125 7.375 L 11.78125 0.53125 L 7.875 0.53125 z');
			preview.transform( 't0,0');
			preview.attr(attributes);
			
		} else if (symbol.shape == 'x') {
			preview = previewElement.path('M 4.34375 0.90625 L 0.90625 3.5 L 6.90625 9.9375 L 0.78125 15.53125 L 3.34375 19.03125 L 9.84375 13.09375 L 15.53125 19.15625 L 19 16.5625 L 13.03125 10.1875 L 19.1875 4.5625 L 16.625 1.09375 L 10.09375 7.03125 L 4.34375 0.90625 z');
			preview.transform( 't0,0');
			preview.attr(attributes);
			
		}
		
		
	} else if (stype == 'LineSymbolizer') {
		preview = previewElement.line(0, 0, 20, 20);
		preview.attr(attributes);
		
	} else if (stype == 'PolygonSymbolizer') {
		preview = previewElement.polygon(0, 0, 20, 0, 20, 20, 0, 20);
		preview.attr(attributes);
	}
	return preview;
};

UniqueSymbol.prototype.updateForm = function() {
	$('#tab-menu').empty();
	$('#tab-content').empty();	
	
	$('#tab-menu').append(this.selected.getTabMenu());
	if (this.selected.type == 'PointSymbolizer' && this.selected.is_vector) {
		$('#tab-content').append(this.selected.getFillTabUI());
		$('#tab-content').append(this.selected.getBorderTabUI());
		$('#tab-content').append(this.selected.getRotationTabUI());		
		$('.nav-tabs a[href="#fill-tab"]').tab('show');
		this.registerSymbolizerEvents();
		
	} else if (this.selected.type == 'PointSymbolizer' && !this.selected.is_vector) {
		$('#tab-content').append(this.newSymbolGraphicTab("active"));			
		$('.nav-tabs a[href="#graphic-tab"]').tab('show');
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
	
	$('input[type=radio][name=symbol-is-vectorial]').change(function() {
        if (this.value == 'vectorial') {
        	self.selected.vectorial = true;
        	self.updateForm();
        	$("#symbolizer-preview").append('<td id="symbolizer-preview"><svg id="symbolizer-preview-' + self.selected.id + '" class="preview-svg"></svg></td>');
    		self.selected.updatePreview();
            
        } else if (this.value == 'external-graphic') {
        	self.selected.vectorial = false;
        	self.updateForm();
        	$("#symbolizer-preview").empty();
    		//self.selected.preview = self.renderExternalGraphicPreview(self.selected);
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
		url: "/gvsigonline/symbology/unique_symbol_save/" + layerId + "/",
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