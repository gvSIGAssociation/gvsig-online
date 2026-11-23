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
 * Símbolos predefinidos (carretera, ferrocarril, río, límite, zona inundable...).
 *
 * - Cada predefinido es una lista de simbolizadores en ORDEN DE DIBUJO (el primero, debajo).
 *   Al aplicarlo sustituyen a los simbolizadores de la regla (la etiqueta se conserva) y se
 *   pueden editar como cualquier otro.
 * - Solo usan construcciones validadas en GeoServer 2.28 y en el visor de teselas vectoriales
 *   (SymbolOptionsEditor.js / symbol_options.py). Los que no necesitan opciones son clásicos.
 * - Las miniaturas las genera el servidor (SymbolOptions.previewUrl) con el SLD que se publica.
 */

var SymbolPresets = {};

SymbolPresets.mark = function(v, options) {
	return $.extend({opacity: 1, size: 12, rotation: 0, well_known_name: 'circle', fill: '#000000', fill_opacity: 1,
		stroke: '#000000', stroke_width: 1, stroke_opacity: 1, stroke_dash_array: 'none'}, v, {options: options || null});
};

SymbolPresets.line = function(v, options) {
	return $.extend({stroke: '#000000', stroke_width: 1, stroke_opacity: 1, stroke_dash_array: 'none'}, v,
		{options: options || null});
};

SymbolPresets.poly = function(v, options) {
	return $.extend({fill: '#ffffff', fill_opacity: 1, stroke: '#000000', stroke_width: 1, stroke_opacity: 1,
		stroke_dash_array: 'none'}, v, {options: options || null});
};

function presetRound(extra) {
	return {stroke: $.extend({linecap: 'round', linejoin: 'round', dash_offset: 0, offset: 0}, extra || {})};
}

function presetHatch(pattern, color, width, spacing, background, stroke) {
	return {fill: {type: 'hatch', hatch: {pattern: pattern, color: color, width: width, spacing: spacing,
		background: background}}, stroke: $.extend({linecap: 'butt', linejoin: 'miter', dash_offset: 0}, stroke || {})};
}

function presetDecoration(shape, size, color, width, fill, spacing, start) {
	var d = {shape: shape, size: size, stroke: color, stroke_width: width, fill: fill || null};
	if (spacing !== undefined) {
		d.spacing = spacing;
		d.start = start || 0;
	}
	return d;
}

