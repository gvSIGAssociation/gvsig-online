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
 
 
var Rule = function(id, name, title, options, utils) {
	this.id = id;
	this.name = name;
	this.title = title;
	this.abstract = "";
	this.filter = "";
	this.minscale = -1;
	this.maxscale = -1;
	this.order = 0;
	this.symbolizers = new Array();
	this.entries = new Array();
	this.label = null;
	this.utils = utils;
	this.selected = null;
	this.selectedCME = null;
	
	if (options) {
		this.id = options.id;
		this.name = options.name;
		this.title = options.title;
		this.abstract = "";
		this.filter = "";
		this.minscale = parseInt(options.minscale);
		this.maxscale = parseInt(options.maxscale);
		this.order = parseInt(options.order);
	}
	
};

Rule.prototype.getTableUI = function(allowImport, type) {
	var self = this;
	
	var ui = '';
	
	ui += '<div data-ruleid="' + this.id + '" class="col-md-12">';
	if(type == 'unique') {
		ui += 	'<div class="box box-primary">';
	} else {
		ui += 	'<div class="box box-primary collapsed-box">';
	}
	ui += 		'<div class="box-header with-border">';
	ui += 			'<div class="rule-preview" id="rule-preview-' + this.id + '"></div>';
	ui += 				'<h3 id="rule-title-' + this.id + '" class="box-title">' + this.title + '</h3>';
	if(type != 'unique') {
		ui += 			'<div class="box-tools pull-right">';
		ui += 				'<button class="btn btn-box-tool btn-box-tool-custom" data-widget="collapse">';
		ui += 					'<i class="fa fa-plus"></i>';
		ui += 				'</button>';
		ui += 				'<div class="btn-group">';
		ui += 					'<button style="color:#3c8dbc;" data-toggle="dropdown" class="btn btn-box-tool btn-box-tool-custom dropdown-toggle">';
		ui += 						'<i class="fa fa-wrench"></i>';
		ui += 					'</button>';
		ui += 					'<ul class="dropdown-menu" role="menu">';
		ui += 						'<li><a href="#" id="edit-rule-' + this.id + '" data-ruleid="' + this.id + '"><i class="fa fa-edit m-r-5"></i> ' + gettext('Edit rule') + '</a></li>';
		if(type == 'expressions') {
			ui += 					'<li><a href="#" class="create-expression" id="create-expression-' + this.id + '" data-ruleid="' + this.id + '"><i class="fa fa-filter m-r-5"></i> ' + gettext('Edit filter') + '</a></li>';
			
		}
		ui += 					'</ul>';
		ui += 				'</div>';
		ui += 				'<button data-ruleid="' + this.id + '" style="color:#f56954;" class="btn btn-box-tool btn-box-tool-custom delete-rule">';
		ui += 					'<i class="fa fa-times"></i>';
		ui += 				'</button>';
		ui += 			'</div>';
	}
	ui += 			'</div>';
	ui += 			'<div class="box-body">';
	ui += 				'<div class="table-responsive">';
	ui += 					'<table id="rule-' + this.id + '-symbolizers" class="table no-margin">';
	ui += 						'<thead>';
	ui += 							'<tr>';
	ui += 								'<th></th>';
	ui += 								'<th>' + gettext('Preview') + '</th>';
	ui +=	 							'<th></th>';											
	ui += 							'</tr>';
	ui += 						'</thead>';
	ui += 						'<tbody id="table-symbolizers-body-' + this.id + '"></tbody>';
	ui += 					'</table>';
	ui += 				'</div>';
	ui += 			'</div>';
	ui += 			'<div class="box-footer clearfix">';
	ui += 				'<a id="append-symbol-button-' + this.id + '" href="javascript:void(0)" class="btn btn-sm btn-default btn-flat pull-right margin-r-5"><i class="fa fa-star-o margin-r-5"></i>' + gettext('Append symbolizer') + '</a>';
	if (allowImport){
		ui += 			'<a id="import-symbol-button-' + this.id + '" href="" class="btn btn-sm btn-default btn-flat pull-right margin-r-5"><i class="fa fa-download margin-r-5"></i>' + gettext('Import from library') + '</a>';
	}
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

Rule.prototype.getColorMapEntryUI = function() {
	var self = this;
	
	var ui = '';
	
	ui += '<div data-ruleid="' + this.id + '" class="col-md-12">';
	ui += 	'<div class="box box-primary">';
	ui += 		'<div class="box-header with-border">';
	ui += 			'<div class="rule-preview" id="rule-preview-' + this.id + '"></div>';
	ui += 				'<h3 id="rule-title-' + this.id + '" class="box-title">' + this.title + '</h3>';
	ui += 				'<div class="box-tools pull-right">';
	ui += 					'<button data-ruleid="' + this.id + '" style="color:#f56954;" class="btn btn-box-tool btn-box-tool-custom delete-rule">';
	ui += 						'<i class="fa fa-times"></i>';
	ui += 					'</button>';
	ui += 				'</div>';
	ui += 			'</div>';
	ui += 			'<div class="box-body">';
	ui += 				'<div class="table-responsive">';
	ui += 					'<table id="rule-' + this.id + '-symbolizers" class="table no-margin">';
	ui += 						'<thead>';
	ui += 							'<tr>';
	ui += 								'<th></th>';
	ui += 								'<th>' + gettext('Color') + '</th>';
	ui += 								'<th>' + gettext('Quantity') + '</th>';
	ui += 								'<th>' + gettext('Label') + '</th>';
	ui += 								'<th>' + gettext('Opacity') + '</th>';
	ui +=	 							'<th></th>';											
	ui += 							'</tr>';
	ui += 						'</thead>';
	ui += 						'<tbody id="table-entries-body-' + this.id + '"></tbody>';
	ui += 					'</table>';
	ui += 				'</div>';
	ui += 			'</div>';
	ui += 			'<div class="box-footer clearfix">';
	ui += 				'<a id="append-color-entry-button-' + this.id + '" href="javascript:void(0)" class="btn btn-sm btn-default btn-flat pull-right margin-r-5"><i class="fa fa-tint margin-r-5"></i>' + gettext('Append color map entry') + '</a>';
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

Rule.prototype.registerEvents = function() {
	var self = this;
	
	$("#edit-rule-" + this.id).on('click', function(e){
		var ui = '';
		ui += '<div class="box">';
		ui += 	'<div class="box-body">';
		ui += 		'<div class="row">';
		ui += 			'<div class="col-md-12 form-group">';
		ui += 				'<label>' + gettext('Rule name') + '</label>';
		ui += 				'<input id="r-name-' + self.id + '" type="text" value="' + self.name + '" class="form-control">';
		ui += 			'</div>';
		ui += 			'<div class="col-md-12 form-group">';
		ui += 				'<label>' + gettext('Rule title') + '</label>';
		ui += 				'<input id="r-title-' + self.id + '" type="text" value="' + self.title + '" class="form-control">';
		ui += 			'</div>';
		ui += 		'</div>';
		ui += 	'</div>';
		ui += 	'<div class="box-footer clearfix">';
		ui += 		'<button id="save-rule-metadata-' + self.id + '" class="btn btn-sm btn-success btn-flat pull-right margin-r-5">';
		ui += 			'<i class="fa fa-floppy-o margin-r-5"></i>' + gettext('Save');
		ui += 		'</button>';
		ui += 	'</div>';
		ui += '</div>';
		
		$('#modal-edit-rule-content').empty();
		$('#modal-edit-rule-content').append(ui);
		
		$("#save-rule-metadata-" + self.id).on('click', function(e){
			var name = $("#r-name-" + self.id).val();
			var title = $("#r-title-" + self.id).val();
			self.name = name;
			self.title = title;
			
			$('#rule-title-' + self.id).text(title);
			
			$('#modal-edit-rule').modal('hide');
		});
		
		$('#modal-edit-rule').modal('show');
	});
	
	$("#append-symbol-button-" + this.id).on('click', function(e){
		self.addSymbolizer();
	});
	
	$("#append-color-entry-button-" + this.id).on('click', function(e){
		self.addColorMapEntry();
	});
	
	$("#import-symbol-button-" + this.id).on('click', function(e){
		e.preventDefault();
		$('#modal-import-symbol').modal('show');
		
		$(".users-list").empty();
		var libraryId = $("#select-library").val();
		if (libraryId) {
			self.getSymbolsFromLibrary(libraryId);
		}
		
		$("#select-library").on('change', function(e) {
			$(".users-list").empty();
			self.getSymbolsFromLibrary(this.value);
		});
	});
	
	
};

Rule.prototype.registerCMEEvents = function() {
	var self = this;
	
	$("#append-color-entry-button-" + this.id).on('click', function(e){
		self.addColorMapEntry();
	});
	
};

Rule.prototype.preview = function() {
	this.symbolizers.sort(function(a, b){
		return parseInt(b.order) - parseInt(a.order);
	});
	
	var sldBody = this.utils.getSLDBody(this.symbolizers);
	var url = this.utils.getPreviewUrl() + '&SLD_BODY=' + encodeURIComponent(sldBody);
	var ui = '<img id="rule-preview-img" src="' + url + '" class="rule-preview"></img>';
	$("#rule-preview-" + this.id).empty();
	$("#rule-preview-" + this.id).append(ui);
};

Rule.prototype.previewRaster = function() {
	var ui = '<img id="rule-preview-img" src="' + IMG_PATH + 'raster.png" class="rule-preview"></img>';
		
	$("#rule-preview-" + this.id).empty();
	$("#rule-preview-" + this.id).append(ui);
};

Rule.prototype.libraryPreview = function(rid,json_symbolizers) {
	var symbolizers = new Array();
	for (var i=0; i<json_symbolizers.length; i++) {
		var json = JSON.parse(json_symbolizers[i].json);
		var type = json_symbolizers[i].type;
		var options = json[0].fields;
		var symbolizer = null;
		if (type == 'MarkSymbolizer') {
			symbolizer = new MarkSymbolizer(this.rule, options, this.utils);
			
		} else if (type == 'LineSymbolizer') {
			symbolizer = new LineSymbolizer(this.rule, options, this.utils);
			
		} else if (type == 'PolygonSymbolizer') {
			symbolizer = new PolygonSymbolizer(this.rule, options, this.utils);
			
		}
		symbolizers.push(symbolizer);
	}
	symbolizers.sort(function(a, b){
		return parseInt(b.order) - parseInt(a.order);
	});
	
	var sldBody = this.utils.getSLDBody(symbolizers);
	var url = this.utils.getPreviewUrl() + '&SLD_BODY=' + encodeURIComponent(sldBody);
	var ui = '<img id="rule-preview-img" src="' + url + '" class="rule-preview"></img>';
	$("#library-symbol-preview-div-" + rid).empty();
	$("#library-symbol-preview-div-" + rid).append(ui);
};


Rule.prototype.getSymbolsFromLibrary = function(libraryId) {
	var self = this;
	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/get_symbols_from_library/",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		data: {
			library_id: libraryId
		},
		success: function(response){
			var symbols = response.rules;
			
			for (var i=0; i<symbols.length; i++) {
				
				var symbol = symbols[i];
				
				var symbolizers = symbol.symbolizers;
				
				var symbolView = '';				
				if (symbolizers[0].type == 'ExternalGraphicSymbolizer') {
					var graphic = JSON.parse(symbolizers[0].json);
					symbolView += '<li>';
					symbolView += 	'<img style="height: ' + graphic[0].fields.size + 'px; width: auto;" src="' + graphic[0].fields.online_resource + '" class="preview-eg"></img>';
					symbolView += 	'<a class="users-list-name" data-rid="' + response.rules[i].id + '" href="">' + response.rules[i].name + '</a>';
					symbolView += '</li>';
					$(".users-list").append(symbolView);
					
				} else {
					symbolView += '<li>';
					symbolView += 	'<div id="library-symbol-preview-div-' + response.rules[i].id + '"></div>';
					symbolView += 	'<a class="users-list-name" data-rid="' + response.rules[i].id + '" href="">' + response.rules[i].name + '</a>';
					symbolView += '</li>';
					$(".users-list").append(symbolView);
					self.libraryPreview(symbol.id, symbolizers);
				}
				$(".users-list-name").on('click', function(e){
					e.preventDefault();
					for (var j=0; j<symbols.length; j++) {
						if (symbols[j].id == this.dataset.rid) {
							if (symbols[j].symbolizers[0].type == self.utils.getFeatureType() || 
								(symbols[j].symbolizers[0].type == 'ExternalGraphicSymbolizer' && self.utils.getFeatureType() == 'PointSymbolizer') || 
									(symbols[j].symbolizers[0].type == 'MarkSymbolizer' && self.utils.getFeatureType() == 'PointSymbolizer')) {
								
								self.loadLibrarySymbol(symbols[j].symbolizers);
								
							} else {
								messageBox.show('warning', gettext('Selected symbol is not compatible with the layer'));
								
							}						
						}
					}	
					$('#modal-import-symbol').modal('hide');
				});
			}
		},
	    error: function(){}
	});
};


