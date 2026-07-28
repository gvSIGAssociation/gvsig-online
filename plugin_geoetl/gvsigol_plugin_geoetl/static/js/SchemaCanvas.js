$('[data-toggle-second="tooltip"]').tooltip();

/** Resolve listLabel entry for a node id (last match wins — avoids stale ports after reload). */
function getListLabelEntry(listLabel, id) {
    var found = null;
    if (!listLabel) {
        return null;
    }
    for (var i = 0; i < listLabel.length; i++) {
        if (listLabel[i] && listLabel[i][0] == id) {
            found = listLabel[i];
        }
    }
    return found;
}

/** Read live input/output port names from a draw2d figure as fallback. */
function getFigurePortNames(canvasCtxt, id) {
    var inputs = [];
    var outputs = [];
    try {
        var fig = canvasCtxt.getFigure(id);
        if (!fig || !fig.getPorts) {
            return null;
        }
        fig.getPorts().each(function (idx, port) {
            var name = port.getName ? port.getName() : port.name;
            if (!name) {
                return;
            }
            if (String(name).indexOf('input') === 0) {
                inputs.push(name);
            } else if (String(name).indexOf('output') === 0) {
                outputs.push(name);
            }
        });
    } catch (err) {
        return null;
    }
    return [inputs, outputs];
}

//get schema from previous task of input edge
function passSchemaWhenInputEdge(canvas, sourceport){

    for (i=0;i<canvas.length;i++){
        try{
            if (canvas[i]['type']!='draw2d.Connection'){
                multiOut = 0
                for(j=0;j<canvas[i]['ports'].length;j++){
                    
                    if(canvas[i]['ports'][j]['name'].startsWith('output')){
                        multiOut = multiOut + 1
                    };
                    
                    if(canvas[i]['ports'][j]['name']==sourceport){
                        var schema = [...canvas[i]['entities'][0]['schema']];
                        if (Array.isArray(schema[multiOut-1])){
                            return schema[multiOut-1]
                        }else{
                            return schema
                        };
                    };
                };
            };
        }catch(error){

        }
    }
};

//get schema from previous edge of input task
function passSchemaWhenInputTask(canvasCtxt, listLabel, id){

    var schema = []
    var sourceports = null

    var entry = getListLabelEntry(listLabel, id);
    if (entry) {
        sourceports = entry[1];
    }
    if (!sourceports || !sourceports.length) {
        var live = getFigurePortNames(canvasCtxt, id);
        if (live) {
            sourceports = live[0];
        }
    }
    if (!sourceports) {
        sourceports = [];
    }
            
    var writer = new draw2d.io.json.Writer();
    writer.marshal(canvasCtxt, function(canvas){

        for(j=0;j<sourceports.length;j++){
            schemaPort =[]
            for (i=0;i<canvas.length;i++){
                try{ 
                    if(canvas[i]!=null){
                        if (canvas[i]['type']=='draw2d.Connection'){
                            if(canvas[i]['target']['port']==sourceports[j]){
                                var ud = canvas[i]['userData'];
                                var cols = null;
                                if (ud != null) {
                                    if (Array.isArray(ud) && ud.length) {
                                        cols = ud[0];
                                    } else if (ud['0'] !== undefined) {
                                        cols = ud['0'];
                                    }
                                }
                                if (Array.isArray(cols)) {
                                    for (k=0; k<cols.length;k++){
                                        if(schemaPort.includes(cols[k])==false){
                                            schemaPort.push(cols[k])
                                        }
                                    }
                                }
                            }
                        }
                    }
                }catch(error){
                    //console.log(error)
                }
            }
            schema.push(schemaPort)
        }
    })

    if (schema.length == 1){
        return schema[0]
    }
    else{
        return schema
    }
};

//get schemas of the task if is already on the canvas
function getOwnSchemas(canvasCtxt, id){
           
    var writer = new draw2d.io.json.Writer();
    writer.marshal(canvasCtxt, function(canvas){
        
        for (i=0;i<canvas.length;i++){
            
            if (canvas[i]['id']==id){
                
                schema = canvas[i]['entities'][0]['schema']
                schemaOld = canvas[i]['entities'][0]['schemaold']
                
                break;
            }
        }
    })
    return [schema, schemaOld]
};

