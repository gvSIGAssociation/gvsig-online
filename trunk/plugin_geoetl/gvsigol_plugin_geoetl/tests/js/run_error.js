// Acciones de error en el panel de estado: carga el EtlRunError.js REAL en jsdom con jQuery real.
//   NODE_PATH=/tmp/etl-js/node_modules node run_error.js
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const read = (f) => fs.readFileSync(path.join(__dirname, '..', '..', 'static', 'js', f), 'utf8');
const tick = (ms = 5) => new Promise((r) => setTimeout(r, ms));
let passed = 0, failed = 0;
async function test(name, fn) {
    try { await fn(); passed++; console.log('  ok   ' + name); }
    catch (e) { failed++; console.log('  FAIL ' + name + '\n       ' + (e.stack || e).split('\n').slice(0, 4).join('\n       ')); }
}

const ID = 'f26a57da-8f8c-36ca-b425-f5fdb584ba8f';
const MESSAGE = 'ERROR: In trans_Join (' + ID + ') Node. zero-length delimited identifier at or near """"\nLINE 1: ...AS A1 ON A0.""::TEXT =...';
const error = (message) => ({ status: 'Error', message: message || MESSAGE });

function makeEnv(opts = {}) {
    const dom = new JSDOM('<!doctype html><body><button id="button-run" title="x"></button><div id="canvas-parent"></div>' +
        '<div id="etl-run-error" hidden></div>' +
        '<div id="etl-run-status-dock__actions" hidden></div></body>', { runScripts: 'outside-only', url: 'https://localhost/gvsigonline/etl/' });
    const w = dom.window;
    w.eval(fs.readFileSync(require.resolve('jquery/dist/jquery.js'), 'utf8'));
    w.gettext = (s) => s;
    w.__copied = [];
    Object.defineProperty(w.navigator, 'clipboard', { value: { writeText: (t) => { w.__copied.push(t); return Promise.resolve(); } } });
    w.__figure = { id: ID, etlAlias: 'n3', NAME: 'trans_Join', x: 10, y: 20, glow: false,
        classLabel: { getText: () => 'Cruce por campo' }, setGlow(v) { this.glow = v; } };
    w.__selected = null;
    w.etlApp = { view: { getFigure: (id) => (id === ID && !opts.otherFlow ? w.__figure : null), setCurrentSelection(f) { w.__selected = f; } } };
    if (opts.assistant) { w.__asked = []; w.etlAssistantAsk = (t) => w.__asked.push(t); }
    w.eval(read('EtlRunError.js'));
    return w;
}
const dock = (w) => w.$('#etl-run-status-dock__actions');

