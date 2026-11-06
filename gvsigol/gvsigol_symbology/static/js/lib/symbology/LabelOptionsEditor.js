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
 * Editor de las opciones avanzadas de etiquetado (TextSymbolizer.options).
 *
 * - Una etiqueta sin opciones es una etiqueta «clásica»: se guarda y se dibuja como siempre
 *   (options = null). Solo cambia si el usuario pulsa «Usar opciones avanzadas».
 * - Al convertirla, las opciones se rellenan para que se vea como la clásica (posición,
 *   desplazamiento, ajuste de línea...), y a partir de ahí se pueden cambiar.
 * - El esquema y sus límites son los de gvsigol_symbology/label_options.py; el servidor
 *   vuelve a validarlo todo al guardar.
 * - Solo añade pestañas y controles al modal de la etiqueta: no cambia los existentes.
 */

var LabelOptionsEditor = function(symbolizer) {
	this.sym = symbolizer;
	this.kind = LabelOptionsEditor.geometryKind(symbolizer.utils ? symbolizer.utils.featureType : null);
	this.fields = (symbolizer.utils && symbolizer.utils.getAlphanumericFields()) || [];
	this.language = $("#select-language").val();
};

LabelOptionsEditor.EVENTS = '.lbladv';
LabelOptionsEditor.MAX_PARTS = 10;
LabelOptionsEditor.MAX_TEXT = 100;
LabelOptionsEditor.POSITIONS = ['top-left', 'top', 'top-right', 'left', 'center', 'right', 'bottom-left', 'bottom', 'bottom-right'];
LabelOptionsEditor.NUMBER_LOCALES = ['es', 'ca', 'en', 'de', 'fr', 'it', 'pt'];
LabelOptionsEditor.DATE_FORMATS = ['dd/MM/yyyy', 'dd-MM-yyyy', 'yyyy-MM-dd', 'MM/yyyy', 'yyyy', 'dd/MM/yyyy HH:mm'];
LabelOptionsEditor.SAMPLE_NUMBER = 12345.678;
LabelOptionsEditor.SAMPLE_DATE = new Date(2024, 2, 15, 9, 30);

/** Texto guardado (o el objeto ya leído) -> objeto de opciones, o null si es una etiqueta clásica. */
LabelOptionsEditor.parse = function(raw) {
	var data = raw;
	if (!raw) {
		return null;
	}
	if (typeof raw === 'string') {
		try {
			data = JSON.parse(raw);
		} catch (e) {
			return null;
		}
	}
	if (!data || typeof data !== 'object' || $.isEmptyObject(data)) {
		return null;
	}
	return LabelOptionsEditor.complete(data);
};

/** Completa con los valores por defecto del esquema v1 (como label_options.DEFAULTS). */
LabelOptionsEditor.complete = function(data) {
	var d = {
		v: 1,
		content: {case: 'none'},
		placement: {
			point: {position: 'top', dx: 0, dy: 0},
			line: {follow: true, repeat: 0, offset: 0, max_angle: 25},
			polygon: {mode: 'interior'},
			rotation: {angle: 0, field: null},
			wrap: 120
		},
		priority: {field: null, allow_overlap: false, space_around: 0},
		style: {letter_spacing: 0, halo: true},
		background: {type: 'none', fill: '#ffffff', fill_opacity: 1, stroke: '#000000', stroke_width: 1, padding: 2}
	};
	return $.extend(true, d, data, {v: 1});
};

/**
 * Opciones iniciales al convertir una etiqueta clásica: reproducen su aspecto en GeoServer
 * (sld_builder, rama antigua): puntos encima del punto a 1,5 alturas de letra, líneas
 * horizontales separadas 15 px y polígonos en el centroide.
 */
LabelOptionsEditor.fromLegacy = function(sym, kind) {
	var size = parseInt(sym.font_size, 10) || 12;
	var options = LabelOptionsEditor.complete({});
	if (sym.label) {
		options.content.parts = [{type: 'field', name: sym.label}];
	}
	if (kind === 'point') {
		options.placement.point = {position: 'top', dx: 0, dy: Math.round(size * 1.5)};
	} else if (kind === 'line') {
		options.placement.line = {follow: false, repeat: 0, offset: 15, max_angle: 25};
	} else {
		options.placement.polygon = {mode: 'centroid'};
	}
	return options;
};

LabelOptionsEditor.geometryKind = function(featureType) {
	if (featureType === 'LineSymbolizer') {
		return 'line';
	}
	if (featureType === 'PolygonSymbolizer') {
		return 'polygon';
	}
	return 'point';
};

LabelOptionsEditor.isNumericBinding = function(binding) {
	return /^java\.(math\.|lang\.(Integer|Long|Short|Byte|Float|Double|Number)$)/.test(binding || '');
};

LabelOptionsEditor.isDateBinding = function(binding) {
	return /^java\.(sql\.(Date|Timestamp)|util\.Date)$/.test(binding || '');
};