// [id, nombre (msgid), simbolizadores en orden de dibujo]
SymbolPresets.CATALOG = {
	PointSymbolizer: [
		['poi', 'Point of interest', [
			SymbolPresets.mark({size: 14, fill: '#ffffff', stroke: '#2c3e50', stroke_width: 1.5}),
			SymbolPresets.mark({size: 6, fill: '#e74c3c', stroke_width: 0})]],
		['target', 'Target', [
			SymbolPresets.mark({size: 16, fill: '#ffffff', fill_opacity: 0, stroke: '#c0392b', stroke_width: 2}),
			SymbolPresets.mark({size: 4, fill: '#c0392b', stroke_width: 0})]],
		['geodesic', 'Survey point', [
			SymbolPresets.mark({size: 16, well_known_name: 'triangle', fill: '#ffffff', stroke: '#000000', stroke_width: 1.5}),
			SymbolPresets.mark({size: 4, fill: '#000000', stroke_width: 0})]],
		['star', 'Highlighted star', [
			SymbolPresets.mark({size: 18, well_known_name: 'star', fill: '#f1c40f', stroke: '#7d6608'})]],
		['diamond', 'Diamond', [
			SymbolPresets.mark({size: 14, well_known_name: 'square', fill: '#f39c12', stroke: '#7e5109'},
				{v: 1, shape: 'qgis://diamond', fill: true, displacement: {x: 0, y: 0}, rotation_field: null})]],
		['hexagon', 'Hexagon', [
			SymbolPresets.mark({size: 14, fill: '#16a085', stroke: '#0b5345'},
				{v: 1, shape: 'qgis://hexagon', fill: true, displacement: {x: 0, y: 0}, rotation_field: null})]],
		['north', 'North arrow', [
			SymbolPresets.mark({size: 20, well_known_name: 'triangle', fill: '#2c3e50', stroke: '#2c3e50'},
				{v: 1, shape: 'extshape://narrow', fill: true, displacement: {x: 0, y: 0}, rotation_field: null})]],
		['cross', 'X mark', [
			SymbolPresets.mark({size: 12, well_known_name: 'x', fill: '#c0392b', stroke: '#ffffff'})]]
	],
	LineSymbolizer: [
		['main_road', 'Main road', [
			SymbolPresets.line({stroke: '#8a5a00', stroke_width: 7}, presetRound()),
			SymbolPresets.line({stroke: '#f6c342', stroke_width: 5}, presetRound())]],
		['secondary_road', 'Secondary road', [
			SymbolPresets.line({stroke: '#6b6b6b', stroke_width: 5}, presetRound()),
			SymbolPresets.line({stroke: '#ffffff', stroke_width: 3}, presetRound())]],
		['track', 'Track', [
			SymbolPresets.line({stroke: '#8b5a2b', stroke_width: 1.5, stroke_dash_array: '6 3'})]],
		['path', 'Footpath', [
			SymbolPresets.line({stroke: '#8b5a2b', stroke_width: 1, stroke_dash_array: '2 3'}, presetRound())]],
		['railway', 'Railway', [
			SymbolPresets.line({stroke: '#333333', stroke_width: 1.5}, {line: true,
				stroke: {linecap: 'butt', linejoin: 'miter', dash_offset: 0, offset: 0},
				marks: presetDecoration('shape://vertline', 8, '#333333', 1.5, null, 7), start: null, end: null})]],
		['railway_classic', 'Railway (classic)', [
			SymbolPresets.line({stroke: '#333333', stroke_width: 4}),
			SymbolPresets.line({stroke: '#ffffff', stroke_width: 2, stroke_dash_array: '10 10'})]],
		['river', 'River', [
			SymbolPresets.line({stroke: '#3a7dc9', stroke_width: 2.5}, presetRound())]],
		['river_flow', 'River with flow direction', [
			SymbolPresets.line({stroke: '#3a7dc9', stroke_width: 2}, $.extend(presetRound(), {line: true,
				marks: presetDecoration('shape://carrow', 11, '#1f5f9e', 1, '#1f5f9e', 50, 25), start: null, end: null}))]],
		['canal', 'Canal', [
			SymbolPresets.line({stroke: '#3a7dc9', stroke_width: 4}),
			SymbolPresets.line({stroke: '#bcd9f5', stroke_width: 2})]],
		['admin_boundary', 'Administrative boundary', [
			SymbolPresets.line({stroke: '#8e44ad', stroke_width: 8, stroke_opacity: 0.25}, presetRound()),
			SymbolPresets.line({stroke: '#8e44ad', stroke_width: 1.5, stroke_dash_array: '10 4 2 4'})]],
		['municipal_boundary', 'Municipal boundary', [
			SymbolPresets.line({stroke: '#555555', stroke_width: 1.2, stroke_dash_array: '6 3 1 3'})]],
		['power_line', 'Power line', [
			SymbolPresets.line({stroke: '#555555', stroke_width: 1}, {line: true,
				stroke: {linecap: 'butt', linejoin: 'miter', dash_offset: 0, offset: 0},
				marks: presetDecoration('circle', 4, '#555555', 0, '#555555', 36, 18), start: null, end: null})]],
		['fence', 'Fence', [
			SymbolPresets.line({stroke: '#6d4c41', stroke_width: 1}, {line: true,
				stroke: {linecap: 'butt', linejoin: 'miter', dash_offset: 0, offset: 0},
				marks: presetDecoration('x', 6, '#6d4c41', 0, '#6d4c41', 12, 6), start: null, end: null})]],
		['flow_arrow', 'Line with end arrow', [
			SymbolPresets.line({stroke: '#2c3e50', stroke_width: 2}, $.extend(presetRound(), {line: true, marks: null,
				start: null, end: presetDecoration('shape://carrow', 12, '#2c3e50', 1, '#2c3e50')}))]],
		['double_line', 'Double line', [
			SymbolPresets.line({stroke: '#444444', stroke_width: 1}, {line: true,
				stroke: {linecap: 'butt', linejoin: 'round', dash_offset: 0, offset: 3}, marks: null, start: null, end: null}),
			SymbolPresets.line({stroke: '#444444', stroke_width: 1}, {line: true,
				stroke: {linecap: 'butt', linejoin: 'round', dash_offset: 0, offset: -3}, marks: null, start: null, end: null})]]
	],
	PolygonSymbolizer: [
		['building', 'Building', [
			SymbolPresets.poly({fill: '#d9d0c9', stroke: '#a89f97'})]],
		['water', 'Water body', [
			SymbolPresets.poly({fill: '#a6cee3', stroke: '#1f78b4'})]],
		['green_area', 'Green area', [
			SymbolPresets.poly({fill: '#c7e9c0', stroke: '#41ab5d'})]],
		['flood_zone', 'Flood zone', [
			SymbolPresets.poly({fill: '#dceefb', fill_opacity: 0.6, stroke: '#2a7ab9'},
				presetHatch('backslash', '#2a7ab9', 1, 8, true))]],
		['protected_area', 'Protected area', [
			SymbolPresets.poly({fill: '#ffffff', stroke: '#2e7d32', stroke_width: 2, stroke_dash_array: '8 4'},
				presetHatch('slash', '#2e7d32', 1, 10, false))]],
		['restricted_area', 'Restricted area', [
			SymbolPresets.poly({fill: '#ffffff', stroke: '#c62828', stroke_width: 1.5},
				presetHatch('times', '#c62828', 1, 12, false))]],
		['vegetation', 'Vegetation', [
			SymbolPresets.poly({fill: '#e5f5e0', stroke: '#2e7d32', stroke_width: 0.5},
				presetHatch('dots', '#2e7d32', 1, 10, true))]],
		['crops', 'Crops', [
			SymbolPresets.poly({fill: '#f5ecd7', stroke: '#9c7a3c'}, presetHatch('horline', '#9c7a3c', 1, 8, true))]],
		['parcel', 'Parcel outline', [
			SymbolPresets.poly({fill: '#ffffff', stroke: '#b03a2e'},
				{fill: {type: 'none'}, stroke: {linecap: 'butt', linejoin: 'miter', dash_offset: 0}})]],
		['dashed_area', 'Dashed outline', [
			SymbolPresets.poly({fill: '#ffffff', stroke: '#34495e', stroke_width: 2, stroke_dash_array: '10 5'},
				{fill: {type: 'none'}, stroke: {linecap: 'butt', linejoin: 'round', dash_offset: 0}})]]
	]
};

