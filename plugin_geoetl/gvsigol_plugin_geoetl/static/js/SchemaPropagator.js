/**
 * Forward schema propagation for the ETL canvas.
 * Mirrors the DFS topological sort of etl_tasks.Graph and applies
 * per-task schema handlers so column lists reach all downstream nodes.
 */

var SCHEMA_GEAR_RED = '#e2504c';
var SCHEMA_GEAR_COLORS = {
    input: '#01b0a0',
    output: '#e79600',
    trans: '#4682B4',
    crea: '#8e57eb'
};

/** Gear icons keyed by figure id — set from TableShape via registerEtlGearIcon. */
var etlGearById = window._etlGearById || {};
window._etlGearById = etlGearById;

function registerEtlGearIcon(nodeId, icon) {
    if (nodeId && icon) {
        etlGearById[nodeId] = icon;
        window._etlGearById[nodeId] = icon;
    }
}

function setGearColorForNode(nodeId, figure, typeName, ok) {
    var icon = (nodeId && etlGearById[nodeId]) || findGearIcon(figure);
    if (!icon || !icon.setColor) {
        return;
    }
    if (nodeId) {
        registerEtlGearIcon(nodeId, icon);
    }
    icon.setColor(ok ? getConfiguredGearColor(typeName) : SCHEMA_GEAR_RED);
    try {
        if (icon.repaint) {
            icon.repaint();
        }
    } catch (err) { /* ignore */ }
}

function EtlSchemaGraph(vertices) {
    this.graph = {};
    this.V = vertices;
    for (var i = 0; i < vertices; i++) {
        this.graph[i] = [];
    }
}

EtlSchemaGraph.prototype.addEdge = function (u, v) {
    if (u < 0 || v < 0) {
        return;
    }
    this.graph[u].push(v);
};

EtlSchemaGraph.prototype.topologicalSortUtil = function (v, visited, stack) {
    visited[v] = true;
    var adj = this.graph[v] || [];
    for (var i = 0; i < adj.length; i++) {
        if (!visited[adj[i]]) {
            this.topologicalSortUtil(adj[i], visited, stack);
        }
    }
    stack.push(v);
};

EtlSchemaGraph.prototype.topologicalSort = function () {
    var visited = [];
    var stack = [];
    for (var i = 0; i < this.V; i++) {
        visited[i] = false;
    }
    for (var j = 0; j < this.V; j++) {
        if (!visited[j]) {
            this.topologicalSortUtil(j, visited, stack);
        }
    }
    return stack.reverse();
};

function schemaAsColumnList(schema) {
    if (!schema) {
        return [];
    }
    if (Array.isArray(schema) && schema.length && Array.isArray(schema[0])) {
        return schema[0].slice();
    }
    if (Array.isArray(schema)) {
        return schema.slice();
    }
    return [];
}

function attrsExistInSchema(attrs, schema) {
    if (attrs === undefined || attrs === null || attrs === '') {
        return true;
    }
    var cols = schemaAsColumnList(schema);
    var list = Array.isArray(attrs) ? attrs : String(attrs).split(/[\s,]+/).filter(Boolean);
    for (var i = 0; i < list.length; i++) {
        var a = list[i];
        if (!a || a === '-') {
            continue;
        }
        if (cols.indexOf(a) === -1) {
            return false;
        }
    }
    return true;
}

function validateAttrFields(params0, inputSchemas, fields) {
    if (!params0) {
        return false;
    }
    for (var i = 0; i < fields.length; i++) {
        var key = fields[i];
        if (params0[key] !== undefined && params0[key] !== null && params0[key] !== '') {
            if (!attrsExistInSchema(params0[key], inputSchemas)) {
                return false;
            }
        }
    }
    return true;
}

function uniqueConcat(a, b) {
    var chars = (a || []).concat(b || []);
    return chars.filter(function (c, index) {
        return chars.indexOf(c) === index;
    });
}

function getTaskParamsEntry(id) {
    if (typeof jsonParams === 'undefined' || !jsonParams) {
        return null;
    }
    for (var i = 0; i < jsonParams.length; i++) {
        if (jsonParams[i].id === id) {
            return jsonParams[i];
        }
    }
    return null;
}

function getNodeTypeFromCanvas(canvasJson, nodeId) {
    for (var i = 0; i < canvasJson.length; i++) {
        if (canvasJson[i] && canvasJson[i].id === nodeId && canvasJson[i].type !== 'draw2d.Connection') {
            return canvasJson[i].type;
        }
    }
    return null;
}

