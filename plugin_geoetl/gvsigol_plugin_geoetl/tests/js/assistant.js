// Tests del chat del asistente: carga el Assistant.js REAL (con marked y DOMPurify reales) en jsdom.
// Solo el canvas draw2d y el backend están simulados.
//   NODE_PATH=/tmp/etl-js/node_modules node assistant.js
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const JS = path.join(__dirname, '..', '..', 'static', 'js');
const read = (f) => fs.readFileSync(path.join(JS, f), 'utf8');
const tick = (ms = 5) => new Promise((r) => setTimeout(r, ms));

let passed = 0, failed = 0;
async function test(name, fn) {
    try { await fn(); passed++; console.log('  ok   ' + name); }
    catch (e) { failed++; console.log('  FAIL ' + name + '\n       ' + (e.stack || e).split('\n').slice(0, 4).join('\n       ')); }
}

const PANEL = `
<input id="etl_id" value="__ID__"><input id="etl_name" value="Mi flujo"><input id="etl_desc" value="">
<div id="canvas-parent"></div>
<button id="etl-assistant-open"></button>
<aside id="etl-assistant" class="pl-assistant is-collapsed">
  <div class="pl-assistant__handle"></div>
  <button id="etl-assistant-export"></button><button id="etl-assistant-clear"></button><button id="etl-assistant-close"></button>
  <div id="etl-assistant-messages"></div>
  <div id="etl-assistant-examples"></div>
  <div id="etl-assistant-context" hidden></div>
  <form id="etl-assistant-form"><textarea id="etl-assistant-input"></textarea>
    <button type="submit" id="etl-assistant-send"><i class="fa fa-paper-plane"></i></button></form>
  <div id="etl-assistant-counter" hidden></div>
</aside>`;

function makeEnv(opts = {}) {
    const dom = new JSDOM('<!doctype html><body>' + PANEL.replace('__ID__', opts.id || '') + '</body>', {
        runScripts: 'outside-only', url: 'https://localhost/gvsigonline/etl/', pretendToBeVisual: true
    });
    const w = dom.window;
    if (opts.session) {
        Object.entries(opts.session).forEach(([k, v]) => w.sessionStorage.setItem(k, v));
    }
    w.eval(fs.readFileSync(require.resolve('jquery/dist/jquery.js'), 'utf8'));
    w.eval(read('lib/marked.min.js'));
    w.eval(read('lib/purify.min.js'));
    w.gettext = (s) => s;
    w.eval('window.draw2d = { Connection: function () {}, command: { CommandDelete: function () {} } };');
    w.Cookies = { get: () => 'csrf' };
    w.confirm = () => true;
    w.__copied = [];
    Object.defineProperty(w.navigator, 'clipboard', {
        value: { writeText: (text) => { w.__copied.push(text); return Promise.resolve(); } }
    });
    // Canvas simulado: figuras con su id visible (etlAlias) y posición
    const figure = (id, alias, name, x, y) => ({
        id, etlAlias: alias, NAME: name, x, y, glow: false,
        classLabel: { getText: () => name }, getX: () => x, getY: () => y,
        setGlow(on) { this.glow = on; }, getCanvas: () => ({})
    });
    w.__figures = [figure('uuid-1', 'n1', 'input_Postgis', 100.4, 80), figure('uuid-3', 'n3', 'trans_Filter', 380, 80)];
    const list = (arr) => ({ each(fn) { arr.forEach((f, i) => fn(i, f)); }, clone() { return list(arr.slice()); } });
    w.__selected = null;
    w.etlApp = { view: {
        _etlAliasTop: 5,                         // se borró n4 y n5: no se reutilizan
        getFigures: () => list(w.__figures),
        getLines: () => list([]),
        getFigure: (id) => w.__figures.find((f) => f.id === id) || null,
        getCommandStack: () => ({ addEventListener() {} }),
        on() {}, setCurrentSelection(f) { w.__selected = f; }
    } };
    w.eval('var jsonParams = [{id: "uuid-1", parameters: [{db: "gis"}], schema: ["a"], "schema-old": []}];');
    // Backend simulado: cada petición queda pendiente hasta que el test la responde
    w.__ajax = [];
    w.$.ajax = function (o) {
        const req = { opts: o, aborted: false, body: JSON.parse(o.data) };
        req.abort = () => { req.aborted = true; o.error({ status: 0 }, 'abort'); o.complete(); };
        req.respond = (data) => { o.success(data); o.complete(); };
        w.__ajax.push(req);
        return req;
    };
    w.eval(read('Assistant.js'));
    return w;
}

