/**
 * Cabecera de los nodos del editor ETL.
 *
 * - Cada nodo lleva un id corto (n1, n2…) visible en la cabecera. Es el mismo id que usa el
 *   asistente para referirse a las tareas, así el usuario sabe de qué nodo habla.
 *   El id se guarda con el workspace (memento.alias) y no cambia al borrar otros nodos.
 * - El engranaje y el id se anclan al borde derecho de la cabecera, y el título reserva ese hueco
 *   con su padding derecho, de modo que nunca se solapan por largo que sea el título.
 *
 * Se carga justo después de draw2d.js: envuelve draw2d.Canvas.prototype.add, por donde pasan
 * todas las altas de figuras (soltar desde la barra, cargar un workspace, asistente, deshacer).
 */
var ETL_ALIAS_RE = /^n([1-9]\d*)$/;
var ETL_HEADER_GAP = 6;        // separación entre título, id y engranaje
var ETL_HEADER_EDGE = 10;      // margen derecho (igual que el padding original)

/** Número de un alias válido ('n12' -> 12) o 0 si no lo es. */
function etlAliasNumber(alias) {
	var m = ETL_ALIAS_RE.exec(typeof alias === 'string' ? alias : '');
	return m ? parseInt(m[1], 10) : 0;
}

/** Alias que llega en un documento guardado o del asistente: 'alias' o un id con forma nN. */
function etlAliasFromDocument(doc) {
	if (!doc) {
		return null;
	}
	if (etlAliasNumber(doc.alias)) {
		return doc.alias;
	}
	if (etlAliasNumber(doc.id)) {
		return doc.id;
	}
	return null;
}

/** ¿Es una figura de nodo ETL (con cabecera)? */
function etlIsNodeFigure(figure) {
	return !!(figure && figure.classLabel && typeof figure.classLabel.getText === 'function');
}

/** Alias en uso en el canvas, sin contar 'except'. */
function etlUsedAliases(canvas, except) {
	var used = {};
	if (canvas && typeof canvas.getFigures === 'function') {
		canvas.getFigures().each(function (i, figure) {
			if (figure !== except && figure.etlAlias) {
				used[figure.etlAlias] = true;
			}
		});
	}
	return used;
}

/**
 * Siguiente alias libre: uno más que el mayor usado en este canvas (incluidos los ya borrados
 * mientras el editor está abierto), para que un id no pase a designar otro nodo distinto.
 */
function etlNextAlias(canvas, used) {
	var top = (canvas && canvas._etlAliasTop) || 0;
	Object.keys(used || {}).forEach(function (alias) {
		top = Math.max(top, etlAliasNumber(alias));
	});
	return 'n' + (top + 1);
}

/** Da a la figura su alias definitivo antes de entrar en el canvas. */
function etlAssignAlias(canvas, figure) {
	var used = etlUsedAliases(canvas, figure);
	var alias = figure.etlAlias;
	if (!etlAliasNumber(alias) || used[alias]) {
		alias = etlNextAlias(canvas, used);
	}
	figure.etlAlias = alias;
	if (canvas) {
		canvas._etlAliasTop = Math.max(canvas._etlAliasTop || 0, etlAliasNumber(alias));
	}
	return alias;
}

/** Ancho que ocupa el id; si draw2d aún no lo ha medido, una estimación por caracteres. */
function etlBadgeWidth(badge) {
	var measured = (badge && typeof badge.getWidth === 'function') ? badge.getWidth() : 0;
	var estimate = 8 + 6.5 * String((badge && badge.getText && badge.getText()) || '').length;
	return (measured && isFinite(measured) && measured > 4) ? measured : Math.ceil(estimate);
}

/** Padding derecho del título para que quepan el id y el engranaje. */
function etlHeaderRightPadding(badgeWidth, gearWidth) {
	return ETL_HEADER_EDGE + gearWidth + ETL_HEADER_GAP + badgeWidth + ETL_HEADER_GAP;
}

