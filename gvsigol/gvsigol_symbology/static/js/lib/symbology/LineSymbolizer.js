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
 
 
var LineSymbolizer = function(rule, options, utils) {
	this.id = 'linesymbolizer' + utils.generateUUID();
	this.stroke = "#000000";
	this.stroke_width = 1;
	this.stroke_dash_array = 'none';
	this.stroke_opacity = 1;
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
	this.type = 'LineSymbolizer';
	// opciones avanzadas (campo options del servidor); ver SymbolOptionsEditor.js
	SymbolOptions.init(this);
};

LineSymbolizer.prototype.getTableUI = function() {
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

LineSymbolizer.prototype.getTabMenu = function() {
	var ui = '';
	ui += '<li class="active"><a href="#stroke-tab" data-toggle="tab">' + gettext('Stroke') + '</a></li>';
	ui += '<li><a href="#decoration-tab" data-toggle="tab">' + symoptT('Decoration') + '</a></li>';
	
	return ui;	
};

/** Pestañas «Trazo» y «Decoración» (Rule.updateForm solo llama a este método para las líneas). */
LineSymbolizer.prototype.getStrokeTabUI = function() {
	var o = this.symbolOptions;
	var ui = '<div class="tab-pane active gol-symopt-pane" id="stroke-tab">';
	ui += SymbolOptions.ui.toggle('line-enabled', 'opt:line', symoptT('Draw the line'), o.line);
	ui += SymbolOptions.ui.row(
		SymbolOptions.ui.color('stroke-color-chooser', 'col:stroke', gettext('Stroke color'), this.stroke, 'opt:line'),
		SymbolOptions.ui.number('stroke-width', 'col:stroke_width', gettext('Stroke width'), this.stroke_width, 0, 100, 0.5, 'px', 'opt:line'),
		SymbolOptions.ui.opacity('stroke-opacity', 'col:stroke_opacity', gettext('Stroke opacity'), this.stroke_opacity, 'opt:line'));
	ui += '<div data-symopt-show="opt:line">';
	ui += SymbolOptions.ui.dashChoice('stroke-dash-custom', this.stroke_dash_array);
	ui += SymbolOptions.ui.capJoin('opt:stroke', o.stroke);
	ui += SymbolOptions.ui.row(
		SymbolOptions.ui.number('stroke-dash-offset', 'opt:stroke.dash_offset', symoptT('Dash offset'), o.stroke.dash_offset, 0, 1000, 1, 'px', '!col:stroke_dash_array=none'),
		SymbolOptions.ui.number('stroke-offset', 'opt:stroke.offset', symoptT('Side offset'), o.stroke.offset, -100, 100, 0.5, 'px'));
	ui += '<p class="gol-symopt-hint">' + symoptT('Side offset moves the line to the left (positive) or to the right (negative) of its direction, for example to draw parallel lines or the edge of a road.') + '</p>';
	ui += '</div></div>';

	ui += '<div class="tab-pane gol-symopt-pane" id="decoration-tab">';
	ui += SymbolOptions.ui.section(symoptT('Marks along the line'), this.decorationUI('marks', SymbolOptions.ALONG_SHAPES, true));
	ui += SymbolOptions.ui.section(symoptT('Start of the line'), this.decorationUI('start', SymbolOptions.END_SHAPES, false));
	ui += SymbolOptions.ui.section(symoptT('End of the line'), this.decorationUI('end', SymbolOptions.END_SHAPES, false));
	ui += '<p class="gol-symopt-hint">' + symoptT('Marks follow the direction of the line: use them for railways, arrows showing the flow, or boundaries.') + '</p>';
	ui += '</div>';
	return ui;
};

LineSymbolizer.prototype.decorationUI = function(key, shapes, along) {
	var d = this.symbolOptions[key] || SymbolOptions.decoration(shapes[0], along ? 10 : 12, along ? 20 : undefined);
	var path = 'opt:' + key;
	var ui = SymbolOptions.ui.shapeChoice(path + '.shape', symoptT('Shape'), shapes, this.symbolOptions[key] ? d.shape : 'none', true);
	var fields = [
		SymbolOptions.ui.number('deco-' + key + '-size', path + '.size', gettext('Size'), d.size, 1, 100, 0.5, 'px', path),
		SymbolOptions.ui.color('deco-' + key + '-color', path + '.stroke', symoptT('Color'), d.stroke, path),
		SymbolOptions.ui.number('deco-' + key + '-width', path + '.stroke_width', gettext('Stroke width'), d.stroke_width, 0, 20, 0.5, 'px', path)
	];
	if (along) {
		fields.push(SymbolOptions.ui.number('deco-' + key + '-spacing', path + '.spacing', symoptT('Gap between marks'), d.spacing, 1, 1000, 1, 'px', path));
		fields.push(SymbolOptions.ui.number('deco-' + key + '-start', path + '.start', symoptT('Initial offset'), d.start, 0, 1000, 1, 'px', path));
	}
	return ui + SymbolOptions.ui.row.apply(null, fields);
};

LineSymbolizer.prototype.registerEvents = function() {
	var self = this;
	SymbolOptions.openDialog();
	SymbolOptions.bind(this, function() {
		self.updatePreview();
		self.rule.preview();
		SymbolOptions.livePreview(self);
	});
	SymbolOptions.livePreview(this);
};

LineSymbolizer.prototype.updatePreview = function() {	
	var url;
	if (SymbolOptions.needed(this)) {
		// símbolo avanzado: la vista previa la genera el servidor con el SLD que se publica
		url = SymbolOptions.previewUrl(this.utils.getPreviewUrl(), [this]);
	} else {
		url = this.utils.getPreviewUrl() + '&SLD_BODY=' + encodeURIComponent(this.toSLDBody());
	}
	var ui = '<img id="symbolizer-preview-' + this.id + '" src="' + url + '" class="symbolizer-preview-' + this.id + '"></img>';
	$("#symbolizer-preview-div-" + this.id).empty();
	$("#symbolizer-preview-div-" + this.id).append(ui);
};

LineSymbolizer.prototype.toXML = function(){
	
	var xml = '';
	xml += '<LineSymbolizer>';
	xml += 	'<Stroke>';
	xml += 		'<CssParameter name="stroke">' + this.stroke + '</CssParameter>';
	xml += 		'<CssParameter name="stroke-width">' + this.stroke_width + '</CssParameter>';
	xml += 		'<CssParameter name="stroke-opacity">' + this.stroke_opacity + '</CssParameter>';
	if (this.stroke_dash_array != 'none') {
		xml += '<CssParameter name="stroke-dasharray">' + this.stroke_dash_array + '</CssParameter>;'
	}
	xml += 	'</Stroke>';
	xml += '</LineSymbolizer>';
	
	return xml;
};

LineSymbolizer.prototype.toSLDBody = function(){
	
	var sld = '';
	sld += '<StyledLayerDescriptor version=\"1.0.0\" xmlns=\"http://www.opengis.net/sld\" xmlns:ogc=\"http://www.opengis.net/ogc\" ';
	sld +=  'xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" ';
	sld +=  'xsi:schemaLocation=\"http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd\">';
	sld += 	'<NamedLayer>';  
	sld +=  	'<Name>Line</Name>';  
	sld +=      '<UserStyle>';
	sld +=          '<Name>Line</Name>';
	sld +=          '<Title>Line</Title>';
	sld +=          '<FeatureTypeStyle>';
	sld +=          	'<Rule>';
	sld +=          		'<Name>Line</Name>';
	sld +=          		'<Title>Line</Title>';
	sld += 					'<LineSymbolizer>';
	sld += 						'<Stroke>';
	sld += 							'<CssParameter name="stroke">' + this.stroke + '</CssParameter>';
	sld += 							'<CssParameter name="stroke-width">' + this.stroke_width + '</CssParameter>';
	sld += 							'<CssParameter name="stroke-opacity">' + this.stroke_opacity + '</CssParameter>';
	if (this.stroke_dash_array != 'none') {
		sld += '<CssParameter name="stroke-dasharray">' + this.stroke_dash_array + '</CssParameter>;'
	}
	sld += 						'</Stroke>';
	sld += 					'</LineSymbolizer>';
	sld +=          	'</Rule>';
	sld +=          '</FeatureTypeStyle>';
	sld +=      '</UserStyle>';
	sld += 	'</NamedLayer>';
	sld += '</StyledLayerDescriptor>';
	
	return sld;
};

LineSymbolizer.prototype.toJSON = function(){
	
	var object = {
		id: this.id,
		type: this.type,
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