LabelOptionsEditor.clamp = function(value, lo, hi, def, integer) {
	var n = parseFloat(value);
	if (isNaN(n)) {
		return def;
	}
	n = Math.max(lo, Math.min(hi, n));
	return integer ? Math.round(n) : n;
};

/** Textos del editor con contexto «symbology» (evita colisiones con otros catálogos). */
function lblT(msgid) {
	return (typeof pgettext === 'function') ? pgettext('symbology', msgid) : gettext(msgid);
}

function lblEsc(value) {
	return symbologyEscapeHtml(value == null ? '' : String(value));
}

function lblPad2(n) {
	return n < 10 ? '0' + n : String(n);
}

/** Misma lógica que el SPA (labelExtras.js) y que numberFormat/dateFormat de GeoServer. */
LabelOptionsEditor.formatNumber = function(value, number) {
	var decimals = LabelOptionsEditor.clamp(number.decimals, 0, 6, 0, true);
	try {
		return new Intl.NumberFormat(number.locale || 'en', {
			minimumFractionDigits: decimals,
			maximumFractionDigits: decimals,
			useGrouping: !!number.thousands
		}).format(value);
	} catch (e) {
		return Number(value).toFixed(decimals);
	}
};

LabelOptionsEditor.formatDate = function(date, pattern) {
	var tokens = {
		yyyy: String(date.getFullYear()),
		MM: lblPad2(date.getMonth() + 1),
		dd: lblPad2(date.getDate()),
		HH: lblPad2(date.getHours()),
		mm: lblPad2(date.getMinutes())
	};
	return pattern.replace(/yyyy|MM|dd|HH|mm/g, function(t) { return tokens[t]; });
};

LabelOptionsEditor.prototype.options = function() {
	return this.sym.labelOptions;
};

LabelOptionsEditor.prototype.field = function(name) {
	for (var i = 0; i < this.fields.length; i++) {
		if (this.fields[i].name === name) {
			return this.fields[i];
		}
	}
	return null;
};

LabelOptionsEditor.prototype.fieldTitle = function(field) {
	return field['title-' + this.language] || field.name;
};

LabelOptionsEditor.prototype.fieldOptions = function(selected, filter, emptyLabel) {
	var ui = '';
	if (emptyLabel) {
		ui += '<option value="">' + lblEsc(emptyLabel) + '</option>';
	}
	for (var i = 0; i < this.fields.length; i++) {
		var f = this.fields[i];
		if (filter && !filter(f)) {
			continue;
		}
		ui += '<option value="' + lblEsc(f.name) + '"' + (f.name === selected ? ' selected' : '') + '>' + lblEsc(this.fieldTitle(f)) + '</option>';
	}
	return ui;
};

function lblNumericField(f) {
	return LabelOptionsEditor.isNumericBinding(f.binding);
}

function lblSelectOptions(values, selected) {
	var ui = '';
	for (var i = 0; i < values.length; i++) {
		ui += '<option value="' + lblEsc(values[i][0]) + '"' + (values[i][0] === selected ? ' selected' : '') + '>' + lblEsc(values[i][1]) + '</option>';
	}
	return ui;
}

function lblCheckbox(id, checked, text) {
	return '<div class="checkbox gol-lbl-check"><label><input type="checkbox" id="' + id + '"' + (checked ? ' checked' : '') + '> ' + text + '</label></div>';
}

function lblNumber(id, label, value, min, max, step, unit) {
	var ui = '<div class="form-group gol-lbl-field">';
	ui += '<label for="' + id + '">' + label + '</label>';
	ui += '<div class="gol-lbl-unit">';
	ui += '<input id="' + id + '" type="number" class="form-control" min="' + min + '" max="' + max + '" step="' + (step || 1) + '" value="' + lblEsc(value) + '">';
	if (unit) {
		ui += '<span class="gol-lbl-unit-text">' + unit + '</span>';
	}
	ui += '</div></div>';
	return ui;
}

function lblWmsOnly() {
	return '<span class="gol-lbl-badge" title="' + lblEsc(lblT('The web viewer (SPA) does not hide overlapping labels, so these options only affect WMS maps (GeoServer).')) + '">' + lblT('WMS maps only') + '</span>';
}

/* ------------------------------------------------------------------ montaje */

/** Añade al modal (ya pintado por la leyenda) el selector de formato y, si procede, las pestañas avanzadas. */
LabelOptionsEditor.prototype.mount = function() {
	this.unmount();
	$('#label-general-tab').append(this.getModeUI());
	if (this.options()) {
		$('#halo-tab').after(this.getTabMenu());
		var panes = this.getContentTabUI() + this.getPlacementTabUI() + this.getBackgroundTabUI();
		if ($('#label-filter-tab').length) {
			$('#label-filter-tab').before(panes);
		} else {
			$('#tab-content').append(panes);
		}
		$('#tab-content').prepend(this.getPreviewUI());
		this.renderParts();
		this.toggleLabelFieldSelect(true);
		this.refreshDependent();
	} else {
		this.toggleLabelFieldSelect(false);
	}
	this.registerEvents();
	this.updatePreview();
};

