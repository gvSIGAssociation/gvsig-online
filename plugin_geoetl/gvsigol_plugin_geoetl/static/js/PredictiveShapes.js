/* global draw2d, $, gettext, jsonParams, listLabel, getPerAttr, isAlreadyInCanvas, setColorIfIsOpened,
   passSchemaWhenInputTask, passSchemaToEdgeConnected, propagateSchemaFrom, getTaskParamsEntry,
   schemaAsColumnList, SCHEMA_HANDLERS, paramsTransTpl, fm_directory, messageBox, Cookies,
   editablerestrictedly */

/**
 * Nodos predictivos y ráster del editor ETL:
 *   input_Raster, trans_RasterSample, trans_RandomForest, trans_RasterPredict,
 *   trans_RasterPolygonize, output_RasterPublish.
 *
 * Se carga DESPUÉS de TableShape.js y SchemaPropagator.js. En lugar de repetir ~200 líneas de
 * plantilla por nodo, defineEtlNode() construye la figura draw2d a partir de una descripción.
 *
 * Convenciones del editor que se respetan:
 *  - Los campos del diálogo se llaman "<parametro>-<idFigura>" (así los rellena la carga de workspaces).
 *  - Al abrir el diálogo se reconstruye todo desde jsonParams + el esquema actual, de modo que no
 *    se depende de cómo la carga genérica rellene selects y casillas.
 *  - Cada arista lleva el esquema (lista de nombres) de lo que transporta: columnas para una tabla,
 *    bandas para un ráster, variables para un modelo.
 */

/* ------------------------------------------------------------------ */
/* Lógica pura (sin draw2d): probada con node, ver tests/js            */
/* ------------------------------------------------------------------ */

var ETL_PORT_KINDS = {
    table: {color: null, label: 'Table'},
    raster: {color: '#c2185b', label: 'Raster'},
    model: {color: '#7e57c2', label: 'Model'}
};

/** Tipo de dato que transporta un puerto; los puertos de los nodos antiguos son tablas. */
function etlKindOfPort(port) {
    return (port && port.etlKind) || 'table';
}

/** Una conexión solo es válida entre puertos del mismo tipo (tabla-tabla, ráster-ráster, modelo-modelo). */
function etlCheckPortKinds(sourceKind, targetKind) {
    if (sourceKind === targetKind) {
        return {ok: true};
    }
    var names = {table: gettext('a table'), raster: gettext('a raster'), model: gettext('a model')};
    return {
        ok: false,
        message: gettext('Cannot connect {source} to an input that expects {target}.')
            .replace('{source}', names[sourceKind] || sourceKind)
            .replace('{target}', names[targetKind] || targetKind)
    };
}

/**
 * Veta la conexión ANTES de que se dibuje: draw2d llama a Port.createCommand al soltar el cable y
 * un null cancela la conexión. Se parchean InputPort y OutputPort una sola vez.
 */
function etlInstallConnectionGuard() {
    if (typeof draw2d === 'undefined' || !draw2d.InputPort || draw2d.InputPort.prototype.etlGuarded) {
        return;
    }
    [draw2d.InputPort, draw2d.OutputPort].forEach(function (PortClass) {
        var original = PortClass.prototype.createCommand;
        PortClass.prototype.createCommand = function (request) {
            if (request && request.getPolicy && request.getPolicy() === draw2d.command.CommandType.CONNECT) {
                var verdict = etlCheckPortKinds(etlKindOfPort(request.source), etlKindOfPort(request.target));
                if (!verdict.ok) {
                    if (typeof messageBox !== 'undefined') {
                        messageBox.show('warning', verdict.message);
                    }
                    return null;
                }
            }
            return original.apply(this, arguments);
        };
        PortClass.prototype.etlGuarded = true;
    });
}

/** Valida una conexión draw2d ya creada (p. ej. al cargar un workspace). */
function etlValidateConnection(connection) {
    var source = connection && (connection.getSource ? connection.getSource() : connection.sourcePort);
    var target = connection && (connection.getTarget ? connection.getTarget() : connection.targetPort);
    if (!source || !target) {
        return {ok: true};
    }
    return etlCheckPortKinds(etlKindOfPort(source), etlKindOfPort(target));
}

/**
 * Esquemas por puerto de entrada. passSchemaWhenInputTask devuelve una lista plana con un solo
 * puerto y una lista de listas con varios; aquí siempre se obtiene un array de n listas.
 */
function etlPerPortSchemas(raw, n) {
    var out = [];
    if (n === 1) {
        out.push(Array.isArray(raw) ? (Array.isArray(raw[0]) ? raw[0].slice() : raw.slice()) : []);
        return out;
    }
    for (var i = 0; i < n; i++) {
        out.push(Array.isArray(raw) && Array.isArray(raw[i]) ? raw[i].slice() : []);
    }
    return out;
}

/** Columnas que no se ofrecen como atributos de usuario. */
var ETL_HIDDEN_COLUMNS = ['wkb_geometry', 'ogc_fid', 'geometry', 'geom'];

function etlUserColumns(columns) {
    return (columns || []).filter(function (c) {
        return ETL_HIDDEN_COLUMNS.indexOf(String(c).toLowerCase()) === -1;
    });
}

function etlUnique(list) {
    return list.filter(function (item, i) {
        return list.indexOf(item) === i;
    });
}

function etlEscape(text) {
    return String(text === undefined || text === null ? '' : text)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

/** Entero opcional: '' -> null; no numérico o fuera de rango -> undefined (error). */
function etlParseInt(text, min, max) {
    if (text === undefined || text === null || String(text).trim() === '') {
        return null;
    }
    var n = Number(text);
    if (!isFinite(n) || Math.floor(n) !== n || n < min || (max !== undefined && n > max)) {
        return undefined;
    }
    return n;
}

function etlParseFloat(text, min) {
    if (text === undefined || text === null || String(text).trim() === '') {
        return null;
    }
    var n = Number(String(text).replace(',', '.'));
    if (!isFinite(n) || n < min) {
        return undefined;
    }
    return n;
}

/** Nombre de capa válido, igual que el backend: minúsculas, dígitos y guion bajo. */
function etlSafeLayerName(text) {
    var t = String(text || '').normalize('NFKD').replace(/[̀-ͯ]/g, '')
        .replace(/[^0-9a-zA-Z_]+/g, '_').replace(/^_+|_+$/g, '').toLowerCase();
    if (t && /^[0-9]/.test(t)) {
        t = 'l_' + t;
    }
    return t.substring(0, 60);
}

/* ---------- Esquemas de salida (también los usa el propagador) ---------- */

var ETL_PIXEL_REPORT_COLUMNS = ['section', 'name', 'value'];
var ETL_POLYGON_COLUMNS = ['class_name', 'class_code', 'area', 'wkb_geometry'];

function etlSampleOutput(inputs, p) {
    var bands = inputs[0] || [];
    return etlUnique(bands.concat(p && p['class-attr'] ? [p['class-attr']] : []));
}

// La matriz de confusión añade además una columna pred_<clase> por cada clase, que solo se conoce al ejecutar
var ETL_MATRIX_COLUMNS = ['real', 'total', 'recall'];

function etlForestOutput(inputs, p) {
    return [ETL_PIXEL_REPORT_COLUMNS.slice(), (p && p.features) ? p.features.slice() : [], ETL_MATRIX_COLUMNS.slice()];
}

/** Nombre de banda como lo deja el servidor: minúsculas, dígitos y guion bajo, y único en la lista. */
function etlBandName(text, existing) {
    var t = String(text || '').normalize('NFKD').replace(/[̀-ͯ]/g, '')
        .replace(/[^0-9a-zA-Z_]+/g, '_').replace(/^_+|_+$/g, '').toLowerCase();
    if (!t || /^[0-9]/.test(t)) {
        t = 'b_' + t;
    }
    var name = t, n = 2;
    while ((existing || []).indexOf(name) !== -1) {
        name = t + '_' + n;
        n += 1;
    }
    return name;
}


/** Nombre de modelo como lo deja el servidor: minúsculas, dígitos y guion bajo (máx. 60). */
function etlSafeModelName(text) {
    var t = String(text || '').normalize('NFKD').replace(/[̀-ͯ]/g, '')
        .replace(/[^0-9a-zA-Z_]+/g, '_').replace(/^_+|_+$/g, '').toLowerCase();
    if (t && /^[0-9]/.test(t)) {
        t = 'm_' + t;
    }
    return t.substring(0, 60);
}

/** Nombres de banda de varios ráster combinados (una lista por entrada conectada), como los deja el servidor. */
function etlStackBands(perInput, prefixes) {
    var out = [];
    var connected = 0;
    perInput.forEach(function (bands) {
        if (!bands || !bands.length) {
            return;
        }
        var prefix = String((prefixes || [])[connected] || '').trim();
        connected += 1;
        bands.forEach(function (name) {
            out.push(etlBandName(prefix ? prefix + '_' + name : name, out));
        });
    });
    return out;
}

/** Índices espectrales: papel de cada banda, en el orden de los parámetros band-1, band-2, band-3. */
var ETL_INDICES = {
    ndvi: {roles: ['nir', 'red'], needsDifferent: true},
    ndwi: {roles: ['green', 'nir'], needsDifferent: true},
    ndbi: {roles: ['swir', 'nir'], needsDifferent: true},
    savi: {roles: ['nir', 'red'], needsDifferent: true},
    evi: {roles: ['nir', 'red', 'blue'], needsDifferent: true},
    brightness: {roles: [], needsDifferent: false},
    nd: {roles: ['a', 'b'], needsDifferent: true}
};

var ETL_BAND_PATTERNS = {
    nir: /(^|_)(nir|ir|infrarrojo|infrared)(_|$)|^b0?8a?$/,
    red: /(^|_)(red|rojo|r)(_|$)|^b0?4$/,
    green: /(^|_)(green|verde|g)(_|$)|^b0?3$/,
    blue: /(^|_)(blue|azul|b)(_|$)|^b0?2$/,
    swir: /swir|^b(11|12)$/
};

/** Banda que probablemente cumple un papel según su nombre ('' si no se reconoce). */
function etlGuessBand(role, names) {
    var pattern = ETL_BAND_PATTERNS[role];
    if (!pattern) {
        return '';
    }
    var found = (names || []).filter(function (n) { return pattern.test(String(n).toLowerCase()); });
    return found.length ? found[0] : '';
}

function etlMissing(needed, available) {
    return (needed || []).filter(function (c) {
        return (available || []).indexOf(c) === -1;
    });
}

/* ------------------------------------------------------------------ */
/* Fábrica de nodos                                                    */
/* ------------------------------------------------------------------ */

function etlRow(label, control, help) {
    return '<div class="form-group" style="margin-top:8px">' +
        '<label class="col-form-label">' + label + '</label>' + control +
        (help ? '<p class="help-block" style="margin:3px 0 0">' + help + '</p>' : '') +
        '</div>';
}

function etlAdvanced(ID, inner) {
    return '<div style="margin-top:12px">' +
        '<a href="#" id="advanced-toggle-' + ID + '" style="cursor:pointer">' +
        '<i class="fa fa-caret-right"></i> ' + gettext('Advanced parameters') + '</a></div>' +
        '<div id="advanced-' + ID + '" style="display:none">' + inner + '</div>';
}

function etlFillSelect($select, options, selected, placeholder) {
    $select.empty();
    if (placeholder) {
        $select.append($('<option>').val('').text(placeholder));
    }
    options.forEach(function (o) {
        var value = (o && typeof o === 'object') ? o.value : o;
        var text = (o && typeof o === 'object') ? o.text : o;
        $select.append($('<option>').val(value).text(text));
    });
    if (selected !== undefined && selected !== null && selected !== '' &&
        options.some(function (o) { return ((o && typeof o === 'object') ? o.value : o) === selected; })) {
        $select.val(selected);
    } else if (!placeholder && options.length) {
        $select.prop('selectedIndex', 0);
    } else {
        $select.val('');
    }
}

function etlSavedParams(ID) {
    var entry = (typeof getTaskParamsEntry === 'function') ? getTaskParamsEntry(ID) : null;
    return (entry && entry.parameters && entry.parameters[0]) ? entry.parameters[0] : {};
}

function etlShowError(ID, message) {
    var $box = $('#error-' + ID);
    if (message) {
        $box.text(message).show();
    } else {
        $box.hide().text('');
    }
}

function etlRestricted(type) {
    return typeof editablerestrictedly !== 'undefined' && editablerestrictedly &&
        (type.indexOf('input_') === 0 || type.indexOf('output_') === 0);
}

/**
 * Crea la figura draw2d del nodo descrito por cfg:
 *   name, title, headerColor, dialogSize
 *   paramKeys: claves de los parámetros que devuelve collect() (las lee assistant/shapes.py)
 *   defaults / defaultSchema (opcional): parámetros y esquema con que nace el nodo si funciona sin configurar
 *   inputs / outputs: [{label, kind}]
 *   body(ID): html del cuerpo del diálogo
 *   setup(ID, ctx): enlaza eventos una sola vez
 *   populate(ID, inputs, saved, ctx): rellena el diálogo al abrirlo
 *   collect(ID, inputs): devuelve los parámetros o lanza Error(mensaje)
 *   outputSchema(inputs, params): esquema de salida (o una promesa)
 */
function defineEtlNode(cfg) {
    window[cfg.name] = draw2d.shape.layout.VerticalLayout.extend({

        NAME: cfg.name,

        init: function (attr) {
            this._super($.extend({bgColor: '#dbddde', color: '#d7d7d7', stroke: 1, radius: 3}, attr));

            this.classLabel = new draw2d.shape.basic.Label({
                text: cfg.title(),
                stroke: 1,
                fontColor: '#ffffff',
                bgColor: cfg.headerColor,
                radius: this.getRadius(),
                padding: 10,
                resizeable: true,
                editor: new draw2d.ui.LabelInplaceEditor()
            });

            var icon = new draw2d.shape.icon.Gear({
                minWidth: 13, minHeight: 13, width: 13, height: 13, color: '#e2504c'
            });
            this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8));
            this.add(this.classLabel);

            var ID = this.id;
            var context = this;

            // Un nodo que no se ha aceptado nunca se guarda como null y rompe la ejecución. Los nodos que
            // funcionan con valores por defecto nacen ya configurados; al cargar un workspace guardado,
            // drawNodes() sustituye esta entrada por la guardada.
            if (cfg.defaults && !getTaskParamsEntry(ID)) {
                isAlreadyInCanvas(jsonParams, {
                    id: ID, parameters: [$.extend({}, cfg.defaults)],
                    schema: cfg.defaultSchema ? cfg.defaultSchema.slice() : [], 'schema-old': []
                }, ID);
            }
            setColorIfIsOpened(jsonParams, this.cssClass, ID, icon);

            $('#canvas-parent').append(
                '<div id="dialog-' + cfg.name + '-' + ID + '" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">' +
                '<div class="modal-dialog' + (cfg.dialogSize ? ' ' + cfg.dialogSize : '') + '" role="document">' +
                '<div class="modal-content">' +
                '<div class="modal-header">' +
                '<button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>' +
                '<h4 class="modal-title">' + paramsTransTpl.replace('{}', cfg.title()) + '</h4>' +
                '</div>' +
                '<div class="modal-body"><form onsubmit="return false">' + cfg.body(ID) +
                '<div id="error-' + ID + '" class="alert alert-danger" style="display:none;margin-top:12px"></div>' +
                '</form></div>' +
                '<div class="modal-footer">' +
                '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">' + gettext('Close') + '</button>' +
                '<button type="button" class="btn btn-default btn-sm" id="accept-' + ID + '">' + gettext('Accept') + '</button>' +
                '</div></div></div></div>');

            $('#advanced-toggle-' + ID).on('click', function (e) {
                e.preventDefault();
                $('#advanced-' + ID).slideToggle('fast');
                $(this).find('i').toggleClass('fa-caret-right fa-caret-down');
            });

            if (cfg.setup) {
                cfg.setup(ID, context);
            }

            function currentInputs() {
                var raw = [];
                try {
                    raw = passSchemaWhenInputTask(context.canvas, listLabel, ID);
                } catch (err) {
                    raw = [];
                }
                return etlPerPortSchemas(raw, cfg.inputs.length || 1);
            }

            icon.on('click', function () {
                etlShowError(ID, '');
                cfg.populate(ID, currentInputs(), etlSavedParams(ID), context);
                if (etlRestricted(cfg.name)) {
                    $('#dialog-' + cfg.name + '-' + ID).find('input, select, textarea, button.btn-default:not([data-dismiss])').prop('disabled', true);
                    $('#accept-' + ID).prop('disabled', true);
                }
                $('#dialog-' + cfg.name + '-' + ID).modal('show');
            });

            $('#accept-' + ID).on('click', function () {
                var inputs = currentInputs();
                var params;
                try {
                    params = cfg.collect(ID, inputs);
                } catch (err) {
                    etlShowError(ID, err.message);
                    return;
                }
                etlShowError(ID, '');

                $.when(cfg.outputSchema(inputs, params)).done(function (schemaOut) {
                    var task = {id: ID, parameters: [params]};
                    var raw = [];
                    try {
                        raw = passSchemaWhenInputTask(context.canvas, listLabel, ID);
                    } catch (err2) {
                        raw = [];
                    }
                    task.schema = schemaOut;
                    task['schema-old'] = raw;
                    isAlreadyInCanvas(jsonParams, task, ID);
                    passSchemaToEdgeConnected(ID, listLabel, schemaOut, context.canvas);
                    if (typeof propagateSchemaFrom === 'function' && context.canvas) {
                        propagateSchemaFrom(ID, context.canvas, {skipStart: true});
                    }
                    icon.setColor(cfg.gearColor || '#4682B4');
                    $('#dialog-' + cfg.name + '-' + ID).modal('hide');
                }).fail(function (message) {
                    etlShowError(ID, message || gettext('The node could not be configured.'));
                });
            });
        },

        addEntity: function (optionalIndex) {
            var inputNames = [];
            var outputNames = [];
            var self = this;

            function addLabel(def, isInput) {
                var kind = ETL_PORT_KINDS[def.kind] || ETL_PORT_KINDS.table;
                var label = new draw2d.shape.basic.Label({
                    text: def.label(),
                    stroke: 0.2,
                    radius: 0,
                    bgColor: '#ffffff',
                    padding: {left: isInput ? 10 : 40, top: 3, right: 10, bottom: 5},
                    fontColor: kind.color || '#107dac',
                    resizeable: true
                });
                var port = label.createPort(isInput ? 'input' : 'output');
                port.setName((isInput ? 'input_' : 'output_') + label.id);
                port.etlKind = def.kind || 'table';
                if (kind.color) {
                    port.setBackgroundColor(kind.color);
                }
                (isInput ? inputNames : outputNames).push(port.name);
                self.add(label);
            }

            // Primero todas las entradas y después las salidas: el orden de los puertos lo usan la
            // carga de workspaces (remapPortName) y el motor de ejecución.
            cfg.inputs.forEach(function (d) { addLabel(d, true); });
            cfg.outputs.forEach(function (d) { addLabel(d, false); });

            listLabel.push([this.id, inputNames, outputNames]);
            return this;
        },

        removeEntity: function (index) {
            this.remove(this.children.get(index + 1).figure);
        },

        getEntity: function (index) {
            return this.children.get(index + 1).figure;
        },

        setName: function (name) {
            this.classLabel.setText(name);
            return this;
        },

        getPersistentAttributes: getPerAttr,

        // Los puertos los crea addEntity() una sola vez (View.onDrop y drawNodes); aquí no se vuelve a llamar.
        setPersistentAttributes: function (memento) {
            this._super(memento);
            this.setName(memento.name);
            return this;
        }
    });
}