/** Locator anclado al borde derecho del padre y centrado en vertical. */
var EtlRightLocator = null;
function etlRightLocator(offset) {
	if (!EtlRightLocator) {
		EtlRightLocator = draw2d.layout.locator.Locator.extend({
			NAME: 'EtlRightLocator',
			init: function (offsetFn) {
				this._super();
				this.offsetFn = offsetFn;
			},
			relocate: function (index, target) {
				var parent = target.getParent();
				var x = parent.getWidth() - this.offsetFn(target);
				var y = Math.round((parent.getHeight() - target.getHeight()) / 2);
				target.setPosition(Math.max(0, x), Math.max(0, y));
			}
		});
	}
	return new EtlRightLocator(offset);
}

function etlFindGear(label) {
	var entry = null;
	if (label && label.children && typeof label.children.each === 'function') {
		label.children.each(function (i, e) {
			if (!entry && e.figure instanceof draw2d.shape.icon.Icon) {
				entry = e;
			}
		});
	}
	return entry;
}

/** Reajusta el padding del título al ancho actual del id. */
function etlLayoutHeader(figure) {
	var header = figure._etlHeader;
	if (!header) {
		return;
	}
	var label = figure.classLabel;
	var padding = etlHeaderRightPadding(etlBadgeWidth(header.badge), header.gearWidth);
	if (!label.padding || label.padding.right !== padding) {
		label.setPadding({right: padding});
		label.fireEvent('resize');
		if (label.getParent && label.getParent()) {
			label.getParent().repaint();
		}
	}
}

/** Coloca el id y reubica el engranaje (una sola vez por figura). */
function etlDecorateHeader(figure) {
	var label = figure.classLabel;
	if (figure._etlHeader) {
		if (figure._etlHeader.badge.getText() !== figure.etlAlias) {
			figure._etlHeader.badge.setText(figure.etlAlias);
		}
		etlLayoutHeader(figure);
		return;
	}
	var gearEntry = etlFindGear(label);
	var gearWidth = gearEntry ? gearEntry.figure.getWidth() : 0;
	var badge = new draw2d.shape.basic.Label({
		text: figure.etlAlias,
		fontSize: 10,
		bold: true,
		fontColor: '#37474f',
		bgColor: '#ffffff',
		stroke: 0,
		radius: 3,
		padding: {top: 1, right: 4, bottom: 1, left: 4}
	});
	if (typeof badge.setUserData === 'function') {
		badge.setUserData({etlAliasBadge: true});
	}
	figure._etlHeader = {badge: badge, gearWidth: gearWidth};
	if (gearEntry) {
		// El engranaje es el mismo objeto: conserva su manejador de clic y su color.
		gearEntry.locator = etlRightLocator(function (target) {
			return ETL_HEADER_EDGE + target.getWidth();
		});
	}
	label.add(badge, etlRightLocator(function (target) {
		return ETL_HEADER_EDGE + gearWidth + ETL_HEADER_GAP + target.getWidth();
	}));
	// El id cambia de ancho al pasar de n9 a n10: se recoloca y se reserva hueco otra vez.
	badge.on('resize', function () {
		etlLayoutHeader(figure);
	});
	etlLayoutHeader(figure);
}

if (typeof draw2d !== 'undefined' && draw2d.Canvas && draw2d.Canvas.prototype.add &&
		!draw2d.Canvas.prototype._etlAddWrapped) {
	(function () {
		var originalAdd = draw2d.Canvas.prototype.add;
		draw2d.Canvas.prototype.add = function (figure) {
			var node = etlIsNodeFigure(figure) && figure.getCanvas() !== this;
			if (node) {
				etlAssignAlias(this, figure);
			}
			var result = originalAdd.apply(this, arguments);
			if (node) {
				try {
					etlDecorateHeader(figure);
				} catch (e) {
					// La cabecera es solo visual: un fallo aquí no debe impedir trabajar con el nodo.
					if (window.console) {
						console.warn('etl: cabecera del nodo', e);
					}
				}
			}
			return result;
		};
		draw2d.Canvas.prototype._etlAddWrapped = true;
	})();
}
