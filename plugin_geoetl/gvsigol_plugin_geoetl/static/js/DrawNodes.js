/* global jsonParams, listLabel, isAlreadyInCanvas, editablerestrictedly, gettext */

function createEtlFigure(type) {
	if (type === 'input_Postgres') {
		type = 'input_Postgis';
	}
	if (!/^(input_|output_|trans_|crea_)[A-Za-z0-9]+$/.test(type || '')) {
		return null;
	}
	var Ctor = window[type];
	if (typeof Ctor !== 'function') {
		return null;
	}
	return new Ctor();
}

/**
 * Remapea un nombre de puerto guardado al del nodo recreado.
 * Primero por índice (como siempre); si falla, por orden entre inputs/outputs.
 */
function etlRemapRestoredPort(oldPorts, newPortNames, oldPortName) {
	oldPorts = oldPorts || [];
	newPortNames = newPortNames || [];
	var i;
	for (i = 0; i < oldPorts.length; i++) {
		if (oldPorts[i] && oldPorts[i].name === oldPortName && newPortNames[i]) {
			return newPortNames[i];
		}
	}
	var kind = String(oldPortName || '').indexOf('output') === 0 ? 'output' : 'input';
	var oldIdx = 0;
	var foundOld = -1;
	for (i = 0; i < oldPorts.length; i++) {
		var n = (oldPorts[i] && oldPorts[i].name) || '';
		if (n.indexOf(kind) === 0) {
			if (n === oldPortName) {
				foundOld = oldIdx;
				break;
			}
			oldIdx++;
		}
	}
	if (foundOld < 0) {
		return oldPortName;
	}
	var newIdx = 0;
	for (i = 0; i < newPortNames.length; i++) {
		if (String(newPortNames[i] || '').indexOf(kind) === 0) {
			if (newIdx === foundOld) {
				return newPortNames[i];
			}
			newIdx++;
		}
	}
	return oldPortName;
}

function etlPortOnFigure(figure, name) {
	var found = null;
	if (!figure || !figure.getPorts) {
		return null;
	}
	figure.getPorts().each(function (i, port) {
		if (port.getName() === name) {
			found = port;
		}
	});
	return found;
}

function etlPortNames(figureId, kind) {
	for (var j = 0; j < listLabel.length; j++) {
		if (listLabel[j][0] === figureId) {
			return kind === 'output' ? (listLabel[j][2] || []) : (listLabel[j][1] || []);
		}
	}
	return [];
}

function etlPortByIndex(figure, kind, index) {
	if (!figure || typeof index !== 'number') {
		return null;
	}
	var names = etlPortNames(figure.id, kind);
	if (index < 0 || index >= names.length) {
		return null;
	}
	return etlPortOnFigure(figure, names[index]);
}

function etlPortIndex(figureId, kind, portName) {
	var names = etlPortNames(figureId, kind);
	return names.indexOf(portName);
}

function etlFigureIdOfPort(port) {
	if (!port || !port.getName) {
		return null;
	}
	var name = port.getName();
	for (var j = 0; j < listLabel.length; j++) {
		var inputs = listLabel[j][1] || [];
		var outputs = listLabel[j][2] || [];
		if (inputs.indexOf(name) !== -1 || outputs.indexOf(name) !== -1) {
			return listLabel[j][0];
		}
	}
	return null;
}

function etlFigureById(view, id, restored) {
	for (var i = 0; i < restored.length; i++) {
		if (restored[i].oldId === id || restored[i].figure.id === id) {
			return restored[i].figure;
		}
	}
	if (view && view.getFigure) {
		return view.getFigure(id);
	}
	return null;
}

function etlStyledConnection() {
	var connection = new draw2d.Connection({
		stroke: 1,
		outlineStroke: 1,
		outlineColor: '#141517',
		color: '#141517',
		router: new draw2d.layout.connection.SplineConnectionRouter()
	});
	connection.setTargetDecorator(
		new draw2d.decoration.connection.ArrowDecorator(15, 10).setBackgroundColor('#141517')
	);
	return connection;
}

