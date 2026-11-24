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

/* ——— Atajos canvas: copiar/pegar (Ctrl+C/V/D) y deshacer/rehacer (Ctrl+Z / Ctrl+Y) ——— */

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

function etlFigureRoot(figure) {
	if (!figure) {
		return null;
	}
	var current = figure;
	// Subir por padres hasta el nodo ETL (input_/trans_/…)
	while (current) {
		if (etlIsCopyableNode(current)) {
			return current;
		}
		if (typeof current.getParent === 'function' && current.getParent()) {
			current = current.getParent();
			continue;
		}
		break;
	}
	if (typeof figure.getRoot === 'function' && figure.getRoot()) {
		return figure.getRoot();
	}
	return figure;
}

/** Puertos de entrada/salida reales del nodo (están en las Labels hijas). */
function etlCollectLivePorts(figure, kind) {
	var ports = [];
	if (!figure) {
		return ports;
	}
	function takeFrom(fig) {
		if (!fig || typeof fig.getPorts !== 'function') {
			return;
		}
		fig.getPorts().each(function (i, port) {
			if (!port) {
				return;
			}
			var name = (typeof port.getName === 'function' ? port.getName() : port.name) || '';
			var isOutput = false;
			var isInput = false;
			try {
				isOutput = (typeof draw2d !== 'undefined' && draw2d.OutputPort && port instanceof draw2d.OutputPort)
					|| /output/i.test(name)
					|| /OutputPort/i.test(String(port.NAME || ''));
				isInput = (typeof draw2d !== 'undefined' && draw2d.InputPort && port instanceof draw2d.InputPort)
					|| /input/i.test(name)
					|| /InputPort/i.test(String(port.NAME || ''));
			} catch (errKind) {
				isOutput = /output/i.test(name);
				isInput = /input/i.test(name);
			}
			if (kind === 'output' && isOutput) {
				ports.push(port);
			} else if (kind === 'input' && isInput) {
				ports.push(port);
			}
		});
	}
	takeFrom(figure);
	if (typeof figure.getChildren === 'function') {
		figure.getChildren().each(function (i, entry) {
			takeFrom(entry && entry.figure ? entry.figure : entry);
		});
	}
	return ports;
}

function etlLivePortIndex(figure, kind, port) {
	var ports = etlCollectLivePorts(figure, kind);
	var name = port && (typeof port.getName === 'function' ? port.getName() : port.name);
	for (var i = 0; i < ports.length; i++) {
		if (ports[i] === port) {
			return i;
		}
		var n = typeof ports[i].getName === 'function' ? ports[i].getName() : ports[i].name;
		if (name && n === name) {
			return i;
		}
	}
	// Fallback listLabel (por si el puerto no aparece aún en hijos)
	if (figure && name) {
		var labeled = etlPortIndex(figure.id, kind, name);
		if (labeled >= 0) {
			return labeled;
		}
	}
	return -1;
}

function etlLivePortByIndex(figure, kind, index) {
	var ports = etlCollectLivePorts(figure, kind);
	if (typeof index === 'number' && index >= 0 && index < ports.length) {
		return ports[index];
	}
	return etlPortByIndex(figure, kind, index);
}

function etlNodeIdFromPort(port, nodeIdSet) {
	if (!port) {
		return null;
	}
	var fromLabel = typeof etlFigureIdOfPort === 'function' ? etlFigureIdOfPort(port) : null;
	if (fromLabel && (!nodeIdSet || nodeIdSet[fromLabel])) {
		return fromLabel;
	}
	var owner = etlFigureRoot(
		typeof port.getParent === 'function' ? port.getParent() : port.parent
	);
	if (owner && owner.id && (!nodeIdSet || nodeIdSet[owner.id])) {
		return owner.id;
	}
	return fromLabel || (owner && owner.id) || null;
}

function etlIsConnectionLine(line) {
	if (!line) {
		return false;
	}
	if (typeof draw2d !== 'undefined' && draw2d.Connection) {
		try {
			if (line instanceof draw2d.Connection) {
				return true;
			}
		} catch (errInst) {
		}
	}
	return (line.NAME === 'draw2d.Connection' || line.cssClass === 'draw2d.Connection')
		&& typeof line.getSource === 'function'
		&& typeof line.getTarget === 'function';
}

