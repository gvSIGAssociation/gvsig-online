/**
 * gvSIG Online.
 * Copyright (C) 2026 SCOLAB.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 */

/**
 * «Sugerir estilo con IA» en simbología (lo aporta un plugin, p. ej. GeoAgents).
 *
 * Solo se carga si el servidor ofrece el asistente (plantillas _ai_style_*.html).
 * La propuesta se carga en el editor con las mismas llamadas que usan los
 * editores al crear reglas (Rule, setFilter, getTableUI, registerEvents,
 * addSymbolizer). NUNCA se guarda: el usuario revisa y pulsa Guardar.
 *
 * Desde «Elegir tipo de leyenda» la propuesta viaja al editor por sessionStorage
 * (clave por capa, caduca a los 10 minutos).
 */
var GolAiStyle = (function() {
	var STORAGE_PREFIX = 'gol-ai-style:';
	var PENDING_TTL_MS = 10 * 60 * 1000;
	var EDITOR_UI = {
		unique_symbol: {table: 'unique', events: 'unique'},
		unique_values: {table: 'unique_values', events: undefined},
		intervals: {table: 'intervals', events: 'intervals'}
	};
	var conf = {url: null, editors: {}, texts: {}};
	var current = null;  // {kind, editor, layerId, geometry}
	// Opciones con clic: cada una añade su texto (traducido en conf.texts) a la petición, que se puede editar
	var CHIPS = {
		chooser: ['chip_categories', 'chip_ranges'],
		common: ['chip_labels', 'chip_scale'],
		polygon: ['chip_hatch', 'chip_grid', 'chip_outline', 'chip_dashed_outline', 'chip_transparent'],
		line: ['chip_dashed', 'chip_dotted', 'chip_arrow_end', 'chip_arrows', 'chip_railway'],
		point: ['chip_diamond', 'chip_star', 'chip_no_fill', 'chip_larger'],
		refine: ['chip_thinner', 'chip_spaced', 'chip_softer', 'chip_no_labels']
	};
	var GEOMETRY = {PolygonSymbolizer: 'polygon', LineSymbolizer: 'line', PointSymbolizer: 'point'};
	var lastSpec = null; // propuesta aplicada en esta página (para retocarla)

	var text = function(key) {
		return conf.texts[key] || key;
	};

	var configure = function(options) {
		conf = $.extend(true, conf, options || {});
	};

	// --- Petición al servidor ------------------------------------------------

	var request = function(payload, done, fail) {
		$.ajax({
			type: 'POST',
			url: conf.url,
			contentType: 'application/json',
			data: JSON.stringify(payload),
			dataType: 'json',
			timeout: 120000,
			beforeSend: function(xhr) {
				xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
			},
			success: function(response) {
				if (response && $.isArray(response.rules) && response.rules.length && EDITOR_UI[response.type]) {
					done(response);
				} else {
					fail(text('invalid'));
				}
			},
			error: function(jqXHR, textStatus) {
				var message = text('unavailable');
				if (textStatus !== 'timeout' && jqXHR.responseJSON && jqXHR.responseJSON.error) {
					message = jqXHR.responseJSON.error;
				} else if (jqXHR.status === 401 || jqXHR.status === 403) {
					message = text('session');
				}
				fail(message);
			}
		});
	};

	// --- Propuesta pendiente (de «Elegir tipo de leyenda» al editor) ---------

	var storePending = function(layerId, proposal) {
		try {
			window.sessionStorage.setItem(STORAGE_PREFIX + layerId, JSON.stringify({t: Date.now(), p: proposal}));
			return true;
		} catch (e) {
			return false;
		}
	};

	var takePending = function(layerId, kind) {
		try {
			var key = STORAGE_PREFIX + layerId;
			var raw = window.sessionStorage.getItem(key);
			if (!raw) { return null; }
			window.sessionStorage.removeItem(key);
			var data = JSON.parse(raw);
			if (!data || !data.p || Date.now() - data.t > PENDING_TTL_MS || data.p.type !== kind) { return null; }
			return data.p;
		} catch (e) {
			return null;
		}
	};

	// --- Carga en el editor --------------------------------------------------

	var ensureOption = function($select, value) {
		if (!$select.length || value === null || value === undefined) { return; }
		var exists = $select.find('option').filter(function() { return this.value === value; }).length > 0;
		if (!exists) {
			$select.append($('<option>').val(value).text(value));
		}
		// Sin .trigger('change'): el cambio recargaría las reglas del editor
		$select.val(value);
	};

	var applyToEditor = function(kind, editor, proposal) {
		var ui = EDITOR_UI[kind];
		if (!ui || !editor || proposal.type !== kind) { return false; }
		// Escalas: si la propuesta trae alguna o es un retoque (en un retoque, '' = quitar el límite).
		// Una sugerencia nueva que no habla de escalas no borra las que haya puesto el usuario.
		var scales = proposal.scales || {};
		if (proposal.refined || scales.minscale !== '' || scales.maxscale !== '') {
			if (scales.minscale !== undefined) { $('#symbol-minscale').val(scales.minscale); }
			if (scales.maxscale !== undefined) { $('#symbol-maxscale').val(scales.maxscale); }
		}
		var minscale = $('#symbol-minscale').val();
		var maxscale = $('#symbol-maxscale').val();

		$('#rules').empty();
		editor.rules.splice(0, editor.rules.length);

		for (var i = 0; i < proposal.rules.length; i++) {
			var r = proposal.rules[i];
			// Símbolo único: la regla se llama como el estilo, igual que UniqueSymbol.addDefault
			var name = kind === 'unique_symbol' ? ($('#style-name').val() || r.name) : r.name;
			var options = {
				id: i, name: name, title: r.title, abstract: '', filter: '',
				minscale: minscale, maxscale: maxscale, order: i
			};
			var rule = new Rule(i, name, r.title, options, editor.utils);
			if (r.filter) {
				rule.setFilter($.extend({}, r.filter));
			}
			$('#rules').append(rule.getTableUI(true, ui.table));
			rule.registerEvents(ui.events);
			rule.addSymbolizer($.extend({}, r.symbolizer));
			rule.preview();
			editor.addRule(rule);
		}

		if (kind === 'unique_values') {
			ensureOption($('#select-unique-values-field'), proposal.field);
		} else if (kind === 'intervals') {
			ensureOption($('#select-numeric-field'), proposal.field);
			var between = $.grep(proposal.rules, function(r) { return r.filter && r.filter.operation === 'is_between'; });
			$('#number-of-intervals').val(between.length);
		}
		if (!$.trim($('#style-title').val() || '') && proposal.title) {
			$('#style-title').val(proposal.title).trigger('change');
		}
		// Etiquetas: set = cargar, remove = desactivar (retoque que las quita), keep = no tocar
		if (proposal.label_action === 'set' && proposal.label && typeof editor.loadLabel === 'function') {
			editor.loadLabel($.extend(true, {}, proposal.label));
		} else if (proposal.label_action === 'remove' && editor.label) {
			editor.label.is_actived = false;
		}
		lastSpec = proposal.spec || null;
		showInfo(proposal);
		return true;
	};

	var showInfo = function(proposal) {
		$('#gol-ai-style-info').remove();
		var $box = $('<div id="gol-ai-style-info" class="gol-ai-style-info" role="status"></div>');
		$box.append($('<button type="button" class="close" aria-label="Close">&times;</button>')
			.on('click', function() { $box.remove(); }));
		$box.append($('<p class="gol-ai-style-info__title"></p>')
			.append('<i class="fa fa-magic" aria-hidden="true"></i> ')
			.append($('<span></span>').text(text('proposal'))));
		if (proposal.explanation) {
			$box.append($('<p></p>').text(proposal.explanation));
		}
		if (proposal.warnings && proposal.warnings.length) {
			var $ul = $('<ul class="gol-ai-style-info__warnings"></ul>');
			$.each(proposal.warnings, function(_, w) { $ul.append($('<li></li>').text(w)); });
			$box.append($ul);
		}
		if (proposal.label_action === 'set') {
			$box.append($('<p></p>').text(text('labels_added')));
		} else if (proposal.label_action === 'remove') {
			$box.append($('<p></p>').text(text('labels_removed')));
		}
		$box.append($('<p class="gol-ai-style-info__review"></p>').text(text('review')));
		$('#rules').before($box);
	};

	// --- Ventana --------------------------------------------------------------

	var setBusy = function(busy) {
		var $go = $('#gol-ai-style-go');
		if (busy) {
			$go.data('idle', $go.data('idle') || $go.html());
			$go.prop('disabled', true).html('<i class="fa fa-spinner fa-spin" aria-hidden="true"></i> ' + $('<span>').text(text('busy')).html());
		} else {
			$go.prop('disabled', false).html($go.data('idle') || $go.html());
		}
	};

	var refining = function() {
		return !!lastSpec && $('#gol-ai-style-refine').is(':checked');
	};

	var renderChips = function() {
		var $box = $('#gol-ai-style-chips');
		if (!$box.length) { return; }
		var geometry = current ? current.geometry : null;
		var keys = refining() ? CHIPS.refine.concat(CHIPS[geometry] || [])
			: (current ? [] : CHIPS.chooser).concat(CHIPS[geometry] || [], CHIPS.common);
		$box.empty();
		$.each(keys, function(_, key) {
			if (!conf.texts[key]) { return; }
			$box.append($('<button type="button" class="gol-ai-style-chip"></button>').text(conf.texts[key]));
		});
	};

	var appendChip = function(chipText) {
		var $req = $('#gol-ai-style-request');
		var value = $.trim($req.val() || '').replace(/[\s,.;]+$/, '');
		var next = value ? value + ', ' + chipText.charAt(0).toLowerCase() + chipText.slice(1) : chipText;
		$req.val(next.substring(0, 300)).trigger('focus');
	};

	var openModal = function(replacing) {
		$('#gol-ai-style-error').text('');
		$('#gol-ai-style-replace').toggle(!!replacing);
		// Retocar solo si en esta página hay una propuesta aplicada
		$('#gol-ai-style-refine-box').toggle(!!lastSpec);
		$('#gol-ai-style-refine').prop('checked', !!lastSpec);
		renderChips();
		$('#modal-ai-style').modal('show');
	};

	var bindModal = function(onGo) {
		$('#gol-ai-style-chips').off('click.golai').on('click.golai', '.gol-ai-style-chip', function() {
			appendChip($(this).text());
		});
		$('#gol-ai-style-refine').off('change.golai').on('change.golai', renderChips);
		$('#gol-ai-style-go').off('click.golai').on('click.golai', function() {
			var payload = {request: $.trim($('#gol-ai-style-request').val() || '').substring(0, 300)};
			$('#gol-ai-style-error').text('');
			setBusy(true);
			onGo(payload, function() {
				setBusy(false);
				$('#modal-ai-style').modal('hide');
			}, function(message) {
				setBusy(false);
				$('#gol-ai-style-error').text(message);
			});
		});
	};

	/** Página «Elegir tipo de leyenda»: pide la propuesta y abre el editor de su tipo. */
	var initChooser = function(layerId) {
		$('#gol-ai-style-open').on('click', function(e) {
			e.preventDefault();
			openModal(false);
		});
		bindModal(function(payload, ok, fail) {
			request(payload, function(proposal) {
				var target = conf.editors[proposal.type];
				if (!target || !storePending(layerId, proposal)) {
					fail(text('invalid'));
					return;
				}
				ok();
				window.location.href = target;
			}, fail);
		});
	};

	/** Editor: botón «Sugerir con IA» y carga de una propuesta pendiente. */
	var attach = function(kind, editor, layerId, featureType) {
		if (!EDITOR_UI[kind] || !editor) { return; }
		current = {kind: kind, editor: editor, layerId: layerId, geometry: GEOMETRY[featureType] || null};
		$('#gol-ai-style-open').on('click', function(e) {
			e.preventDefault();
			openModal(editor.rules && editor.rules.length > 0);
		});
		bindModal(function(payload, ok, fail) {
			payload.type = kind;
			if (lastSpec && $('#gol-ai-style-refine').is(':checked')) {
				payload.previous = lastSpec;
			}
			var $field = kind === 'unique_values' ? $('#select-unique-values-field')
				: (kind === 'intervals' ? $('#select-numeric-field') : $());
			if ($field.length && $field.val()) {
				payload.field = $field.val();
			}
			request(payload, function(proposal) {
				if (applyToEditor(kind, editor, proposal)) {
					ok();
				} else {
					fail(text('invalid'));
				}
			}, fail);
		});
		// Después de que el editor termine de preparar la página (opciones de campos, etc.)
		setTimeout(function() {
			var pending = takePending(layerId, kind);
			if (pending) {
				applyToEditor(kind, editor, pending);
			}
		}, 0);
	};

	return {
		configure: configure,
		initChooser: initChooser,
		attach: attach,
		// para depuración y pruebas
		_applyToEditor: applyToEditor,
		_takePending: takePending,
		_storePending: storePending,
		_lastSpec: function() { return lastSpec; },
		_appendChip: appendChip,
		_renderChips: renderChips
	};
})();