LabelOptionsEditor.prototype.unmount = function() {
	$('#tab-content').off(LabelOptionsEditor.EVENTS);
	$('#lbl-adv-mode, .gol-lbl-tab, #label-content-tab, #label-placement-tab, #label-background-tab, #lbl-adv-preview, #lbl-adv-label-hint').remove();
};

/** Vuelve a pintar todo manteniendo la pestaña activa (al cambiar de clásica a avanzada o al revés). */
LabelOptionsEditor.prototype.remount = function(showTab) {
	this.mount();
	if (this.sym.initializeForm) {
		this.sym.initializeForm();
	}
	$('.nav-tabs a[href="' + (showTab || '#label-general-tab') + '"]').tab('show');
};

/** En modo avanzado el texto se define en «Contenido»: el desplegable clásico se oculta. */
LabelOptionsEditor.prototype.toggleLabelFieldSelect = function(advanced) {
	var group = $('#label-label').closest('.form-group');
	$('#lbl-adv-label-hint').remove();
	if (advanced) {
		group.hide();
		group.after('<p id="lbl-adv-label-hint" class="gol-lbl-hint"><i class="fa fa-info-circle" aria-hidden="true"></i> ' +
			lblT('The label text is defined in the Content tab.') + '</p>');
	} else {
		group.show();
	}
};

/* ------------------------------------------------------------------ interfaz */

LabelOptionsEditor.prototype.getModeUI = function() {
	var advanced = !!this.options();
	var ui = '<div id="lbl-adv-mode" class="gol-lbl-mode' + (advanced ? ' is-advanced' : '') + '">';
	ui += '<div class="gol-lbl-mode-icon" aria-hidden="true"><i class="fa ' + (advanced ? 'fa-sliders' : 'fa-font') + '"></i></div>';
	ui += '<div class="gol-lbl-mode-body">';
	if (advanced) {
		ui += '<strong>' + lblT('Advanced label options') + '</strong>';
		ui += '<span>' + lblT('Compose the text, format numbers and dates, choose the position, a background and the priority.') + '</span>';
	} else {
		ui += '<strong>' + lblT('Classic label') + '</strong>';
		ui += '<span>' + lblT('This label keeps its current look. Advanced options let you compose the text, format numbers and dates, choose the position, add a background and set priorities.') + '</span>';
	}
	ui += '</div>';
	if (advanced) {
		ui += '<button type="button" id="lbl-adv-disable" class="btn btn-default btn-sm">' + lblT('Back to classic label') + '</button>';
	} else {
		ui += '<button type="button" id="lbl-adv-enable" class="btn btn-primary btn-sm"><i class="fa fa-sliders" aria-hidden="true"></i> ' + lblT('Use advanced options') + '</button>';
	}
	ui += '</div>';
	return ui;
};

LabelOptionsEditor.prototype.getTabMenu = function() {
	var ui = '';
	ui += '<li id="label-content-tab-item" class="gol-lbl-tab"><a href="#label-content-tab" data-toggle="tab">' + lblT('Content') + '</a></li>';
	ui += '<li id="label-placement-tab-item" class="gol-lbl-tab"><a href="#label-placement-tab" data-toggle="tab">' + lblT('Placement') + '</a></li>';
	ui += '<li id="label-background-tab-item" class="gol-lbl-tab"><a href="#label-background-tab" data-toggle="tab">' + lblT('Background') + '</a></li>';
	return ui;
};

LabelOptionsEditor.prototype.getPreviewUI = function() {
	var ui = '<div id="lbl-adv-preview" class="gol-lbl-preview" aria-live="polite">';
	ui += '<span class="gol-lbl-preview-caption">' + lblT('Preview') + '</span>';
	ui += '<div class="gol-lbl-preview-stage"><span class="gol-lbl-preview-text"></span></div>';
	ui += '</div>';
	return ui;
};

LabelOptionsEditor.prototype.getContentTabUI = function() {
	var o = this.options();
	var ui = '<div class="tab-pane" id="label-content-tab">';
	ui += '<div class="gol-lbl-section">';
	ui += '<h5 class="gol-lbl-section-title">' + lblT('Label text') + '</h5>';
	ui += '<p class="gol-lbl-hint">' + lblT('Combine fields and fixed text. Numbers and dates can be formatted.') + '</p>';
	ui += '<div id="lbl-adv-parts" class="gol-lbl-parts"></div>';
	ui += '<div class="gol-lbl-actions">';
	ui += '<button type="button" id="lbl-adv-add-field" class="btn btn-default btn-sm"><i class="fa fa-plus" aria-hidden="true"></i> ' + lblT('Field') + '</button>';
	ui += '<button type="button" id="lbl-adv-add-text" class="btn btn-default btn-sm"><i class="fa fa-plus" aria-hidden="true"></i> ' + lblT('Text') + '</button>';
	ui += '</div>';
	ui += '</div>';

	ui += '<div class="gol-lbl-section gol-lbl-grid">';
	ui += '<div class="form-group gol-lbl-field">';
	ui += '<label for="lbl-adv-case">' + lblT('Capitalization') + '</label>';
	ui += '<select id="lbl-adv-case" class="form-control">' + lblSelectOptions([
		['none', lblT('As in the data')], ['upper', lblT('UPPERCASE')], ['lower', lblT('lowercase')]
	], o.content['case']) + '</select>';
	ui += '</div>';
	ui += lblNumber('lbl-adv-letter-spacing', lblT('Letter spacing'), o.style.letter_spacing, -5, 30, 0.5, 'px');
	ui += lblNumber('lbl-adv-wrap', lblT('Wrap text at'), o.placement.wrap, 0, 2000, 10, 'px');
	ui += '</div>';
	ui += '<p class="gol-lbl-hint">' + lblT('Wrap: maximum line width before breaking the text into several lines (0 = never).') + '</p>';
	ui += '</div>';
	return ui;
};

