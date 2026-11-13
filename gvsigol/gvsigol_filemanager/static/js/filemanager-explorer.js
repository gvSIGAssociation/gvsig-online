/*
 * Gestor de ficheros de gvSIG Online: interfaz de explorador (árbol + lista + detalles).
 *
 * Lo pinta todo a partir de la API JSON del módulo (gvsigol_filemanager/api.py). La plantilla
 * browser/filemanager_explorer.html le pasa la configuración (#fm-config) y los textos ya
 * traducidos (#fm-i18n). Sin dependencias: JavaScript del navegador, sin compilar.
 *
 * Contratos con el servidor que no hay que romper: rutas relativas a FILEMANAGER_DIRECTORY,
 * cabecera X-CSRFToken en los POST, respuestas {ok, error, ...} y resultados por elemento en las
 * operaciones múltiples (results).
 */
(function () {
	'use strict';

	var cfgEl = document.getElementById('fm-config');
	var fx = document.getElementById('fx');
	if (!cfgEl || !fx) {
		return;
	}
	var CFG = JSON.parse(cfgEl.textContent);
	var T = JSON.parse(document.getElementById('fm-i18n').textContent);
	var layer = document.getElementById('fx-layer');
	// Selector (?popup=1): elegir un fichero o carpeta para otra pantalla. Mismo contrato que el
	// clásico: window.opener.filemanagerCallback(ruta relativa a FILEMANAGER_DIRECTORY, window.name).
	// Sin acciones que cambien o borren datos; ?ext=tif,tiff limita lo que se muestra y se elige.
	var POPUP = !!CFG.popup;
	var EXTS = CFG.extensions || [];
	// ?multiple=1: el selector deja elegir varios y los envía todos juntos
	var MULTI = POPUP && !!CFG.multiple;
	if (MULTI) {
		fx.classList.add('fx-multi');
	}

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
		minus: svg('<path d="M5 12h14"/>')
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

	// --- Estado ----------------------------------------------------------------------------------

	var S = {
		path: CFG.path || '',
		view: 'files',
		items: [],
		crumbs: [],
		canWrite: false,
		loading: false,
		error: null,
		selected: new Set(),
		anchor: null,
		sort: { key: 'name', dir: 1 },
		filter: '',
		trash: [],
		trashLoading: false,
		tree: new Map(),
		treeOpen: new Set(['']),
		drag: null
	};
	// Por debajo de este ancho el árbol se abre superpuesto (en el selector, ventana pequeña, antes)
	var narrow = window.matchMedia(POPUP ? '(max-width: 599px)' : '(max-width: 1100px)');
	if (!POPUP && !pref('tree', true)) {
		fx.classList.add('no-tree');
	}
	if (!POPUP && !pref('details', true)) {
		fx.classList.add('no-details');
	}

	function byPath(path) {
		for (var i = 0; i < S.items.length; i++) {
			if (S.items[i].path === path) {
				return S.items[i];
			}
		}
		return null;
	}
	function selectedItems() {
		return S.items.filter(function (i) { return S.selected.has(i.path); });
	}
	function canChange(item) {
		return item.can_modify && !item.in_use_by;
	}
	function visibleItems() {
		var list = S.items;
		if (EXTS.length) {
			list = list.filter(function (i) { return i.type === 'directory' || EXTS.indexOf(i.extension) >= 0; });
		}
		if (S.filter) {
			var f = S.filter.toLowerCase();
			list = list.filter(function (i) { return i.name.toLowerCase().indexOf(f) >= 0; });
		}
		var key = S.sort.key;
		var dir = S.sort.dir;
		return list.slice().sort(function (a, b) {
			if (a.type !== b.type) {
				return a.type === 'directory' ? -1 : 1;
			}
			var r;
			if (key === 'size') {
				r = (a.size || 0) - (b.size || 0);
			} else if (key === 'modified') {
				r = String(a.modified || '').localeCompare(String(b.modified || ''));
			} else {
				r = a.name.localeCompare(b.name, LOCALE, { sensitivity: 'base', numeric: true });
			}
			return r * dir || a.name.localeCompare(b.name);
		});
	}

	// --- Navegación ------------------------------------------------------------------------------

	function urlFor(path) {
		var p = new URLSearchParams();
		if (path) {
			p.set('path', path);
		}
		if (POPUP) {
			p.set('popup', '1');
			if (EXTS.length) {
				p.set('ext', EXTS.join(','));
			}
			if (MULTI) {
				p.set('multiple', '1');
			}
		}
		if (CFG.keepUiParam) {
			p.set('ui', 'new');
		}
		var s = p.toString();
		return CFG.browserUrl + (s ? '?' + s : '');
	}

	function navigate(path, opts) {
		opts = opts || {};
		closeMenu();
		S.view = 'files';
		if (path !== S.path) {
			// No mostrar la carpeta anterior mientras se carga la nueva
			S.items = [];
		}
		S.path = path;
		S.error = null;
		S.selected.clear();
		S.anchor = null;
		S.filter = '';
		if (opts.history !== false) {
			history.pushState({ fxPath: path }, '', urlFor(path));
		}
		fx.classList.remove('tree-overlay');
		var loading = loadFolder(false);
		expandTo(path);
		return loading;
	}

	function loadFolder(keepSelection) {
		S.loading = true;
		if (!keepSelection) {
			renderAll();
		}
		var requested = S.path;
		return api('GET', 'list/', { query: query({ path: requested }) }).then(function (r) {
			if (requested !== S.path || S.view !== 'files') {
				return;
			}
			S.loading = false;
			if (!r.ok) {
				if ((r.status === 404 || r.status === 403 || r.status === 400) && S.path) {
					toast(r.error, { error: true });
					return navigate(parentOf(S.path), { history: false }).then(function () {
						history.replaceState({ fxPath: S.path }, '', urlFor(S.path));
					});
				}
				S.error = r.error;
				S.items = [];
				renderAll();
				return;
			}
			S.error = null;
			S.items = r.items || [];
			S.canWrite = !!r.can_write;
			S.crumbs = r.breadcrumbs || [];
			if (keepSelection) {
				var present = new Set(S.items.map(function (i) { return i.path; }));
				S.selected.forEach(function (p) {
					if (!present.has(p)) {
						S.selected.delete(p);
					}
				});
			}
			renderAll();
		});
	}

	window.addEventListener('popstate', function (e) {
		var path = e.state && typeof e.state.fxPath === 'string' ? e.state.fxPath : (new URLSearchParams(location.search).get('path') || '');
		navigate(path, { history: false });
	});

	// --- Árbol -----------------------------------------------------------------------------------

	function loadChildren(path) {
		var node = S.tree.get(path);
		if (node && (node.loaded || node.loading)) {
			return node.promise;
		}
		node = { loaded: false, loading: true, children: [] };
		S.tree.set(path, node);
		node.promise = api('GET', 'list/', { query: query({ path: path, dirs_only: 1 }) }).then(function (r) {
			node.loading = false;
			node.loaded = true;
			node.error = r.ok ? null : r.error;
			node.children = r.ok ? r.items.filter(function (i) {
				return i.name.charAt(0) !== '.';
			}).map(function (i) {
				return { name: i.name, path: i.path, has_subdirs: i.has_subdirs };
			}) : [];
		});
		return node.promise;
	}

	function expandTo(path) {
		var parts = path ? path.split('/') : [];
		var chain = [''];
		var acc = '';
		parts.slice(0, -1).forEach(function (p) {
			acc = acc ? acc + '/' + p : p;
			chain.push(acc);
		});
		var p = Promise.resolve();
		chain.forEach(function (dir) {
			S.treeOpen.add(dir);
			p = p.then(function () { return loadChildren(dir); });
		});
		return p.then(renderTree);
	}

	/** Vuelve a leer las carpetas abiertas del árbol tras un cambio de estructura. */
	function refreshTree() {
		S.tree.clear();
		var open = Array.from(S.treeOpen).sort(function (a, b) { return a.split('/').length - b.split('/').length; });
		var p = Promise.resolve();
		open.forEach(function (dir) {
			p = p.then(function () { return loadChildren(dir); });
		});
		renderTree();
		return p.then(renderTree);
	}

	function treeHtml(openSet, current, opts) {
		function node(n, depth) {
			var st = S.tree.get(n.path);
			var open = openSet.has(n.path);
			var leaf = n.has_subdirs === false || (st && st.loaded && !st.children.length);
			var disabled = opts.isDisabled && opts.isDisabled(n.path);
			var h = '<li><div class="fx-node' + (n.path === current ? ' on' : '') + '" data-tree-path="' + esc(n.path) + '" style="padding-left:' + (depth * 14) + 'px"' + (disabled ? ' aria-disabled="true"' : '') + '>' +
				'<button type="button" class="fx-caret' + (open ? ' open' : '') + (leaf ? ' leaf' : '') + '" data-tree-toggle="' + esc(n.path) + '" tabindex="-1" aria-label="' + esc(n.name) + '">' + ICON.caret + '</button>' +
				'<button type="button" class="fx-node-label" data-tree-go="' + esc(n.path) + '"' + (disabled ? ' disabled style="opacity:.45"' : '') + ' title="' + esc(displayPath(n.path)) + '">' + ICON.folder + '<span>' + esc(n.name) + '</span></button></div>';
			if (open && !leaf) {
				if (!st || st.loading) {
					h += '<div class="fx-tree-msg" style="padding-left:' + (depth * 14 + 30) + 'px">' + esc(t('loading')) + '</div>';
				} else if (st.error) {
					h += '<div class="fx-tree-msg" style="padding-left:' + (depth * 14 + 30) + 'px">' + esc(st.error) + '</div>';
				} else {
					h += '<ul>' + st.children.map(function (c) { return node(c, depth + 1); }).join('') + '</ul>';
				}
			}
			return h + '</li>';
		}
		var html = '<div class="sect">' + esc(t('folders')) + '</div><ul>' + node({ name: 'data', path: '', has_subdirs: true }, 0) + '</ul>';
		if (opts.trash) {
			html += '<div class="sect">&nbsp;</div><div class="fx-node' + (S.view === 'trash' ? ' on' : '') + '"><span class="fx-caret leaf"></span>' +
				'<button type="button" class="fx-node-label" data-act="trash">' + ICON.trash.replace('class="i"', 'class="i trash-ic"') + '<span>' + esc(t('trash')) + '</span></button></div>';
		}
		return html;
	}

	function renderTree() {
		var el = document.getElementById('fx-tree');
		var scroll = el.scrollTop;
		el.innerHTML = treeHtml(S.treeOpen, S.view === 'files' ? S.path : null, { trash: !POPUP });
		el.scrollTop = scroll;
	}

	function handleTreeClick(e, openSet, onGo, rerender) {
		var toggle = e.target.closest('[data-tree-toggle]');
		if (toggle) {
			var p = toggle.getAttribute('data-tree-toggle');
			if (openSet.has(p)) {
				openSet.delete(p);
				rerender();
			} else {
				openSet.add(p);
				rerender();
				loadChildren(p).then(rerender);
			}
			return true;
		}
		var go = e.target.closest('[data-tree-go]');
		if (go && !go.disabled) {
			onGo(go.getAttribute('data-tree-go'));
			return true;
		}
		return false;
	}

	document.getElementById('fx-tree').addEventListener('click', function (e) {
		if (handleTreeClick(e, S.treeOpen, function (p) { navigate(p); }, renderTree)) {
			return;
		}
		var act = e.target.closest('[data-act="trash"]');
		if (act) {
			showTrash();
		}
	});

	// --- Pintado ---------------------------------------------------------------------------------

	function renderAll() {
		renderHead();
		renderList();
		renderDetails();
		renderStatus();
		renderTree();
		renderPick();
	}

	function crumbsHtml() {
		if (S.view === 'trash') {
			return '<nav class="fx-crumbs" aria-label="' + esc(t('path')) + '"><button type="button" data-go="">data</button><span class="sep">/</span><b>' + esc(t('trash')) + '</b></nav>';
		}
		var crumbs = S.crumbs.length ? S.crumbs : [{ label: 'data', path: '' }];
		var out = crumbs.map(function (c, i) {
			if (i === crumbs.length - 1) {
				return '<b>' + esc(c.label) + '</b>';
			}
			return '<button type="button" data-go="' + esc(c.path) + '" data-drop-path="' + esc(c.path) + '">' + esc(c.label) + '</button>';
		});
		return '<nav class="fx-crumbs" aria-label="' + esc(t('path')) + '">' + out.join('<span class="sep">/</span>') + '</nav>';
	}

	function renderHead() {
		var el = document.getElementById('fx-head');
		if (S.view === 'files' && S.selected.size && !POPUP) {
			el.innerHTML = selbarHtml();
			return;
		}
		var tools;
		if (S.view === 'trash') {
			tools = '<button type="button" class="fx-btn icon-only" data-act="toggle-tree" title="' + esc(t('toggleTree')) + '">' + ICON.tree + '</button>' +
				'<button type="button" class="fx-btn" data-act="files">' + esc(t('backToFiles')) + '</button>';
		} else if (POPUP) {
			var pdis = S.canWrite ? '' : ' disabled title="' + esc(t('readOnlyFolder')) + '"';
			tools = '<label class="fx-search">' + ICON.search + '<input type="search" id="fx-filter" placeholder="' + esc(t('search')) + '" aria-label="' + esc(t('search')) + '" value="' + esc(S.filter) + '"></label>' +
				'<button type="button" class="fx-btn icon-only" data-act="toggle-tree" title="' + esc(t('toggleTree')) + '" aria-label="' + esc(t('toggleTree')) + '">' + ICON.tree + '</button>' +
				'<button type="button" class="fx-btn icon-only" data-act="new-folder" title="' + esc(t('newFolder')) + '" aria-label="' + esc(t('newFolder')) + '"' + pdis + '>' + ICON.plus + '</button>' +
				'<button type="button" class="fx-btn" data-act="upload-menu" aria-haspopup="menu"' + pdis + '>' + ICON.upload + esc(t('upload')) + ICON.chevDown + '</button>' +
				'<button type="button" class="fx-btn icon-only ghost" data-act="classic" title="' + esc(t('classicView')) + '" aria-label="' + esc(t('classicView')) + '">' + ICON.classic + '</button>';
		} else {
			var dis = S.canWrite ? '' : ' disabled title="' + esc(t('readOnlyFolder')) + '"';
			tools = '<label class="fx-search">' + ICON.search + '<input type="search" id="fx-filter" placeholder="' + esc(t('search')) + '" aria-label="' + esc(t('search')) + '" value="' + esc(S.filter) + '"></label>' +
				'<button type="button" class="fx-btn icon-only" data-act="toggle-tree" title="' + esc(t('toggleTree')) + '" aria-label="' + esc(t('toggleTree')) + '">' + ICON.tree + '</button>' +
				'<button type="button" class="fx-btn" data-act="new-folder"' + dis + '>' + ICON.plus + esc(t('newFolder')) + '</button>' +
				'<button type="button" class="fx-btn primary" data-act="upload-menu" aria-haspopup="menu"' + dis + '>' + ICON.upload + esc(t('upload')) + ICON.chevDown + '</button>' +
				'<button type="button" class="fx-btn icon-only' + (fx.classList.contains('no-details') ? '' : ' on') + '" data-act="toggle-details" title="' + esc(t('toggleDetails')) + '" aria-label="' + esc(t('toggleDetails')) + '">' + ICON.panel + '</button>' +
				'<button type="button" class="fx-btn icon-only ghost" data-act="page-menu" aria-haspopup="menu" title="' + esc(t('moreActions')) + '" aria-label="' + esc(t('moreActions')) + '">' + ICON.more + '</button>';
		}
		el.innerHTML = '<div class="fx-headbar">' + crumbsHtml() + '<div class="fx-tools">' + tools + '</div></div>';
	}

	function selbarHtml() {
		var items = selectedItems();
		var n = items.length;
		var changeable = items.every(canChange);
		var blockTitle = changeable ? '' : ' title="' + esc(t('notAllowed')) + '"';
		var dis = changeable ? '' : ' disabled';
		return '<div class="fx-selbar"><span class="fx-count">' + esc(t('selectedCount', { n: n })) + '</span>' +
			'<button type="button" class="fx-btn" data-act="download">' + ICON.download + esc(n > 1 || (items[0] && items[0].type === 'directory') ? t('downloadZip') : t('download')) + '</button>' +
			'<button type="button" class="fx-btn" data-act="move"' + dis + blockTitle + '>' + ICON.move + esc(t('moveTo')) + '</button>' +
			'<button type="button" class="fx-btn" data-act="copy">' + ICON.copy + esc(t('copyTo')) + '</button>' +
			(n === 1 ? '<button type="button" class="fx-btn" data-act="rename"' + dis + blockTitle + '>' + ICON.rename + esc(t('rename')) + '</button>' : '') +
			'<button type="button" class="fx-btn danger" data-act="trash-selected"' + dis + blockTitle + '>' + ICON.trash + esc(t('toTrash')) + '</button>' +
			'<span class="fx-spacer"></span><button type="button" class="fx-btn ghost" data-act="clear">' + ICON.close + esc(t('clearSelection')) + '</button></div>';
	}

	function badgesHtml(item) {
		var h = '';
		if (item.companions && item.companions.length) {
			h += '<span class="fx-badge grp" title="' + esc(t('relatedTitle', { names: item.companions.join(', ') })) + '">' + esc(t('related', { n: item.companions.length })) + '</span>';
		}
		if (item.in_use_by) {
			h += '<span class="fx-badge use" title="' + esc(t('inUseTitle', { name: item.in_use_by })) + '">' + esc(t('inUse')) + '</span>';
		}
		return h;
	}

	function sortHeader(key, label, cls) {
		var arrow = S.sort.key === key ? '<span class="arrow">' + (S.sort.dir > 0 ? '↑' : '↓') + '</span>' : '';
		var aria = S.sort.key === key ? (S.sort.dir > 0 ? 'ascending' : 'descending') : 'none';
		return '<th class="' + (cls || '') + '" aria-sort="' + aria + '"><button type="button" data-sort="' + key + '">' + esc(label) + arrow + '</button></th>';
	}

	function renderList() {
		var el = document.getElementById('fx-list');
		if (S.view === 'trash') {
			el.innerHTML = trashHtml();
			return;
		}
		if (S.loading && !S.items.length) {
			el.innerHTML = '<div class="fx-loading">' + esc(t('loading')) + '</div>';
			return;
		}
		if (S.error) {
			el.innerHTML = '<div class="fx-error">' + esc(S.error) + '</div>';
			return;
		}
		var list = visibleItems();
		if (!list.length) {
			el.innerHTML = '<div class="fx-empty">' + typeIcon({ type: 'directory' }, true) +
				(S.filter ? '<strong>' + esc(t('noMatches', { q: S.filter })) + '</strong>' :
					'<strong>' + esc(t('emptyFolder')) + '</strong>' + (S.canWrite ? '<span>' + esc(t('emptyFolderHint')) + '</span>' : '')) + '</div>';
			return;
		}
		var all = list.every(function (i) { return S.selected.has(i.path); });
		var h = '<table class="fx-table"><thead><tr><th class="chk"><input type="checkbox" data-role="check-all" aria-label="' + esc(t('selectAll')) + '"' + (all ? ' checked' : '') + '></th>' +
			sortHeader('name', t('name')) + sortHeader('size', t('size'), 'num') + sortHeader('modified', t('modified')) +
			'<th class="num"><span class="sr-only">' + esc(t('actions')) + '</span></th></tr></thead><tbody>';
		list.forEach(function (it) {
			var sel = S.selected.has(it.path);
			var isDir = it.type === 'directory';
			h += '<tr data-path="' + esc(it.path) + '" class="' + (sel ? 'sel' : '') + '"' + (canChange(it) && !POPUP ? ' draggable="true"' : '') + (isDir ? ' data-drop-path="' + esc(it.path) + '"' : '') + '>' +
				'<td class="chk"><input type="checkbox" data-role="check" aria-label="' + esc(t('selectItem', { name: it.name })) + '"' + (sel ? ' checked' : '') + '></td>' +
				'<td><div class="fx-name">' + typeIcon(it) + '<span class="lbl' + (isDir ? ' dir" data-role="open' : '') + '" title="' + esc(it.name) + '">' + esc(it.name) + '</span>' + badgesHtml(it) + '</div></td>' +
				'<td class="num muted">' + esc(isDir ? '' : fmtSize(it.size)) + '</td>' +
				'<td class="muted">' + esc(fmtDate(it.modified)) + '</td>' +
				'<td><div class="fx-rowacts">' +
				(isDir ? '' : '<button type="button" class="fx-ib" data-act="download-one" title="' + esc(t('download')) + '" aria-label="' + esc(t('download')) + '">' + ICON.download + '</button>') +
				'<button type="button" class="fx-ib" data-act="details-one" title="' + esc(t('details')) + '" aria-label="' + esc(t('details')) + '">' + ICON.info + '</button>' +
				'<button type="button" class="fx-ib" data-act="row-menu" title="' + esc(t('moreActions')) + '" aria-label="' + esc(t('moreActions')) + '" aria-haspopup="menu">' + ICON.more + '</button>' +
				'</div></td></tr>';
		});
		el.innerHTML = h + '</tbody></table>';
	}

	/** Actualiza la selección sin volver a pintar la lista (no rompe el doble clic). */
	function syncSelection() {
		var rows = document.querySelectorAll('#fx-list tr[data-path]');
		var all = rows.length > 0;
		rows.forEach(function (row) {
			var sel = S.selected.has(row.getAttribute('data-path'));
			row.classList.toggle('sel', sel);
			var c = row.querySelector('[data-role="check"]');
			if (c) {
				c.checked = sel;
			}
			if (!sel) {
				all = false;
			}
		});
		var ca = document.querySelector('#fx-list [data-role="check-all"]');
		if (ca) {
			ca.checked = all;
		}
		renderHead();
		renderDetails();
		renderStatus();
		renderPick();
	}

	function kindLabel(item) {
		var k = kindOf(item);
		if (k === 'dir') {
			return t('folder');
		}
		return t('kind_' + k) + (item.extension ? ' (' + item.extension.toUpperCase() + ')' : '');
	}

	function renderDetails() {
		var el = document.getElementById('fx-details');
		if (S.view !== 'files') {
			el.innerHTML = '<div class="none">' + esc(t('trashNote', { days: CFG.trashDays })) + '</div>';
			return;
		}
		var items = selectedItems();
		if (!items.length) {
			el.innerHTML = '<div class="none">' + ICON.info.replace('class="i"', 'class="i" style="width:26px;height:26px"') + '<br>' + esc(t('detailsEmpty')) + '</div>';
			return;
		}
		if (items.length > 1) {
			var files = items.filter(function (i) { return i.type !== 'directory'; });
			var total = files.reduce(function (s, i) { return s + (i.size || 0); }, 0);
			el.innerHTML = '<div class="head">' + typeIcon({ type: 'directory' }, true) + '<h3>' + esc(t('nSelected', { n: items.length })) + '</h3></div>' +
				'<dl><dt>' + esc(t('filesCount')) + '</dt><dd>' + files.length + '</dd><dt>' + esc(t('foldersLabel')) + '</dt><dd>' + (items.length - files.length) + '</dd>' +
				'<dt>' + esc(t('totalSize')) + '</dt><dd>' + esc(fmtSize(total)) + (items.length > files.length ? ' +' : '') + '</dd></dl>' + detailActions(items);
			return;
		}
		var it = items[0];
		var h = '<div class="head">' + typeIcon(it, true) + '<h3>' + esc(it.name) + '</h3></div>';
		if (it.in_use_by) {
			h += '<div class="fx-notice warn">' + esc(t('inUseNotice', { name: it.in_use_by })) + '</div>';
		}
		h += '<dl><dt>' + esc(t('type')) + '</dt><dd>' + esc(kindLabel(it)) + '</dd>';
		if (it.type !== 'directory') {
			h += '<dt>' + esc(t('size')) + '</dt><dd>' + esc(fmtSize(it.size)) + '</dd>';
		}
		h += '<dt>' + esc(t('modified')) + '</dt><dd>' + esc(fmtDate(it.modified)) + '</dd>';
		if (it.companions && it.companions.length) {
			h += '<dt>' + esc(t('relatedFiles')) + '</dt><dd>' + it.companions.map(esc).join('<br>') + '</dd>';
		}
		h += '<dt>' + esc(t('path')) + '</dt><dd class="path">' + esc(displayPath(it.path)) + '</dd></dl>';
		el.innerHTML = h + detailActions(items);
	}

	function detailActions(items) {
		var it = items[0];
		var single = items.length === 1;
		var changeable = items.every(canChange);
		var dis = changeable ? '' : ' disabled title="' + esc(t('notAllowed')) + '"';
		var ext = single ? (it.extension || '') : '';
		var h = '<div class="acts">' +
			'<button type="button" class="fx-btn" data-act="download">' + ICON.download + esc(single && it.type !== 'directory' ? t('download') : t('downloadZip')) + '</button>' +
			(single ? '<button type="button" class="fx-btn" data-act="rename"' + dis + '>' + ICON.rename + esc(t('rename')) + '</button>' : '') +
			'<button type="button" class="fx-btn" data-act="move"' + dis + '>' + ICON.move + esc(t('moveTo')) + '</button>' +
			'<button type="button" class="fx-btn" data-act="copy">' + ICON.copy + esc(t('copyTo')) + '</button>';
		if (single && EXPORTABLE.indexOf(ext) >= 0) {
			h += '<a class="fx-btn wide" href="' + esc(CFG.exportUrl + '?path=' + encodeURIComponent(it.path)) + '">' + ICON.db + esc(t('exportToDatabase')) + '</a>';
		}
		if (single && CFG.transformUrl && TRANSFORMABLE.indexOf(ext) >= 0) {
			h += '<a class="fx-btn wide" href="' + esc(CFG.transformUrl + '?path=' + encodeURIComponent(it.path)) + '">' + ICON.db + esc(t('transformToDatabase')) + '</a>';
		}
		if (single && ext === 'zip' && S.canWrite) {
			h += '<button type="button" class="fx-btn wide" data-act="unzip">' + ICON.unzip + esc(t('unzipHere')) + '</button>';
		}
		h += '<button type="button" class="fx-btn danger wide" data-act="trash-selected"' + dis + '>' + ICON.trash + esc(t('toTrash')) + '</button>';
		return h + '</div>';
	}

	function renderStatus() {
		var el = document.getElementById('fx-status');
		if (S.view === 'trash') {
			el.innerHTML = '<span>' + esc(S.trash.length === 1 ? t('oneItem') : t('items', { n: S.trash.length })) + '</span>';
			return;
		}
		var dirs = S.items.filter(function (i) { return i.type === 'directory'; }).length;
		var left = (S.items.length === 1 ? t('oneItem') : t('items', { n: S.items.length })) + ' · ' + t('foldersCount', { n: dirs });
		if (S.selected.size) {
			left += ' · ' + t('selectedCount', { n: S.selected.size });
		}
		var right = S.canWrite ? t('dragHint') : (S.loading ? '' : t('readOnlyFolder'));
		if (POPUP) {
			right = EXTS.length ? t('pickOnly', { exts: EXTS.map(function (x) { return '.' + x; }).join(', ') }) : t(MULTI ? 'pickHintMulti' : 'pickHint');
		}
		el.innerHTML = '<span>' + esc(left) + '</span><span>' + esc(right) + '</span>';
	}

	// --- Selección -------------------------------------------------------------------------------

	function clickSelect(path, e, fromCheckbox) {
		// El foco en la lista permite usar Supr, F2, Intro y Ctrl+A después de hacer clic
		if (!fromCheckbox) {
			list.focus({ preventScroll: true });
		}
		if (POPUP && !MULTI) {
			S.selected = new Set([path]);
			S.anchor = path;
			syncSelection();
			return;
		}
		var visible = visibleItems().map(function (i) { return i.path; });
		if (e.shiftKey && S.anchor && visible.indexOf(S.anchor) >= 0) {
			var a = visible.indexOf(S.anchor);
			var b = visible.indexOf(path);
			if (!(e.ctrlKey || e.metaKey) && !fromCheckbox) {
				S.selected.clear();
			}
			visible.slice(Math.min(a, b), Math.max(a, b) + 1).forEach(function (p) { S.selected.add(p); });
		} else if (e.ctrlKey || e.metaKey || fromCheckbox) {
			if (S.selected.has(path)) {
				S.selected.delete(path);
			} else {
				S.selected.add(path);
			}
			S.anchor = path;
		} else {
			S.selected = new Set([path]);
			S.anchor = path;
		}
		syncSelection();
	}

	// --- Menús -----------------------------------------------------------------------------------

	var menuEl = null;
	function closeMenu() {
		if (menuEl) {
			menuEl.remove();
			menuEl = null;
		}
	}
	function openMenu(html, x, y, onAction) {
		closeMenu();
		menuEl = document.createElement('div');
		menuEl.className = 'fx-menu';
		menuEl.setAttribute('role', 'menu');
		menuEl.innerHTML = html;
		layer.appendChild(menuEl);
		var w = menuEl.offsetWidth;
		var hgt = menuEl.offsetHeight;
		menuEl.style.left = Math.max(8, Math.min(x, window.innerWidth - w - 8)) + 'px';
		menuEl.style.top = Math.max(8, Math.min(y, window.innerHeight - hgt - 8)) + 'px';
		menuEl.addEventListener('click', function (e) {
			var b = e.target.closest('[data-m]');
			if (!b || b.disabled) {
				return;
			}
			var act = b.getAttribute('data-m');
			closeMenu();
			onAction(act);
		});
		var first = menuEl.querySelector('button:not([disabled]), a');
		if (first) {
			first.focus();
		}
	}
	function menuButton(act, icon, label, opts) {
		opts = opts || {};
		return '<button type="button" role="menuitem" data-m="' + act + '"' + (opts.disabled ? ' disabled' : '') + (opts.danger ? ' class="danger"' : '') + '>' + icon + esc(label) + '</button>';
	}
	function itemMenuHtml(items) {
		var single = items.length === 1;
		var it = items[0];
		var ext = single ? (it.extension || '') : '';
		var changeable = items.every(canChange);
		var h = '';
		if (single && it.type === 'directory') {
			h += menuButton('open', ICON.folder, t('open'));
		}
		h += menuButton('download', ICON.download, single && it.type !== 'directory' ? t('download') : t('downloadZip'));
		if (single && EXPORTABLE.indexOf(ext) >= 0) {
			h += '<a role="menuitem" href="' + esc(CFG.exportUrl + '?path=' + encodeURIComponent(it.path)) + '">' + ICON.db + esc(t('exportToDatabase')) + '</a>';
		}
		if (single && CFG.transformUrl && TRANSFORMABLE.indexOf(ext) >= 0) {
			h += '<a role="menuitem" href="' + esc(CFG.transformUrl + '?path=' + encodeURIComponent(it.path)) + '">' + ICON.db + esc(t('transformToDatabase')) + '</a>';
		}
		if (single && ext === 'zip') {
			h += menuButton('unzip', ICON.unzip, t('unzipHere'), { disabled: !S.canWrite });
		}
		h += '<hr>';
		if (single) {
			h += menuButton('rename', ICON.rename, t('rename'), { disabled: !changeable });
		}
		h += menuButton('move', ICON.move, t('moveTo'), { disabled: !changeable });
		h += menuButton('copy', ICON.copy, t('copyTo'));
		h += '<hr>' + menuButton('trash-selected', ICON.trash, t('toTrash'), { disabled: !changeable, danger: true });
		var inUse = items.filter(function (i) { return i.in_use_by; });
		if (inUse.length) {
			h += '<div class="hint">' + esc(t('inUseHint', { name: inUse[0].in_use_by })) + '</div>';
		} else if (!changeable) {
			h += '<div class="hint">' + esc(t('notAllowed')) + '</div>';
		}
		return h;
	}
	function openItemMenu(x, y) {
		var items = selectedItems();
		if (!items.length) {
			return;
		}
		openMenu(itemMenuHtml(items), x, y, runAction);
	}

	document.addEventListener('mousedown', function (e) {
		if (menuEl && !menuEl.contains(e.target) && !e.target.closest('[data-act="row-menu"],[data-act="upload-menu"],[data-act="page-menu"]')) {
			closeMenu();
		}
	});
	window.addEventListener('resize', closeMenu);
	document.getElementById('fx-list').addEventListener('scroll', closeMenu);

	// --- Acciones --------------------------------------------------------------------------------

	function runAction(act, source) {
		var items = selectedItems();
		switch (act) {
			case 'open':
				if (items[0]) {
					navigate(items[0].path);
				}
				break;
			case 'download':
				downloadItems(items);
				break;
			case 'rename':
				if (items[0]) {
					renameItem(items[0]);
				}
				break;
			case 'move':
				pickAndTransfer(items, 'move');
				break;
			case 'copy':
				pickAndTransfer(items, 'copy');
				break;
			case 'trash-selected':
				trashItems(items);
				break;
			case 'unzip':
				if (items[0]) {
					unzipItem(items[0]);
				}
				break;
			case 'upload-files':
				document.getElementById('fx-input-files').click();
				break;
			case 'upload-folder':
				document.getElementById('fx-input-folder').click();
				break;
			case 'exports':
				location.href = CFG.exportsUrl;
				break;
			case 'classic':
				location.href = CFG.browserUrl + '?' + query({ popup: POPUP ? 1 : null, ui: 'classic', path: S.path || null });
				break;
			case 'show-trash':
				showTrash();
				break;
		}
	}

	function downloadItems(items) {
		if (!items.length) {
			return;
		}
		if (items.length === 1 && items[0].type !== 'directory') {
			location.href = CFG.downloadUrl + encodePath(items[0].path);
			return;
		}
		var paths = items.map(function (i) { return i.path; });
		api('GET', 'download/', { query: query({ paths: paths, check: 1 }) }).then(function (r) {
			if (!r.ok) {
				toast(r.error, { error: true });
				return;
			}
			location.href = CFG.api + 'download/?' + query({ paths: paths });
		});
	}

	document.getElementById('fx-head').addEventListener('click', function (e) {
		var go = e.target.closest('[data-go]');
		if (go) {
			navigate(go.getAttribute('data-go'));
			return;
		}
		var b = e.target.closest('[data-act]');
		if (!b || b.disabled) {
			return;
		}
		var act = b.getAttribute('data-act');
		var r = b.getBoundingClientRect();
		if (act === 'upload-menu') {
			openMenu(menuButton('upload-files', ICON.upload, t('uploadFiles')) + menuButton('upload-folder', ICON.folder, t('uploadFolder')), r.left, r.bottom + 4, runAction);
		} else if (act === 'page-menu') {
			openMenu(menuButton('show-trash', ICON.trash, t('trash')) + menuButton('exports', ICON.history, t('exportHistory')) + '<hr>' + menuButton('classic', ICON.classic, t('classicView')), r.right - 230, r.bottom + 4, runAction);
		} else if (act === 'toggle-tree') {
			if (narrow.matches) {
				fx.classList.toggle('tree-overlay');
			} else {
				fx.classList.toggle('no-tree');
				if (!POPUP) {
					savePref('tree', !fx.classList.contains('no-tree'));
				}
			}
		} else if (act === 'toggle-details') {
			fx.classList.toggle('no-details');
			savePref('details', !fx.classList.contains('no-details'));
			renderHead();
		} else if (act === 'new-folder') {
			newFolder();
		} else if (act === 'clear') {
			S.selected.clear();
			syncSelection();
		} else if (act === 'files') {
			navigate(S.path);
		} else {
			runAction(act);
		}
	});
	document.getElementById('fx-head').addEventListener('input', function (e) {
		if (e.target.id === 'fx-filter') {
			S.filter = e.target.value;
			renderList();
		}
	});
	document.getElementById('fx-details').addEventListener('click', function (e) {
		var b = e.target.closest('[data-act]');
		if (b && !b.disabled) {
			runAction(b.getAttribute('data-act'));
		}
	});

	var list = document.getElementById('fx-list');
	// El árbol superpuesto (ventanas estrechas) se cierra al volver a la lista
	list.addEventListener('mousedown', function () {
		fx.classList.remove('tree-overlay');
	});
	list.addEventListener('click', function (e) {
		if (S.view === 'trash') {
			return handleTrashClick(e);
		}
		var sortBtn = e.target.closest('[data-sort]');
		if (sortBtn) {
			var key = sortBtn.getAttribute('data-sort');
			S.sort = { key: key, dir: S.sort.key === key ? -S.sort.dir : 1 };
			renderList();
			return;
		}
		if (e.target.closest('[data-role="check-all"]')) {
			var vis = visibleItems();
			var all = vis.every(function (i) { return S.selected.has(i.path); });
			S.selected = all ? new Set() : new Set(vis.map(function (i) { return i.path; }));
			syncSelection();
			return;
		}
		var row = e.target.closest('tr[data-path]');
		if (!row) {
			if (!e.target.closest('.fx-table thead') && S.selected.size) {
				S.selected.clear();
				syncSelection();
			}
			return;
		}
		var path = row.getAttribute('data-path');
		if (e.target.closest('[data-role="check"]')) {
			clickSelect(path, e, true);
			return;
		}
		var act = e.target.closest('[data-act]');
		if (act) {
			var a = act.getAttribute('data-act');
			if (!S.selected.has(path) || a !== 'row-menu') {
				S.selected = new Set([path]);
				S.anchor = path;
				syncSelection();
			}
			if (a === 'row-menu') {
				var r = act.getBoundingClientRect();
				openItemMenu(r.right - 230, r.bottom + 4);
			} else if (a === 'download-one') {
				downloadItems([byPath(path)]);
			} else if (a === 'details-one') {
				fx.classList.remove('no-details');
				savePref('details', true);
				renderHead();
			}
			return;
		}
		// En el selector, un clic en el nombre de una carpeta la selecciona (doble clic la abre)
		if (e.target.closest('[data-role="open"]') && !POPUP && !(e.ctrlKey || e.metaKey || e.shiftKey)) {
			navigate(path);
			return;
		}
		clickSelect(path, e, false);
	});
	list.addEventListener('dblclick', function (e) {
		var row = e.target.closest('tr[data-path]');
		if (!row || e.target.closest('[data-act],[data-role="check"]')) {
			return;
		}
		var it = byPath(row.getAttribute('data-path'));
		if (!it) {
			return;
		}
		if (it.type === 'directory') {
			navigate(it.path);
		} else if (POPUP) {
			pick([it]);
		} else {
			downloadItems([it]);
		}
	});
	list.addEventListener('contextmenu', function (e) {
		var row = e.target.closest('tr[data-path]');
		if (!row || S.view !== 'files' || POPUP) {
			return;
		}
		e.preventDefault();
		var path = row.getAttribute('data-path');
		if (!S.selected.has(path)) {
			S.selected = new Set([path]);
			S.anchor = path;
			syncSelection();
		}
		openItemMenu(e.clientX, e.clientY);
	});

	document.addEventListener('keydown', function (e) {
		if (e.key === 'Escape') {
			if (menuEl) {
				closeMenu();
				return;
			}
			if (document.querySelector('.fx-scrim')) {
				return;
			}
			fx.classList.remove('tree-overlay');
			if (S.selected.size) {
				S.selected.clear();
				syncSelection();
			}
			return;
		}
		var tag = (e.target.tagName || '').toLowerCase();
		if (tag === 'input' || tag === 'textarea' || tag === 'select' || document.querySelector('.fx-scrim') || S.view !== 'files') {
			return;
		}
		var items = selectedItems();
		if (POPUP) {
			if (e.key === 'Enter' && items.length && !e.target.closest('button,a')) {
				e.preventDefault();
				if (items.length === 1 && items[0].type === 'directory') {
					navigate(items[0].path);
				} else {
					pick(items);
				}
			} else if (MULTI && (e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'a' && fx.contains(e.target)) {
				e.preventDefault();
				S.selected = new Set(visibleItems().filter(pickable).map(function (i) { return i.path; }));
				syncSelection();
			}
			return;
		}
		if ((e.key === 'Delete' || e.key === 'Backspace' && e.metaKey) && items.length) {
			e.preventDefault();
			if (items.every(canChange)) {
				trashItems(items);
			}
		} else if (e.key === 'F2' && items.length === 1 && canChange(items[0])) {
			e.preventDefault();
			renameItem(items[0]);
		} else if (e.key === 'Enter' && items.length === 1 && fx.contains(document.activeElement || document.body) && !e.target.closest('button,a')) {
			e.preventDefault();
			if (items[0].type === 'directory') {
				navigate(items[0].path);
			} else {
				downloadItems(items);
			}
		} else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'a' && fx.contains(e.target)) {
			e.preventDefault();
			S.selected = new Set(visibleItems().map(function (i) { return i.path; }));
			syncSelection();
		}
	});

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

	function promptName(opts) {
		var value = null;
		var body = '<label class="field">' + esc(opts.label) + '<input type="text" id="fx-dlg-input" autocomplete="off" spellcheck="false" value="' + esc(opts.value || '') + '"></label>' +
			(opts.hint ? '<div class="hint">' + esc(opts.hint) + '</div>' : '');
		return dialog({
			icon: opts.icon,
			title: opts.title,
			body: body,
			buttons: [{ label: t('cancel'), value: null }, { label: opts.okLabel, value: 'ok', cls: 'primary', primary: true }],
			onOpen: function (root) {
				var input = root.querySelector('input');
				if (opts.selectEnd != null) {
					setTimeout(function () { input.setSelectionRange(0, opts.selectEnd); }, 0);
				}
			},
			submit: function (v, root) {
				// La validación del nombre la hace el servidor (mismas reglas que la subida)
				var name = root.querySelector('input').value.trim();
				return opts.submit(name).then(function (res) {
					if (res && res.error) {
						return res.error;
					}
					value = res;
					return null;
				});
			}
		}).then(function () { return value; });
	}

	function newFolder() {
		var parent = S.path;
		promptName({
			icon: ICON.plus,
			title: t('newFolder'),
			label: t('folderName'),
			hint: t('nameHint'),
			okLabel: t('create'),
			submit: function (name) {
				return api('POST', 'mkdir/', { json: { path: parent, name: name } }).then(function (r) {
					return r.ok ? r.item : { error: r.error };
				});
			}
		}).then(function (item) {
			if (!item) {
				return;
			}
			toast(t('folderCreated', { name: item.name }));
			refreshTree();
			loadFolder(true).then(function () {
				S.selected = new Set([item.path]);
				S.anchor = item.path;
				syncSelection();
			});
		});
	}

	function renameItem(item) {
		var dot = item.type === 'directory' ? -1 : item.name.lastIndexOf('.');
		var isShp = item.extension === 'shp';
		promptName({
			icon: ICON.rename,
			title: t('rename'),
			label: t('newName'),
			value: item.name,
			selectEnd: dot > 0 ? dot : item.name.length,
			hint: t('nameHint') + (isShp ? ' ' + t('renameShpHint') : ''),
			okLabel: t('rename'),
			submit: function (name) {
				if (name === item.name) {
					return Promise.resolve(item);
				}
				return api('POST', 'rename/', { json: { path: item.path, name: name } }).then(function (r) {
					return r.ok ? r.item : { error: r.error };
				});
			}
		}).then(function (res) {
			if (!res || res.path === item.path) {
				return;
			}
			toast(t('renamed', { name: res.name }));
			if (item.type === 'directory') {
				refreshTree();
			}
			loadFolder(true).then(function () {
				S.selected = new Set([res.path]);
				S.anchor = res.path;
				syncSelection();
			});
		});
	}

	// --- Mover y copiar --------------------------------------------------------------------------

	function pickFolder(items, mode) {
		var openSet = new Set(['']);
		var current = S.path;
		var parts = current ? current.split('/') : [];
		var acc = '';
		parts.forEach(function (p) {
			acc = acc ? acc + '/' + p : p;
			openSet.add(acc);
		});
		openSet.add(current);
		var dirs = items.filter(function (i) { return i.type === 'directory'; }).map(function (i) { return i.path; });
		function isDisabled(p) {
			return dirs.some(function (d) { return isInside(p, d); });
		}
		var chosen = current;
		var root;
		function render() {
			var tree = root.querySelector('.fx-picker');
			var s = tree.scrollTop;
			tree.innerHTML = treeHtml(openSet, chosen, { isDisabled: isDisabled });
			tree.scrollTop = s;
			root.querySelector('.fx-picker-dest').innerHTML = esc(t('destination', { path: '' })) + '<b>' + esc(displayPath(chosen)) + '</b>';
			var ok = root.querySelector('footer .primary');
			if (ok) {
				ok.disabled = isDisabled(chosen) || (mode === 'move' && items.every(function (i) { return parentOf(i.path) === chosen; }));
			}
		}
		var n = items.length;
		return dialog({
			icon: mode === 'move' ? ICON.move : ICON.copy,
			title: n === 1 ? t(mode === 'move' ? 'moveOne' : 'copyOne', { name: items[0].name }) : t(mode === 'move' ? 'moveTitle' : 'copyTitle', { n: n }),
			sub: t('chooseDestination'),
			wide: true,
			body: '<div class="fx-picker" tabindex="-1"></div><div class="fx-picker-dest"></div>',
			buttons: [{ label: t('cancel'), value: null }, { label: mode === 'move' ? t('move') : t('copy'), value: 'ok', cls: 'primary', primary: true }],
			onOpen: function (r) {
				root = r;
				var p = Promise.resolve();
				Array.from(openSet).sort(function (a, b) { return a.split('/').length - b.split('/').length; }).forEach(function (d) {
					p = p.then(function () { return loadChildren(d); });
				});
				render();
				p.then(render);
				root.querySelector('.fx-picker').addEventListener('click', function (e) {
					handleTreeClick(e, openSet, function (path) {
						chosen = path;
						openSet.add(path);
						render();
						loadChildren(path).then(render);
					}, render);
				});
			}
		}).then(function (v) { return v ? chosen : null; });
	}

	function pickAndTransfer(items, mode) {
		if (!items.length) {
			return;
		}
		pickFolder(items, mode).then(function (dest) {
			if (dest != null) {
				transfer(items.map(function (i) { return i.path; }), dest, mode);
			}
		});
	}

	function transfer(paths, dest, mode, policy) {
		var endpoint = mode === 'move' ? 'move/' : 'copy/';
		return api('POST', endpoint, { json: { paths: paths, destination: dest, on_conflict: policy || (mode === 'move' ? 'error' : 'rename') } }).then(function (r) {
			if (!r.results) {
				toast(r.error, { error: true });
				return;
			}
			var done = r.results.filter(function (x) { return x.ok && x.item && x.item.path !== x.path; });
			var conflicts = r.results.filter(function (x) { return !x.ok && x.conflict; });
			var fails = r.results.filter(function (x) { return !x.ok && !x.conflict; });
			reportFailures(fails);
			var next = Promise.resolve([]);
			if (conflicts.length) {
				next = dialog({
					icon: ICON.warn,
					iconClass: 'w',
					title: t('moveConflictTitle'),
					sub: t('moveConflictSub', { names: conflicts.map(function (c) { return baseName(c.path); }).join(', '), path: displayPath(dest) }),
					buttons: [{ label: t('skip'), value: null }, { label: t('moveConflictKeep'), value: 'rename', cls: 'primary', primary: true }]
				}).then(function (v) {
					if (!v) {
						return [];
					}
					return api('POST', endpoint, { json: { paths: conflicts.map(function (c) { return c.path; }), destination: dest, on_conflict: 'rename' } }).then(function (r2) {
						reportFailures(failuresOf(r2));
						return (r2.results || []).filter(function (x) { return x.ok; });
					});
				});
			}
			return next.then(function (more) {
				done = done.concat(more);
				if (!done.length) {
					return;
				}
				var destName = baseName(dest);
				if (mode === 'move') {
					var moved = done.map(function (x) { return { from: x.path, to: x.item.path }; });
					toast(t('movedN', { n: done.length, name: destName }), { undo: function () { undoMove(moved); } });
				} else {
					toast(t('copiedN', { n: done.length, name: destName }));
				}
				if (done.some(function (x) { return x.item.type === 'directory'; })) {
					refreshTree();
				}
				return loadFolder(true);
			});
		});
	}

	function undoMove(moved) {
		var groups = {};
		moved.forEach(function (m) {
			var back = parentOf(m.from);
			(groups[back] = groups[back] || []).push(m.to);
		});
		var p = Promise.resolve();
		Object.keys(groups).forEach(function (dest) {
			p = p.then(function () {
				return api('POST', 'move/', { json: { paths: groups[dest], destination: dest } }).then(function (r) {
					reportFailures(failuresOf(r));
				});
			});
		});
		p.then(function () {
			toast(t('undone'));
			refreshTree();
			loadFolder(true);
		});
	}

	// --- Papelera --------------------------------------------------------------------------------

	function trashItems(items) {
		items = items.filter(canChange);
		if (!items.length) {
			return;
		}
		var rows = items.map(function (it) {
			var r = '<li><span>' + esc(it.name) + '</span><small>' + esc(it.type === 'directory' ? t('folderWithItems') : fmtSize(it.size)) + '</small></li>';
			(it.companions || []).forEach(function (c) {
				r += '<li class="companion"><span>' + esc(c) + '</span><small>' + esc(t('relatedFile')) + '</small></li>';
			});
			return r;
		}).join('');
		dialog({
			icon: ICON.trash,
			iconClass: 'd',
			title: items.length === 1 ? t('trashTitleOne', { name: items[0].name }) : t('trashTitle', { n: items.length }),
			sub: t('trashSub', { days: CFG.trashDays }),
			body: '<ul class="items">' + rows + '</ul>',
			buttons: [{ label: t('cancel'), value: null }, { label: t('sendToTrash'), value: 'ok', cls: 'danger-solid', primary: true }]
		}).then(function (v) {
			if (!v) {
				return;
			}
			api('POST', 'delete/', { json: { paths: items.map(function (i) { return i.path; }) } }).then(function (r) {
				if (!r.results) {
					toast(r.error, { error: true });
					return;
				}
				var ok = r.results.filter(function (x) { return x.ok; });
				reportFailures(failuresOf(r));
				if (ok.length) {
					var ids = ok.map(function (x) { return x.trash.id; });
					var msg = ok.length === 1 ? t('trashedOne', { name: baseName(ok[0].path) }) : t('trashedN', { n: ok.length });
					toast(msg, { undo: function () { restoreFromTrash(ids, true); } });
				}
				if (items.some(function (i) { return i.type === 'directory'; })) {
					refreshTree();
				}
				S.selected.clear();
				loadFolder(true);
			});
		});
	}

	function restoreFromTrash(ids, isUndo) {
		return api('POST', 'trash/restore/', { json: { ids: ids } }).then(function (r) {
			if (!r.results) {
				toast(r.error, { error: true });
				return;
			}
			reportFailures(failuresOf(r));
			var ok = r.results.filter(function (x) { return x.ok; });
			if (ok.length) {
				toast(isUndo ? t('undone') : t('restoredN', { n: ok.length }));
			}
			refreshTree();
			if (S.view === 'trash') {
				loadTrash();
			} else {
				loadFolder(true);
			}
		});
	}

	function showTrash() {
		closeMenu();
		S.view = 'trash';
		S.selected.clear();
		fx.classList.remove('tree-overlay');
		renderAll();
		loadTrash();
	}

	function loadTrash() {
		S.trashLoading = true;
		renderList();
		return api('GET', 'trash/').then(function (r) {
			S.trashLoading = false;
			if (!r.ok) {
				S.trash = [];
				toast(r.error, { error: true });
			} else {
				S.trash = r.items || [];
			}
			if (S.view === 'trash') {
				renderList();
				renderStatus();
			}
		});
	}

	function daysLeft(item) {
		var ms = new Date(item.expires_at) - new Date();
		return Math.max(0, Math.ceil(ms / 86400000));
	}

	function trashHtml() {
		var h = '<div class="fx-trashnote"><span>' + esc(t('trashNote', { days: CFG.trashDays })) + '</span>' +
			(S.trash.length ? '<button type="button" class="fx-btn danger" data-trash="empty">' + ICON.trash + esc(t('emptyTrash')) + '</button>' : '') + '</div>';
		if (S.trashLoading && !S.trash.length) {
			return h + '<div class="fx-loading">' + esc(t('loading')) + '</div>';
		}
		if (!S.trash.length) {
			return h + '<div class="fx-empty">' + ICON.trash.replace('class="i"', 'class="i" style="width:40px;height:40px"') + '<strong>' + esc(t('trashEmpty')) + '</strong></div>';
		}
		h += '<table class="fx-table"><thead><tr><th>' + esc(t('name')) + '</th><th>' + esc(t('originalLocation')) + '</th><th>' + esc(t('deleted')) + '</th><th class="num">' + esc(t('size')) + '</th><th class="num"><span class="sr-only">' + esc(t('actions')) + '</span></th></tr></thead><tbody>';
		S.trash.forEach(function (it) {
			var left = daysLeft(it);
			var extra = (it.names || []).length - 1;
			h += '<tr><td><div class="fx-name">' + typeIcon(it) + '<span class="lbl">' + esc(it.name) + '</span>' +
				(extra > 0 ? '<span class="fx-badge grp" title="' + esc(it.names.slice(1).join(', ')) + '">' + esc(t('related', { n: extra })) + '</span>' : '') + '</div></td>' +
				'<td class="muted">' + esc(displayPath(it.original_dir)) + '</td>' +
				'<td class="muted">' + esc(fmtDate(it.deleted_at)) + ' · ' + esc(t('by', { user: it.deleted_by })) +
				'<br><span class="fx-left' + (left <= 3 ? ' soon' : '') + '">' + esc(left <= 0 ? t('lastDay') : t('daysLeft', { n: left })) + '</span></td>' +
				'<td class="num muted">' + esc(fmtSize(it.size)) + '</td>' +
				'<td><div class="fx-rowacts" style="opacity:1"><button type="button" class="fx-btn" data-trash="restore" data-id="' + esc(it.id) + '">' + ICON.restore + esc(t('restore')) + '</button>' +
				'<button type="button" class="fx-ib" data-trash="forever" data-id="' + esc(it.id) + '" title="' + esc(t('deleteForever')) + '" aria-label="' + esc(t('deleteForever')) + '">' + ICON.trash + '</button></div></td></tr>';
		});
		return h + '</tbody></table>';
	}

	function handleTrashClick(e) {
		var b = e.target.closest('[data-trash]');
		if (!b) {
			return;
		}
		var kind = b.getAttribute('data-trash');
		var id = b.getAttribute('data-id');
		if (kind === 'restore') {
			restoreFromTrash([id], false);
		} else if (kind === 'forever' || kind === 'empty') {
			var empty = kind === 'empty';
			dialog({
				icon: ICON.trash,
				iconClass: 'd',
				title: empty ? t('emptyTrashTitle') : t('deleteForeverTitle', { n: 1 }),
				sub: t('cannotUndo'),
				buttons: [{ label: t('cancel'), value: null }, { label: empty ? t('emptyTrash') : t('deleteForever'), value: 'ok', cls: 'danger-solid', primary: true }]
			}).then(function (v) {
				if (!v) {
					return;
				}
				var call = empty ? api('POST', 'trash/empty/', { json: {} }) : api('POST', 'trash/delete/', { json: { ids: [id] } });
				call.then(function (r) {
					if (r.results) {
						reportFailures(failuresOf(r));
					} else if (!r.ok) {
						toast(r.error, { error: true });
					}
					var n = empty ? (r.deleted || 0) : (r.results || []).filter(function (x) { return x.ok; }).length;
					if (n) {
						toast(t('deletedForeverN', { n: n }));
					}
					loadTrash();
				});
			});
		}
	}

	// --- Arrastrar para mover (filas sobre carpetas del árbol, de la lista o de las migas) -------

	var dropTargetEl = null;
	function setDropTarget(el) {
		if (dropTargetEl === el) {
			return;
		}
		if (dropTargetEl) {
			dropTargetEl.classList.remove('drop');
		}
		dropTargetEl = el;
		if (el) {
			el.classList.add('drop');
		}
	}
	function targetPathOf(el) {
		var node = el && el.closest('[data-tree-path], [data-drop-path]');
		if (!node || !fx.contains(node)) {
			return null;
		}
		return node.hasAttribute('data-tree-path') ? node.getAttribute('data-tree-path') : node.getAttribute('data-drop-path');
	}
	function validMoveTarget(path) {
		if (path == null || !S.drag) {
			return false;
		}
		return !S.drag.paths.some(function (p) { return isInside(path, p) || parentOf(p) === path; });
	}

	fx.addEventListener('dragstart', function (e) {
		var row = e.target.closest && e.target.closest('tr[data-path]');
		if (!row) {
			return;
		}
		if (POPUP) {
			e.preventDefault();
			return;
		}
		var path = row.getAttribute('data-path');
		if (!S.selected.has(path)) {
			S.selected = new Set([path]);
			S.anchor = path;
			syncSelection();
		}
		var items = selectedItems();
		if (!items.every(canChange)) {
			e.preventDefault();
			return;
		}
		S.drag = { paths: items.map(function (i) { return i.path; }) };
		e.dataTransfer.effectAllowed = 'move';
		e.dataTransfer.setData('application/x-gvsigol-fm', S.drag.paths.join('\n'));
	});
	fx.addEventListener('dragend', function () {
		S.drag = null;
		setDropTarget(null);
	});

	// --- Subir: arrastrar ficheros desde el escritorio ------------------------------------------

	var dropOverlay = null;
	var dropHideTimer = null;
	function isFileDrag(e) {
		return !S.drag && e.dataTransfer && Array.prototype.indexOf.call(e.dataTransfer.types || [], 'Files') >= 0;
	}
	function showDropOverlay(targetPath) {
		var allowed = S.view === 'files' && (targetPath != null ? true : S.canWrite);
		var name = baseName(targetPath != null ? targetPath : S.path);
		if (!dropOverlay) {
			dropOverlay = document.createElement('div');
			dropOverlay.className = 'fx-drop';
			fx.appendChild(dropOverlay);
		}
		dropOverlay.classList.toggle('no', !allowed);
		dropOverlay.innerHTML = '<div><strong>' + esc(allowed ? t('dropHere', { name: name }) : t('cannotUploadHere')) + '</strong>' + (allowed ? '<span>' + esc(t('dropHint')) + '</span>' : '') + '</div>';
		clearTimeout(dropHideTimer);
		dropHideTimer = setTimeout(hideDropOverlay, 200);
	}
	function hideDropOverlay() {
		if (dropOverlay) {
			dropOverlay.remove();
			dropOverlay = null;
		}
	}

	fx.addEventListener('dragover', function (e) {
		var target = targetPathOf(e.target);
		if (S.drag) {
			if (validMoveTarget(target)) {
				e.preventDefault();
				e.dataTransfer.dropEffect = 'move';
				setDropTarget(e.target.closest('[data-tree-path] , [data-drop-path]'));
			} else {
				setDropTarget(null);
			}
			return;
		}
		if (isFileDrag(e)) {
			e.preventDefault();
			e.dataTransfer.dropEffect = S.view === 'files' ? 'copy' : 'none';
			setDropTarget(target != null ? e.target.closest('[data-tree-path], [data-drop-path]') : null);
			showDropOverlay(target);
		}
	});
	fx.addEventListener('drop', function (e) {
		var target = targetPathOf(e.target);
		setDropTarget(null);
		hideDropOverlay();
		if (S.drag) {
			e.preventDefault();
			var paths = S.drag.paths;
			S.drag = null;
			if (validMoveTarget(target) || (target != null && paths.every(function (p) { return !isInside(target, p) && parentOf(p) !== target; }))) {
				transfer(paths, target, 'move');
			}
			return;
		}
		if (!isFileDrag(e) || S.view !== 'files') {
			return;
		}
		e.preventDefault();
		var dest = target != null ? target : S.path;
		if (target == null && !S.canWrite) {
			toast(t('cannotUploadHere'), { error: true });
			return;
		}
		filesFromDrop(e.dataTransfer).then(function (entries) {
			if (entries.length) {
				addUploads(entries, dest);
			}
		});
	});

	/** Ficheros soltados, incluidas carpetas completas (rel = ruta relativa con subcarpetas). */
	function filesFromDrop(dt) {
		var entries = [];
		if (dt.items) {
			for (var i = 0; i < dt.items.length; i++) {
				var entry = dt.items[i].webkitGetAsEntry ? dt.items[i].webkitGetAsEntry() : null;
				if (entry) {
					entries.push(entry);
				}
			}
		}
		if (!entries.length) {
			return Promise.resolve(Array.prototype.map.call(dt.files || [], function (f) { return { file: f, rel: f.name }; }));
		}
		var out = [];
		function walk(entry, prefix) {
			if (entry.isFile) {
				return new Promise(function (res) {
					entry.file(function (f) {
						out.push({ file: f, rel: prefix + f.name });
						res();
					}, function () { res(); });
				});
			}
			if (entry.isDirectory) {
				var reader = entry.createReader();
				var readAll = function () {
					return new Promise(function (res) {
						reader.readEntries(function (batch) { res(batch); }, function () { res([]); });
					}).then(function (batch) {
						if (!batch.length) {
							return;
						}
						var p = Promise.resolve();
						batch.forEach(function (b) {
							p = p.then(function () { return walk(b, prefix + entry.name + '/'); });
						});
						return p.then(readAll);
					});
				};
				return readAll();
			}
			return Promise.resolve();
		}
		var p = Promise.resolve();
		entries.forEach(function (en) {
			p = p.then(function () { return walk(en, ''); });
		});
		return p.then(function () { return out; });
	}

	document.getElementById('fx-input-files').addEventListener('change', function (e) {
		var files = Array.prototype.map.call(e.target.files, function (f) { return { file: f, rel: f.name }; });
		e.target.value = '';
		if (files.length) {
			addUploads(files, S.path);
		}
	});
	document.getElementById('fx-input-folder').addEventListener('change', function (e) {
		var files = Array.prototype.map.call(e.target.files, function (f) { return { file: f, rel: f.webkitRelativePath || f.name }; });
		e.target.value = '';
		if (files.length) {
			addUploads(files, S.path);
		}
	});

	// --- Subidas por trozos y tareas -------------------------------------------------------------

	var U = { items: [], running: 0, max: 2, seq: 0, collapsed: false };
	var panel = null;
	var renderQueued = false;
	var refreshTimer = null;
	var conflictChain = Promise.resolve();

	function activeUploads() {
		return U.items.filter(function (i) { return i.status === 'waiting' || i.status === 'running'; });
	}
	function addUploads(entries, dest) {
		var batch = { policy: null, cancelled: false, size: entries.length };
		entries.forEach(function (en) {
			U.items.push({ key: ++U.seq, kind: 'upload', file: en.file, name: en.rel, dest: dest, size: en.file.size, received: 0, status: 'waiting', batch: batch, tries: 0 });
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
						scheduleRefresh(it.dest);
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
				if (!r || it.status === 'cancelled') {
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

	function scheduleRefresh(dest) {
		if (S.view !== 'files') {
			return;
		}
		if (dest === S.path || isInside(dest, S.path) || dest.indexOf(S.path) === 0) {
			clearTimeout(refreshTimer);
			refreshTimer = setTimeout(function () {
				loadFolder(true);
				refreshTree();
			}, 500);
		}
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
				scheduleRefresh(task.dest);
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

	function renderUploads() {
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
			layer.appendChild(panel);
			panel.addEventListener('click', function (e) {
				if (e.target.closest('[data-panel="collapse"]')) {
					U.collapsed = !U.collapsed;
					renderUploads();
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
		panel.innerHTML = '<header><span>' + esc(title) + '</span><span>' +
			'<button type="button" data-panel="collapse" aria-label="' + esc(t('uploadsTitle')) + '">' + (U.collapsed ? ICON.chevDown.replace('<path', '<path transform="rotate(180 12 12)"') : ICON.minus) + '</button>' +
			(active ? '' : '<button type="button" data-panel="close" aria-label="' + esc(t('close')) + '">' + ICON.close + '</button>') +
			'</span></header>' + (U.collapsed ? '' : '<div class="list">' + U.items.map(uploadRow).join('') + '</div>');
	}

	window.addEventListener('beforeunload', function (e) {
		if (activeUploads().length) {
			e.preventDefault();
			e.returnValue = t('leaveWarning');
			return e.returnValue;
		}
	});

	// --- Selector: elegir y devolver ------------------------------------------------------------

	function pickable(item) {
		if (!item) {
			return false;
		}
		if (EXTS.length) {
			return item.type !== 'directory' && EXTS.indexOf(item.extension) >= 0;
		}
		// Como el clásico: se puede elegir un fichero o una carpeta (p. ej. para un ImageMosaic)
		return true;
	}

	function pick(items) {
		items = (items || []).filter(pickable);
		if (!items.length) {
			return;
		}
		if (!MULTI) {
			items = items.slice(0, 1);
		}
		var paths = items.map(function (i) { return i.path; });
		var opener = null;
		try {
			opener = window.opener;
		} catch (e) {
			opener = null;
		}
		if (!opener || opener.closed || typeof opener.filemanagerCallback !== 'function') {
			toast(t('pickNoOpener'), { error: true });
			return;
		}
		try {
			if (MULTI && typeof opener.filemanagerMultipleCallback === 'function') {
				opener.filemanagerMultipleCallback(paths, window.name);
			} else {
				// Una llamada por fichero; se vuelve a leer porque la pantalla puede cambiarla
				paths.forEach(function (p) {
					if (typeof opener.filemanagerCallback === 'function') {
						opener.filemanagerCallback(p, window.name);
					}
				});
			}
		} catch (e) {
			// Un fallo en la pantalla que abrió el selector no debe dejarlo abierto sin más
			if (window.console) {
				console.error(e);
			}
		}
		window.close();
	}

	function renderPick() {
		var el = document.getElementById('fx-pick');
		if (!el) {
			return;
		}
		var items = selectedItems().filter(pickable);
		if (!MULTI && selectedItems().length !== 1) {
			items = [];
		}
		var ok = S.view === 'files' && items.length > 0;
		var label;
		if (!ok) {
			label = esc(EXTS.length ? t('pickNoneFile') : t('pickNone'));
		} else if (items.length === 1) {
			label = esc(t('pickChosen', { path: '' })) + '<b>' + esc(displayPath(items[0].path)) + '</b>';
		} else {
			label = '<b>' + esc(t('pickChosenN', { n: items.length })) + '</b>';
		}
		el.innerHTML = '<span class="chosen">' + label + '</span>' +
			'<button type="button" class="fx-btn" data-pick="cancel">' + esc(t('cancel')) + '</button>' +
			'<button type="button" class="fx-btn primary" data-pick="ok"' + (ok ? '' : ' disabled') + '>' + esc(t('pickSelect')) + '</button>';
	}

	/**
	 * Las pantallas que abren el selector piden ventanas pequeñas (640×480, 760×520). Sin tocarlas,
	 * el selector agranda su propia ventana (solo crece, sin pasar de la pantalla) y recuerda el
	 * tamaño si el usuario la cambia. resizeTo solo funciona en ventanas abiertas con window.open,
	 * que es como se abre el selector; si el navegador no lo permite, no pasa nada.
	 */
	function sizePopupWindow() {
		var saved = null;
		try {
			saved = JSON.parse(localStorage.getItem('fx.popupSize') || 'null');
		} catch (e) {
			saved = null;
		}
		var availW = (screen.availWidth || 1280) - 40;
		var availH = (screen.availHeight || 800) - 40;
		var w = Math.min(saved && saved.w ? saved.w : 1000, availW);
		var h = Math.min(saved && saved.h ? saved.h : 700, availH);
		if (window.outerWidth >= w && window.outerHeight >= h) {
			return;
		}
		w = Math.max(w, window.outerWidth);
		h = Math.max(h, window.outerHeight);
		try {
			window.resizeTo(w, h);
			window.moveTo(Math.max(0, Math.round(((screen.availWidth || w) - w) / 2)), Math.max(0, Math.round(((screen.availHeight || h) - h) / 2)));
		} catch (e) { /* el navegador no deja cambiar el tamaño */ }
	}

	if (POPUP) {
		if (window.opener) {
			sizePopupWindow();
			var sizeTimer = null;
			window.addEventListener('resize', function () {
				clearTimeout(sizeTimer);
				sizeTimer = setTimeout(function () {
					try {
						localStorage.setItem('fx.popupSize', JSON.stringify({ w: window.outerWidth, h: window.outerHeight }));
					} catch (e) { /* sin almacenamiento: no se recuerda */ }
				}, 500);
			});
		}
		document.getElementById('fx-pick').addEventListener('click', function (e) {
			var b = e.target.closest('[data-pick]');
			if (!b || b.disabled) {
				return;
			}
			if (b.getAttribute('data-pick') === 'cancel') {
				window.close();
			} else {
				pick(selectedItems());
			}
		});
	}

	// --- Arranque --------------------------------------------------------------------------------

	history.replaceState({ fxPath: S.path }, '', urlFor(S.path));
	loadFolder(false);
	expandTo(S.path);
})();