function etlFindLine(view, sourceId, targetId, sourcePort, targetPort) {
	var found = null;
	view.getLines().each(function (i, line) {
		if (found) {
			return;
		}
		var source = line.getSource();
		var target = line.getTarget();
		if (!source || !target) {
			return;
		}
		var sourceFigure = etlFigureIdOfPort(source);
		var targetFigure = etlFigureIdOfPort(target);
		if (sourceFigure !== sourceId || targetFigure !== targetId) {
			return;
		}
		if (etlPortIndex(sourceFigure, 'output', source.getName()) !== sourcePort) {
			return;
		}
		if (etlPortIndex(targetFigure, 'input', target.getName()) !== targetPort) {
			return;
		}
		found = line;
	});
	return found;
}

/** Añade la opción a un select si no la tiene; val() ignora en silencio un valor sin opción. */
function etlEnsureOption($select, value, label) {
	var text = String(value);
	var exists = $select.find('option').filter(function () {
		return this.value === text;
	}).length > 0;
	if (!exists) {
		$select.append($('<option></option>').val(text).text(label === undefined ? text : label));
	}
}

/* Los campos SQL usan CodeMirror, que guarda su propio texto: sin esto, al aceptar el diálogo vuelve el SQL anterior. */
function etlSyncSqlEditor(key, id, value) {
	if (window.etlSqlEditors && window.etlSqlEditors[key + '-' + id] && typeof window.setEtlSqlEditorValue === 'function') {
		window.setEtlSqlEditorValue(key + '-' + id, value);
	}
}

function etlClearField(key, id) {
	var field = $('#' + key + '-' + id);
	if (!field.length) {
		return;
	}
	if (field.is(':checkbox')) {
		field.prop('checked', false).val('');
	} else if (!field.is(':radio')) {
		field.val('');
		etlSyncSqlEditor(key, id, '');
	}
}

/* exact: también vacía los campos cuyo valor llega vacío (cambios del asistente). */
function fillEtlNodeForm(type, figure, parameters, schemaold, exact) {
	if (!parameters || !parameters.length || !parameters[0]) {
		return;
	}
	var multiIn = 0;
	Object.keys(parameters[0]).forEach(function (key) {
		try {
			if (key === 'output_schema' || key === 'output_schemas' || key === 'input_schemas' || key === 'sqls') {
				return;
			}
			if (!parameters[0][key]) {
				if (exact) {
					etlClearField(key, figure.id);
				}
				return;
			}
			if ($('#' + key + '-' + figure.id).is('select') && key.indexOf('epsg') === -1 && key.indexOf('option') === -1) {
				if (typeof schemaold !== 'undefined' && schemaold) {
					var options = Array.isArray(schemaold[multiIn]) ? schemaold[multiIn] : schemaold;
					for (var k = 0; k < options.length; k++) {
						etlEnsureOption($('#' + key + '-' + figure.id), options[k]);
					}
				}
			}
			if (key.indexOf('get_') === 0) {
				var key_ = key.replace('get_', '');
				for (var n = 0; n < parameters[0][key].length; n++) {
					if (Array.isArray(parameters[0][key][n])) {
						etlEnsureOption($('#' + key_ + '-' + figure.id), parameters[0][key][n][0], parameters[0][key][n][1]);
					} else {
						etlEnsureOption($('#' + key_ + '-' + figure.id), parameters[0][key][n]);
					}
				}
			}
			multiIn = multiIn + 1;
			if ($('input:radio[name="' + key + '-' + figure.id + '"]').is(':radio')) {
				$('#' + String(parameters[0][key]).toLowerCase() + '-' + figure.id).attr('checked', true);
				$('#' + String(parameters[0][key]).toLowerCase() + '-' + figure.id).val(parameters[0][key]);
			} else if ($('#' + key + '-' + figure.id).is(':checkbox')) {
				var on = parameters[0][key] !== false && String(parameters[0][key]).toLowerCase() !== 'false';
				$('#' + key + '-' + figure.id).prop('checked', on);
				$('#' + key + '-' + figure.id).val(on ? parameters[0][key] : '');
			} else {
				var field = $('#' + key + '-' + figure.id);
				if (field.is('select')) {
					// Esquema, tabla y similares se cargan con un botón: aún no tienen esa opción
					[].concat(parameters[0][key]).forEach(function (value) {
						etlEnsureOption(field, value);
					});
				}
				field.val(parameters[0][key]);
				etlSyncSqlEditor(key, figure.id, parameters[0][key]);
			}
			if ((type.indexOf('input_') === 0 || type.indexOf('output_') === 0 || type === 'trans_ExecuteSQL') && editablerestrictedly) {
				$('#' + key + '-' + figure.id).prop('disabled', true);
				$('input:radio[name="' + key + '-' + figure.id + '"]').prop('disabled', true);
				$('[id$="accept-' + figure.id + '"]').prop('disabled', true);
			}
		} catch (e) {
		}
	});
}

