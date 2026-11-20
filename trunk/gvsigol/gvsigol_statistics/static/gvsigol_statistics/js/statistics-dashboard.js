/*
 * gvSIG Online — Panel de estadísticas.
 * Consume la API v1 de gvsigol_statistics (solo GET). Requiere jQuery,
 * Chart.js 2.8 y DataTables 1.10 (los carga base.html).
 *
 * Todo texto que procede de datos (títulos, nombres de usuario) se escapa con esc().
 */
(function () {
	'use strict';

	var root = document.getElementById('gol-stats');
	var configEl = document.getElementById('gol-stats-config');
	if (!root || !configEl) {
		return;
	}
	var config = JSON.parse(configEl.textContent);
	var T = config.i18n;
	var API = config.api;
	// Código de idioma de Django (p. ej. 'ca-es-valencia') a uno que acepte Intl
	var LANG = (function (code) {
		var candidates = [code, String(code || '').split('-')[0], 'es'];
		for (var i = 0; i < candidates.length; i++) {
			try {
				if (candidates[i]) {
					new Intl.NumberFormat(candidates[i]);
					return candidates[i];
				}
			} catch (e) {
				/* código no válido para Intl: se prueba el siguiente */
			}
		}
		return 'es';
	})(config.language);

	// Colores de datos (validados: ver statistics-dashboard.css)
	var SERIES_AUTH = '#2a78d6';
	var SERIES_ANON = '#eb6834';
	var HEAT_RAMP = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b'];
	var GRID_COLOR = 'rgba(63,77,90,0.10)';
	var AXIS_COLOR = '#5f7181';

	var numberFmt = new Intl.NumberFormat(LANG);
	var decimalFmt = new Intl.NumberFormat(LANG, { maximumFractionDigits: 1 });
	var dayFmt = new Intl.DateTimeFormat(LANG, { day: 'numeric', month: 'short' });
	var longDayFmt = new Intl.DateTimeFormat(LANG, { day: 'numeric', month: 'long', year: 'numeric' });
	var monthFmt = new Intl.DateTimeFormat(LANG, { month: 'short', year: 'numeric' });
	var longMonthFmt = new Intl.DateTimeFormat(LANG, { month: 'long', year: 'numeric' });
	var dateTimeFmt = new Intl.DateTimeFormat(LANG, { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });

	var STORAGE_KEY = 'gol-stats-state-v1';
	var NOTICE_KEY = 'gol-stats-notice-changes-v1';

	var state = {
		days: '30',
		from: '',
		to: '',
		project: '',
		user: '',
		verb: 'gvsigol_core/get_conf',
		interval: 'auto',
		showTable: false,
		usersVerb: 'gvsigol_core/get_conf',
		heatVerb: 'gvsigol_core/get_conf',
		unusedType: 'project',
		unusedDays: '90',
		metric: ''
	};
	var controllers = {};
	var chart = null;
	var unusedTable = null;

	// ------------------------------------------------------------------
	// Utilidades
	// ------------------------------------------------------------------

	function $1(selector, scope) {
		return (scope || root).querySelector(selector);
	}

	function $all(selector, scope) {
		return Array.prototype.slice.call((scope || root).querySelectorAll(selector));
	}

	function esc(value) {
		return String(value === null || value === undefined ? '' : value)
			.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
			.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
	}

	function fmt(template, value) {
		return String(template).replace('%s', value);
	}

	function pad(n) {
		return n < 10 ? '0' + n : String(n);
	}

	function isoDate(d) {
		return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
	}

	function parseIsoDate(value) {
		var p = value.split('-');
		return new Date(+p[0], +p[1] - 1, +p[2]);
	}

	function formatDateTime(iso) {
		return iso ? dateTimeFmt.format(new Date(iso)) : '';
	}

	function storageGet(key) {
		try {
			return window.localStorage.getItem(key);
		} catch (e) {
			return null;
		}
	}

	function storageSet(key, value) {
		try {
			window.localStorage.setItem(key, value);
		} catch (e) {
			/* almacenamiento no disponible: se ignora */
		}
	}

	function card(name) {
		return $1('[data-st-card="' + name + '"]');
	}

	function cardBody(name) {
		return $1('[data-st-body]', card(name));
	}

	function buildUrl(base, params) {
		var query = [];
		Object.keys(params).forEach(function (key) {
			var value = params[key];
			if (value !== '' && value !== null && value !== undefined) {
				query.push(encodeURIComponent(key) + '=' + encodeURIComponent(value));
			}
		});
		return base + (query.length ? '?' + query.join('&') : '');
	}

	function range() {
		if (state.days === 'custom' && state.from && state.to) {
			return { from: state.from, to: state.to };
		}
		var days = parseInt(state.days === 'custom' ? '30' : state.days, 10);
		var to = new Date();
		var from = new Date(to.getFullYear(), to.getMonth(), to.getDate() - (days - 1));
		return { from: isoDate(from), to: isoDate(to) };
	}

	function baseParams(extra) {
		var r = range();
		var params = { from: r.from, to: r.to, project: state.project, user: state.user };
		Object.keys(extra || {}).forEach(function (k) { params[k] = extra[k]; });
		return params;
	}

	function fetchJSON(url, signal) {
		return fetch(url, {
			credentials: 'same-origin',
			headers: { 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
			signal: signal
		}).then(function (response) {
			return response.json().catch(function () { return {}; }).then(function (body) {
				if (!response.ok) {
					var error = new Error(body.msg || ('HTTP ' + response.status));
					error.status = response.status;
					throw error;
				}
				return body;
			});
		});
	}

	// Carga de una tarjeta: cancela la petición anterior, muestra estados.
	function load(name, request, render) {
		if (controllers[name]) {
			controllers[name].abort();
		}
		var controller = ('AbortController' in window) ? new AbortController() : null;
		controllers[name] = controller;
		var target = name === 'summary' ? $1('[data-st-kpis]') : cardBody(name);
		setLoading(target, true);
		return request(controller ? controller.signal : undefined).then(function (data) {
			if (controllers[name] !== controller) {
				return;
			}
			setLoading(target, false);
			render(data);
		}).catch(function (error) {
			if (error && error.name === 'AbortError') {
				return;
			}
			setLoading(target, false);
			if (window.console) {
				console.error('statistics:', name, error);
			}
			if (name === 'summary') {
				$all('[data-kpi] [data-value]').forEach(function (el) { el.textContent = '–'; });
				$all('[data-kpi] [data-delta]').forEach(function (el) { el.textContent = T.error; });
			} else {
				showState(target, 'error', T.error, function () { load(name, request, render); });
			}
		});
	}

	function setLoading(target, loading) {
		if (!target) {
			return;
		}
		var overlay = target.querySelector(':scope > .st-loading-overlay');
		if (loading && !overlay) {
			overlay = document.createElement('div');
			overlay.className = 'st-loading-overlay';
			overlay.innerHTML = '<i class="fa fa-circle-o-notch fa-spin" aria-hidden="true"></i><span class="sr-only">' + esc(T.loading) + '</span>';
			if (getComputedStyle(target).position === 'static') {
				target.style.position = 'relative';
			}
			target.appendChild(overlay);
		} else if (!loading && overlay) {
			overlay.remove();
		}
		target.setAttribute('aria-busy', loading ? 'true' : 'false');
	}

	function showState(target, kind, message, retry) {
		var icon = kind === 'error' ? 'fa-exclamation-circle' : 'fa-bar-chart';
		target.innerHTML = '<div class="st-state st-state--' + kind + '"><i class="fa ' + icon + '" aria-hidden="true"></i>' +
			'<span>' + esc(message) + '</span>' +
			(retry ? '<button type="button" class="btn-pl-outline">' + esc(T.retry) + '</button>' : '') + '</div>';
		if (retry) {
			target.querySelector('button').addEventListener('click', retry);
		}
	}

	// Tooltip propio (mapa de calor)
	var tooltip = $1('[data-st-tooltip]');

	function showTooltip(title, text, event) {
		tooltip.innerHTML = '<strong>' + esc(title) + '</strong>' + esc(text);
		tooltip.hidden = false;
		var x = event.clientX + 14;
		var y = event.clientY + 14;
		var rect = tooltip.getBoundingClientRect();
		if (x + rect.width > window.innerWidth - 8) {
			x = event.clientX - rect.width - 14;
		}
		if (y + rect.height > window.innerHeight - 8) {
			y = event.clientY - rect.height - 14;
		}
		tooltip.style.left = x + 'px';
		tooltip.style.top = y + 'px';
	}

	function hideTooltip() {
		tooltip.hidden = true;
	}

	function setSegmented(group, attr, value) {
		$all('button', group).forEach(function (button) {
			var active = button.getAttribute(attr) === value;
			button.classList.toggle('is-active', active);
			button.setAttribute('aria-checked', active ? 'true' : 'false');
		});
	}

	// ------------------------------------------------------------------
	// Resumen (KPI + cobertura)
	// ------------------------------------------------------------------

	function renderSummary(data) {
		var kpis = data.kpis;
		Object.keys(kpis).forEach(function (key) {
			var tile = $1('[data-kpi="' + key + '"]');
			if (!tile) {
				return;
			}
			var kpi = kpis[key];
			var isShare = key === 'anonymous_share';
			$1('[data-value]', tile).textContent = kpi.value === null ? '–' :
				(isShare ? decimalFmt.format(kpi.value) + ' %' : numberFmt.format(kpi.value));
			$1('[data-delta]', tile).innerHTML = deltaHtml(kpi, isShare);
		});
		renderCoverage(data.meta);
	}

	function deltaHtml(kpi, isShare) {
		if (isShare) {
			if (kpi.value === null || kpi.previous === null) {
				return '&nbsp;';
			}
			var points = kpi.value - kpi.previous;
			return '<span class="st-flat">' + (points >= 0 ? '+' : '−') + decimalFmt.format(Math.abs(points)) + ' pp</span> ' + esc(T.vsPrevious);
		}
		if (kpi.change === null) {
			return kpi.value ? esc(T.noPrevious) : '&nbsp;';
		}
		if (kpi.change === 0) {
			return '<span class="st-flat">= 0 %</span> ' + esc(T.vsPrevious);
		}
		var up = kpi.change > 0;
		return '<span class="' + (up ? 'st-up' : 'st-down') + '"><i class="fa fa-arrow-' + (up ? 'up' : 'down') + '" aria-hidden="true"></i> ' +
			(up ? '+' : '−') + decimalFmt.format(Math.abs(kpi.change)) + ' %</span> ' + esc(T.vsPrevious);
	}

	function renderCoverage(meta) {
		var subtitle = $1('[data-st-coverage]');
		var notice = $1('[data-st-notice-coverage]');
		var text = $1('[data-st-notice-coverage-text]');
		if (!meta.tracking_since) {
			subtitle.textContent = T.noData;
			text.textContent = T.coverageNone;
			notice.hidden = false;
			return;
		}
		var since = new Date(meta.tracking_since);
		subtitle.textContent = fmt(T.dataSince, longDayFmt.format(since));
		if (isoDate(since) > meta.from) {
			text.textContent = fmt(T.coveragePartial, longDayFmt.format(since));
			notice.hidden = false;
		} else {
			notice.hidden = true;
		}
	}

	// ------------------------------------------------------------------
	// Evolución
	// ------------------------------------------------------------------

	function effectiveInterval() {
		if (state.interval !== 'auto') {
			return state.interval;
		}
		var r = range();
		var days = Math.round((parseIsoDate(r.to) - parseIsoDate(r.from)) / 86400000) + 1;
		if (days <= 62) {
			return 'day';
		}
		return days <= 400 ? 'week' : 'month';
	}

	function periodLabel(period, interval, long) {
		var d = parseIsoDate(period);
		if (interval === 'month') {
			return (long ? longMonthFmt : monthFmt).format(d);
		}
		return (long ? longDayFmt : dayFmt).format(d);
	}

	function loadTimeseries() {
		var interval = effectiveInterval();
		var params = baseParams({ verb: state.verb, interval: interval });
		$1('[data-st-csv]', card('timeseries')).href = buildUrl(API.timeseries, Object.assign({ format: 'csv' }, params));
		load('timeseries', function (signal) {
			return fetchJSON(buildUrl(API.timeseries, params), signal);
		}, renderTimeseries);
	}

	function renderTimeseries(data) {
		var body = cardBody('timeseries');
		var tableWrap = $1('[data-st-table]', card('timeseries'));
		var interval = data.meta.interval;
		var points = data.points;
		var total = points.reduce(function (sum, p) { return sum + p.total; }, 0);

		if (chart) {
			chart.destroy();
			chart = null;
		}
		renderTimeseriesTable(tableWrap, points, interval);
		if (!total) {
			showState(body, 'empty', T.empty);
			return;
		}
		body.innerHTML = '<canvas data-st-canvas role="img" aria-label="' + esc($1('.st-card__title', card('timeseries')).textContent) + '"></canvas>';

		var hasAnon = points.some(function (p) { return p.anonymous > 0; });
		var hasAuth = points.some(function (p) { return p.authenticated > 0; });
		var datasets = [];
		if (hasAuth || !hasAnon) {
			datasets.push(lineDataset(T.authenticated, SERIES_AUTH, points.map(function (p) { return p.authenticated; })));
		}
		if (hasAnon) {
			datasets.push(lineDataset(T.anonymous, SERIES_ANON, points.map(function (p) { return p.anonymous; })));
		}

		chart = new Chart($1('canvas', body).getContext('2d'), {
			type: 'line',
			data: {
				labels: points.map(function (p) { return periodLabel(p.period, interval, false); }),
				datasets: datasets
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				animation: { duration: 250 },
				legend: {
					display: datasets.length > 1,
					position: 'top',
					labels: { usePointStyle: true, boxWidth: 8, fontColor: AXIS_COLOR, fontSize: 12, padding: 16 }
				},
				hover: { mode: 'index', intersect: false },
				tooltips: {
					mode: 'index',
					intersect: false,
					backgroundColor: '#2e3a45',
					titleFontSize: 12,
					bodyFontSize: 12,
					footerFontSize: 12,
					xPadding: 10,
					yPadding: 8,
					callbacks: {
						title: function (items) {
							return periodLabel(points[items[0].index].period, interval, true);
						},
						label: function (item, chartData) {
							return ' ' + chartData.datasets[item.datasetIndex].label + ': ' + numberFmt.format(item.yLabel);
						},
						footer: function (items) {
							return T.total + ': ' + numberFmt.format(points[items[0].index].total);
						}
					}
				},
				scales: {
					xAxes: [{
						gridLines: { display: false },
						ticks: { fontColor: AXIS_COLOR, fontSize: 11, maxTicksLimit: 12, maxRotation: 0, autoSkipPadding: 12 }
					}],
					yAxes: [{
						gridLines: { color: GRID_COLOR, zeroLineColor: GRID_COLOR, drawBorder: false },
						ticks: {
							beginAtZero: true,
							precision: 0,
							fontColor: AXIS_COLOR,
							fontSize: 11,
							maxTicksLimit: 6,
							callback: function (value) { return numberFmt.format(value); }
						}
					}]
				}
			}
		});
	}

	function lineDataset(label, color, values) {
		return {
			label: label,
			data: values,
			borderColor: color,
			backgroundColor: color,
			borderWidth: 2,
			fill: false,
			lineTension: 0.25,
			pointRadius: values.length > 45 ? 0 : 2.5,
			pointHoverRadius: 5,
			pointHitRadius: 10,
			pointBorderWidth: 2,
			pointBackgroundColor: color,
			pointHoverBorderColor: '#fff'
		};
	}

	function renderTimeseriesTable(wrap, points, interval) {
		var rows = points.map(function (p) {
			return '<tr><td>' + esc(periodLabel(p.period, interval, true)) + '</td>' +
				'<td class="st-num">' + numberFmt.format(p.authenticated) + '</td>' +
				'<td class="st-num">' + numberFmt.format(p.anonymous) + '</td>' +
				'<td class="st-num"><strong>' + numberFmt.format(p.total) + '</strong></td></tr>';
		}).join('');
		wrap.innerHTML = '<table class="st-table"><thead><tr><th>' + esc(T.period) + '</th><th class="st-num">' + esc(T.authenticated) +
			'</th><th class="st-num">' + esc(T.anonymous) + '</th><th class="st-num">' + esc(T.total) + '</th></tr></thead><tbody>' + rows + '</tbody></table>';
	}

	// ------------------------------------------------------------------
	// Rankings
	// ------------------------------------------------------------------

	function loadTop(name, verb, by) {
		var params = baseParams({ verb: verb, by: by, limit: 10 });
		$1('[data-st-csv]', card(name)).href = buildUrl(API.top, Object.assign({ format: 'csv' }, params));
		load(name, function (signal) {
			return fetchJSON(buildUrl(API.top, params), signal);
		}, function (data) { renderBars(cardBody(name), data); });
	}

	function renderBars(body, data) {
		var items = data.items;
		if (!items.length) {
			showState(body, 'empty', T.empty);
			if (data.anonymous) {
				body.insertAdjacentHTML('beforeend', '<p class="st-footnote">' + esc(fmt(T.anonymousAccesses, numberFmt.format(data.anonymous))) + '</p>');
			}
			return;
		}
		var max = items[0].count || 1;
		var html = '<ol class="st-bars">' + items.map(function (item) {
			var label = item.exists ? esc(item.label) : '#' + esc(item.id) + ' <small>' + esc(T.deleted) + '</small>';
			var meta = [];
			if (item.unique_users !== undefined && item.unique_users !== null) {
				meta.push(esc(item.unique_users === 1 ? T.uniqueUsersOne : fmt(T.uniqueUsers, numberFmt.format(item.unique_users))));
			}
			if (item.last_seen) {
				meta.push(esc(T.lastSeen) + ': ' + esc(formatDateTime(item.last_seen)));
			}
			return '<li>' +
				'<span class="st-bars__pos">' + item.position + '</span>' +
				'<span class="st-bars__label" title="' + (item.exists ? esc(item.label) : '') + '">' + label + '</span>' +
				'<span class="st-bars__value">' + numberFmt.format(item.count) + '<small>' + decimalFmt.format(item.share) + ' %</small></span>' +
				'<span class="st-bars__track" aria-hidden="true"><span class="st-bars__fill" style="width:' + (item.count * 100 / max).toFixed(1) + '%"></span></span>' +
				(meta.length ? '<span class="st-bars__meta">' + meta.join(' · ') + '</span>' : '') +
				'</li>';
		}).join('') + '</ol>';
		if (data.anonymous) {
			html += '<p class="st-footnote">' + esc(fmt(T.anonymousAccesses, numberFmt.format(data.anonymous))) + '</p>';
		}
		body.innerHTML = html;
	}

	// ------------------------------------------------------------------
	// Mapa de calor
	// ------------------------------------------------------------------

	function loadHeatmap() {
		var params = baseParams({ verb: state.heatVerb });
		load('heatmap', function (signal) {
			return fetchJSON(buildUrl(API.heatmap, params), signal);
		}, renderHeatmap);
	}

	function heatColor(count, max) {
		if (!count) {
			return '';
		}
		var index = Math.min(HEAT_RAMP.length - 1, Math.ceil(count / max * HEAT_RAMP.length) - 1);
		return HEAT_RAMP[index];
	}

	function renderHeatmap(data) {
		var body = cardBody('heatmap');
		if (!data.max) {
			showState(body, 'empty', T.empty);
			return;
		}
		var html = '<div class="st-heatmap" role="table"><span></span>';
		for (var h = 0; h < 24; h++) {
			html += '<span class="st-heatmap__hour" aria-hidden="true">' + (h % 3 === 0 ? h : '') + '</span>';
		}
		data.matrix.forEach(function (row, day) {
			html += '<span class="st-heatmap__day">' + esc(T.weekdays[day]) + '</span>';
			row.forEach(function (count, hour) {
				var color = heatColor(count, data.max);
				html += '<span class="st-heatmap__cell" data-day="' + day + '" data-hour="' + hour + '" data-count="' + count + '"' +
					(color ? ' style="background:' + color + '"' : '') +
					' aria-label="' + esc(T.weekdaysLong[day] + ' ' + pad(hour) + ':00 · ' + count) + '"></span>';
			});
		});
		html += '</div><div class="st-heatmap-legend" aria-hidden="true"><span class="st-heatmap-legend__text">' + esc(T.less) + '</span>' +
			'<span class="st-swatch" style="background:var(--gol-bg)"></span>' +
			HEAT_RAMP.map(function (c) { return '<span class="st-swatch" style="background:' + c + '"></span>'; }).join('') +
			'<span class="st-heatmap-legend__text">' + esc(T.moreActivity) + '</span></div>';
		body.innerHTML = html;
	}

	// ------------------------------------------------------------------
	// Sin uso
	// ------------------------------------------------------------------

	function loadUnused() {
		var params = { type: state.unusedType, days: state.unusedDays };
		$1('[data-st-csv]', card('unused')).href = buildUrl(API.unused, Object.assign({ format: 'csv', limit: 5000 }, params));
		load('unused', function (signal) {
			return fetchJSON(buildUrl(API.unused, Object.assign({ limit: 5000 }, params)), signal);
		}, renderUnused);
	}

	function renderUnused(data) {
		var body = cardBody('unused');
		if (unusedTable) {
			unusedTable.destroy();
			unusedTable = null;
		}
		var isLayer = data.meta.type === 'layer';
		var notice = '';
		if (data.meta.partial_coverage) {
			notice = '<div class="st-notice st-notice--warn"><i class="fa fa-exclamation-triangle" aria-hidden="true"></i><div>' +
				esc(data.meta.tracking_since ? fmt(T.unusedPartial, longDayFmt.format(new Date(data.meta.tracking_since))) : T.coverageNone) +
				'</div></div>';
		}
		if (!data.items.length) {
			showState(body, 'empty', T.emptyUnused);
			body.insertAdjacentHTML('afterbegin', notice);
			return;
		}
		var rows = data.items.map(function (item) {
			var last = item.last_used ? new Date(item.last_used) : null;
			return '<tr><td>' + esc(item.title || item.name) + '</td><td class="st-muted">' + esc(item.name) + '</td>' +
				(isLayer ? '<td class="st-muted">' + esc(item.workspace || '') + '</td>' : '') +
				'<td data-order="' + (last ? last.getTime() : 0) + '">' + (last ? esc(dateTimeFmt.format(last)) : '<span class="st-muted">' + esc(T.never) + '</span>') + '</td></tr>';
		}).join('');
		body.innerHTML = notice + '<div class="st-table-wrap"><table class="st-table" data-st-unused-table><thead><tr><th>' + esc(T.title) +
			'</th><th>' + esc(T.name) + '</th>' + (isLayer ? '<th>' + esc(T.workspace) + '</th>' : '') + '<th>' + esc(T.lastUsed) +
			'</th></tr></thead><tbody>' + rows + '</tbody></table></div>';
		if (window.jQuery && jQuery.fn.DataTable) {
			unusedTable = jQuery($1('[data-st-unused-table]', body)).DataTable({
				order: [[isLayer ? 3 : 2, 'asc']],
				pageLength: 10,
				lengthChange: false,
				searching: true,
				paging: data.items.length > 10,
				info: data.items.length > 10,
				language: {
					search: T.search + ':',
					info: T.tableInfo,
					infoEmpty: T.tableInfoEmpty,
					infoFiltered: T.tableInfoFiltered,
					zeroRecords: T.tableZeroRecords,
					paginate: { previous: T.tablePrevious, next: T.tableNext }
				}
			});
		}
	}

	// ------------------------------------------------------------------
	// Otras métricas (declaradas por plugins)
	// ------------------------------------------------------------------

	function loadMetricsCatalog() {
		fetchJSON(API.metrics).then(function (data) {
			var extra = data.metrics.filter(function (m) { return config.coreVerbs.indexOf(m.verb) === -1; });
			if (!extra.length) {
				return;
			}
			var select = $1('[data-st-metric]');
			select.innerHTML = extra.map(function (m) {
				return '<option value="' + esc(m.key) + '" data-verb="' + esc(m.verb) + '" data-by="' + (m.reverse ? 'user' : 'object') + '">' + esc(m.title) + '</option>';
			}).join('');
			state.metric = extra[0].key;
			card('metric').classList.remove('hidden');
			select.addEventListener('change', function () {
				state.metric = select.value;
				loadMetric();
			});
			loadMetric();
		}).catch(function () { /* sin métricas extra */ });
	}

	function loadMetric() {
		var option = $1('[data-st-metric] option[value="' + state.metric + '"]');
		if (!option) {
			return;
		}
		loadTop('metric', option.getAttribute('data-verb'), option.getAttribute('data-by'));
	}

	// ------------------------------------------------------------------
	// Orquestación
	// ------------------------------------------------------------------

	function loadFiltered() {
		load('summary', function (signal) {
			return fetchJSON(buildUrl(API.summary, baseParams()), signal);
		}, renderSummary);
		loadTimeseries();
		loadTop('top-projects', 'gvsigol_core/get_conf', 'object');
		loadTop('top-layers', 'gvsigol_services/layer_activate', 'object');
		loadTop('top-users', state.usersVerb, 'user');
		loadHeatmap();
		if (state.metric) {
			loadMetric();
		}
	}

	function saveState() {
		storageSet(STORAGE_KEY, JSON.stringify({ days: state.days, from: state.from, to: state.to, interval: state.interval }));
	}

	function restoreState() {
		var saved = storageGet(STORAGE_KEY);
		if (!saved) {
			return;
		}
		try {
			saved = JSON.parse(saved);
			['days', 'from', 'to', 'interval'].forEach(function (key) {
				if (typeof saved[key] === 'string') {
					state[key] = saved[key];
				}
			});
		} catch (e) {
			/* estado guardado no válido: se ignora */
		}
	}

	function syncPeriodControls() {
		setSegmented($1('[data-st-period]'), 'data-days', state.days);
		var custom = $1('[data-st-custom]');
		custom.classList.toggle('hidden', state.days !== 'custom');
		if (state.days === 'custom') {
			if (!state.from || !state.to) {
				var r = range();
				state.from = r.from;
				state.to = r.to;
			}
			$1('[data-st-from]').value = state.from;
			$1('[data-st-to]').value = state.to;
		}
		$1('[data-st-interval]').value = state.interval;
	}

	function bind() {
		$1('[data-st-period]').addEventListener('click', function (event) {
			var button = event.target.closest('button[data-days]');
			if (!button) {
				return;
			}
			state.days = button.getAttribute('data-days');
			syncPeriodControls();
			saveState();
			loadFiltered();
		});

		function onCustomDate() {
			var from = $1('[data-st-from]').value;
			var to = $1('[data-st-to]').value;
			if (from && to && from <= to) {
				state.from = from;
				state.to = to;
				saveState();
				loadFiltered();
			}
		}
		$1('[data-st-from]').addEventListener('change', onCustomDate);
		$1('[data-st-to]').addEventListener('change', onCustomDate);

		// jQuery para que también funcione si se aplica select2
		jQuery($1('[data-st-project]')).on('change', function () {
			state.project = this.value;
			loadFiltered();
		});
		jQuery($1('[data-st-user]')).on('change', function () {
			state.user = this.value;
			loadFiltered();
		});

		$1('[data-st-verb]').addEventListener('click', function (event) {
			var button = event.target.closest('button[data-verb]');
			if (!button) {
				return;
			}
			state.verb = button.getAttribute('data-verb');
			setSegmented($1('[data-st-verb]'), 'data-verb', state.verb);
			loadTimeseries();
		});
		$1('[data-st-interval]').addEventListener('change', function () {
			state.interval = this.value;
			saveState();
			loadTimeseries();
		});
		$1('[data-st-toggle-table]').addEventListener('click', function () {
			state.showTable = !state.showTable;
			this.setAttribute('aria-pressed', state.showTable ? 'true' : 'false');
			this.classList.toggle('is-active', state.showTable);
			$1('[data-st-table]', card('timeseries')).classList.toggle('hidden', !state.showTable);
			cardBody('timeseries').classList.toggle('hidden', state.showTable);
		});

		$1('[data-st-users-verb]').addEventListener('change', function () {
			state.usersVerb = this.value;
			loadTop('top-users', state.usersVerb, 'user');
		});
		$1('[data-st-heatmap-verb]').addEventListener('change', function () {
			state.heatVerb = this.value;
			loadHeatmap();
		});

		$1('[data-st-unused-type]').addEventListener('click', function (event) {
			var button = event.target.closest('button[data-type]');
			if (!button) {
				return;
			}
			state.unusedType = button.getAttribute('data-type');
			setSegmented($1('[data-st-unused-type]'), 'data-type', state.unusedType);
			loadUnused();
		});
		$1('[data-st-unused-days]').addEventListener('change', function () {
			state.unusedDays = this.value;
			loadUnused();
		});

		// Tooltip del mapa de calor
		var heatBody = cardBody('heatmap');
		heatBody.addEventListener('mousemove', function (event) {
			var cell = event.target.closest('.st-heatmap__cell');
			if (!cell) {
				hideTooltip();
				return;
			}
			var day = +cell.getAttribute('data-day');
			var hour = +cell.getAttribute('data-hour');
			var count = +cell.getAttribute('data-count');
			showTooltip(T.weekdaysLong[day] + ', ' + pad(hour) + ':00–' + pad((hour + 1) % 24) + ':00',
				numberFmt.format(count) + ' ' + (count === 1 ? T.eventOne : T.events), event);
		});
		heatBody.addEventListener('mouseleave', hideTooltip);

		// Aviso de cambios en el cálculo (se puede cerrar)
		var changes = $1('[data-st-notice-changes]');
		if (!storageGet(NOTICE_KEY)) {
			changes.hidden = false;
		}
		$1('[data-st-dismiss]', changes).addEventListener('click', function () {
			changes.hidden = true;
			storageSet(NOTICE_KEY, '1');
		});
	}

	function init() {
		restoreState();
		syncPeriodControls();
		setSegmented($1('[data-st-verb]'), 'data-verb', state.verb);
		setSegmented($1('[data-st-unused-type]'), 'data-type', state.unusedType);
		bind();
		loadFiltered();
		loadUnused();
		loadMetricsCatalog();
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();