LabelOptionsEditor.prototype.getPartUI = function(part, index, total) {
	var ui = '<div class="gol-lbl-part" data-index="' + index + '">';
	ui += '<span class="gol-lbl-part-kind">' + (part.type === 'field' ? lblT('Field') : lblT('Text')) + '</span>';
	ui += '<div class="gol-lbl-part-body">';
	if (part.type === 'field') {
		var field = this.field(part.name);
		var binding = field ? field.binding : '';
		var format = part.number ? 'number' : (part.date ? 'date' : 'none');
		ui += '<select class="form-control lbl-part-field" aria-label="' + lblEsc(lblT('Field')) + '">';
		if (!field && part.name) {
			ui += '<option value="' + lblEsc(part.name) + '" selected>' + lblEsc(part.name) + '</option>';
		}
		ui += this.fieldOptions(part.name) + '</select>';
		var formats = [['none', lblT('No format')]];
		if (LabelOptionsEditor.isNumericBinding(binding) || part.number) {
			formats.push(['number', lblT('Number')]);
		}
		if (LabelOptionsEditor.isDateBinding(binding) || part.date) {
			formats.push(['date', lblT('Date')]);
		}
		if (formats.length > 1) {
			ui += '<select class="form-control lbl-part-format" aria-label="' + lblEsc(lblT('Format')) + '">' + lblSelectOptions(formats, format) + '</select>';
		}
		if (part.number) {
			ui += '<div class="gol-lbl-part-format">';
			ui += '<label>' + lblT('Decimals') + ' <input type="number" class="form-control lbl-part-decimals" min="0" max="6" step="1" value="' + lblEsc(part.number.decimals) + '"></label>';
			ui += '<label class="gol-lbl-inline-check"><input type="checkbox" class="lbl-part-thousands"' + (part.number.thousands ? ' checked' : '') + '> ' + lblT('Thousands separator') + '</label>';
			ui += '<label>' + lblT('Language') + ' <select class="form-control lbl-part-locale">' + lblSelectOptions([
				['es', '1.234,5'], ['ca', '1.234,5 (ca)'], ['en', '1,234.5'], ['de', '1.234,5 (de)'], ['fr', '1 234,5'], ['it', '1.234,5 (it)'], ['pt', '1.234,5 (pt)']
			], part.number.locale || 'en') + '</select></label>';
			ui += '</div>';
		} else if (part.date) {
			var dateFormats = [];
			for (var i = 0; i < LabelOptionsEditor.DATE_FORMATS.length; i++) {
				var f = LabelOptionsEditor.DATE_FORMATS[i];
				dateFormats.push([f, LabelOptionsEditor.formatDate(LabelOptionsEditor.SAMPLE_DATE, f)]);
			}
			ui += '<div class="gol-lbl-part-format">';
			ui += '<label>' + lblT('Date format') + ' <select class="form-control lbl-part-date">' + lblSelectOptions(dateFormats, part.date) + '</select></label>';
			ui += '</div>';
		}
	} else {
		ui += '<input type="text" class="form-control lbl-part-text" maxlength="' + LabelOptionsEditor.MAX_TEXT + '" value="' + lblEsc(part.value) + '" placeholder="' + lblEsc(lblT('e.g. " - " or " inhab."')) + '" aria-label="' + lblEsc(lblT('Text')) + '">';
	}
	ui += '</div>';
	ui += '<div class="gol-lbl-part-tools">';
	ui += '<button type="button" class="btn btn-box-tool lbl-part-up" title="' + lblEsc(lblT('Move up')) + '"' + (index === 0 ? ' disabled' : '') + '><i class="fa fa-arrow-up" aria-hidden="true"></i></button>';
	ui += '<button type="button" class="btn btn-box-tool lbl-part-down" title="' + lblEsc(lblT('Move down')) + '"' + (index === total - 1 ? ' disabled' : '') + '><i class="fa fa-arrow-down" aria-hidden="true"></i></button>';
	ui += '<button type="button" class="btn btn-box-tool lbl-part-remove" title="' + lblEsc(lblT('Remove')) + '"' + (total <= 1 ? ' disabled' : '') + '><i class="fa fa-times" aria-hidden="true"></i></button>';
	ui += '</div>';
	ui += '</div>';
	return ui;
};

