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
 * Vista previa de imagen sin imagen (logo e imagen de proyectos y aplicaciones).
 *
 * Si la <img> de .provider-img no tiene src o no se puede cargar, se oculta y se
 * muestra en su lugar un hueco con un icono, en vez del icono de imagen rota. En cuanto
 * la imagen carga (por ejemplo, cuando el JS de la página le pone la del fichero
 * elegido) vuelve a mostrarse. Solo aspecto: no cambia el src ni los campos.
 */
(function ($) {
	'use strict';

	function init(img) {
		var $img = $(img);
		var $box = $img.parent();
		if ($box.data('golImgInit')) {
			return;
		}
		$box.data('golImgInit', true);
		var size = Math.max(parseInt(img.style.height, 10) || 0, parseInt(img.style.maxHeight, 10) || 0) || 52;
		$('<span class="gol-img-empty" aria-hidden="true"><i class="fa fa-picture-o"></i></span>')
			.css({width: size + 'px', height: size + 'px'})
			.insertAfter($img);

		function setEmpty(empty) {
			$box.toggleClass('gol-img--empty', empty);
		}
		img.addEventListener('load', function () { setEmpty(false); });
		img.addEventListener('error', function () { setEmpty(true); });
		var src = img.getAttribute('src');
		setEmpty(!src || (img.complete && img.naturalWidth === 0));
	}

	$(function () {
		$('.provider-img > img[id$="-preview"]').each(function () {
			init(this);
		});
	});
})(jQuery);
