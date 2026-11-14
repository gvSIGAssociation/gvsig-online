/*
 * Gestor de ficheros de gvSIG Online: piezas comunes de la interfaz nueva (utilidades, iconos,
 * API, avisos, diálogos y el motor de subidas por trozos).
 *
 * Lo usan filemanager-explorer.js (página y selector) y filemanager-processes.js (ventana de
 * subidas y procesos). Expone window.GolFm. Lee la configuración (#fm-config) y los textos
 * (#fm-i18n) de la página, y pinta avisos y diálogos en #fx-layer.
 *
 * Subidas en segundo plano: la ventana de procesos («processes») recibe ficheros de otras páginas
 * por BroadcastChannel (canal CHANNEL_NAME) y sigue subiendo mientras se navega. Mensajes:
 *   ping -> pong {state}; enqueue {id, entries:[{file, rel, dest, policy}]} -> enqueued {id};
 *   state {active, percent, items}; uploaded {dest, item}.
 */
(function () {
	'use strict';

	var cfgEl = document.getElementById('fm-config');
	if (!cfgEl) {
		return;
	}
	var CFG = JSON.parse(cfgEl.textContent);
	var T = JSON.parse(document.getElementById('fm-i18n').textContent);
	var layer = document.getElementById('fx-layer');
	// Página que carga el motor: 'explorer' (gestor y selector) o 'processes' (ventana de subidas)
	var ROLE = CFG.role || 'explorer';
	var hooks = {
		// Se llama al terminar una subida o descompresión: (carpeta de destino, elemento)
		onDone: function () {},
		// Se llama cuando cambia la lista de subidas (lo usa la ventana de procesos para pintarla)
		onChange: function () {},
		// Resumen que emite la ventana de procesos ({active, percent, errors}); lo usa el botón
		// de subidas de la barra del gestor
		onProcesses: function () {}
	};

	// --- Utilidades -----------------------------------------------------------------------------

	var LOCALE = (function () {
		var tag = String(CFG.language || 'es').replace('_', '-');
		try {
			new Intl.NumberFormat(tag);
			return tag;
		} catch (e) {
			return 'es';
		}
	})();
	var NUM1 = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 1 });
	var NUM0 = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 0 });
	var DATEF = new Intl.DateTimeFormat(LOCALE, { dateStyle: 'short', timeStyle: 'short' });

	function t(key, vars) {
		var s = T[key] != null ? T[key] : key;
		if (vars) {
			Object.keys(vars).forEach(function (k) {
				s = s.split('{' + k + '}').join(vars[k]);
			});
		}
		return s;
	}
	function esc(s) {
		return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
			return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
		});
	}
	function fmtSize(bytes) {
		if (bytes == null) {
			return '';
		}
		var units = ['B', 'KB', 'MB', 'GB', 'TB'];
		var i = 0;
		var n = bytes;
		while (n >= 1024 && i < units.length - 1) {
			n /= 1024;
			i++;
		}
		return (i ? NUM1 : NUM0).format(n) + ' ' + units[i];
	}
	function fmtDate(iso) {
		if (!iso) {
			return '';
		}
		var d = new Date(iso);
		return isNaN(d) ? '' : DATEF.format(d);
	}
	function parentOf(p) {
		var i = p.lastIndexOf('/');
		return i < 0 ? '' : p.slice(0, i);
	}
	function baseName(p) {
		return p ? p.slice(p.lastIndexOf('/') + 1) : 'data';
	}
	function displayPath(p) {
		return 'data' + (p ? '/' + p : '');
	}
	function encodePath(p) {
		return p.split('/').map(encodeURIComponent).join('/');
	}
	function isInside(path, dir) {
		return path === dir || path.indexOf(dir + '/') === 0;
	}
	function csrf() {
		var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
		return m ? decodeURIComponent(m[1]) : '';
	}
	function query(params) {
		var u = new URLSearchParams();
		Object.keys(params).forEach(function (k) {
			var v = params[k];
			if (Array.isArray(v)) {
				v.forEach(function (x) { u.append(k, x); });
			} else if (v != null) {
				u.append(k, v);
			}
		});
		return u.toString();
	}
	function sleep(ms) {
		return new Promise(function (r) { setTimeout(r, ms); });
	}
	function pref(key, fallback) {
		try {
			var v = localStorage.getItem('fx.' + key);
			return v == null ? fallback : v === '1';
		} catch (e) {
			return fallback;
		}
	}
	function savePref(key, value) {
		try {
			localStorage.setItem('fx.' + key, value ? '1' : '0');
		} catch (e) { /* sin almacenamiento: no se recuerda */ }
	}

	// --- Iconos ----------------------------------------------------------------------------------

	function svg(path, extra) {
		return '<svg class="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"' + (extra || '') + '>' + path + '</svg>';
	}
	var ICON = {
		folder: '<svg class="i" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3 6.5A2.5 2.5 0 0 1 5.5 4h3.6c.6 0 1.2.24 1.65.66L12.2 6H18.5A2.5 2.5 0 0 1 21 8.5v9a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 17.5v-11Z"/></svg>',
		caret: svg('<path d="m9 6 6 6-6 6"/>'),
		upload: svg('<path d="M12 16V4M7 9l5-5 5 5M5 20h14"/>'),
		plus: svg('<path d="M12 5v14M5 12h14"/>'),
		download: svg('<path d="M12 4v12M7 11l5 5 5-5M5 20h14"/>'),
		move: svg('<path d="M3 7.5A2.5 2.5 0 0 1 5.5 5H9l2 2h7.5A2.5 2.5 0 0 1 21 9.5v8a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 17.5Z"/><path d="M10 13.5h6M13.5 11l2.5 2.5-2.5 2.5"/>'),
		copy: svg('<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>'),
		rename: svg('<path d="M4 20h4L19 9l-4-4L4 16v4Z"/>'),
		trash: svg('<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>'),
		db: svg('<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3"/>'),
		unzip: svg('<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M12 3v2M12 7v2M12 11v2M10.5 15h3v3h-3z"/>'),
		more: '<svg class="i" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="5" cy="12" r="1.8"/><circle cx="12" cy="12" r="1.8"/><circle cx="19" cy="12" r="1.8"/></svg>',
		info: svg('<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>'),
		tree: svg('<path d="M4 5h6M4 5v14h6M4 12h6M14 5h6M14 12h6M14 19h6"/>'),
		panel: svg('<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M15 4v16"/>'),
		search: svg('<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4-4"/>'),
		restore: svg('<path d="M4 12a8 8 0 1 0 2.3-5.6L4 8.7M4 4v4.7h4.7"/>'),
		close: svg('<path d="M6 6l12 12M18 6 6 18"/>'),
		warn: svg('<path d="M12 4 2.5 20h19L12 4Z"/><path d="M12 10v4M12 17v.5"/>'),
		check: svg('<path d="m5 12 5 5 9-10"/>', ' stroke-width="2.4"'),
		history: svg('<path d="M12 8v4l3 2"/><circle cx="12" cy="12" r="9"/>'),
		classic: svg('<path d="M4 6h16M4 12h16M4 18h16"/>'),
		chevDown: svg('<path d="m6 9 6 6 6-6"/>'),
		minus: svg('<path d="M5 12h14"/>'),
		cloud: svg('<path d="M7 18a4.5 4.5 0 0 1-.7-8.95A6 6 0 0 1 17.8 8.6 4.5 4.5 0 0 1 17 18"/><path d="M12 20v-8M9 15l3-3 3 3"/>')
	};

	var KINDS = {
		vec: ['shp', 'dbf', 'shx', 'prj', 'cpg', 'qpj', 'sbn', 'sbx', 'gpkg', 'geojson', 'json', 'kml', 'kmz', 'gml', 'gpx', 'dxf'],
		ras: ['tif', 'tiff', 'geotiff', 'jp2', 'ecw', 'img', 'asc', 'vrt', 'tfw', 'mbtiles'],
		pc: ['las', 'laz', 'copc'],
		tab: ['csv', 'xls', 'xlsx', 'ods', 'tsv'],
		zip: ['zip', 'rar', '7z', 'gz', 'tar', 'tgz'],
		img: ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'bmp']
	};
	var EXPORTABLE = ['shp', 'dbf', 'gpkg'];
	var TRANSFORMABLE = ['csv', 'xlsx'];
	var BACKGROUND_UNZIP_SIZE = 100 * 1024 * 1024;

	function kindOf(item) {
		if (item.type === 'directory') {
			return 'dir';
		}
		var e = (item.extension || '').toLowerCase();
		var found = 'doc';
		Object.keys(KINDS).forEach(function (k) {
			if (KINDS[k].indexOf(e) >= 0) {
				found = k;
			}
		});
		return found;
	}
	function typeIcon(item, big) {
		var k = kindOf(item);
		if (k === 'dir') {
			return '<span class="fx-ft dir' + (big ? ' big' : '') + '">' + ICON.folder + '</span>';
		}
		var ext = (item.extension || '').toUpperCase().slice(0, 4);
		return '<span class="fx-ft ' + k + (big ? ' big' : '') + '">' + esc(ext) + '</span>';
	}

	// --- API -------------------------------------------------------------------------------------

	function api(method, endpoint, opts) {
		opts = opts || {};
		var url = CFG.api + endpoint + (opts.query ? '?' + opts.query : '');
		var headers = { 'X-CSRFToken': csrf(), 'Accept': 'application/json' };
		var body;
		if (opts.raw !== undefined) {
			headers['Content-Type'] = 'application/octet-stream';
			body = opts.raw;
		} else if (opts.json) {
			headers['Content-Type'] = 'application/json';
			body = JSON.stringify(opts.json);
		}
		return fetch(url, { method: method, headers: headers, body: body, credentials: 'same-origin' }).then(function (resp) {
			return resp.json().catch(function () {
				return { ok: false };
			}).then(function (data) {
				data = data || {};
				data.status = resp.status;
				if (!resp.ok) {
					data.ok = false;
				}
				if (data.ok === false && !data.error && !data.results) {
					data.error = t('requestFailed');
				}
				return data;
			});
		}, function () {
			return { ok: false, network: true, status: 0, error: t('requestFailed') };
		});
	}

	// --- Avisos ----------------------------------------------------------------------------------

	var toastBox = document.createElement('div');
	toastBox.className = 'fx-toasts';
	toastBox.setAttribute('role', 'status');
	toastBox.setAttribute('aria-live', 'polite');
	layer.appendChild(toastBox);

	function toast(message, opts) {
		opts = opts || {};
		var el = document.createElement('div');
		el.className = 'fx-toast' + (opts.error ? ' err' : '');
		var body = '<div>' + esc(message) + (opts.list && opts.list.length ? '<ul>' + opts.list.map(function (l) { return '<li>' + esc(l) + '</li>'; }).join('') + '</ul>' : '') + '</div>';
		el.innerHTML = body + (opts.undo ? '<button type="button" data-undo="1">' + esc(t('undo')) + '</button>' : '') +
			(opts.action ? '<button type="button" data-action="1">' + esc(opts.action.label) + '</button>' : '') +
			'<button type="button" data-x="1" aria-label="' + esc(t('close')) + '">' + ICON.close + '</button>';
		toastBox.appendChild(el);
		var timer = setTimeout(remove, opts.error ? 12000 : 7000);
		function remove() {
			clearTimeout(timer);
			el.remove();
		}
		el.addEventListener('click', function (e) {
			if (e.target.closest('[data-undo]')) {
				remove();
				opts.undo();
			} else if (e.target.closest('[data-action]')) {
				remove();
				opts.action.run();
			} else if (e.target.closest('[data-x]')) {
				remove();
			}
		});
	}
	function failuresOf(r) {
		return (r.results || []).filter(function (x) { return !x.ok; });
	}
	function reportFailures(fails) {
		if (fails.length) {
			toast(t('partialErrors', { n: fails.length }), {
				error: true,
				list: fails.slice(0, 5).map(function (f) { return baseName(f.path) + ': ' + f.error; })
			});
		}
	}

	// --- Diálogos --------------------------------------------------------------------------------

	/**
	 * Diálogo modal. opts: icon, iconClass, title, sub, body (HTML), buttons [{label, value, cls}],
	 * wide, onOpen(root), submit(value, root) -> Promise<string|null> (error a mostrar o null).
	 * Devuelve una promesa con el valor del botón pulsado, o null si se cancela.
	 */
	function dialog(opts) {
		return new Promise(function (resolve) {
			var previous = document.activeElement;
			var scrim = document.createElement('div');
			scrim.className = 'fx-scrim';
			scrim.innerHTML = '<div class="fx-dialog' + (opts.wide ? ' wide' : '') + '" role="dialog" aria-modal="true" aria-labelledby="fx-dlg-title">' +
				'<header>' + (opts.icon ? '<span class="ic ' + (opts.iconClass || '') + '">' + opts.icon + '</span>' : '') +
				'<div><h2 id="fx-dlg-title">' + esc(opts.title) + '</h2>' + (opts.sub ? '<p class="sub">' + esc(opts.sub) + '</p>' : '') + '</div></header>' +
				'<div class="body"' + (opts.icon ? '' : ' style="padding-left:20px"') + '>' + (opts.body || '') + '<div class="err" hidden></div></div>' +
				'<footer>' + opts.buttons.map(function (b, i) {
					return '<button type="button" class="fx-btn ' + (b.cls || '') + '" data-i="' + i + '">' + esc(b.label) + '</button>';
				}).join('') + '</footer></div>';
			layer.appendChild(scrim);
			var root = scrim.querySelector('.fx-dialog');
			var errEl = root.querySelector('.err');
			var busy = false;
			function close(value) {
				document.removeEventListener('keydown', onKey, true);
				scrim.remove();
				if (previous && previous.focus) {
					previous.focus();
				}
				resolve(value);
			}
			function choose(btn) {
				if (busy) {
					return;
				}
				if (btn.value === null || !opts.submit) {
					close(btn.value);
					return;
				}
				busy = true;
				root.querySelectorAll('footer button').forEach(function (b) { b.disabled = true; });
				Promise.resolve(opts.submit(btn.value, root)).then(function (error) {
					busy = false;
					root.querySelectorAll('footer button').forEach(function (b) { b.disabled = false; });
					if (error) {
						errEl.textContent = error;
						errEl.hidden = false;
					} else {
						close(btn.value);
					}
				});
			}
			function onKey(e) {
				if (e.key === 'Escape') {
					e.stopPropagation();
					close(null);
				} else if (e.key === 'Enter' && e.target.tagName === 'INPUT' && e.target.type === 'text') {
					e.preventDefault();
					var primary = opts.buttons.filter(function (b) { return b.primary; })[0];
					if (primary) {
						choose(primary);
					}
				} else if (e.key === 'Tab') {
					var f = root.querySelectorAll('button:not([disabled]), input:not([disabled]), a[href]');
					if (!f.length) {
						return;
					}
					if (e.shiftKey && document.activeElement === f[0]) {
						e.preventDefault();
						f[f.length - 1].focus();
					} else if (!e.shiftKey && document.activeElement === f[f.length - 1]) {
						e.preventDefault();
						f[0].focus();
					}
				}
			}
			document.addEventListener('keydown', onKey, true);
			scrim.addEventListener('mousedown', function (e) {
				if (e.target === scrim) {
					close(null);
				}
			});
			root.querySelector('footer').addEventListener('click', function (e) {
				var b = e.target.closest('[data-i]');
				if (b) {
					choose(opts.buttons[+b.getAttribute('data-i')]);
				}
			});
			if (opts.onOpen) {
				opts.onOpen(root);
			}
			var focus = root.querySelector('input[type=text]') || root.querySelector('footer .primary, footer .danger-solid') || root.querySelector('footer button');
			if (focus) {
				focus.focus();
			}
		});
	}

	// --- Subidas por trozos y tareas -------------------------------------------------------------

	var U = { items: [], running: 0, max: 2, seq: 0, collapsed: false };
	var panel = null;
	var renderQueued = false;
	var conflictChain = Promise.resolve();

	function activeUploads() {
		return U.items.filter(function (i) { return i.status === 'waiting' || i.status === 'running'; });
	}
	function addUploads(entries, dest) {
		var batch = { policy: null, cancelled: false, size: entries.length };
		entries.forEach(function (en) {
			// policy: la ya elegida en otra página al traspasar la subida (si no, se pregunta)
			U.items.push({ key: ++U.seq, kind: 'upload', file: en.file, name: en.rel, dest: dest, size: en.file.size, received: 0, status: 'waiting', batch: batch, tries: 0, policy: en.policy || null });
		});
		U.collapsed = false;
		pump();
	}
	function pump() {
		while (U.running < U.max) {
			var next = null;
			for (var i = 0; i < U.items.length; i++) {
				if (U.items[i].status === 'waiting' && U.items[i].kind === 'upload') {
					next = U.items[i];
					break;
				}
			}
			if (!next) {
				break;
			}
			U.running++;
			(function (it) {
				runUpload(it).then(null, function () {
					fail(it, t('requestFailed'), true);
				}).then(function () {
					U.running--;
					if (it.status === 'done') {
						finished(it.dest, it.result);
					}
					renderUploads();
					pump();
				});
			})(next);
		}
		renderUploads();
	}
	function fail(it, message, resumable) {
		it.status = 'error';
		it.error = message;
		it.resumable = !!resumable;
	}
	function pct(it) {
		return it.size ? Math.floor(it.received * 100 / it.size) : 100;
	}

	function askConflict(it) {
		var batch = it.batch;
		var p = conflictChain.then(function () {
			if (batch.cancelled) {
				return null;
			}
			if (batch.policy) {
				return batch.policy;
			}
			var policy = 'rename';
			return dialog({
				icon: ICON.warn,
				iconClass: 'w',
				title: t('conflictTitle', { name: baseName(it.name) }),
				sub: t('conflictSub', { path: displayPath(parentOf(it.dest + '/' + it.name).replace(/^\//, '')) }),
				body: '<div class="fx-radios" role="radiogroup">' +
					radio('rename', t('keepBoth'), t('keepBothHint'), true) +
					radio('replace', t('replace'), t('replaceHint')) +
					radio('skip', t('skip'), t('skipHint')) + '</div>' +
					(batch.size > 1 ? '<label class="fx-checkline"><input type="checkbox" id="fx-apply-all"> ' + esc(t('applyToAll')) + '</label>' : ''),
				buttons: [{ label: t('cancelUploads'), value: null }, { label: t('continue'), value: 'ok', cls: 'primary', primary: true }],
				onOpen: function (root) {
					root.querySelector('.fx-radios').addEventListener('change', function (e) {
						policy = e.target.value;
						root.querySelectorAll('.fx-radios label').forEach(function (l) {
							l.classList.toggle('on', l.querySelector('input').checked);
						});
					});
				},
				submit: function (v, root) {
					var all = root.querySelector('#fx-apply-all');
					if (all && all.checked) {
						batch.policy = policy;
					}
					return Promise.resolve(null);
				}
			}).then(function (v) {
				if (!v) {
					batch.cancelled = true;
					U.items.forEach(function (x) {
						if (x.batch === batch && x.status === 'waiting') {
							x.status = 'cancelled';
						}
					});
					return null;
				}
				return policy;
			});
		});
		conflictChain = p.then(null, function () {});
		return p;
	}
	function radio(value, label, hint, checked) {
		return '<label' + (checked ? ' class="on"' : '') + '><input type="radio" name="fx-conflict" value="' + value + '"' + (checked ? ' checked' : '') + '><span>' + esc(label) + '<small>' + esc(hint) + '</small></span></label>';
	}

	function initUpload(it, policy) {
		return api('POST', 'upload/', { json: { path: it.dest, name: it.name, size: it.size, on_conflict: policy } });
	}

	function runUpload(it) {
		it.status = 'running';
		it.error = null;
		var start;
		if (!it.id) {
			start = initUpload(it, it.policy || it.batch.policy || 'error').then(function (r) {
				if (r.status === 409 && r.conflict) {
					return askConflict(it).then(function (choice) {
						if (!choice) {
							it.status = 'cancelled';
							return null;
						}
						it.policy = choice;
						return initUpload(it, choice);
					});
				}
				return r;
			}).then(function (r) {
				if (!r || it.status === 'cancelled' || it.cancel) {
					return false;
				}
				if (!r.ok) {
					fail(it, r.error, false);
					return false;
				}
				if (r.skipped) {
					it.status = 'skipped';
					return false;
				}
				it.id = r.id;
				it.chunk = r.chunk_size;
				it.received = r.received || 0;
				return true;
			});
		} else {
			start = api('GET', 'upload/' + it.id + '/').then(function (r) {
				if (!r.ok) {
					if (r.status === 404) {
						// Caducó: se empieza de nuevo
						it.id = null;
						it.received = 0;
						return runUpload(it).then(function () { return false; });
					}
					fail(it, r.error, true);
					return false;
				}
				it.received = r.received;
				it.chunk = r.chunk_size;
				return true;
			});
		}
		return start.then(function (go) {
			if (!go) {
				return;
			}
			return sendChunks(it);
		});
	}

	function sendChunks(it) {
		if (it.cancel) {
			return Promise.resolve();
		}
		if (it.received >= it.size) {
			return api('POST', 'upload/' + it.id + '/complete/', { json: {} }).then(function (r) {
				if (!r.ok) {
					fail(it, r.error, false);
					return;
				}
				it.status = r.skipped ? 'skipped' : 'done';
				it.result = r.item;
			});
		}
		var end = Math.min(it.size, it.received + it.chunk);
		return api('POST', 'upload/' + it.id + '/chunk/', { query: query({ offset: it.received }), raw: it.file.slice(it.received, end) }).then(function (r) {
			if (it.cancel) {
				return;
			}
			if (r.ok) {
				it.received = r.received;
				it.tries = 0;
				queueRender();
				return sendChunks(it);
			}
			if (r.status === 409 && typeof r.received === 'number') {
				it.received = r.received;
				return sendChunks(it);
			}
			if ((r.network || r.status >= 500) && it.tries < 5) {
				it.tries++;
				queueRender();
				return sleep(1000 * Math.pow(2, it.tries - 1)).then(function () { return sendChunks(it); });
			}
			fail(it, r.network ? t('interrupted', { p: pct(it) }) : r.error, true);
		});
	}

	function cancelItem(it) {
		if (it.status === 'running') {
			it.cancel = true;
		}
		if (it.id) {
			api('POST', 'upload/' + it.id + '/cancel/', { json: {} });
		}
		it.status = 'cancelled';
		renderUploads();
	}
	function retryItem(it) {
		it.status = 'waiting';
		it.tries = 0;
		it.cancel = false;
		if (!it.resumable) {
			it.id = null;
			it.received = 0;
		}
		pump();
	}

	function unzipItem(item) {
		var task = { key: ++U.seq, kind: 'task', name: item.name, status: 'running', progress: null, started: Date.now(), dest: parentOf(item.path) };
		U.items.push(task);
		U.collapsed = false;
		renderUploads();
		var background = (item.size || 0) > BACKGROUND_UNZIP_SIZE;
		function finish(r) {
			if (r && r.ok && r.item) {
				task.status = 'done';
				task.result = r.item;
				task.progress = 100;
				toast(t('unzipped', { name: r.item.name }));
				finished(task.dest, r.item);
			} else {
				task.status = 'error';
				task.error = (r && r.error) || t('requestFailed');
			}
			renderUploads();
		}
		function sync() {
			return api('POST', 'unzip/', { json: { path: item.path } }).then(finish);
		}
		if (!background) {
			return sync();
		}
		return api('POST', 'unzip/', { json: { path: item.path, background: true } }).then(function (r) {
			if (r.status === 202 && r.task_id) {
				return poll(r.task_id);
			}
			if (r.status >= 500) {
				return sync();
			}
			finish(r);
		});
		function poll(id) {
			return sleep(1000).then(function () {
				return api('GET', 'task/' + encodeURIComponent(id) + '/');
			}).then(function (r) {
				if (!r.ok) {
					return finish(r);
				}
				if (r.state === 'SUCCESS' || r.state === 'FAILURE' || r.state === 'REVOKED') {
					return finish(r.result || { ok: false });
				}
				task.progress = r.state === 'PROCESSING' ? r.progress : null;
				task.queued = r.state === 'PENDING' && Date.now() - task.started > 15000;
				queueRender();
				return poll(id);
			});
		}
	}

	function queueRender() {
		if (!renderQueued) {
			renderQueued = true;
			requestAnimationFrame(function () {
				renderQueued = false;
				renderUploads();
			});
		}
	}

	function uploadRow(it) {
		var ext = it.kind === 'task' ? 'zip' : (it.name.split('.').length > 1 ? it.name.split('.').pop().toLowerCase() : '');
		var icon = typeIcon({ type: 'file', extension: ext });
		var width = it.kind === 'task' ? (it.status === 'done' ? 100 : (it.progress != null ? it.progress : 8)) : (it.status === 'done' ? 100 : pct(it));
		var meta;
		var cls = '';
		var actions = '';
		if (it.status === 'waiting') {
			meta = t('waiting');
			actions = '<button type="button" class="fx-ib" data-u="cancel" title="' + esc(t('cancelItem')) + '" aria-label="' + esc(t('cancelItem')) + '">' + ICON.close + '</button>';
		} else if (it.status === 'running') {
			if (it.kind === 'task') {
				meta = it.queued ? t('queueWaiting') : t('unzipping', { name: it.name }) + (it.progress != null ? ' · ' + it.progress + ' %' : '');
			} else {
				meta = fmtSize(it.received) + ' / ' + fmtSize(it.size) + ' · ' + pct(it) + ' %';
				actions = '<button type="button" class="fx-ib" data-u="cancel" title="' + esc(t('cancelItem')) + '" aria-label="' + esc(t('cancelItem')) + '">' + ICON.close + '</button>';
			}
		} else if (it.status === 'done') {
			meta = it.kind === 'task' ? t('unzipped', { name: it.result ? it.result.name : '' }) : t('uploaded') + (it.result && it.result.name !== baseName(it.name) ? ' · ' + it.result.name : '');
			cls = 'ok';
			actions = '<span class="ok">' + ICON.check + '</span>';
		} else if (it.status === 'moving') {
			meta = t('movingToProcesses');
		} else if (it.status === 'moved') {
			meta = t('movedToProcesses');
			cls = 'ok';
		} else if (it.status === 'skipped') {
			meta = t('skipped');
		} else if (it.status === 'cancelled') {
			meta = t('cancelled');
		} else {
			meta = it.error || t('requestFailed');
			cls = 'err';
			if (it.kind === 'upload') {
				actions = '<button type="button" class="fx-btn" data-u="retry" style="padding:3px 9px">' + esc(t('retry')) + '</button>';
			}
		}
		return '<div class="fx-up ' + (it.status === 'done' ? 'done' : it.status === 'error' ? 'error' : '') + '" data-key="' + it.key + '">' + icon +
			'<span class="nm" title="' + esc(it.name) + '">' + esc(it.name) + '</span>' +
			'<div class="bar"><i style="width:' + width + '%"></i></div>' +
			'<span class="meta ' + cls + '">' + esc(meta) + '</span><span class="st">' + actions + '</span></div>';
	}

	/**
	 * Pinta solo lo que cambia. Si se rehiciera el HTML entero con cada trozo (varias veces por
	 * segundo), un botón podría cambiar entre el «mousedown» y el «mouseup» y el clic se perdería.
	 */
	function setHtml(el, html) {
		if (el._fxHtml !== html) {
			el._fxHtml = html;
			el.innerHTML = html;
		}
	}

	/** Actualiza las filas de una lista de subidas: barra y texto en el sitio; el resto, si cambia. */
	function patchRows(listEl, items) {
		var keep = {};
		items.forEach(function (it) {
			var html = uploadRow(it);
			var sig = html.replace(/width:[\d.]+%/, '').replace(/<span class="meta[^"]*">[\s\S]*?<\/span>/, '');
			var row = listEl.querySelector('[data-key="' + it.key + '"]');
			keep[it.key] = true;
			var tmp = document.createElement('div');
			tmp.innerHTML = html;
			var fresh = tmp.firstElementChild;
			if (row && row._fxSig === sig) {
				row.querySelector('.bar i').style.width = fresh.querySelector('.bar i').style.width;
				var meta = row.querySelector('.meta');
				var newMeta = fresh.querySelector('.meta');
				if (meta.textContent !== newMeta.textContent) {
					meta.textContent = newMeta.textContent;
				}
				meta.className = newMeta.className;
				meta.title = newMeta.textContent;
				return;
			}
			fresh._fxSig = sig;
			// El estado puede recortarse en ventanas estrechas: completo al pasar el ratón
			var freshMeta = fresh.querySelector('.meta');
			if (freshMeta) {
				freshMeta.title = freshMeta.textContent;
			}
			if (row) {
				row.replaceWith(fresh);
			} else {
				listEl.appendChild(fresh);
			}
		});
		Array.prototype.slice.call(listEl.children).forEach(function (r) {
			if (!keep[r.getAttribute('data-key')]) {
				r.remove();
			}
		});
	}

	function renderUploads() {
		broadcastState();
		if (ROLE === 'processes') {
			// La ventana de procesos pinta su propia lista
			hooks.onChange();
			return;
		}
		if (!U.items.length) {
			if (panel) {
				panel.remove();
				panel = null;
			}
			return;
		}
		if (!panel) {
			panel = document.createElement('section');
			panel.className = 'fx-uploads';
			panel.setAttribute('aria-label', t('uploadsTitle'));
			panel.innerHTML = '<header></header><div class="bg-slot"></div><div class="list"></div>';
			layer.appendChild(panel);
			panel.addEventListener('click', function (e) {
				if (e.target.closest('[data-panel="collapse"]')) {
					U.collapsed = !U.collapsed;
					renderUploads();
					return;
				}
				if (e.target.closest('[data-panel="background"]')) {
					moveToProcessesWindow();
					return;
				}
				if (e.target.closest('[data-panel="close"]')) {
					U.items = U.items.filter(function (i) { return i.status === 'waiting' || i.status === 'running'; });
					renderUploads();
					return;
				}
				var b = e.target.closest('[data-u]');
				if (!b) {
					return;
				}
				var key = +b.closest('[data-key]').getAttribute('data-key');
				var it = U.items.filter(function (i) { return i.key === key; })[0];
				if (!it) {
					return;
				}
				if (b.getAttribute('data-u') === 'cancel') {
					cancelItem(it);
				} else {
					retryItem(it);
				}
			});
		}
		var active = activeUploads().length;
		var title = active ? t('uploadingN', { n: active }) : t('uploadsDone');
		setHtml(panel.querySelector('header'), '<span>' + esc(title) + '</span><span>' +
			'<button type="button" data-panel="collapse" aria-label="' + esc(t('uploadsTitle')) + '">' + (U.collapsed ? ICON.chevDown.replace('<path', '<path transform="rotate(180 12 12)"') : ICON.minus) + '</button>' +
			(active ? '' : '<button type="button" data-panel="close" aria-label="' + esc(t('close')) + '">' + ICON.close + '</button>') +
			'</span>');
		setHtml(panel.querySelector('.bg-slot'), !U.collapsed && localActive() && channel ?
			'<div class="bg"><button type="button" class="fx-btn" data-panel="background">' + ICON.move + esc(t('continueInBackground')) + '</button><small>' + esc(t('continueInBackgroundHint')) + '</small></div>' : '');
		var listEl = panel.querySelector('.list');
		listEl.hidden = U.collapsed;
		patchRows(listEl, U.items);
	}

	window.addEventListener('beforeunload', function (e) {
		if (activeUploads().length) {
			e.preventDefault();
			e.returnValue = ROLE === 'processes' ? t('leaveWarningProcesses') : t('leaveWarning');
			return e.returnValue;
		}
	});


	function localActive() {
		return U.items.some(function (i) { return i.kind === 'upload' && (i.status === 'waiting' || i.status === 'running'); });
	}

	function finished(dest, item) {
		if (channel) {
			channel.postMessage({ type: 'uploaded', dest: dest, item: item || null });
		}
		hooks.onDone(dest, item);
	}

	// --- Ventana de subidas y procesos (BroadcastChannel) ---------------------------------------

	var CHANNEL_NAME = 'gvsigol-filemanager';
	var PROCESSES_WINDOW = 'gvsigol-filemanager-processes';
	var channel = window.BroadcastChannel ? new BroadcastChannel(CHANNEL_NAME) : null;
	var stateTimer = null;

	/** Resumen para el botón de subidas del gestor y las otras páginas. */
	function stateSummary() {
		var uploadsActive = U.items.filter(function (i) { return i.kind === 'upload' && (i.status === 'waiting' || i.status === 'running'); });
		var tasksActive = U.items.filter(function (i) { return i.kind === 'task' && i.status === 'running'; });
		var total = 0;
		var done = 0;
		uploadsActive.forEach(function (i) {
			total += i.size || 0;
			done += i.received || 0;
		});
		return {
			type: 'state',
			role: ROLE,
			active: uploadsActive.length + tasksActive.length,
			percent: total ? Math.floor(done * 100 / total) : null,
			errors: U.items.filter(function (i) { return i.status === 'error'; }).length
		};
	}
	function broadcastState() {
		if (!channel || ROLE !== 'processes' || stateTimer) {
			return;
		}
		stateTimer = setTimeout(function () {
			stateTimer = null;
			channel.postMessage(stateSummary());
		}, 300);
	}

	/** URL de la ventana de procesos (la vista filemanager:processes). */
	function processesUrl() {
		return CFG.browserUrl + 'processes/';
	}

	/**
	 * Abre (o trae al frente) la ventana de procesos sin recargarla: window.open con una URL la
	 * recargaría y cortaría sus subidas. Debe llamarse desde un clic del usuario.
	 */
	/** Tamaño y posición de la ventana: pequeña y abajo a la derecha de la pantalla. */
	var PROCESSES_W = 400;
	var PROCESSES_H = 460;
	function processesWindowFeatures() {
		var sw = screen.availWidth || 1280;
		var sh = screen.availHeight || 800;
		var left = (screen.availLeft || 0) + Math.max(0, sw - PROCESSES_W - 24);
		var top = (screen.availTop || 0) + Math.max(0, sh - PROCESSES_H - 64);
		return 'width=' + PROCESSES_W + ',height=' + PROCESSES_H + ',left=' + left + ',top=' + top;
	}

	function openProcessesWindow() {
		var w = null;
		try {
			w = window.open('', PROCESSES_WINDOW, processesWindowFeatures());
		} catch (e) {
			w = null;
		}
		if (!w) {
			return null;
		}
		try {
			if (!w.location.href || w.location.href === 'about:blank') {
				w.location.href = processesUrl();
			}
		} catch (e) { /* otra página en esa ventana: se deja */ }
		try {
			w.focus();
		} catch (e) { /* sin foco */ }
		return w;
	}

	/** Promesa: true si responde una ventana de procesos en `ms` milisegundos. */
	function processesWindowAlive(ms) {
		return new Promise(function (resolve) {
			if (!channel) {
				resolve(false);
				return;
			}
			var done = false;
			function onMsg(e) {
				if (e.data && e.data.type === 'pong') {
					done = true;
					channel.removeEventListener('message', onMsg);
					resolve(true);
				}
			}
			channel.addEventListener('message', onMsg);
			channel.postMessage({ type: 'ping' });
			setTimeout(function () {
				if (!done) {
					channel.removeEventListener('message', onMsg);
					resolve(false);
				}
			}, ms || 300);
		});
	}

	/** Envía ficheros a la ventana de procesos. Promesa: true si los ha aceptado. */
	function sendToProcesses(entries) {
		return new Promise(function (resolve) {
			if (!channel || !entries.length) {
				resolve(false);
				return;
			}
			var id = 'e' + Date.now() + Math.random().toString(16).slice(2);
			var done = false;
			function onMsg(e) {
				if (e.data && e.data.type === 'enqueued' && e.data.id === id) {
					done = true;
					channel.removeEventListener('message', onMsg);
					resolve(true);
				}
			}
			channel.addEventListener('message', onMsg);
			try {
				channel.postMessage({ type: 'enqueue', id: id, entries: entries });
			} catch (e) {
				channel.removeEventListener('message', onMsg);
				resolve(false);
				return;
			}
			setTimeout(function () {
				if (!done) {
					channel.removeEventListener('message', onMsg);
					resolve(false);
				}
			}, 3000);
		});
	}

	function entriesOf(items) {
		return items.map(function (i) {
			return { file: i.file, rel: i.name, dest: i.dest, policy: i.policy || i.batch.policy || null };
		});
	}

	/**
	 * Sube ficheros: si hay una ventana de procesos abierta se los pasa (así se puede navegar);
	 * si no, se suben en esta página, con la opción de pasarlos después a segundo plano.
	 */
	function startUploads(entries, dest) {
		if (ROLE === 'processes') {
			addUploads(entries, dest);
			return Promise.resolve('local');
		}
		return processesWindowAlive(300).then(function (alive) {
			if (!alive) {
				addUploads(entries, dest);
				return 'local';
			}
			var withDest = entries.map(function (en) { return { file: en.file, rel: en.rel, dest: dest, policy: null }; });
			return sendToProcesses(withDest).then(function (ok) {
				if (!ok) {
					addUploads(entries, dest);
					return 'local';
				}
				toast(t('sentToProcesses', { n: entries.length }), { action: { label: t('showProcesses'), run: openProcessesWindow } });
				return 'background';
			});
		});
	}

	/**
	 * «Continuar en segundo plano»: abre la ventana de procesos (desde el clic del usuario) y le
	 * pasa las subidas pendientes de esta página. La ventana las reanuda desde lo ya recibido
	 * (el servidor reconoce usuario, carpeta, nombre y tamaño), así que no se repite nada.
	 */
	function moveToProcessesWindow(onDone) {
		onDone = onDone || function () {};
		var w = openProcessesWindow();
		if (!w) {
			toast(t('popupBlocked'), { error: true });
			onDone(false);
			return;
		}
		var pending = U.items.filter(function (i) { return i.kind === 'upload' && (i.status === 'waiting' || i.status === 'running'); });
		// Se paran ya, sin cancelarlas en el servidor (la ventana las reanuda desde lo recibido):
		// si siguieran mientras carga la ventana, podrían terminar aquí y subirse dos veces.
		pending.forEach(function (i) {
			i.cancel = true;
			i.status = 'moving';
		});
		renderUploads();
		var tries = 0;
		(function wait() {
			processesWindowAlive(400).then(function (alive) {
				if (!alive) {
					if (++tries < 25) {
						wait();
					} else {
						resumeHere(pending);
						toast(t('requestFailed'), { error: true });
						onDone(false);
					}
					return;
				}
				sendToProcesses(entriesOf(pending)).then(function (ok) {
					if (ok) {
						pending.forEach(function (i) {
							i.status = 'moved';
						});
						renderUploads();
					} else {
						resumeHere(pending);
						toast(t('requestFailed'), { error: true });
					}
					onDone(ok);
				});
			});
		})();
	}

	/**
	 * Red de seguridad: con subidas en curso en esta página, un enlace que saca de ella pregunta
	 * antes. Cada pantalla de la administración es una página distinta y salir corta las subidas.
	 * El clic en el diálogo es un gesto del usuario, así que puede abrir la ventana de procesos.
	 */
	document.addEventListener('click', function (e) {
		if (ROLE === 'processes' || !channel || !localActive() || e.defaultPrevented) {
			return;
		}
		if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) {
			return;
		}
		var a = e.target.closest && e.target.closest('a[href]');
		if (!a || a.hasAttribute('download') || (a.target && a.target !== '_self')) {
			return;
		}
		var href = a.getAttribute('href') || '';
		if (!href || href.charAt(0) === '#' || href.indexOf('javascript:') === 0) {
			return;
		}
		e.preventDefault();
		var url = a.href;
		dialog({
			icon: ICON.upload,
			iconClass: 'w',
			title: t('leaveWithUploadsTitle'),
			sub: t('leaveWithUploadsSub'),
			buttons: [
				{ label: t('stayHere'), value: null },
				{ label: t('leaveAndStop'), value: 'leave', cls: 'danger' },
				{ label: t('continueAndGo'), value: 'background', cls: 'primary', primary: true }
			]
		}).then(function (v) {
			if (v === 'leave') {
				U.items.forEach(function (i) {
					if (i.kind === 'upload' && (i.status === 'waiting' || i.status === 'running')) {
						i.cancel = true;
						i.status = 'cancelled';
					}
				});
				location.href = url;
			} else if (v === 'background') {
				moveToProcessesWindow(function (ok) {
					if (ok) {
						location.href = url;
					}
				});
			}
		});
	}, true);

	/** El traspaso no ha salido: se siguen subiendo aquí desde lo ya recibido. */
	function resumeHere(items) {
		items.forEach(function (i) {
			i.cancel = false;
			i.resumable = true;
			i.status = 'waiting';
		});
		pump();
	}

	if (channel) {
		channel.addEventListener('message', function (e) {
			var msg = e.data || {};
			if (ROLE === 'processes') {
				if (msg.type === 'ping') {
					var st = stateSummary();
					st.type = 'pong';
					channel.postMessage(st);
					channel.postMessage(stateSummary());
				} else if (msg.type === 'enqueue' && Array.isArray(msg.entries)) {
					var groups = {};
					msg.entries.forEach(function (en) {
						(groups[en.dest] = groups[en.dest] || []).push(en);
					});
					Object.keys(groups).forEach(function (dest) {
						addUploads(groups[dest].map(function (en) { return { file: en.file, rel: en.rel, policy: en.policy }; }), dest);
					});
					channel.postMessage({ type: 'enqueued', id: msg.id });
				}
			} else if (msg.type === 'uploaded') {
				// Subida terminada en la ventana de procesos: la página actualiza su carpeta
				hooks.onDone(msg.dest, msg.item);
			} else if ((msg.type === 'state' || msg.type === 'pong') && msg.role === 'processes') {
				hooks.onProcesses(msg);
			}
		});
	}

	window.GolFm = {
		CFG: CFG,
		T: T,
		ROLE: ROLE,
		hooks: hooks,
		LOCALE: LOCALE,
		t: t,
		esc: esc,
		fmtSize: fmtSize,
		fmtDate: fmtDate,
		parentOf: parentOf,
		baseName: baseName,
		displayPath: displayPath,
		encodePath: encodePath,
		isInside: isInside,
		query: query,
		sleep: sleep,
		pref: pref,
		savePref: savePref,
		ICON: ICON,
		KINDS: KINDS,
		EXPORTABLE: EXPORTABLE,
		TRANSFORMABLE: TRANSFORMABLE,
		kindOf: kindOf,
		typeIcon: typeIcon,
		api: api,
		toast: toast,
		failuresOf: failuresOf,
		reportFailures: reportFailures,
		dialog: dialog,
		uploads: {
			state: U,
			start: startUploads,
			add: addUploads,
			unzip: unzipItem,
			cancel: cancelItem,
			retry: retryItem,
			active: activeUploads,
			row: uploadRow,
			patchRows: patchRows,
			setHtml: setHtml,
			render: renderUploads,
			summary: stateSummary
		},
		openProcessesWindow: openProcessesWindow,
		processesWindowAlive: processesWindowAlive
	};
})();
