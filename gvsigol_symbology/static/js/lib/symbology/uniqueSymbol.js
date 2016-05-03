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
 
 
var UniqueSymbol = function(featureType, fields, sldFilterValues) {
	this.featureType = featureType;
	this.fields = fields;
	this.sldFilterValues = sldFilterValues;
};

UniqueSymbol.prototype.count = 0;

UniqueSymbol.prototype.rules = new Array();
UniqueSymbol.prototype.graphics = new Array();
UniqueSymbol.prototype.labels = new Array();

UniqueSymbol.prototype.selected = null;


UniqueSymbol.prototype.appendRule = function() {
	var self = this;
	
	var rule = {
		id: this.count,
		type: 'rule',
		name: "rule " + this.count,
		preview: null,
		fill_color: "#000000",
		fill_opacity: 0.5,
		with_border: true,
		border_color: "#000000",
		border_size: 1,
		border_opacity: 1,
		rotation: 0,
		geometry_function: "",
		geometry_field: ""
	};
	
	var ui = '';
	ui += '<tr data-rowid="' + rule.id + '">';
	ui += 	'<td><a class="rule-link" data-rid="' + rule.id + '" href="javascript:void(0)">' + rule.name + '</a></td>';
	ui += 	'<td><svg id="rule-preview-' + rule.id + '" class="preview-svg"></svg></td>';	
	ui += 	'<td><a class="delete-rule-link" data-rid="' + rule.id + '" href="javascript:void(0)"><i class="fa fa-times" style="color: #ff0000;"></i></a></td>';
	ui += '</tr>';	
	$('#table-unique-symbol tbody').append(ui);
	
	$(".rule-link").on('click', function(e){	
		e.preventDefault();
		self.selected = self.getRuleById(this.dataset.rid);
		self.updateForm();
	});
	
	$(".delete-rule-link").one('click', function(e){	
		e.preventDefault();
		self.deleteRule(this.dataset.rid);
	});
	
	rule.preview = this.renderPreview(rule);
	
	this.rules.push(rule);
	this.count++;
	this.selected = rule;
	this.updateForm();
	
	return rule;
};

UniqueSymbol.prototype.appendGraphic = function() {
	var self = this;
	
	var graphic = {
		id: this.count,
		type: 'graphic',
		name: "graphic " + this.count,
		preview: null
	};
	
	var ui = '';
	ui += '<tr data-rowid="' + graphic.id + '">';
	ui += 	'<td><a class="graphic-link" data-gid="' + graphic.id + '" href="javascript:void(0)">' + graphic.name + '</a></td>';
	ui += 	'<td><img id="graphic-preview-' + graphic.id + '" class="" /></td>';	
	ui += 	'<td><a class="delete-graphic-link" data-gid="' + graphic.id + '" href="javascript:void(0)"><i class="fa fa-times" style="color: #ff0000;"></i></a></td>';
	ui += '</tr>';	
	$('#table-unique-symbol tbody').append(ui);
	
	$(".graphic-link").on('click', function(e){	
		e.preventDefault();
		self.selected = self.getGraphicById(this.dataset.gid);
		self.updateForm();
	});
	
	$(".delete-graphic-link").one('click', function(e){	
		e.preventDefault();
		self.deleteGraphic(this.dataset.gid);
	});
	
	//graphic.preview = this.renderPreview(rule);
	
	this.graphics.push(graphic);
	this.count++;
	this.selected = graphic;
	this.updateForm();
	
	return graphic;
};

UniqueSymbol.prototype.appendLabel = function() {
	var self = this;
	
	var label = {
		id: this.count,
		type: 'label',
		name: "label " + this.count,
		preview: null
	};
	
	var ui = '';
	ui += '<tr data-rowid="' + label.id + '">';
	ui += 	'<td><a class="label-link" data-lid="' + label.id + '" href="javascript:void(0)">' + label.name + '</a></td>';
	ui += 	'<td><img id="label-preview-' + label.id + '" class="" /></td>';	
	ui += 	'<td><a class="delete-label-link" data-lid="' + label.id + '" href="javascript:void(0)"><i class="fa fa-times" style="color: #ff0000;"></i></a></td>';
	ui += '</tr>';	
	$('#table-unique-symbol tbody').append(ui);
	
	$(".label-link").on('click', function(e){	
		e.preventDefault();
		self.selected = self.getLabelById(this.dataset.lid);
		self.updateForm();
	});
	
	$(".delete-label-link").one('click', function(e){	
		e.preventDefault();
		self.deleteLabel(this.dataset.lid);
	});
	
	//graphic.preview = this.renderPreview(rule);
	
	this.labels.push(label);
	this.count++;
	this.selected = label;
	this.updateForm();
	
	return label;
};

