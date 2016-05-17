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
 
 
var LibrarySymbol = function(symbologyUtils) {
	this.count = 0;
	this.selected = null;
	this.featureType = null;
	this.symbologyUtils = symbologyUtils;
	this.symbolizers = new Array();
};

LibrarySymbol.prototype.getSymbolizers = function() {
	return this.symbolizers;
};

LibrarySymbol.prototype.loadSymbolizers = function(json_symbolizers) {
	var self = this;
	for (var i=0; i<json_symbolizers.length; i++) {
		var symbolizer_object = JSON.parse(json_symbolizers[i].json);
		var symbolizer = null;
		if (symbolizer_object.type == 'PointSymbolizer') {
			symbolizer = new PointSymbolizer(this.count, this, this.symbologyUtils, symbolizer_object);
			$('#table-symbolizers tbody').append(symbolizer.getTableUI());
			this.symbolizers.push(symbolizer);
			symbolizer.updatePreview();
			
		} else if (symbolizer_object.type == 'LineSymbolizer') {
			symbolizer = new LineSymbolizer(this.count, this, symbolizer_object);
			$('#table-symbolizers tbody').append(symbolizer.getTableUI());
			this.symbolizers.push(symbolizer);
			symbolizer.updatePreview();
			
		} else if (symbolizer_object.type == 'PolygonSymbolizer') {
			symbolizer = new PolygonSymbolizer(this.count, this, symbolizer_object);
			$('#table-symbolizers tbody').append(symbolizer.getTableUI());
			this.symbolizers.push(symbolizer);
			symbolizer.updatePreview();
			
		} else if (symbolizer_object.type == 'TextSymbolizer') {
			symbolizer = new TextSymbolizer(this.count, this, symbolizer_object);
			$('#table-symbolizers tbody').append(symbolizer.getTableUI());
			this.symbolizers.push(symbolizer);
			symbolizer.updatePreview();
		}
		this.count++;
	}
	
	$(".edit-symbolizer-link").on('click', function(e){	
		e.preventDefault();
		self.setSelected(self.getSymbolizerById(this.dataset.symbolizerid));
		self.updateForm();
		$('#modal-symbolizer').modal('show');
	});
	
	$(".delete-symbolizer-link").one('click', function(e){	
		e.preventDefault();
		self.removeSymbolizer(this.dataset.symbolizerid);
	});
};

LibrarySymbol.prototype.appendSymbolizer = function(featureType) {
	var self = this;
	
	this.featureType = featureType;
	
	var symbolizer = null;
	if (this.featureType == 'PointSymbolizer') {
		symbolizer = new PointSymbolizer(this.count, null, this.symbologyUtils);
		
	} else if (this.featureType == 'ExternalGraphicSymbolizer') {
		symbolizer = new ExternalGraphicSymbolizer(this.count, null, this.symbologyUtils);
		
	} else if (this.featureType == 'LineSymbolizer') {
		symbolizer = new LineSymbolizer(this.count, null);
		
	} else if (this.featureType == 'PolygonSymbolizer') {
		symbolizer = new PolygonSymbolizer(this.count, null);
	}
	this.count++;
	
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
		self.setSelected(self.getSymbolizerById(this.dataset.symbolizerid));
		self.updateForm();
		$('#modal-symbolizer').modal('show');
	});
	
	$(".delete-symbolizer-link").one('click', function(e){	
		e.preventDefault();
		self.removeSymbolizer(this.dataset.symbolizerid);
	});
	this.symbolizers.push(symbolizer);
	symbolizer.updatePreview();
	self.updatePreview();
	self.setSelected(symbolizer);
	this.updateForm();
	
};

LibrarySymbol.prototype.setSelected = function(element) {
	this.selected = element;
};

LibrarySymbol.prototype.removeSymbolizer = function(id) {
	for (var i=0; i < this.symbolizers.length; i++) {
		if (this.symbolizers[i].id == id) {
			this.symbolizers.splice(i, 1);
		}
	}
	var tbody = document.getElementById('table-symbolizers-body');
	for (var i=0; i<tbody.children.length; i++) {
		if(tbody.children[i].dataset.rowid == id) {
			tbody.removeChild(tbody.children[i]);
		}
	}
};

LibrarySymbol.prototype.getSymbolizerById = function(id) {
	var symbolizer = null;
	for (var i=0; i < this.symbolizers.length; i++) {
		if (this.symbolizers[i].id == id) {
			symbolizer = this.symbolizers[i];
		}
	}
	return symbolizer;
};

LibrarySymbol.prototype.loadSymbols = function(symbolizers) {
	for (var i=0; i<symbolizers.length; i++) {
		var symbolizer = JSON.parse(symbolizers[i].json);
		this.loadSymbol(symbolizer, symbolizers[i].type);
	}
};