function getConfiguredGearColor(typeName) {
    if (!typeName) {
        return SCHEMA_GEAR_COLORS.trans;
    }
    if (typeName.indexOf('input') === 0) {
        return SCHEMA_GEAR_COLORS.input;
    }
    if (typeName.indexOf('output') === 0) {
        return SCHEMA_GEAR_COLORS.output;
    }
    if (typeName.indexOf('crea') === 0) {
        return SCHEMA_GEAR_COLORS.crea;
    }
    return SCHEMA_GEAR_COLORS.trans;
}

function findGearIcon(figure) {
    if (!figure) {
        return null;
    }
    if (figure.id && etlGearById[figure.id]) {
        return etlGearById[figure.id];
    }
    var found = null;
    var candidate = null;

    function consider(fig) {
        if (!fig) {
            return;
        }
        var name = fig.NAME || fig.cssClass || '';
        if (String(name).indexOf('Gear') !== -1 || String(name).indexOf('gear') !== -1) {
            found = fig;
            return;
        }
        // draw2d gear icons are ~13px squares with setColor
        if (!candidate && fig.setColor && fig.getWidth && fig.getHeight &&
            fig.getWidth() <= 16 && fig.getHeight() <= 16) {
            candidate = fig;
        }
    }

    function walk(fig, depth) {
        if (!fig || found || depth > 5) {
            return;
        }
        consider(fig);
        if (found) {
            return;
        }
        try {
            if (fig.getChildren) {
                fig.getChildren().each(function (i, e) {
                    if (found) {
                        return;
                    }
                    if (e.figure) {
                        walk(e.figure, depth + 1);
                    }
                });
            }
        } catch (err) { /* ignore */ }
        try {
            if (fig.classLabel) {
                walk(fig.classLabel, depth + 1);
            }
        } catch (err2) { /* ignore */ }
    }

    walk(figure, 0);
    return found || candidate;
}

function sourceHandler() {
    return {
        computeOutputSchema: function (inputSchemas, params) {
            if (params && params.schema !== undefined) {
                return params.schema;
            }
            return [];
        },
        validateParams: function () {
            return true;
        }
    };
}

function passthroughHandler(attrFields, multiOutCount) {
    attrFields = attrFields || [];
    return {
        computeOutputSchema: function (inputSchemas) {
            var cols = schemaAsColumnList(inputSchemas);
            if (multiOutCount && multiOutCount > 1) {
                var outs = [];
                for (var i = 0; i < multiOutCount; i++) {
                    outs.push(cols.slice());
                }
                return outs;
            }
            return cols;
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return true;
            }
            return validateAttrFields(params.parameters[0], inputSchemas, attrFields);
        }
    };
}

function passthroughKeepSchemaHandler(attrFields) {
    // Like Filter/ModifyValue/Calculator: output equals current input schema
    attrFields = attrFields || [];
    return {
        computeOutputSchema: function (inputSchemas) {
            return schemaAsColumnList(inputSchemas);
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return true;
            }
            return validateAttrFields(params.parameters[0], inputSchemas, attrFields);
        }
    };
}

function outputSinkHandler(attrFields) {
    attrFields = attrFields || [];
    return {
        computeOutputSchema: function (inputSchemas) {
            return schemaAsColumnList(inputSchemas);
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return true;
            }
            return validateAttrFields(params.parameters[0], inputSchemas, attrFields);
        }
    };
}

function opaqueKeepOutputHandler(attrFields) {
    attrFields = attrFields || [];
    return {
        computeOutputSchema: function (inputSchemas, params) {
            if (params && params.schema !== undefined) {
                return params.schema;
            }
            return schemaAsColumnList(inputSchemas);
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return false;
            }
            return validateAttrFields(params.parameters[0], inputSchemas, attrFields);
        }
    };
}

var SCHEMA_HANDLERS = {};