LabelOptionsEditor.prototype.renderParts = function() {
	var parts = this.parts();
	var ui = '';
	for (var i = 0; i < parts.length; i++) {
		ui += this.getPartUI(parts[i], i, parts.length);
	}
	$('#lbl-adv-parts').html(ui);
	var full = parts.length >= LabelOptionsEditor.MAX_PARTS;
	$('#lbl-adv-add-field, #lbl-adv-add-text').prop('disabled', full);
};

LabelOptionsEditor.prototype.getPlacementTabUI = function() {
	var o = this.options();
	var pl = o.placement;
	var ui = '<div class="tab-pane" id="label-placement-tab">';
	ui += '<div class="gol-lbl-section">';
	if (this.kind === 'point') {
		ui += '<h5 class="gol-lbl-section-title">' + lblT('Position relative to the point') + '</h5>';
		ui += '<div class="gol-lbl-placement-point">';
		ui += '<div class="gol-lbl-anchor-grid" role="radiogroup" aria-label="' + lblEsc(lblT('Position relative to the point')) + '">';
		for (var i = 0; i < LabelOptionsEditor.POSITIONS.length; i++) {
			var pos = LabelOptionsEditor.POSITIONS[i];
			var on = pos === pl.point.position;
			ui += '<button type="button" class="gol-lbl-anchor' + (on ? ' active' : '') + '" role="radio" aria-checked="' + (on ? 'true' : 'false') + '" data-position="' + pos + '" title="' + lblEsc(this.positionTitle(pos)) + '"><span></span></button>';
		}
		ui += '</div>';
		ui += '<div class="gol-lbl-grid">';
		ui += lblNumber('lbl-adv-dx', lblT('Horizontal offset'), pl.point.dx, -200, 200, 1, 'px');
		ui += lblNumber('lbl-adv-dy', lblT('Vertical offset'), pl.point.dy, -200, 200, 1, 'px');
		ui += '</div>';
		ui += '</div>';
		ui += '<p class="gol-lbl-hint">' + lblT('Positive offsets move the label right and up.') + '</p>';
	} else if (this.kind === 'line') {
		ui += '<h5 class="gol-lbl-section-title">' + lblT('Labels on lines') + '</h5>';
		ui += lblCheckbox('lbl-adv-follow', pl.line.follow, lblT('Follow the line (curved text)'));
		ui += '<div class="gol-lbl-grid">';
		ui += lblNumber('lbl-adv-max-angle', lblT('Maximum bend angle'), pl.line.max_angle, 0, 90, 1, '°');
		ui += lblNumber('lbl-adv-repeat', lblT('Repeat every'), pl.line.repeat, 0, 5000, 10, 'px');
		ui += lblNumber('lbl-adv-offset', lblT('Distance to the line'), pl.line.offset, -100, 100, 1, 'px');
		ui += '</div>';
		ui += '<p class="gol-lbl-hint">' + lblT('Repeat: 0 = one label per line. Distance: positive values place the label above the line.') + '</p>';
	} else {
		ui += '<h5 class="gol-lbl-section-title">' + lblT('Labels on polygons') + '</h5>';
		ui += '<div class="form-group gol-lbl-field">';
		ui += '<label for="lbl-adv-polygon-mode">' + lblT('Position') + '</label>';
		ui += '<select id="lbl-adv-polygon-mode" class="form-control">' + lblSelectOptions([
			['interior', lblT('Always inside the polygon')], ['centroid', lblT('Centroid (as classic labels)')]
		], pl.polygon.mode) + '</select>';
		ui += '</div>';
	}
	ui += '</div>';

	if (this.kind !== 'line') {
		ui += '<div class="gol-lbl-section">';
		ui += '<h5 class="gol-lbl-section-title">' + lblT('Rotation') + '</h5>';
		ui += '<div class="gol-lbl-grid">';
		ui += lblNumber('lbl-adv-angle', lblT('Angle'), pl.rotation.angle, -360, 360, 1, '°');
		ui += '<div class="form-group gol-lbl-field">';
		ui += '<label for="lbl-adv-rotation-field">' + lblT('Angle from a field') + '</label>';
		ui += '<select id="lbl-adv-rotation-field" class="form-control">' + this.fieldOptions(pl.rotation.field, lblNumericField, lblT('— None —')) + '</select>';
		ui += '</div>';
		ui += '</div>';
		ui += '<p class="gol-lbl-hint">' + lblT('Degrees, clockwise. If a field is chosen, its value is used instead of the fixed angle.') + '</p>';
		ui += '</div>';
	}

	ui += '<div class="gol-lbl-section">';
	ui += '<h5 class="gol-lbl-section-title">' + lblT('Overlapping labels') + ' ' + lblWmsOnly() + '</h5>';
	ui += lblCheckbox('lbl-adv-allow-overlap', o.priority.allow_overlap, lblT('Draw even if it overlaps other labels'));
	ui += '<div class="gol-lbl-grid">';
	ui += lblNumber('lbl-adv-space-around', lblT('Minimum space around'), o.priority.space_around, -20, 200, 1, 'px');
	ui += '<div class="form-group gol-lbl-field">';
	ui += '<label for="lbl-adv-priority-field">' + lblT('Priority field') + '</label>';
	ui += '<select id="lbl-adv-priority-field" class="form-control">' + this.fieldOptions(o.priority.field, lblNumericField, lblT('— None —')) + '</select>';
	ui += '</div>';
	ui += '</div>';
	ui += '<p class="gol-lbl-hint">' + lblT('When labels collide, those with a higher value in the priority field are drawn first.') + '</p>';
	ui += '</div>';
	ui += '</div>';
	return ui;
};