/**
 * Pinta nodos y conexiones. options.transaction abre una transacción del
 * CommandStack si no hay otra abierta. options.view es el canvas.
 * Devuelve un mapa del id de entrada al id real de la figura.
 */
function drawNodes(cnv, options) {
	options = options || {};
	var view = options.view;
	var idMap = {};
	if (!view || !cnv || !cnv.length) {
		return idMap;
	}
	var stack = view.getCommandStack();
	var ownTransaction = false;
	if (options.transaction && !stack.isInTransaction()) {
		stack.startTransaction(options.label || 'etl-assistant');
		ownTransaction = true;
	}
	var restored = [];
	try {
		for (var o = 0; o < cnv.length; o++) {
			if (!cnv[o] || cnv[o].type === 'draw2d.Connection') {
				continue;
			}
			var type = cnv[o].type;
			var figure = createEtlFigure(type);
			if (!figure) {
				continue;
			}
			if (type === 'input_Postgres') {
				type = 'input_Postgis';
			}
			figure.addEntity('id');
			if (cnv[o].name && typeof figure.setName === 'function') {
				figure.setName(cnv[o].name);
			}
			var entity = (cnv[o].entities && cnv[o].entities[0]) ? cnv[o].entities[0] : {};
			var parameters = entity.parameters || [];
			// SQL con IA: restaurar N entradas / M salidas antes de cablear
			if (type === 'trans_AIAction' && typeof figure.syncPorts === 'function') {
				var p0 = parameters[0] || {};
				var restoredIn = parseInt(p0.inputs_count, 10) || 1;
				var restoredOut = parseInt(p0.outputs_count, 10) || 1;
				var savedPorts = cnv[o].ports || [];
				if ((!p0.inputs_count || !p0.outputs_count) && savedPorts.length) {
					var nInPorts = 0;
					var nOutPorts = 0;
					for (var pi = 0; pi < savedPorts.length; pi++) {
						var pname = String((savedPorts[pi] && savedPorts[pi].name) || '');
						if (pname.indexOf('input') === 0) {
							nInPorts++;
						} else if (pname.indexOf('output') === 0) {
							nOutPorts++;
						}
					}
					if (!p0.inputs_count && nInPorts) {
						restoredIn = nInPorts;
					}
					if (!p0.outputs_count && nOutPorts) {
						restoredOut = nOutPorts;
					}
				}
				figure.syncPorts(restoredIn, restoredOut);
			}
			var arrayPorts = [];
			for (var j = 0; j < listLabel.length; j++) {
				if (listLabel[j][0] === figure.id) {
					arrayPorts = (listLabel[j][1] || []).concat(listLabel[j][2] || []);
					break;
				}
			}
			// conserva el id corto guardado (o el nN que propone el asistente)
			if (typeof etlAliasFromDocument === 'function' && etlAliasFromDocument(cnv[o])) {
				figure.etlAlias = etlAliasFromDocument(cnv[o]);
			}
			var oldId = cnv[o].id;
			restored.push({
				oldId: oldId,
				figure: figure,
				oldPorts: cnv[o].ports || [],
				arrayPorts: arrayPorts
			});
			idMap[oldId] = figure.id;
			var schema = entity.schema;
			var schemaold = entity.schemaold;
			isAlreadyInCanvas(jsonParams, {
				id: figure.id,
				parameters: parameters,
				schema: schema,
				'schema-old': schemaold
			}, figure.id);
			stack.execute(new draw2d.command.CommandAdd(view, figure, cnv[o].x || 40, cnv[o].y || 40));
			fillEtlNodeForm(type, figure, parameters, schemaold);
		}

		for (var c = 0; c < cnv.length; c++) {
			if (!cnv[c] || cnv[c].type !== 'draw2d.Connection') {
				continue;
			}
			var sourceId = cnv[c].source && cnv[c].source.node;
			var targetId = cnv[c].target && cnv[c].target.node;
			var sourceFigure = etlFigureById(view, sourceId, restored);
			var targetFigure = etlFigureById(view, targetId, restored);
			if (!sourceFigure || !targetFigure) {
				continue;
			}
			var sourcePort = (typeof cnv[c].source_port === 'number')
				? etlPortByIndex(sourceFigure, 'output', cnv[c].source_port)
				: etlPortOnFigure(sourceFigure, remapPortName(sourceId, cnv[c].source.port, restored));
			var targetPort = (typeof cnv[c].target_port === 'number')
				? etlPortByIndex(targetFigure, 'input', cnv[c].target_port)
				: etlPortOnFigure(targetFigure, remapPortName(targetId, cnv[c].target.port, restored));
			if (!sourcePort || !targetPort) {
				continue;
			}
			var connection = etlStyledConnection();
			connection.setSource(sourcePort);
			connection.setTarget(targetPort);
			stack.execute(new draw2d.command.CommandAdd(view, connection, 0, 0));
		}
		if (ownTransaction) {
			stack.commitTransaction();
		}
	} catch (err) {
		if (ownTransaction && stack.isInTransaction()) {
			stack.transactionCommand = null;
		}
		throw err;
	}
	return idMap;
}

