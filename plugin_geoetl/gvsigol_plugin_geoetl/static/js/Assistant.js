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
		if (!canvasView || !aliasMap[alias]) {
			return null;
		}
		return canvasView.getFigure(aliasMap[alias]);
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
			if (message.role === 'user' || message.role === 'assistant') {
				items.push({role: message.role, content: message.content || ''});
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
		canvasView.getFigures().each(function (i, figure) {
			if (figure instanceof draw2d.Connection) {
				return;
			}
			var alias = 'n' + counter;
			counter += 1;
			localAlias[figure.id] = alias;
			var parameters = {};
			var schema = [];
			var schemaold = [];
			for (var k = 0; k < jsonParams.length; k++) {
				if (jsonParams[k].id === figure.id) {
					parameters = (jsonParams[k].parameters && jsonParams[k].parameters[0]) || {};
					schema = jsonParams[k].schema || [];
					schemaold = jsonParams[k]['schema-old'] || [];
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
				schemaold: schemaold
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
		return {nodes: nodes, edges: edges, selected: selected, aliasOfId: localAlias};
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

	function sendText(text) {
		text = (text || '').trim();
		if (!text || busy) {
			return;
		}
		var summary = canvasSummary();
		var types = {};
		summary.nodes.forEach(function (node) {
			types[node.alias] = node.type;
		});
		remember({role: 'user', content: text}, {types: types, aliasMap: invertAlias(summary)});
		appendMessage({role: 'user', content: text});
		setExamplesVisible(false);
		input.val('').css('height', 'auto');
		busy = true;
		sendBtn.prop('disabled', true);
		input.prop('disabled', true);
		var typing = appendMessage({role: 'assistant', typing: true, content: ''});
		$.ajax({
			type: 'POST',
			url: '/gvsigonline/etl/etl_assistant/',
			contentType: 'application/json',
			data: JSON.stringify({
				message: text,
				history: historyPayload().slice(0, -1),
				canvas: {
					nodes: summary.nodes,
					edges: summary.edges,
					selected: summary.selected
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
				var messageId = 'm' + Date.now().toString(36) + Math.random().toString(36).slice(2);
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
			error: function (xhr) {
				typing.remove();
				var readable = t('The assistant could not be reached. Try again.');
				if (xhr.status === 403) {
					readable = t('You are not allowed to use the assistant on this workspace.');
				}
				var errorMessage = {role: 'error', content: readable, retry: text};
				remember(errorMessage);
				appendMessage(errorMessage);
			},
			complete: function () {
				busy = false;
				sendBtn.prop('disabled', false);
				input.prop('disabled', false);
				input.focus();
			}
		});
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
			saveState({messages: []});
			aliasMap = {};
			renderAll();
		});
		examplesEl.on('click', '.pl-assistant__example', function () {
			sendText($(this).attr('data-example'));
		});
		$('#etl-assistant-form').on('submit', function (event) {
			event.preventDefault();
			sendText(input.val());
		});
		input.on('keydown', function (event) {
			if (event.key === 'Enter' && !event.shiftKey) {
				event.preventDefault();
				sendText(input.val());
			}
		});
		input.on('input', function () {
			this.style.height = 'auto';
			this.style.height = Math.min(this.scrollHeight, 140) + 'px';
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
