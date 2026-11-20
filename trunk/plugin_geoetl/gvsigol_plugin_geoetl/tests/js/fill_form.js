// Relleno del formulario de un nodo: carga el DrawNodes.js REAL en jsdom con jQuery real.
//   NODE_PATH=/tmp/etl-js/node_modules node fill_form.js
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

let passed = 0, failed = 0;
function test(name, fn) {
    try { fn(); passed++; console.log('  ok   ' + name); }
    catch (e) { failed++; console.log('  FAIL ' + name + '\n       ' + (e.stack || e).split('\n').slice(0, 4).join('\n       ')); }
}

function makeEnv() {
    const dom = new JSDOM('<!doctype html><body>' +
        '<select id="schema-name-option-1"></select><select id="tablename-1"></select>' +
        '<select id="attr-1" multiple><option>a</option></select><select id="sheet-name-1"></select>' +
        '<input id="titulo-1"></body>', { runScripts: 'outside-only' });
    const w = dom.window;
    w.eval(fs.readFileSync(require.resolve('jquery/dist/jquery.js'), 'utf8'));
    w.eval('var jsonParams = [], listLabel = [], editablerestrictedly = "";');
    w.eval('var draw2d = { command: { Command: { extend: function () { return function () {}; } } } };');
    w.eval(fs.readFileSync(path.join(__dirname, '..', '..', 'static', 'js', 'DrawNodes.js'), 'utf8'));
    return w;
}
const fill = (w, params, schemaold) => w.fillEtlNodeForm('output_Postgis', { id: '1' }, [params], schemaold);

console.log('Relleno del formulario');

test('un valor sin opción en el desplegable se añade y queda seleccionado', () => {
    const w = makeEnv();
    fill(w, { 'schema-name-option': 'ds_jrodrigo', tablename: 'cruce_zonas' });
    assert.strictEqual(w.$('#schema-name-option-1').val(), 'ds_jrodrigo');
    assert.strictEqual(w.$('#tablename-1').val(), 'cruce_zonas');
});

test('selección múltiple', () => {
    const w = makeEnv();
    fill(w, { attr: ['a', 'b'] });
    assert.strictEqual(JSON.stringify(Array.from(w.$('#attr-1').val())), JSON.stringify(['a', 'b']));
});

test('rellenar dos veces no duplica opciones', () => {
    const w = makeEnv();
    const params = { 'get_sheet-name': ['Datos', 'Otra'], 'sheet-name': 'Datos' };
    fill(w, params);
    fill(w, params);
    assert.strictEqual(w.$('#sheet-name-1 option').length, 2);
    assert.strictEqual(w.$('#sheet-name-1').val(), 'Datos');
});

test('un valor con caracteres especiales no se interpreta como HTML', () => {
    const w = makeEnv();
    fill(w, { tablename: '<img src=x onerror=alert(1)>' });
    assert.strictEqual(w.$('#tablename-1 img').length, 0);
    assert.strictEqual(w.$('#tablename-1').val(), '<img src=x onerror=alert(1)>');
});

test('los campos de texto siguen igual', () => {
    const w = makeEnv();
    fill(w, { titulo: 'hola' });
    assert.strictEqual(w.$('#titulo-1').val(), 'hola');
});

console.log('\n' + passed + ' correctos, ' + failed + ' fallidos');
process.exit(failed ? 1 : 0);