Rule.prototype.loadLibrarySymbol = function(symbolizers) {
	
	$("#table-symbolizers-body-" + this.id).empty();
	this.removeAllSymbolizers();
	this.removeLabel();
	
	for (var i=0; i<symbolizers.length; i++) {
		
		var symbolizer = JSON.parse(symbolizers[i].json);
		var order = symbolizers[i].order;
		var options = symbolizer[0].fields;
		options['order'] = order;
		
		if (symbolizer[0].model == 'gvsigol_symbology.externalgraphicsymbolizer') {
			this.addExternalGraphicSymbolizer(options);
			
		} else {
			this.addSymbolizer(options);
		}	
		
	}
	this.preview();
};

Rule.prototype.addSymbolizer = function(options) {
	var self = this;
	
	var symbolizer = null;
	if (this.utils.getFeatureType() == 'PointSymbolizer') {
		symbolizer = new MarkSymbolizer(this, options, this.utils);
		
	} else if (this.utils.getFeatureType() == 'LineSymbolizer') {
		symbolizer = new LineSymbolizer(this, options, this.utils);
		
	} else if (this.utils.getFeatureType() == 'PolygonSymbolizer') {
		symbolizer = new PolygonSymbolizer(this, options, this.utils);
	}
	
	$('#rule-' + this.id + '-symbolizers tbody').append(symbolizer.getTableUI());
	
	$('#rule-' + this.id + '-symbolizers tbody').sortable({
		placeholder: "sort-highlight",
		handle: ".handle",
		forcePlaceholderSize: true,
		zIndex: 999999
	});
	
	$('#rule-' + this.id + '-symbolizers tbody').on("sortupdate", function(event, ui){			
		var rows = ui.item[0].parentNode.children;
		for(var i=0; i < rows.length; i++) {
			var symbol = self.getSymbolizerById(rows[i].dataset.rowid);
			if (symbol) {
				symbol.order = i;
			}
		}
		self.preview();
	});
	
	$(".edit-symbolizer-link-" + this.id).on('click', function(e){	
		e.preventDefault();
		self.setSelected(self.getSymbolizerById(this.dataset.symbolizerid));
		self.updateForm();
		$('#modal-symbolizer').modal('show');
	});
	
	$(".delete-symbolizer-link-" + this.id).on('click', function(e){	
		e.preventDefault();
		self.removeSymbolizer(this.dataset.symbolizerid);
	});
	
	this.symbolizers.push(symbolizer);
	symbolizer.updatePreview();
	this.preview();
};