/** Puertos del nodo en el mismo orden que usa el guardado (inputs + outputs). */
function etlPortsSnapshot(figure) {
	var ports = [];
	if (!figure) {
		return ports;
	}
	var inputs = etlPortNames(figure.id, 'input');
	var outputs = etlPortNames(figure.id, 'output');
	var i;
	if (inputs.length || outputs.length) {
		for (i = 0; i < inputs.length; i++) {
			ports.push({name: inputs[i]});
		}
		for (i = 0; i < outputs.length; i++) {
			ports.push({name: outputs[i]});
		}
		return ports;
	}
	var liveIn = etlCollectLivePorts(figure, 'input');
	var liveOut = etlCollectLivePorts(figure, 'output');
	for (i = 0; i < liveIn.length; i++) {
		ports.push({
			name: typeof liveIn[i].getName === 'function' ? liveIn[i].getName() : liveIn[i].name
		});
	}
	for (i = 0; i < liveOut.length; i++) {
		ports.push({
			name: typeof liveOut[i].getName === 'function' ? liveOut[i].getName() : liveOut[i].name
		});
	}
	return ports;
}

function etlSnapshotNode(figure) {
	var type = String(figure.cssClass || figure.NAME || '');
	var stored = etlParamsForFigure(figure.id);
	var name = (figure.classLabel && typeof figure.classLabel.getText === 'function')
		? figure.classLabel.getText()
		: '';
	return {
		id: figure.id,
		type: type,
		name: name,
		x: typeof figure.getX === 'function' ? figure.getX() : 40,
		y: typeof figure.getY === 'function' ? figure.getY() : 40,
		ports: etlPortsSnapshot(figure),
		parameters: stored ? etlDeepClone(stored.parameters) || [] : [],
		schema: stored ? etlDeepClone(stored.schema) : undefined,
		'schema-old': stored ? etlDeepClone(stored['schema-old']) : undefined
	};
}

/** Nodos copiables de la selección actual (caja / multi-selección). */
function etlSelectedCopyableNodes(view) {
	var nodes = [];
	var seen = {};
	if (!view || typeof view.getSelection !== 'function') {
		return nodes;
	}
	var selection = view.getSelection();
	if (!selection || typeof selection.getAll !== 'function') {
		var primary = view.getPrimarySelection && view.getPrimarySelection();
		var primaryRoot = etlFigureRoot(primary);
		if (etlIsCopyableNode(primaryRoot)) {
			nodes.push(primaryRoot);
		}
		return nodes;
	}
	selection.getAll().each(function (i, figure) {
		var root = etlFigureRoot(figure);
		if (!etlIsCopyableNode(root) || seen[root.id]) {
			return;
		}
		seen[root.id] = true;
		nodes.push(root);
	});
	return nodes;
}

function etlPushInternalConnection(connections, seen, nodeIdSet, line) {
	if (!line || typeof line.getSource !== 'function' || typeof line.getTarget !== 'function') {
		return;
	}
	if (!line.getSource() || !line.getTarget()) {
		return;
	}
	var sourceId = null;
	var targetId = null;
	var sourcePortName = null;
	var targetPortName = null;
	try {
		if (typeof line.getPersistentAttributes === 'function') {
			var memento = line.getPersistentAttributes();
			if (memento && memento.source && memento.target) {
				sourceId = memento.source.node;
				targetId = memento.target.node;
				sourcePortName = memento.source.port;
				targetPortName = memento.target.port;
			}
		}
	} catch (errMem) {
	}
	if (!sourceId || !targetId) {
		var sourcePort = line.getSource();
		var targetPort = line.getTarget();
		sourceId = etlNodeIdFromPort(sourcePort, nodeIdSet);
		targetId = etlNodeIdFromPort(targetPort, nodeIdSet);
		sourcePortName = sourcePort && (typeof sourcePort.getName === 'function'
			? sourcePort.getName() : sourcePort.name);
		targetPortName = targetPort && (typeof targetPort.getName === 'function'
			? targetPort.getName() : targetPort.name);
	}
	if (!sourceId || !targetId || !nodeIdSet[sourceId] || !nodeIdSet[targetId]) {
		return;
	}
	if (!sourcePortName || !targetPortName) {
		return;
	}
	var key = sourceId + '/' + sourcePortName + '>' + targetId + '/' + targetPortName;
	if (seen[key]) {
		return;
	}
	seen[key] = true;
	connections.push({
		source: {node: sourceId, port: sourcePortName},
		target: {node: targetId, port: targetPortName}
	});
}

/**
 * Cables internos: mismo contrato que el JSON del canvas
 * (source/target.node + .port). Usa getPersistentAttributes de draw2d.
 */
