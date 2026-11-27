/* =================================================================
   gvSIG Online - Ruta de navegación (migas de pan) de la administración

   Todas las páginas de la administración muestran una ruta que empieza
   en «Inicio». Hay dos casos:

     Página con migas propias  (ol.gol-pg-crumbs u ol.gol-sym-crumbs,
                               escritas en la plantilla o en el bloque
                               {% block breadcrumbs %}): se respetan tal
                               cual y solo se les antepone «Inicio» si no
                               lo llevan.
     Página sin migas          se generan en el hueco #gol-crumbs-slot de
                               la plantilla base a partir del menú
                               lateral: sección › subsección (enlace) ›
                               título de la página.

   La sección y la subsección salen de los elementos del menú que la
   página ya marca como activos ($('#submenu-...').addClass('active')).
   Si no marca ninguno, se busca la entrada del menú cuyo enlace sea un
   prefijo de la URL actual. Los textos son los del propio menú, así que
   ya llegan traducidos. La sección se omite si se llama igual que la
   entrada («Proyectos › Proyectos»).

   Una página puede afinar la ruta incluyendo _gol_crumbs_slot.html en su
   {% block breadcrumbs %} con estos atributos del hueco (todos opcionales):
     data-menu          id del <li> del menú al que pertenece la página
     data-parent-label  miga intermedia (y data-parent-href, su enlace)
     data-title         título de la página

   Se calcula al terminar los $(document).ready de la página y se vuelve
   a comprobar en window.load, por si alguna página marca el menú más
   tarde. No cambia nada más del DOM.
   ================================================================= */

