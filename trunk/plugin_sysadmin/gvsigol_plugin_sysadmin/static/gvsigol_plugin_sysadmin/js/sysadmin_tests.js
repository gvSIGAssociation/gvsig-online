/* global jQuery */
/**
 * Sysadmin tests console: discovery table, presets, Celery run + polling.
 */
(function ($) {
	'use strict';

	var rawPayload = null;
	var pollTimer = null;
	var activeRunId = null;
	var pollingBusy = false;
	var runnerLocked = false;

	function getCsrfToken() {
		if ($.gvsigOL && $.gvsigOL.getCsrfCookie) {
			return $.gvsigOL.getCsrfCookie();
		}
		var m = document.cookie.match(/csrftoken=([^;]+)/);
		return m ? decodeURIComponent(m[1]) : '';
	}

	function $root() {
		return $('#sysadmin-tests-app');
	}

	function discoveryUrl() {
		return String($root().data('discover-url') || '');
	}

	function runUrl() {
		return String($root().data('run-url') || '');
	}

	function statusUrl(runId) {
		var tpl = String($root().data('status-url-template') || '');
		var id = String(runId);
		if (tpl.indexOf('/0/') >= 0) {
			return tpl.replace('/0/', '/' + id + '/');
		}
		if (tpl.substr(-3) === '/0/') {
			return tpl.slice(0, -2) + id + '/';
		}
		if (tpl.slice(-2) === '/0') {
			return tpl.slice(0, -1) + id;
		}
		return tpl.replace(/\/0\b/, '/' + id);
	}

	function isTerminalStatus(status) {
		return (
			status === 'success' ||
			status === 'failure' ||
			status === 'error'
		);
	}

	function statusLabelClass(status) {
		switch (status) {
			case 'success':
				return 'label-success';
			case 'failure':
				return 'label-warning';
			case 'error':
				return 'label-danger';
			case 'running':
				return 'label-primary';
			case 'pending':
				return 'label-default';
			default:
				return 'label-default';
		}
	}

	function hideAlert(which) {
		$('#sysadmin-' + which + '-alert').hide().text('');
	}

	function showAlert(which, ok, message) {
		var $el = $('#sysadmin-' + which + '-alert');
		var cls = ok ? 'alert-success' : 'alert-danger';
		$el
			.removeClass('alert-danger alert-success alert-warning')
			.addClass(cls)
			.text(message || '')
			.show();
	}

	function themesFromPayload(payload) {
		return payload && payload.themes ? payload.themes : [];
	}

	function totalTestsFromPayload(payload) {
		var n = 0;
		if (!payload || !payload.modules) {
			return 0;
		}
		for (var i = 0; i < payload.modules.length; i += 1) {
			n += payload.modules[i].tests.length;
		}
		return n;
	}

	function uniqueApps(payload) {
		var seen = {};
		var apps = [];
		if (!payload || !payload.modules) {
			return apps;
		}
		for (var i = 0; i < payload.modules.length; i += 1) {
			var a = payload.modules[i].app;
			if (!seen[a]) {
				seen[a] = true;
				apps.push(a);
			}
		}
		return apps.sort();
	}

	function computeFiltered() {
		if (!rawPayload || !rawPayload.modules) {
			return [];
		}
		var needsDb = $('#filter-needs-db').val();
		var theme = $('#filter-theme').val();
		var q = String($('#filter-search').val() || '')
			.trim()
			.toLowerCase();
		var row = [];

		for (var i = 0; i < rawPayload.modules.length; i += 1) {
			var mod = rawPayload.modules[i];
			if (theme !== 'all' && mod.theme !== theme) {
				continue;
			}
			var sub = [];
			for (var j = 0; j < mod.tests.length; j += 1) {
				var t = mod.tests[j];
				if (needsDb === 'yes' && !t.needs_db) {
					continue;
				}
				if (needsDb === 'no' && t.needs_db) {
					continue;
				}
				if (q) {
					var blob = (
						mod.label +
						' ' +
						t.name +
						' ' +
						mod.app
					).toLowerCase();
					if (blob.indexOf(q) === -1) {
						continue;
					}
				}
				sub.push(t);
			}
			if (sub.length) {
				row.push({
					label: mod.label,
					app: mod.app,
					theme: mod.theme,
					needs_db: mod.needs_db,
					tests: sub,
				});
			}
		}

		return row;
	}

	function gatherPreservedChecks() {
		var map = {};
		$('#sysadmin-test-tree .sysadmin-test-cb:checked').each(function () {
			var id = $(this).attr('data-test-id');
			if (id) {
				map[id] = true;
			}
		});
		return map;
	}

	function updateCounts() {
		var filtered = computeFiltered();
		var vis = 0;
		var k = 0;
		for (; k < filtered.length; k += 1) {
			vis += filtered[k].tests.length;
		}

		var tot = totalTestsFromPayload(rawPayload);

		var checked = $(
			'#sysadmin-test-tree .sysadmin-test-cb:checked',
		).length;

		$('#sysadmin-visible-count').text(String(vis));
		$('#sysadmin-total-count').text(String(tot));
		$('#sysadmin-checked-count').text(String(checked));

		var allowRun = checked > 0 && !runnerLocked;
		$('#btn-run-tests').prop('disabled', !allowRun);
	}

	function renderThemeOptions() {
		var $sel = $('#filter-theme');
		var preserved = String($sel.val() || 'all');

		while ($sel.children().length > 1) {
			$sel.children().last().remove();
		}

		var list = themesFromPayload(rawPayload);
		for (var i = 0; i < list.length; i += 1) {
			var tv = String(list[i]);
			$sel.append($('<option>').attr('value', tv).text(tv));
		}

		if ($sel.find('option[value="' + preserved + '"]').length) {
			$sel.val(preserved);
		} else {
			$sel.val('all');
		}
	}

	function renderAppPresets() {
		var $wrap = $('#sysadmin-app-presets').empty();
		if (!rawPayload) {
			return;
		}
		var apps = uniqueApps(rawPayload);
		var n = apps.length;

		for (var i = 0; i < n; i += 1) {
			var nm = apps[i];

			var $btn = $(
				'<button type="button" class="btn btn-default btn-xs sysadmin-select-app" style="margin-right:6px;margin-bottom:6px;"></button>',
			);
			$btn.attr('data-app', nm);
			$btn.text(nm);
			$wrap.append($btn);
		}
	}

	function renderTree(preserved) {
		var filtered = computeFiltered();

		var $tree = $('#sysadmin-test-tree').empty();

		if (!filtered.length) {
			$tree.append(
				'<p class="text-muted">' +
					'No tests match the current filters.' +
					'</p>',
			);
			updateCounts();
			return;
		}

		for (var i = 0; i < filtered.length; i += 1) {
			var mod = filtered[i];
			var aid = 'sysadmin-mod-panel-' + i;

			var $panel = $('<div class="panel panel-default"></div>');
			var $heading = $(
				'<div class="panel-heading clearfix"></div>',
			);
			var $title = $(
				'<h4 class="panel-title pull-left" style="font-size:14px;"></h4>',
			);
			var $tog = $('<a data-toggle="collapse" href="#' + aid + '"></a>');
			$tog.text(mod.label);

			var $modCbWrap = $('<div class="pull-right"></div>');
			var $modCb = $(
				'<input type="checkbox" class="sysadmin-mod-cb" title="Toggle all tests in this module">',
			);
			$modCbWrap.append($modCb);

			$title.append($tog);
			$heading.append($title).append($modCbWrap);

			var $collapse = $('<div id="' + aid + '" class="panel-collapse collapse in"></div>');
			var $body = $('<div class="panel-body"></div>');
			var $table = $(
				'<table class="table table-striped table-condensed small margin-bottom-none"></table>',
			);
			var $thead = $(
				'<thead><tr><th style="width:32px;"></th><th>' +
					'Test case' +
					'</th><th>' +
					'DB' +
					'</th><th style="width:90px;">Topic</th></tr></thead>',
			);
			$table.append($thead);
			var $tbody = $('<tbody></tbody>');
			var t = 0;
			for (; t < mod.tests.length; t += 1) {
				var testObj = mod.tests[t];
				var $tr = $('<tr></tr>');
				var $td0 = $('<td></td>');
				var $cb = $(
					'<input type="checkbox" class="sysadmin-test-cb">',
				);
				$cb.attr('data-test-id', testObj.id);
				$cb.attr('data-app', mod.app);
				$cb.attr('data-needs-db', testObj.needs_db ? '1' : '0');
				if (preserved && preserved[testObj.id]) {
					$cb.prop('checked', true);
				}
				$td0.append($cb);

				var $td1 = $('<td></td>');
				$td1.text(testObj.name);

				var $td2 = $('<td></td>');
				$td2.text(testObj.needs_db ? 'yes' : 'no');

				var $td3 = $('<td></td>');
				$td3.text(mod.theme);

				$tr.append($td0, $td1, $td2, $td3);
				$tbody.append($tr);
			}
			$table.append($tbody);
			$body.append($table);
			$collapse.append($body);

			$panel.append($heading).append($collapse);
			$tree.append($panel);

			$modCb.on('change', function () {
				var on = $(this).prop('checked');
				$(this)
					.closest('.panel')
					.find('.sysadmin-test-cb')
					.prop('checked', on);
				updateCounts();
			});
		}

		updateCounts();
	}

	function applyPreset(name) {
		if (name === 'no-db') {
			$('#filter-needs-db').val('no');
			renderTree({});
			$('#sysadmin-test-tree .sysadmin-test-cb').prop('checked', true);
		} else if (name === 'only-db') {
			$('#filter-needs-db').val('yes');
			renderTree({});
			$('#sysadmin-test-tree .sysadmin-test-cb').prop('checked', true);
		} else if (name === 'all-visible') {
			renderTree({});
			$('#sysadmin-test-tree .sysadmin-test-cb').prop('checked', true);
		} else if (name === 'clear') {
			$('#sysadmin-test-tree .sysadmin-test-cb').prop('checked', false);
			$('#sysadmin-test-tree .sysadmin-mod-cb').prop('checked', false);
		}
		updateCounts();
	}

	function selectByApp(appName) {
		renderTree({});
		$('#sysadmin-test-tree .sysadmin-test-cb').each(function () {
			var on = $(this).attr('data-app') === appName;
			$(this).prop('checked', on);
		});
		$('#sysadmin-test-tree .sysadmin-mod-cb').each(function () {
			var $panel = $(this).closest('.panel');
			var all = $panel.find('.sysadmin-test-cb').length;
			var sel = $panel.find('.sysadmin-test-cb:checked').length;
			$(this).prop('checked', all > 0 && all === sel);
		});
		updateCounts();
	}

	function stopPolling() {
		if (pollTimer) {
			clearInterval(pollTimer);
			pollTimer = null;
		}
		pollingBusy = false;
	}

	function setRunStatusUi(status, runId) {
		var $lab = $('#sysadmin-run-status-label');
		$lab.removeClass(
			'label-default label-primary label-success label-warning label-danger',
		);
		$lab.addClass(statusLabelClass(status));
		$lab.text(status === 'idle' ? 'Idle' : status);

		var hint = '';
		if (runId) {
			hint = 'run #' + String(runId);
		}
		$('#sysadmin-run-id-hint').text(hint);
	}

	function renderRunOutput(data) {
		var out = data && data.stdout != null ? String(data.stdout) : '';
		var err = data && data.stderr != null ? String(data.stderr) : '';
		$('#sysadmin-run-stdout').text(out);
		$('#sysadmin-run-stderr').text(err);

		var sum = data && data.summary;
		if (sum && typeof sum === 'object') {
			$('#sysadmin-summary-wrap').show();
			var pretty = '';
			try {
				pretty = JSON.stringify(sum, null, 2);
			} catch (e) {
				pretty = String(sum);
			}
			$('#sysadmin-summary').text(pretty);
		} else {
			$('#sysadmin-summary-wrap').hide();
			$('#sysadmin-summary').text('');
		}
	}

	function tickRunnerLockFromStatus(status) {
		var busy = status === 'pending' || status === 'running';
		runnerLocked = busy;
		if (!busy) {
			updateCounts();
		} else {
			$('#btn-run-tests').prop('disabled', true);
		}
	}

	function fetchStatus(runId) {
		if (!runId || pollingBusy) {
			return;
		}
		pollingBusy = true;
		return $.ajax({
			url: statusUrl(runId),
			type: 'GET',
			dataType: 'json',
			complete: function () {
				pollingBusy = false;
			},
		})
			.done(function (data) {
				if (!data || data.error) {
					showAlert('run', false, data.error || 'Status error');
					return;
				}
				setRunStatusUi(data.status, runId);
				renderRunOutput(data);
				var st = String(data.status);
				tickRunnerLockFromStatus(st);

				if (isTerminalStatus(st)) {
					stopPolling();
					runnerLocked = false;
					updateCounts();
				}
			})
			.fail(function (xhr) {
				var detail = xhr.responseText ? xhr.responseText.slice(0, 300) : '';
				showAlert('run', false, 'Polling failed (' + xhr.status + '). ' + detail);
				stopPolling();
				runnerLocked = false;
				updateCounts();
			});
	}

	function schedulePolling(runId) {
		activeRunId = runId;
		stopPolling();
		runnerLocked = true;
		$('#btn-run-tests').prop('disabled', true);
		setRunStatusUi('pending', runId);

		hideAlert('run');
		fetchStatus(runId);
		var intervalMs = 2500;
		pollTimer = setInterval(function () {
			if (activeRunId) {
				fetchStatus(activeRunId);
			}
		}, intervalMs);
	}

	function submitRun() {
		var labels = [];
		$('#sysadmin-test-tree .sysadmin-test-cb:checked').each(function () {
			var tid = $(this).attr('data-test-id');
			if (tid) {
				labels.push(tid);
			}
		});

		if (!labels.length) {
			showAlert(
				'run',
				false,
				'Select at least one test case before running.',
			);
			return;
		}

		var hasDbReq = false;
		$('#sysadmin-test-tree .sysadmin-test-cb:checked').each(function () {
			var nd = $(this).attr('data-needs-db');
			if (nd === '1') {
				hasDbReq = true;
			}
		});
		if (hasDbReq) {
			var okWarn = window.confirm(
				'Some selected tests require a database connection and the Django test DB (often named "test"). Continue?',
			);
			if (!okWarn) {
				return;
			}
		}

		hideAlert('discover');

		var filters = {
			needs_db: $('#filter-needs-db').val(),
			theme: $('#filter-theme').val(),
			search: String($('#filter-search').val() || '').trim(),
		};

		var token = getCsrfToken();

		$.ajax({
			url: runUrl(),
			type: 'POST',
			contentType: 'application/json; charset=utf-8',
			dataType: 'json',
			data: JSON.stringify({ labels: labels, filters: filters }),
			beforeSend: function (xhr) {
				if (token) {
					xhr.setRequestHeader('X-CSRFToken', token);
				}
			},
		})
			.done(function (data, _t, jq) {
				hideAlert('run');
				if (!data || data.error) {
					showAlert('run', false, String((data && data.error) || 'Run failed'));
					return;
				}
				if (jq.status !== 201) {
					showAlert('run', false, 'Unexpected response from server.');
					return;
				}

				renderRunOutput(data);
				schedulePolling(data.id);
			})
			.fail(function (xhr) {
				var msg = '';
				try {
					var j = xhr.responseJSON;
					msg = j && j.error ? String(j.error) : '';
				} catch (_e2) {}
				if (!msg) {
					msg =
						xhr.status === 409
							? 'A test run is already in progress.'
							: 'Run request failed.';
				}
				showAlert('run', false, msg + ' (HTTP ' + xhr.status + ')');
				runnerLocked = false;
				updateCounts();
			});
	}

	function loadDiscovery() {
		hideAlert('discover');
		return $.ajax({
			url: discoveryUrl(),
			type: 'GET',
			dataType: 'json',
		})
			.done(function (data) {
				rawPayload = data;
				renderThemeOptions();
				renderAppPresets();
				renderTree(gatherPreservedChecks());
			})
			.fail(function (xhr) {
				showAlert(
					'discover',
					false,
					'Could not load test catalog (HTTP ' + xhr.status + ').',
				);
			});
	}

	$(document).ready(function () {
		setRunStatusUi('idle', null);
		$('#sysadmin-run-stdout').text('');
		$('#sysadmin-run-stderr').text('');
		$('#sysadmin-summary-wrap').hide();

		loadDiscovery();

		$('#btn-refresh-discovery').on('click', function () {
			loadDiscovery();
		});

		$('#filter-needs-db, #filter-theme').on('change', function () {
			renderTree(gatherPreservedChecks());
		});

		$('#filter-search').on('input', function () {
			renderTree(gatherPreservedChecks());
		});

		$(document).on('click', '.sysadmin-preset', function () {
			var p = $(this).data('preset');
			applyPreset(String(p));
		});

		$(document).on('click', '.sysadmin-select-app', function () {
			var app = String($(this).data('app') || '');
			if (app) {
				selectByApp(app);
			}
		});

		$('#btn-run-tests').on('click', function () {
			submitRun();
		});

		$('#sysadmin-test-tree').on('change', '.sysadmin-test-cb', function () {
			updateCounts();
		});
	});
})(jQuery);