function remapPortName(nodeId, portName, restored) {
	for (var j = 0; j < restored.length; j++) {
		if (restored[j].oldId !== nodeId) {
			continue;
		}
		return etlRemapRestoredPort(restored[j].oldPorts, restored[j].arrayPorts, portName);
	}
	return portName;
}

function etlClearCanvas(view) {
	var stack = view.getCommandStack();
	var lines = view.getLines().clone();
	lines.each(function (i, line) {
		if (line.getCanvas()) {
			stack.execute(new draw2d.command.CommandDelete(line));
		}
	});
	var figures = view.getFigures().clone();
	figures.each(function (i, figure) {
		if (figure instanceof draw2d.Connection) {
			return;
		}
		if (figure.getCanvas()) {
			stack.execute(new draw2d.command.CommandDelete(figure));
		}
	});
}

var EtlApplyCommand = draw2d.command.Command.extend({
	init: function (apply, revert) {
		this._super('etl-assistant');
		this._apply = apply;
		this._revert = revert;
	},
	canExecute: function () {
		return true;
	},
	execute: function () {
		this._apply();
	},
	undo: function () {
		this._revert();
	},
	redo: function () {
		this.execute();
	}
});

/* ——— Copiar / pegar transformadores (Ctrl+C / Ctrl+V), sin cables ——— */

window._etlNodeClipboard = window._etlNodeClipboard || null;
window._etlPasteOffset = 0;

function etlIsEditableKeyboardTarget(target) {
	if (!target) {
		return false;
	}
	var tag = (target.tagName || '').toLowerCase();
	if (tag === 'input' || tag === 'textarea' || tag === 'select') {
		return true;
	}
	if (target.isContentEditable) {
		return true;
	}
	// CodeMirror / diálogos
	if (target.closest && (
		target.closest('.CodeMirror') ||
		target.closest('.modal') ||
		target.closest('.pl-assistant')
	)) {
		return true;
	}
	return false;
}

function etlIsCopyableNode(figure) {
	if (!figure || figure instanceof draw2d.Connection) {
		return false;
	}
	var type = String(figure.cssClass || figure.NAME || '');
	return type.indexOf('trans_') === 0
		|| type.indexOf('crea_') === 0
		|| type.indexOf('input_') === 0
		|| type.indexOf('output_') === 0;
}

function etlParamsForFigure(figureId) {
	if (typeof jsonParams === 'undefined' || !Array.isArray(jsonParams)) {
		return null;
	}
	for (var i = 0; i < jsonParams.length; i++) {
		if (jsonParams[i] && jsonParams[i].id === figureId) {
			return jsonParams[i];
		}
	}
	return null;
}

function etlDeepClone(value) {
	if (value == null) {
		return value;
	}
	try {
		return JSON.parse(JSON.stringify(value));
	} catch (err) {
		return null;
	}
}

