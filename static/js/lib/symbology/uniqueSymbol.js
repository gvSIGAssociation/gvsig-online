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
 * @author: José Badía <jbadia@scolab.es>
 */
 
 
var UniqueSymbol = function(type) {
	this.type = type;
};

UniqueSymbol.prototype.ruleCount = 0;

UniqueSymbol.prototype.rules = new Array();

UniqueSymbol.prototype.selectedRule = null;


UniqueSymbol.prototype.appendRule = function() {
	var self = this;
	
	var rule = {
		id: this.ruleCount,
		name: "rule " + this.ruleCount,
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
	ui += '<tr data-rulerow="' + rule.id + '">';
	ui += 	'<td><a class="rule-link" data-rid="' + rule.id + '" href="javascript:void(0)">' + rule.name + '</a></td>';
	ui += 	'<td><svg id="rule-preview-' + rule.id + '" class="preview-svg"></svg></td>';	
	ui += 	'<td><a class="delete-rule-link" data-rid="' + rule.id + '" href="javascript:void(0)"><i class="fa fa-times" style="color: #ff0000;"></i></a></td>';
	ui += '</tr>';	
	$('#table-rules tbody').append(ui);
	
	$(".rule-link").on('click', function(e){	
		e.preventDefault();
		self.selectedRule = self.getRuleById(this.dataset.rid);
		self.updateForm();
	});
	
	$(".delete-rule-link").one('click', function(e){	
		e.preventDefault();
		self.deleteRule(this.dataset.rid);
	});
	
	rule.preview = this.renderPreview(rule);
	
	this.rules.push(rule);
	this.ruleCount++;
	this.selectedRule = rule;
	this.updateForm();
	
	return rule;
};

UniqueSymbol.prototype.deleteRule = function(rid) {
	for (var i=0; i < this.rules.length; i++) {
		if (this.rules[i].id == rid) {
			this.rules.splice(i, 1);
		}
	}
	var rule = $('#table-rules tbody').find('[data-rulerow="' + rid + '"]')[0];
	$('#table-rules tbody').remove(rule);
};

UniqueSymbol.prototype.getSelectedRule = function() {
	return this.selectedRule;
};

UniqueSymbol.prototype.getRuleById = function(rid) {
	var rule = null;
	for (var i=0; i < this.rules.length; i++) {
		if (this.rules[i].id == rid) {
			rule = this.rules[i];
		}
	}
	return rule;
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
	if (this.type == 'point') {
		preview = previewElement.circle(10, 10, 10);
		preview.attr(attributes);
	}
	return preview;
};

UniqueSymbol.prototype.updateForm = function() {
	$('#tab-content').empty();
	$('#tab-content').append(this.updateFillTab());
	$('#tab-content').append(this.updateBorderTab());
	$('#tab-content').append(this.updateRotationTab());
	$('#tab-content').append(this.updateGeometryTab());

	this.registerEvents();
	
	$('.nav-tabs a[href="#fill-tab"]').tab('show');
};

UniqueSymbol.prototype.registerEvents = function() {
	var self = this;
	
	$( "#fill-opacity-slider" ).slider({
	    min: 0,
	    max: 100,
	    value: 100,
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.selectedRule.fill_opacity = opacity;
			self.selectedRule.preview = self.renderPreview(self.selectedRule);
	    }
	});	
	$("#fill-color-chooser").on('change', function(e) {
		self.selectedRule.fill_color = this.value;
		self.selectedRule.preview = self.renderPreview(self.selectedRule);		
	});	
	$("#border-color-chooser").on('change', function(e) {
		self.selectedRule.border_color = this.value;
		self.selectedRule.preview = self.renderPreview(self.selectedRule);		
	});
	$( "#border-opacity-slider" ).slider({
	    min: 0,
	    max: 100,
	    value: 100,
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.selectedRule.border_opacity = opacity;
			self.selectedRule.preview = self.renderPreview(self.selectedRule);
	    }
	});
	$("#border-size").on('change', function(e) {
		self.selectedRule.border_size = this.value;
		self.selectedRule.preview = self.renderPreview(self.selectedRule);		
	});
};

UniqueSymbol.prototype.updateFillTab = function() {
	var ui = '';
	ui += '<div class="tab-pane active" id="fill-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Fill color') + '</label>';
	ui += 			'<input id="fill-color-chooser" type="color" value="' + this.selectedRule.fill_color + '" class="form-control color-chooser">';					
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

UniqueSymbol.prototype.updateBorderTab = function() {
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
	ui += 				'<input type="color" value="' + this.selectedRule.border_color + '" class="form-control color-chooser">';					
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Border size') + '</label>';
	ui += 			'<input id="border-size" type="number" class="form-control" value="' + parseInt(this.selectedRule.border_size) + '">';					
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

UniqueSymbol.prototype.updateRotationTab = function() {
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

UniqueSymbol.prototype.updateGeometryTab = function() {
	var ui = '';
	ui += '<div class="tab-pane" id="geometry-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="form-group">';
	ui += 			'<label>' + gettext('Function') + '</label>';
	ui += 			'<select class="form-control">';
	ui += 				'<option>option 1</option>';
	ui += 			'</select>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="form-group">';
	ui += 			'<label>' + gettext('Geometry field') + '</label>';
	ui += 			'<select class="form-control">';
	ui += 				'<option>option 1</option>';
	ui += 			'</select>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};
