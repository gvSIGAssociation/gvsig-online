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
   maqueta de DataTables, para que las familias se vean igual, y filtra conforme
   se escribe: en cliente tocando la tabla, en servidor navegando a la query.

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

	/* Marca que la recarga la ha provocado el propio buscador. Solo entonces se
	   devuelve el foco al input. */
	var FOCO_PENDIENTE = 'golListSearchFocus';

	/* Tras la recarga el input vuelve con el texto, que lo pinta la plantilla,
	   pero sin foco, y sin foco no se puede seguir escribiendo. No se devuelve
	   a quien llega desde un enlace con ?search=, que no estaba escribiendo. */
	function restaurarFoco($input) {
		var marca = null;
		try {
			marca = window.sessionStorage.getItem(FOCO_PENDIENTE);
			window.sessionStorage.removeItem(FOCO_PENDIENTE);
		} catch (e) { return; }
		if (!marca) { return; }

		var nodo = $input.get(0);
		var largo = ($input.val() || '').length;
		$input.focus();
		/* Sin esto el texto queda seleccionado y la siguiente tecla lo borra. */
		if (nodo.setSelectionRange) { nodo.setSelectionRange(largo, largo); }
	}

	/* Modo servidor: filtra Django, luego el buscador no puede tocar la tabla,
	   tiene que navegar. Se espera a que el usuario pare de escribir igual que
	   en el modo AJAX, solo que aqui cada viaje recarga la pagina entera. */
	function bindServerSearch($panel, delay) {
		var $form = $panel.find('.pl-search-form').first();
		if (!$form.length) { return; }
		var $input = $form.find('input[name="search"]').first();
		if (!$input.length) { return; }
		/* Sin URLSearchParams se deja el formulario como estaba: envia solo sus
		   campos, que es el comportamiento de siempre. */
		if (!window.URLSearchParams) { return; }

		var $icono = $form.find('.btn-search').find('i');
		var inicial = $input.val() || '';
		var espera = null;

		restaurarFoco($input);

		/* La query se construye sobre la actual y no enviando el formulario,
		   porque un submit solo manda sus propios campos y perderia los filtros
		   que viven en la URL, como el project_id de layer_list. */
		function navegar() {
			var params = new window.URLSearchParams(window.location.search);
			var valor = $input.val() || '';
			if (valor) { params.set('search', valor); } else { params.delete('search'); }
			/* Volver al principio: la pagina 5 del listado completo casi nunca
			   existe en el filtrado. */
			params.delete('page');

			try { window.sessionStorage.setItem(FOCO_PENDIENTE, '1'); } catch (e) {}
			$icono.removeClass('fa-search').addClass('fa-spinner fa-spin');

			var query = params.toString();
			window.location.replace(query ? '?' + query : window.location.pathname);
		}

		function cancelar() {
			if (espera) { window.clearTimeout(espera); espera = null; }
		}

		$input.on('input', function () {
			cancelar();
			espera = window.setTimeout(function () {
				/* Escribir y deshacer no debe costar una recarga. */
				if (($input.val() || '') === inicial) { return; }
				navegar();
			}, delay);
		});

		/* Cubre tanto el boton de la lupa como el Enter, y a diferencia del
		   temporizador navega aunque el texto no haya cambiado. */
		$form.on('submit', function (e) {
			e.preventDefault();
			cancelar();
			navegar();
		});
	}

	/**
	 * @param {string} selector  tabla a inicializar
	 * @param {Object} [opts]    mode: 'client' | 'server'
	 *                           dt:   opciones propias de la pagina
	 *                                 (columnDefs, order, select...)
	 *                           searchDelay: espera del buscador en modo
	 *                                 servidor, en ms
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
		} else {
			bindServerSearch($table.closest('.pl-panel'), opts.searchDelay || 400);
		}
		return table;
	};
})(window, jQuery);