function etlInternalConnections(view, nodeIdSet) {
	var connections = [];
	var seen = {};
	if (!view || !nodeIdSet) {
		return connections;
	}
	if (view.getLines) {
		view.getLines().each(function (i, line) {
			etlPushInternalConnection(connections, seen, nodeIdSet, line);
		});
	}
	// Respaldo: algunos cables solo aparecen en getConnections() de los puertos
	if (!connections.length && view.getFigures) {
		view.getFigures().each(function (fi, figure) {
			var root = etlFigureRoot(figure);
			if (!root || !nodeIdSet[root.id]) {
				return;
			}
			var allPorts = etlCollectLivePorts(root, 'output').concat(etlCollectLivePorts(root, 'input'));
			for (var p = 0; p < allPorts.length; p++) {
				var port = allPorts[p];
				if (!port || typeof port.getConnections !== 'function') {
					continue;
				}
				port.getConnections().each(function (ci, line) {
					etlPushInternalConnection(connections, seen, nodeIdSet, line);
				});
			}
		});
	}
	return connections;
}

function etlApplyNodeChrome(figure, type) {
	if (typeof etlApplyConfiguredChrome === 'function' && figure && figure.classLabel) {
		var gear = null;
		if (typeof etlFindGear === 'function') {
			var entry = etlFindGear(figure.classLabel);
			gear = entry && entry.figure;
		}
		etlApplyConfiguredChrome(gear, type, figure.classLabel);
	}
}

function etlCreatePastedFigure(nodeSnap) {
	var type = nodeSnap.type;
	var figure = (typeof createEtlFigure === 'function') ? createEtlFigure(type) : null;
	if (!figure) {
		var Ctor = window[type];
		if (typeof Ctor === 'function') {
			figure = new Ctor();
		}
	}
	if (!figure) {
		return null;
	}
	figure.addEntity('id');
	if (nodeSnap.name && typeof figure.setName === 'function') {
		figure.setName(nodeSnap.name);
	}
	var parameters = etlDeepClone(nodeSnap.parameters) || [];
	if (type === 'trans_AIAction' && typeof figure.syncPorts === 'function') {
		var p0 = parameters[0] || {};
		figure.syncPorts(p0.inputs_count || 1, p0.outputs_count || 1);
	}
	return {figure: figure, type: type, parameters: parameters};
}

/**
 * Copia la selección: uno o varios nodos y los cables entre ellos.
 * Arrastra un rectángulo en el canvas vacío para multi-seleccionar.
 */
function etlCopySelectedTransformer(view) {
	var nodes = etlSelectedCopyableNodes(view);
	if (!nodes.length) {
		return false;
	}
	var idSet = {};
	var snaps = [];
	for (var i = 0; i < nodes.length; i++) {
		idSet[nodes[i].id] = true;
		snaps.push(etlSnapshotNode(nodes[i]));
	}
	var connections = etlInternalConnections(view, idSet);
	window._etlNodeClipboard = {
		version: 2,
		nodes: snaps,
		connections: connections,
		// Compat con el formato anterior (un solo nodo)
		type: snaps[0].type,
		name: snaps[0].name,
		x: snaps[0].x,
		y: snaps[0].y,
		parameters: snaps[0].parameters,
		schema: snaps[0].schema,
		'schema-old': snaps[0]['schema-old']
	};
	window._etlPasteOffset = 0;
	return true;
}