LabelOptionsEditor.prototype.positionTitle = function(pos) {
	var titles = {
		'top-left': lblT('Top left'), 'top': lblT('Top'), 'top-right': lblT('Top right'),
		'left': lblT('Left'), 'center': lblT('Center'), 'right': lblT('Right'),
		'bottom-left': lblT('Bottom left'), 'bottom': lblT('Bottom'), 'bottom-right': lblT('Bottom right')
	};
	return titles[pos] || pos;
};

LabelOptionsEditor.prototype.getBackgroundTabUI = function() {
	var bg = this.options().background;
	var ui = '<div class="tab-pane" id="label-background-tab">';
	ui += '<div class="gol-lbl-section">';
	ui += lblCheckbox('lbl-adv-bg-box', bg.type === 'box', lblT('Draw a box behind the label'));
	ui += '<div id="lbl-adv-bg-fields" class="gol-lbl-grid">';
	ui += '<div class="form-group gol-lbl-field"><label for="lbl-adv-bg-fill">' + lblT('Fill color') + '</label>';
	ui += '<input id="lbl-adv-bg-fill" type="color" class="form-control color-chooser" value="' + lblEsc(bg.fill) + '"></div>';
	ui += lblNumber('lbl-adv-bg-opacity', lblT('Fill opacity'), Math.round(bg.fill_opacity * 100), 0, 100, 5, '%');
	ui += '<div class="form-group gol-lbl-field"><label for="lbl-adv-bg-stroke">' + lblT('Border color') + '</label>';
	ui += '<input id="lbl-adv-bg-stroke" type="color" class="form-control color-chooser" value="' + lblEsc(bg.stroke) + '"></div>';
	ui += lblNumber('lbl-adv-bg-stroke-width', lblT('Border width'), bg.stroke_width, 0, 10, 0.5, 'px');
	ui += lblNumber('lbl-adv-bg-padding', lblT('Inner margin'), bg.padding, 0, 50, 1, 'px');
	ui += '</div>';
	// Limitación de GeoServer (ver label_sld.box_layout)
	ui += '<p class="gol-lbl-hint"><i class="fa fa-info-circle" aria-hidden="true"></i> ' +
		lblT('With a background, WMS maps (GeoServer) only split the text into several lines when the label is centered without rotation or placed to the right of the point; otherwise it is drawn on a single line.') + '</p>';
	ui += '</div>';
	ui += '</div>';
	return ui;
};

/* ------------------------------------------------------------------ estado */

LabelOptionsEditor.prototype.parts = function() {
	var o = this.options();
	if (!o.content.parts || !o.content.parts.length) {
		o.content.parts = this.sym.label ? [{type: 'field', name: this.sym.label}] : [];
	}
	return o.content.parts;
};

/** El campo «label» clásico sigue siendo el primer campo de la etiqueta (leyenda, compatibilidad). */
LabelOptionsEditor.prototype.syncLabelField = function() {
	var parts = this.parts();
	for (var i = 0; i < parts.length; i++) {
		if (parts[i].type === 'field' && parts[i].name) {
			this.sym.label = parts[i].name;
			$('#label-label').val(parts[i].name);
			return;
		}
	}
};

LabelOptionsEditor.prototype.refreshDependent = function() {
	var o = this.options();
	$('#lbl-adv-bg-fields').toggleClass('is-disabled', o.background.type !== 'box')
		.find('input').prop('disabled', o.background.type !== 'box');
	$('#lbl-adv-max-angle').prop('disabled', !o.placement.line.follow);
	$('#lbl-adv-repeat').prop('disabled', !o.placement.line.follow);
	$('#lbl-adv-angle').prop('disabled', !!o.placement.rotation.field);
};

