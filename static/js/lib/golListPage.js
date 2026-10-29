/* =================================================================
   gvSIG Online - Inicializador unico de las tablas de los listados

   Antes cada listado repetia la misma receta de DataTables (unas 20
   lineas, con el bloque de textos identico en 17 plantillas). Aqui queda
   una sola, con dos modos:

     client  DataTables filtra, cuenta y pagina.
     server  Django ya lo hace; DataTables solo ordena la pagina visible.

   Una tabla que use el propio serverSide de DataTables (user_list pide los
   datos por AJAX) va en modo cliente: es DataTables quien sigue gestionando
   pie y busqueda, solo que pidiendo al servidor. Basta pasarle serverSide y
   ajax dentro de dt.

   En todos los casos el buscador vive en la cabecera del panel, no en la
   maqueta de DataTables, para que las familias se vean igual. No filtra
   mientras se escribe: cada letra redibujaba la tabla (o recargaba la
   pagina, en modo servidor) y Chrome se comia las teclas siguientes. El
   filtro se aplica al pulsar la lupa o Enter, igual que antes.

   Los textos llegan en window.GOL_DT_LANG desde _gol_datatables_lang.html.
   ================================================================= */

(function (window, $) {
	'use strict';

	/* El buscador y el selector de tamano son marcado propio de la cabecera,
	   asi que no se piden a DataTables ('l' y 'f'). En modo cliente el pie
	   agrupa recuento y paginas en una sola franja. */
	function layoutFor(mode) {
		return mode === 'server' ? 't' : 't<"pl-panel__foot"ip>';
	}

	function bindHeaderSearch(table, $panel) {
		var $form = $panel.find('.pl-search-form').first();
		if (!$form.length) { return; }
		var $input = $form.find('input[type="text"]').first();
		var $clear = $form.find('.btn-clear');

		/* En los listados que pagina Django el boton de limpiar solo aparece si
		   hay busqueda, porque lo decide la plantilla. Aqui se replica. */
		function syncClear() { $clear.toggle(!!$input.val()); }
		syncClear();

		function aplicar() {
			table.search($input.val()).draw();
			syncClear();
		}

		/* El mismo marcado se usa en los listados que filtran en servidor, donde
		   el formulario si navega. Aqui el filtrado es en cliente, luego se
		   impide el envio para no recargar la pagina. La lupa es type=submit,
		   asi que este handler cubre el clic y el Enter. */
		$input.on('input', syncClear);
		$form.on('submit', function (e) {
			e.preventDefault();
			aplicar();
		});

		$clear.on('click', function (e) {
			e.preventDefault();
			$input.val('');
			aplicar();
		});
	}

	/* Modo servidor: filtra Django, luego el buscador no puede tocar la tabla,
	   tiene que navegar. Solo al confirmar: una recarga a medias de escribir
	   sustituye el input por el texto que ya se habia enviado y se pierde el
	   resto. */
	function bindServerSearch($panel) {
		var $form = $panel.find('.pl-search-form').first();
		if (!$form.length) { return; }
		var $input = $form.find('input[name="search"]').first();
		if (!$input.length) { return; }
		/* Sin URLSearchParams se deja el formulario como estaba: envia solo sus
		   campos, que es el comportamiento de siempre. */
		if (!window.URLSearchParams) { return; }

		var $icono = $form.find('.btn-search').find('i');
		var navegando = false;

		/* La query se construye sobre la actual y no enviando el formulario,
		   porque un submit solo manda sus propios campos y perderia los filtros
		   que viven en la URL, como el project_id de layer_list. */
		function navegar() {
			if (navegando) { return; }
			navegando = true;

			var params = new window.URLSearchParams(window.location.search);
			var valor = $input.val() || '';
			if (valor) { params.set('search', valor); } else { params.delete('search'); }
			/* Volver al principio: la pagina 5 del listado completo casi nunca
			   existe en el filtrado. */
			params.delete('page');

			$icono.removeClass('fa-search').addClass('fa-spinner fa-spin');

			var query = params.toString();
			window.location.assign(query ? '?' + query : window.location.pathname);
		}

		/* Cubre tanto el boton de la lupa como el Enter. */
		$form.on('submit', function (e) {
			e.preventDefault();
			navegar();
		});
	}

	/**
	 * @param {string} selector  tabla a inicializar
	 * @param {Object} [opts]    mode: 'client' | 'server'
	 *                           dt:   opciones propias de la pagina
	 *                                 (columnDefs, order, select...)
	 */
	window.golListTable = function (selector, opts) {
		opts = opts || {};
		var mode = opts.mode === 'server' ? 'server' : 'client';
		var $table = $(selector);
		if (!$table.length) { return null; }

		var conf = $.extend(true, {
			responsive: true,
			lengthChange: false,
			language: window.GOL_DT_LANG || {},
			dom: layoutFor(mode)
		}, opts.dt || {});

		if (mode === 'server') {
			conf.paging = false;
			conf.searching = false;
			conf.info = false;
		}

		var table = $table.DataTable(conf);
		if (mode === 'client') {
			/* Normalmente la cabecera es la del panel, pero cache_list lleva una
			   tabla por pestana y ahi el ambito es el .tab-pane. */
			bindHeaderSearch(table, $table.closest('.pl-panel, .tab-pane'));
		} else {
			bindServerSearch($table.closest('.pl-panel'));
		}
		return table;
	};
})(window, jQuery);