(function registerSchemaHandlers() {
    var inputs = [
        'input_Indenova', 'input_Segex', 'input_Csv', 'input_Json', 'input_PadronAlbacete',
        'input_PadronAtm', 'input_Excel', 'input_Sharepoint', 'input_Xml', 'input_Shp',
        'input_Oracle', 'input_SqlServer', 'input_Postgis', 'input_Kml', 'crea_Grid'
    ];
    for (var i = 0; i < inputs.length; i++) {
        SCHEMA_HANDLERS[inputs[i]] = sourceHandler();
    }

    SCHEMA_HANDLERS.trans_RemoveAttr = {
        computeOutputSchema: function (inputSchemas, params) {
            var schemaMod = schemaAsColumnList(inputSchemas);
            var attrs = params && params.parameters && params.parameters[0] ? params.parameters[0].attr : null;
            if (!attrs) {
                return schemaMod;
            }
            var list = Array.isArray(attrs) ? attrs : [attrs];
            for (var oa = 0; oa < list.length; oa++) {
                var idx = schemaMod.indexOf(list[oa]);
                if (idx !== -1) {
                    schemaMod.splice(idx, 1);
                }
            }
            return schemaMod;
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return false;
            }
            return attrsExistInSchema(params.parameters[0].attr, inputSchemas);
        }
    };

    SCHEMA_HANDLERS.trans_KeepAttr = {
        computeOutputSchema: function (inputSchemas, params) {
            var attrs = params && params.parameters && params.parameters[0] ? params.parameters[0].attr : null;
            if (!attrs) {
                return [];
            }
            return Array.isArray(attrs) ? attrs.slice() : [attrs];
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return false;
            }
            return attrsExistInSchema(params.parameters[0].attr, inputSchemas);
        }
    };

    SCHEMA_HANDLERS.trans_RenameAttr = {
        computeOutputSchema: function (inputSchemas, params) {
            var schemaMod = schemaAsColumnList(inputSchemas);
            var p = params && params.parameters && params.parameters[0] ? params.parameters[0] : {};
            var oldAttrs = p['old-attr'];
            var newAttrStr = p['new-attr'];
            if (!oldAttrs || newAttrStr === undefined || newAttrStr === null) {
                return schemaMod;
            }
            var oldList = Array.isArray(oldAttrs) ? oldAttrs : [oldAttrs];
            var newList = String(newAttrStr).split(' ');
            for (var oa = 0; oa < oldList.length; oa++) {
                var oldAttr = oldList[oa];
                var newAttr = newList[oa] !== undefined ? newList[oa] : newList[0];
                var idx = schemaMod.indexOf(oldAttr);
                if (idx !== -1 && newAttr) {
                    schemaMod.splice(idx, 1, newAttr);
                }
            }
            return schemaMod;
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return false;
            }
            var oldAttrs = params.parameters[0]['old-attr'];
            if (oldAttrs === undefined || oldAttrs === null || oldAttrs === '' ||
                (Array.isArray(oldAttrs) && oldAttrs.length === 0)) {
                return false;
            }
            return attrsExistInSchema(oldAttrs, inputSchemas);
        }
    };

    SCHEMA_HANDLERS.trans_ConcatAttr = {
        computeOutputSchema: function (inputSchemas, params) {
            var schemaMod = schemaAsColumnList(inputSchemas);
            var p = params && params.parameters && params.parameters[0] ? params.parameters[0] : {};
            if (p['new-attr']) {
                schemaMod.push(p['new-attr']);
            }
            return schemaMod;
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return false;
            }
            return attrsExistInSchema(params.parameters[0].attr, inputSchemas);
        }
    };

    SCHEMA_HANDLERS.trans_PadAttr = {
        computeOutputSchema: function (inputSchemas, params) {
            var schemaMod = schemaAsColumnList(inputSchemas);
            var p = params && params.parameters && params.parameters[0] ? params.parameters[0] : {};
            if (p.attr) {
                var idx = schemaMod.indexOf(p.attr);
                if (idx !== -1) {
                    schemaMod.splice(idx, 1);
                    schemaMod.push(p.attr);
                }
            }
            return schemaMod;
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return false;
            }
            return attrsExistInSchema(params.parameters[0].attr, inputSchemas);
        }
    };

    SCHEMA_HANDLERS.trans_FilterDupli = passthroughHandler(['attr'], 2);
    SCHEMA_HANDLERS.trans_Filter = passthroughKeepSchemaHandler(['attr']);
    SCHEMA_HANDLERS.trans_ModifyValue = passthroughKeepSchemaHandler(['attr']);
    SCHEMA_HANDLERS.trans_Calculator = passthroughKeepSchemaHandler(['attr']);
    SCHEMA_HANDLERS.trans_Reproject = passthroughHandler([]);
    SCHEMA_HANDLERS.trans_CadastralGeom = passthroughHandler(['attr']);
    SCHEMA_HANDLERS.trans_ExplodeGeom = passthroughHandler([]);
    SCHEMA_HANDLERS.trans_Buffer = passthroughHandler(['radius-attr', 'current-area-attr', 'area-attr-reach']);
    SCHEMA_HANDLERS.trans_RemoveGeom = passthroughHandler([]);

    SCHEMA_HANDLERS.trans_ValGeom = {
        computeOutputSchema: function (inputSchemas) {
            var base = schemaAsColumnList(inputSchemas);
            return [base.concat(['_valid']), base.concat(['_valid', '_reason', '_location'])];
        },
        validateParams: function () {
            return true;
        }
    };

    SCHEMA_HANDLERS.trans_SimpGeom = {
        computeOutputSchema: function (inputSchemas) {
            var base = schemaAsColumnList(inputSchemas);
            return [base.slice(), base.slice()];
        },
        validateParams: function () {
            return true;
        }
    };

    SCHEMA_HANDLERS.trans_Counter = {
        computeOutputSchema: function (inputSchemas, params) {
            var schemaMod = schemaAsColumnList(inputSchemas);
            var p = params && params.parameters && params.parameters[0] ? params.parameters[0] : {};
            if (p.attr) {
                schemaMod.push(p.attr);
            }
            schemaMod.shift();
            return schemaMod;
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return false;
            }
            return validateAttrFields(params.parameters[0], inputSchemas, ['group-by-attr']);
        }
    };

    SCHEMA_HANDLERS.trans_Stats = {
        computeOutputSchema: function (inputSchemas, params) {
            var schemaMod = ['_max', '_min', '_count', '_sum', '_mean', '_median', '_mode', '_desv'];
            var p = params && params.parameters && params.parameters[0] ? params.parameters[0] : {};
            if (p['group-by-attr']) {
                schemaMod = [p['group-by-attr']].concat(schemaMod);
            }
            return schemaMod;
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return false;
            }
            return validateAttrFields(params.parameters[0], inputSchemas, ['attr', 'group-by-attr']);
        }
    };

    SCHEMA_HANDLERS.trans_ChangeAttrType = {
        computeOutputSchema: function (inputSchemas, params) {
            var schemaMod = schemaAsColumnList(inputSchemas);
            var p = params && params.parameters && params.parameters[0] ? params.parameters[0] : {};
            if (p.attr) {
                var idx = schemaMod.indexOf(p.attr);
                if (idx !== -1) {
                    schemaMod.splice(idx, 1);
                    schemaMod.push(p.attr);
                }
            }
            return schemaMod;
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return false;
            }
            return attrsExistInSchema(params.parameters[0].attr, inputSchemas);
        }
    };

    SCHEMA_HANDLERS.trans_CorrectSpelling = {
        computeOutputSchema: function (inputSchemas) {
            var schemaMod = schemaAsColumnList(inputSchemas);
            schemaMod.push('_corrected');
            return schemaMod;
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return false;
            }
            return attrsExistInSchema(params.parameters[0].attr, inputSchemas);
        }
    };

    SCHEMA_HANDLERS.trans_ExecuteSQL = opaqueKeepOutputHandler([]);

    SCHEMA_HANDLERS.trans_CreateAttr = {
        computeOutputSchema: function (inputSchemas, params) {
            var schemaMod = schemaAsColumnList(inputSchemas);
            var p = params && params.parameters && params.parameters[0] ? params.parameters[0] : {};
            if (p.attr) {
                schemaMod.push(p.attr);
            }
            return schemaMod;
        },
        validateParams: function () {
            return true;
        }
    };

    SCHEMA_HANDLERS.trans_ExposeAttr = {
        computeOutputSchema: function (inputSchemas, params) {
            var schemaMod = schemaAsColumnList(inputSchemas);
            var p = params && params.parameters && params.parameters[0] ? params.parameters[0] : {};
            var attrsStr = p.attrs || '';
            var newSchemaAttr = String(attrsStr).split(' ').filter(Boolean);
            for (var i = 0; i < newSchemaAttr.length; i++) {
                if (schemaMod.indexOf(newSchemaAttr[i]) === -1) {
                    schemaMod.push(newSchemaAttr[i]);
                }
            }
            return schemaMod;
        },
        validateParams: function () {
            return true;
        }
    };

    SCHEMA_HANDLERS.trans_Join = {
        computeOutputSchema: function (inputSchemas) {
            if (Array.isArray(inputSchemas) && Array.isArray(inputSchemas[0])) {
                return [uniqueConcat(inputSchemas[0], inputSchemas[1]), inputSchemas[0], inputSchemas[1]];
            }
            return schemaAsColumnList(inputSchemas);
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return false;
            }
            var p = params.parameters[0];
            var ok = true;
            if (Array.isArray(inputSchemas) && Array.isArray(inputSchemas[0])) {
                if (p.attr1 && inputSchemas[0].indexOf(p.attr1) === -1) {
                    ok = false;
                }
                if (p.attr2 && inputSchemas[1] && inputSchemas[1].indexOf(p.attr2) === -1) {
                    ok = false;
                }
                var a1 = (p['attr-1'] || '').split(' ').filter(Boolean);
                var a2 = (p['attr-2'] || '').split(' ').filter(Boolean);
                for (var i = 0; i < a1.length; i++) {
                    if (inputSchemas[0].indexOf(a1[i]) === -1) {
                        ok = false;
                    }
                }
                for (var j = 0; j < a2.length; j++) {
                    if (inputSchemas[1] && inputSchemas[1].indexOf(a2[j]) === -1) {
                        ok = false;
                    }
                }
            }
            return ok;
        }
    };

    SCHEMA_HANDLERS.trans_NearestNeighbor = {
        computeOutputSchema: function (inputSchemas) {
            if (Array.isArray(inputSchemas) && Array.isArray(inputSchemas[0])) {
                return [uniqueConcat(inputSchemas[0], inputSchemas[1]), inputSchemas[0], inputSchemas[1]];
            }
            return schemaAsColumnList(inputSchemas);
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return false;
            }
            if (Array.isArray(inputSchemas) && Array.isArray(inputSchemas[0])) {
                var attr = params.parameters[0].attr;
                if (attr && inputSchemas[0].indexOf(attr) === -1) {
                    return false;
                }
            }
            return true;
        }
    };

    SCHEMA_HANDLERS.trans_CompareRows = {
        computeOutputSchema: function (inputSchemas) {
            if (Array.isArray(inputSchemas) && Array.isArray(inputSchemas[0])) {
                return [inputSchemas[0], inputSchemas[0], inputSchemas[0], inputSchemas[1]];
            }
            return schemaAsColumnList(inputSchemas);
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return false;
            }
            return attrsExistInSchema(params.parameters[0].attr, Array.isArray(inputSchemas[0]) ? inputSchemas[0] : inputSchemas);
        }
    };

    SCHEMA_HANDLERS.trans_Intersection = {
        computeOutputSchema: function (inputSchemas, params) {
            var p = params && params.parameters && params.parameters[0] ? params.parameters[0] : {};
            if (p.merge === 'true' || p.merge === true) {
                if (Array.isArray(inputSchemas) && Array.isArray(inputSchemas[0])) {
                    return uniqueConcat(inputSchemas[0], inputSchemas[1]);
                }
                return schemaAsColumnList(inputSchemas);
            }
            if (Array.isArray(inputSchemas) && Array.isArray(inputSchemas[0])) {
                return inputSchemas[0].slice();
            }
            return schemaAsColumnList(inputSchemas);
        },
        validateParams: function () {
            return true;
        }
    };

    SCHEMA_HANDLERS.trans_SpatialRel = {
        computeOutputSchema: function (inputSchemas) {
            var schemaMod;
            if (Array.isArray(inputSchemas) && Array.isArray(inputSchemas[0])) {
                schemaMod = inputSchemas[0].slice();
            } else {
                schemaMod = schemaAsColumnList(inputSchemas);
            }
            schemaMod.push('_related');
            return schemaMod;
        },
        validateParams: function () {
            return true;
        }
    };

    SCHEMA_HANDLERS.trans_Cluster = {
        computeOutputSchema: function (inputSchemas) {
            var schemaMod = schemaAsColumnList(inputSchemas);
            schemaMod.push('_cluster');
            schemaMod.push('_cluster_rmse');
            schemaMod.push('_distance_to_centroid');
            schemaMod.shift();
            return schemaMod;
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return true;
            }
            return validateAttrFields(params.parameters[0], inputSchemas, ['attr']);
        }
    };

    SCHEMA_HANDLERS.trans_Difference = {
        computeOutputSchema: function (inputSchemas) {
            if (Array.isArray(inputSchemas) && Array.isArray(inputSchemas[0])) {
                return inputSchemas[0].slice();
            }
            return schemaAsColumnList(inputSchemas);
        },
        validateParams: function () {
            return true;
        }
    };

    SCHEMA_HANDLERS.trans_Voronoi = {
        computeOutputSchema: function () {
            return [];
        },
        validateParams: function () {
            return true;
        }
    };

    SCHEMA_HANDLERS.trans_MGRS = {
        computeOutputSchema: function (inputSchemas, params) {
            var schemaMod = schemaAsColumnList(inputSchemas);
            var p = params && params.parameters && params.parameters[0] ? params.parameters[0] : {};
            if (p.select === 'mgrstolatlon') {
                schemaMod.push('_lon', '_lat');
            } else {
                schemaMod.push('_mgrs_grid');
            }
            return schemaMod;
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return false;
            }
            var p = params.parameters[0];
            if (p.select === 'mgrstolatlon') {
                return attrsExistInSchema(p.mgrs, inputSchemas);
            }
            return attrsExistInSchema(p.lon, inputSchemas) && attrsExistInSchema(p.lat, inputSchemas);
        }
    };

    SCHEMA_HANDLERS.trans_TextToPoint = {
        computeOutputSchema: function (inputSchemas) {
            var schemaMod = schemaAsColumnList(inputSchemas);
            schemaMod.push('_xlon');
            schemaMod.push('_ylat');
            return schemaMod;
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return false;
            }
            return validateAttrFields(params.parameters[0], inputSchemas, ['lon', 'lat']);
        }
    };

    SCHEMA_HANDLERS.trans_WktGeom = {
        computeOutputSchema: function (inputSchemas, params) {
            var schemaMod = schemaAsColumnList(inputSchemas);
            var p = params && params.parameters && params.parameters[0] ? params.parameters[0] : {};
            if (p.attr) {
                var idx = schemaMod.indexOf(p.attr);
                if (idx !== -1) {
                    schemaMod.splice(idx, 1);
                }
            }
            return schemaMod;
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return false;
            }
            return attrsExistInSchema(params.parameters[0].attr, inputSchemas);
        }
    };

    SCHEMA_HANDLERS.trans_SplitAttr = {
        computeOutputSchema: function (inputSchemas, params) {
            var schemaMod = schemaAsColumnList(inputSchemas);
            var p = params && params.parameters && params.parameters[0] ? params.parameters[0] : {};
            if (p.attr) {
                var idx = schemaMod.indexOf(p.attr);
                if (idx !== -1) {
                    schemaMod.splice(idx, 1);
                }
            }
            if (p.list) {
                schemaMod.push(p.list);
            }
            return schemaMod;
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return false;
            }
            return attrsExistInSchema(params.parameters[0].attr, inputSchemas);
        }
    };

    SCHEMA_HANDLERS.trans_ExplodeList = {
        computeOutputSchema: function (inputSchemas, params) {
            var schemaMod = schemaAsColumnList(inputSchemas);
            var p = params && params.parameters && params.parameters[0] ? params.parameters[0] : {};
            if (p.list) {
                var idx = schemaMod.indexOf(p.list);
                if (idx !== -1) {
                    schemaMod.splice(idx, 1);
                }
            }
            if (p.attr) {
                schemaMod.push(p.attr);
            }
            return schemaMod;
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return false;
            }
            return attrsExistInSchema(params.parameters[0].list, inputSchemas);
        }
    };

    SCHEMA_HANDLERS.trans_Union = {
        computeOutputSchema: function (inputSchemas, params) {
            var p = params && params.parameters && params.parameters[0] ? params.parameters[0] : {};
            if (!p['group-by-attr'] || p['group-by-attr'] === '-') {
                var schemaMod = schemaAsColumnList(inputSchemas);
                schemaMod.shift();
                return schemaMod;
            }
            return [p['group-by-attr']];
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return false;
            }
            var gba = params.parameters[0]['group-by-attr'];
            if (!gba || gba === '-') {
                return true;
            }
            return attrsExistInSchema(gba, inputSchemas);
        }
    };

    SCHEMA_HANDLERS.trans_FilterGeom = {
        computeOutputSchema: function (inputSchemas) {
            var cols = schemaAsColumnList(inputSchemas);
            return [cols, cols, cols, cols, cols, cols];
        },
        validateParams: function () {
            return true;
        }
    };

    SCHEMA_HANDLERS.trans_LineEndPoints = {
        computeOutputSchema: function (inputSchemas) {
            var schemaMod = schemaAsColumnList(inputSchemas);
            schemaMod.push('_xini', '_yini', '_xend', '_yend');
            return schemaMod;
        },
        validateParams: function () {
            return true;
        }
    };

    SCHEMA_HANDLERS.trans_CalcLength = {
        computeOutputSchema: function (inputSchemas) {
            var schemaMod = schemaAsColumnList(inputSchemas);
            schemaMod.push('_length');
            return schemaMod;
        },
        validateParams: function () {
            return true;
        }
    };

    SCHEMA_HANDLERS.trans_CalcArea = {
        computeOutputSchema: function (inputSchemas, params) {
            var schemaMod = schemaAsColumnList(inputSchemas);
            var p = params && params.parameters && params.parameters[0] ? params.parameters[0] : {};
            if (p.attr) {
                schemaMod.push(p.attr);
            }
            return schemaMod;
        },
        validateParams: function () {
            return true;
        }
    };

    SCHEMA_HANDLERS.trans_CurrentDate = {
        computeOutputSchema: function (inputSchemas, params) {
            var schemaMod = schemaAsColumnList(inputSchemas);
            var p = params && params.parameters && params.parameters[0] ? params.parameters[0] : {};
            if (p.attr) {
                schemaMod.push(p.attr);
            }
            return schemaMod;
        },
        validateParams: function () {
            return true;
        }
    };

    SCHEMA_HANDLERS.trans_Geocoder = {
        computeOutputSchema: function (inputSchemas, params) {
            var schemaMod = schemaAsColumnList(inputSchemas);
            var p = params && params.parameters && params.parameters[0] ? params.parameters[0] : {};
            if (p['mode-option'] === 'direct') {
                schemaMod.push('_X', '_Y');
            } else {
                schemaMod.push('_ADDRESS');
            }
            return schemaMod;
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return false;
            }
            var p = params.parameters[0];
            if (p['mode-option'] === 'direct') {
                return attrsExistInSchema(p['attr-selected'] || p.attr, inputSchemas);
            }
            return validateAttrFields(p, inputSchemas, ['x', 'y']);
        }
    };

    SCHEMA_HANDLERS.trans_IDW = {
        computeOutputSchema: function () {
            return ['id', 'x', 'y', 'interpolated_value'];
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return false;
            }
            return attrsExistInSchema(params.parameters[0]['value-field'], inputSchemas);
        }
    };

    SCHEMA_HANDLERS.trans_Kriging = {
        computeOutputSchema: function () {
            return ['id', 'x', 'y', 'kriging_value', 'kriging_variance'];
        },
        validateParams: function (inputSchemas, params) {
            if (!params || !params.parameters || !params.parameters[0]) {
                return false;
            }
            return attrsExistInSchema(params.parameters[0]['value-field'], inputSchemas);
        }
    };

    SCHEMA_HANDLERS.output_Postgis = outputSinkHandler([]);
    SCHEMA_HANDLERS.output_Visualizer = outputSinkHandler([]);
})();

