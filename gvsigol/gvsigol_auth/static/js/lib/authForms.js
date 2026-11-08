/**
 * gvSIG Online.
 * Copyright (C) 2010-2017 SCOLAB.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

/**
 * Ayudas de los formularios de usuarios, grupos y roles (solo avisos).
 *
 * Cada .form-group con data-gol-auth-check comprueba su campo mientras se escribe con
 * las mismas reglas que el servidor y lo indica debajo. Nunca cambia el valor por su
 * cuenta (las correcciones son botones que pulsa el usuario) ni impide enviar el
 * formulario: el servidor sigue validando como siempre. Los textos llegan ya traducidos
 * en atributos data-msg-* de la plantilla.
 *
 *   identifier       nombre de rol o grupo: ^[a-zA-Z_][a-zA-Z0-9_]*$ (views._valid_name_regex)
 *                    y, si hay data-reserved, nombres reservados («admin» en roles).
 *   username         la vista lo guarda con .lower() sobre el dato sin limpiar: se avisa de
 *                    mayúsculas y de espacios.
 *   email            formato básico (aviso orientativo).
 *   password         validadores de AUTH_PASSWORD_VALIDATORS: longitud mínima, no solo
 *                    números y parecido a usuario/nombre/apellidos/correo (como Django).
 *   password-repeat  las dos contraseñas deben coincidir (UserCreationForm).
 */
