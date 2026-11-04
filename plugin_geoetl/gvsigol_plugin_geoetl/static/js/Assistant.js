/* global gettext, jsonParams, drawNodes, etlClearCanvas, etlFindLine, EtlApplyCommand, fillEtlNodeForm, propagateSchemaFrom */

(function () {
	var STORAGE_WIDTH = 'etl-assistant-width';
	var STORAGE_OPEN = 'etl-assistant-open';
	var UNDO_LABEL = 'etl-assistant';
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
			if (message.actions) {
				body.append(message.actions);
			}
			if (message.status) {
				body.append($('<div class="pl-assistant__status"></div>').text(message.status));
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
				items.push({
					role: 'assistant',
					content: message.content || '',
					summary: message.summary || [],
					status: status
				});
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

	function applyProposal(proposal) {
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
		stack.startTransaction(UNDO_LABEL);
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
		var summary = canvasSummary();
		var types = {};
		summary.nodes.forEach(function (node) {
			types[node.alias] = node.type;
		});
		var question = {id: newId(), role: 'user', content: text};
		remember(question, {types: types, aliasMap: invertAlias(summary)});
		appendMessage(question);
		setExamplesVisible(false);
		input.val('').css('height', 'auto');
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
		currentXhr = $.ajax({
			type: 'POST',
			url: '/gvsigonline/etl/etl_assistant/',
			contentType: 'application/json',
			data: JSON.stringify({
				message: text,
				history: historyPayload().slice(0, -1),
				canvas: {
					nodes: summary.nodes,
					edges: summary.edges,
					selected: summary.selected,
					next_alias: summary.nextAlias
				},
				workspace_id: $('#etl_id').val() || null
			}),
			beforeSend: function (xhr) {
				xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
			},
			success: function (response) {
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
				if (proposal && !response.error && !response.needs_confirmation) {
					stored.settled = 'applied';
					stored.status = t('Applied');
				}
				remember(stored, {aliasMap: map, types: mergedTypes});
				stored.actions = actions;
				appendMessage(stored, mergedTypes);
			},
			error: function (xhr, textStatus) {
				typing.remove();
				var readable = t('The assistant could not be reached. Try again.');
				if (stopped || textStatus === 'abort') {
					readable = t('Stopped. The canvas has not changed.');
				} else if (xhr.status === 403) {
					readable = t('You are not allowed to use the assistant on this workspace.');
				}
				var errorMessage = {role: 'error', content: readable, retry: text};
				remember(errorMessage);
				appendMessage(errorMessage);
			},
			complete: function () {
				clearInterval(timer);
				currentXhr = null;
				setBusy(false);
				input.focus();
			}
		});
		currentXhr.etlStop = function () {
			stopped = true;
			currentXhr.abort();
		};
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
			this.style.height = 'auto';
			this.style.height = Math.min(this.scrollHeight, 140) + 'px';
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