SymbolPresets.forType = function(featureType) {
	return SymbolPresets.CATALOG[featureType] || [];
};

SymbolPresets.find = function(featureType, id) {
	var list = SymbolPresets.forType(featureType);
	for (var i = 0; i < list.length; i++) {
		if (list[i][0] === id) {
			return list[i];
		}
	}
	return null;
};

/**
 * Opciones de los simbolizadores de un predefinido en ORDEN DE DIBUJO (el primero, debajo), con su
 * order (0 = el de encima, como las filas del editor) y las opciones como texto (como llegan del servidor).
 */
SymbolPresets.definitions = function(preset) {
	var defs = preset[2], n = defs.length, result = [];
	for (var i = 0; i < n; i++) {
		var def = $.extend(true, {}, defs[i]);
		def.order = n - 1 - i;
		def.options = def.options ? JSON.stringify(def.options) : null;
		result.push(def);
	}
	return result;
};

/** Simbolizadores del editor de un predefinido, en orden de dibujo (para la miniatura). */
SymbolPresets.build = function(rule, featureType, preset) {
	var ctor = {PointSymbolizer: MarkSymbolizer, LineSymbolizer: LineSymbolizer, PolygonSymbolizer: PolygonSymbolizer}[featureType];
	return $.map(SymbolPresets.definitions(preset), function(def) { return [new ctor(rule, def, rule.utils)]; });
};

/** Galería de predefinidos para una regla (modal creado al vuelo). */
SymbolPresets.open = function(rule) {
	var featureType = rule.utils.getFeatureType();
	var list = SymbolPresets.forType(featureType);
	if (!list.length) {
		return;
	}
	var modal = $('#modal-symbol-presets');
	if (!modal.length) {
		$('body').append(
			'<div class="modal fade gol-sympreset-modal" id="modal-symbol-presets" tabindex="-1" role="dialog" aria-labelledby="modal-symbol-presets-title">' +
			'<div class="modal-dialog modal-lg" role="document"><div class="modal-content">' +
			'<div class="modal-header"><button type="button" class="close" data-dismiss="modal" aria-label="' + symoptEsc(gettext('Close')) + '">' +
			'<span aria-hidden="true">&times;</span></button><h4 class="modal-title" id="modal-symbol-presets-title">' + symoptT('Symbol presets') + '</h4></div>' +
			'<div class="modal-body"><p class="gol-symopt-hint">' + symoptT('Choose a preset to replace the symbolizers of the rule. The label is kept, and you can edit the symbolizers afterwards.') + '</p>' +
			'<div class="gol-sympreset-grid"></div></div></div></div></div>');
		modal = $('#modal-symbol-presets');
	}
	var grid = modal.find('.gol-sympreset-grid').empty();
	var previewUrl = rule.utils.getPreviewUrl();
	for (var i = 0; i < list.length; i++) {
		var preset = list[i];
		var thumb = SymbolOptions.previewUrl(previewUrl, SymbolPresets.build(rule, featureType, preset), 120, 60);
		grid.append('<button type="button" class="gol-sympreset-card" data-preset="' + symoptEsc(preset[0]) + '">' +
			'<span class="gol-sympreset-thumb"><img src="' + symoptEsc(thumb) + '" alt="" loading="lazy"></span>' +
			'<span class="gol-sympreset-name">' + symoptEsc(symoptT(preset[1])) + '</span></button>');
	}
	grid.off('click.sympreset').on('click.sympreset', '.gol-sympreset-card', function() {
		var preset = SymbolPresets.find(featureType, this.getAttribute('data-preset'));
		modal.modal('hide');
		if (preset) {
			rule.applyPreset(preset);
		}
	});
	modal.modal('show');
};
