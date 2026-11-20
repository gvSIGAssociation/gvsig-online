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
 * Secciones desplegables de los formularios (<details class="gol-pg-section">).
 *
 * Solo aspecto: los campos de una sección cerrada siguen dentro del formulario y se
 * envían igual. El script no cambia ningún valor; además:
 *
 *  - Resumen en la cabecera: data-gol-meta-fields lista (selectores separados por comas)
 *    los campos que se resumen: de un select, el texto de la opción elegida; de una
 *    casilla marcada, el texto de su etiqueta; de un campo de texto, su valor.
 *    data-gol-meta-count + data-gol-meta-count-label ("{n} ...") añaden un recuento.
 *  - Recuerda abierta/cerrada por navegador (localStorage) en las secciones con
 *    data-gol-section-persist. Las que no lo llevan se abren siempre al cargar.
 *  - data-gol-section-collapse (la del minimapa): se abre al cargar, porque OpenLayers
 *    y select2 calculan su tamaño al iniciarse, y se cierra justo después de que la
 *    página haya hecho su inicialización (ready).
 *  - Al abrir una sección con data-gol-section-resize avisa con un evento resize de la
 *    ventana, para que el minimapa recalcule su tamaño.
 *  - Si el navegador marca un campo como no válido dentro de una sección cerrada, la
 *    abre para que se vea el error.
 */
(function ($) {
	'use strict';

	var PREFIX = 'gol-pg-section:';

	function storageGet(key) {
		try { return window.localStorage.getItem(key); } catch (e) { return null; }
	}
	function storageSet(key, value) {
		try { window.localStorage.setItem(key, value); } catch (e) { /* sin almacenamiento */ }
	}

	function fieldText(el) {
		var $el = $(el);
		if (el.tagName === 'SELECT') {
			var txt = $.trim($el.find('option:selected').first().text());
			return txt && txt !== '---------' ? txt : '';
		}
		if (el.type === 'checkbox' || el.type === 'radio') {
			if (!el.checked) {
				return '';
			}
			return $.trim(($el.closest('label').text() || '').replace(/\s+/g, ' '));
		}
		return $.trim($el.val() || '');
	}

	function updateMeta($section) {
		var $meta = $section.find('> summary .gol-pg-section__meta');
		if (!$meta.length) {
			return;
		}
		var parts = [];
		var fields = $section.attr('data-gol-meta-fields');
		if (fields) {
			$section.find(fields).each(function () {
				var t = fieldText(this);
				if (t) {
					parts.push(t);
				}
			});
		}
		var countSel = $section.attr('data-gol-meta-count');
		if (countSel) {
			var n = $section.find(countSel).length;
			var label = $section.attr('data-gol-meta-count-label') || '{n}';
			parts.push(label.replace('{n}', n));
		}
		var text = parts.join(' · ');
		$meta.text(text).attr('title', text);
	}

	function init(details) {
		var $section = $(details);
		if ($section.data('golSectionInit')) {
			return;
		}
		$section.data('golSectionInit', true);
		var group = $section.closest('[data-gol-sections]').attr('data-gol-sections') || 'form';
		var key = PREFIX + group + ':' + ($section.attr('data-gol-section') || '');

		if ($section.is('[data-gol-section-persist]')) {
			var saved = storageGet(key);
			if (saved === '1') {
				details.open = true;
			} else if (saved === '0') {
				details.open = false;
			}
		} else {
			details.open = true;
		}

		details.addEventListener('toggle', function () {
			if ($section.is('[data-gol-section-persist]')) {
				storageSet(key, details.open ? '1' : '0');
			}
			if (details.open && $section.is('[data-gol-section-resize]')) {
				try {
					window.dispatchEvent(new Event('resize'));
				} catch (e) {
					$(window).trigger('resize');
				}
			}
		});

		$section.on('change input dp.change', function () {
			updateMeta($section);
		});
		updateMeta($section);
	}

	$(function () {
		$('details.gol-pg-section').each(function () {
			init(this);
		});
		// Los valores que rellena el JS de la página al cargar (fecha de caducidad...)
		// y cierre de las secciones que deben quedar colapsadas tras iniciarse
		setTimeout(function () {
			$('details.gol-pg-section').each(function () {
				updateMeta($(this));
			});
			$('details.gol-pg-section[data-gol-section-collapse]').each(function () {
				this.open = false;
			});
		}, 0);
		// Un campo no válido dentro de una sección cerrada: se abre la sección
		document.addEventListener('invalid', function (e) {
			var d = e.target && e.target.closest ? e.target.closest('details.gol-pg-section') : null;
			if (d && !d.open) {
				d.open = true;
			}
		}, true);
	});

	window.GolFormSections = {updateMeta: updateMeta};
})(jQuery);
