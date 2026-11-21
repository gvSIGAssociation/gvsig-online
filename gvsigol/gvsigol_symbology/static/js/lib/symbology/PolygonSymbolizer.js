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
 
 
var PolygonSymbolizer = function(rule, options, utils) {
	this.id = 'polygonsymbolizer' + utils.generateUUID();
	this.fill = "#000000";
	this.fill_opacity = 0.5;
	this.stroke = "#000000";
	this.stroke_width = 1;
	this.stroke_opacity = 1;
	this.stroke_dash_array = 'none';
	this.order = 0;
	this.rule = rule;
	this.utils = utils;
	
	if (options) {
		$.extend(this, options);
	} else {
		if(rule && rule.symbolizers){
			this.order = rule.symbolizers.length;
		}
	}
	this.type = 'PolygonSymbolizer';
	// opciones avanzadas (campo options del servidor); ver SymbolOptionsEditor.js
	SymbolOptions.init(this);
};

PolygonSymbolizer.prototype.getTableUI = function() {
	var ui = '';
	ui += '<tr data-rowid="' + this.id + '">';
	ui += 	'<td>'
	ui += 		'<span class="handle"> ';
	ui += 			'<i class="fa fa-ellipsis-v"></i>';
	ui += 			'<i class="fa fa-ellipsis-v"></i>';
	ui += 		'</span>';
	ui += 	'</td>';
	ui += 	'<td id="symbolizer-preview-div-' + this.id + '"></td>';
	ui += 	'<td><a class="edit-symbolizer-link-' + this.rule.id + '" data-symbolizerid="' + this.id + '" href="javascript:void(0)"><i class="fa fa-edit text-primary"></i></a></td>';
	ui += 	'<td><a class="delete-symbolizer-link-' + this.rule.id + '" data-symbolizerid="' + this.id + '" href="javascript:void(0)"><i class="fa fa-times text-danger"></i></a></td>';
	ui += '</tr>';	
	
	return ui;
};

PolygonSymbolizer.prototype.getTabMenu = function() {
	var ui = '';
	ui += '<li class="active"><a href="#fill-tab" data-toggle="tab">' + gettext('Fill') + '</a></li>';
	ui += '<li><a href="#stroke-tab" data-toggle="tab">' + gettext('Stroke') + '</a></li>';
	
	return ui;	
};

PolygonSymbolizer.prototype.getFillTabUI = function() {
	var o = this.symbolOptions;
	var hatch = o.fill.hatch || {pattern: 'slash', color: '#000000', width: 1, spacing: 10, background: true};
	var types = [['solid', symoptT('Solid'), symoptT('Solid')], ['hatch', symoptT('Hatch'), symoptT('Hatch')],
		['none', symoptT('No fill'), symoptT('No fill')]];
	var patterns = $.map(SymbolOptions.HATCHES, function(h) { return [[h[0], SymbolOptions.hatchSvg(h[0]), symoptT(h[1])]]; });
	var ui = '<div class="tab-pane active gol-symopt-pane" id="fill-tab">';
	ui += SymbolOptions.ui.choice('opt:fill.type', symoptT('Fill type'), types, o.fill.type, 'gol-symopt-segmented');
	ui += '<div data-symopt-show="opt:fill.type=hatch">';
	ui += SymbolOptions.ui.choice('opt:fill.hatch.pattern', symoptT('Pattern'), patterns, hatch.pattern, 'gol-symopt-hatches');
	ui += SymbolOptions.ui.row(
		SymbolOptions.ui.color('hatch-color', 'opt:fill.hatch.color', symoptT('Pattern color'), hatch.color),
		SymbolOptions.ui.number('hatch-width', 'opt:fill.hatch.width', symoptT('Line width'), hatch.width, 0.25, 10, 0.25, 'px'),
		SymbolOptions.ui.number('hatch-spacing', 'opt:fill.hatch.spacing', symoptT('Spacing'), hatch.spacing, 2, 100, 1, 'px'));
	ui += SymbolOptions.ui.toggle('hatch-background', 'opt:fill.hatch.background', symoptT('Background color under the pattern'), hatch.background);
	ui += '</div>';
	ui += SymbolOptions.ui.row(
		SymbolOptions.ui.color('fill-color-chooser', 'col:fill', gettext('Fill color'), this.fill, 'opt:fill.type=solid'),
		SymbolOptions.ui.opacity('fill-opacity', 'col:fill_opacity', gettext('Fill opacity'), this.fill_opacity, 'opt:fill.type=solid'));
	ui += SymbolOptions.ui.row(
		SymbolOptions.ui.color('fill-bg-color', 'col:fill', symoptT('Background color'), this.fill, 'opt:fill.hatch.background'),
		SymbolOptions.ui.opacity('fill-bg-opacity', 'col:fill_opacity', symoptT('Background opacity'), this.fill_opacity, 'opt:fill.hatch.background'));
	ui += '</div>';
	return ui;
};

PolygonSymbolizer.prototype.getStrokeTabUI = function() {
	var o = this.symbolOptions;
	var ui = '<div class="tab-pane gol-symopt-pane" id="stroke-tab">';
	ui += SymbolOptions.ui.row(
		SymbolOptions.ui.color('stroke-color-chooser', 'col:stroke', gettext('Stroke color'), this.stroke),
		SymbolOptions.ui.number('stroke-width', 'col:stroke_width', gettext('Stroke width'), this.stroke_width, 0, 50, 0.5, 'px'),
		SymbolOptions.ui.opacity('stroke-opacity', 'col:stroke_opacity', gettext('Stroke opacity'), this.stroke_opacity));
	ui += SymbolOptions.ui.dashChoice('stroke-dash-custom', this.stroke_dash_array);
	ui += SymbolOptions.ui.capJoin('opt:stroke', o.stroke);
	ui += SymbolOptions.ui.row(
		SymbolOptions.ui.number('stroke-dash-offset', 'opt:stroke.dash_offset', symoptT('Dash offset'), o.stroke.dash_offset, 0, 1000, 1, 'px', '!col:stroke_dash_array=none'));
	ui += '</div>';
	return ui;
};

