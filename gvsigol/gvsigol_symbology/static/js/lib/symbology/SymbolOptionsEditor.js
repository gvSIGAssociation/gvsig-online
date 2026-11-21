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
 * Simbología avanzada de marcas, líneas y polígonos (MarkSymbolizer / LineSymbolizer /
 * PolygonSymbolizer .options): esquema, controles comunes del editor y vista previa.
 *
 * - Un simbolizador solo envía opciones si usa algo que el simbolizador clásico no puede
 *   expresar (forma nueva, trama, extremos, desplazamiento...). Si no, se guarda como siempre
 *   (options = null) y su SLD no cambia: editar el color de un símbolo antiguo lo deja antiguo.
 * - El esquema y sus límites son los de gvsigol_symbology/symbol_options.py; el servidor vuelve a
 *   validarlo todo al guardar.
 * - La vista previa de los simbolizadores con opciones la genera el servidor con el mismo SLD que
 *   se publica (/gvsigonline/symbology/symbol_preview/); los clásicos siguen con la suya.
 * - Los controles llevan data-symopt="col:campo" (columna del modelo) o "opt:ruta" (opciones);
 *   un único manejador delegado en #tab-content los enlaza (espacio de nombres .symopt).
 */

var SymbolOptions = {};

SymbolOptions.EVENTS = '.symopt';
SymbolOptions.PREVIEW_URL = '/gvsigonline/symbology/symbol_preview/';

function symoptT(msgid) {
	return (typeof pgettext === 'function') ? pgettext('symbology', msgid) : gettext(msgid);
}