(function ($) {
	'use strict';

	var IDENTIFIER_RE = /^[a-zA-Z_][a-zA-Z0-9_]*$/;
	var seq = 0;

	function msg($group, key) {
		return $group.attr('data-msg-' + key) || '';
	}

	function chars(s) {
		return Array.from ? Array.from(s) : String(s).split('');
	}

	/* ---- Línea de estado bajo el campo ---- */

	function ensureStatus($group, $input) {
		var $status = $group.children('.gol-pg-status');
		if ($status.length) {
			return $status;
		}
		var id = ($input.attr('id') || ('gol-auth-' + (++seq))) + '-status';
		$status = $('<p class="gol-pg-status" aria-live="polite"></p>').attr('id', id);
		var $hint = $group.children('.gol-pg-hint').last();
		if ($hint.length) {
			$hint.after($status);
		} else if ($input.parent().hasClass('gol-pg-pass')) {
			$input.parent().after($status);
		} else {
			$input.after($status);
		}
		var described = [];
		if ($hint.length) {
			if (!$hint.attr('id')) {
				$hint.attr('id', id.replace(/-status$/, '-hint'));
			}
			described.push($hint.attr('id'));
		}
		described.push(id);
		$input.attr('aria-describedby', described.join(' '));
		return $status;
	}

	function clear($input, $status) {
		$status.empty().removeClass('is-valid is-invalid is-info');
		$input.removeClass('gol-pg-input-valid gol-pg-input-invalid').removeAttr('aria-invalid');
	}

	function show($input, $status, state, text, fix) {
		var icon = state === 'valid' ? 'fa-check-circle' : (state === 'invalid' ? 'fa-exclamation-circle' : 'fa-info-circle');
		$status.addClass('is-' + state).append(
			$('<i class="fa" aria-hidden="true"></i>').addClass(icon),
			document.createTextNode(' ' + text)
		);
		if (state === 'valid') {
			$input.addClass('gol-pg-input-valid');
		} else if (state === 'invalid') {
			$input.addClass('gol-pg-input-invalid').attr('aria-invalid', 'true');
		}
		if (fix) {
			var $fix = $('<button type="button" class="gol-pg-fix"></button>').text(fix.label);
			$fix.on('click', function () {
				$input.val(fix.value).trigger('input').trigger('focus');
			});
			$status.append(document.createTextNode(' '), $fix);
		}
	}

	/* ---- Nombre de rol o grupo ---- */

	/** «Técnicos de Campo» -> «Tecnicos_de_Campo»; «2024 obras» -> «_2024_obras» */
	function suggestIdentifier(value) {
		var s = String(value || '');
		if (s.normalize) {
			s = s.normalize('NFD').replace(/[̀-ͯ]/g, '');
		}
		s = s.replace(/[^a-zA-Z0-9_]+/g, '_').replace(/_+/g, '_').replace(/^_+|_+$/g, '');
		if (/^[0-9]/.test(s)) {
			s = '_' + s;
		}
		return s.substring(0, 150);
	}

	function checkIdentifier($group, $input, $status) {
		var value = $input.val();
		clear($input, $status);
		if (!value) {
			return;
		}
		var reserved = ($group.attr('data-reserved') || '').split(/\s+/).filter(Boolean);
		if (reserved.indexOf(value) !== -1) {
			show($input, $status, 'invalid', msg($group, 'reserved'));
			return;
		}
		if (IDENTIFIER_RE.test(value)) {
			show($input, $status, 'valid', msg($group, 'valid'));
			return;
		}
		var suggestion = suggestIdentifier(value);
		var fix = (suggestion && IDENTIFIER_RE.test(suggestion) && reserved.indexOf(suggestion) === -1) ?
			{label: msg($group, 'use') + ' «' + suggestion + '»', value: suggestion} : null;
		show($input, $status, 'invalid', msg($group, 'invalid'), fix);
	}

	/* ---- Nombre de usuario ---- */

	function checkUsername($group, $input, $status) {
		var value = $input.val();
		clear($input, $status);
		if (!value) {
			return;
		}
		if (/\s/.test(value)) {
			var noSpaces = value.replace(/\s+/g, '');
			show($input, $status, 'invalid', msg($group, 'spaces'),
				noSpaces ? {label: msg($group, 'use') + ' «' + noSpaces.toLowerCase() + '»', value: noSpaces.toLowerCase()} : null);
			return;
		}
		if (value !== value.toLowerCase()) {
			show($input, $status, 'info', msg($group, 'saved-as') + ' «' + value.toLowerCase() + '»');
		}
	}

	/* ---- Correo ---- */

	function checkEmail($group, $input, $status) {
		var value = $input.val();
		clear($input, $status);
		if (!value || $input.prop('readOnly')) {
			return;
		}
		if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
			show($input, $status, 'invalid', msg($group, 'invalid'));
		}
	}

	/* ---- Contraseña ---- */

	/** difflib.SequenceMatcher(a, b).quick_ratio() */
	function quickRatio(a, b) {
		var ca = chars(a), cb = chars(b);
		var total = ca.length + cb.length;
		if (!total) {
			return 1;
		}
		var avail = {};
		var i;
		for (i = 0; i < cb.length; i++) {
			avail[cb[i]] = (avail[cb[i]] || 0) + 1;
		}
		var matches = 0;
		for (i = 0; i < ca.length; i++) {
			if (avail[ca[i]] > 0) {
				avail[ca[i]]--;
				matches++;
			}
		}
		return 2 * matches / total;
	}

	/** UserAttributeSimilarityValidator (max_similarity 0.7) con los valores del formulario */
	function tooSimilar(password, values) {
		var MAX = 0.7;
		var pwd = password.toLowerCase();
		var pwdLen = chars(pwd).length;
		for (var v = 0; v < values.length; v++) {
			if (!values[v]) {
				continue;
			}
			var lower = values[v].toLowerCase();
			var parts;
			try {
				parts = lower.split(new RegExp('[^\\p{L}\\p{N}_]+', 'u'));
			} catch (e) {
				parts = lower.split(/\W+/);
			}
			parts.push(lower);
			for (var p = 0; p < parts.length; p++) {
				var partLen = chars(parts[p]).length;
				// exceeds_maximum_length_ratio: Django descarta estas comparaciones
				if (pwdLen >= 10 * partLen && partLen < MAX / 2 * pwdLen) {
					continue;
				}
				if (quickRatio(pwd, parts[p]) >= MAX) {
					return true;
				}
			}
		}
		return false;
	}

	function setRule($list, rule, state) {
		var $li = $list.children('[data-rule="' + rule + '"]');
		$li.removeClass('is-ok is-bad');
		if (state) {
			$li.addClass(state === 'ok' ? 'is-ok' : 'is-bad');
		}
	}

	function checkPassword($group, $input) {
		var value = $input.val() || '';
		var $list = $group.find('.gol-pg-checklist').first();
		if (!value) {
			$list.children().removeClass('is-ok is-bad');
			$input.removeClass('gol-pg-input-valid gol-pg-input-invalid').removeAttr('aria-invalid');
			return;
		}
		var min = parseInt($group.attr('data-min-length'), 10) || 8;
		var okLength = chars(value).length >= min;
		var allDigits;
		try {
			allDigits = new RegExp('^\\p{Nd}+$', 'u').test(value);
		} catch (e) {
			allDigits = /^[0-9]+$/.test(value);
		}
		var okNumeric = !allDigits;
		var $form = $input.closest('form');
		var values = $.map(['username', 'first_name', 'last_name', 'email'], function (name) {
			return $form.find('[name="' + name + '"]').val() || '';
		});
		var okSimilar = !tooSimilar(value, values);
		setRule($list, 'length', okLength ? 'ok' : 'bad');
		setRule($list, 'numeric', okNumeric ? 'ok' : 'bad');
		setRule($list, 'similar', okSimilar ? 'ok' : 'bad');
		var ok = okLength && okNumeric && okSimilar;
		$input.toggleClass('gol-pg-input-invalid', !ok).toggleClass('gol-pg-input-valid', false);
		if (ok) {
			$input.removeAttr('aria-invalid');
		} else {
			$input.attr('aria-invalid', 'true');
		}
	}

	function checkRepeat($group, $input, $status) {
		var value = $input.val() || '';
		clear($input, $status);
		if (!value) {
			return;
		}
		var $first = $input.closest('form').find('[name="' + ($group.attr('data-match') || 'password1') + '"]');
		if ($first.val() === value) {
			show($input, $status, 'valid', msg($group, 'match'));
		} else {
			show($input, $status, 'invalid', msg($group, 'mismatch'));
		}
	}

	/** Botón para ver u ocultar la contraseña: solo cambia el type del input */
	function addPasswordToggle($group, $input) {
		if ($input.parent().hasClass('gol-pg-pass')) {
			return;
		}
		var showLabel = msg($group, 'show') || 'Show password';
		var hideLabel = msg($group, 'hide') || 'Hide password';
		$input.wrap('<span class="gol-pg-pass"></span>');
		var $btn = $('<button type="button" class="gol-pg-pass__toggle" aria-pressed="false"><i class="fa fa-eye" aria-hidden="true"></i></button>')
			.attr({'title': showLabel, 'aria-label': showLabel});
		$btn.on('click', function () {
			var visible = $input.attr('type') === 'text';
			$input.attr('type', visible ? 'password' : 'text');
			$btn.attr({'title': visible ? showLabel : hideLabel, 'aria-label': visible ? showLabel : hideLabel, 'aria-pressed': String(!visible)});
			$btn.find('.fa').toggleClass('fa-eye', visible).toggleClass('fa-eye-slash', !visible);
		});
		$input.after($btn);
	}

	/* ---- Arranque ---- */

	function init(group) {
		var $group = $(group);
		if ($group.data('golAuthInit')) {
			return;
		}
		$group.data('golAuthInit', true);
		var kind = $group.attr('data-gol-auth-check');
		var $input = $group.find('input.form-control, input[type="text"], input[type="email"], input[type="password"]').first();
		if (!$input.length) {
			return;
		}
		var $status;
		var run;
		switch (kind) {
		case 'identifier':
			$input.attr({autocomplete: 'off', spellcheck: 'false'});
			$status = ensureStatus($group, $input);
			run = function () { checkIdentifier($group, $input, $status); };
			break;
		case 'username':
			$input.attr({autocomplete: 'off', spellcheck: 'false', autocapitalize: 'none'});
			$status = ensureStatus($group, $input);
			run = function () { checkUsername($group, $input, $status); };
			break;
		case 'email':
			$status = ensureStatus($group, $input);
			run = function () { checkEmail($group, $input, $status); };
			break;
		case 'password':
			$input.attr('autocomplete', 'new-password');
			addPasswordToggle($group, $input);
			var $list = $group.find('.gol-pg-checklist').first();
			if ($list.attr('id')) {
				$input.attr('aria-describedby', $list.attr('id'));
			}
			run = function () { checkPassword($group, $input); };
			// el parecido depende también del usuario, el nombre y el correo
			$input.closest('form').on('input', '[name="username"], [name="first_name"], [name="last_name"], [name="email"]', run);
			break;
		case 'password-repeat':
			$input.attr('autocomplete', 'new-password');
			addPasswordToggle($group, $input);
			$status = ensureStatus($group, $input);
			run = function () { checkRepeat($group, $input, $status); };
			$input.closest('form').on('input', '[name="' + ($group.attr('data-match') || 'password1') + '"]', run);
			break;
		default:
			return;
		}
		// change llega al salir del campo con un valor ya comprobado: repintar el aviso
		// ahí sustituía el botón de corrección en mitad del clic y este se perdía
		var lastValue;
		function runIfChanged() {
			var value = $input.val();
			if (value !== lastValue) {
				lastValue = value;
				run();
			}
		}
		$input.on('input change', runIfChanged);
		runIfChanged();
	}

	$(function () {
		$('[data-gol-auth-check]').each(function () {
			init(this);
		});
	});

	window.GolAuthForms = {suggestIdentifier: suggestIdentifier, quickRatio: quickRatio, tooSimilar: tooSimilar};
})(jQuery);