/** Pega el último flujo copiado (nodos + cables internos), desplazado. */
function etlPasteTransformer(view) {
	var clip = window._etlNodeClipboard;
	if (!view || !clip) {
		return null;
	}
	var nodes = Array.isArray(clip.nodes) && clip.nodes.length
		? clip.nodes
		: (clip.type ? [clip] : []);
	if (!nodes.length) {
		return null;
	}
	var connections = Array.isArray(clip.connections) ? clip.connections : [];
	window._etlPasteOffset = (window._etlPasteOffset || 0) + 1;
	var dx = 40 * window._etlPasteOffset;
	var dy = 40 * window._etlPasteOffset;
	var stack = view.getCommandStack();
	var ownTransaction = false;
	if (stack && !stack.isInTransaction()) {
		stack.startTransaction('etl-paste');
		ownTransaction = true;
	}
	var idMap = {};
	var restored = [];
	var pasted = [];
	try {
		for (var i = 0; i < nodes.length; i++) {
			var created = etlCreatePastedFigure(nodes[i]);
			if (!created) {
				continue;
			}
			var figure = created.figure;
			idMap[nodes[i].id] = figure.id;
			isAlreadyInCanvas(jsonParams, {
				id: figure.id,
				parameters: created.parameters,
				schema: etlDeepClone(nodes[i].schema),
				'schema-old': etlDeepClone(nodes[i]['schema-old'])
			}, figure.id);
			stack.execute(new draw2d.command.CommandAdd(
				view, figure, (nodes[i].x || 40) + dx, (nodes[i].y || 40) + dy
			));
			if (typeof fillEtlNodeForm === 'function') {
				fillEtlNodeForm(created.type, figure, created.parameters, nodes[i]['schema-old']);
			}
			etlApplyNodeChrome(figure, created.type);
			var arrayPorts = etlPortNames(figure.id, 'input').concat(etlPortNames(figure.id, 'output'));
			if (!arrayPorts.length) {
				var liveIn = etlCollectLivePorts(figure, 'input');
				var liveOut = etlCollectLivePorts(figure, 'output');
				arrayPorts = liveIn.concat(liveOut).map(function (p) {
					return typeof p.getName === 'function' ? p.getName() : p.name;
				});
			}
			restored.push({
				oldId: nodes[i].id,
				figure: figure,
				oldPorts: nodes[i].ports || [],
				arrayPorts: arrayPorts
			});
			pasted.push(figure);
		}
		for (var c = 0; c < connections.length; c++) {
			var conn = connections[c];
			var src = conn.source || {};
			var tgt = conn.target || {};
			// Compat con el formato anterior (índices)
			if (!src.node && conn.sourceId) {
				src = {node: conn.sourceId, port: null};
			}
			if (!tgt.node && conn.targetId) {
				tgt = {node: conn.targetId, port: null};
			}
			var newSourceId = idMap[src.node];
			var newTargetId = idMap[tgt.node];
			if (!newSourceId || !newTargetId) {
				continue;
			}
			var sourceFigure = view.getFigure(newSourceId) || etlFigureById(view, newSourceId, restored);
			var targetFigure = view.getFigure(newTargetId) || etlFigureById(view, newTargetId, restored);
			if (!sourceFigure || !targetFigure) {
				continue;
			}
			var sourcePort = null;
			var targetPort = null;
			// getPorts() cachea hijos: forzar recálculo tras crear el nodo
			sourceFigure.cachedPorts = null;
			targetFigure.cachedPorts = null;
			if (src.port) {
				var srcName = remapPortName(src.node, src.port, restored);
				sourcePort = etlPortOnFigure(sourceFigure, srcName)
					|| etlPortOnFigure(sourceFigure, src.port);
				if (!sourcePort) {
					sourcePort = etlLivePortByIndex(
						sourceFigure, 'output',
						etlPortIndex(src.node, 'output', src.port)
					);
				}
			} else if (typeof conn.sourcePort === 'number') {
				sourcePort = etlLivePortByIndex(sourceFigure, 'output', conn.sourcePort);
			}
			if (tgt.port) {
				var tgtName = remapPortName(tgt.node, tgt.port, restored);
				targetPort = etlPortOnFigure(targetFigure, tgtName)
					|| etlPortOnFigure(targetFigure, tgt.port);
				if (!targetPort) {
					targetPort = etlLivePortByIndex(
						targetFigure, 'input',
						etlPortIndex(tgt.node, 'input', tgt.port)
					);
				}
			} else if (typeof conn.targetPort === 'number') {
				targetPort = etlLivePortByIndex(targetFigure, 'input', conn.targetPort);
			}
			if (!sourcePort || !targetPort) {
				continue;
			}
			var connection = etlStyledConnection();
			connection.setSource(sourcePort);
			connection.setTarget(targetPort);
			stack.execute(new draw2d.command.CommandAdd(view, connection, 0, 0));
			if (typeof propagateSchemaFrom === 'function' && targetFigure) {
				try {
					propagateSchemaFrom(targetFigure.id, view, {skipStart: true});
				} catch (errProp) {
				}
			}
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
	if (pasted.length && typeof view.setCurrentSelection === 'function') {
		if (pasted.length === 1 || typeof draw2d === 'undefined' || !draw2d.util || !draw2d.util.ArrayList) {
			view.setCurrentSelection(pasted[0]);
		} else {
			var list = new draw2d.util.ArrayList();
			for (var s = 0; s < pasted.length; s++) {
				list.add(pasted[s]);
			}
			view.setCurrentSelection(list);
		}
	}
	return pasted.length === 1 ? pasted[0] : pasted;
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
		var stack = (typeof view.getCommandStack === 'function') ? view.getCommandStack() : null;
		// Ctrl+Z deshacer; Ctrl+Shift+Z o Ctrl+Y rehacer (misma pila que los botones Undo/Redo)
		if (key === 'z' && event.shiftKey) {
			if (stack && stack.canRedo && stack.canRedo()) {
				event.preventDefault();
				stack.redo();
			}
			return;
		}
		if (key === 'z') {
			if (stack && stack.canUndo && stack.canUndo()) {
				event.preventDefault();
				stack.undo();
			}
			return;
		}
		if (key === 'y') {
			if (stack && stack.canRedo && stack.canRedo()) {
				event.preventDefault();
				stack.redo();
			}
			return;
		}
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
