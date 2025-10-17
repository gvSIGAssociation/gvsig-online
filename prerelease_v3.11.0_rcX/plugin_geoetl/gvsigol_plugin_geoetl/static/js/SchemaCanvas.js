$('[data-toggle-second="tooltip"]').tooltip();

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

    for(i=0;i<listLabel.length;i++){
        if(listLabel[i][0]==id){
            var sourceports =listLabel[i][1]
            break;
        }
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
                                for (k=0; k<canvas[i]['userData']['0'].length;k++){
                                    if(schemaPort.includes(canvas[i]['userData']['0'][k])==false){
                                        schemaPort.push(canvas[i]['userData']['0'][k])
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

    for(i=0;i<listLabel.length;i++){
        if(listLabel[i][0]==id){
            var targetports =listLabel[i][2]
            break;
        }
    };

    var writer = new draw2d.io.json.Writer();
    try{
        writer.marshal(canvasCtxt, function(canvas){
        
            for(j=0;j<targetports.length;j++){
                
                for(i=0; i<canvas.length;i++){
                    if(canvas[i]!=null){
                        if (canvas[i]['type']=='draw2d.Connection'){
                            
                            if(canvas[i]['source']['port']==targetports[j]){
                                
                                edge = canvasCtxt.getLine(canvas[i]['id'])

                                delete edge['userData']
                                
                                if (Array.isArray(schema[j])){
                                    edge['userData'] = [schema[j]]
                                }else{
                                    edge['userData'] = [schema]
                                };
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

            }, 100);

            return connection;
        }
    }
    ));

    app.view.installEditPolicy(new draw2d.policy.canvas.ShowGridEditPolicy());

});