/* ------------------------------------------------------------------ */
/* Definición de los nodos                                             */
/* ------------------------------------------------------------------ */

var ETL_PREDICTIVE_COLOR = '#b7a5e0';
// Nodos de la categoría Ráster: rosa frambuesa claro, a juego con el botón y con los puertos ráster
var ETL_RASTER_COLOR = '#f06292';

/* ---------- Entrada ráster ---------- */

function etlRasterRequest(params) {
    var form = new FormData();
    form.append('jsonParamsRaster', JSON.stringify({parameters: [params]}));
    var d = $.Deferred();
    $.ajax({
        type: 'POST',
        url: '/gvsigonline/etl/etl_schema_raster/',
        data: form,
        cache: false,
        contentType: false,
        processData: false,
        beforeSend: function (xhr) { xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken')); }
    }).done(function (data) {
        d.resolve(data);
    }).fail(function (xhr) {
        var msg = gettext('The raster could not be read.');
        try { msg = JSON.parse(xhr.responseText).error || msg; } catch (e) { /* respuesta no JSON */ }
        d.reject(msg);
    });
    return d.promise();
}

function etlRenderBands(ID, info, aliases) {
    var html = '';
    info.bands.forEach(function (defaultName, i) {
        var alias = aliases[i] && aliases[i].trim() ? aliases[i].trim() : '';
        html += '<div class="row" style="margin-top:4px">' +
            '<div class="col-xs-3 text-right" style="padding-top:6px"><span class="text-muted">' + gettext('Band') + ' ' + (i + 1) + '</span></div>' +
            '<div class="col-xs-9"><input type="text" class="form-control input-sm raster-band-alias-' + ID + '" ' +
            'placeholder="b' + (i + 1) + '" value="' + etlEscape(alias) + '"></div></div>';
    });
    $('#raster-bands-' + ID).html(html);
    $('#raster-info-' + ID).text(info.bands.length + ' ' + gettext('bands') + ' · ' + (info.crs || gettext('no CRS')) +
        ' · ' + info.width + ' × ' + info.height + ' px');
    $('#raster-bands-box-' + ID).show();
}

function etlLoadRaster(ID, aliases) {
    var path = $('#raster-file-' + ID).val();
    if (!path) {
        $('#raster-bands-box-' + ID).hide();
        return $.Deferred().reject(gettext('Select a GeoTIFF file.')).promise();
    }
    return etlRasterRequest({'raster-file': path, 'band-names': ''}).done(function (info) {
        etlShowError(ID, '');
        etlRenderBands(ID, info, aliases || []);
    }).fail(function (msg) {
        $('#raster-bands-box-' + ID).hide();
        etlShowError(ID, msg);
    });
}

function etlCollectAliases(ID) {
    return $('.raster-band-alias-' + ID).map(function () {
        return $(this).val().replace(/,/g, ' ').trim();
    }).get();
}

defineEtlNode({
    name: 'input_Raster',
    // Claves que devuelve collect(): las lee el catálogo del asistente (assistant/shapes.py)
    paramKeys: ['raster-file', 'band-names'],
    title: function () { return gettext('Raster (GeoTIFF)'); },
    headerColor: '#83d0c9',
    gearColor: '#01b0a0',
    inputs: [],
    outputs: [{label: function () { return gettext('Raster'); }, kind: 'raster'}],
    body: function (ID) {
        return etlRow(gettext('GeoTIFF file'),
            '<div class="input-group">' +
            '<input type="text" id="raster-file-' + ID + '" class="form-control" placeholder="' + etlEscape(gettext('Choose a .tif / .tiff file')) + '">' +
            '<span class="input-group-btn"><a href="#" id="select-file-button-' + ID + '" class="btn btn-default">' +
            '<i class="fa fa-folder-open"></i> ' + gettext('Select file') + '</a></span></div>',
            gettext('The file must be in the file manager. It can have any number of bands.')) +
            '<div id="raster-bands-box-' + ID + '" style="display:none;margin-top:12px">' +
            '<p class="text-muted" id="raster-info-' + ID + '"></p>' +
            '<label class="col-form-label">' + gettext('Band names (optional)') + '</label>' +
            '<p class="help-block" style="margin-top:0">' +
            gettext('Name the bands so that later steps are easier to read, for example Red, Green, Infrared.') + '</p>' +
            '<div id="raster-bands-' + ID + '"></div></div>';
    },
    setup: function (ID) {
        $('#select-file-button-' + ID).on('click', function (e) {
            e.preventDefault();
            window.open('/gvsigonline/filemanager/?popup=1', 'Ratting',
                'width=640, height=480,left=150,top=200,toolbar=0,status=0,scrollbars=1');
            // El gestor de ficheros entrega la ruta a UNA función global compartida por todos los nodos
            // (Shapefile, CSV...). Se instala la de este nodo solo mientras se elige el ráster y se
            // devuelve la anterior después; si no, el siguiente nodo que elija un fichero (p. ej. un
            // .shp) lo recibiría esta función y lo rechazaría como "no es un GeoTIFF".
            var previous = window.filemanagerCallback;
            var mine = function (url) {
                var lower = url.toLowerCase();
                if (lower.endsWith('.tif') || lower.endsWith('.tiff')) {
                    window.filemanagerCallback = previous;
                    $('#raster-file-' + ID).val('file://' + fm_directory + url);
                    etlLoadRaster(ID, []);
                } else {
                    messageBox.show('warning', gettext('The selected file is not a GeoTIFF.'));
                }
            };
            window.filemanagerCallback = mine;
            $('#dialog-input_Raster-' + ID).one('hidden.bs.modal', function () {
                if (window.filemanagerCallback === mine) {
                    window.filemanagerCallback = previous;
                }
            });
        });
        $('#raster-file-' + ID).on('change', function () { etlLoadRaster(ID, []); });
    },
    populate: function (ID, inputs, saved) {
        $('#raster-file-' + ID).val(saved['raster-file'] || '');
        $('#raster-bands-box-' + ID).hide();
        if (saved['raster-file']) {
            etlLoadRaster(ID, String(saved['band-names'] || '').split(','));
        }
    },
    collect: function (ID) {
        var path = $('#raster-file-' + ID).val().trim();
        if (!path) {
            throw new Error(gettext('Select a GeoTIFF file.'));
        }
        return {'raster-file': path, 'band-names': etlCollectAliases(ID).join(',')};
    },
    outputSchema: function (inputs, p) {
        // El servidor valida el fichero y devuelve los nombres de banda normalizados
        var d = $.Deferred();
        etlRasterRequest(p).done(function (info) { d.resolve(info.bands); }).fail(function (msg) { d.reject(msg); });
        return d.promise();
    }
});

/* ---------- Muestrear ráster ---------- */

defineEtlNode({
    name: 'trans_RasterSample',
    // Claves que devuelve collect(): las lee el catálogo del asistente (assistant/shapes.py)
    paramKeys: ['class-attr', 'max-per-class', 'seed'],
    title: function () { return gettext('Sample Raster'); },
    headerColor: ETL_PREDICTIVE_COLOR,
    inputs: [{label: function () { return gettext('Raster'); }, kind: 'raster'},
             {label: function () { return gettext('Samples'); }, kind: 'table'}],
    outputs: [{label: function () { return gettext('Pixels'); }, kind: 'table'}],
    body: function (ID) {
        return '<p class="text-muted">' +
            gettext('Reads the raster pixels that fall inside each sample polygon. The result is a table with one row per pixel, one column per band and the class of the polygon.') + '</p>' +
            etlRow(gettext('Class column'), '<select id="class-attr-' + ID + '" class="form-control"></select>',
                gettext('Column of the sample polygons that says which class each one belongs to.')) +
            etlAdvanced(ID,
                etlRow(gettext('Maximum pixels per class'),
                    '<input type="number" id="max-per-class-' + ID + '" min="1" class="form-control" placeholder="' + etlEscape(gettext('No limit')) + '">',
                    gettext('Limits and balances the classes when some have many more pixels than others.')) +
                etlRow(gettext('Random seed'), '<input type="number" id="seed-' + ID + '" min="0" value="42" class="form-control">',
                    gettext('Using the same seed gives the same sample every time.')));
    },
    populate: function (ID, inputs, saved) {
        etlFillSelect($('#class-attr-' + ID), etlUserColumns(inputs[1]), saved['class-attr']);
        $('#max-per-class-' + ID).val(saved['max-per-class'] || '');
        $('#seed-' + ID).val(saved.seed || 42);
    },
    collect: function (ID, inputs) {
        if (!inputs[0].length) { throw new Error(gettext('Connect and configure a raster first.')); }
        if (!inputs[1].length) { throw new Error(gettext('Connect the sample polygons first.')); }
        var cls = $('#class-attr-' + ID).val();
        if (!cls) { throw new Error(gettext('Choose the class column.')); }
        if (inputs[0].indexOf(cls) !== -1) {
            throw new Error(gettext('The class column has the same name as a raster band. Rename one of them.'));
        }
        var max = etlParseInt($('#max-per-class-' + ID).val(), 1);
        var seed = etlParseInt($('#seed-' + ID).val(), 0);
        if (max === undefined) { throw new Error(gettext('The maximum pixels per class must be a whole number greater than 0.')); }
        if (seed === undefined || seed === null) { throw new Error(gettext('The random seed must be a whole number.')); }
        return {'class-attr': cls, 'max-per-class': max === null ? '' : String(max), seed: String(seed)};
    },
    outputSchema: function (inputs, p) { return etlSampleOutput(inputs, p); }
});

/* ---------- Random Forest ---------- */

/** Muestra solo los campos que aplican al tipo de validación elegido. */
function etlToggleValidation(ID) {
    var mode = $('#validation-' + ID).val() || 'random';
    // Automática: por polígonos si la tabla lo permite (usa las rondas); si no, reserva aleatoria (usa el %)
    $('#test-percent-' + ID).closest('.col-md-4').toggle(mode === 'random' || mode === 'auto');
    $('#folds-wrap-' + ID).toggle(mode !== 'random');
    $('#block-wrap-' + ID).toggle(mode === 'block');
}

function etlRenderFeatures(ID, columns, checked, target) {
    $('#features-' + ID).data('columns', columns);
    var html = '';
    columns.forEach(function (c) {
        var disabled = c === target;
        html += '<div class="checkbox" style="margin:2px 0"><label>' +
            '<input type="checkbox" class="rf-feature-' + ID + '" value="' + etlEscape(c) + '"' +
            (checked.indexOf(c) !== -1 && !disabled ? ' checked' : '') + (disabled ? ' disabled' : '') + '> ' +
            etlEscape(c) + '</label></div>';
    });
    $('#features-' + ID).html(html || '<p class="text-muted">' + gettext('Connect a table first.') + '</p>');
}

function etlCheckedFeatures(ID) {
    return $('.rf-feature-' + ID + ':checked').map(function () { return $(this).val(); }).get();
}

defineEtlNode({
    name: 'trans_RandomForest',
    // Claves que devuelve collect(): las lee el catálogo del asistente (assistant/shapes.py)
    paramKeys: ['target', 'features', 'problem', 'n-estimators', 'max-depth', 'min-samples-leaf', 'test-percent', 'seed', 'validation', 'folds', 'block-size', 'max-features'],
    title: function () { return gettext('Random Forest'); },
    headerColor: ETL_PREDICTIVE_COLOR,
    dialogSize: 'modal-lg',
    inputs: [{label: function () { return gettext('Data'); }, kind: 'table'}],
    outputs: [{label: function () { return gettext('Report'); }, kind: 'table'},
              {label: function () { return gettext('Model'); }, kind: 'model'},
              {label: function () { return gettext('Confusion matrix'); }, kind: 'table'}],
    body: function (ID) {
        return '<p class="text-muted">' +
            gettext('Learns from the rows that have a value in the variable to predict. It gives a report with the quality of the model and the importance of each variable, and the trained model to apply it elsewhere.') + '</p>' +
            etlRow(gettext('Variable to predict'), '<select id="target-' + ID + '" class="form-control"></select>',
                gettext('If it is text or has only a few whole values, the classes are predicted; if it is a continuous number, its value is estimated.')) +
            etlRow(gettext('Variables used to predict'),
                '<div style="margin-bottom:4px"><a href="#" id="features-all-' + ID + '">' + gettext('All') + '</a> · ' +
                '<a href="#" id="features-none-' + ID + '">' + gettext('None') + '</a></div>' +
                '<div id="features-' + ID + '" style="max-height:200px;overflow:auto;border:1px solid #ddd;padding:6px 10px"></div>',
                gettext('They must be numeric columns.')) +
            etlAdvanced(ID,
                '<div class="row">' +
                '<div class="col-md-4">' + etlRow(gettext('Type of problem'),
                    '<select id="problem-' + ID + '" class="form-control"></select>') + '</div>' +
                '<div class="col-md-4">' + etlRow(gettext('Number of trees'),
                    '<input type="number" id="n-estimators-' + ID + '" min="1" max="2000" class="form-control">') + '</div>' +
                '<div class="col-md-4">' + etlRow(gettext('Maximum depth'),
                    '<input type="number" id="max-depth-' + ID + '" min="1" class="form-control" placeholder="' + etlEscape(gettext('No limit')) + '">') + '</div>' +
                '</div><div class="row">' +
                '<div class="col-md-4">' + etlRow(gettext('Minimum samples per leaf'),
                    '<input type="number" id="min-samples-leaf-' + ID + '" min="1" class="form-control">') + '</div>' +
                '<div class="col-md-4">' + etlRow(gettext('% kept to evaluate'),
                    '<input type="number" id="test-percent-' + ID + '" min="0" max="50" class="form-control">',
                    gettext('Data not used for learning, to measure quality. 0 turns it off.')) + '</div>' +
                '<div class="col-md-4">' + etlRow(gettext('Random seed'),
                    '<input type="number" id="seed-' + ID + '" min="0" class="form-control">') + '</div>' +
                '</div><div class="row">' +
                '<div class="col-md-8">' + etlRow(gettext('Variables tried at each split'),
                    '<select id="max-features-' + ID + '" class="form-control"></select>',
                    gettext('Automatic follows Breiman (2001): the square root of the number of variables in classification and a third of them in regression. All of them is not a random forest but bagged trees.')) + '</div>' +
                '</div><div class="row">' +
                '<div class="col-md-4">' + etlRow(gettext('How quality is measured'),
                    '<select id="validation-' + ID + '" class="form-control"></select>',
                    gettext('Neighbouring pixels look alike, so a random split is optimistic. Leaving out whole polygons or blocks gives a more honest estimate.')) + '</div>' +
                '<div class="col-md-4" id="folds-wrap-' + ID + '">' + etlRow(gettext('Number of rounds'),
                    '<input type="number" id="folds-' + ID + '" min="2" max="10" class="form-control">',
                    gettext('The data is split into this many parts; each one is left out once.')) + '</div>' +
                '<div class="col-md-4" id="block-wrap-' + ID + '">' + etlRow(gettext('Block size'),
                    '<input type="number" id="block-size-' + ID + '" min="0" step="any" class="form-control">',
                    gettext('Side of each square block, in the units of the raster coordinate system (for example metres).')) + '</div>' +
                '</div>' +
                '<p class="help-block">' + gettext('The confusion matrix has one column per predicted class, named pred_ followed by the class.') + '</p>');
    },
    setup: function (ID) {
        $('#validation-' + ID).on('change', function () { etlToggleValidation(ID); });
        $('#target-' + ID).on('change', function () {
            // Las columnas se guardan al rellenar el diálogo: no se leen del desplegable (incluye "Elegir…")
            etlRenderFeatures(ID, $('#features-' + ID).data('columns') || [], etlCheckedFeatures(ID), $(this).val());
        });
        $('#features-all-' + ID).on('click', function (e) {
            e.preventDefault();
            $('.rf-feature-' + ID + ':not(:disabled)').prop('checked', true);
        });
        $('#features-none-' + ID).on('click', function (e) {
            e.preventDefault();
            $('.rf-feature-' + ID).prop('checked', false);
        });
    },
    populate: function (ID, inputs, saved) {
        var cols = etlUserColumns(inputs[0]);
        etlFillSelect($('#target-' + ID), cols, saved.target, gettext('Choose…'));
        var target = $('#target-' + ID).val();
        var previous = Array.isArray(saved.features) ? saved.features.filter(function (f) { return cols.indexOf(f) !== -1; }) : [];
        var checked = previous.length ? previous : cols.filter(function (c) { return c !== target; });
        etlRenderFeatures(ID, cols, checked, target);
        etlFillSelect($('#problem-' + ID), [
            {value: 'auto', text: gettext('Detect automatically')},
            {value: 'classification', text: gettext('Classification (categories)')},
            {value: 'regression', text: gettext('Regression (number)')}], saved.problem || 'auto');
        $('#n-estimators-' + ID).val(saved['n-estimators'] || 100);
        $('#max-depth-' + ID).val(saved['max-depth'] || '');
        $('#min-samples-leaf-' + ID).val(saved['min-samples-leaf'] || 1);
        $('#test-percent-' + ID).val(saved['test-percent'] !== undefined && saved['test-percent'] !== '' ? saved['test-percent'] : 20);
        $('#seed-' + ID).val(saved.seed || 42);
        etlFillSelect($('#validation-' + ID), [
            {value: 'auto', text: gettext('Automatic (sample polygons out when possible)')},
            {value: 'random', text: gettext('Random split')},
            {value: 'polygon', text: gettext('Leave sample polygons out')},
            {value: 'block', text: gettext('Leave spatial blocks out')}], saved.validation || 'auto');
        etlFillSelect($('#max-features-' + ID), [
            {value: 'auto', text: gettext('Automatic (√p in classification, p/3 in regression)')},
            {value: 'sqrt', text: gettext('Square root of the number of variables')},
            {value: 'third', text: gettext('A third of the variables')},
            {value: 'all', text: gettext('All the variables (bagging)')}], saved['max-features'] || 'auto');
        $('#folds-' + ID).val(saved.folds || 5);
        $('#block-size-' + ID).val(saved['block-size'] || '');
        etlToggleValidation(ID);
    },
    collect: function (ID, inputs) {
        if (!inputs[0].length) { throw new Error(gettext('Connect a table with data first.')); }
        var target = $('#target-' + ID).val();
        if (!target) { throw new Error(gettext('Choose the variable to predict.')); }
        var features = etlCheckedFeatures(ID).filter(function (f) { return f !== target; });
        if (!features.length) { throw new Error(gettext('Choose at least one variable used to predict.')); }
        var n = etlParseInt($('#n-estimators-' + ID).val(), 1, 2000);
        var depth = etlParseInt($('#max-depth-' + ID).val(), 1);
        var leaf = etlParseInt($('#min-samples-leaf-' + ID).val(), 1);
        var test = etlParseInt($('#test-percent-' + ID).val(), 0, 50);
        var seed = etlParseInt($('#seed-' + ID).val(), 0);
        if (n === undefined || n === null) { throw new Error(gettext('The number of trees must be between 1 and 2000.')); }
        if (depth === undefined) { throw new Error(gettext('The maximum depth must be a whole number greater than 0.')); }
        if (leaf === undefined || leaf === null) { throw new Error(gettext('The minimum samples per leaf must be a whole number greater than 0.')); }
        if (test === undefined || test === null) { throw new Error(gettext('The percentage kept to evaluate must be between 0 and 50.')); }
        if (seed === undefined || seed === null) { throw new Error(gettext('The random seed must be a whole number.')); }
        var validation = $('#validation-' + ID).val() || 'auto';
        var folds = etlParseInt($('#folds-' + ID).val(), 2, 10);
        var block = etlParseFloat($('#block-size-' + ID).val(), 0);
        if (validation !== 'random' && (folds === undefined || folds === null)) {
            throw new Error(gettext('The number of rounds must be between 2 and 10.'));
        }
        if (validation === 'block' && !block) {
            throw new Error(gettext('Enter the block size, a number greater than 0.'));
        }
        return {
            target: target, features: features, problem: $('#problem-' + ID).val() || 'auto',
            'n-estimators': String(n), 'max-depth': depth === null ? '' : String(depth),
            'min-samples-leaf': String(leaf), 'test-percent': String(test), seed: String(seed),
            validation: validation, folds: String(folds || 5),
            'block-size': validation === 'block' ? String(block) : '',
            'max-features': $('#max-features-' + ID).val() || 'auto'
        };
    },
    outputSchema: function (inputs, p) { return etlForestOutput(inputs, p); }
});

/* ---------- Predecir ráster ---------- */

defineEtlNode({
    name: 'trans_RasterPredict',
    // Claves que devuelve collect(): las lee el catálogo del asistente (assistant/shapes.py)
    paramKeys: ['configured'],
    defaults: {configured: 'true'},
    defaultSchema: [['prediction'], ['confidence']],
    title: function () { return gettext('Predict Raster'); },
    headerColor: ETL_PREDICTIVE_COLOR,
    inputs: [{label: function () { return gettext('Raster'); }, kind: 'raster'},
             {label: function () { return gettext('Model'); }, kind: 'model'}],
    outputs: [{label: function () { return gettext('Result'); }, kind: 'raster'},
              {label: function () { return gettext('Certainty'); }, kind: 'raster'}],
    body: function (ID) {
        return '<p class="text-muted">' +
            gettext('Applies the model to every pixel of the raster. The result is a raster where each pixel holds the predicted class (or value). It needs no parameters.') + '</p>' +
            '<p class="text-muted">' +
            gettext('The second output (Certainty) says how sure the model is of each pixel: the share of votes of the trees for the chosen class, from 0 to 1. It is a relative indicator, not a calibrated probability. For a numeric model it is the spread between the trees, in the units of the variable, which is smaller than a real prediction interval. It is always generated; connect it only if you need it.') + '</p>' +
            '<div id="predict-status-' + ID + '"></div>';
    },
    populate: function (ID, inputs) {
        var model = inputs[1] || [];
        var missing = etlMissing(model, inputs[0]);
        var html = '';
        if (!inputs[0].length || !model.length) {
            html = '<div class="alert alert-info">' + gettext('Connect a raster and a trained model.') + '</div>';
        } else if (missing.length) {
            html = '<div class="alert alert-warning">' + gettext('The raster does not have the bands the model was trained with:') +
                ' <b>' + etlEscape(missing.join(', ')) + '</b></div>';
        } else {
            html = '<div class="alert alert-success">' + gettext('The raster has all the bands the model needs:') +
                ' ' + etlEscape(model.join(', ')) + '</div>';
        }
        $('#predict-status-' + ID).html(html);
    },
    collect: function (ID, inputs) {
        if (!inputs[0].length || !inputs[1].length) { throw new Error(gettext('Connect a raster and a trained model.')); }
        var missing = etlMissing(inputs[1], inputs[0]);
        if (missing.length) {
            throw new Error(gettext('The raster does not have the bands the model was trained with:') + ' ' + missing.join(', '));
        }
        return {configured: 'true'};
    },
    outputSchema: function () { return [['prediction'], ['confidence']]; }
});

/* ---------- Poligonizar ráster ---------- */

defineEtlNode({
    name: 'trans_RasterPolygonize',
    // Claves que devuelve collect(): las lee el catálogo del asistente (assistant/shapes.py)
    paramKeys: ['classes', 'min-area', 'simplify', 'connectivity'],
    defaults: {classes: '', 'min-area': '0', simplify: '0', connectivity: '4'},
    defaultSchema: ETL_POLYGON_COLUMNS,
    title: function () { return gettext('Raster to Polygons'); },
    headerColor: ETL_RASTER_COLOR,
    inputs: [{label: function () { return gettext('Raster'); }, kind: 'raster'}],
    outputs: [{label: function () { return gettext('Polygons'); }, kind: 'table'}],
    body: function (ID) {
        return '<p class="text-muted">' +
            gettext('Turns a classified raster into polygons. Each polygon has its class and its area.') + '</p>' +
            etlRow(gettext('Classes to keep'), '<input type="text" id="classes-' + ID + '" class="form-control" placeholder="' + etlEscape(gettext('All classes')) + '">',
                gettext('Names of the classes, separated by commas. Leave it empty to keep all of them.')) +
            etlRow(gettext('Minimum area'), '<input type="number" id="min-area-' + ID + '" min="0" step="any" class="form-control">',
                gettext('Polygons smaller than this are discarded, in squared units of the raster coordinate system (for example square metres). Useful to remove isolated pixels.')) +
            etlAdvanced(ID,
                etlRow(gettext('Simplify'), '<input type="number" id="simplify-' + ID + '" min="0" step="any" class="form-control">',
                    gettext('Smooths the staircase edges. In units of the coordinate system; 0 leaves them as they are.')) +
                etlRow(gettext('Pixels count as neighbours'), '<select id="connectivity-' + ID + '" class="form-control"></select>',
                    gettext('With 8, pixels touching only at a corner are joined into the same polygon.')));
    },
    populate: function (ID, inputs, saved) {
        $('#classes-' + ID).val(saved.classes || '');
        $('#min-area-' + ID).val(saved['min-area'] || 0);
        $('#simplify-' + ID).val(saved.simplify || 0);
        etlFillSelect($('#connectivity-' + ID), [
            {value: '4', text: gettext('Only along the sides (4)')},
            {value: '8', text: gettext('Also at the corners (8)')}], String(saved.connectivity || '4'));
    },
    collect: function (ID, inputs) {
        if (!inputs[0].length) { throw new Error(gettext('Connect a classified raster first.')); }
        var area = etlParseFloat($('#min-area-' + ID).val(), 0);
        var simp = etlParseFloat($('#simplify-' + ID).val(), 0);
        if (area === undefined) { throw new Error(gettext('The minimum area must be a number greater than or equal to 0.')); }
        if (simp === undefined) { throw new Error(gettext('The simplification must be a number greater than or equal to 0.')); }
        var classes = $('#classes-' + ID).val().split(',').map(function (c) { return c.trim(); })
            .filter(function (c) { return c; }).join(',');
        return {classes: classes, 'min-area': String(area || 0), simplify: String(simp || 0),
                connectivity: $('#connectivity-' + ID).val() || '4'};
    },
    outputSchema: function () { return ETL_POLYGON_COLUMNS.slice(); }
});

/* ---------- Filtro de mayoría ---------- */

defineEtlNode({
    name: 'trans_RasterMajority',
    // Claves que devuelve collect(): las lee el catálogo del asistente (assistant/shapes.py)
    paramKeys: ['mode', 'window', 'iterations', 'min-pixels', 'connectivity'],
    defaults: {mode: 'majority', window: '3', iterations: '1', 'min-pixels': '4', connectivity: '4'},
    defaultSchema: ['prediction'],
    title: function () { return gettext('Clean Raster'); },
    headerColor: ETL_RASTER_COLOR,
    inputs: [{label: function () { return gettext('Raster'); }, kind: 'raster'}],
    outputs: [{label: function () { return gettext('Raster'); }, kind: 'raster'}],
    body: function (ID) {
        return '<p class="text-muted">' +
            gettext('Removes the isolated pixels ("salt and pepper") of a classified raster. Use it between Predict Raster and Raster to Polygons.') + '</p>' +
            etlRow(gettext('Method'), '<select id="mode-' + ID + '" class="form-control"></select>') +
            '<div id="majority-box-' + ID + '"><div class="row">' +
            '<div class="col-md-6">' + etlRow(gettext('Window'), '<select id="window-' + ID + '" class="form-control"></select>',
                gettext('Each pixel takes the most frequent class of its neighbours. A bigger window cleans more but blurs small areas.')) + '</div>' +
            '<div class="col-md-6">' + etlRow(gettext('Repetitions'), '<input type="number" id="iterations-' + ID + '" min="1" max="5" class="form-control">',
                gettext('Applying it several times removes larger spots.')) + '</div></div></div>' +
            '<div id="sieve-box-' + ID + '"><div class="row">' +
            '<div class="col-md-6">' + etlRow(gettext('Minimum patch size (pixels)'), '<input type="number" id="min-pixels-' + ID + '" min="2" class="form-control">',
                gettext('Groups of connected pixels smaller than this are absorbed by their largest neighbour. The edges of the large areas are not changed.')) + '</div>' +
            '<div class="col-md-6">' + etlRow(gettext('Pixels count as neighbours'), '<select id="connectivity-' + ID + '" class="form-control"></select>') + '</div>' +
            '</div></div>';
    },
    setup: function (ID) {
        $('#mode-' + ID).on('change', function () {
            var mode = $(this).val();
            $('#majority-box-' + ID).toggle(mode === 'majority');
            $('#sieve-box-' + ID).toggle(mode === 'sieve');
        });
    },
    populate: function (ID, inputs, saved) {
        etlFillSelect($('#mode-' + ID), [
            {value: 'majority', text: gettext('Majority filter (smooths)')},
            {value: 'sieve', text: gettext('Minimum patch size (keeps the edges)')}], saved.mode || 'majority');
        etlFillSelect($('#window-' + ID), [
            {value: '3', text: '3 × 3'}, {value: '5', text: '5 × 5'}, {value: '7', text: '7 × 7'}], String(saved.window || '3'));
        etlFillSelect($('#connectivity-' + ID), [
            {value: '4', text: gettext('Only along the sides (4)')},
            {value: '8', text: gettext('Also at the corners (8)')}], String(saved.connectivity || '4'));
        $('#iterations-' + ID).val(saved.iterations || 1);
        $('#min-pixels-' + ID).val(saved['min-pixels'] || 4);
        $('#mode-' + ID).trigger('change');
    },
    collect: function (ID, inputs) {
        if (!inputs[0].length) { throw new Error(gettext('Connect a classified raster first.')); }
        var mode = $('#mode-' + ID).val() || 'majority';
        var iterations = etlParseInt($('#iterations-' + ID).val(), 1, 5);
        var pixels = etlParseInt($('#min-pixels-' + ID).val(), 2);
        if (mode === 'majority' && (iterations === undefined || iterations === null)) {
            throw new Error(gettext('The repetitions must be a whole number between 1 and 5.'));
        }
        if (mode === 'sieve' && (pixels === undefined || pixels === null)) {
            throw new Error(gettext('The minimum patch size must be a whole number of at least 2 pixels.'));
        }
        return {mode: mode, window: $('#window-' + ID).val() || '3', iterations: String(iterations || 1),
                'min-pixels': String(pixels || 4), connectivity: $('#connectivity-' + ID).val() || '4'};
    },
    outputSchema: function (inputs) { return inputs[0].length ? inputs[0].slice() : ['prediction']; }
});

/* ---------- Índice espectral ---------- */

function etlIndexOptions() {
    return [
        {value: 'ndvi', text: gettext('NDVI - vegetation')},
        {value: 'ndwi', text: gettext('NDWI - water')},
        {value: 'ndbi', text: gettext('NDBI - built-up areas')},
        {value: 'savi', text: gettext('SAVI - vegetation, soil adjusted')},
        {value: 'evi', text: gettext('EVI - enhanced vegetation')},
        {value: 'brightness', text: gettext('Brightness (mean of all bands)')},
        {value: 'nd', text: gettext('Normalized difference of two bands')}];
}

function etlIndexDescription(index) {
    return {
        ndvi: gettext('(NIR − Red) / (NIR + Red). High values mean healthy vegetation.'),
        ndwi: gettext('(Green − NIR) / (Green + NIR). High values mean water.'),
        ndbi: gettext('(SWIR − NIR) / (SWIR + NIR). High values mean built-up areas and bare soil.'),
        savi: gettext('(1 + L) · (NIR − Red) / (NIR + Red + L). Like NDVI but less affected by bare soil. Needs reflectance values.'),
        evi: gettext('2.5 · (NIR − Red) / (NIR + 6 · Red − 7.5 · Blue + 1). Vegetation index that does not saturate in dense vegetation. Needs reflectance values.'),
        brightness: gettext('Mean of all the bands of the raster.'),
        nd: gettext('(A − B) / (A + B) for two bands you choose. Valid for any other normalized index.')
    }[index] || '';
}

function etlRoleLabel(role) {
    return {nir: gettext('Near infrared (NIR)'), red: gettext('Red'), green: gettext('Green'), blue: gettext('Blue'),
            swir: gettext('Shortwave infrared (SWIR)'), a: gettext('Band A'), b: gettext('Band B')}[role] || role;
}

/** Dibuja un desplegable de banda por cada papel del índice elegido, preseleccionando por el nombre. */
/** Conversión a reflectancia: los campos de escala y offset solo se ven en "Personalizada"; aviso en SAVI/EVI. */
function etlToggleReflectance(ID) {
    var preset = $('#reflectance-' + ID).val() || 'none';
    var index = $('#index-' + ID).val();
    $('#scale-box-' + ID).toggle(preset === 'custom');
    $('#reflectance-warning-' + ID).toggle(preset === 'none' && (index === 'savi' || index === 'evi'));
}

function etlRenderIndexBands(ID, bands, saved) {
    var index = $('#index-' + ID).val();
    var def = ETL_INDICES[index];
    var html = '';
    if (def) {
        def.roles.forEach(function (role, i) {
            html += etlRow(etlRoleLabel(role), '<select id="band-' + (i + 1) + '-' + ID + '" class="form-control"></select>');
        });
    }
    $('#index-bands-' + ID).html(html);
    if (def) {
        def.roles.forEach(function (role, i) {
            var chosen = saved && saved['band-' + (i + 1)] && bands.indexOf(saved['band-' + (i + 1)]) !== -1
                ? saved['band-' + (i + 1)] : etlGuessBand(role, bands);
            etlFillSelect($('#band-' + (i + 1) + '-' + ID), bands, chosen, gettext('Choose…'));
        });
    }
    $('#index-help-' + ID).text(etlIndexDescription(index));
    $('#savi-box-' + ID).toggle(index === 'savi');
    etlToggleReflectance(ID);
}

defineEtlNode({
    name: 'trans_RasterIndex',
    // Claves que devuelve collect(): las lee el catálogo del asistente (assistant/shapes.py)
    paramKeys: ['index', 'band-1', 'band-2', 'band-3', 'name', 'reflectance', 'scale', 'offset', 'savi-l'],
    title: function () { return gettext('Spectral Index'); },
    headerColor: ETL_RASTER_COLOR,
    dialogSize: 'modal-lg',
    inputs: [{label: function () { return gettext('Raster'); }, kind: 'raster'}],
    outputs: [{label: function () { return gettext('Raster'); }, kind: 'raster'}],
    body: function (ID) {
        return '<p class="text-muted">' +
            gettext('Adds a band with a spectral index to the raster. The original bands are kept, so the new band can be used to train the model like any other. To add several indices, chain several nodes.') + '</p>' +
            etlRow(gettext('Index'), '<select id="index-' + ID + '" class="form-control"></select>',
                '<span id="index-help-' + ID + '"></span>') +
            '<div id="index-bands-' + ID + '"></div>' +
            etlRow(gettext('Name of the new band'), '<input type="text" id="name-' + ID + '" class="form-control">',
                gettext('This is how the band will appear in the following steps.')) +
            etlRow(gettext('Values of the image'), '<select id="reflectance-' + ID + '" class="form-control"></select>',
                gettext('How to turn the values of the image into reflectance (0-1) before computing the index: reflectance = (value + offset) / scale. With an offset (Sentinel-2 since 2022, Landsat Collection 2) not even the NDVI is right without it. Orthophotos (PNOA) are not calibrated reflectance: the index is useful to classify one image, not as a physical measure to compare dates or sheets.')) +
            '<div id="reflectance-warning-' + ID + '" class="alert alert-warning" style="display:none">' +
                gettext('SAVI and EVI need reflectance values between 0 and 1: choose how to convert the image, unless it already is.') + '</div>' +
            '<div id="scale-box-' + ID + '" style="display:none"><div class="row">' +
                '<div class="col-md-6">' + etlRow(gettext('Reflectance scale'),
                    '<input type="number" id="scale-' + ID + '" min="0" step="any" class="form-control">',
                    gettext('Value that means 100% reflectance.')) + '</div>' +
                '<div class="col-md-6">' + etlRow(gettext('Offset'),
                    '<input type="number" id="offset-' + ID + '" step="any" class="form-control">',
                    gettext('Added to the value before dividing by the scale (for example -1000 in Sentinel-2 L2A).')) + '</div>' +
            '</div></div>' +
            '<div id="savi-box-' + ID + '" style="display:none">' + etlRow(gettext('Soil adjustment (L)'),
                '<input type="number" id="savi-l-' + ID + '" min="0" max="1" step="any" class="form-control">',
                gettext('0.5 is suitable for most cases.')) + '</div>';
    },
    setup: function (ID) {
        $('#index-' + ID).on('change', function () {
            var bands = $('#index-bands-' + ID).data('bands') || [];
            var index = $(this).val();
            etlRenderIndexBands(ID, bands, {});
            if (!$('#name-' + ID).data('edited')) {
                $('#name-' + ID).val(index);
            }
        });
        $('#name-' + ID).on('input', function () { $(this).data('edited', true); });
        $('#reflectance-' + ID).on('change', function () { etlToggleReflectance(ID); });
    },
    populate: function (ID, inputs, saved) {
        var bands = etlUserColumns(inputs[0]);
        // Flujos guardados antes de existir la conversión: solo tenían la escala
        var preset = saved.reflectance || (saved.scale && Number(saved.scale) !== 1 ? 'custom' : 'none');
        etlFillSelect($('#reflectance-' + ID), [
            {value: 'none', text: gettext('Use them as they are (already reflectance, or only to classify)')},
            {value: 'uint8', text: gettext('8-bit image (0-255), for example an orthophoto')},
            {value: 'sentinel2_l2a', text: gettext('Sentinel-2 L2A since 2022: (value - 1000) / 10000')},
            {value: 'sentinel2_l2a_pre2022', text: gettext('Sentinel-2 L2A before 2022: value / 10000')},
            {value: 'landsat_c2_l2', text: gettext('Landsat Collection 2 level 2: value × 0.0000275 - 0.2')},
            {value: 'custom', text: gettext('Custom (scale and offset)')}], preset);
        $('#offset-' + ID).val(saved.offset || 0);
        $('#index-bands-' + ID).data('bands', bands);
        etlFillSelect($('#index-' + ID), etlIndexOptions(), saved.index, gettext('Choose…'));
        etlRenderIndexBands(ID, bands, saved);
        $('#name-' + ID).data('edited', !!saved.name).val(saved.name || $('#index-' + ID).val() || '');
        $('#scale-' + ID).val(saved.scale || 1);
        $('#savi-l-' + ID).val(saved['savi-l'] || 0.5);
    },
    collect: function (ID, inputs) {
        if (!inputs[0].length) { throw new Error(gettext('Connect and configure a raster first.')); }
        var index = $('#index-' + ID).val();
        if (!index) { throw new Error(gettext('Choose the index.')); }
        var def = ETL_INDICES[index];
        var out = {index: index, 'band-1': '', 'band-2': '', 'band-3': ''};
        var chosen = [];
        def.roles.forEach(function (role, i) {
            var band = $('#band-' + (i + 1) + '-' + ID).val();
            if (!band) { throw new Error(gettext('Choose the band for:') + ' ' + etlRoleLabel(role)); }
            out['band-' + (i + 1)] = band;
            chosen.push(band);
        });
        if (def.needsDifferent && etlUnique(chosen).length !== chosen.length) {
            throw new Error(gettext('Choose a different band for each role.'));
        }
        var preset = $('#reflectance-' + ID).val() || 'none';
        var scale = etlParseFloat($('#scale-' + ID).val(), 0);
        var offsetText = String($('#offset-' + ID).val() || '').trim().replace(',', '.');
        var offset = offsetText === '' ? 0 : Number(offsetText);
        var l = etlParseFloat($('#savi-l-' + ID).val(), 0);
        if (preset === 'custom' && !scale) {
            throw new Error(gettext('The reflectance scale must be a number greater than 0.'));
        }
        if (preset === 'custom' && !isFinite(offset)) { throw new Error(gettext('The offset must be a number.')); }
        if (l === undefined || (l !== null && l > 1)) { throw new Error(gettext('The soil adjustment must be between 0 and 1.')); }
        var name = $('#name-' + ID).val().trim() || index;
        out.name = name;
        out.reflectance = preset;
        out.scale = String(preset === 'custom' ? scale : 1);
        out.offset = String(preset === 'custom' ? offset : 0);
        out['savi-l'] = String(l === null ? 0.5 : l);
        return out;
    },
    outputSchema: function (inputs, p) {
        var bands = etlUserColumns(inputs[0]);
        return bands.concat([etlBandName(p.name || p.index, bands)]);
    }
});

/* ---------- Recortar ráster ---------- */

defineEtlNode({
    name: 'trans_RasterClip',
    // Claves que devuelve collect(): las lee el catálogo del asistente (assistant/shapes.py)
    paramKeys: ['mode', 'pixel-size', 'resampling'],
    defaults: {mode: 'polygon', 'pixel-size': '', resampling: 'average'},
    defaultSchema: [],
    title: function () { return gettext('Clip Raster'); },
    headerColor: ETL_RASTER_COLOR,
    inputs: [{label: function () { return gettext('Raster'); }, kind: 'raster'},
             {label: function () { return gettext('Mask'); }, kind: 'table'}],
    outputs: [{label: function () { return gettext('Raster'); }, kind: 'raster'}],
    body: function (ID) {
        return '<p class="text-muted">' +
            gettext('Cuts a raster with a mask of polygons (a vector layer), keeping only your study area. If you want, it also changes the pixel size in the same step, which makes a large image much lighter.') + '</p>' +
            etlRow(gettext('What to keep'), '<select id="mode-' + ID + '" class="form-control"></select>',
                gettext('Inside the polygons only: what is outside has no data. The rectangle: the image is only cut to the extent of the polygons.')) +
            etlRow(gettext('New pixel size'), '<input type="number" id="pixel-size-' + ID + '" min="0" step="any" class="form-control" placeholder="' + etlEscape(gettext('Keep the original')) + '">',
                gettext('In the units of the raster coordinate system (metres in UTM). For example 1 for a 25 cm orthophoto: the result has 16 times fewer pixels. Empty = keep the original.')) +
            etlAdvanced(ID,
                etlRow(gettext('Resampling when the size changes'), '<select id="resampling-' + ID + '" class="form-control"></select>',
                    gettext('Average is the best way to reduce the size. A raster of classes always uses nearest neighbour, so classes are not mixed.')));
    },
    populate: function (ID, inputs, saved) {
        etlFillSelect($('#mode-' + ID), [
            {value: 'polygon', text: gettext('Inside the polygons only')},
            {value: 'bbox', text: gettext('The rectangle that contains them')}], saved.mode || 'polygon');
        $('#pixel-size-' + ID).val(saved['pixel-size'] || '');
        etlFillSelect($('#resampling-' + ID), [
            {value: 'average', text: gettext('Average')},
            {value: 'bilinear', text: gettext('Bilinear')},
            {value: 'nearest', text: gettext('Nearest neighbour')}], saved.resampling || 'average');
    },
    collect: function (ID, inputs) {
        if (!inputs[0].length || !inputs[1].length) { throw new Error(gettext('Connect a raster and a mask of polygons first.')); }
        var size = etlParseFloat($('#pixel-size-' + ID).val(), 0);
        if (size === undefined || size === 0) { throw new Error(gettext('The pixel size must be a number greater than 0.')); }
        return {mode: $('#mode-' + ID).val() || 'polygon', 'pixel-size': size === null ? '' : String(size),
                resampling: $('#resampling-' + ID).val() || 'average'};
    },
    outputSchema: function (inputs) { return inputs[0].slice(); }
});

/* ---------- Evaluar clasificación ---------- */

defineEtlNode({
    name: 'trans_ClassAssess',
    // Claves que devuelve collect(): las lee el catálogo del asistente (assistant/shapes.py)
    paramKeys: ['class-attr'],
    title: function () { return gettext('Assess Classification'); },
    headerColor: ETL_PREDICTIVE_COLOR,
    inputs: [{label: function () { return gettext('Raster'); }, kind: 'raster'},
             {label: function () { return gettext('Validation samples'); }, kind: 'table'}],
    outputs: [{label: function () { return gettext('Report'); }, kind: 'table'},
              {label: function () { return gettext('Confusion matrix'); }, kind: 'table'}],
    body: function (ID) {
        return '<p class="text-muted">' +
            gettext('Measures how good a classified raster is using validation samples that were NOT used to train the model: polygons (all their pixels) or points, each with its real class. It gives the overall accuracy, the accuracy of each class, the confusion matrix and 95 % intervals obtained by resampling whole samples (bootstrap).') + '</p>' +
            '<p class="help-block">' + gettext('For a statistically valid accuracy of the map, the samples must be a random sample stratified by class (see Stratified Sample). Hand-drawn polygons only give an indication.') + '</p>' +
            etlRow(gettext('Class column'), '<select id="class-attr-' + ID + '" class="form-control"></select>',
                gettext('Column of the validation samples with the real class of each one.')) +
            '<p class="help-block">' + gettext('For each class, "precision" is the accuracy for the user (of what the map says is that class, how much really is) and "recall" is the accuracy for the producer (of what really is that class, how much the map finds).') + '</p>';
    },
    populate: function (ID, inputs, saved) {
        etlFillSelect($('#class-attr-' + ID), etlUserColumns(inputs[1]), saved['class-attr'], gettext('Choose…'));
    },
    collect: function (ID, inputs) {
        if (!inputs[0].length) { throw new Error(gettext('Connect a classified raster first.')); }
        if (!inputs[1].length) { throw new Error(gettext('Connect the validation samples first.')); }
        var cls = $('#class-attr-' + ID).val();
        if (!cls) { throw new Error(gettext('Choose the class column.')); }
        return {'class-attr': cls};
    },
    outputSchema: function () { return [ETL_PIXEL_REPORT_COLUMNS.slice(), ETL_MATRIX_COLUMNS.slice()]; }
});

/* ---------- Combinar ráster ---------- */

defineEtlNode({
    name: 'trans_RasterStack',
    // Claves que devuelve collect(): las lee el catálogo del asistente (assistant/shapes.py)
    paramKeys: ['resampling', 'prefix-1', 'prefix-2', 'prefix-3', 'prefix-4'],
    defaults: {resampling: 'bilinear', 'prefix-1': '', 'prefix-2': '', 'prefix-3': '', 'prefix-4': ''},
    defaultSchema: [],
    title: function () { return gettext('Combine Rasters'); },
    headerColor: ETL_RASTER_COLOR,
    dialogSize: 'modal-lg',
    inputs: [{label: function () { return gettext('Raster 1 (reference)'); }, kind: 'raster'},
             {label: function () { return gettext('Raster 2'); }, kind: 'raster'},
             {label: function () { return gettext('Raster 3'); }, kind: 'raster'},
             {label: function () { return gettext('Raster 4'); }, kind: 'raster'}],
    outputs: [{label: function () { return gettext('Raster'); }, kind: 'raster'}],
    body: function (ID) {
        return '<p class="text-muted">' +
            gettext('Joins the bands of several rasters (for example an orthophoto and a terrain model with another resolution) into one. The first connected raster is the reference: the others are reprojected and resampled to its grid. Where a raster does not cover the reference, its bands have no data.') + '</p>' +
            etlRow(gettext('Resampling'), '<select id="resampling-' + ID + '" class="form-control"></select>',
                gettext('Bilinear is smoother and suits imagery and continuous values. Nearest keeps the original values and is the one to use for classes.')) +
            '<div id="stack-prefixes-' + ID + '"></div>';
    },
    populate: function (ID, inputs, saved) {
        etlFillSelect($('#resampling-' + ID), [
            {value: 'bilinear', text: gettext('Bilinear')},
            {value: 'nearest', text: gettext('Nearest neighbour')}], saved.resampling || 'bilinear');
        var html = '';
        var connected = 0;
        inputs.forEach(function (bands) {
            if (!bands || !bands.length) { return; }
            connected += 1;
            html += etlRow(gettext('Prefix for the bands of raster') + ' ' + connected + ' (' + etlEscape(bands.join(', ')) + ')',
                '<input type="text" id="stack-prefix-' + connected + '-' + ID + '" class="form-control" maxlength="20" value="' +
                etlEscape(saved['prefix-' + connected] || '') + '">',
                connected === 1 ? gettext('Optional. Useful when several rasters have bands with the same name, for example two dates.') : '');
        });
        if (!connected) {
            html = '<div class="alert alert-info">' + gettext('Connect at least two rasters.') + '</div>';
        }
        $('#stack-prefixes-' + ID).html(html);
    },
    collect: function (ID, inputs) {
        var connected = inputs.filter(function (bands) { return bands && bands.length; }).length;
        if (connected < 2) { throw new Error(gettext('Connect and configure at least two rasters first.')); }
        var out = {resampling: $('#resampling-' + ID).val() || 'bilinear', 'prefix-1': '', 'prefix-2': '', 'prefix-3': '', 'prefix-4': ''};
        for (var i = 1; i <= connected; i++) {
            out['prefix-' + i] = ($('#stack-prefix-' + i + '-' + ID).val() || '').trim();
        }
        return out;
    },
    outputSchema: function (inputs, p) {
        return etlStackBands(inputs, [p['prefix-1'], p['prefix-2'], p['prefix-3'], p['prefix-4']]);
    }
});

/* ---------- Predecir tabla ---------- */

defineEtlNode({
    name: 'trans_TablePredict',
    // Claves que devuelve collect(): las lee el catálogo del asistente (assistant/shapes.py)
    paramKeys: ['column'],
    title: function () { return gettext('Predict Table'); },
    headerColor: ETL_PREDICTIVE_COLOR,
    inputs: [{label: function () { return gettext('Data'); }, kind: 'table'},
             {label: function () { return gettext('Model'); }, kind: 'model'}],
    outputs: [{label: function () { return gettext('Table'); }, kind: 'table'}],
    body: function (ID) {
        return '<p class="text-muted">' +
            gettext('Applies the model to every row of a table (parcels, points, sections…). The result is the same table, geometry included, with two new columns: the prediction and how sure the model is (for a numeric model, the disagreement between the trees).') + '</p>' +
            etlRow(gettext('Name of the prediction column'), '<input type="text" id="column-' + ID + '" class="form-control" maxlength="60">',
                gettext('The confidence goes in a column with the same name followed by _confidence. Rows with empty or non-numeric values in the variables are left without prediction.')) +
            '<div id="tpredict-status-' + ID + '"></div>';
    },
    populate: function (ID, inputs, saved) {
        $('#column-' + ID).val(saved.column || 'prediction');
        var missing = etlMissing(inputs[1], inputs[0]);
        var html;
        if (!inputs[0].length || !inputs[1].length) {
            html = '<div class="alert alert-info">' + gettext('Connect a table and a trained model.') + '</div>';
        } else if (missing.length) {
            html = '<div class="alert alert-warning">' + gettext('The table does not have the columns the model was trained with:') +
                ' <b>' + etlEscape(missing.join(', ')) + '</b></div>';
        } else {
            html = '<div class="alert alert-success">' + gettext('The table has all the columns the model needs:') +
                ' ' + etlEscape(inputs[1].join(', ')) + '</div>';
        }
        $('#tpredict-status-' + ID).html(html);
    },
    collect: function (ID, inputs) {
        if (!inputs[0].length || !inputs[1].length) { throw new Error(gettext('Connect a table and a trained model.')); }
        var missing = etlMissing(inputs[1], inputs[0]);
        if (missing.length) {
            throw new Error(gettext('The table does not have the columns the model was trained with:') + ' ' + missing.join(', '));
        }
        var column = etlBandName($('#column-' + ID).val().trim() || 'prediction', []);
        if (inputs[0].indexOf(column) !== -1 || inputs[0].indexOf(column + '_confidence') !== -1) {
            throw new Error(gettext('The table already has a column with that name. Choose another name.'));
        }
        return {column: $('#column-' + ID).val().trim() || 'prediction'};
    },
    outputSchema: function (inputs, p) {
        var column = etlBandName((p && p.column) || 'prediction', []);
        return inputs[0].concat([column, column + '_confidence']);
    }
});

/* ---------- Guardar modelo ---------- */

defineEtlNode({
    name: 'output_ModelSave',
    // Claves que devuelve collect(): las lee el catálogo del asistente (assistant/shapes.py)
    paramKeys: ['model-name', 'description', 'on-existing'],
    title: function () { return gettext('Save Model'); },
    headerColor: '#e8ca93',
    gearColor: '#e79600',
    inputs: [{label: function () { return gettext('Model'); }, kind: 'model'}],
    outputs: [],
    body: function (ID) {
        return '<p class="text-muted">' +
            gettext('Keeps the trained model so it can be applied later to other images or tables without training again. Models are private to the user who saves them.') + '</p>' +
            etlRow(gettext('Model name'), '<input type="text" id="model-name-' + ID + '" class="form-control" maxlength="60">',
                '<span id="model-name-hint-' + ID + '"></span>') +
            etlRow(gettext('Description'), '<input type="text" id="description-' + ID + '" class="form-control" maxlength="500">',
                gettext('Optional. For example the image, the date or the samples used.')) +
            etlRow(gettext('If the model already exists'), '<select id="on-existing-' + ID + '" class="form-control"></select>');
    },
    setup: function (ID) {
        $('#model-name-' + ID).on('input', function () {
            var safe = etlSafeModelName($(this).val());
            $('#model-name-hint-' + ID).text(safe ? gettext('It will be saved as:') + ' ' + safe : '');
        });
    },
    populate: function (ID, inputs, saved) {
        $('#model-name-' + ID).val(saved['model-name'] || '').trigger('input');
        $('#description-' + ID).val(saved.description || '');
        etlFillSelect($('#on-existing-' + ID), [
            {value: 'version', text: gettext('Add a new version (keeps the previous ones)')},
            {value: 'replace', text: gettext('Replace it (deletes the previous versions)')},
            {value: 'fail', text: gettext('Stop with an error')}], saved['on-existing'] || 'version');
    },
    collect: function (ID, inputs) {
        if (!inputs[0].length) { throw new Error(gettext('Connect a trained model first.')); }
        var name = $('#model-name-' + ID).val().trim();
        if (!etlSafeModelName(name)) { throw new Error(gettext('Write a name for the model.')); }
        return {'model-name': name, description: $('#description-' + ID).val().trim(),
                'on-existing': $('#on-existing-' + ID).val() || 'version'};
    },
    outputSchema: function () { return []; }
});

/* ---------- Modelo guardado ---------- */

var etlSavedModels = {loadedAt: 0, data: null};

function etlLoadSavedModels(force) {
    var d = $.Deferred();
    if (!force && etlSavedModels.data && Date.now() - etlSavedModels.loadedAt < 15000) {
        return d.resolve(etlSavedModels.data).promise();
    }
    $.getJSON('/gvsigonline/etl/etl_models_list/').done(function (data) {
        etlSavedModels = {loadedAt: Date.now(), data: data.models || []};
        d.resolve(etlSavedModels.data);
    }).fail(function () { d.reject(gettext('The saved models could not be loaded.')); });
    return d.promise();
}

/** Versión elegida de un modelo guardado: la última si es "latest". */
function etlPickVersion(model, version) {
    var versions = (model && model.versions) || [];
    if (!versions.length) { return null; }
    if (!version || version === 'latest') { return versions[versions.length - 1]; }
    return versions.filter(function (v) { return String(v.version) === String(version); })[0] || null;
}

function etlModelInfoHtml(v) {
    if (!v) { return ''; }
    var metrics = Object.keys(v.metrics || {}).slice(0, 4).map(function (k) { return k + ' = ' + Number(v.metrics[k]).toPrecision(3); });
    return '<div class="alert alert-info" style="margin-top:8px">' +
        '<div><b>' + etlEscape(v.problem === 'regression' ? gettext('Regression') : gettext('Classification')) + '</b> · ' +
        etlEscape(String(v.created || '').replace('T', ' ').replace('Z', '')) + (v.rows ? ' · ' + v.rows + ' ' + gettext('rows') : '') + '</div>' +
        '<div>' + gettext('Variables') + ': ' + etlEscape((v.features || []).join(', ')) + '</div>' +
        ((v.classes || []).length ? '<div>' + gettext('Classes') + ': ' + etlEscape(v.classes.join(', ')) + '</div>' : '') +
        (metrics.length ? '<div>' + etlEscape(metrics.join(' · ')) + '</div>' : '') +
        (v.description ? '<div class="text-muted">' + etlEscape(v.description) + '</div>' : '') + '</div>';
}

function etlDeleteSavedModel(name, version) {
    var d = $.Deferred();
    $.ajax({
        type: 'POST', url: '/gvsigonline/etl/etl_models_delete/', data: {name: name, version: version || ''},
        beforeSend: function (xhr) { xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken')); }
    }).done(function () { d.resolve(); }).fail(function (xhr) {
        var msg = gettext('The model could not be deleted.');
        try { msg = JSON.parse(xhr.responseText).error || msg; } catch (e) { /* respuesta no JSON */ }
        d.reject(msg);
    });
    return d.promise();
}

defineEtlNode({
    name: 'input_Model',
    // Claves que devuelve collect(): las lee el catálogo del asistente (assistant/shapes.py)
    paramKeys: ['model-name', 'model-version'],
    title: function () { return gettext('Saved Model'); },
    headerColor: '#83d0c9',
    gearColor: '#01b0a0',
    inputs: [],
    outputs: [{label: function () { return gettext('Model'); }, kind: 'model'}],
    body: function (ID) {
        return '<p class="text-muted">' +
            gettext('Uses a model saved earlier with Save Model, without training again. Connect it to Predict Raster or Predict Table.') + '</p>' +
            etlRow(gettext('Model'), '<select id="model-name-' + ID + '" class="form-control"></select>') +
            etlRow(gettext('Version'), '<select id="model-version-' + ID + '" class="form-control"></select>',
                gettext('Latest always uses the most recent version, even if you save a newer one later.')) +
            '<div id="model-info-' + ID + '"></div>' +
            '<div style="margin-top:8px"><a href="#" id="model-delete-version-' + ID + '" class="text-danger"><i class="fa fa-trash"></i> ' +
            gettext('Delete this version') + '</a> · <a href="#" id="model-delete-all-' + ID + '" class="text-danger">' +
            gettext('Delete the whole model') + '</a></div>';
    },
    setup: function (ID) {
        function refresh() {
            var models = $('#model-name-' + ID).data('models') || [];
            var model = models.filter(function (m) { return m.name === $('#model-name-' + ID).val(); })[0];
            var versions = model ? model.versions : [];
            etlFillSelect($('#model-version-' + ID),
                [{value: 'latest', text: gettext('Latest')}].concat(versions.slice().reverse().map(function (v) {
                    return {value: String(v.version), text: gettext('Version') + ' ' + v.version + ' · ' + String(v.created || '').substring(0, 10)};
                })), $('#model-version-' + ID).val());
            $('#model-info-' + ID).html(etlModelInfoHtml(etlPickVersion(model, $('#model-version-' + ID).val())));
        }
        $('#model-name-' + ID).on('change', function () { $('#model-version-' + ID).val('latest'); refresh(); });
        $('#model-version-' + ID).on('change', refresh);
        function remove(version) {
            var name = $('#model-name-' + ID).val();
            if (!name) { return; }
            var question = version ? gettext('Delete this version of the model?') : gettext('Delete the model and all its versions?');
            if (typeof window.confirm === 'function' && !window.confirm(question)) { return; }
            etlDeleteSavedModel(name, version).done(function () {
                etlLoadSavedModels(true).done(function (models) {
                    $('#model-name-' + ID).data('models', models);
                    etlFillSelect($('#model-name-' + ID), models.map(function (m) { return m.name; }), '', gettext('Choose…'));
                    refresh();
                    etlShowError(ID, '');
                });
            }).fail(function (msg) { etlShowError(ID, msg); });
        }
        $('#model-delete-version-' + ID).on('click', function (e) {
            e.preventDefault();
            var v = $('#model-version-' + ID).val();
            if (v && v !== 'latest') { remove(v); } else { remove(String((etlPickVersion(($('#model-name-' + ID).data('models') || [])
                .filter(function (m) { return m.name === $('#model-name-' + ID).val(); })[0], 'latest') || {}).version || '')); }
        });
        $('#model-delete-all-' + ID).on('click', function (e) { e.preventDefault(); remove(''); });
    },
    populate: function (ID, inputs, saved) {
        etlFillSelect($('#model-name-' + ID), [], '', gettext('Loading…'));
        etlLoadSavedModels(true).done(function (models) {
            $('#model-name-' + ID).data('models', models);
            etlFillSelect($('#model-name-' + ID), models.map(function (m) { return m.name; }), saved['model-name'], gettext('Choose…'));
            $('#model-version-' + ID).empty().append($('<option>').val('latest').text(gettext('Latest')));
            $('#model-version-' + ID).val(saved['model-version'] || 'latest');
            $('#model-name-' + ID).trigger('change');
            if (saved['model-version'] && saved['model-version'] !== 'latest') { $('#model-version-' + ID).val(String(saved['model-version'])); $('#model-version-' + ID).trigger('change'); }
            if (!models.length) {
                $('#model-info-' + ID).html('<div class="alert alert-warning">' + gettext('There are no saved models yet. Train one and save it with Save Model.') + '</div>');
            }
        }).fail(function (msg) { etlShowError(ID, msg); });
    },
    collect: function (ID) {
        var name = $('#model-name-' + ID).val();
        if (!name) { throw new Error(gettext('Choose the saved model.')); }
        return {'model-name': name, 'model-version': $('#model-version-' + ID).val() || 'latest'};
    },
    outputSchema: function (inputs, p) {
        // El esquema del puerto de modelo son las variables con las que se entrenó (para comprobar el ráster o la tabla)
        var d = $.Deferred();
        etlLoadSavedModels(false).done(function (models) {
            var model = models.filter(function (m) { return m.name === p['model-name']; })[0];
            var version = etlPickVersion(model, p['model-version']);
            if (!version) { d.reject(gettext('That model or version no longer exists.')); } else { d.resolve((version.features || []).slice()); }
        }).fail(function (msg) { d.reject(msg); });
        return d.promise();
    }
});

/* ---------- Muestreo estratificado ---------- */

var ETL_SAMPLE_POINT_COLUMNS = ['id', 'map_class', 'map_code', 'reference', 'wkb_geometry'];
var ETL_AREA_COLUMNS = ['class', 'map_area', 'estimated_area', 'se_area', 'ci_low', 'ci_high', 'users_accuracy',
                        'users_ci', 'producers_accuracy', 'producers_ci', 'samples', 'reference_samples'];

defineEtlNode({
    name: 'trans_StratifiedSample',
    // Claves que devuelve collect(): las lee el catálogo del asistente (assistant/shapes.py)
    paramKeys: ['per-class', 'seed'],
    defaults: {'per-class': '50', seed: '42'},
    defaultSchema: ETL_SAMPLE_POINT_COLUMNS,
    title: function () { return gettext('Stratified Sample'); },
    headerColor: ETL_PREDICTIVE_COLOR,
    inputs: [{label: function () { return gettext('Raster'); }, kind: 'raster'}],
    outputs: [{label: function () { return gettext('Points'); }, kind: 'table'}],
    body: function (ID) {
        return '<p class="text-muted">' +
            gettext('Picks random points from each class of a classified map, all pixels of a class with the same chance. You then write the real class of each point in the "reference" column (in the field, or looking at an orthophoto) and use them in Estimate Areas. This is the sampling design that makes accuracy and areas statistically valid.') + '</p>' +
            etlRow(gettext('Points per class'), '<input type="number" id="per-class-' + ID + '" min="2" class="form-control">',
                gettext('At least 50 per class is the usual recommendation; more points give narrower intervals. Small classes get all their pixels if they have fewer.')) +
            etlAdvanced(ID, etlRow(gettext('Random seed'), '<input type="number" id="seed-' + ID + '" min="0" class="form-control">',
                gettext('The same seed gives the same points every time.')));
    },
    populate: function (ID, inputs, saved) {
        $('#per-class-' + ID).val(saved['per-class'] || 50);
        $('#seed-' + ID).val(saved.seed || 42);
    },
    collect: function (ID, inputs) {
        if (!inputs[0].length) { throw new Error(gettext('Connect a classified raster first.')); }
        var n = etlParseInt($('#per-class-' + ID).val(), 2);
        var seed = etlParseInt($('#seed-' + ID).val(), 0);
        if (n === undefined || n === null) { throw new Error(gettext('The points per class must be a whole number of at least 2.')); }
        if (seed === undefined || seed === null) { throw new Error(gettext('The random seed must be a whole number.')); }
        return {'per-class': String(n), seed: String(seed)};
    },
    outputSchema: function () { return ETL_SAMPLE_POINT_COLUMNS.slice(); }
});

/* ---------- Estimar superficie ---------- */

defineEtlNode({
    name: 'trans_AreaEstimate',
    // Claves que devuelve collect(): las lee el catálogo del asistente (assistant/shapes.py)
    paramKeys: ['reference-attr', 'confidence-level'],
    title: function () { return gettext('Estimate Areas'); },
    headerColor: ETL_PREDICTIVE_COLOR,
    inputs: [{label: function () { return gettext('Raster'); }, kind: 'raster'},
             {label: function () { return gettext('Reference points'); }, kind: 'table'}],
    outputs: [{label: function () { return gettext('Areas'); }, kind: 'table'},
              {label: function () { return gettext('Report'); }, kind: 'table'}],
    body: function (ID) {
        return '<p class="text-muted">' +
            gettext('Estimates the real area of each class, correcting the errors of the map with reference points, and gives its confidence interval (Olofsson et al., 2014). Counting the pixels of a class gives a biased area; this is the recommended way to report areas.') + '</p>' +
            etlRow(gettext('Column with the real class'), '<select id="reference-attr-' + ID + '" class="form-control"></select>',
                gettext('The points must come from a random sample stratified by map class, such as the one made by Stratified Sample.')) +
            etlRow(gettext('Confidence level'), '<select id="confidence-level-' + ID + '" class="form-control"></select>');
    },
    populate: function (ID, inputs, saved) {
        var cols = etlUserColumns(inputs[1]);
        etlFillSelect($('#reference-attr-' + ID), cols, saved['reference-attr'] || (cols.indexOf('reference') !== -1 ? 'reference' : ''), gettext('Choose…'));
        etlFillSelect($('#confidence-level-' + ID), [{value: '0.90', text: '90 %'}, {value: '0.95', text: '95 %'},
            {value: '0.99', text: '99 %'}], saved['confidence-level'] || '0.95');
    },
    collect: function (ID, inputs) {
        if (!inputs[0].length) { throw new Error(gettext('Connect a classified raster first.')); }
        if (!inputs[1].length) { throw new Error(gettext('Connect the reference points first.')); }
        var attr = $('#reference-attr-' + ID).val();
        if (!attr) { throw new Error(gettext('Choose the column with the real class.')); }
        return {'reference-attr': attr, 'confidence-level': $('#confidence-level-' + ID).val() || '0.95'};
    },
    outputSchema: function () { return [ETL_AREA_COLUMNS.slice(), ETL_PIXEL_REPORT_COLUMNS.slice()]; }
});

/* ---------- Publicar ráster ---------- */

var etlPublishTargets = {loadedAt: 0, data: null};

function etlLoadPublishTargets() {
    var d = $.Deferred();
    if (etlPublishTargets.data && Date.now() - etlPublishTargets.loadedAt < 60000) {
        return d.resolve(etlPublishTargets.data).promise();
    }
    $.getJSON('/gvsigonline/etl/etl_raster_publish_targets/').done(function (data) {
        etlPublishTargets = {loadedAt: Date.now(), data: data};
        d.resolve(data);
    }).fail(function () { d.reject(gettext('The workspaces and layer groups could not be loaded.')); });
    return d.promise();
}

defineEtlNode({
    name: 'output_RasterPublish',
    // Claves que devuelve collect(): las lee el catálogo del asistente (assistant/shapes.py)
    paramKeys: ['workspace', 'layer-group', 'title', 'layer-name', 'on-existing', 'public', 'update-style', 'band', 'ramp-min', 'ramp-max', 'abstract'],
    title: function () { return gettext('Publish Raster'); },
    headerColor: '#e8ca93',
    gearColor: '#e79600',
    inputs: [{label: function () { return gettext('Raster'); }, kind: 'raster'}],
    outputs: [],
    body: function (ID) {
        return '<p class="text-muted">' +
            gettext('Publishes the raster as a layer, ready to add to a project. The classes get a colour style.') + '</p>' +
            '<div class="row"><div class="col-md-6">' +
            etlRow(gettext('Workspace'), '<select id="workspace-' + ID + '" class="form-control"></select>') + '</div>' +
            '<div class="col-md-6">' +
            etlRow(gettext('Layer group'), '<select id="layer-group-' + ID + '" class="form-control"></select>') + '</div></div>' +
            etlRow(gettext('Layer title'), '<input type="text" id="title-' + ID + '" class="form-control" maxlength="150">') +
            etlRow(gettext('Layer name'), '<input type="text" id="layer-name-' + ID + '" class="form-control" maxlength="60">',
                gettext('Letters, digits and underscores. If you leave it empty it is made from the title.')) +
            etlRow(gettext('If the layer already exists'), '<select id="on-existing-' + ID + '" class="form-control"></select>',
                gettext('Replacing keeps the layer and its permissions: only the raster changes.')) +
            '<div class="checkbox"><label><input type="checkbox" id="public-' + ID + '"> ' + gettext('Public layer') + '</label></div>' +
            etlAdvanced(ID,
                etlRow(gettext('Style when replacing'), '<select id="update-style-' + ID + '" class="form-control"></select>',
                    gettext('The style created by this node is updated when the classes or the value range change. Classes that already existed keep their colour. A style you made yourself is never touched.')) +
                etlRow(gettext('Band to publish'), '<select id="band-' + ID + '" class="form-control"></select>',
                    gettext('For a raster with several bands. By default it is published as it is.')) +
                '<div class="row"><div class="col-md-6">' + etlRow(gettext('Colour ramp: minimum'),
                    '<input type="number" id="ramp-min-' + ID + '" step="any" class="form-control" placeholder="' + etlEscape(gettext('Automatic')) + '">') + '</div>' +
                '<div class="col-md-6">' + etlRow(gettext('Colour ramp: maximum'),
                    '<input type="number" id="ramp-max-' + ID + '" step="any" class="form-control" placeholder="' + etlEscape(gettext('Automatic')) + '">') + '</div></div>' +
                '<p class="help-block">' + gettext('Only for rasters with values (not classes). The confidence always goes from 0 to 1.') + '</p>' +
                etlRow(gettext('Layer description'), '<input type="text" id="abstract-' + ID + '" class="form-control" maxlength="500">'));
    },
    populate: function (ID, inputs, saved) {
        etlFillSelect($('#on-existing-' + ID), [
            {value: 'replace', text: gettext('Replace its raster')},
            {value: 'fail', text: gettext('Stop with an error')}], saved['on-existing'] || 'replace');
        $('#title-' + ID).val(saved.title || '');
        $('#layer-name-' + ID).val(saved['layer-name'] || '');
        $('#public-' + ID).prop('checked', saved['public'] === 'true');
        etlFillSelect($('#update-style-' + ID), [
            {value: 'auto', text: gettext('Update it only if the classes or the range change')},
            {value: 'yes', text: gettext('Always regenerate it')},
            {value: 'no', text: gettext('Never touch it')}], saved['update-style'] || 'auto');
        // Solo tiene sentido con varias bandas (un ráster predicho o de confianza tiene una)
        var bands = inputs[0].length > 1 ? etlUserColumns(inputs[0]) : [];
        etlFillSelect($('#band-' + ID), bands.map(function (b) { return {value: b, text: b}; }), saved.band || '', gettext('All bands'));
        $('#band-' + ID).closest('.form-group').toggle(bands.length > 1);
        $('#ramp-min-' + ID).val(saved['ramp-min'] || '');
        $('#ramp-max-' + ID).val(saved['ramp-max'] || '');
        $('#abstract-' + ID).val(saved.abstract || '');
        etlFillSelect($('#workspace-' + ID), [], '', gettext('Loading…'));
        etlFillSelect($('#layer-group-' + ID), [], '', gettext('Loading…'));
        etlLoadPublishTargets().done(function (data) {
            etlFillSelect($('#workspace-' + ID), data.workspaces.map(function (w) { return w.name; }), saved.workspace, gettext('Choose…'));
            etlFillSelect($('#layer-group-' + ID), data.layer_groups.map(function (g) { return {value: g.name, text: g.title}; }),
                saved['layer-group'], gettext('Choose…'));
        }).fail(function (msg) { etlShowError(ID, msg); });
    },
    collect: function (ID, inputs) {
        if (!inputs[0].length) { throw new Error(gettext('Connect a raster first.')); }
        var ws = $('#workspace-' + ID).val();
        var group = $('#layer-group-' + ID).val();
        var title = $('#title-' + ID).val().trim();
        var name = etlSafeLayerName($('#layer-name-' + ID).val().trim() || title);
        if (!ws) { throw new Error(gettext('Choose the workspace.')); }
        if (!group) { throw new Error(gettext('Choose the layer group.')); }
        if (!name) { throw new Error(gettext('Write a title or a name for the layer.')); }
        var lo = etlParseFloat($('#ramp-min-' + ID).val(), -Infinity);
        var hi = etlParseFloat($('#ramp-max-' + ID).val(), -Infinity);
        if (lo === undefined || hi === undefined) { throw new Error(gettext('The colour ramp limits must be numbers.')); }
        if ((lo === null) !== (hi === null)) { throw new Error(gettext('Fill in both limits of the colour ramp, or leave both empty.')); }
        if (lo !== null && hi <= lo) { throw new Error(gettext('The maximum of the colour ramp must be greater than the minimum.')); }
        return {
            workspace: ws, 'layer-group': group, title: title || name, 'layer-name': name,
            'on-existing': $('#on-existing-' + ID).val() || 'replace',
            'public': $('#public-' + ID).is(':checked') ? 'true' : '',
            'update-style': $('#update-style-' + ID).val() || 'auto',
            band: inputs[0].length > 1 ? ($('#band-' + ID).val() || '') : '',
            'ramp-min': lo === null ? '' : String(lo), 'ramp-max': hi === null ? '' : String(hi),
            abstract: $('#abstract-' + ID).val().trim()
        };
    },
    outputSchema: function () { return []; }
});

/* ---------- Publicar capa (PostGIS) ---------- */

var etlLayerTargets = {loadedAt: 0, data: null};

function etlLoadLayerTargets(force) {
    var d = $.Deferred();
    if (!force && etlLayerTargets.data && Date.now() - etlLayerTargets.loadedAt < 60000) {
        return d.resolve(etlLayerTargets.data).promise();
    }
    $.getJSON('/gvsigonline/etl/etl_layer_publish_targets/').done(function (data) {
        etlLayerTargets = {loadedAt: Date.now(), data: data};
        d.resolve(data);
    }).fail(function () { d.reject(gettext('The data stores and layer groups could not be loaded.')); });
    return d.promise();
}

/* Formulario de siempre para crear un almacén: al guardar redirige a la lista, se cierra y se recarga. */
function etlOpenDatastoreForm(onDone) {
    var popup = window.open('/gvsigonline/services/datastore_add/', 'etl-new-datastore',
        'width=900, height=700,left=150,top=100,toolbar=0,status=0,scrollbars=1');
    if (!popup) { return; }
    var watch = setInterval(function () {
        var saved = false;
        try {
            saved = !popup.closed && popup.location.pathname.indexOf('datastore_list') !== -1;
        } catch (e) {}
        if (saved) { popup.close(); }
        if (saved || popup.closed) {
            clearInterval(watch);
            onDone();
        }
    }, 500);
}

defineEtlNode({
    name: 'output_LayerPublish',
    // Claves que devuelve collect(): las lee el catálogo del asistente (assistant/shapes.py)
    paramKeys: ['datastore', 'layer-group', 'title', 'layer-name', 'on-existing', 'public', 'abstract'],
    title: function () { return gettext('Publish Layer'); },
    headerColor: '#e8ca93',
    gearColor: '#e79600',
    inputs: [{label: function () { return gettext('Layer'); }}],
    outputs: [],
    body: function (ID) {
        return '<p class="text-muted">' +
            gettext('Saves the table in a data store and publishes it as a layer with a default style.') + '</p>' +
            '<div class="row"><div class="col-md-6">' +
            etlRow(gettext('Data store'), '<select id="datastore-' + ID + '" class="form-control"></select>') +
            '<a href="#" id="new-datastore-' + ID + '">' + gettext('Create a new data store…') + '</a></div>' +
            '<div class="col-md-6">' +
            etlRow(gettext('Layer group'), '<select id="layer-group-' + ID + '" class="form-control"></select>') + '</div></div>' +
            etlRow(gettext('Layer title'), '<input type="text" id="title-' + ID + '" class="form-control" maxlength="150">') +
            etlRow(gettext('Layer name'), '<input type="text" id="layer-name-' + ID + '" class="form-control" maxlength="60">',
                gettext('Letters, digits and underscores. If you leave it empty it is made from the title.')) +
            etlRow(gettext('If the layer already exists'), '<select id="on-existing-' + ID + '" class="form-control"></select>',
                gettext('Replacing keeps the layer, its style and its permissions: only the data changes.')) +
            '<div class="checkbox"><label><input type="checkbox" id="public-' + ID + '"> ' + gettext('Public layer') + '</label></div>' +
            etlRow(gettext('Layer description'), '<input type="text" id="abstract-' + ID + '" class="form-control" maxlength="500">');
    },
    populate: function (ID, inputs, saved) {
        etlFillSelect($('#on-existing-' + ID), [
            {value: 'replace', text: gettext('Replace its data')},
            {value: 'fail', text: gettext('Stop with an error')}], saved['on-existing'] || 'replace');
        $('#title-' + ID).val(saved.title || '');
        $('#layer-name-' + ID).val(saved['layer-name'] || '');
        $('#public-' + ID).prop('checked', saved['public'] === 'true');
        $('#abstract-' + ID).val(saved.abstract || '');
        function fill(force) {
            var current = $('#datastore-' + ID).val() || saved.datastore;
            etlFillSelect($('#datastore-' + ID), [], '', gettext('Loading…'));
            etlFillSelect($('#layer-group-' + ID), [], '', gettext('Loading…'));
            etlLoadLayerTargets(force).done(function (data) {
                etlFillSelect($('#datastore-' + ID), data.datastores, current, gettext('Choose…'));
                etlFillSelect($('#layer-group-' + ID), data.layer_groups.map(function (g) { return {value: g.name, text: g.title}; }),
                    saved['layer-group'], gettext('Choose…'));
            }).fail(function (msg) { etlShowError(ID, msg); });
        }
        $('#new-datastore-' + ID).off('click').on('click', function (e) {
            e.preventDefault();
            etlOpenDatastoreForm(function () { fill(true); });
        });
        fill(false);
    },
    collect: function (ID, inputs) {
        if (!inputs[0].length) { throw new Error(gettext('Connect a table first.')); }
        var store = $('#datastore-' + ID).val();
        var group = $('#layer-group-' + ID).val();
        var title = $('#title-' + ID).val().trim();
        var name = etlSafeLayerName($('#layer-name-' + ID).val().trim() || title);
        if (!store) { throw new Error(gettext('Choose the data store.')); }
        if (!group) { throw new Error(gettext('Choose the layer group.')); }
        if (!name) { throw new Error(gettext('Write a title or a name for the layer.')); }
        return {
            datastore: store, 'layer-group': group, title: title || name, 'layer-name': name,
            'on-existing': $('#on-existing-' + ID).val() || 'replace',
            'public': $('#public-' + ID).is(':checked') ? 'true' : '',
            abstract: $('#abstract-' + ID).val().trim()
        };
    },
    outputSchema: function () { return []; }
});

etlInstallConnectionGuard();

/* ------------------------------------------------------------------ */
/* Manejadores de esquema para el propagador                           */
/* ------------------------------------------------------------------ */

(function registerPredictiveHandlers() {
    if (typeof SCHEMA_HANDLERS === 'undefined') {
        return;
    }
    function params0(params) {
        return params && params.parameters && params.parameters[0] ? params.parameters[0] : {};
    }

    SCHEMA_HANDLERS.input_Raster = {
        computeOutputSchema: function (inputs, params) { return (params && params.schema) || []; },
        validateParams: function (inputs, params) { return !!params0(params)['raster-file']; }
    };

    SCHEMA_HANDLERS.trans_RasterSample = {
        computeOutputSchema: function (inputs, params) { return etlSampleOutput(etlPerPortSchemas(inputs, 2), params0(params)); },
        validateParams: function (inputs, params) {
            var per = etlPerPortSchemas(inputs, 2);
            var cls = params0(params)['class-attr'];
            return !!cls && per[1].indexOf(cls) !== -1 && per[0].indexOf(cls) === -1;
        }
    };

    SCHEMA_HANDLERS.trans_RandomForest = {
        computeOutputSchema: function (inputs, params) { return etlForestOutput(etlPerPortSchemas(inputs, 1), params0(params)); },
        validateParams: function (inputs, params) {
            var cols = etlPerPortSchemas(inputs, 1)[0];
            var p = params0(params);
            return !!p.target && cols.indexOf(p.target) !== -1 && Array.isArray(p.features) && p.features.length > 0 &&
                etlMissing(p.features, cols).length === 0;
        }
    };

    SCHEMA_HANDLERS.trans_RasterPredict = {
        computeOutputSchema: function () { return [['prediction'], ['confidence']]; },
        validateParams: function (inputs) {
            var per = etlPerPortSchemas(inputs, 2);
            return per[0].length > 0 && per[1].length > 0 && etlMissing(per[1], per[0]).length === 0;
        }
    };

    SCHEMA_HANDLERS.trans_RasterMajority = {
        computeOutputSchema: function (inputs) {
            var cols = etlPerPortSchemas(inputs, 1)[0];
            return cols.length ? cols : ['prediction'];
        },
        validateParams: function (inputs) { return etlPerPortSchemas(inputs, 1)[0].length > 0; }
    };

    SCHEMA_HANDLERS.trans_RasterIndex = {
        computeOutputSchema: function (inputs, params) {
            var bands = etlUserColumns(etlPerPortSchemas(inputs, 1)[0]);
            var p = params0(params);
            return bands.concat([etlBandName(p.name || p.index, bands)]);
        },
        validateParams: function (inputs, params) {
            var bands = etlPerPortSchemas(inputs, 1)[0];
            var p = params0(params);
            var def = ETL_INDICES[p.index];
            if (!def || !bands.length) { return false; }
            return def.roles.every(function (role, i) { return bands.indexOf(p['band-' + (i + 1)]) !== -1; });
        }
    };

    SCHEMA_HANDLERS.trans_StratifiedSample = {
        computeOutputSchema: function () { return ETL_SAMPLE_POINT_COLUMNS.slice(); },
        validateParams: function (inputs) { return etlPerPortSchemas(inputs, 1)[0].length > 0; }
    };

    SCHEMA_HANDLERS.trans_AreaEstimate = {
        computeOutputSchema: function () { return [ETL_AREA_COLUMNS.slice(), ETL_PIXEL_REPORT_COLUMNS.slice()]; },
        validateParams: function (inputs, params) {
            var per = etlPerPortSchemas(inputs, 2);
            var attr = params0(params)['reference-attr'];
            return per[0].length > 0 && !!attr && per[1].indexOf(attr) !== -1;
        }
    };

    SCHEMA_HANDLERS.trans_RasterClip = {
        computeOutputSchema: function (inputs) { return etlPerPortSchemas(inputs, 2)[0]; },
        validateParams: function (inputs) {
            var per = etlPerPortSchemas(inputs, 2);
            return per[0].length > 0 && per[1].length > 0;
        }
    };

    SCHEMA_HANDLERS.trans_ClassAssess = {
        computeOutputSchema: function () { return [ETL_PIXEL_REPORT_COLUMNS.slice(), ETL_MATRIX_COLUMNS.slice()]; },
        validateParams: function (inputs, params) {
            var per = etlPerPortSchemas(inputs, 2);
            var cls = params0(params)['class-attr'];
            return per[0].length > 0 && !!cls && per[1].indexOf(cls) !== -1;
        }
    };

    SCHEMA_HANDLERS.trans_RasterStack = {
        computeOutputSchema: function (inputs, params) {
            var p = params0(params);
            return etlStackBands(etlPerPortSchemas(inputs, 4), [p['prefix-1'], p['prefix-2'], p['prefix-3'], p['prefix-4']]);
        },
        validateParams: function (inputs) {
            return etlPerPortSchemas(inputs, 4).filter(function (b) { return b.length > 0; }).length >= 2;
        }
    };

    SCHEMA_HANDLERS.trans_TablePredict = {
        computeOutputSchema: function (inputs, params) {
            var per = etlPerPortSchemas(inputs, 2);
            var column = etlBandName(params0(params).column || 'prediction', []);
            return per[0].concat([column, column + '_confidence']);
        },
        validateParams: function (inputs) {
            var per = etlPerPortSchemas(inputs, 2);
            return per[0].length > 0 && per[1].length > 0 && etlMissing(per[1], per[0]).length === 0;
        }
    };

    SCHEMA_HANDLERS.output_ModelSave = {
        computeOutputSchema: function () { return []; },
        validateParams: function (inputs, params) { return !!etlSafeModelName(params0(params)['model-name']); }
    };

    SCHEMA_HANDLERS.input_Model = {
        computeOutputSchema: function (inputs, params) { return (params && params.schema) || []; },
        validateParams: function (inputs, params) { return !!params0(params)['model-name']; }
    };

    SCHEMA_HANDLERS.trans_RasterPolygonize = {
        computeOutputSchema: function () { return ETL_POLYGON_COLUMNS.slice(); },
        validateParams: function (inputs) { return etlPerPortSchemas(inputs, 1)[0].length > 0; }
    };

    SCHEMA_HANDLERS.output_LayerPublish = {
        computeOutputSchema: function () { return []; },
        validateParams: function (inputs, params) {
            var p = params0(params);
            return !!(p.datastore && p['layer-group'] && p['layer-name']);
        }
    };

    SCHEMA_HANDLERS.output_RasterPublish = {
        computeOutputSchema: function () { return []; },
        validateParams: function (inputs, params) {
            var p = params0(params);
            return !!(p.workspace && p['layer-group'] && p['layer-name']);
        }
    };
})();