PolygonSymbolizer.prototype.afterChoice = function(path, value) {
	// con trama sin fondo no hay color de relleno que mostrar; con «sin relleno», tampoco
	if (path === 'opt:fill.type' && value === 'hatch' && !this.symbolOptions.fill.hatch) {
		this.symbolOptions.fill.hatch = {pattern: 'slash', color: '#000000', width: 1, spacing: 10, background: true};
	}
};

PolygonSymbolizer.prototype.registerEvents = function() {
	var self = this;
	SymbolOptions.openDialog();
	SymbolOptions.bind(this, function() {
		self.updatePreview();
		self.rule.preview();
		SymbolOptions.livePreview(self);
	});
	SymbolOptions.livePreview(this);
};

PolygonSymbolizer.prototype.updatePreview = function() {	
	var url;
	if (SymbolOptions.needed(this)) {
		// símbolo avanzado: la vista previa la genera el servidor con el SLD que se publica
		url = SymbolOptions.previewUrl(this.utils.getPreviewUrl(), [this]);
	} else {
		var sldBody = this.toSLDBody();
		if (sldBody == null) {
			return;
		}
		url = this.utils.getPreviewUrl() + '&SLD_BODY=' + encodeURIComponent(sldBody);
	}
	var ui = '<img id="symbolizer-preview-' + this.id + '" src="' + url + '" class="symbolizer-preview-' + this.id + '"></img>';
	$("#symbolizer-preview-div-" + this.id).empty();
	$("#symbolizer-preview-div-" + this.id).append(ui);
};

PolygonSymbolizer.prototype.toSLDBody = function(){
	
	var sld = '';
	sld += '<StyledLayerDescriptor version=\"1.0.0\" xmlns=\"http://www.opengis.net/sld\" xmlns:ogc=\"http://www.opengis.net/ogc\" ';
	sld +=  'xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" ';
	sld +=  'xsi:schemaLocation=\"http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd\">';
	sld += 	'<NamedLayer>';  
	sld +=  	'<Name>polygon</Name>';  
	sld +=      '<UserStyle>';
	sld +=          '<Name>polygon</Name>';
	sld +=          '<Title>polygon</Title>';
	sld +=          '<FeatureTypeStyle>';
	sld +=          	'<Rule>';
	sld +=          		'<Name>polygon</Name>';
	sld +=          		'<Title>polygon</Title>';
	sld += 					'<PolygonSymbolizer>';
	sld += 						'<Fill>';
	sld += 							'<CssParameter name="fill">' + this.fill + '</CssParameter>';
	sld += 							'<CssParameter name="fill-opacity">' + this.fill_opacity + '</CssParameter>';
	sld += 						'</Fill>';
	sld += 						'<Stroke>';
	sld += 							'<CssParameter name="stroke">' + this.stroke + '</CssParameter>';
	sld += 							'<CssParameter name="stroke-width">' + this.stroke_width + '</CssParameter>';
	sld += 							'<CssParameter name="stroke-opacity">' + this.stroke_opacity + '</CssParameter>';
	if (this.stroke_dash_array != 'none') {
		sld += '<CssParameter name="stroke-dasharray">' + this.stroke_dash_array + '</CssParameter>;'
	}
	sld += 						'</Stroke>';
	sld += 					'</PolygonSymbolizer>';
	sld +=          	'</Rule>';
	sld +=          '</FeatureTypeStyle>';
	sld +=      '</UserStyle>';
	sld += 	'</NamedLayer>';
	sld += '</StyledLayerDescriptor>';
	
	return sld;
};

PolygonSymbolizer.prototype.toXML = function(){
	
	var xml = '';
	xml += '<PolygonSymbolizer>';
	xml += 	'<Fill>';
	xml += 		'<CssParameter name="fill">' + this.fill + '</CssParameter>';
	xml += 		'<CssParameter name="fill-opacity">' + this.fill_opacity + '</CssParameter>';
	xml += 	'</Fill>';
	xml += 	'<Stroke>';
	xml += 		'<CssParameter name="stroke">' + this.stroke + '</CssParameter>';
	xml += 		'<CssParameter name="stroke-width">' + this.stroke_width + '</CssParameter>';
	xml += 		'<CssParameter name="stroke-opacity">' + this.stroke_opacity + '</CssParameter>';
	if (this.stroke_dash_array != 'none') {
		xml += '<CssParameter name="stroke-dasharray">' + this.stroke_dash_array + '</CssParameter>;'
	}
	xml += 	'</Stroke>';
	xml += '</PolygonSymbolizer>';
	
	return xml;
};

PolygonSymbolizer.prototype.toJSON = function(){
	
	var object = {
		id: this.id,
		type: this.type,
		fill: this.fill,
		fill_opacity: this.fill_opacity,
		stroke: this.stroke,
		stroke_width: this.stroke_width,
		stroke_opacity: this.stroke_opacity,
		stroke_dash_array: this.stroke_dash_array,
		// solo si usa algo que el simbolizador clásico no puede expresar (si no, null)
		options: SymbolOptions.forJSON(this),
		order: this.order
	};
	
	return JSON.stringify(object);
};