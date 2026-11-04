// Harness: carga el JS REAL del editor (TableShape.js hasta INPUTS, NodeHeader.js, SchemaPropagator.js, PredictiveShapes.js)
// en jsdom con jQuery real. Solo draw2d y el backend están simulados.
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const JS = path.join(__dirname, '..', '..', 'static', 'js');
const jquerySrc = fs.readFileSync(require.resolve('jquery/dist/jquery.js'), 'utf8');

function makeEnv() {
    const dom = new JSDOM('<!doctype html><body><div id="canvas-parent"></div></body>', {
        runScripts: 'outside-only', url: 'https://localhost/gvsigonline/etl/'
    });
    const w = dom.window;
    w.eval(jquerySrc);

    // ---- draw2d simulado (lo mínimo que usa la fábrica) ----
    let counter = 0;
    const uid = () => 'id' + (++counter);
    w.eval(`
    window.__ids = 0;
    function Port(kind){ this.kind = kind; this.id = 'p' + (++window.__ids); }
    Port.prototype.setName = function(n){ this.name = n; };
    Port.prototype.getName = function(){ return this.name; };
    Port.prototype.setBackgroundColor = function(c){ this.bg = c; };
    function Label(attr){ this.attr = attr; this.id = 'l' + (++window.__ids); this.text = attr.text; this.kids = []; }
    Label.prototype.createPort = function(kind){ this.port = new Port(kind); return this.port; };
    Label.prototype.add = function(f){ this.kids.push(f); };
    Label.prototype.getText = function(){ return this.text; };
    Label.prototype.setText = function(t){ this.text = t; };
    function Gear(attr){ this.handlers = {}; this.color = attr.color; }
    Gear.prototype.on = function(ev, fn){ this.handlers[ev] = fn; };
    Gear.prototype.setColor = function(c){ this.color = c; };
    function InputPort(){}  InputPort.prototype.createCommand = function(){ return 'cmd-in'; };
    function OutputPort(){} OutputPort.prototype.createCommand = function(){ return 'cmd-out'; };
    function Base(attr){ this.id = 'fig' + (++window.__ids); this.children = []; }
    Base.prototype._super = function(){};
    Base.prototype.add = function(l){ this.children.push(l); };
    Base.prototype.getRadius = function(){ return 3; };
    window.draw2d = {
        shape: { layout: { VerticalLayout: { extend: function(def){
                    function Cls(attr){ Base.call(this, attr); this.cssClass = def.NAME; this.canvas = { stub: true }; def.init.call(this, attr); }
                    Cls.prototype = Object.create(Base.prototype);
                    Object.keys(def).forEach(function(k){ Cls.prototype[k] = def[k]; });
                    return Cls; } } },
                 basic: { Label: Label }, icon: { Gear: Gear } },
        layout: { locator: { XYRelPortLocator: function(){} } },
        ui: { LabelInplaceEditor: function(){} },
        command: { CommandType: { CONNECT: 'CONNECT' } },
        InputPort: InputPort, OutputPort: OutputPort
    };
    `);

    // ---- globales del entorno del editor ----
    w.$.fn.modal = function (cmd) { this.each(function () { this.dataset.modal = cmd; }); return this; };
    w.open = () => null;
    w.gettext = (s) => s;
    w.fm_directory = '/opt/gvsigol_data/data/';
    w.messageBox = { calls: [], show(level, msg) { this.calls.push([level, msg]); } };
    w.Cookies = { get: () => 'csrf' };
    w.editablerestrictedly = false;

    // Código REAL: cabecera de TableShape.js (jsonParams, listLabel, getPerAttr, isAlreadyInCanvas, ...)
    const tableSrc = fs.readFileSync(path.join(JS, 'TableShape.js'), 'utf8');
    const table = tableSrc.slice(0, tableSrc.indexOf('////  INPUTS'));
    w.eval(table);
    // Código REAL: id y cabecera de los nodos (sin draw2d.Canvas no envuelve nada)
    w.eval(fs.readFileSync(path.join(JS, 'NodeHeader.js'), 'utf8'));
    // Código REAL: propagador de esquemas
    w.eval(fs.readFileSync(path.join(JS, 'SchemaPropagator.js'), 'utf8'));

    // Dobles de las funciones que dependen del canvas draw2d
    w.__edges = [];          // [id, schema] publicados a las aristas
    w.__propagated = [];
    w.__inputs = {};         // id -> esquema que "llega" al nodo
    w.passSchemaWhenInputTask = (canvas, ll, id) => (w.__inputs[id] !== undefined ? w.__inputs[id] : []);
    w.passSchemaToEdgeConnected = (id, ll, schema) => { w.__edges.push([id, JSON.parse(JSON.stringify(schema))]); };
    w.propagateSchemaFrom = (id) => { w.__propagated.push(id); };

    // Backend simulado
    w.__ajax = [];
    w.$.ajax = function (opts) {
        const d = w.$.Deferred();
        w.__ajax.push(opts);
        setTimeout(() => (w.__ajaxHandler || (() => d.reject({ responseText: '{}' })))(opts, d), 0);
        return d.promise();
    };
    w.$.getJSON = function (url) {
        const d = w.$.Deferred();
        w.__ajax.push({ url });
        setTimeout(() => d.resolve(w.__targets), 0);
        return d.promise();
    };

    // Código REAL: fábrica y nodos
    w.eval(fs.readFileSync(path.join(JS, 'PredictiveShapes.js'), 'utf8'));
    return w;
}

const tick = (ms = 5) => new Promise((r) => setTimeout(r, ms));
module.exports = { makeEnv, tick };