function buildCanvasGraph(canvasCtxt) {
    var canvasJson = [];
    var writer = new draw2d.io.json.Writer();
    writer.marshal(canvasCtxt, function (json) {
        canvasJson = json;
    });

    var nodes = [];
    var edges = [];
    var idToIndex = {};
    var idToFigure = {};

    for (var i = 0; i < canvasJson.length; i++) {
        var item = canvasJson[i];
        if (!item) {
            continue;
        }
        if (item.type === 'draw2d.Connection') {
            edges.push(item);
        } else {
            idToIndex[item.id] = nodes.length;
            nodes.push(item);
            try {
                idToFigure[item.id] = canvasCtxt.getFigure(item.id);
            } catch (err) {
                idToFigure[item.id] = null;
            }
        }
    }

    var g = new EtlSchemaGraph(nodes.length);
    var adjIds = {};
    for (var n = 0; n < nodes.length; n++) {
        adjIds[nodes[n].id] = [];
    }

    for (var e = 0; e < edges.length; e++) {
        var edge = edges[e];
        var sourceId = edge.source && edge.source.node;
        var targetId = edge.target && edge.target.node;
        var si = idToIndex[sourceId];
        var ti = idToIndex[targetId];
        if (si === undefined || ti === undefined) {
            continue;
        }
        g.addEdge(si, ti);
        adjIds[sourceId].push(targetId);
    }

    var sortedIdx = g.topologicalSort();
    var sortedIds = sortedIdx.map(function (idx) {
        return nodes[idx].id;
    });

    return {
        nodes: nodes,
        edges: edges,
        sortedIds: sortedIds,
        idToFigure: idToFigure,
        idToIndex: idToIndex,
        adjIds: adjIds,
        canvasJson: canvasJson
    };
}

