/* global gettext, fm_directory, setGearColorForNode, jsonParams, drawNodes, etlClearCanvas, etlFindLine, EtlApplyCommand, fillEtlNodeForm, propagateSchemaFrom, etlFindGear */

(function () {
	var STORAGE_WIDTH = 'etl-assistant-width';
	var STORAGE_OPEN = 'etl-assistant-open';
	var UNDO_LABEL = 'etl-assistant';
	var COMPOSER_MAX_HEIGHT = 140;
	var OPTION_LISTS = {
		output_Postgis: {'schema-name-option': 'get_schema-name-option', tablename: 'get_tablename'},
		input_Postgis: {'schema-name': 'get_schema-name', tablename: 'get_tablename'},
		input_SqlServer: {'schema-name': 'get_schema-name', 'table-name': 'get_table-name'}
	};
	var UNDO_LABEL_PARAM = 'etl-assistant-param';   // cambio de un parámetro: no es la propuesta
	var panel, messagesEl, input, examplesEl, contextEl, sendBtn;
	var selectedFigure = null;
	var busy = false;
	var examplesShown = false;
	var aliasMap = {};
	var currentXhr = null;       // petición en curso (para Detener)
	var recall = -1;             // posición al recorrer las preguntas anteriores con ↑ / ↓
	var MESSAGE_LIMIT = 8000;    // mismo límite que el servidor (agent.py)
	var COUNTER_FROM = 7000;

	function workspaceKey() {
		var id = $('#etl_id').val();
		return 'etl-assistant-chat:' + (id || 'new');
	}

	function view() {
		return window.etlApp && window.etlApp.view;
	}

	function t(text) {
		return (typeof gettext === 'function') ? gettext(text) : text;
	}

	function loadState() {
		try {
			return JSON.parse(sessionStorage.getItem(workspaceKey()) || '{"messages":[]}');
		} catch (e) {
			return {messages: []};
		}
	}

	function saveState(state) {
		try {
			sessionStorage.setItem(workspaceKey(), JSON.stringify(state));
		} catch (e) {
		}
	}

	function familyOf(typeName) {
		if (!typeName) {
			return 'transform';
		}
		if (typeName.indexOf('input_') === 0) {
			return 'input';
		}
		if (typeName.indexOf('output_') === 0) {
			return 'output';
		}
		if (typeName.indexOf('crea_') === 0) {
			return 'creator';
		}
		return 'transform';
	}

	function typeIndex() {
		var index = {};
		var canvas = canvasSummary();
		(canvas.nodes || []).forEach(function (node) {
			index[node.alias] = node.type;
		});
		return index;
	}

	function renderMarkdown(text) {
		var raw = String(text || '');
		if (window.marked && window.DOMPurify && typeof marked.parse === 'function') {
			return DOMPurify.sanitize(marked.parse(raw));
		}
		return $('<div>').text(raw).html().replace(/\n/g, '<br>');
	}

	function aliasesIn(text) {
		var found = [];
		var match;
		var re = /\bn\d+\b/g;
		while ((match = re.exec(text || ''))) {
			if (found.indexOf(match[0]) === -1) {
				found.push(match[0]);
			}
		}
		return found;
	}

	function figureForAlias(alias) {
		var canvasView = view();
		if (!canvasView) {
			return null;
		}
		var found = null;
		canvasView.getFigures().each(function (i, figure) {
			if (!found && figure.etlAlias === alias) {
				found = figure;
			}
		});
		if (!found && aliasMap[alias]) {
			found = canvasView.getFigure(aliasMap[alias]);
		}
		return found;
	}

	// Convierte los n3, n12… del texto en etiquetas que resaltan y centran su nodo.
	function decorateAliases(container) {
		var root = container && container[0];
		if (!root || !document.createTreeWalker) {
			return;
		}
		var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
		var targets = [];
		var node;
		while ((node = walker.nextNode())) {
			if (/\bn\d+\b/.test(node.nodeValue) && !$(node.parentNode).closest('code, pre, a, .pl-assistant__alias').length) {
				targets.push(node);
			}
		}
		targets.forEach(function (textNode) {
			var parts = textNode.nodeValue.split(/(\bn\d+\b)/);
			var fragment = document.createDocumentFragment();
			parts.forEach(function (part) {
				if (/^n\d+$/.test(part) && figureForAlias(part)) {
					var chip = document.createElement('span');
					chip.className = 'pl-assistant__alias';
					chip.setAttribute('role', 'button');
					chip.setAttribute('tabindex', '0');
					chip.setAttribute('data-alias', part);
					chip.setAttribute('title', t('Show node on the canvas'));
					chip.textContent = part;
					fragment.appendChild(chip);
				} else if (part) {
					fragment.appendChild(document.createTextNode(part));
				}
			});
			textNode.parentNode.replaceChild(fragment, textNode);
		});
	}

	function copyText(text, button) {
		function done() {
			if (!button) {
				return;
			}
			var icon = button.find('i');
			icon.removeClass('fa-copy').addClass('fa-check');
			setTimeout(function () {
				icon.removeClass('fa-check').addClass('fa-copy');
			}, 1500);
		}
		function fallback() {
			var area = $('<textarea readonly></textarea>').val(text).css({position: 'fixed', top: '-1000px'});
			$('body').append(area);
			area[0].select();
			try {
				document.execCommand('copy');
				done();
			} catch (e) {
			}
			area.remove();
		}
		if (navigator.clipboard && navigator.clipboard.writeText) {
			navigator.clipboard.writeText(text).then(done, fallback);
		} else {
			fallback();
		}
	}

	function toolButton(icon, label, handler, extraClass) {
		var button = $('<button type="button" class="pl-assistant__tool"></button>')
			.attr('aria-label', label).attr('title', label)
			.append($('<i class="fa" aria-hidden="true"></i>').addClass(icon));
		if (extraClass) {
			button.addClass(extraClass);
		}
		button.on('click', function (event) {
			event.stopPropagation();
			handler(button);
		});
		return button;
	}

	function messageTools(message) {
		var bar = $('<div class="pl-assistant__tools"></div>');
		var text = message.content || '';
		if (message.role === 'user') {
			bar.append(toolButton('fa-copy', t('Copy'), function (button) {
				copyText(text, button);
			}));
			bar.append(toolButton('fa-pencil', t('Edit and resend'), function () {
				setInput(text);
			}));
			bar.append(toolButton('fa-repeat', t('Ask again'), function () {
				sendText(text);
			}));
		} else {
			bar.append(toolButton('fa-copy', t('Copy'), function (button) {
				copyText(assistantMarkdown(message), button);
			}));
			if (message.id && message.settled !== 'applied' && !(message.proposal && message.needsConfirmation && !message.settled)) {
				bar.append(toolButton('fa-refresh', t('Regenerate answer'), function () {
					regenerate(message.id);
				}, 'js-regenerate'));
			}
		}
		return bar;
	}

	function assistantMarkdown(message) {
		var lines = [message.content || ''];
		if (message.summary && message.summary.length) {
			lines.push('', t('Changes') + ':');
			message.summary.forEach(function (line) {
				lines.push('- ' + line);
			});
		}
		if (message.assumptions && message.assumptions.length) {
			lines.push('', t('Assumptions') + ':');
			message.assumptions.forEach(function (line) {
				lines.push('- ' + line);
			});
		}
		if (message.warnings && message.warnings.length) {
			lines.push('', t('Warnings') + ':');
			message.warnings.forEach(function (line) {
				lines.push('- ' + line);
			});
		}
		if (message.issues && message.issues.length) {
			lines.push('', t('Problems in the flow') + ':');
			message.issues.forEach(function (issue) {
				lines.push('- ' + issue.message);
			});
		}
		if (message.questions && message.questions.length) {
			lines.push('', t('The assistant needs to know') + ':');
			message.questions.forEach(function (question) {
				var answer = (message.answers || {})[question.id];
				lines.push('- ' + (question.text || question.label) + (answer ? ' → ' + answer : ''));
			});
		}
		return lines.join('\n').trim();
	}

	function setInput(text) {
		input.val(text);
		input.trigger('input');
		input.focus();
		var end = text.length;
		if (input[0].setSelectionRange) {
			input[0].setSelectionRange(end, end);
		}
	}

	// Quita la última respuesta (y su pregunta) y vuelve a preguntar.
	function regenerate(messageId) {
		if (busy) {
			return;
		}
		var state = loadState();
		var messages = state.messages || [];
		var index = -1;
		for (var i = 0; i < messages.length; i++) {
			if (messages[i].id === messageId) {
				index = i;
			}
		}
		var question = -1;
		for (var j = index - 1; j >= 0; j--) {
			if (messages[j].role === 'user') {
				question = j;
				break;
			}
		}
		if (index === -1 || question === -1) {
			return;
		}
		var text = messages[question].content;
		state.messages = messages.slice(0, question);
		saveState(state);
		renderAll();
		sendText(text);
	}

	function userQuestions() {
		return (loadState().messages || []).filter(function (message) {
			return message.role === 'user' && message.content;
		}).map(function (message) {
			return message.content;
		});
	}

	function updateCounter() {
		var counter = $('#etl-assistant-counter');
		var length = (input.val() || '').length;
		var over = length > MESSAGE_LIMIT;
		counter.toggleClass('is-over', over).prop('hidden', length < COUNTER_FROM)
			.text(length.toLocaleString() + ' / ' + MESSAGE_LIMIT.toLocaleString());
		if (!busy) {
			sendBtn.prop('disabled', over);
		}
	}

	function setBusy(on) {
		busy = on;
		input.prop('disabled', on);
		sendBtn.prop('disabled', false).toggleClass('is-stop', on)
			.attr('aria-label', on ? t('Stop') : t('Send')).attr('title', on ? t('Stop') : t('Send'));
		sendBtn.find('i').toggleClass('fa-paper-plane', !on).toggleClass('fa-stop', on);
		if (!on) {
			updateCounter();
		}
	}

	function exportConversation() {
		var state = loadState();
		var lines = ['# ' + t('Conversation with the ETL assistant'), ''];
		var name = $('#etl_name').val();
		if (name) {
			lines.push('**' + t('Workspace') + ':** ' + name, '');
		}
		(state.messages || []).forEach(function (message) {
			if (message.role === 'user') {
				lines.push('**' + t('You') + ':** ' + (message.content || ''), '');
			} else if (message.role === 'assistant') {
				lines.push('**' + t('Assistant') + ':** ' + assistantMarkdown(message), '');
				if (message.status) {
					lines.push('_' + message.status + '_', '');
				}
			} else if (message.role === 'error') {
				lines.push('> ' + (message.content || ''), '');
			}
		});
		var blob = new Blob([lines.join('\n')], {type: 'text/markdown;charset=utf-8'});
		var link = document.createElement('a');
		link.href = URL.createObjectURL(blob);
		link.download = 'asistente-etl-' + ($('#etl_id').val() || 'nuevo') + '.md';
		document.body.appendChild(link);
		link.click();
		setTimeout(function () {
			URL.revokeObjectURL(link.href);
			link.remove();
		}, 0);
	}

	function highlightAliases(aliases, on) {
		(aliases || []).forEach(function (alias) {
			var figure = figureForAlias(alias);
			if (figure && figure.setGlow) {
				figure.setGlow(!!on);
			}
		});
	}

	function focusAlias(alias) {
		var canvasView = view();
		var figure = figureForAlias(alias);
		if (!canvasView || !figure) {
			return;
		}
		canvasView.setCurrentSelection(figure);
		var parent = document.getElementById('canvas-parent');
		if (parent) {
			parent.scrollLeft = Math.max(0, (figure.x || 0) - parent.clientWidth / 2);
			parent.scrollTop = Math.max(0, (figure.y || 0) - parent.clientHeight / 2);
		}
	}

	function bindAliasHover(element, text) {
		var aliases = aliasesIn(text);
		element.on('mouseenter', function () {
			highlightAliases(aliases, true);
		});
		element.on('mouseleave', function () {
			highlightAliases(aliases, false);
		});
		element.on('click', function () {
			if (aliases.length) {
				focusAlias(aliases[0]);
			}
		});
	}

	function changeLine(text, types) {
		var alias = (aliasesIn(text)[0]) || '';
		var family = familyOf(types[alias]);
		var item = $('<li></li>');
		item.append($('<span class="pl-assistant__dot"></span>').addClass('pl-assistant__dot--' + family));
		item.append(document.createTextNode(text));
		bindAliasHover(item, text);
		return item;
	}

	function setExamplesVisible(show) {
		examplesShown = show;
		examplesEl.toggleClass('is-hidden', !show);
		refreshExamples();
	}

	function refreshExamples(summary) {
		if (!examplesEl || !examplesShown) {
			return;
		}
		summary = summary || canvasSummary();
		var mode = summary.nodes.length ? 'flow' : 'empty';
		if (mode !== 'empty') {
			closeGuided();
		}
		var selection = summary.selected ? 'yes' : 'no';
		examplesEl.find('.pl-assistant__example').each(function () {
			var button = $(this);
			var visible = button.attr('data-when') === mode;
			var needs = button.attr('data-selection');
			if (visible && needs) {
				visible = needs === selection;
			}
			button.toggle(visible);
		});
	}

	function appendMessage(message, types) {
		// Las sugerencias solo tienen sentido en la última respuesta
		messagesEl.find('.pl-assistant__next').remove();
		var row = $('<div class="pl-assistant__row"></div>');
		var avatar = $('<div class="pl-assistant__avatar"></div>');
		var body = $('<div class="pl-assistant__body"></div>');
		if (message.role === 'user') {
			row.addClass('pl-assistant__row--user');
			avatar.append($('<i class="fa fa-user"></i>'));
			body.append($('<div class="pl-assistant__bubble pl-assistant__bubble--user"></div>').text(message.content || ''));
			body.append(messageTools(message));
		} else if (message.role === 'error') {
			avatar.append($('<i class="fa fa-exclamation"></i>'));
			var errorBubble = $('<div class="pl-assistant__bubble pl-assistant__bubble--error"></div>').text(message.content || '');
			body.append(errorBubble);
			if (message.retry) {
				var retry = $('<button type="button" class="btn-default"></button>').text(t('Retry'));
				retry.on('click', function () {
					sendText(message.retry);
				});
				body.append($('<div class="pl-assistant__actions"></div>').append(retry));
			}
		} else {
			avatar.append($('<i class="fa fa-comments"></i>'));
			var bubble = $('<div class="pl-assistant__bubble"></div>');
			if (message.typing) {
				bubble.append('<span class="pl-assistant__typing" aria-hidden="true"><span></span><span></span><span></span></span>');
			} else {
				bubble.html(renderMarkdown(message.content || ''));
				decorateAliases(bubble);
			}
			body.append(bubble);
			if (message.summary && message.summary.length) {
				var list = $('<ul class="pl-assistant__changes"></ul>');
				message.summary.forEach(function (line) {
					list.append(changeLine(line, types || {}));
				});
				body.append($('<div class="pl-assistant__card"></div>').append(list));
			}
			if (message.assumptions && message.assumptions.length) {
				var details = $('<details class="pl-assistant__card" open></details>');
				details.append($('<summary></summary>').text(t('Assumptions')));
				var assumptions = $('<ul class="pl-assistant__assumptions"></ul>');
				message.assumptions.forEach(function (line) {
					var item = $('<li></li>').text(line);
					bindAliasHover(item, line);
					var choice = (message.assumptionChoices || []).filter(function (candidate) {
						return candidate.text === line;
					})[0];
					if (choice) {
						item.append(alternativeControl(message, choice));
					}
					assumptions.append(item);
				});
				details.append(assumptions);
				body.append(details);
			}
			if (message.warnings && message.warnings.length) {
				var warnings = $('<details class="pl-assistant__card pl-assistant__card--warn"></details>');
				warnings.append($('<summary></summary>').text(t('Warnings')));
				var warningList = $('<ul class="pl-assistant__assumptions"></ul>');
				message.warnings.forEach(function (line) {
					warningList.append($('<li></li>').text(line));
				});
				warnings.append(warningList);
				body.append(warnings);
			}
			if (message.issues && message.issues.length) {
				body.append(issuesCard(message));
			}
			if (message.questions && message.questions.length) {
				body.append(questionsCard(message));
			}
			if (message.actions) {
				body.append(message.actions);
			}
			if (message.status) {
				body.append($('<div class="pl-assistant__status"></div>').text(message.status));
			}
			if (message.nextSteps && message.nextSteps.length && message.settled !== 'undone' && message.settled !== 'discarded') {
				body.append(nextStepsBar(message));
			}
			if (!message.typing) {
				// Solo la última respuesta se puede regenerar.
				messagesEl.find('.js-regenerate').remove();
				body.append(messageTools(message));
			}
		}
		row.append(avatar).append(body);
		messagesEl.append(row);
		messagesEl.scrollTop(messagesEl[0].scrollHeight);
		return row;
	}

	// ------------------------------------------------------------------
	// Problemas del flujo con botones (ETL_ASSISTANT_ACTIONS)
	// ------------------------------------------------------------------

	// Se resuelven en el engranaje del nodo: no hace falta el modelo
	var CONFIGURE_CODES = ['unconfigured', 'missing_parameter', 'invalid_choice', 'invalid_schema',
		'unknown_connection', 'connection_type', 'unknown_column'];
	// Se piden al asistente
	var FIX_CODES = ['unconnected_input', 'duplicated_input', 'dead_end', 'no_output', 'cycle',
		'kind_mismatch', 'bad_port', 'source', 'target'];

	/* Abre el engranaje de un nodo con su propio manejador de clic, como si lo pulsara el usuario. */
	function openNodeConfig(alias) {
		var figure = figureForAlias(alias);
		if (!figure || typeof etlFindGear !== 'function') {
			return false;
		}
		var gear = etlFindGear(figure.classLabel);
		if (!gear || !gear.figure || typeof gear.figure.fireEvent !== 'function') {
			return false;
		}
		focusAlias(alias);
		try {
			gear.figure.fireEvent('click');
		} catch (e) {
			// El diálogo del nodo ha fallado: es el mismo error que al pulsar la rueda a mano
			return false;
		}
		return true;
	}

	function issuesCard(message) {
		var issues = message.issues;
		var card = $('<div class="pl-assistant__card pl-assistant__issues"></div>');
		card.append($('<div class="pl-assistant__card-title"></div>').text(t('Problems in the flow')));
		var list = $('<ul class="pl-assistant__issue-list"></ul>');
		var fixable = [];
		issues.forEach(function (issue, index) {
			var item = $('<li class="pl-assistant__issue"></li>').addClass('is-' + (issue.level || 'warning'));
			var text = $('<span class="pl-assistant__issue-text"></span>').text(issue.message || '');
			bindAliasHover(text, issue.message || '');
			item.append(text);
			if (issue.node && CONFIGURE_CODES.indexOf(issue.code) !== -1) {
				var configure = $('<button type="button" class="btn-default btn-xs"></button>').text(t('Configure node'));
				configure.on('click', function () {
					if (!openNodeConfig(issue.node)) {
						showIssueNote(item, t('The node is not on the canvas. Apply the changes first.'));
					}
				});
				item.append(configure);
				if (issue.resolved) {
					showResolved(item, message, issue, index);
				} else if (issue.pick) {
					addPicker(item, message, issue, index);
				}
			} else if (FIX_CODES.indexOf(issue.code) !== -1) {
				fixable.push(issue);
				var fix = $('<button type="button" class="btn-default btn-xs"></button>').text(t('Fix problem'));
				fix.on('click', function () {
					askToFix([issue]);
				});
				item.append(fix);
			}
			list.append(item);
		});
		card.append(list);
		if (fixable.length > 1) {
			var all = $('<button type="button" class="btn-default"></button>').text(t('Fix all problems'));
			all.on('click', function () {
				askToFix(fixable);
			});
			card.append($('<div class="pl-assistant__actions"></div>').append(all));
		}
		return card;
	}

	// ------------------------------------------------------------------
	// Preguntas con opciones (ETL_ASSISTANT_QUESTIONS)
	// ------------------------------------------------------------------

	var RADIO_LIMIT = 6;      // hasta aquí, botones de opción; con más, lista con buscador
	var questionSeq = 0;

	function updateStored(id, change) {
		var state = loadState();
		(state.messages || []).forEach(function (item) {
			if (item.id === id) {
				change(item);
			}
		});
		saveState(state);
	}

	// ------------------------------------------------------------------
	// Elegir un fichero en el administrador de archivos, como los nodos
	// ------------------------------------------------------------------

	/*
	 * El popup entrega la ruta a una función global que comparten los nodos: la del chat se instala solo
	 * mientras se elige y luego vuelve la anterior (igual que el nodo ráster en PredictiveShapes.js).
	 * onPick recibe (valor "file://…", ruta relativa); onInvalid, si el fichero no es del tipo esperado.
	 */
	function openFileManager(extensions, onPick, onInvalid) {
		var allowed = (extensions || '').split(',').filter(Boolean);
		var previous = window.filemanagerCallback;
		var mine = function (url) {
			window.filemanagerCallback = previous;
			var lower = String(url).toLowerCase();
			var valid = !allowed.length || allowed.some(function (extension) {
				return lower.endsWith('.' + extension);
			});
			if (valid) {
				onPick('file://' + fm_directory + url, url);
			} else {
				onInvalid(allowed);
			}
		};
		window.filemanagerCallback = mine;
		var popup = window.open('/gvsigonline/filemanager/?popup=1', 'etl-assistant-files',
			'width=640, height=480,left=150,top=200,toolbar=0,status=0,scrollbars=1');
		var restore = function () {
			if (window.filemanagerCallback === mine) {
				window.filemanagerCallback = previous;
			}
		};
		if (!popup) {
			restore();
			return;
		}
		var watch = setInterval(function () {
			if (popup.closed) {
				clearInterval(watch);
				restore();
			}
		}, 500);
	}

	function wrongFileText(allowed) {
		return t('That file is not valid. Choose a file of type:') + ' ' + allowed.map(function (extension) {
			return '.' + extension;
		}).join(', ');
	}

	/* Botón "Seleccionar fichero" con la ruta elegida al lado. onChange recibe {value, label}. */
	function filePickerField(box, extensions, onChange) {
		var chosen = null;
		var kinds = (extensions || '').split(',').filter(Boolean).map(function (extension) {
			return '.' + extension;
		}).join(', ');
		var error = $('<div class="pl-assistant__field-error"></div>').hide();
		var pick = $('<button type="button" class="pl-assistant__file-drop js-file-picker"></button>')
			.append('<i class="fa fa-folder-open-o" aria-hidden="true"></i> ')
			.append($('<span></span>').text(t('Select file')));
		if (kinds) {
			pick.append($('<small></small>').text(kinds));
		}
		var name = $('<span class="pl-assistant__file-name"></span>');
		var change = $('<button type="button" class="btn-link btn-xs js-file-change"></button>').text(t('Change file'));
		var done = $('<div class="pl-assistant__file-chosen"></div>')
			.append('<i class="fa fa-check-circle" aria-hidden="true"></i>').append(name).append(change).hide();

		function open() {
			error.hide();
			openFileManager(extensions, function (value, label) {
				chosen = {value: value, label: label};
				name.text(label).attr('title', label);
				pick.hide();
				done.css('display', 'flex');
				onChange(chosen);
			}, function (allowed) {
				error.text(wrongFileText(allowed)).show();
			});
		}

		pick.on('click', open);
		change.on('click', open);
		box.append(pick).append(done).append(error);
		return {value: function () {
			return chosen;
		}};
	}

	// ------------------------------------------------------------------
	// Suposiciones cambiables con un clic (ETL_ASSISTANT_ALTERNATIVES)
	// ------------------------------------------------------------------

	function currentParameters(figureId) {
		for (var i = 0; i < jsonParams.length; i++) {
			if (jsonParams[i].id === figureId) {
				var params = jsonParams[i].parameters;
				return $.extend({}, (params && params[0]) || {});
			}
		}
		return {};
	}

	/* Cambia un parámetro de un nodo del canvas: un update_node con el resto de parámetros intactos. */
	function applyParameter(alias, param, value) {
		var changes = {};
		changes[param] = value;
		return applyParameters(alias, changes);
	}

	/* Varios parámetros de un nodo en un solo cambio; undefined quita el parámetro. */
	function applyParameters(alias, changes) {
		var figure = figureForAlias(alias);
		if (!figure) {
			return false;
		}
		var params = currentParameters(figure.id);
		Object.keys(changes).forEach(function (key) {
			if (changes[key] === undefined) {
				delete params[key];
				return;
			}
			params[key] = changes[key];
			// La lista del desplegable se guarda con el nodo: sin ella no se vería al reabrirlo
			var listName = (OPTION_LISTS[figure.NAME] || {})[key];
			if (listName && (params[listName] || []).indexOf(changes[key]) === -1) {
				params[listName] = (params[listName] || []).concat([changes[key]]);
			}
		});
		try {
			applyProposal({mode: 'patch', ops: [{op: 'update_node', id: figure.id, type: figure.NAME, parameters: params}]}, UNDO_LABEL_PARAM);
		} catch (e) {
			return false;
		}
		refreshColumns(figure);
		return true;
	}

	/* Apunta en el mensaje un valor elegido con un clic; sin value, lo quita. Va al historial del modelo. */
	function storeChange(message, node, param, value) {
		updateStored(message.id, function (item) {
			var changes = (item.changes || []).filter(function (change) {
				return !(change.node === node && change.param === param);
			});
			if (value !== undefined) {
				changes.push({node: node, param: param, value: value});
			}
			item.changes = changes;
			message.changes = changes;
		});
	}

	function recordChange(message, choice, value) {
		updateStored(message.id, function (item) {
			(item.assumptionChoices || []).forEach(function (candidate) {
				if (candidate.text === choice.text) {
					candidate.value = value;
				}
			});
		});
		storeChange(message, choice.node, choice.param, value);
		choice.value = value;
	}

	/* Suposición sobre un fichero: se cambia en el administrador de archivos. */
	function fileAlternativeControl(message, choice) {
		var box = $('<span class="pl-assistant__alternative"></span>');
		var name = $('<span class="pl-assistant__file-name"></span>').text(String(choice.value).split('/').pop());
		var button = $('<button type="button" class="btn-default btn-xs js-file-picker"></button>').text(t('Change file'));
		box.append(name).append(button);
		var pending = message.proposal && message.needsConfirmation && !message.settled;
		if (message.settled === 'discarded' || message.settled === 'undone') {
			button.prop('disabled', true).attr('title', t('These changes are no longer on the canvas.'));
			return box;
		}
		if (pending) {
			button.prop('disabled', true).attr('title', t('Apply the changes first.')).attr('data-pending-for', message.id);
		}
		function note(text) {
			box.find('.pl-assistant__issue-note').remove();
			box.append($('<span class="pl-assistant__issue-note"></span>').text(text));
		}
		button.on('click', function () {
			openFileManager((choice.file_picker || {}).extensions, function (value) {
				var before = choice.value;
				box.find('.pl-assistant__alternative-undo, .pl-assistant__issue-note').remove();
				if (!applyParameter(choice.node, choice.param, value)) {
					note(t('The node is not on the canvas. Apply the changes first.'));
					return;
				}
				recordChange(message, choice, value);
				name.text(String(value).split('/').pop());
				var undo = $('<button type="button" class="btn-link btn-xs pl-assistant__alternative-undo"></button>').text(t('Undo'));
				undo.on('click', function () {
					if (!applyParameter(choice.node, choice.param, before)) {
						return;
					}
					recordChange(message, choice, before);
					storeChange(message, choice.node, choice.param, undefined);
					name.text(String(before).split('/').pop());
					undo.remove();
				});
				box.append(undo);
			}, function (allowed) {
				note(wrongFileText(allowed));
			});
		});
		return box;
	}

	function alternativeControl(message, choice) {
		if (choice.file_picker) {
			return fileAlternativeControl(message, choice);
		}
		var box = $('<span class="pl-assistant__alternative"></span>');
		var select = $('<select class="form-control input-sm"></select>')
			.attr('aria-label', t('Change this assumption'));
		(choice.options || []).forEach(function (option) {
			select.append($('<option></option>').val(option.value).text(option.label));
		});
		select.val(choice.value);
		box.append(select);
		var pending = message.proposal && message.needsConfirmation && !message.settled;
		var gone = message.settled === 'discarded' || message.settled === 'undone';
		if (gone) {
			select.prop('disabled', true).attr('title', t('These changes are no longer on the canvas.'));
			return box;
		}
		if (pending) {
			// Se activa al pulsar Aplicar (actionBar)
			select.prop('disabled', true).attr('title', t('Apply the changes first.'))
				.attr('data-pending-for', message.id);
		}
		var previous = choice.value;
		select.on('change', function () {
			var value = select.val();
			box.find('.pl-assistant__alternative-undo, .pl-assistant__issue-note').remove();
			if (!applyParameter(choice.node, choice.param, value)) {
				select.val(previous);
				box.append($('<span class="pl-assistant__issue-note"></span>')
					.text(t('The node is not on the canvas. Apply the changes first.')));
				return;
			}
			var before = previous;
			previous = value;
			recordChange(message, choice, value);
			var undo = $('<button type="button" class="btn-link btn-xs pl-assistant__alternative-undo"></button>')
				.text(t('Undo'));
			undo.on('click', function () {
				// Se repone el valor: la pila podría tener encima otro cambio distinto
				if (!applyParameter(choice.node, choice.param, before)) {
					return;
				}
				select.val(before);
				previous = before;
				recordChange(message, choice, before);
				storeChange(message, choice.node, choice.param, undefined);
				undo.remove();
			});
			box.append(undo);
		});
		return box;
	}

	/* Un control por pregunta. value() devuelve [{value, label}] o null si aún no hay respuesta. */
	function questionControl(question, onChange) {
		var name = 'etl-q' + (++questionSeq);
		var box = $('<div class="pl-assistant__question-control"></div>');
		var options = question.options || [];
		var other = $('<input type="text" class="form-control input-sm pl-assistant__other">')
			.attr('placeholder', t('Other answer…')).attr('aria-label', t('Other answer…'));
		other.on('input', onChange);
		var allowOther = question.source !== 'datastores';    // un destino tiene que ser un almacén

		if (question.file_picker) {
			var file = filePickerField(box, question.file_picker.extensions, onChange);
			return {element: box, value: function () {
				return file.value() ? [file.value()] : null;
			}};
		}

		if (!options.length) {
			if (question.empty) {
				box.append($('<div class="pl-assistant__issue-note"></div>').text(question.empty === 'connections' ?
					t('You have no connections available.') : t('There are no options available.')));
			}
			box.append(other.attr('placeholder', t('Write the answer…')));
			return {element: box, value: function () {
				var text = other.val().trim();
				return text ? [{value: text, label: text}] : null;
			}};
		}

		if (question.multiple || options.length <= RADIO_LIMIT) {
			var type = question.multiple ? 'checkbox' : 'radio';
			options.forEach(function (option) {
				var input = $('<input>').attr({type: type, name: name}).val(option.value).data('label', option.label);
				input.on('change', onChange);
				box.append($('<label class="pl-assistant__option"></label>').append(input)
					.append($('<span></span>').text(option.label)));
			});
			if (allowOther) {
				var otherCheck = $('<input>').attr({type: type, name: name}).addClass('js-other');
				otherCheck.on('change', function () {
					other.prop('disabled', !otherCheck.prop('checked'));
					if (otherCheck.prop('checked')) {
						other.trigger('focus');
					}
					onChange();
				});
				other.prop('disabled', true);
				box.append($('<label class="pl-assistant__option"></label>').append(otherCheck)
					.append($('<span></span>').text(t('Other…'))));
				box.append(other);
			}
			return {element: box, value: function () {
				var chosen = [];
				box.find('input[name="' + name + '"]:checked').each(function () {
					var input = $(this);
					if (input.hasClass('js-other')) {
						var text = other.val().trim();
						if (text) {
							chosen.push({value: text, label: text});
						}
					} else {
						chosen.push({value: input.val(), label: input.data('label')});
					}
				});
				return chosen.length ? chosen : null;
			}};
		}

		// Muchas opciones: un desplegable con buscador
		var select = selectWithSearch(box, options, question.label || question.text);
		select.on('change', function () {
			if (select.val()) {
				other.val('');
			}
			onChange();
		});
		other.on('input', function () {
			if (other.val().trim()) {
				select.val('').trigger('change.select2');
			}
		});
		if (allowOther) {
			box.append(other);
		}
		return {element: box, value: function () {
			var text = other.val().trim();
			if (text) {
				return [{value: text, label: text}];
			}
			return select.val() ? [{value: select.val(), label: select.find('option:selected').text()}] : null;
		}};
	}

	function answerText(chosen) {
		return chosen.map(function (item) {
			return item.value !== item.label ? item.label + ' (' + item.value + ')' : item.label;
		}).join(', ');
	}

	function questionsCard(message) {
		var card = $('<div class="pl-assistant__card pl-assistant__questions"></div>');
		var progress = $('<span class="pl-assistant__progress"></span>');
		card.append($('<div class="pl-assistant__card-title pl-assistant__questions-head"></div>')
			.append($('<span></span>').text(t('The assistant needs to know'))).append(progress));
		var state = message.questionsState;
		var controls = [];
		var submit = $('<button type="button" class="btn-pl-add"></button>').text(t('Answer questions'));

		function refresh() {
			var answered = controls.filter(function (control) {
				return control.value();
			}).length;
			progress.text(t('{done} of {total}').replace('{done}', answered).replace('{total}', controls.length));
			submit.prop('disabled', busy || answered < controls.length);
		}

		/* Tras crear un almacén: la lista nueva, con el recién creado ya marcado. */
		function reloadDatastores(question, position) {
			requestOptions({type: 'output_Postgis', param: 'db-option', parameters: {}}, function (response) {
				if (response.error || !response.options) {
					return;
				}
				var known = (question.options || []).map(function (option) {
					return option.value;
				});
				var added = response.options.filter(function (option) {
					return known.indexOf(option.value) === -1;
				})[0];
				question.options = response.options;
				updateStored(message.id, function (item) {
					item.questions.forEach(function (candidate) {
						if (candidate.id === question.id) {
							candidate.options = response.options;
						}
					});
				});
				var fresh = questionControl(question, refresh);
				controls[position].element.replaceWith(fresh.element);
				controls[position] = fresh;
				if (added) {
					fresh.element.find('input, select').filter(function () {
						return this.value === added.value;
					}).prop('checked', true);
					fresh.element.find('select').val(added.value).trigger('change.select2');
				}
				refresh();
			}, function () {
			});
		}

		message.questions.forEach(function (question) {
			var block = $('<fieldset class="pl-assistant__question"></fieldset>');
			block.append($('<legend></legend>').text(question.text || question.label));
			if (state === 'answered') {
				block.append($('<div class="pl-assistant__answer"></div>')
					.text((message.answers || {})[question.id] || ''));
			} else {
				var control = questionControl(question, refresh);
				controls.push(control);
				block.append(control.element);
				if (question.create_datastore) {
					block.append(createDatastoreButton(reloadDatastores.bind(null, question, controls.length - 1)));
				}
			}
			card.append(block);
		});

		if (state === 'answered') {
			card.addClass('is-answered');
			return card;
		}
		if (state === 'skipped') {
			card.addClass('is-skipped');
			card.find('input, select, button').prop('disabled', true);
			card.append($('<div class="pl-assistant__issue-note"></div>').text(t('Answered in the text box.')));
			return card;
		}

		submit.on('click', function () {
			if (busy) {
				return;
			}
			var answers = {};
			var parts = [];
			for (var i = 0; i < controls.length; i++) {
				var chosen = controls[i].value();
				if (!chosen) {
					return;
				}
				var question = message.questions[i];
				answers[question.id] = chosen.map(function (item) {
					return item.label;
				}).join(', ');
				parts.push((question.label || question.text) + ': ' + answerText(chosen));
			}
			updateStored(message.id, function (item) {
				item.questionsState = 'answered';
				item.answers = answers;
			});
			message.questionsState = 'answered';
			message.answers = answers;
			card.replaceWith(questionsCard(message));
			sendText(parts.join(' · '));
		});
		card.on('keydown', 'input[type=text]', function (event) {
			if (event.key === 'Enter' && !submit.prop('disabled')) {
				event.preventDefault();
				submit.trigger('click');
			}
		});
		card.append($('<div class="pl-assistant__actions pl-assistant__actions--end"></div>').append(submit));
		refresh();
		return card;
	}

	/* Si el usuario escribe en el cuadro en lugar de responder, las preguntas abiertas quedan cerradas. */
	function closeOpenQuestions() {
		var state = loadState();
		var changed = false;
		(state.messages || []).forEach(function (item) {
			if (item.questions && item.questions.length && !item.questionsState) {
				item.questionsState = 'skipped';
				changed = true;
			}
		});
		if (changed) {
			saveState(state);
			messagesEl.find('.pl-assistant__questions').not('.is-answered').each(function () {
				var card = $(this);
				card.addClass('is-skipped').find('input, select, button').prop('disabled', true);
				if (!card.find('.pl-assistant__issue-note').length) {
					card.append($('<div class="pl-assistant__issue-note"></div>').text(t('Answered in the text box.')));
				}
			});
		}
	}

	// ------------------------------------------------------------------
	// Completar un parámetro desde el chat (ETL_ASSISTANT_PARAM_PICKER)
	// ------------------------------------------------------------------

	/* Por qué no se puede tocar aún el nodo de un mensaje; se mira el estado guardado, que cambia al aplicar. */
	function blockedReason(message) {
		var stored = (loadState().messages || []).filter(function (item) {
			return item.id === message.id;
		})[0] || message;
		if (stored.proposal && stored.needsConfirmation && !stored.settled) {
			return t('Apply the changes first.');
		}
		if (stored.settled === 'discarded' || stored.settled === 'undone') {
			return t('These changes are no longer on the canvas.');
		}
		return '';
	}

	// ------------------------------------------------------------------
	// Columnas de las entradas (ETL_ASSISTANT_COLUMNS)
	// ------------------------------------------------------------------

	var READABLE_INPUTS = ['input_Shp', 'input_Csv', 'input_Excel', 'input_Kml', 'input_Postgis', 'input_Oracle', 'input_SqlServer'];

	function columnsEnabled() {
		return panel.attr('data-columns') === '1';
	}

	function paramsEntry(figureId) {
		return jsonParams.filter(function (entry) {
			return entry.id === figureId;
		})[0];
	}

	/* La rueda solo está en verde si la entrada tiene columnas de verdad. */
	function markUnreadInputs(canvasView) {
		if (!columnsEnabled() || typeof setGearColorForNode !== 'function') {
			return;
		}
		canvasView.getFigures().each(function (i, figure) {
			if (READABLE_INPUTS.indexOf(figure.NAME) !== -1) {
				var entry = paramsEntry(figure.id);
				if (!entry || !entry.schema || !entry.schema.length) {
					setGearColorForNode(figure.id, figure, figure.NAME, false);
				}
			}
		});
	}

	/* Tras cambiar el origen de una entrada: lee sus columnas y las pasa a los nodos siguientes. */
	function refreshColumns(figure) {
		if (!columnsEnabled() || READABLE_INPUTS.indexOf(figure.NAME) === -1) {
			return;
		}
		$.ajax({
			type: 'POST',
			url: '/gvsigonline/etl/etl_assistant/columns/',
			contentType: 'application/json',
			data: JSON.stringify({
				type: figure.NAME,
				parameters: currentParameters(figure.id),
				workspace_id: $('#etl_id').val() || null
			}),
			beforeSend: function (xhr) {
				xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
			},
			success: function (response) {
				var entry = paramsEntry(figure.id);
				var canvasView = view();
				if (!entry || !canvasView) {
					return;
				}
				$.extend(entry.parameters[0], response.params || {});
				fillEtlNodeForm(figure.NAME, {id: figure.id}, entry.parameters, entry['schema-old']);
				if (response.schema && response.schema.length) {
					entry.schema = response.schema;
					if (typeof propagateSchemaFrom === 'function') {
						propagateSchemaFrom(figure.id, canvasView, {skipStart: false});
					}
				} else {
					entry.schema = [];
					markUnreadInputs(canvasView);
					if (response.error) {
						appendMessage({role: 'error', content: t('The columns of the node could not be read:') + ' ' + response.error});
					}
				}
			}
		});
	}

	/*
	 * Formulario de siempre para crear un almacén, en una ventana aparte: conserva sus permisos y
	 * validaciones. Al guardar redirige a la lista: se cierra y se recargan las opciones.
	 */
	function openDatastoreForm(onDone) {
		var popup = window.open('/gvsigonline/services/datastore_add/', 'etl-assistant-datastore',
			'width=900, height=700,left=150,top=100,toolbar=0,status=0,scrollbars=1');
		if (!popup) {
			return;
		}
		var watch = setInterval(function () {
			var saved = false;
			try {
				saved = !popup.closed && popup.location.pathname.indexOf('datastore_list') !== -1;
			} catch (e) {
			}
			if (saved) {
				popup.close();
			}
			if (saved || popup.closed) {
				clearInterval(watch);
				onDone();
			}
		}, 500);
	}

	function createDatastoreButton(onDone) {
		return $('<button type="button" class="btn-link btn-xs js-create-datastore"></button>')
			.text(t('Create a new data store…')).on('click', function () {
				openDatastoreForm(onDone);
			});
	}

	function requestOptions(data, success, failure) {
		$.ajax({
			type: 'POST',
			url: '/gvsigonline/etl/etl_assistant/options/',
			contentType: 'application/json',
			data: JSON.stringify($.extend({workspace_id: $('#etl_id').val() || null}, data)),
			beforeSend: function (xhr) {
				xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
			},
			success: success,
			error: failure
		});
	}

	/* Desplegable con buscador integrado (Select2, como los nodos). Se añade a box y devuelve el select. */
	function selectWithSearch(box, options, label) {
		var select = $('<select class="form-control input-sm"></select>').attr('aria-label', label);
		select.append($('<option value=""></option>').text(t('Choose an option…')));
		options.forEach(function (option) {
			select.append($('<option></option>').val(option.value).text(option.label));
		});
		box.append(select);
		if ($.fn.select2) {
			select.select2({width: '100%', placeholder: t('Choose an option…')});
		}
		return select;
	}

	function addPicker(item, message, issue, index) {
		var button = $('<button type="button" class="btn-default btn-xs js-pick"></button>').text(t('Choose a value'));
		button.on('click', function () {
			item.find('.pl-assistant__issue-note, .pl-assistant__picker').remove();
			var reason = blockedReason(message);
			if (reason) {
				showIssueNote(item, reason);
				return;
			}
			var figure = figureForAlias(issue.node);
			if (!figure) {
				showIssueNote(item, t('The node is not on the canvas. Apply the changes first.'));
				return;
			}
			if (issue.pick.file_picker) {
				openFileManager(issue.pick.file_picker.extensions, function (value, label) {
					applyPick(item, message, issue, index, value, label);
				}, function (allowed) {
					showIssueNote(item, wrongFileText(allowed));
				});
				return;
			}
			load();
		});
		function load() {
			var figure = figureForAlias(issue.node);
			if (!figure) {
				showIssueNote(item, t('The node is not on the canvas. Apply the changes first.'));
				return;
			}
			item.find('.pl-assistant__picker').remove();
			button.prop('disabled', true);
			requestOptions({
				type: issue.pick.type,
				param: issue.param,
				parameters: currentParameters(figure.id)
			}, function (response) {
				button.prop('disabled', false);
				if (response.error) {
					showIssueNote(item, t('The options could not be loaded.'));
				} else if (response.needs === 'connection') {
					showIssueNote(item, t('Choose the connection of the node first.'));
				} else if (response.needs === 'schema') {
					showIssueNote(item, t('Choose the schema of the node first.'));
				} else if ((!response.options || !response.options.length) && !response.create_datastore) {
					showIssueNote(item, t('There are no options available.'));
				} else {
					showPicker(item, message, issue, index, response.options || [], response.create_datastore ? load : null);
				}
			}, function () {
				button.prop('disabled', false);
				showIssueNote(item, t('The options could not be loaded.'));
			});
		}
		item.append(button);
	}

	function applyPick(item, message, issue, index, value, label, params) {
		var changes = params;
		if (!changes) {
			changes = {};
			changes[issue.param] = value;
		}
		var figure = figureForAlias(issue.node);
		var current = figure ? currentParameters(figure.id) : {};
		var previous = {};
		Object.keys(changes).forEach(function (key) {
			previous[key] = current[key];
		});
		if (!applyParameters(issue.node, changes)) {
			showIssueNote(item, t('The node is not on the canvas. Apply the changes first.'));
			return false;
		}
		issue.resolved = {value: value, label: label, changed: Object.keys(changes), previous: previous};
		updateStored(message.id, function (stored) {
			stored.issues[index].resolved = issue.resolved;
		});
		Object.keys(changes).forEach(function (key) {
			storeChange(message, issue.node, key, changes[key]);
		});
		showResolved(item, message, issue, index);
		return true;
	}

	function showPicker(item, message, issue, index, options, reload) {
		var box = $('<div class="pl-assistant__picker"></div>');
		var select = selectWithSearch(box, options, t('Choose a value'));
		select.on('change', function () {
			var value = select.val();
			if (!value) {
				return;
			}
			var option = options.filter(function (candidate) {
				return candidate.value === value;
			})[0];
			if (!applyPick(item, message, issue, index, value, select.find('option:selected').text(), option && option.params)) {
				select.val('');
			}
		});
		if (reload) {
			box.append(createDatastoreButton(reload));
		}
		item.append(box);
	}

	function showResolved(item, message, issue, index) {
		item.addClass('is-resolved');
		item.find('.js-pick, .pl-assistant__picker, .pl-assistant__issue-note').remove();
		var done = $('<div class="pl-assistant__issue-resolved"></div>')
			.text(t('Value chosen:') + ' ' + issue.resolved.label + ' ');
		var undo = $('<button type="button" class="btn-link btn-xs"></button>').text(t('Undo'));
		undo.on('click', function () {
			var resolved = issue.resolved;
			var changed = resolved.changed || [issue.param];
			var restore = {};
			changed.forEach(function (key) {
				restore[key] = resolved.previous ? resolved.previous[key] : resolved.before;
			});
			if (!applyParameters(issue.node, restore)) {
				showIssueNote(item, t('The node is not on the canvas. Apply the changes first.'));
				return;
			}
			delete issue.resolved;
			updateStored(message.id, function (stored) {
				delete stored.issues[index].resolved;
			});
			changed.forEach(function (key) {
				storeChange(message, issue.node, key, undefined);
			});
			item.removeClass('is-resolved');
			done.remove();
			if (issue.pick) {
				addPicker(item, message, issue, index);
			}
		});
		item.append(done.append(undo));
	}

	// ------------------------------------------------------------------
	// Siguiente paso y arranque guiado (ETL_ASSISTANT_NEXT_STEPS)
	// ------------------------------------------------------------------

	function nextStepText(code) {
		if (code === 'add_output') {
			return {label: t('Add a PostGIS output'), message: t('Add an output to a new PostGIS table at the end of the flow.')};
		}
		if (code === 'explain') {
			return {label: t('Explain the flow'), message: t('Explain what the flow on the canvas does, step by step.')};
		}
		if (code === 'review') {
			return {label: t('Review the flow'), message: t('Review the flow and tell me which parameters are missing or may cause errors.')};
		}
		return null;
	}

	function nextStepsBar(message) {
		var bar = $('<div class="pl-assistant__next"></div>');
		message.nextSteps.forEach(function (step) {
			var text = nextStepText(step.code);
			if (text) {
				bar.append($('<button type="button" class="pl-assistant__next-step"></button>').text(text.label)
					.on('click', function () {
						sendText(text.message);
					}));
			}
		});
		return bar;
	}

	function guidedEnabled() {
		return panel.attr('data-guided') === '1';
	}

	function closeGuided() {
		examplesEl.find('.pl-assistant__guided').remove();
	}

	/* Formulario del ejemplo "CSV a PostGIS": elige fichero y conexión, y compone la petición. */
	function openGuided(button) {
		closeGuided();
		var form = $('<div class="pl-assistant__card pl-assistant__guided"></div>');
		var fields = {};
		var submit = $('<button type="button" class="btn-pl-add"></button>').text(t('Create the flow')).prop('disabled', true);
		var note = $('<div class="pl-assistant__issue-note"></div>').hide();

		function refresh() {
			submit.prop('disabled', !(fields.file && fields.file.value() && fields.connection && fields.connection.val()));
		}

		function fail(text) {
			if (form.find('.js-guided-fallback').length) {
				return;
			}
			submit.remove();
			note.text(text).show();
			note.after($('<button type="button" class="btn-default js-guided-fallback"></button>').text(t('Ask the assistant'))
				.on('click', function () {
					closeGuided();
					sendText(button.attr('data-example'));
				}));
		}

		function field(key, label, type, param, emptyText) {
			var box = $('<div class="pl-assistant__guided-field"></div>')
				.append($('<div class="pl-assistant__card-title"></div>').text(label));
			form.append(box);
			function load() {
				box.find('select, input, .js-create-datastore').remove();
				fields[key] = null;
				refresh();
				requestOptions({type: type, param: param, parameters: {}}, function (response) {
					if (response.error) {
						fail(t('The options could not be loaded.'));
					} else if ((!response.options || !response.options.length) && !response.create_datastore) {
						fail(emptyText);
					} else {
						fields[key] = selectWithSearch(box, response.options || [], label);
						fields[key].on('change', refresh);
						if (response.create_datastore) {
							box.append(createDatastoreButton(load));
						}
					}
				}, function () {
					fail(t('The options could not be loaded.'));
				});
			}
			load();
		}

		form.append($('<div class="pl-assistant__card-title"></div>').text(button.text()));
		var fileBox = $('<div class="pl-assistant__guided-field"></div>')
			.append($('<div class="pl-assistant__card-title"></div>').text(t('CSV file')));
		form.append(fileBox);
		fields.file = filePickerField(fileBox, 'csv,txt', refresh);
		field('connection', t('Where to create the table'), 'output_Postgis', 'db-option', t('You have no PostGIS connections available.'));
		submit.on('click', function () {
			var file = fields.file.value();
			var text = t('Load the CSV file {file} into a new table of the data store {store}.')
				.replace('{file}', function () {
					return answerText([file]);
				})
				.replace('{store}', function () {
					return answerText([{value: fields.connection.val(), label: fields.connection.find('option:selected').text()}]);
				});
			closeGuided();
			sendText(text);
		});
		var cancel = $('<button type="button" class="btn-default"></button>').text(t('Cancel')).on('click', closeGuided);
		form.append(note).append($('<div class="pl-assistant__actions"></div>').append(submit).append(cancel));
		button.after(form);
	}

	function showIssueNote(item, text) {
		item.find('.pl-assistant__issue-note').remove();
		item.append($('<div class="pl-assistant__issue-note"></div>').text(text));
	}

	function askToFix(issues) {
		if (busy) {
			return;
		}
		if (issues.length === 1) {
			sendText(t('Fix this problem:') + ' ' + issues[0].message);
			return;
		}
		sendText(t('Fix these problems:') + '\n' + issues.map(function (issue) {
			return '- ' + issue.message;
		}).join('\n'));
	}

	function renderAll() {
		var state = loadState();
		messagesEl.empty();
		aliasMap = state.aliasMap || {};
		(state.messages || []).forEach(function (message) {
			var copy = $.extend({}, message);
			if (copy.proposal && copy.needsConfirmation && !copy.settled) {
				copy.actions = actionBar(copy.proposal, true, copy.id);
			}
			appendMessage(copy, state.types || {});
		});
		setExamplesVisible(!(state.messages || []).length);
	}

	function settleMessage(id, kind, status) {
		if (!id) {
			return;
		}
		var state = loadState();
		(state.messages || []).forEach(function (item) {
			if (item.id === id) {
				item.settled = kind;
				item.status = status;
			}
		});
		saveState(state);
	}

	function remember(message, extra) {
		var state = loadState();
		state.messages = state.messages || [];
		state.messages.push(message);
		if (extra) {
			if (extra.aliasMap) {
				state.aliasMap = extra.aliasMap;
			}
			if (extra.types) {
				state.types = extra.types;
			}
		}
		saveState(state);
		aliasMap = state.aliasMap || aliasMap;
	}

	function historyPayload() {
		var state = loadState();
		var items = [];
		(state.messages || []).forEach(function (message) {
			if (message.role === 'user') {
				items.push({role: 'user', content: message.content || ''});
			} else if (message.role === 'assistant') {
				// Lo que propuso y qué hizo el usuario con ello, para que el modelo no lo suponga.
				var status = message.settled || (message.proposal ? 'pending' : '');
				var item = {
					role: 'assistant',
					content: message.content || '',
					summary: message.summary || [],
					status: status
				};
				if (message.changes && message.changes.length) {
					// Suposiciones que el usuario cambió con un clic: que el modelo no las deshaga
					item.changes = message.changes;
				}
				if (message.questions && message.questions.length) {
					// Qué preguntó: la respuesta del usuario llega como "Etiqueta: valor"
					item.questions = message.questions.map(function (question) {
						return {label: question.label, text: question.text};
					});
				}
				items.push(item);
			}
		});
		return items.slice(-17);
	}

	function canvasSummary() {
		var canvasView = view();
		var nodes = [];
		var edges = [];
		var localAlias = {};
		if (!canvasView) {
			return {nodes: nodes, edges: edges, selected: null};
		}
		var counter = 1;
		var seen = {};
		canvasView.getFigures().each(function (i, figure) {
			if (figure instanceof draw2d.Connection) {
				return;
			}
			// El alias es el id visible en la cabecera del nodo (NodeHeader.js)
			var alias = figure.etlAlias;
			if (!alias || seen[alias]) {
				while (seen['n' + counter]) {
					counter += 1;
				}
				alias = 'n' + counter;
			}
			seen[alias] = true;
			localAlias[figure.id] = alias;
			var parameters = {};
			var schema = [];
			var schemaold = [];
			// Estado de la rueda: sin configurar (no hay tarea) o configuración que no encaja.
			var status = 'unconfigured';
			for (var k = 0; k < jsonParams.length; k++) {
				if (jsonParams[k].id === figure.id) {
					parameters = (jsonParams[k].parameters && jsonParams[k].parameters[0]) || {};
					schema = jsonParams[k].schema || [];
					schemaold = jsonParams[k]['schema-old'] || [];
					status = jsonParams[k]._schemaValid === false ? 'invalid' : '';
				}
			}
			var typeName = figure.NAME || figure.cssClass;
			nodes.push({
				alias: alias,
				id: figure.id,
				type: typeName,
				label: (figure.classLabel && figure.classLabel.getText) ? figure.classLabel.getText() : typeName,
				parameters: parameters,
				schema: schema,
				schemaold: schemaold,
				status: status,
				x: Math.round(figure.getX ? figure.getX() : (figure.x || 0)),
				y: Math.round(figure.getY ? figure.getY() : (figure.y || 0))
			});
		});
		canvasView.getLines().each(function (i, line) {
			var source = line.getSource();
			var target = line.getTarget();
			if (!source || !target || typeof etlFigureIdOfPort !== 'function') {
				return;
			}
			var sourceId = etlFigureIdOfPort(source);
			var targetId = etlFigureIdOfPort(target);
			if (!localAlias[sourceId] || !localAlias[targetId]) {
				return;
			}
			var sourcePort = etlPortIndex(sourceId, 'output', source.getName());
			var targetPort = etlPortIndex(targetId, 'input', target.getName());
			if (sourcePort < 0 || targetPort < 0) {
				return;
			}
			edges.push({
				source: localAlias[sourceId],
				target: localAlias[targetId],
				source_port: sourcePort,
				target_port: targetPort
			});
		});
		var selected = null;
		if (selectedFigure && localAlias[selectedFigure.id]) {
			selected = localAlias[selectedFigure.id];
		}
		// Siguiente id libre: el editor no reutiliza los de nodos borrados (NodeHeader.js).
		var top = canvasView._etlAliasTop || 0;
		Object.keys(seen).forEach(function (alias) {
			var number = parseInt(alias.slice(1), 10);
			if (number > top) {
				top = number;
			}
		});
		return {nodes: nodes, edges: edges, selected: selected, aliasOfId: localAlias, nextAlias: 'n' + (top + 1)};
	}

	function updateContext() {
		var summary = canvasSummary();
		refreshExamples(summary);
		if (!summary.selected) {
			contextEl.attr('hidden', true).text('');
			return;
		}
		var label = summary.selected;
		summary.nodes.forEach(function (node) {
			if (node.alias === summary.selected) {
				label = (node.label || node.type) + ' ' + node.alias;
			}
		});
		contextEl.removeAttr('hidden').text(t('Context') + ': ' + label);
	}

	function refreshCanvas() {
		var canvasView = view();
		if (!canvasView || !canvasView.getZoom || !canvasView.setZoom) {
			return;
		}
		canvasView.setZoom(canvasView.getZoom(), false);
	}

	function setOpen(open) {
		panel.toggleClass('is-collapsed', !open);
		$('#etl-assistant-open').attr('aria-expanded', open ? 'true' : 'false');
		localStorage.setItem(STORAGE_OPEN, open ? '1' : '0');
		if (open) {
			var width = parseInt(localStorage.getItem(STORAGE_WIDTH) || '380', 10);
			if (width >= 320 && width <= 600) {
				panel.css('width', width + 'px');
			}
			input.focus();
		}
		refreshCanvas();
		updateContext();
	}

	function nodeDocument(node) {
		var ports = [];
		var index;
		for (index = 0; index < (node.input_count || 0); index++) {
			ports.push({name: 'in_' + index});
		}
		for (index = 0; index < (node.output_count || 0); index++) {
			ports.push({name: 'out_' + index});
		}
		return {
			type: node.type,
			id: node.id,
			x: node.x,
			y: node.y,
			name: node.label,
			ports: ports,
			entities: [{
				parameters: [node.parameters || {}],
				schema: node.schema || [],
				schemaold: node.schemaold || node['schema-old'] || []
			}]
		};
	}

	function edgeDocument(op) {
		return {
			type: 'draw2d.Connection',
			source: {node: op.source, port: 'out_' + op.source_port},
			target: {node: op.target, port: 'in_' + op.target_port},
			source_port: op.source_port,
			target_port: op.target_port
		};
	}

	function updateExisting(op) {
		var canvasView = view();
		var figure = canvasView.getFigure(op.id);
		if (figure && op.label && figure.setName) {
			figure.setName(op.label);
		}
		var entry = null;
		for (var i = 0; i < jsonParams.length; i++) {
			if (jsonParams[i].id === op.id) {
				entry = jsonParams[i];
				break;
			}
		}
		if (!entry) {
			entry = {id: op.id, parameters: [{}], schema: [], 'schema-old': []};
			jsonParams.push(entry);
		}
		entry.parameters = [op.parameters || {}];
		if (op.schema) {
			entry.schema = op.schema;
		}
		if (op.schemaold) {
			entry['schema-old'] = op.schemaold;
		}
		fillEtlNodeForm(op.type || (figure && figure.NAME) || '', {id: op.id}, entry.parameters, entry['schema-old']);
	}

	function removeNode(canvasView, id) {
		var stack = canvasView.getCommandStack();
		var lines = canvasView.getLines().clone();
		lines.each(function (i, line) {
			var source = line.getSource();
			var target = line.getTarget();
			if (!source || !target) {
				return;
			}
			if (etlFigureIdOfPort(source) === id || etlFigureIdOfPort(target) === id) {
				stack.execute(new draw2d.command.CommandDelete(line));
			}
		});
		var figure = canvasView.getFigure(id);
		if (figure) {
			stack.execute(new draw2d.command.CommandDelete(figure));
		}
		var kept = [];
		for (var i = 0; i < jsonParams.length; i++) {
			if (jsonParams[i].id !== id) {
				kept.push(jsonParams[i]);
			}
		}
		jsonParams = kept;
	}

	function propagateInputs(canvasView) {
		if (typeof propagateSchemaFrom !== 'function') {
			return;
		}
		canvasView.getFigures().each(function (i, figure) {
			var typeName = figure.NAME || '';
			if (typeName.indexOf('input_') === 0 || typeName.indexOf('crea_') === 0) {
				propagateSchemaFrom(figure.id, canvasView, {skipStart: false});
			}
		});
	}

	function fillEmptyNames(proposal) {
		if (proposal.name && !$('#etl_name').val()) {
			$('#etl_name').val(proposal.name);
		}
		if (proposal.description && !$('#etl_desc').val()) {
			$('#etl_desc').val(proposal.description);
		}
	}

	function typesFromProposal(proposal, base) {
		var types = $.extend({}, base || {});
		if (!proposal) {
			return types;
		}
		(proposal.nodes || []).forEach(function (node) {
			types[node.alias || node.id] = node.type;
		});
		(proposal.ops || []).forEach(function (op) {
			if (op.op === 'add_node' && op.node) {
				types[op.node.alias || op.node.id] = op.node.type;
			}
			if (op.alias && op.type) {
				types[op.alias] = op.type;
			}
		});
		return types;
	}

	function applyProposal(proposal, undoLabel) {
		var canvasView = view();
		if (!canvasView) {
			throw new Error('canvas');
		}
		var stack = canvasView.getCommandStack();
		var before = JSON.parse(JSON.stringify(jsonParams));
		var summary = canvasSummary();
		var map = {};
		(summary.nodes || []).forEach(function (node) {
			map[node.alias] = node.id;
		});
		stack.startTransaction(undoLabel || UNDO_LABEL);
		try {
			var created = {};
			if (proposal.mode === 'replace') {
				etlClearCanvas(canvasView);
				jsonParams = [];
				var documents = (proposal.nodes || []).map(nodeDocument);
				(proposal.edges || []).forEach(function (edge) {
					documents.push(edgeDocument(edge));
				});
				created = drawNodes(documents, {view: canvasView});
				map = created;
			} else {
				var fresh = [];
				(proposal.ops || []).forEach(function (op) {
					if (op.op === 'remove_edge') {
						var line = etlFindLine(canvasView, op.source, op.target, op.source_port, op.target_port);
						if (line) {
							stack.execute(new draw2d.command.CommandDelete(line));
						}
					} else if (op.op === 'remove_node') {
						removeNode(canvasView, op.id);
					} else if (op.op === 'update_node') {
						updateExisting(op);
					} else if (op.op === 'add_node') {
						fresh.push(nodeDocument(op.node));
					} else if (op.op === 'add_edge') {
						fresh.push(edgeDocument(op));
					}
				});
				if (fresh.length) {
					created = drawNodes(fresh, {view: canvasView});
					$.extend(map, created);
				}
			}
			var after = JSON.parse(JSON.stringify(jsonParams));
			stack.execute(new EtlApplyCommand(
				function () {
					jsonParams = JSON.parse(JSON.stringify(after));
				},
				function () {
					jsonParams = JSON.parse(JSON.stringify(before));
				}
			));
			stack.commitTransaction();
			propagateInputs(canvasView);
			markUnreadInputs(canvasView);
			fillEmptyNames(proposal);
			return map;
		} catch (err) {
			jsonParams = before;
			if (stack.isInTransaction()) {
				stack.transactionCommand = null;
			}
			throw err;
		}
	}

	function actionBar(proposal, needsConfirmation, messageId) {
		var bar = $('<div class="pl-assistant__actions"></div>');
		if (needsConfirmation) {
			var applyBtn = $('<button type="button" class="btn-pl-add"></button>').text(t('Apply'));
			var discardBtn = $('<button type="button" class="btn-default"></button>').text(t('Discard'));
			applyBtn.on('click', function () {
				try {
					var map = applyProposal(proposal);
					applyBtn.prop('disabled', true);
					discardBtn.prop('disabled', true);
					bar.after($('<div class="pl-assistant__status"></div>').text(t('Applied')));
					var state = loadState();
					state.aliasMap = map;
					saveState(state);
					settleMessage(messageId, 'applied', t('Applied'));
					aliasMap = map;
					// Las suposiciones de esta propuesta ya se pueden cambiar
					messagesEl.find('[data-pending-for="' + messageId + '"]').prop('disabled', false)
						.removeAttr('title').removeAttr('data-pending-for');
				} catch (e) {
					bar.after($('<div class="pl-assistant__bubble pl-assistant__bubble--error"></div>').text(t('The flow could not be drawn.')));
				}
			});
			discardBtn.on('click', function () {
				applyBtn.prop('disabled', true);
				discardBtn.prop('disabled', true);
				bar.after($('<div class="pl-assistant__status"></div>').text(t('Discarded')));
				settleMessage(messageId, 'discarded', t('Discarded'));
			});
			bar.append(applyBtn, discardBtn);
		} else {
			var undoBtn = $('<button type="button" class="btn-default"></button>').text(t('Undo'));
			undoBtn.on('click', function () {
				var canvasView = view();
				if (!canvasView) {
					return;
				}
				var stack = canvasView.getCommandStack();
				if (stack.getUndoLabel && stack.getUndoLabel() !== UNDO_LABEL) {
					return;
				}
				stack.undo();
				undoBtn.prop('disabled', true);
				messagesEl.find('.pl-assistant__next').remove();
				bar.after($('<div class="pl-assistant__status"></div>').text(t('Undone')));
				settleMessage(messageId, 'undone', t('Undone'));
			});
			bar.append(undoBtn);
		}
		return bar;
	}

	function newId() {
		return 'm' + Date.now().toString(36) + Math.random().toString(36).slice(2);
	}

	function sendText(text) {
		text = (text || '').trim();
		if (!text || busy) {
			return;
		}
		if (text.length > MESSAGE_LIMIT) {
			updateCounter();
			return;
		}
		recall = -1;
		closeOpenQuestions();
		var summary = canvasSummary();
		var types = {};
		summary.nodes.forEach(function (node) {
			types[node.alias] = node.type;
		});
		var question = {id: newId(), role: 'user', content: text};
		remember(question, {types: types, aliasMap: invertAlias(summary)});
		appendMessage(question);
		setExamplesVisible(false);
		input.val('').css({height: 'auto', overflowY: 'hidden'});
		updateCounter();
		setBusy(true);
		var typing = appendMessage({role: 'assistant', typing: true, content: ''});
		var started = Date.now();
		var elapsed = $('<span class="pl-assistant__elapsed"></span>');
		typing.find('.pl-assistant__bubble').append(elapsed);
		var timer = setInterval(function () {
			var seconds = Math.round((Date.now() - started) / 1000);
			if (seconds >= 3) {
				elapsed.text(t('Thinking…') + ' ' + seconds + ' s');
			}
		}, 1000);
		var stopped = false;
		var requestBody = {
			message: text,
			history: historyPayload().slice(0, -1),
			canvas: {
				nodes: summary.nodes,
				edges: summary.edges,
				selected: summary.selected,
				next_alias: summary.nextAlias
			},
			workspace_id: $('#etl_id').val() || null
		};

		function showResponse(response) {
			typing.remove();
			var proposal = response.proposal;
			var mergedTypes = typesFromProposal(proposal, types);
			var actions = null;
			var map = invertAlias(summary);
			var messageId = newId();
			if (proposal && !response.error) {
				if (response.needs_confirmation) {
					actions = actionBar(proposal, true, messageId);
				} else {
					try {
						map = applyProposal(proposal);
						actions = actionBar(proposal, false, messageId);
					} catch (e) {
						response.warnings = (response.warnings || []).concat([t('The flow could not be drawn.')]);
					}
				}
			}
			var stored = {
				id: messageId,
				role: 'assistant',
				content: response.reply || '',
				summary: response.summary || [],
				assumptions: response.assumptions || [],
				warnings: response.warnings || [],
				proposal: proposal,
				needsConfirmation: !!response.needs_confirmation
			};
			if (response.issues && response.issues.length) {
				stored.issues = response.issues;
			}
			if (response.questions && response.questions.length) {
				stored.questions = response.questions;
			}
			if (response.assumption_choices && response.assumption_choices.length) {
				stored.assumptionChoices = response.assumption_choices;
			}
			if (response.next_steps && response.next_steps.length) {
				stored.nextSteps = response.next_steps;
			}
			if (proposal && !response.error && !response.needs_confirmation) {
				stored.settled = 'applied';
				stored.status = t('Applied');
			}
			remember(stored, {aliasMap: map, types: mergedTypes});
			stored.actions = actions;
			appendMessage(stored, mergedTypes);
		}

		function showFailure(kind) {
			typing.remove();
			var readable = t('The assistant could not be reached. Try again.');
			if (kind === 'stopped') {
				readable = t('Stopped. The canvas has not changed.');
			} else if (kind === 'forbidden') {
				readable = t('You are not allowed to use the assistant on this workspace.');
			}
			var errorMessage = {role: 'error', content: readable, retry: text};
			remember(errorMessage);
			appendMessage(errorMessage);
		}

		function finish() {
			clearInterval(timer);
			currentXhr = null;
			setBusy(false);
			input.focus();
		}

		if (streamingEnabled()) {
			currentXhr = streamRequest(requestBody, {
				step: function (event) {
					showStep(typing, event);
				},
				text: function (event) {
					showLiveText(typing, event);
				},
				response: showResponse,
				failure: showFailure,
				done: finish
			});
			return;
		}

		currentXhr = $.ajax({
			type: 'POST',
			url: '/gvsigonline/etl/etl_assistant/',
			contentType: 'application/json',
			data: JSON.stringify(requestBody),
			beforeSend: function (xhr) {
				xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
			},
			success: function (response) {
				showResponse(response);
			},
			error: function (xhr, textStatus) {
				if (stopped || textStatus === 'abort') {
					showFailure('stopped');
				} else if (xhr.status === 403) {
					showFailure('forbidden');
				} else {
					showFailure('network');
				}
			},
			complete: function () {
				finish();
			}
		});
		currentXhr.etlStop = function () {
			stopped = true;
			currentXhr.abort();
		};
	}

	// ------------------------------------------------------------------
	// Pasos en vivo y Detener real (ETL_ASSISTANT_STREAMING)
	// ------------------------------------------------------------------

	function streamingEnabled() {
		return !!(panel && panel.attr('data-streaming') === '1' && window.fetch && window.AbortController &&
			window.TextDecoder);
	}

	function newQueryId() {
		return 'q' + Date.now().toString(36) + Math.random().toString(36).slice(2, 12);
	}

	function cancelOnServer(queryId) {
		try {
			window.fetch('/gvsigonline/etl/etl_assistant/cancel/', {
				method: 'POST',
				credentials: 'same-origin',
				headers: {'Content-Type': 'application/json', 'X-CSRFToken': Cookies.get('csrftoken')},
				body: JSON.stringify({query_id: queryId})
			}).catch(function () {
			});
		} catch (e) {
		}
	}

	/*
	 * POST al endpoint SSE. Llama a handlers.step con cada paso, a handlers.response con el resultado
	 * (el mismo JSON que /etl_assistant/) o a handlers.failure('stopped' | 'forbidden' | 'network'), y
	 * siempre a handlers.done al final. Devuelve un objeto con etlStop() para el botón Detener.
	 */
	function streamRequest(body, handlers) {
		var controller = new window.AbortController();
		var queryId = newQueryId();
		var stopped = false;
		var settled = false;
		var request = {queryId: queryId};

		function settle(fn, arg) {
			if (settled) {
				return;
			}
			settled = true;
			fn(arg);
			handlers.done();
		}

		function handleFrame(frame) {
			var data = frame.split('\n').filter(function (line) {
				return line.indexOf('data:') === 0;
			}).map(function (line) {
				return line.slice(5).replace(/^ /, '');
			}).join('\n');
			if (!data) {
				return;
			}
			var event;
			try {
				event = JSON.parse(data);
			} catch (e) {
				return;
			}
			if (event.type === 'step') {
				handlers.step(event);
			} else if (event.type === 'answer_delta' && typeof event.delta === 'string') {
				handlers.text(event);
			} else if (event.type === 'result') {
				settle(handlers.response, event.payload || {});
			}
		}

		request.etlStop = function () {
			stopped = true;
			cancelOnServer(queryId);
			controller.abort();
			settle(handlers.failure, 'stopped');
		};

		window.fetch('/gvsigonline/etl/etl_assistant/stream/', {
			method: 'POST',
			credentials: 'same-origin',
			signal: controller.signal,
			headers: {'Content-Type': 'application/json', 'X-CSRFToken': Cookies.get('csrftoken'),
				'Accept': 'text/event-stream'},
			body: JSON.stringify($.extend({}, body, {query_id: queryId}))
		}).then(function (response) {
			if (response.status === 403) {
				settle(handlers.failure, 'forbidden');
				return null;
			}
			if (!response.ok || !response.body) {
				settle(handlers.failure, 'network');
				return null;
			}
			var type = response.headers.get('Content-Type') || '';
			if (type.indexOf('application/json') === 0) {
				// Error antes de empezar el turno: mismo JSON que /etl_assistant/
				return response.json().then(function (json) {
					settle(json && json.reply !== undefined ? handlers.response : handlers.failure,
						json && json.reply !== undefined ? json : 'network');
				});
			}
			var reader = response.body.getReader();
			var decoder = new window.TextDecoder('utf-8');
			var buffer = '';
			function pump() {
				return reader.read().then(function (chunk) {
					if (chunk.done) {
						buffer += decoder.decode();
						if (buffer.trim()) {
							handleFrame(buffer);
						}
						settle(handlers.failure, stopped ? 'stopped' : 'network');
						return null;
					}
					buffer += decoder.decode(chunk.value, {stream: true});
					var frames = buffer.split('\n\n');
					buffer = frames.pop();
					frames.forEach(handleFrame);
					return settled ? reader.cancel() : pump();
				});
			}
			return pump();
		}).catch(function () {
			settle(handlers.failure, stopped ? 'stopped' : 'network');
		});
		return request;
	}

	function stepText(event) {
		var d = event.detail || {};
		var table = [d.schema, d.table].filter(Boolean).join('.');
		switch (event.tool) {
		case 'list_connections':
			return t('Checking the available connections');
		case 'list_tables':
			return d.schema ? t('Listing the tables of') + ' ' + [d.connection, d.schema].filter(Boolean).join('.')
				: t('Listing the schemas of') + ' ' + (d.connection || '');
		case 'get_table_schema':
			return t('Reading the columns of') + ' ' + table;
		case 'get_node_specs':
			return t('Reading the node specs') + (d.types ? ': ' + d.types : '');
		case 'list_files':
			return d.folder ? t('Looking for files in') + ' ' + d.folder : t('Looking for files');
		case 'get_canvas_nodes':
			return t('Reading the nodes') + (d.ids ? ' ' + d.ids : '');
		case 'check_workspace':
			return t('Checking the flow');
		case 'propose_workspace':
			return t('Validating the proposal');
		default:
			return t('Working…');
		}
	}

	var STEPS_SHOWN = 4;

	/*
	 * Texto de la respuesta mientras se genera (ETL_ASSISTANT_TOKEN_STREAMING). Con reset empieza de nuevo.
	 * Es provisional: al llegar el resultado la burbuja se sustituye por el mensaje definitivo.
	 */
	function showLiveText(typing, event) {
		var live = (event.reset ? '' : (typing.data('liveText') || '')) + event.delta;
		typing.data('liveText', live);
		var bubble = typing.find('.pl-assistant__bubble');
		var box = bubble.find('.pl-assistant__live');
		if (!box.length) {
			box = $('<div class="pl-assistant__live"></div>');
			bubble.append(box);
		}
		box.html(renderMarkdown(live));
		messagesEl.scrollTop(messagesEl[0].scrollHeight);
	}

	function showStep(typing, event) {
		var bubble = typing.find('.pl-assistant__bubble');
		var list = bubble.find('.pl-assistant__steps');
		if (!list.length) {
			list = $('<ul class="pl-assistant__steps"></ul>');
			bubble.append(list);
		}
		var label = stepText(event);
		var last = list.children().last();
		if (last.length && last.text() === label) {
			return;
		}
		list.children().removeClass('is-current');
		list.append($('<li class="pl-assistant__step is-current"></li>').text(label));
		while (list.children().length > STEPS_SHOWN) {
			list.children().first().remove();
		}
		messagesEl.scrollTop(messagesEl[0].scrollHeight);
	}

	function stopRequest() {
		if (currentXhr && currentXhr.etlStop) {
			currentXhr.etlStop();
		}
	}

	function invertAlias(summary) {
		var map = {};
		(summary.nodes || []).forEach(function (node) {
			map[node.alias] = node.id;
		});
		return map;
	}

	function bindResize() {
		var handle = panel.find('.pl-assistant__handle');
		handle.on('mousedown', function (event) {
			event.preventDefault();
			handle.addClass('is-dragging');
			var startX = event.clientX;
			var startW = panel.outerWidth();
			function move(ev) {
				var next = startW + (startX - ev.clientX);
				next = Math.max(320, Math.min(600, next));
				panel.css('width', next + 'px');
				refreshCanvas();
			}
			function up() {
				handle.removeClass('is-dragging');
				$(document).off('mousemove', move).off('mouseup', up);
				localStorage.setItem(STORAGE_WIDTH, String(panel.outerWidth()));
				refreshCanvas();
			}
			$(document).on('mousemove', move).on('mouseup', up);
		});
	}

	function init() {
		panel = $('#etl-assistant');
		if (!panel.length) {
			return;
		}
		messagesEl = $('#etl-assistant-messages');
		if (!$('#etl_id').val()) {
			// Workspace nuevo: no se arrastra la conversación de otro workspace nuevo anterior.
			try {
				sessionStorage.removeItem(workspaceKey());
			} catch (e) {
			}
		}
		input = $('#etl-assistant-input');
		examplesEl = $('#etl-assistant-examples');
		contextEl = $('#etl-assistant-context');
		sendBtn = $('#etl-assistant-send');
		renderAll();
		bindResize();
		// Tarjeta de error de ejecución (EtlRunError.js): Preguntar al asistente
		window.etlAssistantAsk = function (text) {
			setOpen(true);
			sendText(text);
		};
		$('#etl-assistant-open').on('click', function () {
			setOpen(panel.hasClass('is-collapsed'));
		});
		$('#etl-assistant-close').on('click', function () {
			setOpen(false);
		});
		$('#etl-assistant-clear').on('click', function () {
			if (!(loadState().messages || []).length || window.confirm(t('Delete the whole conversation?'))) {
				saveState({messages: []});
				aliasMap = {};
				renderAll();
			}
		});
		$('#etl-assistant-export').on('click', function () {
			if ((loadState().messages || []).length) {
				exportConversation();
			}
		});
		messagesEl.on('mouseenter', '.pl-assistant__alias', function () {
			highlightAliases([$(this).attr('data-alias')], true);
		}).on('mouseleave', '.pl-assistant__alias', function () {
			highlightAliases([$(this).attr('data-alias')], false);
		}).on('click keydown', '.pl-assistant__alias', function (event) {
			if (event.type === 'keydown' && event.key !== 'Enter' && event.key !== ' ') {
				return;
			}
			event.preventDefault();
			focusAlias($(this).attr('data-alias'));
		});
		examplesEl.on('click', '.pl-assistant__example', function () {
			if ($(this).attr('data-guided-start') && guidedEnabled()) {
				openGuided($(this));
				return;
			}
			closeGuided();
			sendText($(this).attr('data-example'));
		});
		$('#etl-assistant-form').on('submit', function (event) {
			event.preventDefault();
			if (busy) {
				stopRequest();
				return;
			}
			sendText(input.val());
		});
		input.on('keydown', function (event) {
			if (event.key === 'Enter' && !event.shiftKey) {
				event.preventDefault();
				sendText(input.val());
				return;
			}
			// ↑ / ↓ recorren las preguntas anteriores, como en una terminal.
			var atStart = this.selectionStart === 0 && this.selectionEnd === 0;
			if (event.key === 'ArrowUp' && (!input.val() || (recall !== -1 && atStart))) {
				var questions = userQuestions();
				if (!questions.length) {
					return;
				}
				event.preventDefault();
				recall = recall === -1 ? questions.length - 1 : Math.max(0, recall - 1);
				input.val(questions[recall]).trigger('input');
				this.setSelectionRange(0, 0);
			} else if (event.key === 'ArrowDown' && recall !== -1 && this.selectionStart === input.val().length) {
				var list = userQuestions();
				event.preventDefault();
				recall += 1;
				if (recall >= list.length) {
					recall = -1;
					input.val('').trigger('input');
				} else {
					input.val(list[recall]).trigger('input');
				}
			}
		});
		input.on('input', function () {
			// scrollHeight no cuenta el borde: sin sumarlo sale la barra con la segunda línea
			var border = this.offsetHeight - this.clientHeight;
			this.style.height = 'auto';
			var needed = this.scrollHeight + border;
			this.style.height = Math.min(needed, COMPOSER_MAX_HEIGHT) + 'px';
			this.style.overflowY = needed > COMPOSER_MAX_HEIGHT ? 'auto' : 'hidden';
			updateCounter();
		});
		$(document).on('keydown', function (event) {
			if (event.key !== 'Escape' || panel.hasClass('is-collapsed')) {
				return;
			}
			if ($('.modal.in, .modal.show').length) {
				return;
			}
			setOpen(false);
		});
		bindSelection(0);
		if (localStorage.getItem(STORAGE_OPEN) === '1') {
			setOpen(true);
		}
	}

	function bindSelection(attempt) {
		var canvasView = view();
		if (!canvasView || !canvasView.on) {
			if (attempt < 50) {
				setTimeout(function () {
					bindSelection(attempt + 1);
				}, 100);
			}
			return;
		}
		canvasView.on('select', function (emitter, event) {
			selectedFigure = event && event.figure;
			updateContext();
		});
		var stack = canvasView.getCommandStack && canvasView.getCommandStack();
		if (stack && stack.addEventListener) {
			stack.addEventListener(function (event) {
				if (!event || !event.isPostChangeEvent || event.isPostChangeEvent()) {
					if (selectedFigure && !selectedFigure.getCanvas()) {
						selectedFigure = null;
					}
					updateContext();
				}
			});
		}
		updateContext();
	}

	$(init);
})();