const reply = (extra) => Object.assign({ reply: '', warnings: [], assumptions: [], summary: [],
    needs_confirmation: false, proposal: null, error: false }, extra);

(async () => {
    console.log('Chat del asistente (Assistant.js real)');

    await test('workspace nuevo: no arrastra la conversación de otro workspace nuevo', async () => {
        const old = JSON.stringify({ messages: [{ role: 'user', content: 'de otro flujo' }] });
        const w = makeEnv({ session: { 'etl-assistant-chat:new': old, 'etl-assistant-chat:7': old } });
        await tick();
        assert.strictEqual(w.sessionStorage.getItem('etl-assistant-chat:new'), null);
        assert.ok(w.sessionStorage.getItem('etl-assistant-chat:7'));      // los guardados se respetan
        assert.strictEqual(w.$('#etl-assistant-messages').text().indexOf('de otro flujo'), -1);
    });

    await test('envía posición, estado y siguiente id libre', async () => {
        const w = makeEnv({ id: '7' });
        await tick();
        w.$('#etl-assistant-input').val('añade un filtro');
        w.$('#etl-assistant-form').trigger('submit');
        const body = w.__ajax[0].body;
        assert.strictEqual(body.canvas.next_alias, 'n6');
        const n1 = body.canvas.nodes.find((n) => n.alias === 'n1');
        const n3 = body.canvas.nodes.find((n) => n.alias === 'n3');
        assert.deepStrictEqual([n1.x, n1.y, n1.status], [100, 80, '']);
        assert.strictEqual(n3.status, 'unconfigured');                     // sin tarea en jsonParams
    });

    await test('ids clicables en la respuesta; solo los que existen', async () => {
        const w = makeEnv({ id: '7' });
        await tick();
        w.$('#etl-assistant-input').val('explica');
        w.$('#etl-assistant-form').trigger('submit');
        w.__ajax[0].respond(reply({ reply: 'n1 lee la tabla, n3 filtra y `n1` en código. n9 no existe.' }));
        const chips = w.$('.pl-assistant__alias').map((i, el) => el.textContent).get();
        assert.strictEqual(JSON.stringify(chips), JSON.stringify(['n1', 'n3']));
        w.$('.pl-assistant__alias').first().trigger('click');
        assert.strictEqual(w.__selected.etlAlias, 'n1');
        w.$('.pl-assistant__alias').eq(1).trigger('mouseenter');
        assert.strictEqual(w.__figures[1].glow, true);
    });

    await test('Detener cancela la petición y no cambia el canvas', async () => {
        const w = makeEnv({ id: '7' });
        await tick();
        w.$('#etl-assistant-input').val('crea un flujo');
        w.$('#etl-assistant-form').trigger('submit');
        const send = w.$('#etl-assistant-send');
        assert.ok(send.hasClass('is-stop'));
        assert.strictEqual(send.prop('disabled'), false);
        w.$('#etl-assistant-form').trigger('submit');                     // segundo clic = detener
        assert.ok(w.__ajax[0].aborted);
        assert.ok(!send.hasClass('is-stop'));
        assert.ok(/Stopped/.test(w.$('.pl-assistant__bubble--error').text()));
        assert.strictEqual(w.__ajax.length, 1);
    });

    await test('↑ recupera preguntas anteriores; ↓ vuelve al cuadro vacío', async () => {
        const w = makeEnv({ id: '7' });
        await tick();
        ['primera', 'segunda'].forEach((q) => {
            w.$('#etl-assistant-input').val(q);
            w.$('#etl-assistant-form').trigger('submit');
            w.__ajax[w.__ajax.length - 1].respond(reply({ reply: 'ok' }));
        });
        const input = w.$('#etl-assistant-input');
        const key = (k) => input.trigger(w.$.Event('keydown', { key: k }));
        key('ArrowUp');
        assert.strictEqual(input.val(), 'segunda');
        key('ArrowUp');
        assert.strictEqual(input.val(), 'primera');
        input[0].setSelectionRange(input.val().length, input.val().length);
        key('ArrowDown');
        assert.strictEqual(input.val(), 'segunda');
        input[0].setSelectionRange(input.val().length, input.val().length);
        key('ArrowDown');
        assert.strictEqual(input.val(), '');
    });

    await test('contador y bloqueo por encima del límite', async () => {
        const w = makeEnv({ id: '7' });
        await tick();
        const input = w.$('#etl-assistant-input');
        input.val('x'.repeat(7500)).trigger('input');
        assert.strictEqual(w.$('#etl-assistant-counter').prop('hidden'), false);
        assert.strictEqual(w.$('#etl-assistant-send').prop('disabled'), false);
        input.val('x'.repeat(8100)).trigger('input');
        assert.ok(w.$('#etl-assistant-counter').hasClass('is-over'));
        assert.strictEqual(w.$('#etl-assistant-send').prop('disabled'), true);
        w.$('#etl-assistant-form').trigger('submit');
        assert.strictEqual(w.__ajax.length, 0);
    });

    await test('copiar, editar y reenviar, regenerar y estado en el historial', async () => {
        const w = makeEnv({ id: '7' });
        await tick();
        w.$('#etl-assistant-input').val('pregunta uno');
        w.$('#etl-assistant-form').trigger('submit');
        w.__ajax[0].respond(reply({ reply: 'Respuesta **uno**', summary: ['Añado Filter (n6).'],
            proposal: { mode: 'patch', ops: [] }, needs_confirmation: true }));
        const userTools = w.$('.pl-assistant__row--user .pl-assistant__tool');
        assert.strictEqual(userTools.length, 3);
        userTools.eq(0).trigger('click');
        assert.strictEqual(w.__copied[0], 'pregunta uno');
        userTools.eq(1).trigger('click');
        assert.strictEqual(w.$('#etl-assistant-input').val(), 'pregunta uno');
        // pendiente de aplicar: no se ofrece regenerar
        assert.strictEqual(w.$('.js-regenerate').length, 0);
        const lastTools = w.$('.pl-assistant__row').last().find('.pl-assistant__tool');
        lastTools.eq(0).trigger('click');
        await tick();
        assert.ok(/Respuesta \*\*uno\*\*[\s\S]*- Añado Filter \(n6\)\./.test(w.__copied[1]), w.__copied[1]);
        // el historial informa al modelo de que la propuesta sigue pendiente
        w.$('#etl-assistant-input').val('pregunta dos');
        w.$('#etl-assistant-form').trigger('submit');
        const history = w.__ajax[1].body.history;
        assert.deepStrictEqual(history.map((h) => h.role), ['user', 'assistant']);
        assert.strictEqual(history[1].status, 'pending');
        assert.deepStrictEqual(history[1].summary, ['Añado Filter (n6).']);
        w.__ajax[1].respond(reply({ reply: 'Respuesta dos' }));
        // regenerar la última: quita la pareja y vuelve a preguntar lo mismo
        assert.strictEqual(w.$('.js-regenerate').length, 1);
        w.$('.js-regenerate').trigger('click');
        assert.strictEqual(w.__ajax[2].body.message, 'pregunta dos');
        assert.strictEqual(w.$('#etl-assistant-messages').text().indexOf('Respuesta dos'), -1);
    });

    await test('exportar descarga la conversación en Markdown', async () => {
        const w = makeEnv({ id: '7' });
        await tick();
        let blob = null;
        w.URL.createObjectURL = (b) => { blob = b; return 'blob:x'; };
        w.URL.revokeObjectURL = () => {};
        w.HTMLAnchorElement.prototype.click = function () { this.__clicked = true; };
        w.$('#etl-assistant-input').val('hola');
        w.$('#etl-assistant-form').trigger('submit');
        w.__ajax[0].respond(reply({ reply: 'Buenas', warnings: ['ojo'] }));
        w.$('#etl-assistant-export').trigger('click');
        const text = await new Promise((resolve) => {
            const reader = new w.FileReader();
            reader.onload = () => resolve(reader.result);
            reader.readAsText(blob);
        });
        assert.ok(text.includes('**Workspace:** Mi flujo'));
        assert.ok(text.includes('**You:** hola'));
        assert.ok(text.includes('**Assistant:** Buenas'));
        assert.ok(text.includes('- ojo'));
    });

    console.log('\n' + passed + ' correctos, ' + failed + ' fallidos');
    process.exit(failed ? 1 : 0);
})();