UniqueSymbol.prototype.deleteRule = function(id) {
	for (var i=0; i < this.rules.length; i++) {
		if (this.rules[i].id == id) {
			this.rules.splice(i, 1);
		}
	}
	var tbody = document.getElementById('table-unique-symbol-body');
	for (var i=0; i<tbody.children.length; i++) {
		if(tbody.children[i].dataset.rowid == id) {
			tbody.removeChild(tbody.children[i]);
		}
	}
	if (this.rules.length >= 1) {
		this.selected = this.rules[0];
		this.updateForm();
	} else {
		$('#tab-content').empty();
		$('#tab-menu').empty();
	}
};

UniqueSymbol.prototype.deleteGraphic = function(id) {
	for (var i=0; i < this.graphics.length; i++) {
		if (this.graphics[i].id == id) {
			this.graphics.splice(i, 1);
		}
	}
	var tbody = document.getElementById('table-unique-symbol-body');
	for (var i=0; i<tbody.children.length; i++) {
		if(tbody.children[i].dataset.rowid == id) {
			tbody.removeChild(tbody.children[i]);
		}
	}
	if (this.graphics.length >= 1) {
		this.selected = this.graphics[0];
		this.updateForm();
	} else {
		$('#tab-content').empty();
		$('#tab-menu').empty();
	}
};

UniqueSymbol.prototype.deleteLabel = function(id) {
	for (var i=0; i < this.labels.length; i++) {
		if (this.labels[i].id == id) {
			this.labels.splice(i, 1);
		}
	}
	var tbody = document.getElementById('table-unique-symbol-body');
	for (var i=0; i<tbody.children.length; i++) {
		if(tbody.children[i].dataset.rowid == id) {
			tbody.removeChild(tbody.children[i]);
		}
	}
	if (this.labels.length >= 1) {
		this.selected = this.labels[0];
		this.updateForm();
	} else {
		$('#tab-content').empty();
		$('#tab-menu').empty();
	}
};

UniqueSymbol.prototype.getSelected = function() {
	return this.selected;
};

UniqueSymbol.prototype.getRuleById = function(id) {
	var rule = null;
	for (var i=0; i < this.rules.length; i++) {
		if (this.rules[i].id == id) {
			rule = this.rules[i];
		}
	}
	return rule;
};

UniqueSymbol.prototype.getGraphicById = function(id) {
	var graphic = null;
	for (var i=0; i < this.graphics.length; i++) {
		if (this.graphics[i].id == id) {
			rule = this.graphics[i];
		}
	}
	return graphic;
};

UniqueSymbol.prototype.getLabelById = function(id) {
	var label = null;
	for (var i=0; i < this.labels.length; i++) {
		if (this.labels[i].id == id) {
			label = this.labels[i];
		}
	}
	return label;
};

UniqueSymbol.prototype.renderPreview = function(rule) {
	
	var attributes = {
		fill: rule.fill_color,
		fillOpacity: parseFloat(rule.fill_opacity),
		stroke: rule.border_color,
		strokeOpacity: rule.border_opacity,
		strokeWidth: rule.border_size
	}
	
	var preview = null;
	var previewElement = Snap("#rule-preview-" + rule.id);
	if (this.featureType == 'PointSymbolizer') {
		preview = previewElement.circle(10, 10, 10);
		preview.attr(attributes);
		
	} else if (this.featureType == 'LineSymbolizer') {
		preview = previewElement.line(0, 0, 20, 20);
		preview.attr(attributes);
		
	} else if (this.featureType == 'PolygonSymbolizer') {
		preview = previewElement.polygon(0, 0, 20, 0, 20, 20, 0, 20);
		preview.attr(attributes);
	}
	return preview;
};

UniqueSymbol.prototype.updateForm = function() {
	$('#tab-menu').empty();
	$('#tab-content').empty();	
	
	if (this.selected.type == 'rule') {
		$('#tab-menu').append(this.newRuleTabMenu());
		$('#tab-content').append(this.newRuleFillTab());
		$('#tab-content').append(this.newRuleBorderTab());
		$('#tab-content').append(this.newRuleRotationTab());
		$('#tab-content').append(this.newRuleGeometryTab());
		this.registerRuleEvents();
		$('.nav-tabs a[href="#fill-tab"]').tab('show');
		
	} else if (this.selected.type == 'graphic') {
		
	} else if (this.selected.type == 'label') {
	
	}
};