function getReachableForward(startId, adjIds) {
    var reachable = {};
    var queue = [startId];
    reachable[startId] = true;
    while (queue.length) {
        var cur = queue.shift();
        var nexts = adjIds[cur] || [];
        for (var i = 0; i < nexts.length; i++) {
            if (!reachable[nexts[i]]) {
                reachable[nexts[i]] = true;
                queue.push(nexts[i]);
            }
        }
    }
    return reachable;
}

function applySchemaHandler(typeName, inputSchemas, params) {
    var handler = SCHEMA_HANDLERS[typeName];
    if (!handler) {
        // Unknown type: passthrough
        return {
            outputSchema: schemaAsColumnList(inputSchemas),
            schemaOld: inputSchemas,
            ok: !!(params && params.parameters)
        };
    }
    var ok = true;
    try {
        ok = handler.validateParams(inputSchemas, params);
    } catch (err) {
        ok = false;
    }
    var outputSchema;
    try {
        outputSchema = handler.computeOutputSchema(inputSchemas, params);
    } catch (err2) {
        outputSchema = params && params.schema !== undefined ? params.schema : schemaAsColumnList(inputSchemas);
        ok = false;
    }
    return {
        outputSchema: outputSchema,
        schemaOld: inputSchemas,
        ok: !!ok
    };
}

