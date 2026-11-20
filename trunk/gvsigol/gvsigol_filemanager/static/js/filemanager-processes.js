/*
 * Ventana de subidas y procesos del gestor de ficheros (templates/filemanager_processes.html).
 *
 * Hace las subidas que le pasan las demás páginas por BroadcastChannel (filemanager-common.js) y
 * las que se reanudan aquí, y muestra:
 *  - lo que se está subiendo o se ha subido en esta ventana,
 *  - las subidas en pausa que el servidor guarda (se continúan eligiendo otra vez el fichero),
 *  - las tareas en segundo plano del usuario (descomprimir), aunque se lanzaran desde otra página.
 */
(function () {
	'use strict';

	var G = window.GolFm;
	if (!G) {
		return;
	}
	var t = G.t, esc = G.esc, fmtSize = G.fmtSize, fmtDate = G.fmtDate, displayPath = G.displayPath;
	var ICON = G.ICON, typeIcon = G.typeIcon, api = G.api, toast = G.toast, baseName = G.baseName;
	var U = G.uploads.state;
	var server = { uploads: [], tasks: [] };
	var resumeTarget = null;
	var pollTimer = null;
	// Cierre automático: solo si esta ventana ha hecho algo y todo ha terminado bien
	var openedAt = new Date().toISOString();
	var hadWork = false;
	var keepOpen = false;
	var closeTimer = null;
	var closeIn = 0;
	var CLOSE_SECONDS = 10;
	var FINISHED = ['SUCCESS', 'FAILURE', 'REVOKED'];

	document.title = t('uploadsTitle') + ' · gvSIG Online';

	function extOf(name) {
		var parts = String(name).split('.');
		return parts.length > 1 ? parts.pop().toLowerCase() : '';
	}

	/** Subidas del servidor que no está haciendo ya esta ventana. */
	function pausedUploads() {
		return server.uploads.filter(function (p) {
			return !U.items.some(function (i) {
				return i.kind === 'upload' && i.dest === p.path && i.name === p.name && i.size === p.size &&
					(i.status === 'waiting' || i.status === 'running' || i.status === 'done');
			});
		});
	}

	function renderActive() {
		var el = document.getElementById('fx-proc-active');
		if (!U.items.length) {
			G.uploads.setHtml(el, '<div class="fx-proc-empty">' + esc(t('nothingRunning')) + '</div>');
			return;
		}
		// Filas actualizadas en el sitio para que los botones no cambien bajo el ratón
		G.uploads.setHtml(el, '<div class="fx-proc-list"></div>');
		G.uploads.patchRows(el.firstElementChild, U.items);
	}

	function renderPaused() {
		var list = pausedUploads();
		document.getElementById('fx-proc-paused-box').hidden = !list.length;
		G.uploads.setHtml(document.getElementById('fx-proc-paused'), '<div class="fx-proc-list">' + list.map(function (p) {
			var pct = p.size ? Math.floor(p.received * 100 / p.size) : 0;
			var where = displayPath((p.path ? p.path + '/' : '') + p.name);
			return '<div class="fx-up error" data-upload="' + esc(p.id) + '" title="' + esc(where) + '">' + typeIcon({ type: 'file', extension: extOf(p.name) }) +
				'<span class="nm">' + esc(baseName(p.name)) + '</span>' +
				'<div class="bar"><i style="width:' + pct + '%"></i></div>' +
				'<span class="meta">' + pct + ' % · ' + esc(fmtSize(p.received)) + ' / ' + esc(fmtSize(p.size)) + '</span>' +
				'<span class="st"><button type="button" class="fx-btn" data-resume="' + esc(p.id) + '">' + esc(t('chooseFileToResume')) + '</button>' +
				'<button type="button" class="fx-ib" data-discard="' + esc(p.id) + '" title="' + esc(t('discard')) + '" aria-label="' + esc(t('discard')) + '">' + ICON.trash + '</button></span></div>';
		}).join('') + '</div>');
	}

	function taskMeta(task) {
		if (task.state === 'SUCCESS') {
			var r = task.result || {};
			return r.ok ? { cls: 'ok', text: t('unzipped', { name: r.item ? r.item.name : '' }), width: 100, done: true } : { cls: 'err', text: r.error || t('requestFailed'), width: 100, error: true };
		}
		if (task.state === 'FAILURE' || task.state === 'REVOKED') {
			return { cls: 'err', text: t('requestFailed'), width: 100, error: true };
		}
		if (task.state === 'PROCESSING') {
			// El nombre ya está en la fila: aquí solo el avance
			return { cls: '', text: (task.progress || 0) + ' %', width: task.progress || 0 };
		}
		return { cls: '', text: t('queueWaiting'), width: 4 };
	}

	function renderTasks() {
		var list = server.tasks;
		document.getElementById('fx-proc-tasks-box').hidden = !list.length;
		G.uploads.setHtml(document.getElementById('fx-proc-tasks'), '<div class="fx-proc-list">' + list.map(function (task) {
			var m = taskMeta(task);
			return '<div class="fx-up' + (m.done ? ' done' : m.error ? ' error' : '') + '" title="' + esc(displayPath(task.path) + ' · ' + fmtDate(task.started)) + '">' + typeIcon({ type: 'file', extension: 'zip' }) +
				'<span class="nm">' + esc(task.name) + '</span>' +
				'<div class="bar"><i style="width:' + m.width + '%"></i></div>' +
				'<span class="meta ' + m.cls + '">' + esc(m.text) + '</span>' +
				'<span class="st">' + (m.done ? '<span class="ok">' + ICON.check + '</span>' : '') + '</span></div>';
		}).join('') + '</div>');
	}

	function finishedLocal(i) {
		return i.status === 'done' || i.status === 'skipped' || i.status === 'cancelled';
	}
	function taskFinished(task) {
		return FINISHED.indexOf(task.state) >= 0;
	}
	function taskFailed(task) {
		return task.state === 'FAILURE' || task.state === 'REVOKED' || (task.state === 'SUCCESS' && task.result && task.result.ok === false);
	}
	/** Tareas lanzadas mientras esta ventana estaba abierta (las antiguas no cuentan para cerrarla). */
	function sessionTasks() {
		return server.tasks.filter(function (task) { return task.started >= openedAt; });
	}

	function canAutoClose() {
		if (keepOpen || !hadWork || G.uploads.active().length) {
			return false;
		}
		if (U.items.some(function (i) { return i.status === 'error'; }) || pausedUploads().length) {
			return false;
		}
		if (server.tasks.some(function (task) { return !taskFinished(task); }) || sessionTasks().some(taskFailed)) {
			return false;
		}
		return true;
	}

	function updateAutoClose() {
		if (U.items.some(function (i) { return i.status === 'done'; }) || sessionTasks().some(function (task) { return task.state === 'SUCCESS'; })) {
			hadWork = true;
		}
		if (canAutoClose()) {
			if (!closeTimer) {
				closeIn = CLOSE_SECONDS;
				closeTimer = setInterval(function () {
					closeIn -= 1;
					if (closeIn <= 0) {
						clearInterval(closeTimer);
						closeTimer = null;
						window.close();
						return;
					}
					renderTools();
				}, 1000);
			}
		} else if (closeTimer) {
			clearInterval(closeTimer);
			closeTimer = null;
		}
	}

	function renderTools() {
		var completed = U.items.filter(finishedLocal).length + server.tasks.filter(taskFinished).length;
		G.uploads.setHtml(document.getElementById('fx-proc-notice'), closeTimer ?
			'<div class="fx-notice info fx-proc-closing"><span>' + esc(t('closingIn', { n: closeIn })) + '</span>' +
			'<button type="button" class="fx-btn" data-tool="keep">' + esc(t('keepOpen')) + '</button></div>' : '');
		G.uploads.setHtml(document.getElementById('fx-proc-tools'), completed ?
			'<button type="button" class="fx-btn ghost" data-tool="clear" title="' + esc(t('clearCompleted')) + '">' + ICON.check + esc(t('clearCompleted')) + '</button>' : '');
	}

	function clearCompleted() {
		// Lo terminado de esta ventana se quita aquí; las tareas del servidor, en su registro
		U.items = U.items.filter(function (i) { return !finishedLocal(i); });
		server.tasks = server.tasks.filter(function (task) { return !taskFinished(task); });
		render();
		api('POST', 'processes/clear/', { json: {} }).then(poll);
	}

	function render() {
		renderActive();
		renderPaused();
		renderTasks();
		updateAutoClose();
		renderTools();
	}
	G.hooks.onChange = render;

	function poll() {
		clearTimeout(pollTimer);
		return api('GET', 'processes/').then(function (r) {
			if (r.ok) {
				server.uploads = r.uploads || [];
				server.tasks = r.tasks || [];
				render();
			}
			var busy = G.uploads.active().length || server.tasks.some(function (task) { return task.state !== 'SUCCESS' && task.state !== 'FAILURE' && task.state !== 'REVOKED'; });
			pollTimer = setTimeout(poll, busy ? 2000 : 6000);
		});
	}

	document.getElementById('fx-proc').addEventListener('click', function (e) {
		var tool = e.target.closest('[data-tool]');
		if (tool) {
			if (tool.getAttribute('data-tool') === 'keep') {
				keepOpen = true;
				updateAutoClose();
				renderTools();
			} else {
				clearCompleted();
			}
			return;
		}
		var resume = e.target.closest('[data-resume]');
		if (resume) {
			resumeTarget = server.uploads.filter(function (p) { return p.id === resume.getAttribute('data-resume'); })[0] || null;
			if (resumeTarget) {
				document.getElementById('fx-proc-resume').click();
			}
			return;
		}
		var discard = e.target.closest('[data-discard]');
		if (discard) {
			var id = discard.getAttribute('data-discard');
			G.dialog({
				icon: ICON.trash,
				iconClass: 'd',
				title: t('discardTitle'),
				sub: t('discardSub'),
				buttons: [{ label: t('cancel'), value: null }, { label: t('discard'), value: 'ok', cls: 'danger-solid', primary: true }]
			}).then(function (v) {
				if (v) {
					api('POST', 'upload/' + encodeURIComponent(id) + '/cancel/', { json: {} }).then(poll);
				}
			});
			return;
		}
		var b = e.target.closest('[data-u]');
		if (b) {
			var key = +b.closest('[data-key]').getAttribute('data-key');
			var it = U.items.filter(function (i) { return i.key === key; })[0];
			if (it) {
				if (b.getAttribute('data-u') === 'cancel') {
					G.uploads.cancel(it);
				} else {
					G.uploads.retry(it);
				}
			}
		}
	});

	document.getElementById('fx-proc-resume').addEventListener('change', function (e) {
		var file = e.target.files[0];
		e.target.value = '';
		var p = resumeTarget;
		resumeTarget = null;
		if (!file || !p) {
			return;
		}
		// El servidor reconoce la subida por usuario, carpeta, nombre y tamaño
		if (file.size !== p.size) {
			toast(t('resumeMismatch', { name: baseName(p.name), size: fmtSize(p.size) }), { error: true });
			return;
		}
		G.uploads.add([{ file: file, rel: p.name, policy: p.on_conflict && p.on_conflict !== 'error' ? p.on_conflict : null }], p.path);
	});

	G.hooks.onDone = function () {
		poll();
	};

	render();
	poll();
})();