Rule.prototype.addExternalGraphicSymbolizer = function(options) {
	var self = this;
	
	var symbolizer = new ExternalGraphicSymbolizer(options.name, options.format, options.size, options.online_resource);
	
	$('#rule-' + this.id + '-symbolizers tbody').append(symbolizer.getTableUI());	
	$('#rule-' + this.id + '-symbolizers tbody').sortable({
		placeholder: "sort-highlight",
		handle: ".handle",
		forcePlaceholderSize: true,
		zIndex: 999999
	});
	$('#rule-' + this.id + '-symbolizers tbody').on("sortupdate", function(event, ui){});
	
	$(".edit-eg-link").on('click', function(e){	
		e.preventDefault();
		messageBox.show('warning', gettext('Image symbols can only be edited from the library'));
	});
	$(".delete-symbolizer-link").one('click', function(e){	
		e.preventDefault();
		self.removeSymbolizer(this.dataset.symbolizerid);
	});
	
	this.symbolizers.push(symbolizer);
};

Rule.prototype.addColorMapEntry = function(options) {
	var self = this;
	
	var colorMapEntry = new ColorMapEntry(this, options, this.utils);
	
	$('#rule-' + this.id + '-symbolizers tbody').append(colorMapEntry.getTableUI());
	
	$('#rule-' + this.id + '-symbolizers tbody').sortable({
		placeholder: "sort-highlight",
		handle: ".handle",
		forcePlaceholderSize: true,
		zIndex: 999999
	});
	
	$('#rule-' + this.id + '-symbolizers tbody').on("sortupdate", function(event, ui){			
		var rows = ui.item[0].parentNode.children;
		for(var i=0; i < rows.length; i++) {
			var cme = self.getCMEById(rows[i].dataset.rowid);
			if (cme) {
				cme.order = i;
			}
		}
	});
	
	$(".edit-color-map-entry-link-" + this.id).on('click', function(e){	
		e.preventDefault();
		self.setSelectedCME(self.getCMEById(this.dataset.colormapentryid));
		self.updateCMEForm();
		$('#modal-color-map-entry').modal('show');
	});
	$(".delete-color-map-entry-link-" + this.id).one('click', function(e){	
		e.preventDefault();
		self.removeColorMapEntry(this.dataset.colormapentryid);
	});
	
	colorMapEntry.updatePreview();
	this.entries.push(colorMapEntry);
};

