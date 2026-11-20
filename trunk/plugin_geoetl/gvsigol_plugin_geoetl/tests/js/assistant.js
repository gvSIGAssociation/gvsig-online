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
  <div id="etl-assistant-examples"><button type="button" class="pl-assistant__example" data-when="empty"
    data-guided-start="csv_postgis" data-example="Carga un CSV">CSV a PostGIS</button></div>
  <div id="etl-assistant-context" hidden></div>
  <form id="etl-assistant-form"><textarea id="etl-assistant-input"></textarea>
    <button type="submit" id="etl-assistant-send"><i class="fa fa-paper-plane"></i></button></form>
  <div id="etl-assistant-counter" hidden></div>
</aside>`;

function makeEnv(opts = {}) {
    let panel = PANEL.replace('__ID__', opts.id || '');
    if (opts.streaming) {
        panel = panel.replace('class="pl-assistant is-collapsed"', 'class="pl-assistant is-collapsed" data-streaming="1"');
    }
    if (opts.columns) {
        panel = panel.replace('class="pl-assistant is-collapsed"', 'class="pl-assistant is-collapsed" data-columns="1"');
    }
    if (opts.guided) {
        panel = panel.replace('class="pl-assistant is-collapsed"', 'class="pl-assistant is-collapsed" data-guided="1"');
    }
    const dom = new JSDOM('<!doctype html><body>' + panel + '</body>', {
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
    w.__gearClicks = [];
    const figure = (id, alias, name, x, y) => ({
        id, etlAlias: alias, NAME: name, x, y, glow: false,
        classLabel: { getText: () => name,
            __gear: { figure: { fireEvent: (ev) => w.__gearClicks.push(alias + ':' + ev) } } },
        getX: () => x, getY: () => y,
        setGlow(on) { this.glow = on; }, getCanvas: () => ({})
    });
    w.__figures = [figure('uuid-1', 'n1', 'input_Postgis', 100.4, 80), figure('uuid-3', 'n3', 'trans_Filter', 380, 80)];
    const list = (arr) => ({ each(fn) { arr.forEach((f, i) => fn(i, f)); }, clone() { return list(arr.slice()); } });
    if (opts.empty) {
        w.__figures = [];
    }
    w.__selected = null;
    w.etlApp = { view: {
        _etlAliasTop: 5,                         // se borró n4 y n5: no se reutilizan
        getFigures: () => list(w.__figures),
        getLines: () => list([]),
        getFigure: (id) => w.__figures.find((f) => f.id === id) || null,
        getCommandStack: () => w.__stack,
        on() {}, setCurrentSelection(f) { w.__selected = f; }
    } };
    w.etlFindGear = (label) => label.__gear;                       // NodeHeader.js
    // Pila de Deshacer mínima de draw2d y lo que usa applyProposal
    w.__filled = [];
    w.__select2 = [];
    w.$.fn.select2 = function (options) { w.__select2.push({ el: this[0], options }); return this; };
    w.__stack = {
        done: [], label: null, inTx: false,
        addEventListener() {},
        startTransaction(label) { this.inTx = true; this.label = label; this.tx = []; },
        execute(cmd) { if (cmd.execute) { cmd.execute(); } (this.inTx ? this.tx : this.done).push(cmd); },
        commitTransaction() { this.inTx = false; this.done.push({ label: this.label, cmds: this.tx }); },
        isInTransaction() { return this.inTx; },
        getUndoLabel() { const last = this.done[this.done.length - 1]; return last ? last.label : null; },
        undo() { const last = this.done.pop(); (last.cmds || []).slice().reverse().forEach((c) => c.undo && c.undo()); }
    };
    w.EtlApplyCommand = function (redo, undo) { this.execute = redo; this.undo = undo; };
    w.fillEtlNodeForm = (...args) => w.__filled.push(args);
    w.__gears = [];
    w.__propagated = [];
    w.setGearColorForNode = (id, f, type, ok) => w.__gears.push([id, ok]);
    w.propagateSchemaFrom = (id) => w.__propagated.push(id);
    w.fm_directory = '/fm/';
    w.__opened = [];
    w.__popup = { closed: false, close() { this.closed = true; } };
    w.open = (url) => { w.__opened.push(url); return w.__popup; };
    w.filemanagerCallback = function nodeCallback() {};
    w.eval('var jsonParams = [{id: "uuid-1", parameters: [{db: "gis"}], schema: ["a"], "schema-old": []}];');
    // Backend simulado: cada petición queda pendiente hasta que el test la responde
    w.__ajax = [];
    w.$.ajax = function (o) {
        const req = { opts: o, aborted: false, body: JSON.parse(o.data) };
        req.abort = () => { req.aborted = true; o.error({ status: 0 }, 'abort'); if (o.complete) { o.complete(); } };
        req.respond = (data) => { o.success(data); if (o.complete) { o.complete(); } };
        w.__ajax.push(req);
        return req;
    };
    // fetch simulado (streaming): el test va entregando el flujo SSE trozo a trozo
    w.__fetch = [];
    w.TextDecoder = TextDecoder;
    w.fetch = function (url, opts) {
        const req = { url, opts, body: JSON.parse(opts.body), cancelled: false };
        const queue = [];
        let waiting = null;
        const deliver = (item) => { if (waiting) { const r = waiting; waiting = null; r(item); } else { queue.push(item); } };
        req.push = (text) => deliver({ done: false, value: new TextEncoder().encode(text) });
        req.end = () => deliver({ done: true });
        const reader = {
            read: () => (queue.length ? Promise.resolve(queue.shift()) : new Promise((r) => { waiting = r; })),
            cancel: () => { req.cancelled = true; return Promise.resolve(); }
        };
        w.__fetch.push(req);
        if (url.indexOf('/cancel/') !== -1) {
            return Promise.resolve({ ok: true, status: 200 });
        }
        return new Promise((resolve, reject) => {
            opts.signal.addEventListener('abort', () => { req.aborted = true; reject(new Error('AbortError')); });
            resolve({ status: opts.status || 200, ok: true, headers: { get: () => 'text/event-stream' },
                body: { getReader: () => reader } });
        });
    };
    w.eval(read('Assistant.js'));
    return w;
}

// Parámetros del primer nodo, sin las listas de los desplegables (get_*)
const params = (w) => JSON.stringify(Object.fromEntries(
    Object.entries(JSON.parse(w.eval('JSON.stringify(jsonParams[0].parameters[0])'))).filter(([k]) => !k.startsWith('get_'))));

const sse = (event) => 'data: ' + JSON.stringify(event) + '\n\n';

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

    console.log('Streaming (ETL_ASSISTANT_STREAMING)');

    await test('sin el interruptor sigue usando la petición de siempre', async () => {
        const w = makeEnv({ id: '7' });
        await tick();
        w.$('#etl-assistant-input').val('hola');
        w.$('#etl-assistant-form').trigger('submit');
        assert.strictEqual(w.__ajax.length, 1);
        assert.strictEqual(w.__fetch.length, 0);
    });

    await test('pasos en vivo y resultado por el stream', async () => {
        const w = makeEnv({ id: '7', streaming: true });
        await tick();
        w.$('#etl-assistant-input').val('carga municipios');
        w.$('#etl-assistant-form').trigger('submit');
        assert.strictEqual(w.__ajax.length, 0);
        const req = w.__fetch[0];
        assert.strictEqual(req.url, '/gvsigonline/etl/etl_assistant/stream/');
        assert.strictEqual(req.body.message, 'carga municipios');
        assert.strictEqual(req.body.canvas.next_alias, 'n6');                 // mismo cuerpo que la petición de siempre
        assert.ok(/^q[a-z0-9]+$/.test(req.body.query_id));
        req.push(sse({ type: 'start', query_id: req.body.query_id }));
        req.push(sse({ type: 'step', tool: 'get_table_schema',
            detail: { connection: 'gis', schema: 'public', table: 'municipios' } }));
        await tick();
        req.push(sse({ type: 'ping' }) + sse({ type: 'step', tool: 'propose_workspace', detail: {} }));
        await tick();
        const steps = w.$('.pl-assistant__step').map((i, el) => el.textContent).get();
        assert.strictEqual(JSON.stringify(steps),
            JSON.stringify(['Reading the columns of public.municipios', 'Validating the proposal']));
        assert.ok(w.$('.pl-assistant__step').last().hasClass('is-current'));
        // el resultado llega partido en dos trozos
        const frame = sse({ type: 'result', payload: reply({ reply: 'Listo, n1 cargado.' }) });
        req.push(frame.slice(0, 20));
        await tick();
        assert.strictEqual(w.$('.pl-assistant__steps').length, 1);            // aún pensando
        req.push(frame.slice(20));
        await tick();
        assert.strictEqual(w.$('.pl-assistant__steps').length, 0);
        assert.ok(w.$('#etl-assistant-messages').text().includes('Listo, n1 cargado.'));
        assert.ok(!w.$('#etl-assistant-send').hasClass('is-stop'));
        assert.ok(req.cancelled);                                              // deja de leer tras el resultado
    });

    await test('Detener corta el stream y avisa al servidor', async () => {
        const w = makeEnv({ id: '7', streaming: true });
        await tick();
        w.$('#etl-assistant-input').val('crea un flujo');
        w.$('#etl-assistant-form').trigger('submit');
        const req = w.__fetch[0];
        req.push(sse({ type: 'step', tool: 'list_connections', detail: {} }));
        await tick();
        w.$('#etl-assistant-form').trigger('submit');                         // segundo clic = detener
        await tick();
        assert.ok(req.aborted);
        const cancel = w.__fetch[1];
        assert.strictEqual(cancel.url, '/gvsigonline/etl/etl_assistant/cancel/');
        assert.strictEqual(cancel.body.query_id, req.body.query_id);
        assert.ok(/Stopped/.test(w.$('.pl-assistant__bubble--error').text()));
        assert.ok(!w.$('#etl-assistant-send').hasClass('is-stop'));
        assert.strictEqual(w.$('.pl-assistant__bubble--error').length, 1);     // un solo aviso
    });

    await test('texto en vivo: se acumula, se reinicia y lo sustituye la respuesta final', async () => {
        const w = makeEnv({ id: '7', streaming: true });
        await tick();
        w.$('#etl-assistant-input').val('añade un filtro');
        w.$('#etl-assistant-form').trigger('submit');
        const req = w.__fetch[0];
        req.push(sse({ type: 'answer_delta', delta: 'Voy a ', reset: true }) +
            sse({ type: 'answer_delta', delta: 'mirar', reset: false }));
        await tick();
        assert.strictEqual(w.$('.pl-assistant__live').text().trim(), 'Voy a mirar');
        req.push(sse({ type: 'step', tool: 'check_workspace', detail: {} }) +
            sse({ type: 'answer_delta', delta: 'He añadido **n2**', reset: true }) +
            sse({ type: 'answer_delta', delta: '<img src=x onerror=alert(1)>', reset: false }));
        await tick();
        const live = w.$('.pl-assistant__live');
        assert.strictEqual(live.find('strong').text(), 'n2');                 // Markdown
        assert.strictEqual(live.find('img').attr('onerror'), undefined);      // saneado
        assert.strictEqual(live.text().indexOf('Voy a mirar'), -1);           // reset
        assert.strictEqual(w.$('.pl-assistant__step').length, 1);              // los pasos siguen
        req.push(sse({ type: 'result', payload: reply({ reply: 'Filtro añadido (n2).' }) }));
        await tick();
        assert.strictEqual(w.$('.pl-assistant__live').length, 0);
        const text = w.$('#etl-assistant-messages').text();
        assert.ok(text.includes('Filtro añadido (n2).'));
        assert.strictEqual(text.indexOf('He añadido'), -1);                   // manda el resultado
    });

    console.log('Problemas con botones (ETL_ASSISTANT_ACTIONS)');

    const ISSUES = [
        { level: 'error', node: 'n3', code: 'unconfigured', message: 'Filter (n3): está sin configurar.' },
        { level: 'error', node: 'n3', code: 'unconnected_input', message: 'Filter (n3): la entrada 0 no está conectada.' },
        { level: 'error', node: 'n9', code: 'missing_parameter', param: 'csv-file', message: 'CSV (n9): falta csv-file.' },
        { level: 'warning', node: null, code: 'no_output', message: 'El flujo no termina en ninguna salida.' }
    ];

    await test('sin issues el panel no cambia', async () => {
        const w = makeEnv({ id: '7' });
        await tick();
        w.$('#etl-assistant-input').val('revisa');
        w.$('#etl-assistant-form').trigger('submit');
        w.__ajax[0].respond(reply({ reply: 'Todo bien.' }));
        assert.strictEqual(w.$('.pl-assistant__issues').length, 0);
    });

    await test('Configurar abre el engranaje del nodo sin llamar al asistente', async () => {
        const w = makeEnv({ id: '7' });
        await tick();
        w.$('#etl-assistant-input').val('revisa');
        w.$('#etl-assistant-form').trigger('submit');
        w.__ajax[0].respond(reply({ reply: 'Hay problemas.', issues: ISSUES }));
        const items = w.$('.pl-assistant__issue');
        assert.strictEqual(items.length, 4);
        assert.ok(items.eq(0).hasClass('is-error'));
        items.eq(0).find('button').trigger('click');
        assert.strictEqual(JSON.stringify(w.__gearClicks), JSON.stringify(['n3:click']));
        assert.strictEqual(w.__selected.etlAlias, 'n3');
        assert.strictEqual(w.__ajax.length, 1);                              // sin turno nuevo
        // nodo que no está en el canvas: aviso y nada más
        items.eq(2).find('button').trigger('click');
        assert.strictEqual(w.__gearClicks.length, 1);
        assert.ok(/Apply the changes first/.test(items.eq(2).find('.pl-assistant__issue-note').text()));
    });

    await test('Arreglar y Arreglar todo piden el arreglo al asistente', async () => {
        const w = makeEnv({ id: '7' });
        await tick();
        w.$('#etl-assistant-input').val('revisa');
        w.$('#etl-assistant-form').trigger('submit');
        w.__ajax[0].respond(reply({ reply: 'Hay problemas.', issues: ISSUES }));
        const items = w.$('.pl-assistant__issue');
        assert.strictEqual(items.eq(1).find('button').text(), 'Fix problem');
        items.eq(1).find('button').trigger('click');
        assert.strictEqual(w.__ajax[1].body.message, 'Fix this problem: Filter (n3): la entrada 0 no está conectada.');
        w.__ajax[1].respond(reply({ reply: 'Arreglado.' }));
        // dos de estructura (entrada sin conectar y sin salida): Arreglar todo
        const all = w.$('.pl-assistant__issues').first().find('.pl-assistant__actions button');
        assert.strictEqual(all.text(), 'Fix all problems');
        all.trigger('click');
        const message = w.__ajax[2].body.message;
        assert.ok(message.startsWith('Fix these problems:'));
        assert.ok(message.includes('- Filter (n3): la entrada 0 no está conectada.'));
        assert.ok(message.includes('- El flujo no termina en ninguna salida.'));
        assert.ok(!message.includes('está sin configurar'));                // lo de configurar no se pide
        // se ve como pregunta del usuario
        assert.ok(w.$('.pl-assistant__bubble--user').last().text().startsWith('Fix these problems:'));
    });

    await test('los problemas se conservan al recargar el panel', async () => {
        const w = makeEnv({ id: '7' });
        await tick();
        w.$('#etl-assistant-input').val('revisa');
        w.$('#etl-assistant-form').trigger('submit');
        w.__ajax[0].respond(reply({ reply: 'Hay problemas.', issues: ISSUES }));
        const saved = w.sessionStorage.getItem('etl-assistant-chat:7');
        const again = makeEnv({ id: '7', session: { 'etl-assistant-chat:7': saved } });
        await tick();
        assert.strictEqual(again.$('.pl-assistant__issue').length, 4);
    });

    console.log('Preguntas con opciones (ETL_ASSISTANT_QUESTIONS)');

    const MANY = Array.from({ length: 9 }, (_, i) => ({ value: 'campo_' + i, label: 'campo_' + i }));
    const QUESTIONS = [
        { id: 'q1', label: 'Separador', text: '¿Qué separador usa el CSV?', node: 'n1', param: 'separator',
            multiple: false, options: [{ value: ';', label: ';' }, { value: ',', label: ',' }] },
        { id: 'q2', label: 'Campo de cruce', text: '¿Por qué campo cruzo?', multiple: false, options: MANY },
        { id: 'q3', label: 'Fichero', text: '¿Qué fichero?', multiple: false,
            options: [{ value: 'file:///fm/rol_a/padron.csv', label: 'rol_a/padron.csv' }] },
        { id: 'q4', label: 'Nombre', text: '¿Cómo llamo a la tabla?', multiple: false, options: [] }
    ];

    async function askedEnv() {
        const w = makeEnv({ id: '7' });
        await tick();
        w.$('#etl-assistant-input').val('carga el csv');
        w.$('#etl-assistant-form').trigger('submit');
        w.__ajax[0].respond(reply({ reply: 'Necesito unos datos.', questions: QUESTIONS }));
        return w;
    }

    await test('tarjeta: opciones, lista con buscador, Otro y texto libre', async () => {
        const w = await askedEnv();
        const blocks = w.$('.pl-assistant__question');
        assert.strictEqual(blocks.length, 4);
        assert.strictEqual(blocks.eq(0).find('legend').text(), '¿Qué separador usa el CSV?');
        assert.strictEqual(blocks.eq(0).find('input[type=radio]').length, 3);   // 2 + Otro
        const select = blocks.eq(1).find('select');
        assert.strictEqual(select.find('option').length, 10);                     // más de 6: desplegable
        assert.strictEqual(select.attr('size'), undefined);
        assert.strictEqual(w.__select2[0].el, select[0]);                         // con buscador integrado
        assert.strictEqual(blocks.eq(1).find('input[type=search]').length, 0);
        assert.strictEqual(w.$('.pl-assistant__progress').text(), '0 of 4');
        assert.strictEqual(blocks.eq(3).find('input[type=text]').length, 1);     // sin opciones: texto libre
        const submit = w.$('.pl-assistant__questions button.btn-pl-add');
        assert.strictEqual(submit.prop('disabled'), true);
    });

    await test('Responder envía "Etiqueta: valor" y la tarjeta queda respondida', async () => {
        const w = await askedEnv();
        const blocks = w.$('.pl-assistant__question');
        blocks.eq(0).find('input[type=radio]').eq(0).prop('checked', true).trigger('change');
        blocks.eq(1).find('select').val('campo_3').trigger('change');
        blocks.eq(2).find('input[type=radio]').eq(0).prop('checked', true).trigger('change');
        const submit = w.$('.pl-assistant__questions button.btn-pl-add');
        assert.strictEqual(submit.prop('disabled'), true);                      // falta el nombre
        blocks.eq(3).find('input[type=text]').val('padron_2025').trigger('input');
        assert.strictEqual(submit.prop('disabled'), false);
        submit.trigger('click');
        const message = w.__ajax[1].body.message;
        assert.strictEqual(message, 'Separador: ; · Campo de cruce: campo_3 · ' +
            'Fichero: rol_a/padron.csv (file:///fm/rol_a/padron.csv) · Nombre: padron_2025');
        assert.ok(w.$('.pl-assistant__bubble--user').last().text().startsWith('Separador: ;'));
        const card = w.$('.pl-assistant__questions');
        assert.ok(card.hasClass('is-answered'));
        assert.strictEqual(card.find('input, select').length, 0);
        assert.strictEqual(card.find('.pl-assistant__answer').eq(2).text(), 'rol_a/padron.csv');
        // el modelo sabrá qué preguntó
        const history = w.__ajax[1].body.history;
        assert.strictEqual(history[1].questions[1].label, 'Campo de cruce');
        // al recargar se ve respondida
        const again = makeEnv({ id: '7', session: { 'etl-assistant-chat:7': w.sessionStorage.getItem('etl-assistant-chat:7') } });
        await tick();
        assert.ok(again.$('.pl-assistant__questions').hasClass('is-answered'));
    });

    await test('Otro… con texto propio', async () => {
        const w = makeEnv({ id: '7' });
        await tick();
        w.$('#etl-assistant-input').val('carga');
        w.$('#etl-assistant-form').trigger('submit');
        w.__ajax[0].respond(reply({ reply: 'Una duda.', questions: [QUESTIONS[0]] }));
        const block = w.$('.pl-assistant__question');
        const other = block.find('.pl-assistant__other');
        assert.strictEqual(other.prop('disabled'), true);
        block.find('input.js-other').prop('checked', true).trigger('change');
        assert.strictEqual(other.prop('disabled'), false);
        other.val('|').trigger('input');
        other.trigger(w.$.Event('keydown', { key: 'Enter' }));                 // Enter responde
        assert.strictEqual(w.__ajax[1].body.message, 'Separador: |');
    });

    await test('el cuadro de texto crece sin barra y la saca solo al llegar al máximo', async () => {
        const w = makeEnv({ id: '7' });
        await tick();
        const input = w.$('#etl-assistant-input');
        const box = input[0];
        const size = (scroll) => Object.defineProperties(box, {
            scrollHeight: { configurable: true, value: scroll }, offsetHeight: { configurable: true, value: 40 },
            clientHeight: { configurable: true, value: 38 } });
        size(58);
        input.trigger('input');
        assert.strictEqual([box.style.height, box.style.overflowY].join('|'), '60px|hidden');   // cuenta el borde
        size(300);
        input.trigger('input');
        assert.strictEqual([box.style.height, box.style.overflowY].join('|'), '140px|auto');
    });

    console.log('Administrador de archivos');

    async function fileQuestionEnv() {
        const w = makeEnv({ id: '7' });
        await tick();
        w.$('#etl-assistant-input').val('carga');
        w.$('#etl-assistant-form').trigger('submit');
        w.__ajax[0].respond(reply({ reply: 'Una duda.', questions: [
            { id: 'q1', label: 'Shapefile', text: '¿Qué shapefile?', multiple: false, source: 'files', options: [],
                file_picker: { extensions: 'shp' } }] }));
        return w;
    }

    await test('pregunta de fichero: abre el administrador y usa la ruta elegida', async () => {
        const w = await fileQuestionEnv();
        const nodeCallback = w.filemanagerCallback;
        const submit = w.$('.pl-assistant__questions .btn-pl-add');
        assert.strictEqual(w.$('.pl-assistant__question select').length, 0);    // no se listan
        w.$('.js-file-picker').trigger('click');
        assert.strictEqual(w.__opened[0], '/gvsigonline/filemanager/?popup=1');
        assert.notStrictEqual(w.filemanagerCallback, nodeCallback);
        w.filemanagerCallback('rol_a/rios.shp', 'rios.shp');
        assert.strictEqual(w.filemanagerCallback, nodeCallback);               // devuelve la de los nodos
        assert.strictEqual(w.$('.pl-assistant__file-name').text(), 'rol_a/rios.shp');
        assert.strictEqual(w.$('.pl-assistant__file-chosen').css('display'), 'flex');
        assert.strictEqual(w.$('.js-file-picker').css('display'), 'none');        // se cambia con Cambiar
        assert.strictEqual(submit.prop('disabled'), false);
        submit.trigger('click');
        assert.strictEqual(w.__ajax[1].body.message, 'Shapefile: rol_a/rios.shp (file:///fm/rol_a/rios.shp)');
    });

    await test('fichero de otro tipo: avisa y no lo acepta', async () => {
        const w = await fileQuestionEnv();
        w.$('.js-file-picker').trigger('click');
        w.filemanagerCallback('rol_a/datos.csv', 'datos.csv');
        assert.ok(/Choose a file of type: \.shp/.test(w.$('.pl-assistant__question .pl-assistant__field-error').text()));
        assert.strictEqual(w.$('.pl-assistant__questions .btn-pl-add').prop('disabled'), true);
    });

    await test('cerrar el administrador sin elegir devuelve el callback de los nodos', async () => {
        const w = await fileQuestionEnv();
        const nodeCallback = w.filemanagerCallback;
        w.$('.js-file-picker').trigger('click');
        w.__popup.closed = true;
        await tick(600);
        assert.strictEqual(w.filemanagerCallback, nodeCallback);
    });

    await test('si el usuario escribe en el cuadro, las preguntas se cierran', async () => {
        const w = await askedEnv();
        w.$('#etl-assistant-input').val('usa punto y coma y el campo cod_mun');
        w.$('#etl-assistant-form').trigger('submit');
        const card = w.$('.pl-assistant__questions');
        assert.ok(card.hasClass('is-skipped'));
        assert.strictEqual(card.find('input:not(:disabled), select:not(:disabled)').length, 0);
        const saved = JSON.parse(w.sessionStorage.getItem('etl-assistant-chat:7'));
        assert.strictEqual(saved.messages[1].questionsState, 'skipped');
    });

    console.log('Suposiciones cambiables (ETL_ASSISTANT_ALTERNATIVES)');

    const CHOICE = { text: 'n1: conexión gis', node: 'n1', param: 'db', value: 'gis',
        options: [{ value: 'gis', label: 'gis' }, { value: 'pg', label: 'pg' }] };

    async function alternativesEnv(extra) {
        const w = makeEnv({ id: '7' });
        await tick();
        w.eval('jsonParams[0].parameters = [{db: "gis", "schema-name": "public"}]');
        w.$('#etl-assistant-input').val('carga');
        w.$('#etl-assistant-form').trigger('submit');
        // copia, como una respuesta JSON de verdad
        w.__ajax[0].respond(JSON.parse(JSON.stringify(reply(Object.assign({ reply: 'Hecho.',
            assumptions: ['n1: conexión gis', 'n1: otra cosa'], assumption_choices: [CHOICE] }, extra || {})))));
        return w;
    }

    await test('cambiar una suposición aplica el parámetro sin llamar al asistente', async () => {
        const w = await alternativesEnv();
        const select = w.$('.pl-assistant__alternative select');
        assert.strictEqual(select.length, 1);                                   // solo la que tiene alternativas
        assert.strictEqual(select.val(), 'gis');
        select.val('pg').trigger('change');
        assert.strictEqual(w.eval('JSON.stringify(jsonParams[0].parameters)'),
            JSON.stringify([{ db: 'pg', 'schema-name': 'public' }]));          // conserva el resto
        assert.strictEqual(w.__filled[0][1].id, 'uuid-1');
        assert.strictEqual(w.__stack.getUndoLabel(), 'etl-assistant-param');   // una entrada de Deshacer, propia
        assert.strictEqual(w.__ajax.length, 1);                                // sin turno nuevo
        // el modelo lo sabrá en el siguiente turno
        w.$('#etl-assistant-input').val('sigue');
        w.$('#etl-assistant-form').trigger('submit');
        const history = w.__ajax[1].body.history;
        assert.strictEqual(JSON.stringify(history[1].changes), JSON.stringify([{ node: 'n1', param: 'db', value: 'pg' }]));
    });

    await test('Deshacer del cambio vuelve al valor anterior', async () => {
        const w = await alternativesEnv();
        const select = w.$('.pl-assistant__alternative select');
        select.val('pg').trigger('change');
        w.$('.pl-assistant__alternative-undo').trigger('click');
        assert.strictEqual(w.eval('jsonParams[0].parameters[0].db'), 'gis');
        assert.strictEqual(select.val(), 'gis');
        assert.strictEqual(w.$('.pl-assistant__alternative-undo').length, 0);
        // al recargar se ve el valor vigente
        const again = makeEnv({ id: '7', session: { 'etl-assistant-chat:7': w.sessionStorage.getItem('etl-assistant-chat:7') } });
        await tick();
        assert.strictEqual(again.$('.pl-assistant__alternative select').val(), 'gis');
    });

    await test('con la propuesta pendiente de aplicar, el desplegable espera', async () => {
        const w = await alternativesEnv({ proposal: { mode: 'patch', ops: [] }, needs_confirmation: true });
        const select = w.$('.pl-assistant__alternative select');
        assert.strictEqual(select.prop('disabled'), true);
        assert.ok(/Apply the changes first/.test(select.attr('title')));
        // al aplicar la propuesta, se puede cambiar
        w.$('.pl-assistant__actions .btn-pl-add').trigger('click');
        assert.strictEqual(select.prop('disabled'), false);
        select.val('pg').trigger('change');
        assert.strictEqual(w.eval('jsonParams[0].parameters[0].db'), 'pg');
    });

    await test('nodo que ya no está: no cambia nada y avisa', async () => {
        const w = await alternativesEnv({ assumption_choices: [Object.assign({}, CHOICE, { node: 'n9' })],
            assumptions: ['n1: conexión gis'] });
        const select = w.$('.pl-assistant__alternative select');
        select.val('pg').trigger('change');
        assert.strictEqual(select.val(), 'gis');
        assert.strictEqual(w.__stack.done.length, 0);
        assert.ok(w.$('.pl-assistant__alternative .pl-assistant__issue-note').length);
    });

    await test('Deshacer de un desplegable solo revierte ese cambio', async () => {
        const w = makeEnv({ id: '7' });
        await tick();
        w.eval('jsonParams[0].parameters = [{db: "gis", "schema-name": "public"}]');
        w.$('#etl-assistant-input').val('carga');
        w.$('#etl-assistant-form').trigger('submit');
        w.__ajax[0].respond(JSON.parse(JSON.stringify(reply({ reply: 'Hecho.', assumptions: ['a', 'b'], assumption_choices: [
            { text: 'a', node: 'n1', param: 'db', value: 'gis', options: [{ value: 'gis', label: 'gis' }, { value: 'pg', label: 'pg' }] },
            { text: 'b', node: 'n1', param: 'schema-name', value: 'public', options: [{ value: 'public', label: 'public' }, { value: 'datos', label: 'datos' }] }
        ] }))));
        const selects = w.$('.pl-assistant__alternative select');
        selects.eq(0).val('pg').trigger('change');
        selects.eq(1).val('datos').trigger('change');
        w.$('.pl-assistant__alternative').eq(0).find('.pl-assistant__alternative-undo').trigger('click');
        assert.strictEqual(params(w), JSON.stringify({ db: 'gis', 'schema-name': 'datos' }));
        assert.strictEqual(selects.eq(0).val(), 'gis');
        const saved = JSON.parse(w.sessionStorage.getItem('etl-assistant-chat:7'));
        assert.strictEqual(JSON.stringify(saved.messages[1].changes),
            JSON.stringify([{ node: 'n1', param: 'schema-name', value: 'datos' }]));
    });

    console.log('Completar parámetros (ETL_ASSISTANT_PARAM_PICKER)');

    const PICK = { level: 'error', node: 'n1', code: 'missing_parameter', param: 'tablename',
        pick: { type: 'input_Postgis' }, message: 'PostGIS (n1): falta tablename.' };

    async function pickerEnv(extra) {
        const w = makeEnv({ id: '7' });
        await tick();
        w.eval('jsonParams[0].parameters = [{db: "gis", "schema-name": "public"}]');
        w.$('#etl-assistant-input').val('revisa');
        w.$('#etl-assistant-form').trigger('submit');
        w.__ajax[0].respond(JSON.parse(JSON.stringify(reply(Object.assign({ reply: 'Falta un dato.', issues: [PICK] }, extra || {})))));
        return w;
    }
    const OPTIONS = [{ value: 'municipios', label: 'municipios' }, { value: 'padron', label: 'padron' }];

    await test('sin pick solo está Configurar', async () => {
        const w = await pickerEnv({ issues: [Object.assign({}, PICK, { pick: undefined })] });
        assert.strictEqual(w.$('.js-pick').length, 0);
        assert.strictEqual(w.$('.pl-assistant__issue button').length, 1);
    });

    await test('Elegir carga las opciones y aplica sin llamar al asistente', async () => {
        const w = await pickerEnv();
        w.$('.js-pick').trigger('click');
        const load = w.__ajax[1];
        assert.strictEqual(load.opts.url, '/gvsigonline/etl/etl_assistant/options/');
        assert.strictEqual(JSON.stringify([load.body.type, load.body.param, load.body.workspace_id]),
            JSON.stringify(['input_Postgis', 'tablename', '7']));
        assert.strictEqual(load.body.parameters.db, 'gis');
        load.respond({ options: OPTIONS, needs: null, error: false });
        const select = w.$('.pl-assistant__picker select');
        assert.strictEqual(select.find('option').length, 3);                  // con "Elige una opción"
        select.val('padron').trigger('change');
        assert.strictEqual(params(w), JSON.stringify({ db: 'gis', 'schema-name': 'public', tablename: 'padron' }));
        const item = w.$('.pl-assistant__issue');
        assert.ok(item.hasClass('is-resolved'));
        assert.ok(/Value chosen: padron/.test(item.text()));
        assert.strictEqual(w.$('.js-pick').length, 0);
        assert.strictEqual(w.__ajax.length, 2);                               // ningún turno nuevo
        // el modelo lo sabrá y sigue resuelto al recargar
        const saved = w.sessionStorage.getItem('etl-assistant-chat:7');
        assert.strictEqual(JSON.stringify(JSON.parse(saved).messages[1].changes),
            JSON.stringify([{ node: 'n1', param: 'tablename', value: 'padron' }]));
        const again = makeEnv({ id: '7', session: { 'etl-assistant-chat:7': saved } });
        await tick();
        assert.ok(again.$('.pl-assistant__issue').hasClass('is-resolved'));
    });

    await test('Deshacer quita el valor y vuelve a ofrecer Elegir', async () => {
        const w = await pickerEnv();
        w.$('.js-pick').trigger('click');
        w.__ajax[1].respond({ options: OPTIONS, needs: null, error: false });
        w.$('.pl-assistant__picker select').val('padron').trigger('change');
        w.$('.pl-assistant__issue-resolved button').trigger('click');
        assert.strictEqual(params(w), JSON.stringify({ db: 'gis', 'schema-name': 'public' }));
        assert.ok(!w.$('.pl-assistant__issue').hasClass('is-resolved'));
        assert.strictEqual(w.$('.js-pick').length, 1);
        const saved = JSON.parse(w.sessionStorage.getItem('etl-assistant-chat:7'));
        assert.strictEqual(saved.messages[1].issues[0].resolved, undefined);
        assert.strictEqual(saved.messages[1].changes.length, 0);
    });

    await test('avisos: falta la conexión, sin opciones y error al cargar', async () => {
        const w = await pickerEnv();
        const note = () => w.$('.pl-assistant__issue-note').text();
        w.$('.js-pick').trigger('click');
        w.__ajax[1].respond({ options: [], needs: 'connection', error: false });
        assert.ok(/connection of the node/.test(note()));
        w.$('.js-pick').trigger('click');
        w.__ajax[2].respond({ options: [], needs: null, error: false });
        assert.ok(/no options/.test(note()));
        w.$('.js-pick').trigger('click');
        w.__ajax[3].respond({ options: [], needs: null, error: true });
        assert.ok(/could not be loaded/.test(note()));
        w.$('.js-pick').trigger('click');
        w.__ajax[4].abort();
        assert.ok(/could not be loaded/.test(note()));
        assert.strictEqual(w.$('.js-pick').prop('disabled'), false);
    });

    await test('Elegir usa el desplegable con buscador', async () => {
        const w = await pickerEnv();
        w.$('.js-pick').trigger('click');
        w.__ajax[1].respond({ options: MANY, needs: null, error: false });
        const box = w.$('.pl-assistant__picker');
        assert.strictEqual(box.find('option').length, MANY.length + 1);
        assert.ok(w.__select2.some((entry) => entry.el === box.find('select')[0]));
    });

    await test('con la propuesta pendiente no se pide nada hasta aplicarla', async () => {
        const w = await pickerEnv({ proposal: { mode: 'patch', ops: [] }, needs_confirmation: true });
        w.$('.js-pick').trigger('click');
        assert.strictEqual(w.__ajax.length, 1);
        assert.ok(/Apply the changes first/.test(w.$('.pl-assistant__issue-note').text()));
        w.$('.pl-assistant__actions .btn-pl-add').trigger('click');
        w.$('.js-pick').trigger('click');
        assert.strictEqual(w.__ajax.length, 2);
    });

    console.log('Siguiente paso y arranque guiado (ETL_ASSISTANT_NEXT_STEPS)');

    const STEPS = [{ code: 'add_output' }, { code: 'explain' }, { code: 'inventado' }];

    await test('sugerencias: envían su mensaje y solo están en la última respuesta', async () => {
        const w = makeEnv({ id: '7' });
        await tick();
        w.$('#etl-assistant-input').val('hola');
        w.$('#etl-assistant-form').trigger('submit');
        w.__ajax[0].respond(reply({ reply: 'Hecho.', next_steps: STEPS }));
        const buttons = w.$('.pl-assistant__next-step');
        assert.strictEqual(buttons.map((i, el) => el.textContent).get().join('|'), 'Add a PostGIS output|Explain the flow');
        buttons.eq(1).trigger('click');
        assert.strictEqual(w.__ajax[1].body.message, 'Explain what the flow on the canvas does, step by step.');
        assert.strictEqual(w.$('.pl-assistant__next').length, 0);             // mientras piensa, ninguna
        w.__ajax[1].respond(reply({ reply: 'Explicado.' }));
        assert.strictEqual(w.$('.pl-assistant__next').length, 0);
    });

    await test('sugerencias: se ven al recargar y desaparecen si se deshace la propuesta', async () => {
        const w = makeEnv({ id: '7' });
        await tick();
        w.$('#etl-assistant-input').val('hola');
        w.$('#etl-assistant-form').trigger('submit');
        w.__ajax[0].respond(reply({ reply: 'Hecho.', proposal: { mode: 'patch', ops: [] }, next_steps: STEPS }));
        const reload = () => { const a = makeEnv({ id: '7', session: { 'etl-assistant-chat:7': w.sessionStorage.getItem('etl-assistant-chat:7') } }); return tick().then(() => a); };
        assert.strictEqual((await reload()).$('.pl-assistant__next').length, 1);
        w.$('.pl-assistant__actions button').first().trigger('click');         // Deshacer de la propuesta
        assert.strictEqual(w.$('.pl-assistant__next').length, 0);
        assert.strictEqual((await reload()).$('.pl-assistant__next').length, 0);
    });

    await test('Deshacer de la propuesta no se lleva un parámetro elegido después', async () => {
        const w = await alternativesEnv({ proposal: { mode: 'patch', ops: [] } });
        w.$('.pl-assistant__alternative select').val('pg').trigger('change');
        w.$('.pl-assistant__actions button').first().trigger('click');
        assert.strictEqual(w.eval('jsonParams[0].parameters[0].db'), 'pg');
        const saved = JSON.parse(w.sessionStorage.getItem('etl-assistant-chat:7'));
        assert.notStrictEqual(saved.messages[1].settled, 'undone');
    });

    const PG = [{ value: 'gis', label: 'gis' }];
    const example = (w) => w.$('.pl-assistant__example');

    await test('sin el interruptor el ejemplo se envía como siempre', async () => {
        const w = makeEnv({ empty: true });
        await tick();
        example(w).trigger('click');
        assert.strictEqual(w.__ajax[0].body.message, 'Carga un CSV');
        assert.strictEqual(w.$('.pl-assistant__guided').length, 0);
    });

    await test('arranque guiado: elige fichero y conexión y compone la petición', async () => {
        const w = makeEnv({ empty: true, guided: true });
        await tick();
        example(w).trigger('click');
        assert.strictEqual(JSON.stringify([w.__ajax[0].body.type, w.__ajax[0].body.param]),
            JSON.stringify(['output_Postgis', 'db-option']));
        w.__ajax[0].respond({ options: PG, needs: null, error: false });
        const form = w.$('.pl-assistant__guided');
        const submit = form.find('.btn-pl-add');
        assert.strictEqual(submit.prop('disabled'), true);
        form.find('.js-file-picker').trigger('click');
        w.filemanagerCallback('a.csv', 'a.csv');
        assert.strictEqual(submit.prop('disabled'), true);
        form.find('select').val('gis').trigger('change');
        assert.strictEqual(submit.prop('disabled'), false);
        submit.trigger('click');
        assert.strictEqual(w.__ajax[1].body.message,
            'Load the CSV file a.csv (file:///fm/a.csv) into a new table of the data store gis.');
        assert.strictEqual(w.$('.pl-assistant__guided').length, 0);
    });

    await test('arranque guiado: sin conexiones se puede preguntar igualmente, y Cancelar cierra', async () => {
        const w = makeEnv({ empty: true, guided: true });
        await tick();
        example(w).trigger('click');
        w.__ajax[0].respond({ options: [], needs: null, error: false });
        assert.ok(/no PostGIS connections/.test(w.$('.pl-assistant__guided > .pl-assistant__issue-note').text()));
        assert.strictEqual(w.$('.js-guided-fallback').length, 1);
        w.$('.js-guided-fallback').trigger('click');
        assert.strictEqual(w.__ajax[1].body.message, 'Carga un CSV');
        const other = makeEnv({ empty: true, guided: true });
        await tick();
        example(other).trigger('click');
        other.$('.pl-assistant__guided .btn-default').last().trigger('click');
        assert.strictEqual(other.$('.pl-assistant__guided').length, 0);
    });

    await test('Elegir en un problema de fichero abre el administrador, sin pedir opciones', async () => {
        const w = await pickerEnv({ issues: [Object.assign({}, PICK, { param: 'csv-file',
            pick: { type: 'input_Csv', file_picker: { extensions: 'csv,txt' } } })] });
        w.$('.js-pick').trigger('click');
        assert.strictEqual(w.__ajax.length, 1);
        assert.strictEqual(w.__opened.length, 1);
        w.filemanagerCallback('a.csv', 'a.csv');
        assert.strictEqual(w.eval('jsonParams[0].parameters[0]["csv-file"]'), 'file:///fm/a.csv');
        assert.ok(w.$('.pl-assistant__issue').hasClass('is-resolved'));
    });

    await test('suposición sobre un fichero: se cambia en el administrador y se puede deshacer', async () => {
        const w = await alternativesEnv({ assumption_choices: [{ text: 'n1: conexión gis', node: 'n1', param: 'csv-file',
            value: 'file:///fm/a.csv', options: [], file_picker: { extensions: 'csv,txt' } }] });
        assert.strictEqual(w.$('.pl-assistant__alternative select').length, 0);
        w.$('.pl-assistant__alternative .js-file-picker').trigger('click');
        w.filemanagerCallback('b.csv', 'b.csv');
        assert.strictEqual(w.eval('jsonParams[0].parameters[0]["csv-file"]'), 'file:///fm/b.csv');
        assert.strictEqual(w.$('.pl-assistant__alternative .pl-assistant__file-name').text(), 'b.csv');
        w.$('.pl-assistant__alternative-undo').trigger('click');
        assert.strictEqual(w.eval('jsonParams[0].parameters[0]["csv-file"]'), 'file:///fm/a.csv');
    });

    console.log('Almacenes (datastores) como destino');

    const STORES = [{ value: 'connection=gis; schema=carto', label: 'Cartografía · ws', params: { 'db-option': 'gis', 'schema-name-option': 'carto' } }];
    const NEW_STORE = { value: 'connection=gis; schema=nuevo', label: 'Nuevo · ws', params: { 'db-option': 'gis', 'schema-name-option': 'nuevo' } };

    async function storeEnv(options) {
        const w = makeEnv({ id: '7' });
        await tick();
        w.$('#etl-assistant-input').val('crea la tabla');
        w.$('#etl-assistant-form').trigger('submit');
        w.__ajax[0].respond(JSON.parse(JSON.stringify(reply({ reply: 'Una duda.', questions: [
            { id: 'q1', label: 'Destino', text: '¿Dónde creo la tabla?', multiple: false, source: 'datastores',
                options, create_datastore: true }] }))));
        return w;
    }

    await test('pregunta de destino: almacenes sin Otro, y la respuesta lleva conexión y esquema', async () => {
        const w = await storeEnv(STORES);
        assert.strictEqual(w.$('.pl-assistant__question .js-other').length, 0);
        w.$('.pl-assistant__question input[type=radio]').eq(0).prop('checked', true).trigger('change');
        w.$('.pl-assistant__questions .btn-pl-add').trigger('click');
        assert.strictEqual(w.__ajax[1].body.message, 'Destino: Cartografía · ws (connection=gis; schema=carto)');
    });

    await test('crear un almacén: abre el formulario y al guardar deja marcado el nuevo', async () => {
        const w = await storeEnv(STORES);
        w.$('.js-create-datastore').trigger('click');
        assert.strictEqual(w.__opened[0], '/gvsigonline/services/datastore_add/');
        w.__popup.location = { pathname: '/gvsigonline/services/datastore_list/' };
        await tick(600);
        assert.strictEqual(w.__popup.closed, true);                            // se cierra sola al guardar
        assert.strictEqual(JSON.stringify([w.__ajax[1].body.type, w.__ajax[1].body.param]),
            JSON.stringify(['output_Postgis', 'db-option']));
        w.__ajax[1].respond({ options: STORES.concat([NEW_STORE]), needs: null, error: false, create_datastore: true });
        const radios = w.$('.pl-assistant__question input[type=radio]');
        assert.strictEqual(radios.length, 2);
        assert.strictEqual(radios.eq(1).prop('checked'), true);
        assert.strictEqual(w.$('.pl-assistant__questions .btn-pl-add').prop('disabled'), false);
        const saved = JSON.parse(w.sessionStorage.getItem('etl-assistant-chat:7'));
        assert.strictEqual(saved.messages[1].questions[0].options.length, 2);
    });

    await test('Elegir en la salida: el almacén rellena conexión y esquema, y Deshacer quita los dos', async () => {
        const w = await pickerEnv({ issues: [Object.assign({}, PICK, { param: 'db-option', pick: { type: 'output_Postgis' } })] });
        w.eval('jsonParams[0].parameters = [{tablename: "t"}]');
        w.$('.js-pick').trigger('click');
        w.__ajax[1].respond({ options: STORES, needs: null, error: false, create_datastore: true });
        assert.strictEqual(w.$('.pl-assistant__picker .js-create-datastore').length, 1);
        w.$('.pl-assistant__picker select').val(STORES[0].value).trigger('change');
        assert.strictEqual(w.eval('JSON.stringify(jsonParams[0].parameters[0])'),
            JSON.stringify({ tablename: 't', 'db-option': 'gis', 'schema-name-option': 'carto' }));
        let saved = JSON.parse(w.sessionStorage.getItem('etl-assistant-chat:7'));
        assert.strictEqual(saved.messages[1].changes.length, 2);
        w.$('.pl-assistant__issue-resolved button').trigger('click');
        assert.strictEqual(w.eval('JSON.stringify(jsonParams[0].parameters[0])'), JSON.stringify({ tablename: 't' }));
        saved = JSON.parse(w.sessionStorage.getItem('etl-assistant-chat:7'));
        assert.strictEqual(saved.messages[1].changes.length, 0);
    });

    await test('Elegir el almacén deja el esquema en la lista del desplegable', async () => {
        const w = await pickerEnv({ issues: [Object.assign({}, PICK, { param: 'db-option', pick: { type: 'output_Postgis' } })] });
        w.eval('jsonParams[0].parameters = [{tablename: "t"}]');
        w.__figures[0].NAME = 'output_Postgis';
        w.$('.js-pick').trigger('click');
        w.__ajax[1].respond({ options: STORES, needs: null, error: false, create_datastore: true });
        w.$('.pl-assistant__picker select').val(STORES[0].value).trigger('change');
        assert.strictEqual(w.eval('JSON.stringify(jsonParams[0].parameters[0]["get_schema-name-option"])'), JSON.stringify(['carto']));
    });

    await test('arranque guiado sin almacenes: se puede crear uno', async () => {
        const w = makeEnv({ empty: true, guided: true });
        await tick();
        example(w).trigger('click');
        w.__ajax[0].respond({ options: [], needs: null, error: false, create_datastore: true });
        assert.strictEqual(w.$('.pl-assistant__guided .js-create-datastore').length, 1);
        assert.strictEqual(w.$('.js-guided-fallback').length, 0);
        w.$('.js-create-datastore').trigger('click');
        w.__popup.closed = true;
        await tick(600);
        w.__ajax[1].respond({ options: STORES, needs: null, error: false, create_datastore: true });
        assert.strictEqual(w.$('.pl-assistant__guided select option').length, 2);
    });

    console.log('Columnas de las entradas (ETL_ASSISTANT_COLUMNS)');

    async function columnsEnv(columns) {
        const w = makeEnv({ id: '7', columns });
        await tick();
        w.eval('jsonParams[0].parameters = [{db: "gis"}]; jsonParams[0].schema = []');
        w.$('#etl-assistant-input').val('carga');
        w.$('#etl-assistant-form').trigger('submit');
        w.__ajax[0].respond(JSON.parse(JSON.stringify(reply({ reply: 'Hecho.', assumptions: ['n1: fichero'], assumption_choices: [
            { text: 'n1: fichero', node: 'n1', param: 'csv-file', value: 'file:///fm/a.csv', options: [], file_picker: { extensions: 'csv' } }] }))));
        w.$('.pl-assistant__alternative .js-file-picker').trigger('click');
        w.filemanagerCallback('b.csv', 'b.csv');
        return w;
    }

    await test('al cambiar el origen se leen las columnas y pasan al siguiente nodo', async () => {
        const w = await columnsEnv(true);
        const read = w.__ajax[1];
        assert.strictEqual(read.opts.url, '/gvsigonline/etl/etl_assistant/columns/');
        assert.strictEqual(read.body.type, 'input_Postgis');
        assert.strictEqual(read.body.parameters['csv-file'], 'file:///fm/b.csv');
        read.respond({ schema: ['id_zona', 'nombre'], params: { separator: ';' }, sheets: null, error: null });
        assert.strictEqual(w.eval('JSON.stringify(jsonParams[0].schema)'), JSON.stringify(['id_zona', 'nombre']));
        assert.strictEqual(w.eval('jsonParams[0].parameters[0].separator'), ';');
        assert.strictEqual(w.__propagated[0], 'uuid-1');
    });

    await test('si no se pueden leer: rueda roja y aviso en el chat', async () => {
        const w = await columnsEnv(true);
        w.__ajax[1].respond({ schema: null, params: {}, sheets: null, error: 'No se han podido leer las columnas.' });
        assert.strictEqual(JSON.stringify(w.__gears.pop()), JSON.stringify(['uuid-1', false]));
        assert.ok(/could not be read/.test(w.$('.pl-assistant__bubble--error').text()));
    });

    await test('sin el interruptor no se piden columnas', async () => {
        const w = await columnsEnv(false);
        assert.strictEqual(w.__ajax.length, 1);
    });

    await test('stream cortado sin resultado: error y se puede reintentar', async () => {
        const w = makeEnv({ id: '7', streaming: true });
        await tick();
        w.$('#etl-assistant-input').val('hola');
        w.$('#etl-assistant-form').trigger('submit');
        const req = w.__fetch[0];
        req.push(sse({ type: 'start', query_id: req.body.query_id }));
        req.end();
        await tick();
        assert.ok(/could not be reached/.test(w.$('.pl-assistant__bubble--error').text()));
        assert.ok(!w.$('#etl-assistant-send').hasClass('is-stop'));
    });

    console.log('\n' + passed + ' correctos, ' + failed + ' fallidos');
    process.exit(failed ? 1 : 0);
})();
