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
		this.id = rule_opts.id;
		this.name = rule_opts.name;
		this.title = rule_opts.title;	
		this.minscale = parseInt(rule_opts.minscale);
		this.maxscale = parseInt(rule_opts.maxscale);
		this.order = parseInt(rule_opts.order);
	}
	
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
	$('#append-label-button').css('display', 'block');
};