Rule.prototype.setLabel = function(label) {
	this.label = label;
};

Rule.prototype.getLabel = function() {
	return this.label;
};

Rule.prototype.setSelected = function(symbolizer) {
	this.selected = symbolizer;
};

Rule.prototype.setSelectedCME = function(cme) {
	this.selectedCME = cme;
};

Rule.prototype.updateForm = function() {
	$('#tab-menu').empty();
	$('#tab-content').empty();	
	
	$('#tab-menu').append(this.selected.getTabMenu());
	if (this.selected.type == 'MarkSymbolizer') {
		$('#tab-content').append(this.selected.getGraphicTabUI());
		$('#tab-content').append(this.selected.getFillTabUI());
		$('#tab-content').append(this.selected.getStrokeTabUI());
		$('#tab-content').append(this.selected.getRotationTabUI());		
		$('.nav-tabs a[href="#graphic-tab"]').tab('show');
		this.selected.registerEvents();
		
	} else if (this.selected.type == 'ExternalGraphicSymbolizer') {
		this.selected.registerEvents();
		
	} else if (this.selected.type == 'LineSymbolizer') {
		$('#tab-content').append(this.selected.getStrokeTabUI());
		$('.nav-tabs a[href="#stroke-tab"]').tab('show');
		this.selected.registerEvents();
		
	} else if (this.selected.type == 'PolygonSymbolizer') {
		$('#tab-content').append(this.selected.getFillTabUI());
		$('#tab-content').append(this.selected.getStrokeTabUI());
		$('.nav-tabs a[href="#fill-tab"]').tab('show');
		this.selected.registerEvents();
		
	} else if (this.selected.type == 'TextSymbolizer') {
		$('#tab-content').append(this.selected.getFontTabUI());
		$('#tab-content').append(this.selected.getHaloTabUI());
		$('.nav-tabs a[href="#label-font-tab"]').tab('show');
		this.selected.registerEvents();
	}
};