LibrarySymbol.prototype.loadSymbol = function(symbolizer, featureType) {
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
	$('#table-unique-symbol tbody').append(ui);
	
	$("#table-unique-symbol-body").sortable({
		placeholder: "sort-highlight",
		handle: ".handle",
		forcePlaceholderSize: true,
		zIndex: 999999
	});
	$("#table-unique-symbol-body").on("sortupdate", function(event, ui){
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

LibrarySymbol.prototype.updatePreview = function() {
	for (var i=0; i<this.symbolizers.length; i++) {
		if (this.symbolizers[i].type == 'ExternalGraphicSymbolizer') {
			
		} else {
			$("#library-symbol-preview-svg").empty();
			var previewElement = Snap("#library-symbol-preview-svg");
			var previewGroup = previewElement.g();
			var preview = this.addSymbolizerToPreview(previewElement, this.symbolizers[i], this.symbolizers[i].type);
			previewGroup.add(preview);
		}
		
	}
};

LibrarySymbol.prototype.loadSymbols = function(rid,symbolizers) {
	
	$("#symbolizer-preview-" + rid).empty();
	var previewElement = Snap("#symbolizer-preview-" + rid);
	var previewGroup = previewElement.g();
	
	var max = 20;
	for (var i=0; i<symbolizers.length; i++) {
		var symbolizer = JSON.parse(symbolizers[i].json);
		var preview = this.addSymbolizerToPreview(previewElement, symbolizer, symbolizers[i].type);
		previewGroup.add(preview);
	}
	
	$('.preview-svg-' + rid).css("height",max+"px");
	$('.preview-svg-' + rid).css("width",max+"px");
};

LibrarySymbol.prototype.addSymbolizerToPreview = function(previewElement, symbolizer, stype) {
	
	var attributes = {
		fill: symbolizer.fill_color,
		fillOpacity: parseFloat(symbolizer.fill_opacity),
		stroke: symbolizer.border_color,
		strokeOpacity: symbolizer.border_opacity,
		strokeWidth: symbolizer.border_size
	}
	if (symbolizer.border_type == 'dotted') {
		attributes.strokeDasharray= "1 1";
	} else if (symbolizer.border_type == 'stripped') {
		attributes.strokeDasharray= "4 4";
	}
	
	var preview = null;
	if (stype == 'PointSymbolizer') {
		if (symbolizer.shape == 'circle') {
			preview = previewElement.circle(symbolizer.size/2, symbolizer.size/2, symbolizer.size/2);
			preview.attr(attributes);
			
		} else if (symbolizer.shape == 'square') {
			preview = previewElement.polygon(0, 0, symbolizer.size, 0, symbolizer.size, symbolizer.size, 0, symbolizer.size);
			preview.attr(attributes);
			
		} else if (symbolizer.shape == 'triangle') {
			var matrix = new Snap.Matrix();
			matrix.rotate(180, symbolizer.size, symbolizer.size);
			preview = previewElement.polygon(0, 0, symbolizer.size, 0, symbolizer.size/2, symbolizer.size);
			preview.transform(matrix);
			preview.attr(attributes);
			
		}/*  else if (symbolizer.shape == 'star') {
			preview = previewElement.path('M 7.0268739,7.8907968 2.2616542,5.5298295 -2.3847299,8.1168351 -1.6118504,2.8552628 -5.5080506,-0.76428228 -0.2651651,-1.6551455 1.9732348,-6.479153 4.4406368,-1.7681645 9.7202441,-1.13002 6.0022969,2.6723943 z');
			preview.transform( 't8,9');
			preview.attr(attributes);
			
		} else if (symbolizer.shape == 'cross') {
			preview = previewElement.path('M 7.875 0.53125 L 7.875 7.40625 L 0.59375 7.40625 L 0.59375 11.3125 L 7.875 11.3125 L 7.875 19.46875 L 11.78125 19.46875 L 11.78125 11.28125 L 19.5625 11.28125 L 19.53125 7.375 L 11.78125 7.375 L 11.78125 0.53125 L 7.875 0.53125 z');
			preview.transform( 't0,0');
			preview.attr(attributes);
			
		} else if (symbolizer.shape == 'x') {
			preview = previewElement.path('M 4.34375 0.90625 L 0.90625 3.5 L 6.90625 9.9375 L 0.78125 15.53125 L 3.34375 19.03125 L 9.84375 13.09375 L 15.53125 19.15625 L 19 16.5625 L 13.03125 10.1875 L 19.1875 4.5625 L 16.625 1.09375 L 10.09375 7.03125 L 4.34375 0.90625 z');
			preview.transform( 't0,0');
			preview.attr(attributes);
			
		}*/
			
	} else if (stype == 'LineSymbolizer') {
		preview = previewElement.line(0, 0, 30, 30);
		preview.attr(attributes);
		
	} else if (stype == 'PolygonSymbolizer') {
		preview = previewElement.polygon(0, 0, 30, 0, 30, 30, 0, 30);
		preview.attr(attributes);
	}
	
	return preview;
};


LibrarySymbol.prototype.updateForm = function() {
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
		$('#tab-content').append(this.selected.getGraphicTabUI());
		this.selected.registerExternalGraphicEvents();
		
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
		
	}
};

LibrarySymbol.prototype.registerSymbolizerEvents = function() {
	var self = this;
	$("#graphic-size").on('change', function(e) {
		self.selected.size = this.value;
		self.selected.updatePreview();	
		self.updatePreview();
	});
	$('input[type=radio][name=symbol-is-vectorial]').change(function() {
        if (this.value == 'vectorial') {
        	self.selected.vectorial = true;
        	self.updateForm();
        	$("#symbolizer-preview").append('<td id="symbolizer-preview"><svg id="symbolizer-preview-' + self.selected.id + '" class="preview-svg"></svg></td>');
        	self.selected.updatePreview();
        	self.updatePreview();
            
        } else if (this.value == 'external-graphic') {
        	self.selected.vectorial = false;
        	self.updateForm();
        	$("#symbolizer-preview").empty();
        }
    });
	$("#shape").on('change', function(e) {
		self.selected.shape = this.value;
		self.selected.updatePreview();	
		self.updatePreview();
	});
	$( "#fill-opacity-slider" ).slider({
	    min: 0,
	    max: 100,
	    value: (self.selected.fill_opacity * 100),
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.selected.fill_opacity = opacity;
	    	self.selected.updatePreview();
	    	self.updatePreview();
	    },
	    slide: function( event, ui ) {
	    	$("#fill-opacity-output").text(ui.value + '%');
	    }
	});	
	$("#fill-color-chooser").on('change', function(e) {
		self.selected.fill_color = this.value;
		self.selected.updatePreview();	
		self.updatePreview();
	});	
	$('#symbol-with-border').on('change', function() {
		self.selected.with_border = this.checked;		
		self.selected.updatePreview();
		self.updatePreview();
	});
	$("#border-color-chooser").on('change', function(e) {
		self.selected.border_color = this.value;
		self.selected.updatePreview();	
		self.updatePreview();
	});
	$( "#border-opacity-slider" ).slider({
	    min: 0,
	    max: 100,
	    value: (self.selected.border_opacity * 100),
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.selected.border_opacity = opacity;
	    	self.selected.updatePreview();
	    	self.updatePreview();
	    },
	    slide: function( event, ui ) {
	    	$("#border-opacity-output").text(ui.value + '%');
	    }
	});
	$("#border-size").on('change', function(e) {
		self.selected.border_size = this.value;
		self.selected.updatePreview();	
		self.updatePreview();
	});
	$('#border-type').on('change', function() {
		self.selected.border_type = this.value;
		self.selected.updatePreview();
		self.updatePreview();
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

LibrarySymbol.prototype.save = function(libraryid, name, title, filter) {
	
	var elements = new Array();
	for (var i=0; i < this.symbolizers.length; i++) {
		var symbolizer = {
			type: this.symbolizers[i].type,
			sld: this.symbolizers[i].toXML(),
			json: this.symbolizers[i].toJSON(),
			order: this.symbolizers[i].order
		};
		elements.push(symbolizer);
	}
	
	var symbol = {
		name: name,
		title: title,
		filter: filter,
		symbolizers: elements
	};
	
	$.ajax({
		type: "POST",
		async: false,
		//contentType: false,
	    enctype: 'multipart/form-data',
		url: "/gvsigonline/symbology/symbol_add/" + libraryid + "/" + this.featureType + "/",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		data: {
			file: $("#eg-file")[0],
			rule: JSON.stringify(symbol)
		},
		success: function(response){
			if (response.success) {
				location.href = "/gvsigonline/symbology/library_update/" + libraryid + "/";
			} else {
				$("#form-error").append('<p>*' + response.message + '</p>');
			}
			
		},
	    error: function(){}
	});
};

LibrarySymbol.prototype.update = function(id, name, title, filter) {
	
	var elements = new Array();
	for (var i=0; i < this.symbolizers.length; i++) {
		var symbolizer = {
			type: this.symbolizers[i].type,
			sld: this.symbolizers[i].toXML(),
			json: this.symbolizers[i].toJSON(),
			order: this.symbolizers[i].order
		};
		elements.push(symbolizer);
	}
	
	var symbol = {
		name: name,
		title: title,
		filter: filter,
		symbolizers: elements
	};
	
	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/symbol_update/" + id + "/",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		data: {
			rule: JSON.stringify(symbol)
		},
		success: function(response){
			if (response.success) {
				location.href = "/gvsigonline/symbology/library_update/" + response.library_id + "/";
			} else {
				$("#form-error").append('<p>*' + response.message + '</p>');
			}
			
		},
	    error: function(){}
	});
};