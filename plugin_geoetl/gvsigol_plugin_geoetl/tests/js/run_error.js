// Tarjeta de error de ejecución: carga el EtlRunError.js REAL en jsdom con jQuery real.
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
        '<div id="etl-run-error" hidden></div></body>', { runScripts: 'outside-only', url: 'https://localhost/gvsigonline/etl/' });
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
const card = (w) => w.$('#etl-run-error .etl-run-error');

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

    await test('tarjeta con nodo legible, detalle y copia del mensaje completo', async () => {
        const w = makeEnv();
        w.EtlRunError.update(error());
        assert.strictEqual(w.$('#etl-run-error').prop('hidden'), false);
        assert.ok(/Cruce por campo \(n3\)/.test(card(w).find('.etl-run-error__node').text()));
        assert.ok(card(w).find('pre').text().startsWith('zero-length'));
        assert.ok(!card(w).find('pre').text().includes(ID));
        card(w).find('.js-copy-error').trigger('click');
        await tick();
        assert.strictEqual(w.__copied[0], MESSAGE);
        assert.strictEqual(card(w).find('.js-copy-error span').text(), 'Copied');
        assert.ok(/details above the canvas/.test(w.$('#button-run').attr('title')));
    });

    await test('el nodo se centra y resalta al pulsarlo', async () => {
        const w = makeEnv();
        w.EtlRunError.update(error());
        card(w).find('.etl-run-error__node button').trigger('click');
        assert.strictEqual(w.__selected.etlAlias, 'n3');
        assert.strictEqual(w.__figure.glow, true);
    });

    await test('no repinta en cada consulta, para no perder la selección', async () => {
        const w = makeEnv();
        w.EtlRunError.update(error());
        const before = card(w)[0];
        w.EtlRunError.update(error());
        assert.strictEqual(card(w)[0], before);
    });

    await test('el error de otro flujo no se enseña', async () => {
        const w = makeEnv({ otherFlow: true });
        w.EtlRunError.update(error());
        assert.strictEqual(card(w).length, 0);
        assert.strictEqual(w.$('#button-run').attr('title'), 'x');
    });

    await test('sin id de nodo se enseña tal cual', async () => {
        const w = makeEnv();
        w.EtlRunError.update(error('ERROR: Hay nodos sin configurar.'));
        assert.strictEqual(card(w).find('pre').text(), 'ERROR: Hay nodos sin configurar.');
        assert.strictEqual(card(w).find('.etl-run-error__node').length, 0);
    });

    await test('Cerrar no vuelve por el mismo error; sí tras lanzar otra ejecución', async () => {
        const w = makeEnv();
        w.EtlRunError.update(error());
        card(w).find('.etl-run-error__close').trigger('click');
        assert.strictEqual(card(w).length, 0);
        w.EtlRunError.update(error());
        assert.strictEqual(card(w).length, 0);
        w.EtlRunError.update(error('ERROR: otro distinto'));
        assert.strictEqual(card(w).length, 1);
        w.EtlRunError.update({ status: 'Running', message: '' });
        assert.strictEqual(card(w).length, 0);
        w.EtlRunError.update(error());
        assert.strictEqual(card(w).length, 1);
    });

    await test('al ejecutar de nuevo se olvida el cierre, aunque no se llegue a ver Running', async () => {
        const w = makeEnv();
        w.EtlRunError.update(error());
        card(w).find('.etl-run-error__close').trigger('click');
        w.$(w.document).trigger('ready');
        await tick();
        w.$('#button-run').trigger('click');
        w.EtlRunError.update(error());
        assert.strictEqual(card(w).length, 1);
    });

    await test('una respuesta fallida de la consulta no toca la tarjeta', async () => {
        const w = makeEnv();
        w.EtlRunError.update(error());
        w.EtlRunError.update({ status: 500 });
        assert.strictEqual(card(w).length, 1);
        w.EtlRunError.update({ status: 'Success', message: 'ok' });
        assert.strictEqual(card(w).length, 0);
    });

    await test('Preguntar al asistente solo si está activo, y sin ids internos', async () => {
        const off = makeEnv();
        off.EtlRunError.update(error());
        assert.strictEqual(card(off).find('.js-ask-assistant').length, 0);
        const w = makeEnv({ assistant: true });
        w.EtlRunError.update(error());
        card(w).find('.js-ask-assistant').trigger('click');
        assert.ok(w.__asked[0].includes('n3: zero-length'));
        assert.ok(!w.__asked[0].includes(ID));
    });

    await test('lista de workspaces: Copiar en el mensaje', async () => {
        const w = makeEnv();
        w.$('body').append('<div id="modal-error"><div class="messageBoxMsg">x</div></div>');
        w.EtlRunError.addCopyToMessageBox('ERROR: uno');
        w.$('#modal-error .js-copy-error').trigger('click');
        await tick();
        assert.strictEqual(w.__copied[0], 'ERROR: uno');
    });

    console.log('\n' + passed + ' correctos, ' + failed + ' fallidos');
    process.exit(failed ? 1 : 0);
})();