Rule.prototype.updateCMEForm = function() {
	$('#tab-menu').empty();
	$('#tab-content').empty();	
	
	$('#tab-menu').append(this.selectedCME.getTabMenu());
	$('#tab-content').append(this.selectedCME.getColorMapEntryTabUI());

	this.selectedCME.registerEvents();
};

Rule.prototype.getNextSymbolizerId = function() {
	return this.symbolizers.length;
};

Rule.prototype.getSymbolizers = function() {
	return this.symbolizers;
};

Rule.prototype.getEntries = function() {
	return this.entries;
};


Rule.prototype.getSymbolizerById = function(id) {
	for (var i=0; i < this.symbolizers.length; i++) {
		if (this.symbolizers[i].id == id) {
			return this.symbolizers[i];
		}
	}
};

Rule.prototype.getCMEById = function(id) {
	for (var i=0; i < this.entries.length; i++) {
		if (this.entries[i].id == id) {
			return this.entries[i];
		}
	}
};

Rule.prototype.removeSymbolizer = function(id) {
	for (var i=0; i < this.symbolizers.length; i++) {
		if (this.symbolizers[i].id == id) {
			this.symbolizers.splice(i, 1);
		}
	}
	var tbody = document.getElementById('table-symbolizers-body-' + this.id);
	for (var i=0; i<tbody.children.length; i++) {
		if(tbody.children[i].dataset.rowid == id) {
			tbody.removeChild(tbody.children[i]);
		}
	}
	this.preview();
};

Rule.prototype.removeColorMapEntry = function(id) {
	for (var i=0; i < this.entries.length; i++) {
		if (this.entries[i].id == id) {
			this.entries.splice(i, 1);
		}
	}
	var tbody = document.getElementById('table-entries-body-' + this.id);
	for (var i=0; i<tbody.children.length; i++) {
		if(tbody.children[i].dataset.rowid == id) {
			tbody.removeChild(tbody.children[i]);
		}
	}
};

Rule.prototype.removeAllSymbolizers = function(id) {
	this.symbolizers.splice(0, this.symbolizers.length);
	this.preview();
};

Rule.prototype.removeAllEntries = function(id) {
	this.entries.splice(0, this.entries.length);
};

Rule.prototype.removeLabel = function() {
	this.label = null;
};

Rule.prototype.getObject = function() {
	var object = {
		id: this.id,
		name: this.name,
		title: this.title,
		abstract: '',
		filter: this.filter,
		minscale: this.minscale,
		maxscale: this.maxscale,
		order: this.order
	};
	return object;
};

Rule.prototype.setFilter = function(filter) {
	this.filter = filter;
};