(function (window, $) {
	'use strict';

	if (!$ || window.golBreadcrumbs) { return; }

	var TITLE_SELECTORS = [
		'.gol-pg-title',
		'.gol-sym-page-title',
		'.pl-panel__title',
		'.box-title',
		'h1', 'h2', 'h3'
	];

	function cleanText(el) {
		return $.trim($(el).text().replace(/\s+/g, ' '));
	}

	function normPath(href) {
		if (!href || href.charAt(0) === '#') { return ''; }
		var a = document.createElement('a');
		a.href = href;
		var path = a.pathname || '';
		if (path.charAt(0) !== '/') { path = '/' + path; }
		if (path.charAt(path.length - 1) !== '/') { path += '/'; }
		return path;
	}

	function currentPath() {
		return normPath(window.location.pathname);
	}

	/* «Inicio»: el primer elemento del menú lateral */
	function homeItem() {
		var $a = $('#menu-home > a').first();
		if (!$a.length) { return null; }
		return { label: cleanText($a.find('span').first()) || cleanText($a), href: $a.attr('href') };
	}

	/* Enlace de un <li> del menú, o null si no es navegable (href="#") */
	function linkOf($li) {
		var $a = $li.children('a').first();
		var href = $a.attr('href');
		return (href && href !== '#' && href.indexOf('javascript:') !== 0) ? href : null;
	}

	function labelOf($li) {
		var $a = $li.children('a').first();
		var $span = $a.children('span').first();
		return $span.length ? cleanText($span) : cleanText($a);
	}

	/* Busca en el menú la entrada cuyo enlace sea el prefijo más largo de la URL */
	function findByUrl($menu, path) {
		var best = null, bestLen = 0;
		$menu.find('li').each(function () {
			var $li = $(this);
			if ($li.attr('id') === 'menu-home') { return; }
			var p = normPath(linkOf($li));
			if (p && p.length > bestLen && path.indexOf(p) === 0) {
				best = $li;
				bestLen = p.length;
			}
		});
		return best;
	}

	/* Sección y subsección activas como lista de {label, href} */
	function menuTrail($slot) {
		var $menu = $('#admin-left-menu');
		if (!$menu.length) { return []; }

		var $leaf = $();
		var forced = $slot.attr('data-menu');
		if (forced) { $leaf = $menu.find('li').filter(function () { return this.id === forced; }).first(); }
		if (!$leaf.length) { $leaf = $menu.find('.treeview-menu > li.active').first(); }
		if (!$leaf.length) {
			$leaf = $menu.children('li.active').not('#menu-home').first();
		}
		if (!$leaf.length) {
			$leaf = findByUrl($menu, currentPath());
		}
		if (!$leaf || !$leaf.length) { return []; }

		var trail = [];
		var leaf = { label: labelOf($leaf), href: linkOf($leaf) };
		var $section = $leaf.parent('.treeview-menu').closest('li');
		// «Proyectos › Proyectos»: la sección sobra si se llama igual que la entrada
		if ($section.length && labelOf($section).toLowerCase() !== leaf.label.toLowerCase()) {
			trail.push({ label: labelOf($section), href: linkOf($section) });
		}
		trail.push(leaf);
		return trail;
	}

	/* Título visible de la página (fuera de las ventanas modales) */
	function pageTitle($content) {
		for (var i = 0; i < TITLE_SELECTORS.length; i++) {
			var found = null;
			$content.find(TITLE_SELECTORS[i]).each(function () {
				if ($(this).closest('.modal, nav, #gol-crumbs-slot').length) { return; }
				var text = cleanText(this);
				if (text) { found = text; return false; }
			});
			if (found) { return found; }
		}
		return null;
	}

	function buildTrail($content, $slot) {
		var home = homeItem();
		if (!home) { return null; }
		var path = currentPath();
		if (normPath(home.href) === path) { return null; } // portada

		var trail = [home].concat(menuTrail($slot));
		var parentLabel = $.trim($slot.attr('data-parent-label') || '');
		if (parentLabel) {
			trail.push({ label: parentLabel, href: $slot.attr('data-parent-href') || null });
		}
		var last = trail[trail.length - 1];

		// En la página a la que lleva la última miga, esa miga es la página actual
		if (last.href && normPath(last.href) === path) {
			last.href = null;
		} else {
			var title = $.trim($slot.attr('data-title') || '') || pageTitle($content);
			if (title && title.toLowerCase() !== last.label.toLowerCase()) {
				trail.push({ label: title, href: null });
			} else {
				last.href = null;
			}
		}
		return trail;
	}

	function render(trail) {
		var $ol = $('<ol class="gol-pg-crumbs"></ol>');
		$.each(trail, function (i, item) {
			var $li = $('<li></li>');
			if (i === trail.length - 1) {
				$li.attr('aria-current', 'page').text(item.label);
			} else if (item.href) {
				$li.append($('<a></a>').attr('href', item.href).text(item.label));
			} else {
				$li.text(item.label);
			}
			$ol.append($li);
		});
		return $ol;
	}

	/* Migas escritas en la plantilla: solo se les antepone «Inicio» */
	function completeExisting($lists) {
		var home = homeItem();
		if (!home) { return; }
		$lists.each(function () {
			var $ol = $(this);
			if ($ol.data('golHome')) { return; }
			var first = cleanText($ol.children('li').first());
			if (first.toLowerCase() !== home.label.toLowerCase()) {
				$ol.prepend($('<li></li>').append($('<a></a>').attr('href', home.href).text(home.label)));
			}
			$ol.data('golHome', true);
		});
	}

	function run() {
		var $content = $('#base-content-wrapper > .content');
		if (!$content.length) { return; }
		var $slot = $('#gol-crumbs-slot');

		var $own = $content.find('ol.gol-pg-crumbs, ol.gol-sym-crumbs').filter(function () {
			return !$(this).closest('#gol-crumbs-slot').length;
		});
		if ($own.length) {
			$slot.empty().prop('hidden', true);
			completeExisting($own);
			return;
		}
		if (!$slot.length) { return; }

		var trail = buildTrail($content, $slot);
		if (!trail || trail.length < 2) {
			$slot.empty().prop('hidden', true);
			return;
		}
		var key = $.map(trail, function (t) { return t.label + '|' + (t.href || ''); }).join('>');
		if ($slot.data('golKey') === key) { return; }
		$slot.data('golKey', key).empty().append(render(trail)).prop('hidden', false);
	}

	window.golBreadcrumbs = { refresh: run };

	$(function () { window.setTimeout(run, 0); });
	$(window).on('load', run);

})(window, window.jQuery);
