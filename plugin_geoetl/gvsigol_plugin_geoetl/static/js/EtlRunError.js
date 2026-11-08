/* global gettext */

/*
 * Error de la última ejecución del editor ETL, en una tarjeta legible y que se puede copiar.
 * Antes solo estaba en el tooltip del botón Ejecutar, que no se puede seleccionar.
 *
 * El estado de ejecución es por usuario, no por workspace: un error con id de nodo solo se enseña
 * si ese nodo está en el canvas abierto. Mientras no esté (el canvas aún se está cargando, o el
 * error es de otro flujo) no se pinta nada y se vuelve a mirar en la siguiente consulta de estado.
 */
var EtlRunError = (function () {
	var DISMISSED_KEY = 'etl-run-error-dismissed';
	var PATTERN = /^\s*ERROR:\s*In\s+(\S+?)(?:\s+\(([^)]+)\))?\s+Node\.\s*([\s\S]*)$/;
	var COPIED_MS = 2000;
	var GLOW_MS = 2500;
	var ASK_LIMIT = 6000;
	var shown = null;

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

	function dismissed() {
		try {
			return sessionStorage.getItem(DISMISSED_KEY);
		} catch (e) {
			return null;
		}
	}

	function setDismissed(message) {
		try {
			if (message === null) {
				sessionStorage.removeItem(DISMISSED_KEY);
			} else {
				sessionStorage.setItem(DISMISSED_KEY, message);
			}
		} catch (e) {
		}
	}

	function view() {
		return window.etlApp && window.etlApp.view;
	}

	function figureOf(id) {
		var canvas = view();
		return (canvas && id) ? canvas.getFigure(id) : null;
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
		button.on('click', function () {
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

	function hide() {
		shown = null;
		$('#etl-run-error').empty().prop('hidden', true);
	}

	function askAssistant(message, parsed, figure) {
		var where = figure && figure.etlAlias ? figure.etlAlias + ': ' : '';
		window.etlAssistantAsk(t('The flow failed with this error. Explain the cause and how to fix it:') + '\n' +
			where + String(parsed.detail).slice(0, ASK_LIMIT));
	}

	function render(message, parsed, figure) {
		var card = $('<div class="etl-run-error" role="alert"></div>');
		var close = $('<button type="button" class="etl-run-error__close"></button>').attr('aria-label', t('Close'))
			.append('<i class="fa fa-times" aria-hidden="true"></i>');
		close.on('click', function () {
			setDismissed(message);
			hide();
		});
		card.append($('<div class="etl-run-error__head"></div>')
			.append('<i class="fa fa-times-circle" aria-hidden="true"></i>')
			.append($('<strong></strong>').text(t('The run failed')))
			.append(close));
		if (figure) {
			card.append($('<div class="etl-run-error__node"></div>').append($('<span></span>').text(t('Node:') + ' '))
				.append($('<button type="button" class="btn-link"></button>').text(nodeName(figure)).on('click', function () {
					focusNode(figure);
				})));
		} else if (parsed.type) {
			card.append($('<div class="etl-run-error__node"></div>').text(t('Node:') + ' ' + parsed.type));
		}
		card.append($('<pre class="etl-run-error__detail" tabindex="0"></pre>').text(parsed.detail));
		var actions = $('<div class="etl-run-error__actions"></div>')
			.append(copyButton(message, 'btn btn-default btn-sm js-copy-error', t('Copy error')));
		if (typeof window.etlAssistantAsk === 'function') {
			actions.append($('<button type="button" class="btn btn-default btn-sm js-ask-assistant"></button>')
				.text(t('Ask the assistant')).on('click', function () {
					askAssistant(message, parsed, figure);
				}));
		}
		$('#etl-run-error').empty().append(card.append(actions)).prop('hidden', false);
	}

	/* Se llama con la respuesta de la consulta de estado, cada 5 s: no repinta si nada cambia,
	   para no perder el texto que el usuario esté seleccionando. */
	function update(data) {
		if (!data || ['', 'Running', 'Success', 'Error'].indexOf(data.status) === -1) {
			return;
		}
		if (data.status !== 'Error') {
			if (data.status === 'Running') {
				setDismissed(null);
			}
			hide();
			return;
		}
		var message = String(data.message || '');
		if (message === dismissed()) {
			hide();
			return;
		}
		if (message !== shown) {
			var parsed = parse(message);
			var figure = figureOf(parsed.id);
			if (parsed.id && !figure) {
				hide();
				return;
			}
			render(message, parsed, figure);
			shown = message;
		}
		// La tarjeta ya enseña el error: el tooltip del botón no tiene que repetirlo entero
		$('#button-run').attr('title', t('The last run failed. See the details above the canvas.'));
	}

	/* Lista de workspaces: añade Copiar al mensaje que acaba de abrir messageBox. */
	function addCopyToMessageBox(message) {
		$('#modal-error .messageBoxMsg').append($('<div style="margin-top:10px"></div>')
			.append(copyButton(String(message || ''), 'btn btn-default btn-xs js-copy-error', t('Copy error'))));
	}

	function init() {
		// Una ejecución nueva puede fallar igual antes de la siguiente consulta: que vuelva a verse
		$('#button-run').on('click', function () {
			setDismissed(null);
		});
	}

	return {parse: parse, update: update, addCopyToMessageBox: addCopyToMessageBox, init: init};
})();

$(function () {
	EtlRunError.init();
});
