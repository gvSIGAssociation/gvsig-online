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

function fillEtlNodeForm(type, figure, parameters, schemaold) {
	if (!parameters || !parameters.length || !parameters[0]) {
		return;
	}
	var multiIn = 0;
	Object.keys(parameters[0]).forEach(function (key) {
		try {
			if (!parameters[0][key]) {
				return;
			}
			if ($('#' + key + '-' + figure.id).is('select') && key.indexOf('epsg') === -1 && key.indexOf('option') === -1) {
				if (typeof schemaold !== 'undefined' && schemaold) {
					var options = Array.isArray(schemaold[multiIn]) ? schemaold[multiIn] : schemaold;
					for (var k = 0; k < options.length; k++) {
						$('#' + key + '-' + figure.id).append('<option>' + options[k] + '</option>');
					}
				}
			}
			if (key.indexOf('get_') === 0) {
				var key_ = key.replace('get_', '');
				for (var n = 0; n < parameters[0][key].length; n++) {
					if (Array.isArray(parameters[0][key][n])) {
						$('#' + key_ + '-' + figure.id).append(
							'<option value ="' + parameters[0][key][n][0] + '">' + parameters[0][key][n][1] + '</option>'
						);
					} else {
						$('#' + key_ + '-' + figure.id).append('<option>' + parameters[0][key][n] + '</option>');
					}
				}
			}
			multiIn = multiIn + 1;
			if ($('input:radio[name="' + key + '-' + figure.id + '"]').is(':radio')) {
				$('#' + String(parameters[0][key]).toLowerCase() + '-' + figure.id).attr('checked', true);
				$('#' + String(parameters[0][key]).toLowerCase() + '-' + figure.id).val(parameters[0][key]);
			} else if ($('#' + key + '-' + figure.id).is(':checkbox')) {
				$('#' + key + '-' + figure.id).attr('checked', true);
				$('#' + key + '-' + figure.id).val(parameters[0][key]);
			} else {
				$('#' + key + '-' + figure.id).val(parameters[0][key]);
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
			var arrayPorts = [];
			for (var j = 0; j < listLabel.length; j++) {
				if (listLabel[j][0] === figure.id) {
					arrayPorts = (listLabel[j][1] || []).concat(listLabel[j][2] || []);
					break;
				}
			}
			var oldId = cnv[o].id;
			restored.push({
				oldId: oldId,
				figure: figure,
				oldPorts: cnv[o].ports || [],
				arrayPorts: arrayPorts
			});
			idMap[oldId] = figure.id;
			var entity = (cnv[o].entities && cnv[o].entities[0]) ? cnv[o].entities[0] : {};
			var parameters = entity.parameters || [];
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
		var oldPorts = restored[j].oldPorts || [];
		for (var k = 0; k < oldPorts.length; k++) {
			if (oldPorts[k] && oldPorts[k].name === portName) {
				return restored[j].arrayPorts[k];
			}
		}
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
