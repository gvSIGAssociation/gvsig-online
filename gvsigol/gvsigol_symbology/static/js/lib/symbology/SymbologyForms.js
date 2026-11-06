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
 * Ayudas de los formularios sencillos de simbología (solo aspecto).
 *
 * Campo «Nombre» (input[data-gol-sym-name]): indica mientras se escribe si el nombre es
 * válido (^[a-z0-9_]+$, la misma regla que el servidor) y, si no lo es, propone uno
 * válido que el usuario puede aplicar con un clic. Nunca cambia el valor por su cuenta
 * ni impide enviar el formulario: el servidor sigue validando como siempre.
 */
var SymbologyForms = (function($) {
	var NAME_RE = /^[a-z0-9_]+$/;

	function t(msgid) {
		return (typeof pgettext === 'function') ? pgettext('symbology', msgid) : gettext(msgid);
	}

	/** «Mi Biblioteca (2024)» -> «mi_biblioteca_2024» */
	function suggestName(value) {
		var s = String(value || '');
		if (s.normalize) {
			s = s.normalize('NFD').replace(/[̀-ͯ]/g, '');
		}
		s = s.toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/_+/g, '_').replace(/^_+|_+$/g, '');
		return s.substring(0, 100);
	}

	function render($input, $status) {
		var value = $input.val();
		$status.empty().removeClass('is-valid is-invalid');
		$input.removeClass('gol-sym-input-valid gol-sym-input-invalid').removeAttr('aria-invalid');
		if (!value) {
			return;
		}
		if (NAME_RE.test(value)) {
			$input.addClass('gol-sym-input-valid');
			$status.addClass('is-valid').append($('<i class="fa fa-check-circle" aria-hidden="true"></i>'), document.createTextNode(' ' + t('Valid name')));
			return;
		}
		$input.addClass('gol-sym-input-invalid').attr('aria-invalid', 'true');
		$status.addClass('is-invalid').append($('<i class="fa fa-exclamation-circle" aria-hidden="true"></i>'), document.createTextNode(' ' + t('This name is not valid.') + ' '));
		var suggestion = suggestName(value);
		if (suggestion) {
			var $fix = $('<button type="button" class="gol-sym-name-fix"></button>');
			$fix.text(t('Use') + ' «' + suggestion + '»');
			$fix.on('click', function() {
				$input.val(suggestion).trigger('input').trigger('focus');
			});
			$status.append($fix);
		}
	}

	function initNameField(input) {
		var $input = $(input);
		if ($input.data('golSymNameInit')) {
			return;
		}
		$input.data('golSymNameInit', true);
		var $status = $('<p class="gol-sym-name-status" aria-live="polite"></p>');
		var $hint = $input.siblings('.gol-sym-field-hint').first();
		if ($hint.length) {
			$hint.after($status);
		} else {
			$input.after($status);
		}
		$input.on('input change', function() {
			render($input, $status);
		});
		render($input, $status);
	}

	/**
	 * Edición en línea de la descripción en la cabecera de las páginas de detalle
	 * (form[data-gol-sym-inline-edit]): «Editar descripción» muestra el área de texto en el
	 * sitio del texto; Cancelar (o Escape) la oculta y devuelve el valor original. Es el mismo
	 * formulario de siempre: se envía con su botón Guardar.
	 */
	function initInlineEdit(form) {
		var $form = $(form);
		if ($form.data('golSymInlineInit')) {
			return;
		}
		$form.data('golSymInlineInit', true);
		var $view = $form.find('.gol-sym-inline-edit__view');
		var $editor = $form.find('.gol-sym-inline-edit__editor');
		var $field = $editor.find('textarea').first();
		var original = $field.val();

		function open() {
			$view.prop('hidden', true);
			$editor.prop('hidden', false);
			$form.addClass('is-editing');
			var el = $field.get(0);
			if (el) {
				el.focus();
				if (el.setSelectionRange) {
					el.setSelectionRange(el.value.length, el.value.length);
				}
			}
		}
		function close() {
			$field.val(original);
			$editor.prop('hidden', true);
			$view.prop('hidden', false);
			$form.removeClass('is-editing');
			$form.find('.gol-sym-inline-edit__open').trigger('focus');
		}
		$form.on('click', '.gol-sym-inline-edit__open', function(e) {
			e.preventDefault();
			open();
		});
		$form.on('click', '.gol-sym-inline-edit__cancel', function(e) {
			e.preventDefault();
			close();
		});
		$field.on('keydown', function(e) {
			if (e.key === 'Escape' || e.keyCode === 27) {
				e.preventDefault();
				close();
			}
		});
		// Con un error del servidor el editor se abre ya desplegado
		if ($form.is('[data-open]')) {
			open();
		}
	}

	$(function() {
		$('input[data-gol-sym-name]').each(function() {
			initNameField(this);
		});
		$('form[data-gol-sym-inline-edit]').each(function() {
			initInlineEdit(this);
		});
	});

	return {suggestName: suggestName, initNameField: initNameField, initInlineEdit: initInlineEdit};
})(jQuery);