/**
 * Propagate schemas forward from startNodeId along the canvas DAG.
 * @param {string} startNodeId
 * @param {object} canvasCtxt draw2d canvas
 * @param {object} [options]
 * @param {boolean} [options.skipStart=false] If true, do not recompute the start node (already committed on Accept).
 */
function propagateSchemaFrom(startNodeId, canvasCtxt, options) {
    options = options || {};
    var skipStart = !!options.skipStart;
    if (!canvasCtxt || !startNodeId) {
        return;
    }
    if (typeof listLabel === 'undefined') {
        return;
    }

    var graph = buildCanvasGraph(canvasCtxt);
    var reachable = getReachableForward(startNodeId, graph.adjIds);

    for (var s = 0; s < graph.sortedIds.length; s++) {
        var nodeId = graph.sortedIds[s];
        if (!reachable[nodeId]) {
            continue;
        }
        if (skipStart && nodeId === startNodeId) {
            continue;
        }

        var typeName = getNodeTypeFromCanvas(graph.canvasJson, nodeId);
        var params = getTaskParamsEntry(nodeId);
        var figure = graph.idToFigure[nodeId];

        // Sources have no useful upstream; keep stored schema and push to edges
        if (typeName && (typeName.indexOf('input_') === 0 || typeName.indexOf('crea_') === 0)) {
            if (params && params.schema !== undefined) {
                params['schema-old'] = params['schema-old'] || [];
                params._schemaValid = true;
                passSchemaToEdgeConnected(nodeId, listLabel, params.schema, canvasCtxt);
                setGearColorForNode(nodeId, figure, typeName, true);
            }
            continue;
        }

        var inputSchemas = passSchemaWhenInputTask(canvasCtxt, listLabel, nodeId);

        if (!params) {
            // Never configured: leave gear red, do not invent outgoing schema
            setGearColorForNode(nodeId, figure, typeName, false);
            continue;
        }

        var result = applySchemaHandler(typeName, inputSchemas, params);

        params['schema-old'] = result.schemaOld;
        params._schemaValid = result.ok;
        // Opaque handlers (ExecuteSQL): keep previous output if invalid.
        // Others: always publish best-effort output schema from current input.
        var isOpaque = (typeName === 'trans_ExecuteSQL');
        if (result.ok || params.schema === undefined || !isOpaque) {
            params.schema = result.outputSchema;
        }

        passSchemaToEdgeConnected(nodeId, listLabel, params.schema, canvasCtxt);

        setGearColorForNode(nodeId, figure, typeName, result.ok);
    }
}