function symoptEsc(value) {
	return String(value == null ? '' : value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// [valor, texto, clásica, solo trazo]. Lista blanca validada en GeoServer 2.28 (symbol_options.SHAPES).
SymbolOptions.SHAPES = [
	['circle', 'Circle', true, false],
	['square', 'Square', true, false],
	['triangle', 'Triangle', true, false],
	['star', 'Star', true, false],
	['cross', 'Cross', true, false],
	['x', 'X', true, false],
	['qgis://diamond', 'Diamond', false, false],
	['qgis://pentagon', 'Pentagon', false, false],
	['qgis://hexagon', 'Hexagon', false, false],
	['qgis://rectangle', 'Rectangle', false, false],
	['qgis://semicircle', 'Semicircle', false, false],
	['qgis://equilateral_triangle', 'Equilateral triangle', false, false],
	['qgis://arrowhead', 'Arrowhead', false, false],
	['extshape://narrow', 'North arrow', false, false],
	['extshape://sarrow', 'South arrow', false, false],
	['shape://carrow', 'Closed arrow', false, false],
	['shape://oarrow', 'Open arrow', false, true],
	['shape://vertline', 'Vertical line', false, true],
	['shape://slash', 'Slash', false, true],
	['shape://backslash', 'Backslash', false, true],
	['shape://plus', 'Plus', false, true],
	['shape://times', 'Times', false, true]
];
// Formas habituales para las marcas a lo largo de una línea y para los extremos
SymbolOptions.ALONG_SHAPES = ['shape://vertline', 'circle', 'square', 'qgis://diamond', 'triangle', 'x', 'shape://times',
	'shape://plus', 'shape://oarrow', 'shape://carrow', 'qgis://arrowhead', 'star'];
SymbolOptions.END_SHAPES = ['shape://carrow', 'shape://oarrow', 'qgis://arrowhead', 'circle', 'square', 'qgis://diamond',
	'shape://vertline', 'x'];
// Forma clásica que se guarda en well_known_name (como symbol_options.LEGACY_SHAPE)
SymbolOptions.LEGACY_SHAPE = {
	'shape://plus': 'cross', 'shape://times': 'cross', 'qgis://diamond': 'square', 'qgis://rectangle': 'square',
	'qgis://pentagon': 'circle', 'qgis://hexagon': 'circle', 'qgis://semicircle': 'circle',
	'qgis://equilateral_triangle': 'triangle', 'qgis://arrowhead': 'triangle', 'extshape://narrow': 'triangle',
	'extshape://sarrow': 'triangle', 'shape://oarrow': 'triangle', 'shape://carrow': 'triangle'
};
SymbolOptions.HATCHES = [
	['slash', 'Diagonal /'], ['backslash', 'Diagonal \\'], ['horline', 'Horizontal'], ['vertline', 'Vertical'],
	['plus', 'Grid'], ['times', 'Diagonal grid'], ['dots', 'Dots']
];
// Los siete primeros son los del editor clásico (SymbologyUtils.linePatterns)
SymbolOptions.DASHES = ['none', '5 10', '10 5', '5 1', '1 5', '15 10 5 10', '5 5 1 5', '2 2', '8 4', '12 4 2 4',
	'20 5', '15 5 5 5 5 5'];
SymbolOptions.LINECAPS = [['butt', 'Butt'], ['round', 'Round'], ['square', 'Square']];
SymbolOptions.LINEJOINS = [['miter', 'Miter'], ['round', 'Round'], ['bevel', 'Bevel']];

/** Tipo de campo numérico de GeoServer (como LabelOptionsEditor.isNumericBinding). */
SymbolOptions.isNumericBinding = function(binding) {
	return /^java\.(math\.|lang\.(Integer|Long|Short|Byte|Float|Double|Number)$)/.test(binding || '');
};

SymbolOptions.shapeInfo = function(value) {
	for (var i = 0; i < SymbolOptions.SHAPES.length; i++) {
		if (SymbolOptions.SHAPES[i][0] === value) {
			return SymbolOptions.SHAPES[i];
		}
	}
	return null;
};

SymbolOptions.isLegacyShape = function(value) {
	var info = SymbolOptions.shapeInfo(value);
	return !!(info && info[2]);
};

SymbolOptions.isLineShape = function(value) {
	var info = SymbolOptions.shapeInfo(value);
	return !!(info && info[3]);
};

SymbolOptions.legacyShape = function(value) {
	return SymbolOptions.isLegacyShape(value) ? value : (SymbolOptions.LEGACY_SHAPE[value] || 'circle');
};

// ---------------------------------------------------------------------------- esquema

SymbolOptions.decoration = function(shape, size, spacing) {
	var d = {shape: shape, size: size, fill: SymbolOptions.isLineShape(shape) ? null : '#000000', stroke: '#000000', stroke_width: 1};
	if (spacing !== undefined) {
		d.spacing = spacing;
		d.start = 0;
	}
	return d;
};

SymbolOptions.defaults = function(kind) {
	if (kind === 'mark') {
		return {v: 1, shape: 'circle', fill: true, displacement: {x: 0, y: 0}, rotation_field: null};
	}
	if (kind === 'line') {
		return {v: 1, line: true, stroke: {linecap: 'butt', linejoin: 'miter', dash_offset: 0, offset: 0},
			marks: null, start: null, end: null};
	}
	return {v: 1, fill: {type: 'solid'}, stroke: {linecap: 'butt', linejoin: 'miter', dash_offset: 0}};
};

/** Texto guardado (o el objeto) -> opciones completas (si no hay, los valores por defecto). */
SymbolOptions.parse = function(kind, raw) {
	var data = raw;
	if (typeof raw === 'string' && raw) {
		try {
			data = JSON.parse(raw);
		} catch (e) {
			data = null;
		}
	}
	var o = SymbolOptions.defaults(kind);
	if (!data || typeof data !== 'object') {
		return o;
	}
	if (kind === 'mark') {
		o.shape = SymbolOptions.shapeInfo(data.shape) ? data.shape : 'circle';
		o.fill = data.fill !== false;
		o.displacement = $.extend(o.displacement, data.displacement || {});
		o.rotation_field = data.rotation_field || null;
	} else if (kind === 'line') {
		o.line = data.line !== false;
		o.stroke = $.extend(o.stroke, data.stroke || {});
		o.marks = data.marks ? $.extend(SymbolOptions.decoration('shape://vertline', 10, 20), data.marks) : null;
		o.start = data.start ? $.extend(SymbolOptions.decoration('circle', 10), data.start) : null;
		o.end = data.end ? $.extend(SymbolOptions.decoration('shape://carrow', 10), data.end) : null;
	} else {
		o.fill = $.extend({type: 'solid'}, data.fill || {});
		if (o.fill.type === 'hatch') {
			o.fill.hatch = $.extend({pattern: 'slash', color: '#000000', width: 1, spacing: 10, background: true}, o.fill.hatch || {});
		}
		o.stroke = $.extend(o.stroke, data.stroke || {});
	}
	return o;
};

/** ¿Usa el simbolizador algo que el clásico no puede expresar? */
SymbolOptions.needed = function(sym) {
	var o = sym.symbolOptions;
	if (!o) {
		return false;
	}
	if (sym.type === 'MarkSymbolizer') {
		return !SymbolOptions.isLegacyShape(o.shape) || !o.fill || !!Number(o.displacement.x) || !!Number(o.displacement.y)
			|| !!o.rotation_field;
	}
	var s = o.stroke;
	var strokeExtras = s.linecap !== 'butt' || s.linejoin !== 'miter' || !!Number(s.dash_offset);
	if (sym.type === 'LineSymbolizer') {
		return strokeExtras || !o.line || !!Number(s.offset) || !!o.marks || !!o.start || !!o.end;
	}
	return strokeExtras || o.fill.type !== 'solid';
};

/** Opciones para toJSON (null si el simbolizador es clásico). */
SymbolOptions.forJSON = function(sym) {
	if (!SymbolOptions.needed(sym)) {
		return null;
	}
	var o = $.extend(true, {}, sym.symbolOptions);
	if (o.fill && o.fill.type !== 'hatch') {
		delete o.fill.hatch;
	}
	return o;
};

SymbolOptions.kindOf = function(sym) {
	return {MarkSymbolizer: 'mark', LineSymbolizer: 'line', PolygonSymbolizer: 'polygon'}[sym.type];
};

/** Inicializa symbolOptions a partir del campo options que llega del servidor. */
SymbolOptions.init = function(sym) {
	sym.symbolOptions = SymbolOptions.parse(SymbolOptions.kindOf(sym), sym.options);
	if (sym.type === 'MarkSymbolizer' && !sym.options) {
		sym.symbolOptions.shape = SymbolOptions.shapeInfo(sym.well_known_name) ? sym.well_known_name : 'circle';
	}
	delete sym.options;
};

// ---------------------------------------------------------------------------- dibujos SVG

function symoptRound(n) {
	return Math.round(n * 100) / 100;
}

function symoptPoly(points) {
	var d = '';
	for (var i = 0; i < points.length; i++) {
		d += (i === 0 ? 'M' : 'L') + symoptRound(points[i][0]) + ',' + symoptRound(points[i][1]) + ' ';
	}
	return d + 'Z';
}

function symoptRegular(n, r) {
	var pts = [];
	for (var i = 0; i < n; i++) {
		var a = (-90 + i * 360 / n) * Math.PI / 180;
		pts.push([r * Math.cos(a), r * Math.sin(a)]);
	}
	return pts;
}

/** Path SVG de una forma centrada en (0, 0), como mapbox_symbol_converter.shape_path. */
SymbolOptions.shapePath = function(shape, size) {
	var r = size / 2, t = size * 0.125, pts, i;
	switch (shape) {
	case 'circle':
		return 'M' + (-r) + ',0 A' + r + ',' + r + ' 0 1 0 ' + r + ',0 A' + r + ',' + r + ' 0 1 0 ' + (-r) + ',0 Z';
	case 'square':
		return symoptPoly([[-r, -r], [r, -r], [r, r], [-r, r]]);
	case 'triangle':
	case 'qgis://equilateral_triangle':
		return symoptPoly(symoptRegular(3, r));
	case 'star':
		pts = [];
		for (i = 0; i < 10; i++) {
			var rad = i % 2 === 0 ? r : r * 0.382, a = (-90 + i * 36) * Math.PI / 180;
			pts.push([rad * Math.cos(a), rad * Math.sin(a)]);
		}
		return symoptPoly(pts);
	case 'cross':
	case 'x':
		pts = [[-t, -r], [t, -r], [t, -t], [r, -t], [r, t], [t, t], [t, r], [-t, r], [-t, t], [-r, t], [-r, -t], [-t, -t]];
		if (shape === 'x') {
			var c = Math.SQRT1_2;
			pts = $.map(pts, function(p) { return [[p[0] * c - p[1] * c, p[0] * c + p[1] * c]]; });
		}
		return symoptPoly(pts);
	case 'qgis://diamond':
		return symoptPoly([[0, -r], [r, 0], [0, r], [-r, 0]]);
	case 'qgis://pentagon':
		return symoptPoly(symoptRegular(5, r));
	case 'qgis://hexagon':
		return symoptPoly(symoptRegular(6, r));
	case 'qgis://rectangle':
		return symoptPoly([[-r, -r / 2], [r, -r / 2], [r, r / 2], [-r, r / 2]]);
	case 'qgis://semicircle':
		return 'M' + (-r) + ',0 A' + r + ',' + r + ' 0 0 1 ' + r + ',0 Z';
	case 'qgis://arrowhead':
	case 'shape://carrow':
		return symoptPoly([[-r, -r], [r, 0], [-r, r]]);
	case 'extshape://narrow':
	case 'extshape://sarrow':
		pts = [[0, -r], [0.5 * r, -0.2 * r], [0.15 * r, -0.2 * r], [0.15 * r, r], [-0.15 * r, r], [-0.15 * r, -0.2 * r], [-0.5 * r, -0.2 * r]];
		if (shape === 'extshape://sarrow') {
			pts = $.map(pts, function(p) { return [[p[0], -p[1]]]; });
		}
		return symoptPoly(pts);
	case 'shape://vertline':
		return 'M0,' + (-r) + ' L0,' + r;
	case 'shape://slash':
		return 'M' + (-r) + ',' + r + ' L' + r + ',' + (-r);
	case 'shape://backslash':
		return 'M' + (-r) + ',' + (-r) + ' L' + r + ',' + r;
	case 'shape://plus':
		return 'M0,' + (-r) + ' L0,' + r + ' M' + (-r) + ',0 L' + r + ',0';
	case 'shape://times':
		return 'M' + (-r) + ',' + (-r) + ' L' + r + ',' + r + ' M' + (-r) + ',' + r + ' L' + r + ',' + (-r);
	case 'shape://oarrow':
		return 'M' + (-r) + ',' + (-r) + ' L' + r + ',0 L' + (-r) + ',' + r;
	}
	return '';
};

SymbolOptions.shapeSvg = function(shape, px) {
	var d = SymbolOptions.shapePath(shape, px - 4);
	var lineOnly = SymbolOptions.isLineShape(shape);
	return '<svg width="' + px + '" height="' + px + '" viewBox="0 0 ' + px + ' ' + px + '" aria-hidden="true" focusable="false">' +
		'<path d="' + d + '" transform="translate(' + (px / 2) + ' ' + (px / 2) + ')" fill="' + (lineOnly ? 'none' : 'currentColor') +
		'" fill-opacity="0.25" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>';
};

SymbolOptions.dashSvg = function(dash) {
	var attr = dash && dash !== 'none' ? ' stroke-dasharray="' + symoptEsc(dash) + '"' : '';
	return '<svg width="96" height="10" viewBox="0 0 96 10" aria-hidden="true" focusable="false"><line x1="2" y1="5" x2="94" y2="5" ' +
		'stroke="currentColor" stroke-width="2"' + attr + '/></svg>';
};

SymbolOptions.hatchSvg = function(pattern) {
	var s = 8, lines = {
		slash: [[0, s, s, 0]], backslash: [[0, 0, s, s]], horline: [[0, s / 2, s, s / 2]], vertline: [[s / 2, 0, s / 2, s]],
		plus: [[0, s / 2, s, s / 2], [s / 2, 0, s / 2, s]], times: [[0, s, s, 0], [0, 0, s, s]]
	}[pattern];
	var id = 'symopt-h-' + pattern;
	var tile = '';
	if (pattern === 'dots') {
		tile = '<circle cx="4" cy="4" r="1.4" fill="currentColor"/>';
	} else {
		for (var i = 0; i < lines.length; i++) {
			tile += '<line x1="' + lines[i][0] + '" y1="' + lines[i][1] + '" x2="' + lines[i][2] + '" y2="' + lines[i][3] +
				'" stroke="currentColor" stroke-width="1"/>';
		}
	}
	return '<svg width="34" height="24" viewBox="0 0 34 24" aria-hidden="true" focusable="false"><defs><pattern id="' + id +
		'" width="8" height="8" patternUnits="userSpaceOnUse">' + tile + '</pattern></defs>' +
		'<rect x="1" y="1" width="32" height="22" rx="3" fill="url(#' + id + ')" stroke="currentColor" stroke-opacity="0.4"/></svg>';
};

// ---------------------------------------------------------------------------- controles

SymbolOptions.ui = {};

SymbolOptions.ui.section = function(title, body, extraClass) {
	return '<fieldset class="gol-symopt-section' + (extraClass ? ' ' + extraClass : '') + '"><legend>' + title + '</legend>' + body + '</fieldset>';
};

SymbolOptions.ui.field = function(id, label, control, showIf) {
	return '<div class="form-group gol-symopt-field"' + (showIf ? ' data-symopt-show="' + symoptEsc(showIf) + '"' : '') + '>' +
		'<label for="' + id + '">' + label + '</label>' + control + '</div>';
};

SymbolOptions.ui.number = function(id, path, label, value, min, max, step, unit, showIf) {
	var ctl = '<div class="gol-symopt-unit"><input id="' + id + '" data-symopt="' + path + '" data-type="number" type="number" class="form-control"' +
		' min="' + min + '" max="' + max + '" step="' + (step || 1) + '" value="' + symoptEsc(value) + '">' +
		(unit ? '<span class="gol-symopt-unit-text">' + unit + '</span>' : '') + '</div>';
	return SymbolOptions.ui.field(id, label, ctl, showIf);
};

SymbolOptions.ui.color = function(id, path, label, value, showIf) {
	var ctl = '<input id="' + id + '" data-symopt="' + path + '" data-type="color" type="color" class="form-control color-chooser gol-symopt-color" value="' +
		symoptEsc(value || '#000000') + '">';
	return SymbolOptions.ui.field(id, label, ctl, showIf);
};

SymbolOptions.ui.opacity = function(id, path, label, value, showIf) {
	var pct = Math.round(Number(value == null ? 1 : value) * 100);
	var ctl = '<div class="gol-symopt-range"><input id="' + id + '" data-symopt="' + path + '" data-type="percent" type="range" min="0" max="100" step="5" value="' +
		pct + '"><output for="' + id + '">' + pct + '%</output></div>';
	return SymbolOptions.ui.field(id, label, ctl, showIf);
};

SymbolOptions.ui.toggle = function(id, path, label, checked, showIf) {
	return '<div class="gol-symopt-toggle"' + (showIf ? ' data-symopt-show="' + symoptEsc(showIf) + '"' : '') + '><label for="' + id + '">' +
		'<input id="' + id + '" data-symopt="' + path + '" data-type="bool" type="checkbox"' + (checked ? ' checked' : '') + '> ' + label + '</label></div>';
};

SymbolOptions.ui.select = function(id, path, label, options, selected, showIf) {
	var ctl = '<select id="' + id + '" data-symopt="' + path + '" data-type="text" class="form-control">';
	for (var i = 0; i < options.length; i++) {
		ctl += '<option value="' + symoptEsc(options[i][0]) + '"' + (options[i][0] === selected ? ' selected' : '') + '>' + symoptEsc(options[i][1]) + '</option>';
	}
	return SymbolOptions.ui.field(id, label, ctl + '</select>', showIf);
};

/** Grupo de botones excluyentes (forma, trama, guiones, extremos...). items: [[valor, contenido, título]]. */
SymbolOptions.ui.choice = function(path, label, items, selected, extraClass, showIf) {
	var ui = '<div class="form-group gol-symopt-field"' + (showIf ? ' data-symopt-show="' + symoptEsc(showIf) + '"' : '') + '>';
	ui += '<span class="gol-symopt-label">' + label + '</span>';
	ui += '<div class="gol-symopt-choice ' + (extraClass || '') + '" role="radiogroup" aria-label="' + symoptEsc(label) + '">';
	for (var i = 0; i < items.length; i++) {
		var active = String(items[i][0]) === String(selected);
		ui += '<button type="button" role="radio" aria-checked="' + active + '" class="gol-symopt-option' + (active ? ' active' : '') +
			'" data-symopt-choice="' + path + '" data-value="' + symoptEsc(items[i][0]) + '" title="' + symoptEsc(items[i][2] || '') + '">' + items[i][1] + '</button>';
	}
	return ui + '</div></div>';
};

SymbolOptions.ui.shapeChoice = function(path, label, shapes, selected, withNone, showIf) {
	var items = [];
	if (withNone) {
		items.push(['none', '<span class="gol-symopt-none">' + symoptT('None') + '</span>', symoptT('None')]);
	}
	for (var i = 0; i < shapes.length; i++) {
		var info = SymbolOptions.shapeInfo(shapes[i]);
		items.push([shapes[i], SymbolOptions.shapeSvg(shapes[i], 26), symoptT(info[1])]);
	}
	return SymbolOptions.ui.choice(path, label, items, selected, 'gol-symopt-shapes', showIf);
};

SymbolOptions.ui.dashChoice = function(id, value) {
	var items = [], known = false;
	for (var i = 0; i < SymbolOptions.DASHES.length; i++) {
		var dash = SymbolOptions.DASHES[i];
		known = known || dash === value;
		items.push([dash, SymbolOptions.dashSvg(dash), dash === 'none' ? symoptT('Solid') : dash]);
	}
	var ui = SymbolOptions.ui.choice('col:stroke_dash_array', symoptT('Dash pattern'), items, value, 'gol-symopt-dashes');
	ui += SymbolOptions.ui.field(id, symoptT('Custom pattern'),
		'<input id="' + id + '" data-symopt="col:stroke_dash_array" data-type="dash" type="text" class="form-control gol-symopt-dash-input" placeholder="' +
		symoptEsc(symoptT('e.g. 10 4 2 4')) + '" value="' + symoptEsc(known || value === 'none' ? '' : value) + '">' +
		'<p class="gol-symopt-hint">' + symoptT('Dash and gap lengths in pixels, separated by spaces.') + '</p>');
	return ui;
};

SymbolOptions.ui.capJoin = function(prefix, stroke) {
	var caps = $.map(SymbolOptions.LINECAPS, function(c) { return [[c[0], symoptT(c[1]), symoptT(c[1])]]; });
	var joins = $.map(SymbolOptions.LINEJOINS, function(c) { return [[c[0], symoptT(c[1]), symoptT(c[1])]]; });
	return '<div class="gol-symopt-row">' +
		SymbolOptions.ui.choice(prefix + '.linecap', symoptT('Line ends'), caps, stroke.linecap, 'gol-symopt-segmented') +
		SymbolOptions.ui.choice(prefix + '.linejoin', symoptT('Corners'), joins, stroke.linejoin, 'gol-symopt-segmented') + '</div>';
};

SymbolOptions.ui.row = function() {
	return '<div class="gol-symopt-row">' + Array.prototype.join.call(arguments, '') + '</div>';
};

// ---------------------------------------------------------------------------- enlace de datos

function symoptGet(sym, path) {
	var parts = path.split(':'), obj = parts[0] === 'col' ? sym : sym.symbolOptions, keys = parts[1].split('.');
	for (var i = 0; i < keys.length && obj != null; i++) {
		obj = obj[keys[i]];
	}
	return obj;
}

function symoptSet(sym, path, value) {
	var parts = path.split(':'), keys = parts[1].split('.');
	if (parts[0] === 'col') {
		sym[keys[0]] = value;
		return;
	}
	var o = sym.symbolOptions;
	// marcas a lo largo / extremos: «ninguna» las quita; elegir forma las crea con valores por defecto
	if (keys.length === 2 && (keys[0] === 'marks' || keys[0] === 'start' || keys[0] === 'end') && keys[1] === 'shape') {
		if (value === 'none') {
			o[keys[0]] = null;
		} else {
			var current = o[keys[0]] || SymbolOptions.decoration(value, keys[0] === 'end' ? 12 : 8, keys[0] === 'marks' ? 20 : undefined);
			current.shape = value;
			if (SymbolOptions.isLineShape(value)) {
				current.fill = null;
			} else if (!current.fill) {
				current.fill = current.stroke || '#000000';
			}
			o[keys[0]] = current;
		}
		return;
	}
	if (keys.length === 2 && keys[0] === 'fill' && keys[1] === 'type' && value === 'hatch' && !o.fill.hatch) {
		o.fill.hatch = {pattern: 'slash', color: '#000000', width: 1, spacing: 10, background: true};
	}
	for (var i = 0; i < keys.length - 1; i++) {
		if (o[keys[i]] == null) {
			o[keys[i]] = {};
		}
		o = o[keys[i]];
	}
	o[keys[keys.length - 1]] = value;
	// el color de las decoraciones rellena las formas que tienen relleno
	if (keys.length === 2 && keys[1] === 'stroke' && (keys[0] === 'marks' || keys[0] === 'start' || keys[0] === 'end')
			&& o.fill && !SymbolOptions.isLineShape(o.shape)) {
		o.fill = value;
	}
}

function symoptCoerce(input) {
	var type = input.getAttribute('data-type');
	if (type === 'bool') {
		return input.checked;
	}
	if (type === 'percent') {
		return Math.round(Number(input.value)) / 100;
	}
	if (type === 'number') {
		var n = Number(input.value), min = Number(input.min), max = Number(input.max);
		if (!isFinite(n)) {
			n = 0;
		}
		return Math.max(isFinite(min) ? min : n, Math.min(isFinite(max) ? max : n, n));
	}
	if (type === 'dash') {
		var v = $.trim(input.value).replace(/,/g, ' ').replace(/\s+/g, ' ');
		return /^\d+(\.\d+)?( \d+(\.\d+)?)*$/.test(v) ? v : null;
	}
	if (type === 'text') {
		return input.value === '' ? null : input.value;
	}
	if (type === 'color') {
		return String(input.value).toLowerCase(); // como el servidor (symbol_options._color)
	}
	return input.value;
}

/** Muestra u oculta lo que depende de otros valores (data-symopt-show="ruta=valor1|valor2" o "ruta"). */
SymbolOptions.refreshVisibility = function(sym) {
	$('#tab-content [data-symopt-show]').each(function() {
		var cond = this.getAttribute('data-symopt-show'), negate = cond.charAt(0) === '!';
		if (negate) {
			cond = cond.substring(1);
		}
		var eq = cond.indexOf('='), visible;
		if (eq > 0) {
			var value = symoptGet(sym, cond.substring(0, eq));
			visible = $.inArray(String(value), cond.substring(eq + 1).split('|')) >= 0;
		} else {
			var v = symoptGet(sym, cond);
			visible = !!v && v !== 'none';
		}
		$(this).toggle(negate ? !visible : visible);
	});
};

/** Enlaza los controles del modal con el simbolizador. onChange se llama tras cada cambio. */
SymbolOptions.bind = function(sym, onChange) {
	var content = $('#tab-content');
	content.off(SymbolOptions.EVENTS);
	content.on('input' + SymbolOptions.EVENTS, 'input[type=range][data-symopt]', function() {
		$(this).siblings('output').text(this.value + '%');
	});
	// números y colores: también mientras se escribe o se arrastra (el evento change solo llega al
	// salir del campo o pulsar Intro), con una pequeña espera para no pedir una vista previa por tecla
	content.on('input' + SymbolOptions.EVENTS, 'input[type=number][data-symopt], input[type=color][data-symopt]', function() {
		var input = this;
		clearTimeout(input._symoptTimer);
		input._symoptTimer = setTimeout(function() {
			if (input.value !== '') {
				$(input).trigger('change');
			}
		}, 400);
	});
	content.on('change' + SymbolOptions.EVENTS, '[data-symopt]', function() {
		var value = symoptCoerce(this);
		if (this.getAttribute('data-type') === 'dash') {
			if (value === null) {
				$(this).addClass('is-invalid');
				return;
			}
			$(this).removeClass('is-invalid');
			content.find('[data-symopt-choice="col:stroke_dash_array"]').removeClass('active').attr('aria-checked', 'false');
		}
		var path = this.getAttribute('data-symopt');
		symoptSet(sym, path, value);
		// otros controles de la misma columna (p. ej. color de relleno y color de fondo de la trama)
		content.find('[data-symopt="' + path + '"]').not(this).each(function() {
			if (this.type === 'range') {
				this.value = Math.round(Number(value) * 100);
				$(this).siblings('output').text(this.value + '%');
			} else if (this.type !== 'checkbox' && this.getAttribute('data-type') !== 'dash') {
				this.value = value;
			}
		});
		SymbolOptions.refreshVisibility(sym);
		onChange();
	});
	content.on('click' + SymbolOptions.EVENTS, '[data-symopt-choice]', function() {
		var path = this.getAttribute('data-symopt-choice');
		var value = this.getAttribute('data-value');
		$(this).closest('.gol-symopt-choice').find('.gol-symopt-option').removeClass('active').attr('aria-checked', 'false');
		$(this).addClass('active').attr('aria-checked', 'true');
		if (path === 'col:stroke_dash_array') {
			content.find('.gol-symopt-dash-input').val('').removeClass('is-invalid');
		}
		symoptSet(sym, path, value);
		if (sym.afterChoice) {
			sym.afterChoice(path, value);
		}
		SymbolOptions.refreshVisibility(sym);
		onChange();
	});
	SymbolOptions.refreshVisibility(sym);
};

// ---------------------------------------------------------------------------- vista previa

SymbolOptions.isGeometry = function(sym) {
	return !!(sym && SymbolOptions.kindOf(sym));
};

/** ¿Alguno de estos simbolizadores necesita la vista previa del servidor? */
SymbolOptions.anyAdvanced = function(symbolizers) {
	for (var i = 0; i < symbolizers.length; i++) {
		if (SymbolOptions.isGeometry(symbolizers[i]) && SymbolOptions.needed(symbolizers[i])) {
			return true;
		}
	}
	return false;
};

/** URL de la vista previa del servidor para estos simbolizadores (en orden de dibujo). */
SymbolOptions.previewUrl = function(previewUrl, symbolizers, width, height) {
	var items = [];
	for (var i = 0; i < symbolizers.length; i++) {
		if (SymbolOptions.isGeometry(symbolizers[i])) {
			items.push({type: symbolizers[i].type, json: symbolizers[i].toJSON()});
		}
	}
	var params = {url: previewUrl, symbolizers: JSON.stringify(items)};
	if (width) {
		params.width = width;
		params.height = height;
	}
	return SymbolOptions.PREVIEW_URL + '?' + $.param(params);
};

/** Vista previa grande y fija en la parte superior del modal del simbolizador. */
SymbolOptions.livePreview = function(sym) {
	var box = $('#symopt-live');
	if (!box.length) {
		var anchor = $('#tab-menu').closest('.nav-tabs-custom');
		if (!anchor.length) {
			anchor = $('#tab-content');
		}
		anchor.before('<div id="symopt-live" class="gol-symopt-live" aria-live="polite"><img alt="' +
			symoptEsc(symoptT('Symbol preview')) + '"><span class="gol-symopt-live-note"></span></div>');
		box = $('#symopt-live');
	}
	clearTimeout(SymbolOptions._liveTimer);
	SymbolOptions._liveTimer = setTimeout(function() {
		var url = sym.utils && sym.utils.getPreviewUrl ? sym.utils.getPreviewUrl() : null;
		if (!url) {
			box.hide();
			return;
		}
		box.show();
		box.find('img').attr('src', SymbolOptions.previewUrl(url, [sym], 240, 120));
		box.find('.gol-symopt-live-note').text(SymbolOptions.needed(sym) ? symoptT('Advanced symbol') : '');
	}, 250);
};

/** Quita lo que este módulo añade al modal (al abrir otro simbolizador, p. ej. una etiqueta). */
SymbolOptions.cleanup = function() {
	$('#symopt-live').remove();
	$('#tab-content').off(SymbolOptions.EVENTS);
	$('#modal-symbolizer .modal-dialog').removeClass('gol-symopt-dialog');
};

SymbolOptions.openDialog = function() {
	$('#modal-symbolizer .modal-dialog').addClass('gol-symopt-dialog');
};