//add the schema of the task to later edge if it exists
function passSchemaToEdgeConnected(id, listLabel, schema, canvasCtxt){

    var targetports = null;
    var entry = getListLabelEntry(listLabel, id);
    if (entry) {
        targetports = entry[2];
    }
    if (!targetports || !targetports.length) {
        var live = getFigurePortNames(canvasCtxt, id);
        if (live) {
            targetports = live[1];
        }
    }
    if (!targetports) {
        return;
    }

    var writer = new draw2d.io.json.Writer();
    try{
        writer.marshal(canvasCtxt, function(canvas){
        
            for(j=0;j<targetports.length;j++){
                
                for(i=0; i<canvas.length;i++){
                    if(canvas[i]!=null){
                        if (canvas[i]['type']=='draw2d.Connection'){
                            
                            if(canvas[i]['source']['port']==targetports[j]){
                                
                                edge = canvasCtxt.getLine(canvas[i]['id'])

                                var edgeSchema;
                                if (Array.isArray(schema[j])){
                                    edgeSchema = schema[j];
                                }else{
                                    edgeSchema = schema;
                                }

                                if (edge.setUserData) {
                                    edge.setUserData([edgeSchema]);
                                } else {
                                    edge['userData'] = [edgeSchema];
                                }
                            }
                        }
                    }
                
                }
            }
        });
    }catch(error){
        //console.log(error)
            
    }
    
};


document.addEventListener("DOMContentLoaded",function () {

    var routerToUse = new draw2d.layout.connection.SplineConnectionRouter();
    var app  = new gvsigolETL.Application();

    app.view.installEditPolicy(new draw2d.policy.connection.DragConnectionCreatePolicy({
        createConnection: function(){
            var connection = new draw2d.Connection({
                stroke:1,
                outlineStroke:1,
                outlineColor:"#141517",
                color:"#141517",
                router:routerToUse
            });

            connection.setTargetDecorator(new draw2d.decoration.connection.ArrowDecorator(15, 10).setBackgroundColor("#141517")); 
            
            setTimeout(function()
            {
                var sourcePort = connection.sourcePort.name;

                jsCanvas =[]
                
                var writer = new draw2d.io.json.Writer();
                
                writer.marshal(app.view, function(json){

                    jsCanvas.push(json)
                });

                schemaEdge = passSchemaWhenInputEdge(jsCanvas[0], sourcePort)
                
                connection['userData'] = [schemaEdge]

                // Propagate schema forward from the target node once the connection is attached
                try {
                    var tgtPort = connection.getTarget ? connection.getTarget() : connection.targetPort;
                    if (tgtPort) {
                        var targetFigure = tgtPort.getParent ? tgtPort.getParent() : tgtPort.parent;
                        // Port parent may be the label; walk up to the task figure
                        while (targetFigure && targetFigure.getParent && targetFigure.cssClass &&
                               String(targetFigure.cssClass).indexOf('input_') !== 0 &&
                               String(targetFigure.cssClass).indexOf('trans_') !== 0 &&
                               String(targetFigure.cssClass).indexOf('output_') !== 0 &&
                               String(targetFigure.cssClass).indexOf('crea_') !== 0) {
                            var parentFig = targetFigure.getParent();
                            if (!parentFig || parentFig === targetFigure) {
                                break;
                            }
                            targetFigure = parentFig;
                        }
                        if (targetFigure && targetFigure.id && typeof propagateSchemaFrom === 'function') {
                            propagateSchemaFrom(targetFigure.id, app.view, { skipStart: false });
                        }
                    }
                } catch (propErr) {
                    // ignore propagation errors on connect
                }

            }, 100);

            return connection;
        }
    }
    ));

    app.view.installEditPolicy(new draw2d.policy.canvas.ShowGridEditPolicy());

});