/**
 * Commit a task's schema after Accept and propagate downstream.
 */
function commitTaskSchema(ID, taskJson, schemaOut, canvasCtxt, icon, configuredColor) {
    if (taskJson) {
        if (schemaOut !== undefined) {
            taskJson.schema = schemaOut;
        }
        isAlreadyInCanvas(jsonParams, taskJson, ID);
    }
    if (schemaOut !== undefined && canvasCtxt) {
        passSchemaToEdgeConnected(ID, listLabel, schemaOut, canvasCtxt);
    }
    if (icon && configuredColor) {
        icon.setColor(configuredColor);
    }
    if (canvasCtxt && typeof propagateSchemaFrom === 'function') {
        propagateSchemaFrom(ID, canvasCtxt, { skipStart: true });
    }
}

/**
 * Refill a select with schema columns while preserving still-valid selections.
 */
function refillSelectPreserving($select, columns, previousSelected) {
    if (!$select || !$select.length) {
        return;
    }
    if (typeof schemaAsColumnList === 'function') {
        columns = schemaAsColumnList(columns);
    } else if (!Array.isArray(columns)) {
        columns = [];
    } else if (columns.length && Array.isArray(columns[0])) {
        columns = columns[0].slice();
    }
    var prev = previousSelected;
    if (prev === undefined) {
        prev = $select.val();
    }
    // Destroy select2 temporarily so option DOM updates apply cleanly
    var hadSelect2 = false;
    try {
        if ($select.data('select2')) {
            hadSelect2 = true;
            $select.select2('destroy');
        }
    } catch (err) { /* ignore */ }

    $select.empty();
    for (var i = 0; i < columns.length; i++) {
        if (columns[i] === undefined || columns[i] === null) {
            continue;
        }
        $select.append($('<option></option>').text(columns[i]).val(columns[i]));
    }
    if (prev !== null && prev !== undefined && prev !== '') {
        if (Array.isArray(prev)) {
            var keep = [];
            for (var j = 0; j < prev.length; j++) {
                if (columns.indexOf(prev[j]) !== -1) {
                    keep.push(prev[j]);
                }
            }
            if (keep.length) {
                $select.val(keep);
            }
        } else if (columns.indexOf(prev) !== -1) {
            $select.val(prev);
        }
    }
    if (hadSelect2) {
        try {
            $select.select2({
                tags: true,
                tokenSeparators: [',', ' '],
                width: '100%'
            });
        } catch (err2) { /* ignore */ }
    }
}

/**
 * Get previously selected attribute values from jsonParams for a node.
 */
function getStoredParamValue(nodeId, paramKey) {
    var entry = getTaskParamsEntry(nodeId);
    if (!entry || !entry.parameters || !entry.parameters[0]) {
        return undefined;
    }
    return entry.parameters[0][paramKey];
}