/** Copia el nodo seleccionado (entrada/salida/transformador/creador) sin conexiones. */
function etlCopySelectedTransformer(view) {
	if (!view || typeof view.getPrimarySelection !== 'function') {
		return false;
	}
	var figure = view.getPrimarySelection();
	if (!etlIsCopyableNode(figure)) {
		return false;
	}
	var type = String(figure.cssClass || figure.NAME || '');
	var stored = etlParamsForFigure(figure.id);
	var name = (figure.classLabel && typeof figure.classLabel.getText === 'function')
		? figure.classLabel.getText()
		: '';
	window._etlNodeClipboard = {
		type: type,
		name: name,
		x: typeof figure.getX === 'function' ? figure.getX() : 40,
		y: typeof figure.getY === 'function' ? figure.getY() : 40,
		parameters: stored ? etlDeepClone(stored.parameters) || [] : [],
		schema: stored ? etlDeepClone(stored.schema) : undefined,
		'schema-old': stored ? etlDeepClone(stored['schema-old']) : undefined
	};
	window._etlPasteOffset = 0;
	return true;
}

/** Pega el último transformador copiado, desplazado y sin cables. */
function etlPasteTransformer(view) {
	var clip = window._etlNodeClipboard;
	if (!view || !clip || !clip.type) {
		return null;
	}
	var figure = (typeof createEtlFigure === 'function') ? createEtlFigure(clip.type) : null;
	if (!figure) {
		var Ctor = window[clip.type];
		if (typeof Ctor === 'function') {
			figure = new Ctor();
		}
	}
	if (!figure) {
		return null;
	}
	figure.addEntity('id');
	if (clip.name && typeof figure.setName === 'function') {
		figure.setName(clip.name);
	}
	var parameters = etlDeepClone(clip.parameters) || [];
	if (clip.type === 'trans_AIAction' && typeof figure.syncPorts === 'function') {
		var p0 = parameters[0] || {};
		figure.syncPorts(p0.inputs_count || 1, p0.outputs_count || 1);
	}
	window._etlPasteOffset = (window._etlPasteOffset || 0) + 1;
	var dx = 40 * window._etlPasteOffset;
	var dy = 40 * window._etlPasteOffset;
	var x = (clip.x || 40) + dx;
	var y = (clip.y || 40) + dy;
	isAlreadyInCanvas(jsonParams, {
		id: figure.id,
		parameters: parameters,
		schema: etlDeepClone(clip.schema),
		'schema-old': etlDeepClone(clip['schema-old'])
	}, figure.id);
	view.getCommandStack().execute(new draw2d.command.CommandAdd(view, figure, x, y));
	if (typeof fillEtlNodeForm === 'function') {
		fillEtlNodeForm(clip.type, figure, parameters, clip['schema-old']);
	}
	if (typeof etlApplyConfiguredChrome === 'function' && figure.classLabel) {
		var gear = null;
		if (typeof etlFindGear === 'function') {
			var entry = etlFindGear(figure.classLabel);
			gear = entry && entry.figure;
		}
		etlApplyConfiguredChrome(gear, clip.type, figure.classLabel);
	}
	if (typeof view.setCurrentSelection === 'function') {
		view.setCurrentSelection(figure);
	}
	return figure;
}

function etlInstallCopyPaste(view) {
	if (!view || view._etlCopyPasteInstalled) {
		return;
	}
	view._etlCopyPasteInstalled = true;
	$(document).on('keydown.etlCopyPaste', function (event) {
		if (!(event.ctrlKey || event.metaKey) || event.altKey) {
			return;
		}
		if (etlIsEditableKeyboardTarget(event.target)) {
			return;
		}
		var key = (event.key || '').toLowerCase();
		if (key === 'c') {
			if (etlCopySelectedTransformer(view)) {
				event.preventDefault();
			}
			return;
		}
		if (key === 'v') {
			if (window._etlNodeClipboard) {
				event.preventDefault();
				etlPasteTransformer(view);
			}
			return;
		}
		if (key === 'd') {
			// Atajo extra: duplicar selección al instante
			if (etlCopySelectedTransformer(view) && etlPasteTransformer(view)) {
				event.preventDefault();
			}
		}
	});
}