UniqueSymbol.prototype.registerRuleEvents = function() {
	var self = this;
	
	$( "#fill-opacity-slider" ).slider({
	    min: 0,
	    max: 100,
	    value: 100,
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.selected.fill_opacity = opacity;
			self.selected.preview = self.renderPreview(self.selected);
	    }
	});	
	$("#fill-color-chooser").on('change', function(e) {
		self.selected.fill_color = this.value;
		self.selected.preview = self.renderPreview(self.selected);		
	});	
	$("#border-color-chooser").on('change', function(e) {
		self.selected.border_color = this.value;
		self.selected.preview = self.renderPreview(self.selected);		
	});
	$( "#border-opacity-slider" ).slider({
	    min: 0,
	    max: 100,
	    value: 100,
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.selected.border_opacity = opacity;
			self.selected.preview = self.renderPreview(self.selected);
	    }
	});
	$("#border-size").on('change', function(e) {
		self.selected.border_size = this.value;
		self.selected.preview = self.renderPreview(self.selected);		
	});
};

UniqueSymbol.prototype.newRuleTabMenu = function() {
	var ui = '';
	ui += '<li class="active"><a href="#fill-tab" data-toggle="tab">' + gettext('Fill') + '</a></li>';
	ui += '<li><a href="#border-tab" data-toggle="tab">' + gettext('Border') + '</a></li>';
	ui += '<li><a href="#rotation-tab" data-toggle="tab">' + gettext('Rotation') + '</a></li>'; 
	ui += '<li><a href="#geometry-tab" data-toggle="tab">' + gettext('Geometry') + '</a></li>';
	
	return ui;	
};

UniqueSymbol.prototype.newRuleFillTab = function() {
	var ui = '';
	ui += '<div class="tab-pane active" id="fill-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Fill color') + '</label>';
	ui += 			'<input id="fill-color-chooser" type="color" value="' + this.selected.fill_color + '" class="form-control color-chooser">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label style="display: block;">' + gettext('Fill opacity') + ' (%)</label>';
	ui += 			'<div id="fill-opacity-slider"><div/>';
	ui += 		'</div>';				 
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
	
};

UniqueSymbol.prototype.newRuleBorderTab = function() {
	var ui = '';
	ui += '<div class="tab-pane" id="border-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 checkbox">';
	ui += 			'<label>';
	ui += 				'<input type="checkbox" name="usergroup-{{group.id}}" id="usergroup-{{group.id}}"/>' + gettext('With border');
	ui += 			'</label>';	
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Border color') + '</label>';
	ui += 				'<input type="color" value="' + this.selected.border_color + '" class="form-control color-chooser">';					
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Border size') + '</label>';
	ui += 			'<input id="border-size" type="number" class="form-control" value="' + parseInt(this.selected.border_size) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label style="display: block;">' + gettext('Border opacity') + ' (%)</label>';
	ui += 			'<div id="border-opacity-slider"><div/>';
	ui += 		'</div>';					 
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

UniqueSymbol.prototype.newRuleRotationTab = function() {
	var ui = '';
	ui += '<div class="tab-pane" id="rotation-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label style="display: block;">' + gettext('Rotation') + ' (Degrees)</label>';
	ui += 			'<div id="rotation-slider"><div/>';
	ui += 		'</div>';			 
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

UniqueSymbol.prototype.newRuleGeometryTab = function() {
	var ui = '';
	ui += '<div class="tab-pane" id="geometry-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="form-group">';
	ui += 			'<label>' + gettext('Function') + '</label>';
	ui += 			'<select class="form-control">';
	for (var key in this.sldFilterValues) {
		ui += 			'<option value"' + this.sldFilterValues[key] + '">' + this.sldFilterValues[key] + '</option>';
	}
	ui += 			'</select>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="form-group">';
	ui += 			'<label>' + gettext('Geometry field') + '</label>';
	ui += 			'<select class="form-control">';
	for (var i=0; i < this.fields.length; i++) {
		ui += 			'<option value"' + this.fields[i].name + '">' + this.fields[i].name + '</option>';
	}	
	ui += 			'</select>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};
