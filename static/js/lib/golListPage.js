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
   maqueta de DataTables, para que las familias se vean igual.

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

	function bindHeaderSearch(table, $panel, delay) {
		var $form = $panel.find('.pl-search-form').first();
		if (!$form.length) { return; }
		var $input = $form.find('input[type="text"]').first();
		var $clear = $form.find('.btn-clear');
		var espera = null;

		/* En los listados que pagina Django el boton de limpiar solo aparece si
		   hay busqueda, porque lo decide la plantilla. Aqui se replica. */
		function syncClear() { $clear.toggle(!!$input.val()); }
		syncClear();

		/* El mismo marcado se usa en los listados que filtran en servidor, donde
		   el formulario si navega. Aqui el filtrado es en cliente, luego se
		   impide el envio para no recargar la pagina. */
		$form.on('submit', function (e) { e.preventDefault(); });

		/* Si la tabla pide los datos al servidor, cada tecla seria una peticion:
		   se espera a que el usuario pare de escribir. Filtrando en cliente no
		   hace falta y responde al instante. */
		$input.on('input', function () {
			var valor = this.value;
			syncClear();
			if (!delay) { table.search(valor).draw(); return; }
			if (espera) { window.clearTimeout(espera); }
			espera = window.setTimeout(function () { table.search(valor).draw(); }, delay);
		});

		$form.find('.btn-search').on('click', function (e) {
			e.preventDefault();
			if (espera) { window.clearTimeout(espera); }
			table.search($input.val()).draw();
		});

		$clear.on('click', function (e) {
			e.preventDefault();
			if (espera) { window.clearTimeout(espera); }
			$input.val('');
			table.search('').draw();
			syncClear();
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
			bindHeaderSearch(table, $table.closest('.pl-panel, .tab-pane'),
			                 conf.serverSide ? 300 : 0);
		}
		return table;
	};
})(window, jQuery);
