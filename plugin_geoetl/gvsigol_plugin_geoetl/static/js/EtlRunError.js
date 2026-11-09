/* global gettext */

/*
 * Acciones sobre el error de la última ejecución en el panel de estado (abajo a la derecha):
 * Copiar error y, si el asistente ETL (GeoCopilot) está activo, Preguntar al asistente.
 *
 * El mensaje del error ya lo pinta el dock (#etl-run-status-dock). Aquí solo van los botones,
 * para no ocupar el canvas con otra franja arriba.
 */
var EtlRunError = (function () {
	var PATTERN = /^\s*ERROR:\s*In\s+(\S+?)(?:\s+\(([^)]+)\))?\s+Node\.\s*([\s\S]*)$/;
	var COPIED_MS = 2000;
	var GLOW_MS = 2500;
	var ASK_LIMIT = 6000;
	var dockMessage = null;
	var dockAsk = null;

	function t(text) {
		return (typeof gettext === 'function') ? gettext(text) : text;
	}

	function parse(message) {
		var text = String(message || '');
		var match = text.match(PATTERN);
		if (!match) {
			return {type: null, id: null, detail: text};
		}
		return {type: match[1], id: match[2] || null, detail: match[3] || text};
	}

	function view() {
		return window.etlApp && window.etlApp.view;
	}

	function figureOf(id) {
		var canvas = view();
		return (canvas && id) ? canvas.getFigure(id) : null;
	}

	function assistantReady() {
		return typeof window.etlAssistantAsk === 'function';
	}

	function copy(text, done) {
		function fallback() {
			var area = $('<textarea style="position:fixed;opacity:0"></textarea>').val(text).appendTo('body');
			area[0].select();
			var ok = false;
			try {
				ok = document.execCommand('copy');
			} catch (e) {
			}
			area.remove();
			done(ok);
		}
		if (navigator.clipboard && navigator.clipboard.writeText) {
			navigator.clipboard.writeText(text).then(function () {
				done(true);
			}, fallback);
		} else {
			fallback();
		}
	}

	function copyButton(text, classes, label) {
		var button = $('<button type="button"></button>').addClass(classes)
			.append('<i class="fa fa-clipboard" aria-hidden="true"></i> ')
			.append($('<span></span>').text(label));
		button.on('click', function (e) {
			e.preventDefault();
			e.stopPropagation();
			copy(text, function (ok) {
				if (ok) {
					button.find('span').text(t('Copied'));
					setTimeout(function () {
						button.find('span').text(label);
					}, COPIED_MS);
				}
			});
		});
		return button;
	}

	function askPrompt(parsed, figure) {
		var where = figure && figure.etlAlias ? figure.etlAlias + ': ' : '';
		return t('The flow failed with this error. Explain the cause and how to fix it:') + '\n' +
			where + String(parsed.detail).slice(0, ASK_LIMIT);
	}

	function askAssistant(message, parsed, figure) {
		if (!assistantReady()) {
			return;
		}
		window.etlAssistantAsk(askPrompt(parsed, figure));
	}

	function askButton(message, parsed, figure, classes) {
		return $('<button type="button"></button>').addClass(classes)
			.append('<i class="fa fa-comments" aria-hidden="true"></i> ')
			.append($('<span></span>').text(t('Ask the assistant')))
			.on('click', function (e) {
				e.preventDefault();
				e.stopPropagation();
				askAssistant(message, parsed, figure);
			});
	}

	function focusNode(figure) {
		var canvas = view();
		if (!canvas || !figure) {
			return;
		}
		canvas.setCurrentSelection(figure);
		var parent = document.getElementById('canvas-parent');
		if (parent) {
			parent.scrollLeft = Math.max(0, (figure.x || 0) - parent.clientWidth / 2);
			parent.scrollTop = Math.max(0, (figure.y || 0) - parent.clientHeight / 2);
		}
		if (figure.setGlow) {
			figure.setGlow(true);
			setTimeout(function () {
				figure.setGlow(false);
			}, GLOW_MS);
		}
	}

	function nodeName(figure) {
		var label = figure.classLabel && figure.classLabel.getText ? figure.classLabel.getText() : figure.NAME;
		return figure.etlAlias ? label + ' (' + figure.etlAlias + ')' : label;
	}

	function clearDockActions() {
		dockMessage = null;
		dockAsk = null;
		$('#etl-run-status-dock__actions').empty().prop('hidden', true);
		$('#etl-run-error').empty().prop('hidden', true);
	}

	function syncDockActions(message) {
		var $actions = $('#etl-run-status-dock__actions');
		if (!$actions.length) {
			return;
		}
		if (!message) {
			clearDockActions();
			return;
		}
		var ask = assistantReady();
		if (dockMessage === message && dockAsk === ask) {
			return;
		}
		dockMessage = message;
		dockAsk = ask;
		var parsed = parse(message);
		var figure = figureOf(parsed.id);
		$actions.empty().prop('hidden', false);
		if (figure) {
			$actions.append($('<button type="button" class="btn btn-link btn-sm js-focus-node"></button>')
				.text(t('Node:') + ' ' + nodeName(figure))
				.on('click', function (e) {
					e.preventDefault();
					e.stopPropagation();
					focusNode(figure);
				}));
		}
		$actions.append(copyButton(message, 'btn btn-default btn-sm js-copy-error', t('Copy error')));
		if (ask) {
			$actions.append(askButton(message, parsed, figure, 'btn btn-default btn-sm js-ask-assistant'));
		}
	}

	/* Se llama con la respuesta de la consulta de estado. */
	function update(data) {
		if (!data || ['', 'Running', 'Success', 'Error'].indexOf(data.status) === -1) {
			return;
		}
		// Ya no hay franja arriba: dejar el contenedor vacío por si quedó algo antiguo en caché
		$('#etl-run-error').empty().prop('hidden', true);

		if (data.status !== 'Error') {
			clearDockActions();
			return;
		}
		var message = String(data.message || '');
		syncDockActions(message);
		$('#button-run').attr('title', t('The last run failed. See the details in the run status panel.'));
	}

	/* Lista de workspaces / messageBox: Copiar y, si hay asistente, Preguntar. */
	function addCopyToMessageBox(message) {
		var text = String(message || '');
		var parsed = parse(text);
		var row = $('<div style="margin-top:10px;display:flex;flex-wrap:wrap;gap:6px"></div>')
			.append(copyButton(text, 'btn btn-default btn-xs js-copy-error', t('Copy error')));
		if (assistantReady()) {
			row.append(askButton(text, parsed, null, 'btn btn-default btn-xs js-ask-assistant'));
		}
		$('#modal-error .messageBoxMsg').append(row);
	}

	function init() {
	}

	return {parse: parse, update: update, addCopyToMessageBox: addCopyToMessageBox, init: init};
})();

$(function () {
	EtlRunError.init();
});