LabelOptionsEditor.prototype.registerEvents = function() {
	var self = this;
	var ev = LabelOptionsEditor.EVENTS;
	var $root = $('#tab-content');

	$root.on('click' + ev, '#lbl-adv-enable', function() {
		self.sym.labelOptions = LabelOptionsEditor.fromLegacy(self.sym, self.kind);
		self.remount('#label-content-tab');
	});
	$root.on('click' + ev, '#lbl-adv-disable', function() {
		if (!window.confirm(lblT('The advanced options of this label will be discarded and it will be drawn as a classic label. Continue?'))) {
			return;
		}
		self.syncLabelField();
		self.sym.labelOptions = null;
		self.remount('#label-general-tab');
	});

	if (!this.options()) {
		return;
	}
	var o = this.options();
	var num = LabelOptionsEditor.clamp;
	var bind = function(selector, handler) {
		$root.on('change' + ev, selector, function() {
			handler.call(this, $(this));
			self.refreshDependent();
			self.updatePreview();
		});
	};

	// Contenido
	$root.on('click' + ev, '#lbl-adv-add-field, #lbl-adv-add-text', function() {
		var parts = self.parts();
		if (parts.length >= LabelOptionsEditor.MAX_PARTS) {
			return;
		}
		if (this.id === 'lbl-adv-add-field') {
			parts.push({type: 'field', name: self.fields.length ? self.fields[0].name : self.sym.label});
		} else {
			parts.push({type: 'text', value: ' '});
		}
		self.renderParts();
		self.updatePreview();
	});
	$root.on('click' + ev, '.lbl-part-up, .lbl-part-down, .lbl-part-remove', function() {
		var parts = self.parts();
		var i = parseInt($(this).closest('.gol-lbl-part').attr('data-index'), 10);
		if ($(this).hasClass('lbl-part-remove')) {
			if (parts.length > 1) {
				parts.splice(i, 1);
			}
		} else {
			var j = $(this).hasClass('lbl-part-up') ? i - 1 : i + 1;
			if (j >= 0 && j < parts.length) {
				var tmp = parts[i];
				parts[i] = parts[j];
				parts[j] = tmp;
			}
		}
		self.syncLabelField();
		self.renderParts();
		self.updatePreview();
	});
	var partOf = function($el) {
		return self.parts()[parseInt($el.closest('.gol-lbl-part').attr('data-index'), 10)];
	};
	bind('.lbl-part-field', function($el) {
		var part = partOf($el);
		part.name = $el.val();
		var field = self.field(part.name);
		if (part.number && !(field && LabelOptionsEditor.isNumericBinding(field.binding))) {
			delete part.number;
		}
		if (part.date && !(field && LabelOptionsEditor.isDateBinding(field.binding))) {
			delete part.date;
		}
		self.syncLabelField();
		self.renderParts();
	});
	bind('.lbl-part-format', function($el) {
		var part = partOf($el);
		delete part.number;
		delete part.date;
		if ($el.val() === 'number') {
			part.number = {decimals: 0, thousands: true, locale: 'es'};
		} else if ($el.val() === 'date') {
			part.date = LabelOptionsEditor.DATE_FORMATS[0];
		}
		self.renderParts();
	});
	bind('.lbl-part-decimals', function($el) {
		var part = partOf($el);
		part.number.decimals = num($el.val(), 0, 6, 0, true);
		$el.val(part.number.decimals);
	});
	bind('.lbl-part-thousands', function($el) { partOf($el).number.thousands = $el.is(':checked'); });
	bind('.lbl-part-locale', function($el) { partOf($el).number.locale = $el.val(); });
	bind('.lbl-part-date', function($el) { partOf($el).date = $el.val(); });
	$root.on('input' + ev + ' change' + ev, '.lbl-part-text', function() {
		partOf($(this)).value = String($(this).val()).substring(0, LabelOptionsEditor.MAX_TEXT);
		self.updatePreview();
	});
	bind('#lbl-adv-case', function($el) { o.content['case'] = $el.val(); });
	bind('#lbl-adv-letter-spacing', function($el) { o.style.letter_spacing = num($el.val(), -5, 30, 0); $el.val(o.style.letter_spacing); });
	bind('#lbl-adv-wrap', function($el) { o.placement.wrap = num($el.val(), 0, 2000, 120, true); $el.val(o.placement.wrap); });

	// Colocación
	$root.on('click' + ev, '.gol-lbl-anchor', function() {
		o.placement.point.position = $(this).attr('data-position');
		$('.gol-lbl-anchor').removeClass('active').attr('aria-checked', 'false');
		$(this).addClass('active').attr('aria-checked', 'true');
		self.updatePreview();
	});
	bind('#lbl-adv-dx', function($el) { o.placement.point.dx = num($el.val(), -200, 200, 0, true); $el.val(o.placement.point.dx); });
	bind('#lbl-adv-dy', function($el) { o.placement.point.dy = num($el.val(), -200, 200, 0, true); $el.val(o.placement.point.dy); });
	bind('#lbl-adv-follow', function($el) { o.placement.line.follow = $el.is(':checked'); });
	bind('#lbl-adv-max-angle', function($el) { o.placement.line.max_angle = num($el.val(), 0, 90, 25, true); $el.val(o.placement.line.max_angle); });
	bind('#lbl-adv-repeat', function($el) { o.placement.line.repeat = num($el.val(), 0, 5000, 0, true); $el.val(o.placement.line.repeat); });
	bind('#lbl-adv-offset', function($el) { o.placement.line.offset = num($el.val(), -100, 100, 0, true); $el.val(o.placement.line.offset); });
	bind('#lbl-adv-polygon-mode', function($el) { o.placement.polygon.mode = $el.val(); });
	bind('#lbl-adv-angle', function($el) { o.placement.rotation.angle = num($el.val(), -360, 360, 0); $el.val(o.placement.rotation.angle); });
	bind('#lbl-adv-rotation-field', function($el) { o.placement.rotation.field = $el.val() || null; });
	bind('#lbl-adv-allow-overlap', function($el) { o.priority.allow_overlap = $el.is(':checked'); });
	bind('#lbl-adv-space-around', function($el) { o.priority.space_around = num($el.val(), -20, 200, 0, true); $el.val(o.priority.space_around); });
	bind('#lbl-adv-priority-field', function($el) { o.priority.field = $el.val() || null; });

	// Fondo
	bind('#lbl-adv-bg-box', function($el) { o.background.type = $el.is(':checked') ? 'box' : 'none'; });
	bind('#lbl-adv-bg-fill', function($el) { o.background.fill = $el.val(); });
	bind('#lbl-adv-bg-opacity', function($el) {
		var pct = num($el.val(), 0, 100, 100, true);
		$el.val(pct);
		o.background.fill_opacity = pct / 100;
	});
	bind('#lbl-adv-bg-stroke', function($el) { o.background.stroke = $el.val(); });
	bind('#lbl-adv-bg-stroke-width', function($el) { o.background.stroke_width = num($el.val(), 0, 10, 1); $el.val(o.background.stroke_width); });
	bind('#lbl-adv-bg-padding', function($el) { o.background.padding = num($el.val(), 0, 50, 2, true); $el.val(o.background.padding); });

	// Fuente y halo (controles clásicos): solo se refresca la vista previa
	$root.on('change' + ev + ' slidechange' + ev, '#label-font-tab, #label-halo-tab', function() {
		self.updatePreview();
	});
};

