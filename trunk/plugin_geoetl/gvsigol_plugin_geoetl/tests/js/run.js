const assert = require('assert');
const { makeEnv, tick } = require('./harness');

let passed = 0, failed = 0;
// jsdom crea arrays de otro 'realm': se compara el contenido, no el prototipo
const same = (a, b, msg) => assert.strictEqual(JSON.stringify(a), JSON.stringify(b), msg);
async function test(name, fn) {
    try { await fn(); passed++; console.log('  ok   ' + name); }
    catch (e) { failed++; console.log('  FAIL ' + name + '\n       ' + (e.stack || e).split('\n').slice(0, 4).join('\n       ')); }
}


// Claves declaradas (paramKeys) por cada nodo en PredictiveShapes.js
const SRC = require('fs').readFileSync(require('path').join(__dirname, '..', '..', 'static', 'js', 'PredictiveShapes.js'), 'utf8');
function declaredKeys(type) {
    const m = SRC.match(new RegExp("name: '" + type + "',[\\s\\S]*?paramKeys: \\[([^\\]]*)\\]"));
    return m[1].split(',').map((x) => x.trim().replace(/['"]/g, '')).filter(Boolean).sort();
}
function checkKeys(type, task) {
    same(Object.keys(task.parameters[0]).sort(), declaredKeys(type), type + ': claves guardadas vs paramKeys');
}

(async () => {
    const w = makeEnv();
    const $ = w.$;

    // Crea la figura y devuelve utilidades para manejar su diálogo
    function node(type, inputs) {
        const fig = new w[type]();
        fig.addEntity('id');
        const id = fig.id;
        w.__inputs[id] = inputs;
        const icon = fig.classLabel.kids[0];
        const dialog = $('#dialog-' + type + '-' + id);
        return {
            fig, id, icon, dialog,
            open: () => icon.handlers.click(),
            accept: () => $('#accept-' + id).trigger('click'),
            error: () => ($('#error-' + id).is(':visible') || $('#error-' + id).css('display') !== 'none') ? $('#error-' + id).text() : '',
            f: (name) => $('#' + name + '-' + id),
            task: () => w.jsonParams.find((t) => t.id === id)
        };
    }

    console.log('Cabecera de los nodos (id nN)');
    const fakeCanvas = (figs) => ({ getFigures: () => ({ each(fn) { figs.forEach((f, i) => fn(i, f)); } }) });
    await test('id: alias válidos, documento y siguiente libre', () => {
        assert.strictEqual(w.etlAliasNumber('n12'), 12);
        assert.strictEqual(w.etlAliasNumber('n0'), 0);
        assert.strictEqual(w.etlAliasNumber('x3'), 0);
        assert.strictEqual(w.etlAliasNumber('6f1c-uuid'), 0);
        assert.strictEqual(w.etlAliasFromDocument({ id: 'n4' }), 'n4');               // asistente
        assert.strictEqual(w.etlAliasFromDocument({ id: 'uuid', alias: 'n2' }), 'n2'); // guardado
        assert.strictEqual(w.etlAliasFromDocument({ id: 'uuid' }), null);              // workspace antiguo
        assert.strictEqual(w.etlNextAlias(null, { n1: true, n7: true }), 'n8');
    });
    await test('id: se conserva, no se repite y no se reutiliza al borrar', () => {
        const figs = [];
        const canvas = fakeCanvas(figs);
        const add = (alias) => { const f = { etlAlias: alias }; w.etlAssignAlias(canvas, f); figs.push(f); return f; };
        assert.strictEqual(add().etlAlias, 'n1');
        assert.strictEqual(add().etlAlias, 'n2');
        assert.strictEqual(add('n9').etlAlias, 'n9');      // alias guardado
        assert.strictEqual(add('n2').etlAlias, 'n10');     // duplicado -> nuevo
        figs.splice(2, 1);                                 // se borra n9
        assert.strictEqual(add().etlAlias, 'n11');         // no vuelve a usar n9 ni n10
        const again = figs[0];                             // deshacer/rehacer: la misma figura conserva su id
        assert.strictEqual(w.etlAssignAlias(canvas, again), 'n1');
    });
    await test('cabecera: engranaje e id a la derecha sin solapar el título', () => {
        const d = w.draw2d;
        const saved = { Locator: d.layout.locator.Locator, Icon: d.shape.icon.Icon };
        d.layout.locator.Locator = { extend(def) {
            function C(a) { def.init.call(this, a); }
            C.prototype = Object.assign({ _super() {} }, def); return C; } };
        d.shape.icon.Icon = d.shape.icon.Gear;
        const geo = (o, wdt, hgt) => Object.assign(o, { w: wdt, h: hgt,
            getWidth() { return this.w; }, getHeight() { return this.h; },
            getParent() { return this.parent; }, setPosition(x, y) { this.x = x; this.y = y; },
            on(ev, fn) { (this.ev = this.ev || {})[ev] = fn; } });
        const LabelProto = d.shape.basic.Label.prototype;
        const extra = ['getWidth', 'getHeight', 'getParent', 'setPosition', 'on'];
        extra.forEach((k) => { LabelProto[k] = function () { geo(this, 28, 14); return this[k].apply(this, arguments); }; });
        try {
            const label = geo({ padding: { top: 10, right: 10, bottom: 10, left: 10 }, getText: () => 'Un título muy largo',
                children: { list: [], each(fn) { this.list.forEach((e, i) => fn(i, e)); } },
                add(f, loc) { this.children.list.push({ figure: f, locator: loc }); f.parent = this; },
                setPadding(p) { Object.assign(this.padding, p); }, fireEvent() {} }, 240, 34);
            const gear = geo(new d.shape.icon.Gear({ color: '#e2504c' }), 13, 13);
            label.add(gear, 'XYRel');
            const fig = { classLabel: label, etlAlias: 'n3' };
            w.etlDecorateHeader(fig);
            const [gearE, badgeE] = label.children.list;
            assert.strictEqual(gearE.figure, gear);                       // mismo objeto: conserva el clic
            assert.notStrictEqual(gearE.locator, 'XYRel');
            gearE.locator.relocate(0, gear);
            badgeE.locator.relocate(1, badgeE.figure);
            assert.strictEqual(badgeE.figure.text, 'n3');
            assert.strictEqual(gear.x, 240 - 10 - 13);                    // anclado a la derecha
            assert.strictEqual(gear.y, Math.round((34 - 13) / 2));        // centrado
            assert.ok(badgeE.figure.x + 28 <= gear.x - 6, 'id antes del engranaje');
            // el texto del título termina donde empieza el id (con separación)
            assert.ok(240 - label.padding.right <= badgeE.figure.x - 6, 'el título reserva el hueco');
            w.etlDecorateHeader(fig);                                     // idempotente
            assert.strictEqual(label.children.list.length, 2);
        } finally {
            d.layout.locator.Locator = saved.Locator; d.shape.icon.Icon = saved.Icon;
            extra.forEach((k) => { delete LabelProto[k]; });
        }
    });

    console.log('Lógica pura');
    await test('puertos: tabla/ráster/modelo', () => {
        assert.strictEqual(w.etlCheckPortKinds('raster', 'raster').ok, true);
        const bad = w.etlCheckPortKinds('table', 'raster');
        assert.strictEqual(bad.ok, false);
        assert.ok(/a table.*a raster/.test(bad.message), bad.message);
        assert.strictEqual(w.etlKindOfPort({}), 'table');           // nodos antiguos = tablas
        assert.strictEqual(w.etlKindOfPort({ etlKind: 'model' }), 'model');
    });
    await test('guarda de conexión veta y avisa; permite lo válido', () => {
        const mk = (k) => ({ etlKind: k });
        const req = (a, b) => ({ getPolicy: () => 'CONNECT', source: a, target: b });
        const inPort = new w.draw2d.InputPort();
        assert.strictEqual(inPort.createCommand(req(mk('table'), mk('raster'))), null);
        assert.strictEqual(w.messageBox.calls.length, 1);
        assert.strictEqual(inPort.createCommand(req(mk('raster'), mk('raster'))), 'cmd-in');
        assert.strictEqual(inPort.createCommand(req({}, {})), 'cmd-in');                 // tabla-tabla (nodos antiguos)
        assert.strictEqual(new w.draw2d.OutputPort().createCommand(req(mk('model'), mk('table'))), null);
        assert.strictEqual(inPort.createCommand({ getPolicy: () => 'MOVE' }), 'cmd-in'); // otras órdenes pasan
    });
    await test('etlPerPortSchemas', () => {
        same(Array.from(w.etlPerPortSchemas(['a', 'b'], 1)[0]), ['a', 'b']);
        same(JSON.parse(JSON.stringify(w.etlPerPortSchemas([['a'], ['b']], 2))), [['a'], ['b']]);
        same(JSON.parse(JSON.stringify(w.etlPerPortSchemas([], 2))), [[], []]);
        same(JSON.parse(JSON.stringify(w.etlPerPortSchemas(undefined, 1))), [[]]);
    });
    await test('parseInt/parseFloat/safeLayerName', () => {
        assert.strictEqual(w.etlParseInt('', 1), null);
        assert.strictEqual(w.etlParseInt('5', 1), 5);
        assert.strictEqual(w.etlParseInt('0', 1), undefined);
        assert.strictEqual(w.etlParseInt('2.5', 1), undefined);
        assert.strictEqual(w.etlParseInt('60', 0, 50), undefined);
        assert.strictEqual(w.etlParseFloat('1,5', 0), 1.5);
        assert.strictEqual(w.etlParseFloat('-1', 0), undefined);
        assert.strictEqual(w.etlSafeLayerName('Capa de Prueba ñ'), 'capa_de_prueba_n');
        assert.strictEqual(w.etlSafeLayerName('2024 Mapa'), 'l_2024_mapa');
        assert.strictEqual(w.etlSafeLayerName('   '), '');
    });
    await test('etlEscape evita inyección de HTML', () => {
        assert.strictEqual(w.etlEscape('<img src=x onerror=1>"\''), '&lt;img src=x onerror=1&gt;&quot;&#39;');
    });

    console.log('Estructura de los nodos');
    await test('puertos de cada nodo: orden, tipos y listLabel', () => {
        const expect = {
            input_Raster: [[], ['raster']],
            trans_RasterSample: [['raster', 'table'], ['table']],
            trans_RandomForest: [['table'], ['table', 'model', 'table']],
            trans_RasterPredict: [['raster', 'model'], ['raster', 'raster']],
            trans_RasterMajority: [['raster'], ['raster']],
            trans_RasterIndex: [['raster'], ['raster']],
            trans_ClassAssess: [['raster', 'table'], ['table', 'table']],
            trans_RasterClip: [['raster', 'table'], ['raster']],
            trans_StratifiedSample: [['raster'], ['table']],
            trans_AreaEstimate: [['raster', 'table'], ['table', 'table']],
            trans_RasterStack: [['raster', 'raster', 'raster', 'raster'], ['raster']],
            trans_TablePredict: [['table', 'model'], ['table']],
            output_ModelSave: [['model'], []],
            input_Model: [[], ['model']],
            trans_RasterPolygonize: [['raster'], ['table']],
            output_RasterPublish: [['raster'], []]
        };
        Object.keys(expect).forEach((type) => {
            const before = w.listLabel.length;
            const fig = new w[type](); fig.addEntity('id');
            const entry = w.listLabel[w.listLabel.length - 1];
            assert.strictEqual(w.listLabel.length, before + 1, type);
            assert.strictEqual(entry[0], fig.id);
            assert.strictEqual(entry[1].length, expect[type][0].length, type + ' entradas');
            assert.strictEqual(entry[2].length, expect[type][1].length, type + ' salidas');
            // el orden de los puertos persistidos: entradas primero, luego salidas
            const ports = fig.children.slice(1).map((l) => l.port);   // el primer hijo es la cabecera
            const kinds = ports.map((p) => p.etlKind);
            same(kinds, expect[type][0].concat(expect[type][1]), type);
            same(ports.map((p) => p.kind), expect[type][0].map(() => 'input').concat(expect[type][1].map(() => 'output')));
            ports.forEach((p) => assert.ok(/^(input|output)_/.test(p.name), p.name));
            assert.ok(fig.cssClass.startsWith(type.split('_')[0]), 'cssClass');
        });
    });
    await test('puertos ráster y modelo van coloreados', () => {
        const fig = new w.trans_RandomForest(); fig.addEntity('id');
        const [data, report, model, matrix] = fig.children.slice(1).map((l) => l.port);
        assert.strictEqual(data.bg, undefined);
        assert.strictEqual(report.bg, undefined);
        assert.strictEqual(model.bg, '#7e57c2');
        assert.strictEqual(matrix.bg, undefined);   // la matriz de confusión es una tabla
    });
    await test('el punto y el texto de los conectores ráster usan el mismo color (rosa frambuesa)', () => {
        const color = w.ETL_PORT_KINDS.raster.color;
        assert.strictEqual(color, '#c2185b');
        ['input_Raster', 'trans_RasterClip', 'trans_RasterPredict', 'output_RasterPublish'].forEach((type) => {
            const fig = new w[type](); fig.addEntity('id');
            fig.children.slice(1).forEach((label) => {
                const kind = label.port.etlKind;
                const expected = kind === 'table' ? '#107dac' : w.ETL_PORT_KINDS[kind].color;
                assert.strictEqual(label.attr.fontColor, expected, type + ' texto ' + kind);
                assert.strictEqual(label.port.bg, kind === 'table' ? undefined : expected, type + ' punto ' + kind);
            });
        });
        // los nodos de la categoría Ráster llevan su cabecera; los predictivos, la suya
        const clip = new w.trans_RasterClip(); const rf = new w.trans_RandomForest();
        assert.strictEqual(clip.classLabel.attr.bgColor, w.ETL_RASTER_COLOR);
        assert.strictEqual(w.ETL_RASTER_COLOR, '#f06292');
        assert.strictEqual(rf.classLabel.attr.bgColor, w.ETL_PREDICTIVE_COLOR);
    });

    await test('los nodos que funcionan sin configurar nacen configurados; los demás no', () => {
        // Un nodo sin entrada en jsonParams se guarda como null y rompe la ejecución
        const predict = node('trans_RasterPredict', [['rojo'], ['rojo']]);
        const poly = node('trans_RasterPolygonize', [['prediction']]);
        same(predict.task().parameters[0], { configured: 'true' });
        same(predict.task().schema, [['prediction'], ['confidence']]);
        same(poly.task().parameters[0], { classes: '', 'min-area': '0', simplify: '0', connectivity: '4' });
        same(poly.task().schema, ['class_name', 'class_code', 'area', 'wkb_geometry']);
        // y sus claves coinciden con las declaradas para el asistente
        checkKeys('trans_RasterPredict', predict.task());
        checkKeys('trans_RasterPolygonize', poly.task());
        const clean = node('trans_RasterMajority', [['prediction']]);
        same(clean.task().parameters[0], { mode: 'majority', window: '3', iterations: '1', 'min-pixels': '4', connectivity: '4' });
        checkKeys('trans_RasterMajority', clean.task());
        ['trans_RasterSample', 'trans_RandomForest', 'trans_RasterIndex', 'trans_AreaEstimate', 'input_Raster', 'output_RasterPublish'].forEach((t) => {
            assert.strictEqual(node(t, []).task(), undefined, t + ' necesita configuración del usuario');
        });
        // al aceptar, la entrada se sustituye (no se duplica)
        const before = w.jsonParams.filter((t) => t.id === poly.id).length;
        poly.open(); poly.f('min-area').val('25'); poly.accept();
        assert.strictEqual(w.jsonParams.filter((t) => t.id === poly.id).length, before);
        assert.strictEqual(poly.task().parameters[0]['min-area'], '25');
    });

    console.log('Diálogo: Random Forest');
    await test('rellena objetivo y predictoras; excluye geometría; pre-marca todas menos el objetivo', async () => {
        const n = node('trans_RandomForest', ['ogc_fid', 'wkb_geometry', 'rojo', 'verde', 'ir', 'clase']);
        n.open();
        const opts = n.f('target').find('option').map((i, o) => o.value).get();
        same(opts, ['', 'rojo', 'verde', 'ir', 'clase']);
        assert.strictEqual($('.rf-feature-' + n.id).length, 4);
        n.f('target').val('clase').trigger('change');
        const feats = $('.rf-feature-' + n.id);
        assert.strictEqual(feats.filter(':disabled').val(), 'clase');           // el objetivo no es predictora
        assert.strictEqual($('.rf-feature-' + n.id + ':checked').length, 3);
        assert.ok(!$('.rf-feature-' + n.id).map((i, e) => e.value).get().includes(''), 'no debe haber una predictora vacía');
        $('#features-all-' + n.id).trigger('click');
        assert.ok(!$('.rf-feature-' + n.id + ':checked').map((i, e) => e.value).get().includes(''));
    });
    await test('valida y guarda; salida = [informe, variables del modelo]', async () => {
        const n = node('trans_RandomForest', ['rojo', 'verde', 'ir', 'clase']);
        n.open();
        n.accept();
        assert.ok(/variable to predict/i.test(n.error()), 'sin objetivo: ' + n.error());
        n.f('target').val('clase').trigger('change');
        $('.rf-feature-' + n.id).prop('checked', false);
        n.accept();
        assert.ok(/at least one variable/i.test(n.error()), n.error());
        $('#features-all-' + n.id).trigger('click');
        n.f('test-percent').val('80'); n.accept();
        assert.ok(/between 0 and 50/.test(n.error()), n.error());
        n.f('test-percent').val('20'); n.f('n-estimators').val('5000'); n.accept();
        assert.ok(/between 1 and 2000/.test(n.error()), n.error());
        n.f('n-estimators').val('200');
        n.accept();
        await tick();
        assert.strictEqual(n.error(), '');
        const t = n.task();
        same(JSON.parse(JSON.stringify(t.parameters[0])), {
            target: 'clase', features: ['rojo', 'verde', 'ir'], problem: 'auto', 'n-estimators': '200',
            'max-depth': '', 'min-samples-leaf': '1', 'test-percent': '20', seed: '42',
            validation: 'auto', folds: '5', 'block-size': '', 'max-features': 'auto' });
        same(t.schema, [['section', 'name', 'value'], ['rojo', 'verde', 'ir'], ['real', 'total', 'recall']]);
        const edge = w.__edges.filter((e) => e[0] === n.id).pop();
        same(edge[1], [['section', 'name', 'value'], ['rojo', 'verde', 'ir'], ['real', 'total', 'recall']]);
        assert.ok(w.__propagated.includes(n.id));
        assert.strictEqual(n.icon.color, '#4682B4');
        checkKeys('trans_RandomForest', t);
    });
    await test('reabrir conserva la configuración y descarta columnas que ya no existen', async () => {
        const n = node('trans_RandomForest', ['rojo', 'verde', 'ir', 'clase']);
        n.open(); n.f('target').val('clase').trigger('change');
        $('.rf-feature-' + n.id).prop('checked', false);
        $('.rf-feature-' + n.id + '[value=rojo]').prop('checked', true);
        n.f('seed').val('7'); n.f('max-depth').val('12'); n.accept(); await tick();
        w.__inputs[n.id] = ['rojo', 'ir', 'clase'];            // 'verde' desaparece aguas arriba
        n.open();
        assert.strictEqual(n.f('target').val(), 'clase');
        same($('.rf-feature-' + n.id + ':checked').map((i, e) => e.value).get(), ['rojo']);
        assert.strictEqual(n.f('seed').val(), '7');
        assert.strictEqual(n.f('max-depth').val(), '12');
        same($('.rf-feature-' + n.id).map((i, e) => e.value).get(), ['rojo', 'ir', 'clase']);   // 'verde' ya no existe; 'clase' es el objetivo
    });
    await test('sin tabla conectada avisa', () => {
        const n = node('trans_RandomForest', []);
        n.open(); n.accept();
        assert.ok(/Connect a table/.test(n.error()), n.error());
    });

    console.log('Diálogo: Muestrear ráster');
    await test('clase desde la tabla de muestras; salida = bandas + clase', async () => {
        const n = node('trans_RasterSample', [['rojo', 'verde', 'ir'], ['ogc_fid', 'wkb_geometry', 'clase', 'otra']]);
        n.open();
        same(n.f('class-attr').find('option').map((i, o) => o.value).get(), ['clase', 'otra']);
        n.f('class-attr').val('clase'); n.f('max-per-class').val('0'); n.accept();
        assert.ok(/greater than 0/.test(n.error()), n.error());
        n.f('max-per-class').val('500'); n.accept(); await tick();
        assert.strictEqual(n.error(), '');
        same(JSON.parse(JSON.stringify(n.task().parameters[0])), { 'class-attr': 'clase', 'max-per-class': '500', seed: '42' });
        same(n.task().schema, ['rojo', 'verde', 'ir', 'clase']);
        checkKeys('trans_RasterSample', n.task());
    });
    await test('rechaza clase con el nombre de una banda y entradas sin conectar', async () => {
        let n = node('trans_RasterSample', [['rojo', 'clase'], ['clase']]);
        n.open(); n.f('class-attr').val('clase'); n.accept();
        assert.ok(/same name as a raster band/.test(n.error()), n.error());
        n = node('trans_RasterSample', [[], ['clase']]);
        n.open(); n.accept(); assert.ok(/Connect and configure a raster/.test(n.error()), n.error());
        n = node('trans_RasterSample', [['rojo'], []]);
        n.open(); n.accept(); assert.ok(/Connect the sample polygons/.test(n.error()), n.error());
    });

    console.log('Diálogo: Predecir ráster');
    await test('comprueba que el ráster tiene las bandas del modelo', async () => {
        let n = node('trans_RasterPredict', [['rojo', 'verde'], ['rojo', 'ir']]);
        n.open();
        assert.ok(/does not have the bands/.test($('#predict-status-' + n.id).text()));
        assert.ok(/ir/.test($('#predict-status-' + n.id).text()));
        n.accept(); assert.ok(/does not have the bands/.test(n.error()), n.error());
        n = node('trans_RasterPredict', [['rojo', 'verde', 'ir'], ['rojo', 'ir']]);
        n.open(); assert.ok(/has all the bands/.test($('#predict-status-' + n.id).text()));
        n.accept(); await tick();
        assert.strictEqual(n.error(), '');
        same(n.task().schema, [['prediction'], ['confidence']]);
        checkKeys('trans_RasterPredict', n.task());
    });

    console.log('Diálogo: Poligonizar');
    await test('valores por defecto, validación y guardado', async () => {
        const n = node('trans_RasterPolygonize', [['prediction']]);
        n.open();
        assert.strictEqual(n.f('connectivity').val(), '4');
        n.f('min-area').val('-3'); n.accept(); assert.ok(/minimum area/.test(n.error()), n.error());
        n.f('min-area').val('25.5'); n.f('classes').val(' Clase A , ,Clase B '); n.f('connectivity').val('8'); n.accept(); await tick();
        assert.strictEqual(n.error(), '');
        same(JSON.parse(JSON.stringify(n.task().parameters[0])), { classes: 'Clase A,Clase B', 'min-area': '25.5', simplify: '0', connectivity: '8' });
        same(n.task().schema, ['class_name', 'class_code', 'area', 'wkb_geometry']);
        checkKeys('trans_RasterPolygonize', n.task());
        n.open();
        assert.strictEqual(n.f('connectivity').val(), '8');
        assert.strictEqual(n.f('classes').val(), 'Clase A,Clase B');
    });

    console.log('Diálogo: Entrada ráster');
    await test('lee bandas del servidor, permite alias y guarda esquema normalizado', async () => {
        w.__ajaxHandler = (opts, d) => {
            const sent = JSON.parse(opts.data.get('jsonParamsRaster')).parameters[0];
            const names = (sent['band-names'] || '').split(',');
            const bands = ['b1', 'b2', 'b3'].map((b, i) => (names[i] && names[i].trim() ? names[i].trim().toLowerCase() : b));
            d.resolve({ bands, crs: 'EPSG:25830', width: 4000, height: 3000 });
        };
        const n = node('input_Raster', []);
        n.open();
        n.f('raster-file').val('file:///opt/gvsigol_data/data/a.tif').trigger('change');
        await tick(20);
        assert.strictEqual($('.raster-band-alias-' + n.id).length, 3);
        assert.ok(/3 bands · EPSG:25830 · 4000 × 3000 px/.test($('#raster-info-' + n.id).text()), $('#raster-info-' + n.id).text());
        $('.raster-band-alias-' + n.id).eq(0).val('Rojo, oscuro'); $('.raster-band-alias-' + n.id).eq(2).val('IR');
        n.accept(); await tick(20);
        assert.strictEqual(n.error(), '');
        assert.strictEqual(n.task().parameters[0]['band-names'], 'Rojo  oscuro,,IR');    // la coma del alias se sustituye
        same(n.task().schema, ['rojo  oscuro', 'b2', 'ir']);
        assert.strictEqual(n.icon.color, '#01b0a0');
        checkKeys('input_Raster', n.task());
        // reabrir recupera los alias
        n.open(); await tick(20);
        assert.strictEqual($('.raster-band-alias-' + n.id).eq(2).val(), 'IR');
    });
    await test('errores del servidor se muestran en el diálogo y no cierran ni guardan', async () => {
        w.__ajaxHandler = (opts, d) => d.reject({ responseText: JSON.stringify({ error: 'El fichero debe estar en el gestor de ficheros.' }) });
        const n = node('input_Raster', []);
        n.open();
        n.f('raster-file').val('/etc/passwd.tif'); n.accept(); await tick(20);
        assert.ok(/gestor de ficheros/.test(n.error()), n.error());
        assert.strictEqual(n.task(), undefined);
    });
    await test('sin fichero seleccionado', () => {
        const n = node('input_Raster', []);
        n.open(); n.accept();
        assert.ok(/Select a GeoTIFF/.test(n.error()), n.error());
    });
    await test('selector de ficheros: acepta .tif y rechaza otros', async () => {
        w.__ajaxHandler = (o, d) => d.resolve({ bands: ['b1'], crs: 'EPSG:4326', width: 1, height: 1 });
        const n = node('input_Raster', []);
        n.open();
        $('#select-file-button-' + n.id).trigger('click');            // window.open no existe en jsdom: ignorado
        w.filemanagerCallback('x/otro.csv');
        assert.ok(w.messageBox.calls.some((c) => /not a GeoTIFF/.test(c[1])));
        w.filemanagerCallback('x/mapa.TIF'); await tick(20);
        assert.strictEqual(n.f('raster-file').val(), 'file:///opt/gvsigol_data/data/x/mapa.TIF');
    });

    await test('el selector de ráster no secuestra el gestor de ficheros de otros nodos', async () => {
        w.__ajaxHandler = (o, d) => d.resolve({ bands: ['b1'], crs: 'EPSG:4326', width: 1, height: 1 });
        const otro = function () {};                    // p. ej. la función del nodo Shapefile
        w.filemanagerCallback = otro;
        const n = node('input_Raster', []);
        n.open();
        $('#select-file-button-' + n.id).trigger('click');
        assert.notStrictEqual(w.filemanagerCallback, otro, 'mientras se elige el ráster, la función es la del nodo');
        w.filemanagerCallback('x/mapa.tif'); await tick(20);
        assert.strictEqual(w.filemanagerCallback, otro, 'tras elegir el ráster se devuelve la anterior');
        // si se abre el selector y se cierra el diálogo sin elegir, también se devuelve
        $('#select-file-button-' + n.id).trigger('click');
        assert.notStrictEqual(w.filemanagerCallback, otro);
        $('#dialog-input_Raster-' + n.id).trigger('hidden.bs.modal');
        assert.strictEqual(w.filemanagerCallback, otro, 'al cerrar el diálogo se devuelve la anterior');
    });

    console.log('Diálogo: Publicar ráster');
    await test('carga destinos, deriva el nombre del título y guarda', async () => {
        w.__targets = { workspaces: [{ id: 1, name: 'ws_dev' }, { id: 2, name: 'ws_x' }],
                        layer_groups: [{ id: 5, name: 'g_dev', title: 'Grupo dev' }] };
        const n = node('output_RasterPublish', [['prediction']]);
        n.open(); await tick();
        same(n.f('workspace').find('option').map((i, o) => o.value).get(), ['', 'ws_dev', 'ws_x']);
        assert.strictEqual(n.f('layer-group').find('option[value=g_dev]').text(), 'Grupo dev');
        n.accept(); assert.ok(/workspace/.test(n.error()), n.error());
        n.f('workspace').val('ws_dev'); n.accept(); assert.ok(/layer group/.test(n.error()), n.error());
        n.f('layer-group').val('g_dev'); n.accept(); assert.ok(/title or a name/.test(n.error()), n.error());
        n.f('title').val('Superficie de Vegetación 2024'); n.accept(); await tick();
        assert.strictEqual(n.error(), '');
        same(JSON.parse(JSON.stringify(n.task().parameters[0])), {
            workspace: 'ws_dev', 'layer-group': 'g_dev', title: 'Superficie de Vegetación 2024',
            'layer-name': 'superficie_de_vegetacion_2024', 'on-existing': 'replace', 'public': '',
            'update-style': 'auto', band: '', 'ramp-min': '', 'ramp-max': '', abstract: '' });
        same(n.task().schema, []);
        checkKeys('output_RasterPublish', n.task());
        n.open(); await tick();
        assert.strictEqual(n.f('workspace').val(), 'ws_dev');
        assert.strictEqual(n.f('layer-name').val(), 'superficie_de_vegetacion_2024');
    });
    await test('falla con claridad si no se pueden cargar los destinos', async () => {
        w.$.getJSON = () => { const d = w.$.Deferred(); setTimeout(() => d.reject(), 0); return d.promise(); };
        w.etlPublishTargets = { loadedAt: 0, data: null };
        const n = node('output_RasterPublish', [['x']]);
        n.open(); await tick(20);
        assert.ok(/could not be loaded/.test(n.error()), n.error());
    });

    console.log('Diálogo: Random Forest, validación');
    await test('solo se muestran los campos de la validación elegida', () => {
        const n = node('trans_RandomForest', ['rojo', 'ir', 'clase']);
        n.open();
        const vis = (name) => n.f(name).closest('.col-md-4').css('display') !== 'none';
        assert.strictEqual(n.f('validation').val(), 'auto');                // por defecto: automática
        assert.strictEqual(vis('test-percent'), true);                        // por si cae en reserva aleatoria
        assert.strictEqual(vis('folds'), true);                               // por si valida por polígonos
        assert.strictEqual(vis('block-size'), false);
        n.f('validation').val('random').trigger('change');
        assert.strictEqual(vis('test-percent'), true);
        assert.strictEqual(vis('folds'), false);
        n.f('validation').val('polygon').trigger('change');
        assert.strictEqual(vis('test-percent'), false);
        assert.strictEqual(vis('folds'), true);
        assert.strictEqual(vis('block-size'), false);
        n.f('validation').val('block').trigger('change');
        assert.strictEqual(vis('block-size'), true);
    });
    await test('valida y guarda la validación por bloques', async () => {
        const n = node('trans_RandomForest', ['rojo', 'ir', 'clase']);
        n.open(); n.f('target').val('clase').trigger('change');
        n.f('validation').val('block').trigger('change');
        n.accept(); assert.ok(/block size/.test(n.error()), n.error());
        n.f('block-size').val('25.5'); n.f('folds').val('1'); n.accept();
        assert.ok(/rounds/.test(n.error()), n.error());
        n.f('folds').val('4'); n.accept(); await tick();
        assert.strictEqual(n.error(), '');
        const p = n.task().parameters[0];
        assert.strictEqual(p.validation, 'block'); assert.strictEqual(p.folds, '4'); assert.strictEqual(p['block-size'], '25.5');
        n.open();
        assert.strictEqual(n.f('validation').val(), 'block');
        assert.strictEqual(n.f('block-size').val(), '25.5');
        // volver a aleatoria no guarda el tamaño de bloque
        n.f('validation').val('random').trigger('change'); n.accept(); await tick();
        assert.strictEqual(n.task().parameters[0]['block-size'], '');
        checkKeys('trans_RandomForest', n.task());
    });

    console.log('Diálogo: Limpiar ráster');
    await test('método de mayoría y de tamaño mínimo; esquema de paso', async () => {
        const n = node('trans_RasterMajority', [['prediction']]);
        n.open();
        const shown = (id) => n.f(id).css('display') !== 'none';
        assert.strictEqual(shown('majority-box'), true); assert.strictEqual(shown('sieve-box'), false);
        n.f('mode').val('sieve').trigger('change');
        assert.strictEqual(shown('majority-box'), false); assert.strictEqual(shown('sieve-box'), true);
        n.f('min-pixels').val('1'); n.accept(); assert.ok(/at least 2/.test(n.error()), n.error());
        n.f('min-pixels').val('9'); n.accept(); await tick();
        assert.strictEqual(n.error(), '');
        const p = n.task().parameters[0];
        assert.strictEqual(p.mode, 'sieve'); assert.strictEqual(p['min-pixels'], '9');
        same(n.task().schema, ['prediction']);
        checkKeys('trans_RasterMajority', n.task());
        const m = node('trans_RasterMajority', [['prediction']]);
        m.open(); m.f('iterations').val('9'); m.accept(); assert.ok(/between 1 and 5/.test(m.error()), m.error());
        m.f('iterations').val('2'); m.f('window').val('5'); m.accept(); await tick();
        assert.strictEqual(m.task().parameters[0].window, '5'); assert.strictEqual(m.task().parameters[0].iterations, '2');
    });
    await test('sin ráster conectado avisa', () => {
        const n = node('trans_RasterMajority', []);
        n.open(); n.accept();
        assert.ok(/Connect a classified raster/.test(n.error()), n.error());
    });

    console.log('Diálogo: Índice espectral');
    await test('adivina las bandas por su nombre y propone el nombre del índice', () => {
        const n = node('trans_RasterIndex', ['azul', 'verde', 'rojo', 'ir', 'swir']);
        n.open();
        n.f('index').val('ndvi').trigger('change');
        assert.strictEqual(n.f('band-1').val(), 'ir');     // NIR
        assert.strictEqual(n.f('band-2').val(), 'rojo');
        assert.strictEqual(n.f('name').val(), 'ndvi');
        n.f('index').val('evi').trigger('change');
        assert.strictEqual(n.f('band-3').val(), 'azul');
        n.f('index').val('ndwi').trigger('change');
        assert.strictEqual(n.f('band-1').val(), 'verde');
        n.f('index').val('brightness').trigger('change');
        assert.strictEqual($('#index-bands-' + n.id).children().length, 0);   // sin bandas que elegir
    });
    await test('guarda el índice y añade la banda al esquema', async () => {
        const n = node('trans_RasterIndex', ['azul', 'verde', 'rojo', 'ir']);
        n.open(); n.accept(); assert.ok(/Choose the index/.test(n.error()), n.error());
        n.f('index').val('ndvi').trigger('change');
        n.f('name').val('NDVI de prueba').trigger('input');
        n.accept(); await tick();
        assert.strictEqual(n.error(), '');
        same(n.task().parameters[0], { index: 'ndvi', 'band-1': 'ir', 'band-2': 'rojo', 'band-3': '', name: 'NDVI de prueba',
            reflectance: 'none', scale: '1', offset: '0', 'savi-l': '0.5' });
        same(n.task().schema, ['azul', 'verde', 'rojo', 'ir', 'ndvi_de_prueba']);
        checkKeys('trans_RasterIndex', n.task());
        n.open();
        assert.strictEqual(n.f('index').val(), 'ndvi'); assert.strictEqual(n.f('band-1').val(), 'ir');
        assert.strictEqual(n.f('name').val(), 'NDVI de prueba');
    });
    await test('el nombre de la banda nueva se hace único como en el servidor', async () => {
        const n = node('trans_RasterIndex', ['rojo', 'ir']);
        n.open(); n.f('index').val('ndvi').trigger('change'); n.f('name').val('Rojo').trigger('input');
        n.accept(); await tick();
        same(n.task().schema, ['rojo', 'ir', 'rojo_2']);
    });
    await test('valida bandas repetidas, sin elegir y la escala', async () => {
        const n = node('trans_RasterIndex', ['rojo', 'ir']);
        n.open(); n.f('index').val('ndvi').trigger('change');
        n.f('band-1').val('rojo'); n.accept(); assert.ok(/different band/.test(n.error()), n.error());
        n.f('band-1').val(''); n.accept(); assert.ok(/Choose the band for/.test(n.error()), n.error());
        n.f('band-1').val('ir');
        n.f('index').val('savi').trigger('change');
        const shown = (id) => n.f(id).css('display') !== 'none';
        assert.strictEqual(shown('savi-box'), true);
        assert.strictEqual(shown('scale-box'), false);                       // solo con conversión personalizada
        assert.strictEqual(shown('reflectance-warning'), true);              // SAVI sin convertir a reflectancia: aviso
        n.f('reflectance').val('uint8').trigger('change');
        assert.strictEqual(shown('reflectance-warning'), false);
        n.f('reflectance').val('custom').trigger('change');
        assert.strictEqual(shown('scale-box'), true);
        n.f('band-1').val('ir'); n.f('band-2').val('rojo'); n.f('scale').val('0'); n.accept();
        assert.ok(/reflectance scale/.test(n.error()), n.error());
        n.f('scale').val('10000'); n.f('offset').val('-1000'); n.f('savi-l').val('2'); n.accept();
        assert.ok(/between 0 and 1/.test(n.error()), n.error());
        n.f('savi-l').val('0.4'); n.accept(); await tick();
        assert.strictEqual(n.error(), '');
        const p = n.task().parameters[0];
        same([p.reflectance, p.scale, p.offset, p['savi-l']], ['custom', '10000', '-1000', '0.4']);
        // un preset no arrastra los campos personalizados
        n.open(); n.f('reflectance').val('sentinel2_l2a').trigger('change'); n.accept(); await tick();
        same([n.task().parameters[0].reflectance, n.task().parameters[0].scale, n.task().parameters[0].offset], ['sentinel2_l2a', '1', '0']);
        // un flujo guardado antes (solo con escala) se abre como conversión personalizada
        const old = node('trans_RasterIndex', ['rojo', 'ir']);
        w.isAlreadyInCanvas(w.jsonParams, { id: old.id, parameters: [{ index: 'savi', 'band-1': 'ir', 'band-2': 'rojo', scale: '255', 'savi-l': '0.5' }], schema: [] }, old.id);
        old.open();
        same([old.f('reflectance').val(), old.f('scale').val(), old.f('offset').val()], ['custom', '255', '0']);
    });
    await test('helpers: nombre de banda y detección por nombre', () => {
        // Los mismos casos que tests/test_raster_nodes.py::EditorServerParityTest (deben dar lo mismo en el servidor)
        [['NDVI Año 1', [], 'ndvi_ano_1'], ['1x', [], 'b_1x'], ['Rojo', ['rojo'], 'rojo_2'], ['  Infrarrojo cercano ', [], 'infrarrojo_cercano'], ['a-b/c', [], 'a_b_c'],
         ['Ñandú', [], 'nandu'], ['fecha 2_rojo', ['fecha_2_rojo'], 'fecha_2_rojo_2']]
            .forEach(([text, existing, expected]) => assert.strictEqual(w.etlBandName(text, existing), expected, text));
        assert.strictEqual(w.etlGuessBand('nir', ['b1', 'infrarrojo_cercano']), 'infrarrojo_cercano');
        assert.strictEqual(w.etlGuessBand('red', ['b1', 'red']), 'red');
        assert.strictEqual(w.etlGuessBand('red', ['b4', 'b8']), 'b4');
        assert.strictEqual(w.etlGuessBand('nir', ['b4', 'b8']), 'b8');
        assert.strictEqual(w.etlGuessBand('swir', ['b11']), 'b11');
        assert.strictEqual(w.etlGuessBand('blue', ['b1', 'b2']), 'b2');
        assert.strictEqual(w.etlGuessBand('green', ['x']), '');
        assert.strictEqual(w.etlGuessBand('a', ['x']), '');
    });

    console.log('Diálogo: Evaluar clasificación');
    await test('pide ráster, muestras y columna de clase', async () => {
        const n = node('trans_ClassAssess', [['prediction'], ['clase', 'wkb_geometry', 'ogc_fid']]);
        n.open();
        same(n.f('class-attr').find('option').map((i, o) => o.value).get(), ['', 'clase']);
        n.accept(); assert.ok(/Choose the class column/.test(n.error()), n.error());
        n.f('class-attr').val('clase'); n.accept(); await tick();
        assert.strictEqual(n.error(), '');
        same(n.task().parameters[0], { 'class-attr': 'clase' });
        same(n.task().schema, [['section', 'name', 'value'], ['real', 'total', 'recall']]);
        checkKeys('trans_ClassAssess', n.task());
        const empty = node('trans_ClassAssess', [[], ['clase']]);
        empty.open(); empty.accept(); assert.ok(/Connect a classified raster/.test(empty.error()), empty.error());
        const nosamples = node('trans_ClassAssess', [['prediction'], []]);
        nosamples.open(); nosamples.accept(); assert.ok(/validation samples/.test(nosamples.error()), nosamples.error());
    });

    console.log('Diálogo: Combinar ráster');
    await test('nace configurado, pide prefijos de los ráster conectados y calcula las bandas', async () => {
        const n = node('trans_RasterStack', [['rojo', 'verde'], ['mdt'], [], []]);
        same(n.task().parameters[0], { resampling: 'bilinear', 'prefix-1': '', 'prefix-2': '', 'prefix-3': '', 'prefix-4': '' });
        n.open();
        assert.strictEqual($('#stack-prefixes-' + n.id + ' input').length, 2);
        $('#stack-prefix-2-' + n.id).val('terreno'); n.f('resampling').val('nearest');
        n.accept(); await tick();
        assert.strictEqual(n.error(), '');
        same(n.task().schema, ['rojo', 'verde', 'terreno_mdt']);
        assert.strictEqual(n.task().parameters[0].resampling, 'nearest');
        assert.strictEqual(n.task().parameters[0]['prefix-2'], 'terreno');
        checkKeys('trans_RasterStack', n.task());
        n.open();
        assert.strictEqual($('#stack-prefix-2-' + n.id).val(), 'terreno');
    });
    await test('combinar: bandas repetidas se hacen únicas y hacen falta dos ráster', async () => {
        const n = node('trans_RasterStack', [['rojo', 'ir'], ['rojo', 'ir'], ['rojo'], []]);
        n.open(); n.accept(); await tick();
        same(n.task().schema, ['rojo', 'ir', 'rojo_2', 'ir_2', 'rojo_3']);
        const one = node('trans_RasterStack', [['rojo'], [], [], []]);
        one.open(); one.accept(); assert.ok(/at least two rasters/.test(one.error()), one.error());
        assert.strictEqual(w.etlStackBands([['a'], [], ['b']], ['p1', 'p2']).join(','), 'p1_a,p2_b');
    });

    console.log('Diálogo: Predecir tabla');
    await test('comprueba las columnas del modelo y propone el nombre de la columna', async () => {
        const n = node('trans_TablePredict', [['x', 'ruido', 'wkb_geometry'], ['x', 'zzz']]);
        n.open();
        assert.ok(/does not have the columns/.test($('#tpredict-status-' + n.id).text()));
        n.accept(); assert.ok(/does not have the columns/.test(n.error()), n.error());
        const ok = node('trans_TablePredict', [['x', 'ruido', 'wkb_geometry'], ['x', 'ruido']]);
        ok.open();
        assert.strictEqual(ok.f('column').val(), 'prediction');
        ok.f('column').val('Clase prevista'); ok.accept(); await tick();
        assert.strictEqual(ok.error(), '');
        same(ok.task().schema, ['x', 'ruido', 'wkb_geometry', 'clase_prevista', 'clase_prevista_confidence']);
        checkKeys('trans_TablePredict', ok.task());
        const clash = node('trans_TablePredict', [['x', 'prediction'], ['x']]);
        clash.open(); clash.accept(); assert.ok(/already has a column/.test(clash.error()), clash.error());
    });

    console.log('Diálogo: Guardar modelo');
    await test('valida el nombre, enseña cómo se guardará y guarda', async () => {
        const n = node('output_ModelSave', [['x', 'y']]);
        n.open();
        n.accept(); assert.ok(/name for the model/.test(n.error()), n.error());
        n.f('model-name').val('Cobertura Año 2024').trigger('input');
        assert.ok(/cobertura_ano_2024/.test($('#model-name-hint-' + n.id).text()), $('#model-name-hint-' + n.id).text());
        n.f('on-existing').val('replace'); n.f('description').val(' imagen de mayo '); n.accept(); await tick();
        assert.strictEqual(n.error(), '');
        same(n.task().parameters[0], { 'model-name': 'Cobertura Año 2024', description: 'imagen de mayo', 'on-existing': 'replace' });
        same(n.task().schema, []);
        checkKeys('output_ModelSave', n.task());
        const none = node('output_ModelSave', [[]]);
        none.open(); none.accept(); assert.ok(/Connect a trained model/.test(none.error()), none.error());
        assert.strictEqual(w.etlSafeModelName('9 a'), 'm_9_a');
        assert.strictEqual(w.etlSafeModelName('x'.repeat(80)).length, 60);
    });

    console.log('Diálogo: Modelo guardado');
    const savedModels = [
        { name: 'cobertura', versions: [
            { version: 1, created: '2026-01-01T10:00:00Z', problem: 'classification', features: ['rojo', 'ir'], classes: ['A', 'B'], metrics: { accuracy: 0.9 }, rows: 100, description: 'v1' },
            { version: 2, created: '2026-02-01T10:00:00Z', problem: 'classification', features: ['rojo', 'ir', 'ndvi'], classes: ['A', 'B'], metrics: { accuracy: 0.95 }, rows: 200, description: '' }] },
        { name: 'biomasa', versions: [{ version: 1, created: '2026-03-01T10:00:00Z', problem: 'regression', features: ['x'], classes: [], metrics: {}, rows: 50, description: '' }] }];
    const modelsEnv = () => {
        w.etlSavedModels = { loadedAt: 0, data: null };
        w.$.getJSON = (url) => { const d = w.$.Deferred(); w.__ajax.push({ url }); setTimeout(() => d.resolve({ models: JSON.parse(JSON.stringify(savedModels)) }), 0); return d.promise(); };
        w.confirm = () => true;
    };
    await test('lista los modelos, elige la última versión y su esquema son las variables del modelo', async () => {
        modelsEnv();
        const n = node('input_Model', []);
        n.open(); await tick(20);
        same(n.f('model-name').find('option').map((i, o) => o.value).get(), ['', 'cobertura', 'biomasa']);
        n.accept(); assert.ok(/Choose the saved model/.test(n.error()), n.error());
        n.f('model-name').val('cobertura').trigger('change');
        same(n.f('model-version').find('option').map((i, o) => o.value).get(), ['latest', '2', '1']);
        assert.ok(/rojo, ir, ndvi/.test($('#model-info-' + n.id).text()), $('#model-info-' + n.id).text());
        n.f('model-version').val('1').trigger('change');
        assert.ok(/rojo, ir/.test($('#model-info-' + n.id).text()) && !/ndvi/.test($('#model-info-' + n.id).text()));
        n.accept(); await tick(20);
        assert.strictEqual(n.error(), '');
        same(n.task().parameters[0], { 'model-name': 'cobertura', 'model-version': '1' });
        same(n.task().schema, ['rojo', 'ir']);
        checkKeys('input_Model', n.task());
        n.open(); await tick(20);
        assert.strictEqual(n.f('model-name').val(), 'cobertura');
        assert.strictEqual(n.f('model-version').val(), '1');
        n.f('model-version').val('latest').trigger('change'); n.accept(); await tick(20);
        same(n.task().schema, ['rojo', 'ir', 'ndvi']);
    });
    await test('sin modelos guardados lo explica; un error del servidor se muestra', async () => {
        w.etlSavedModels = { loadedAt: 0, data: null };
        w.$.getJSON = () => { const d = w.$.Deferred(); setTimeout(() => d.resolve({ models: [] }), 0); return d.promise(); };
        const n = node('input_Model', []);
        n.open(); await tick(20);
        assert.ok(/no saved models/.test($('#model-info-' + n.id).text()), $('#model-info-' + n.id).text());
        w.etlSavedModels = { loadedAt: 0, data: null };
        w.$.getJSON = () => { const d = w.$.Deferred(); setTimeout(() => d.reject(), 0); return d.promise(); };
        const bad = node('input_Model', []);
        bad.open(); await tick(20);
        assert.ok(/could not be loaded/.test(bad.error()), bad.error());
    });
    await test('borrar una versión o el modelo entero llama al servidor y refresca la lista', async () => {
        modelsEnv();
        const deleted = [];
        w.$.ajax = function (opts) {
            const d = w.$.Deferred();
            if (/etl_models_delete/.test(opts.url)) {
                deleted.push(opts.data);
                setTimeout(() => d.resolve({ deleted: 1 }), 0);
            } else { setTimeout(() => d.reject({ responseText: '{}' }), 0); }
            return d.promise();
        };
        const n = node('input_Model', []);
        n.open(); await tick(20);
        n.f('model-name').val('biomasa').trigger('change');
        n.f('model-delete-all').trigger('click'); await tick(30);
        same(deleted, [{ name: 'biomasa', version: '' }]);
        n.f('model-name').val('cobertura').trigger('change');
        n.f('model-delete-version').trigger('click'); await tick(30);
        same(deleted[1], { name: 'cobertura', version: '2' });    // "latest" se borra como la versión que es
        w.confirm = () => false;
        n.f('model-delete-all').trigger('click'); await tick(20);
        assert.strictEqual(deleted.length, 2);                     // al cancelar no se llama al servidor
    });

    console.log('Diálogo: Publicar ráster, opciones nuevas');
    await test('banda solo con varias bandas; límites de la rampa coherentes; estilo por defecto', async () => {
        w.etlPublishTargets = { loadedAt: 0, data: null };
        w.__targets = { workspaces: [{ id: 1, name: 'ws' }], layer_groups: [{ id: 5, name: 'g', title: 'G' }] };
        w.$.getJSON = (url) => { const d = w.$.Deferred(); setTimeout(() => d.resolve(w.__targets), 0); return d.promise(); };
        const single = node('output_RasterPublish', [['prediction']]);
        single.open(); await tick(20);
        assert.strictEqual(single.f('band').closest('.form-group').css('display'), 'none');
        const multi = node('output_RasterPublish', [['rojo', 'verde', 'ir']]);
        multi.open(); await tick(20);
        same(multi.f('band').find('option').map((i, o) => o.value).get(), ['', 'rojo', 'verde', 'ir']);
        multi.f('workspace').val('ws'); multi.f('layer-group').val('g'); multi.f('title').val('Capa');
        multi.f('band').val('ir'); multi.f('ramp-min').val('0'); multi.accept();
        assert.ok(/both limits/.test(multi.error()), multi.error());
        multi.f('ramp-max').val('0'); multi.accept(); assert.ok(/greater than the minimum/.test(multi.error()), multi.error());
        multi.f('ramp-max').val('1'); multi.f('update-style').val('no'); multi.f('abstract').val(' resumen '); multi.accept(); await tick();
        assert.strictEqual(multi.error(), '');
        const p = multi.task().parameters[0];
        same([p.band, p['ramp-min'], p['ramp-max'], p['update-style'], p.abstract], ['ir', '0', '1', 'no', 'resumen']);
        single.f('workspace').val('ws'); single.f('layer-group').val('g'); single.f('title').val('Otra'); single.accept(); await tick();
        assert.strictEqual(single.task().parameters[0].band, '');          // una sola banda: no se envía
        assert.strictEqual(single.task().parameters[0]['update-style'], 'auto');
    });

    console.log('Diálogo: Recortar ráster');
    await test('nace configurado, valida el tamaño de píxel y pasa las bandas', async () => {
        const n = node('trans_RasterClip', [['nir', 'rojo', 'verde'], ['id', 'wkb_geometry']]);
        same(n.task().parameters[0], { mode: 'polygon', 'pixel-size': '', resampling: 'average' });
        checkKeys('trans_RasterClip', n.task());
        n.open();
        same(n.f('mode').find('option').map((i, o) => o.value).get(), ['polygon', 'bbox']);
        n.f('pixel-size').val('0'); n.accept(); assert.ok(/greater than 0/.test(n.error()), n.error());
        n.f('pixel-size').val('1'); n.f('mode').val('bbox'); n.f('resampling').val('bilinear'); n.accept(); await tick();
        assert.strictEqual(n.error(), '');
        same(n.task().parameters[0], { mode: 'bbox', 'pixel-size': '1', resampling: 'bilinear' });
        same(n.task().schema, ['nir', 'rojo', 'verde']);                 // los nombres de banda pasan tal cual
        n.open();
        assert.strictEqual(n.f('pixel-size').val(), '1'); assert.strictEqual(n.f('mode').val(), 'bbox');
        const unconnected = node('trans_RasterClip', [['a'], []]);
        unconnected.open(); unconnected.accept(); assert.ok(/mask of polygons/.test(unconnected.error()), unconnected.error());
        const empty = node('trans_RasterClip', [[], ['id']]);
        empty.open(); empty.accept(); assert.ok(/Connect a raster/.test(empty.error()), empty.error());
    });

    console.log('Diálogo: Muestreo estratificado y Estimar superficie');
    await test('muestreo: nace configurado con 50 por clase y valida el número', async () => {
        const n = node('trans_StratifiedSample', [['prediction']]);
        same(n.task().parameters[0], { 'per-class': '50', seed: '42' });
        same(n.task().schema, ['id', 'map_class', 'map_code', 'reference', 'wkb_geometry']);
        checkKeys('trans_StratifiedSample', n.task());
        n.open(); n.f('per-class').val('1'); n.accept(); assert.ok(/at least 2/.test(n.error()), n.error());
        n.f('per-class').val('80'); n.accept(); await tick();
        assert.strictEqual(n.task().parameters[0]['per-class'], '80');
    });
    await test('estimar superficie: propone la columna reference y guarda el nivel', async () => {
        const n = node('trans_AreaEstimate', [['prediction'], ['id', 'map_class', 'map_code', 'reference', 'wkb_geometry']]);
        n.open();
        assert.strictEqual(n.f('reference-attr').val(), 'reference');
        n.f('confidence-level').val('0.90'); n.accept(); await tick();
        assert.strictEqual(n.error(), '');
        same(n.task().parameters[0], { 'reference-attr': 'reference', 'confidence-level': '0.90' });
        same(n.task().schema[0].slice(0, 3), ['class', 'map_area', 'estimated_area']);
        checkKeys('trans_AreaEstimate', n.task());
        const none = node('trans_AreaEstimate', [['prediction'], []]);
        none.open(); none.accept(); assert.ok(/reference points/.test(none.error()), none.error());
    });

    console.log('Propagador de esquemas (código real)');
    await test('los manejadores validan columnas y calculan salidas', () => {
        const H = w.SCHEMA_HANDLERS;
        const p = (o) => ({ parameters: [o] });
        assert.strictEqual(H.trans_RasterSample.validateParams([['b1'], ['clase']], p({ 'class-attr': 'clase' })), true);
        assert.strictEqual(H.trans_RasterSample.validateParams([['b1'], ['otra']], p({ 'class-attr': 'clase' })), false);
        assert.strictEqual(H.trans_RasterSample.validateParams([['clase'], ['clase']], p({ 'class-attr': 'clase' })), false);
        same(Array.from(H.trans_RasterSample.computeOutputSchema([['b1', 'b2'], ['clase']], p({ 'class-attr': 'clase' }))), ['b1', 'b2', 'clase']);
        assert.strictEqual(H.trans_RandomForest.validateParams(['a', 'y'], p({ target: 'y', features: ['a'] })), true);
        assert.strictEqual(H.trans_RandomForest.validateParams(['a'], p({ target: 'y', features: ['a'] })), false);
        assert.strictEqual(H.trans_RandomForest.validateParams(['a', 'y'], p({ target: 'y', features: ['zz'] })), false);
        assert.strictEqual(H.trans_RasterPredict.validateParams([['b1', 'b2'], ['b1']]), true);
        assert.strictEqual(H.trans_RasterPredict.validateParams([['b1'], ['b2']]), false);
        assert.strictEqual(H.output_RasterPublish.validateParams([['x']], p({ workspace: 'w', 'layer-group': 'g', 'layer-name': 'n' })), true);
        assert.strictEqual(H.output_RasterPublish.validateParams([['x']], p({ workspace: 'w' })), false);
        assert.strictEqual(w.applySchemaHandler('trans_RandomForest', ['a', 'y'], p({ target: 'y', features: ['a'] })).ok, true);
        same(Array.from(H.trans_RasterClip.computeOutputSchema([['a', 'b'], ['id']], p({}))), ['a', 'b']);
        assert.strictEqual(H.trans_RasterClip.validateParams([['a'], ['id']]), true);
        assert.strictEqual(H.trans_RasterClip.validateParams([['a'], []]), false);
        assert.strictEqual(H.trans_ClassAssess.validateParams([['p'], ['clase']], p({ 'class-attr': 'clase' })), true);
        assert.strictEqual(H.trans_ClassAssess.validateParams([['p'], ['otra']], p({ 'class-attr': 'clase' })), false);
        same(Array.from(H.trans_RasterStack.computeOutputSchema([['a'], ['b'], [], []], p({ 'prefix-2': 'x' }))), ['a', 'x_b']);
        assert.strictEqual(H.trans_RasterStack.validateParams([['a'], [], [], []]), false);
        assert.strictEqual(H.trans_RasterStack.validateParams([['a'], ['b'], [], []]), true);
        same(Array.from(H.trans_TablePredict.computeOutputSchema([['x'], ['x']], p({ column: 'pred' }))), ['x', 'pred', 'pred_confidence']);
        assert.strictEqual(H.trans_TablePredict.validateParams([['x'], ['x', 'z']]), false);
        assert.strictEqual(H.output_ModelSave.validateParams([['x']], p({ 'model-name': 'm' })), true);
        assert.strictEqual(H.output_ModelSave.validateParams([['x']], p({ 'model-name': '  ' })), false);
        assert.strictEqual(H.input_Model.validateParams([], p({ 'model-name': 'm' })), true);
        same(Array.from(H.input_Model.computeOutputSchema([], { schema: ['f1', 'f2'] })), ['f1', 'f2']);
    });

    console.log('\n' + passed + ' correctos, ' + failed + ' fallidos');
    process.exit(failed ? 1 : 0);
})();
