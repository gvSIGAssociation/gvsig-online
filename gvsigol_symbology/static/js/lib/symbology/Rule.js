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
 
 
var Rule = function(id, featureType, rule_opts) {
	this.id = id;
	this.type = featureType;
	this.name = $("#style-name").val();
	this.title = gettext('Rule') + ' ' + id;
	this.filter = '';
	this.minscale = -1;
	this.maxscale = -1;
	this.order = 0;
	this.symbolizers = new Array();
	this.labels = new Array();
	
	if (rule_opts) {
		this.name = rule_opts.name;
		this.title = rule_opts.title;
		//this.createUI();
//		if (rule_opts.symbolizers != "") {
//			this.loadSymbolizers(rule_opts.symbolizers);
//		}		
		
	} else {
		//this.createUI();
	}
	
};

Rule.prototype.createUI = function() {
	var ui = '';
	ui += '<tr data-rowid="' + this.id + '">';
	ui += 	'<td><span id="rule-name" class="text-muted">' + this.name + '</span></td>';
	ui += 	'<td><span id="rule-title" class="text-muted">' + this.title + '</span></td>';
	ui += 	'<td id="rule-preview"><svg id="rule-preview-' + this.id + '" class="preview-svg"></svg></td>';	
	//ui += 	'<td><a class="edit-rule-link" data-ruleid="' + this.id + '" href="javascript:void(0)"><i class="fa fa-edit text-primary"></i></a></td>';
	ui += '</tr>';	
	
	$('#table-rules tbody').append(ui);
};

Rule.prototype.loadSymbolizers = function(json_symbolizers) {
	var self = this;
	for (var i=0; i<json_symbolizers.length; i++) {
		var symbolizer_object = JSON.parse(json_symbolizers[i].json);
		var symbolizer = null;
		if (symbolizer_object.type == 'PointSymbolizer') {
			symbolizer = new PointSymbolizer(this.getNextSymbolizerId(), this, symbolizer_object);
			$('#table-symbolizers tbody').append(symbolizer.getTableUI());
			this.appendSymbolizer(symbolizer);
			symbolizer.updatePreview();
			
		} else if (symbolizer_object.type == 'LineSymbolizer') {
			symbolizer = new LineSymbolizer(this.getNextSymbolizerId(), this, symbolizer_object);
			$('#table-symbolizers tbody').append(symbolizer.getTableUI());
			this.appendSymbolizer(symbolizer);
			symbolizer.updatePreview();
			
		} else if (symbolizer_object.type == 'PolygonSymbolizer') {
			symbolizer = new PolygonSymbolizer(this.getNextSymbolizerId(), this, symbolizer_object);
			$('#table-symbolizers tbody').append(symbolizer.getTableUI());
			this.appendSymbolizer(symbolizer);
			symbolizer.updatePreview();
			
		} else if (symbolizer_object.type == 'TextSymbolizer') {
			symbolizer = new TextSymbolizer(this.getNextLabelId(), this, symbolizer_object);
			$('#table-symbolizers tbody').append(symbolizer.getTableUI());
			this.appendLabel(symbolizer);
			symbolizer.updatePreview();
		}
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

Rule.prototype.getNextSymbolizerId = function() {
	return this.symbolizers.length;
};

Rule.prototype.getNextLabelId = function() {
	return this.labels.length;
};

Rule.prototype.getSymbolizers = function() {
	return this.symbolizers;
};

Rule.prototype.getLabels = function() {
	return this.labels;
};

Rule.prototype.appendSymbolizer = function(symbolizer) {
	this.symbolizers.push(symbolizer);
};

Rule.prototype.appendLabel = function(label) {
	this.labels.push(label);
};

Rule.prototype.getSymbolizerById = function(id) {
	for (var i=0; i < this.symbolizers.length; i++) {
		if (this.symbolizers[i].id == id) {
			return this.symbolizers[i];
		}
	}
};

Rule.prototype.getLabelById = function(id) {
	for (var i=0; i < this.labels.length; i++) {
		if (this.labels[i].id == id) {
			return this.labels[i];
		}
	}
};

Rule.prototype.removeSymbolizer = function(id) {
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
	//this.updatePreview();
};

Rule.prototype.removeAllSymbolizers = function(id) {
	this.symbolizers.splice(0, this.symbolizers.length);
};

Rule.prototype.removeAllLabels = function(id) {
	this.labels.splice(0, this.labels.length);
};

Rule.prototype.removeLabel = function(id) {
	for (var i=0; i < this.labels.length; i++) {
		if (this.labels[i].id == id) {
			this.labels.splice(i, 1);
		}
	}
	var tbody = document.getElementById('table-symbolizers-body');
	for (var i=0; i<tbody.children.length; i++) {
		if(tbody.children[i].dataset.rowid == id) {
			tbody.removeChild(tbody.children[i]);
		}
	}
	//this.updatePreview();
};

Rule.prototype.updatePreview = function() {
	
	$("#rule-preview-" + this.id).empty();
	var previewElement = Snap("#rule-preview-" + this.id);
	var previewGroup = previewElement.g();
	
	for (var i=0; i<this.symbolizers.length; i++) {
		var preview = this.addSymbolizer(previewElement, this.symbolizers[i], this.symbolizers[i].type);
		previewGroup.add(preview);
	}
};

Rule.prototype.addSymbolizer = function(previewElement, symbolizer, stype) {
	
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
			preview = previewElement.circle(10, 10, 10);
			preview.attr(attributes);
			
		} else if (symbolizer.shape == 'square') {
			preview = previewElement.polygon(0, 0, 20, 0, 20, 20, 0, 20);
			preview.attr(attributes);
			
		} else if (symbolizer.shape == 'triangle') {
			preview = previewElement.path('M 12.462757,7.4046606 -2.6621031,7.3865562 4.9160059,-5.7029049 z');
			preview.transform( 't5,8');
			preview.attr(attributes);
			
		}  else if (symbolizer.shape == 'star') {
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