/* ------------------------------------------------------------------ vista previa */

LabelOptionsEditor.prototype.sampleText = function() {
	var o = this.options();
	var parts = this.parts();
	var text = '';
	for (var i = 0; i < parts.length; i++) {
		var p = parts[i];
		if (p.type === 'text') {
			text += p.value || '';
		} else if (p.number) {
			text += LabelOptionsEditor.formatNumber(LabelOptionsEditor.SAMPLE_NUMBER, p.number);
		} else if (p.date) {
			text += LabelOptionsEditor.formatDate(LabelOptionsEditor.SAMPLE_DATE, p.date);
		} else {
			var field = this.field(p.name);
			text += field ? this.fieldTitle(field) : (p.name || '');
		}
	}
	if (o.content['case'] === 'upper') {
		text = text.toUpperCase();
	} else if (o.content['case'] === 'lower') {
		text = text.toLowerCase();
	}
	return text || lblT('Label');
};

function lblRgba(hex, opacity) {
	var m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex || '');
	if (!m) {
		return 'transparent';
	}
	var a = Math.max(0, Math.min(1, parseFloat(opacity)));
	if (isNaN(a)) {
		a = 1;
	}
	return 'rgba(' + parseInt(m[1], 16) + ', ' + parseInt(m[2], 16) + ', ' + parseInt(m[3], 16) + ', ' + a + ')';
}

LabelOptionsEditor.prototype.updatePreview = function() {
	var o = this.options();
	var $text = $('#lbl-adv-preview .gol-lbl-preview-text');
	if (!o || !$text.length) {
		return;
	}
	var s = this.sym;
	var size = Math.max(6, Math.min(72, parseInt(s.font_size, 10) || 12));
	var radius = parseFloat(s.halo_radius) || 0;
	var halo = 'none';
	if (o.style.halo && radius > 0 && parseFloat(s.halo_fill_opacity) > 0) {
		var hc = lblRgba(s.halo_fill, s.halo_fill_opacity);
		var r = Math.min(radius, 6);
		halo = [r + 'px 0 ' + hc, '-' + r + 'px 0 ' + hc, '0 ' + r + 'px ' + hc, '0 -' + r + 'px ' + hc,
			r + 'px ' + r + 'px ' + hc, '-' + r + 'px -' + r + 'px ' + hc, r + 'px -' + r + 'px ' + hc, '-' + r + 'px ' + r + 'px ' + hc].join(', ');
	}
	var bg = o.background;
	var box = bg.type === 'box';
	var wrap = o.placement.wrap;
	$text.text(this.sampleText()).css({
		'font-family': s.font_family || 'Arial',
		'font-size': size + 'px',
		'font-weight': s.font_weight || 'normal',
		'font-style': s.font_style || 'normal',
		'color': lblRgba(s.fill, s.fill_opacity === undefined ? 1 : s.fill_opacity),
		'letter-spacing': (o.style.letter_spacing || 0) + 'px',
		'text-shadow': halo,
		'max-width': wrap ? wrap + 'px' : 'none',
		'background-color': box ? lblRgba(bg.fill, bg.fill_opacity) : 'transparent',
		'border': box && bg.stroke_width > 0 ? bg.stroke_width + 'px solid ' + bg.stroke : '0',
		'padding': box ? bg.padding + 'px' : '0',
		'transform': (this.kind !== 'line' && !o.placement.rotation.field && o.placement.rotation.angle) ? 'rotate(' + o.placement.rotation.angle + 'deg)' : 'none'
	});
};
