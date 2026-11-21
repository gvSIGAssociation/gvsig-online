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
 
 
var MarkSymbolizer = function(rule, options, utils) {
	this.id = 'marksymbolizer' + utils.generateUUID();
	this.well_known_name = 'circle';
	this.fill = "#000000";
	this.fill_opacity = 0.5;
	this.stroke = "#000000";
	this.stroke_width = 1;
	this.stroke_opacity = 1;
	this.stroke_dash_array = 'none';
	this.rotation = 0;
	this.order = 0;
	this.size = 10;
	this.opacity = 1;
	this.rule = rule;
	this.utils = utils;
	
	if (options) {
		$.extend(this, options);
	} else {
		if(rule && rule.symbolizers){
			this.order = rule.symbolizers.length;
		}
	}
	this.type = 'MarkSymbolizer';
	// opciones avanzadas (campo options del servidor); ver SymbolOptionsEditor.js
	SymbolOptions.init(this);
};

MarkSymbolizer.prototype.getTableUI = function() {
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

MarkSymbolizer.prototype.getTabMenu = function() {
	var ui = '';
	ui += '<li class="active"><a href="#graphic-tab" data-toggle="tab">' + symoptT('Shape') + '</a></li>';
	ui += '<li><a href="#fill-tab" data-toggle="tab">' + gettext('Fill') + '</a></li>';
	ui += '<li><a href="#stroke-tab" data-toggle="tab">' + gettext('Stroke') + '</a></li>';
	
	return ui;	
};

MarkSymbolizer.prototype.numericFields = function() {
	var fields = (this.utils && this.utils.getAlphanumericFields && this.utils.getAlphanumericFields()) || [];
	var result = [['', symoptT('No field')]];
	for (var i = 0; i < fields.length; i++) {
		var f = fields[i];
		if (f && f.name && SymbolOptions.isNumericBinding(f.binding)) {
			result.push([f.name, f.name]);
		}
	}
	return result;
};

MarkSymbolizer.prototype.getGraphicTabUI = function() {
	var o = this.symbolOptions;
	var shapes = $.map(SymbolOptions.SHAPES, function(s) { return s[0]; });
	var ui = '<div class="tab-pane active gol-symopt-pane" id="graphic-tab">';
	ui += SymbolOptions.ui.shapeChoice('opt:shape', symoptT('Shape'), shapes, o.shape, false);
	ui += SymbolOptions.ui.row(
		SymbolOptions.ui.number('graphic-size', 'col:size', gettext('Size'), this.size, 1, 200, 0.5, 'px'),
		SymbolOptions.ui.opacity('graphic-opacity', 'col:opacity', symoptT('Symbol opacity'), this.opacity));
	var rotation = SymbolOptions.ui.number('graphic-rotation', 'col:rotation', gettext('Rotation'), this.rotation, -360, 360, 1, 'º');
	var fields = this.numericFields();
	if (fields.length > 1) {
		rotation += SymbolOptions.ui.select('graphic-rotation-field', 'opt:rotation_field', symoptT('Add angle from field'), fields, o.rotation_field || '');
	}
	ui += SymbolOptions.ui.section(gettext('Rotation'), SymbolOptions.ui.row(rotation));
	ui += SymbolOptions.ui.section(symoptT('Offset'), SymbolOptions.ui.row(
		SymbolOptions.ui.number('graphic-dx', 'opt:displacement.x', symoptT('Horizontal'), o.displacement.x, -200, 200, 1, 'px'),
		SymbolOptions.ui.number('graphic-dy', 'opt:displacement.y', symoptT('Vertical (up)'), o.displacement.y, -200, 200, 1, 'px')));
	ui += '</div>';
	return ui;
};

MarkSymbolizer.prototype.getFillTabUI = function() {
	var o = this.symbolOptions;
	var ui = '<div class="tab-pane gol-symopt-pane" id="fill-tab">';
	ui += '<p class="gol-symopt-hint" data-symopt-show="opt:shape=shape://oarrow|shape://vertline|shape://slash|shape://backslash|shape://plus|shape://times">' +
		symoptT('This shape is drawn with its stroke only.') + '</p>';
	ui += SymbolOptions.ui.toggle('fill-enabled', 'opt:fill', symoptT('Fill the shape'), o.fill);
	ui += SymbolOptions.ui.row(
		SymbolOptions.ui.color('fill-color-chooser', 'col:fill', gettext('Fill color'), this.fill, 'opt:fill'),
		SymbolOptions.ui.opacity('fill-opacity', 'col:fill_opacity', gettext('Fill opacity'), this.fill_opacity, 'opt:fill'));
	ui += '</div>';
	return ui;
};

MarkSymbolizer.prototype.getStrokeTabUI = function() {
	var ui = '<div class="tab-pane gol-symopt-pane" id="stroke-tab">';
	ui += SymbolOptions.ui.row(
		SymbolOptions.ui.color('stroke-color-chooser', 'col:stroke', gettext('Stroke color'), this.stroke),
		SymbolOptions.ui.number('stroke-width', 'col:stroke_width', gettext('Stroke width'), this.stroke_width, 0, 50, 0.5, 'px'),
		SymbolOptions.ui.opacity('stroke-opacity', 'col:stroke_opacity', gettext('Stroke opacity'), this.stroke_opacity));
	ui += SymbolOptions.ui.dashChoice('stroke-dash-custom', this.stroke_dash_array);
	ui += '</div>';
	return ui;
};

/** La rotación va en la pestaña de la forma (se mantiene el método: Rule.updateForm lo llama). */
MarkSymbolizer.prototype.getRotationTabUI = function() {
	return '';
};

MarkSymbolizer.prototype.afterChoice = function(path, value) {
	if (path === 'opt:shape') {
		// forma clásica equivalente para quien no conoce las opciones (y la propia, si es clásica)
		this.well_known_name = SymbolOptions.legacyShape(value);
	}
};

MarkSymbolizer.prototype.registerEvents = function() {
	var self = this;
	SymbolOptions.openDialog();
	SymbolOptions.bind(this, function() {
		self.updatePreview();
		self.rule.preview();
		SymbolOptions.livePreview(self);
	});
	SymbolOptions.livePreview(this);
};

MarkSymbolizer.prototype.updatePreview = function() {	
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

MarkSymbolizer.prototype.toXML = function(){
	
	var xml = '';
	xml += '<PointSymbolizer>';
	xml += 	'<Graphic>';
	xml += 		'<Mark>';
	xml += 			'<WellKnownName>' + this.well_known_name + '</WellKnownName>';
	xml += 			'<Fill>';
	xml += 				'<CssParameter name="fill">' + this.fill + '</CssParameter>';
	xml += 				'<CssParameter name="fill-opacity">' + this.fill_opacity + '</CssParameter>';
	xml += 			'</Fill>';
	xml += 			'<Stroke>';
	xml += 				'<CssParameter name="stroke">' + this.stroke + '</CssParameter>';
	xml += 				'<CssParameter name="stroke-width">' + this.stroke_width + '</CssParameter>';
	xml += 				'<CssParameter name="stroke-opacity">' + this.stroke_opacity + '</CssParameter>';
	if (this.stroke_dash_array != 'none') {
		xml += '<CssParameter name="stroke-dasharray">' + this.stroke_dash_array + '</CssParameter>;'
	}
	xml += 			'</Stroke>';
	xml += 		'</Mark>';
	xml += 		'<Opacity>1</Opacity>';
	xml += 		'<Size>' + this.size + '</Size>';
	xml += 		'<Rotation>0</Rotation>';
	xml += 	'</Graphic>';
	xml += '</PointSymbolizer>';
	
	return xml;
};

MarkSymbolizer.prototype.toSLDBody = function(){
	
	var sld = '';
	sld += '<StyledLayerDescriptor version=\"1.0.0\" xmlns=\"http://www.opengis.net/sld\" xmlns:ogc=\"http://www.opengis.net/ogc\" ';
	sld +=  'xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" ';
	sld +=  'xsi:schemaLocation=\"http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd\">';
	sld += 	'<NamedLayer>';  
	sld +=  	'<Name>Mark</Name>';  
	sld +=      '<UserStyle>';
	sld +=          '<Name>Mark</Name>';
	sld +=          '<Title>Mark</Title>';
	sld +=          '<FeatureTypeStyle>';
	sld +=          	'<Rule>';
	sld +=          		'<Name>Mark</Name>';
	sld +=          		'<Title>Mark</Title>';
	sld += 					'<PointSymbolizer>';
	sld += 						'<Graphic>';
	sld += 							'<Mark>';
	sld += 								'<WellKnownName>' + this.well_known_name + '</WellKnownName>';
	sld += 								'<Fill>';
	sld += 									'<CssParameter name="fill">' + this.fill + '</CssParameter>';
	sld += 									'<CssParameter name="fill-opacity">' + this.fill_opacity + '</CssParameter>';
	sld += 								'</Fill>';
	sld += 								'<Stroke>';
	sld += 									'<CssParameter name="stroke">' + this.stroke + '</CssParameter>';
	sld += 									'<CssParameter name="stroke-width">' + this.stroke_width + '</CssParameter>';
	sld += 									'<CssParameter name="stroke-opacity">' + this.stroke_opacity + '</CssParameter>';
	if (this.stroke_dash_array != 'none') {
		sld += '<CssParameter name="stroke-dasharray">' + this.stroke_dash_array + '</CssParameter>;'
	}
	sld += 								'</Stroke>';
	sld += 							'</Mark>';
	sld += 							'<Opacity>1</Opacity>';
	sld += 							'<Size>' + this.size + '</Size>';
	sld += 							'<Rotation>0</Rotation>';
	sld += 						'</Graphic>';
	sld += 					'</PointSymbolizer>';
	sld +=          	'</Rule>';
	sld +=          '</FeatureTypeStyle>';
	sld +=      '</UserStyle>';
	sld += 	'</NamedLayer>';
	sld += '</StyledLayerDescriptor>';
	
	return sld;
};

MarkSymbolizer.prototype.toJSON = function(){
	
	var object = {
		id: this.id,
		type: this.type,
		well_known_name: this.well_known_name,
		fill: this.fill,
		fill_opacity: this.fill_opacity,
		stroke: this.stroke,
		stroke_width: this.stroke_width,
		stroke_opacity: this.stroke_opacity,
		stroke_dash_array: this.stroke_dash_array,
		rotation: this.rotation,
		// solo si usa algo que el simbolizador clásico no puede expresar (si no, null)
		options: SymbolOptions.forJSON(this),
		order: this.order,
		size: this.size,
		opacity: this.opacity
	};
	
	return JSON.stringify(object);
};