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
 * @author: Javi Rodrigo <jrodrigo@scolab.es>
 */

var SymbologyUtils = function(map, layer, fonts, alphanumericFields) {
	this.map = map;
	this.layer = layer;
	this.fonts = fonts;
	this.alphanumericFields = alphanumericFields;
};

SymbologyUtils.prototype.fontStyles = [
	{value: 'normal', title: gettext('Normal')},
	{value: 'cursive', title: gettext('Cursive')},
	{value: 'oblique',title: gettext('Oblique')}
];

SymbologyUtils.prototype.fontWeights = [
	{value: 'normal', title: gettext('Normal')},
	{value: 'bold', title: gettext('Bold')}
];

SymbologyUtils.prototype.shapes = [
	{value: 'circle', title: gettext('Circle')},
	{value: 'square', title: gettext('Square')},
	{value: 'triangle', title: gettext('Triangle')}/*,
	{value: 'star', title: gettext('Star')},
	{value: 'cross', title: gettext('Cross')},
	{value: 'x', title: 'X'}*/
];

SymbologyUtils.prototype.external_graphic_formats = [
	{value: 'image/png', title: 'image/png'},
	{value: 'image/jpeg', title: 'image/jpeg'},
	{value: 'image/gif', title: 'image/gif'}
];

SymbologyUtils.prototype.getFonts = function(element){
	return this.fonts;
};

SymbologyUtils.prototype.getFontStyles = function(element){
	return this.fontStyles;
};

SymbologyUtils.prototype.getFontWeights = function(element){
	return this.fontWeights;
};

SymbologyUtils.prototype.getShapes = function(element){
	return this.shapes;
};

SymbologyUtils.prototype.getAlphanumericFields = function(element){
	return this.alphanumericFields;
};

SymbologyUtils.prototype.updateMap = function(rule) {
	var self = this;
	var symbolizers = new Array();
	for (var i=0; i < rule.getSymbolizers().length; i++) {
		var symbolizer = {
			type: rule.getSymbolizers()[i].type,
			sld: rule.getSymbolizers()[i].toXML(),
			json: rule.getSymbolizers()[i].toJSON(),
			order: rule.getSymbolizers()[i].order
		};
		symbolizers.push(symbolizer);
	}
	
	for (var i=0; i < rule.getLabels().length; i++) {
		var label = {
			type: rule.getLabels()[i].type,
			sld: rule.getLabels()[i].toXML(),
			json: rule.getLabels()[i].toJSON(),
			order: rule.getLabels()[i].order
		};
		symbolizers.push(label);
	}
	rule['rule_symbolizers'] = symbolizers
	var data = {
		name: $('#style-name').val(),
		title: $('#style-title').val(),
		rules: [rule]
	}
	
	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/get_sld_body/",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		data: {
			style_data: JSON.stringify(data)
		},
		success: function(response){
			self.reloadLayerPreview(response.sld_body);		
		},
	    error: function(){}
	});
};

SymbologyUtils.prototype.reloadLayerPreview = function(sld_body){
	var layers = this.map.getLayers();
	var self = this;
	layers.forEach(function(layer){
		if (!layer.baselayer) {
			if (layer.get("id") === 'preview-layer') {
				layer.getSource().updateParams({'SLD_BODY': sld_body, STYLES: undefined});
				self.map.render();
			}
		};
	}, this);
};