(async () => {
    console.log('Error de ejecución');

    await test('separa nodo y detalle; tolera otros formatos', async () => {
        const w = makeEnv();
        const p = w.EtlRunError.parse(MESSAGE);
        assert.strictEqual(p.type, 'trans_Join');
        assert.strictEqual(p.id, ID);
        assert.ok(p.detail.startsWith('zero-length'));
        assert.ok(p.detail.includes('\nLINE 1'));
        assert.strictEqual(w.EtlRunError.parse('ERROR: In trans_Join Node. boom').id, null);
        assert.strictEqual(w.EtlRunError.parse('ERROR: Hay nodos sin configurar').type, null);
        assert.strictEqual(w.EtlRunError.parse('ERROR: Hay nodos sin configurar').detail, 'ERROR: Hay nodos sin configurar');
    });

    await test('no pinta franja arriba; botones solo en el panel de estado', async () => {
        const w = makeEnv();
        w.EtlRunError.update(error());
        assert.strictEqual(w.$('#etl-run-error').prop('hidden'), true);
        assert.strictEqual(w.$('#etl-run-error .etl-run-error').length, 0);
        assert.strictEqual(dock(w).prop('hidden'), false);
        assert.strictEqual(dock(w).find('.js-copy-error').length, 1);
        assert.ok(/Cruce por campo \(n3\)/.test(dock(w).find('.js-focus-node').text()));
        dock(w).find('.js-copy-error').trigger('click');
        await tick();
        assert.strictEqual(w.__copied[0], MESSAGE);
        assert.ok(/run status panel/.test(w.$('#button-run').attr('title')));
    });

    await test('el nodo se centra y resalta al pulsarlo en el panel', async () => {
        const w = makeEnv();
        w.EtlRunError.update(error());
        dock(w).find('.js-focus-node').trigger('click');
        assert.strictEqual(w.__selected.etlAlias, 'n3');
        assert.strictEqual(w.__figure.glow, true);
    });

    await test('no repinta los botones en cada consulta', async () => {
        const w = makeEnv();
        w.EtlRunError.update(error());
        const before = dock(w).find('.js-copy-error')[0];
        w.EtlRunError.update(error());
        assert.strictEqual(dock(w).find('.js-copy-error')[0], before);
    });

    await test('error de otro flujo: sin ir al nodo, pero sí Copiar en el panel', async () => {
        const w = makeEnv({ otherFlow: true });
        w.EtlRunError.update(error());
        assert.strictEqual(dock(w).find('.js-focus-node').length, 0);
        assert.strictEqual(dock(w).find('.js-copy-error').length, 1);
    });

    await test('sin id de nodo: Copiar con el mensaje tal cual', async () => {
        const w = makeEnv();
        w.EtlRunError.update(error('ERROR: Hay nodos sin configurar.'));
        assert.strictEqual(dock(w).find('.js-focus-node').length, 0);
        dock(w).find('.js-copy-error').trigger('click');
        await tick();
        assert.strictEqual(w.__copied[0], 'ERROR: Hay nodos sin configurar.');
    });

    await test('al pasar a Running o Success se ocultan los botones', async () => {
        const w = makeEnv();
        w.EtlRunError.update(error());
        w.EtlRunError.update({ status: 'Running', message: '' });
        assert.strictEqual(dock(w).prop('hidden'), true);
        w.EtlRunError.update(error());
        assert.strictEqual(dock(w).find('.js-copy-error').length, 1);
        w.EtlRunError.update({ status: 'Success', message: 'ok' });
        assert.strictEqual(dock(w).prop('hidden'), true);
    });

    await test('una respuesta fallida de la consulta no toca el panel', async () => {
        const w = makeEnv();
        w.EtlRunError.update(error());
        w.EtlRunError.update({ status: 500 });
        assert.strictEqual(dock(w).find('.js-copy-error').length, 1);
    });

    await test('Preguntar al asistente solo si está activo, y sin ids internos', async () => {
        const off = makeEnv();
        off.EtlRunError.update(error());
        assert.strictEqual(dock(off).find('.js-ask-assistant').length, 0);
        const w = makeEnv({ assistant: true });
        w.EtlRunError.update(error());
        dock(w).find('.js-ask-assistant').trigger('click');
        assert.ok(w.__asked[0].includes('n3: zero-length'));
        assert.ok(!w.__asked[0].includes(ID));
    });

    await test('si el asistente llega después, aparece Preguntar en el panel', async () => {
        const w = makeEnv();
        w.EtlRunError.update(error());
        assert.strictEqual(dock(w).find('.js-ask-assistant').length, 0);
        w.__asked = [];
        w.etlAssistantAsk = (t) => w.__asked.push(t);
        w.EtlRunError.update(error());
        assert.strictEqual(dock(w).find('.js-ask-assistant').length, 1);
    });

    await test('lista de workspaces: Copiar en el mensaje', async () => {
        const w = makeEnv();
        w.$('body').append('<div id="modal-error"><div class="messageBoxMsg">x</div></div>');
        w.EtlRunError.addCopyToMessageBox('ERROR: uno');
        w.$('#modal-error .js-copy-error').trigger('click');
        await tick();
        assert.strictEqual(w.__copied[0], 'ERROR: uno');
        assert.strictEqual(w.$('#modal-error .js-ask-assistant').length, 0);
    });

    await test('lista de workspaces: Preguntar si hay asistente', async () => {
        const w = makeEnv({ assistant: true });
        w.$('body').append('<div id="modal-error"><div class="messageBoxMsg">x</div></div>');
        w.EtlRunError.addCopyToMessageBox('ERROR: uno');
        w.$('#modal-error .js-ask-assistant').trigger('click');
        assert.ok(w.__asked[0].includes('ERROR: uno'));
    });

    console.log('\n' + passed + ' correctos, ' + failed + ' fallidos');
    process.exit(failed ? 1 : 0);
})();
