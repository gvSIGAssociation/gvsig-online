var jsonParams = []

var formData = new FormData();

var listLabel=[]

function getPerAttr(){
    var memento= this._super();
    
    for (i = 0; i < jsonParams.length; i++) {
        if(this.id == jsonParams[i]["id"]){
            var parametros = jsonParams[i]
            break
        }
    }

    memento.name = this.classLabel.getText();
    memento.entities   = [];
    
    try{
        
        this.children.each(function(i,e){
            
            if(i>0){ // skip the header of the figure
                memento.entities.push({
                    text:e.figure.getText(),
                    id: e.figure.id,
                    parameters: parametros["parameters"],
                    schema: parametros["schema"],
                    schemaold: parametros["schema-old"]
                });
            }
        });

        
        return memento;
    }
    catch{

    }
};

function isAlreadyInCanvas(jsonParams, jsonTask, ID){

    if(jsonParams.length == 0){

        jsonParams.push(jsonTask)

    } else {

        is = false

        for (i = 0; i < jsonParams.length; i++) {

            if(ID == jsonParams[i]["id"]){

                jsonParams[i] = jsonTask
                is = true
                break;

            };
        };

        if(is == false) {

            jsonParams.push(jsonTask)
        };
    };
};

function setColorIfIsOpened(jsonParams, type, ID, icon){
    
    setTimeout(function(){
        
        for(k=0;k<jsonParams.length;k++){
            if (jsonParams[k]['id'] == ID){

                if (type.startsWith('input')){ 
                    icon.setColor('#01b0a0')
                }else if (type.startsWith('output')){ 
                    icon.setColor("#e79600")
                }else if (type.startsWith('trans')){ 
                    icon.setColor("#4682B4")
                }
                break;
            }
        } },1)

};

function getPathFile(fileType, ID){
    $('#select-file-button-'+ID).click(function (e) {
        window.open("/gvsigonline/filemanager/?popup=1","Ratting","width=640, height=480,left=150,top=200,toolbar=0,status=0,scrollbars=1");
    });
    window.filemanagerCallback = function(url) {

        if(fileType == 'csv' && url.endsWith('.csv')){
            $("#"+fileType+"-file-"+ID).val("file://" + fm_directory + url)
        } else if(fileType == 'excel' && (url.endsWith('.xls') || url.endsWith('.xlsx'))){
            $("#"+fileType+"-file-"+ID).val("file://" + fm_directory + url)
        } else if(fileType == 'shp' && url.endsWith('.shp')){
            $("#"+fileType+"-file-"+ID).val("file://" + fm_directory + url)
        } else if(fileType == 'json' && url.endsWith('.json') && ID == '0'){
            $("#etl_json_upload").val("file://" + fm_directory + url)
        } else{
            messageBox.show('warning', gettext('File selected is not a ')+fileType)
        }
    }
};


////////////////////////////////////////////////  INPUTS /////////////////////////////////////////////////////////
//// INPUT INDENOVA ////
input_Indenova = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "input_Indenova",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text:"InDenova",
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#83d0c9", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
       
        var icon = new draw2d.shape.icon.Gear({ 
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-input-indenova-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title">'+gettext('InDenova Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<label class="col-form-label" >'+gettext('Domain:')+'</label>'+
                                '<input type="text" id="domain-'+ID+'" name="file" class="form-control"></input>'+
                            '</div>'+ 
                            '<div>'+
                                '<label class="col-form-label" >'+gettext('API Key:')+'</label>'+
                                '<input type="text" id="api-key-'+ID+'" name="file" class="form-control"></input>'+
                            '</div>'+ 
                            '<div>'+
                                '<label class="col-form-label" >'+gettext('Client ID:')+'</label>'+
                                '<input type="text" id="client-id-'+ID+'" name="file" class="form-control"></input>'+
                            '</div>'+
                            '<div>'+
                                '<label class="col-form-label" >'+gettext('Secret:')+'</label>'+
                                '<input type="text" id="secret-'+ID+'" name="file" class="form-control"></input>'+
                            '</div>'+ 
                            '<div class="column33">'+
                                '<label class="col-form-label" >'+gettext('List urban procedures:')+'</label><br>'+
                                '<a href="#" id="get-proced-'+ID+'" class="btn btn-default btn-sm"><i class="fa fa-download margin-r-5"></i>'+gettext('Get procedures')+'</a>'+
                            '</div>'+
                            '<div class="box-tools column66">'+
                                '<select id="proced-list-'+ID+'" name="proced-list" multiple style="width: 100%; height:200px">'+
                                    '<option value="all">'+gettext('ALL')+'</option>'+
                                '</select>'+
                            '</div><br>'+
                            '<div class="column33">'+
                                '<div class="form-check">'+
                                    '<input type="radio" name="date-indenova-'+ID+'" class="form-check-input" id="check-init-date-'+ID+'" value="check-init-date">'+	
                                    '<label for="init-date">'+gettext('From an initial date')+'</label>'+
                                '</div>'+
                                '<div class="form-check">'+
                                    '<input type="radio" name="date-indenova-'+ID+'" class="form-check-input" id="check-init-end-date-'+ID+'" value="check-init-end-date">'+	
                                    '<label for="init-end-date">'+gettext('Between dates')+'</label>'+
                                '</div>'+
                            '</div>'+
                            '<div class="column33">'+
                                '<div class="input-group date">'+
                                    '<input type="date" class="form-control" id="init-date-'+ID+'" name="init-date" placeHolder="dd/mm/yyyy"/>'+
                                    '<input type="date" class="form-control" id="end-date-'+ID+'" name="end-date" placeHolder="dd/mm/yyyy"/>'+
                                '</div>'+
                            '</div>'+
                            '<div class="column33">'+
                                
                                '<input type="checkbox" name="checkbox-init-indenova" id="checkbox-init-'+ID+'" value=""/>'+
                                '<label for="checkbox">'+gettext('Current date for initial')+'</label>'+
                                '<br><br>'+
                                '<input type="checkbox" name="checkbox-end-indenova" id="checkbox-end-'+ID+'" value=""/>'+
                                '<label for="checkbox">'+gettext('Current date for end')+'</label>'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="input-indenova-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        var context = this

        $('#end-date-'+ID).prop('disabled', true)
        $("#checkbox-"+ID).prop('disabled', true)

        
        $('input:radio[name="date-indenova-'+ID+'"]').change(function(){
            if ($('#check-init-date-'+ID).is(':checked')){
                
                $('#end-date-'+ID).prop('disabled', true)
                $('#end-date-'+ID).val("")
                $("#checkbox-"+ID).prop('disabled', true)
                $("#checkbox-"+ID).prop('checked', false)
                
            }
            else{
                
            
                $('#end-date-'+ID).prop('disabled', false)
                $("#checkbox-"+ID).prop('disabled', false)
            }
        });

        //checkendtoday = false
        $("#checkbox-end-"+ID).click(function() {
            if($("#checkbox-end-"+ID).is(':checked')){
                //checkendtoday = true
                //let today = new Date().toISOString().slice(0, 10)
                $('#end-date-'+ID).val("")
            }//else{                checkendtoday = false            }
        });

        //checkinittoday = false
        $("#checkbox-init-"+ID).click(function() {
            if($("#checkbox-init-"+ID).is(':checked')){
                //checkinittoday = true
                //let today = new Date().toISOString().slice(0, 10)
                $('#init-date-'+ID).val("")
            }//else{                checkinittoday = false            }
        });

        $('#proced-list-'+ID).click(function(){
            if($(this).val()=='all'){
                $('#proced-list-'+ID+' option').prop('selected', true)
            }
        });

        $('#get-proced-'+ID).click(function(){
                
            $(this).hover(function(){
                $(this).css('cursor','wait');
                
            });
            
            var paramsProced = {"id": ID,
            "parameters": [
                {"domain": $('#domain-'+ID).val(),
                "api-key": $('#api-key-'+ID).val()/*,
                "client-id": $('#client-id-'+ID).val(),
                "secret": $('#secret-'+ID).val()*/
                }
            ]};

            var formDataProced = new FormData();

            formDataProced.append('jsonParamsProced', JSON.stringify(paramsProced))

            $.ajax({
                type: 'POST',
                url: '/gvsigonline/etl/etl_proced_indenova/',
                data: formDataProced,
                beforeSend:function(xhr){
                    xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
                },
                cache: false, 
                contentType: false, 
                processData: false,
                success: function (data) {
                    
                    $('#get-proced-'+ID).hover(function(){
                        $(this).css('cursor','pointer');
                    });
                    
                    for(i=0;i<data.length;i++){
                        $('#proced-list-'+ID).append('<option value="'+data[i][0]+'">'+data[i][0]+' - '+data[i][1]+'</option>')
                    };
                },
                error: function(){
                    $('#get-proced-'+ID).hover(function(){
                        $(this).css('cursor','pointer');
                    });
                }
            })
        });
        
        icon.on("click", function(){

            $('#dialog-input-indenova-'+ID).modal('show')

            if ($('#check-init-date-'+ID).is(':checked')){
                
                $('#end-date-'+ID).prop('disabled', true)
                $('#end-date-'+ID).val("")
                $("#checkbox-"+ID).prop('disabled', true)
                $("#checkbox-"+ID).prop('checked', false)
                
            }
            else{
            
                $('#end-date-'+ID).prop('disabled', false)
                $("#checkbox-"+ID).prop('disabled', false)
            }

            $('#input-indenova-accept-'+ID).click(function() {

                if($("#checkbox-init-"+ID).is(':checked')){
                    $("#checkbox-init-"+ID).val("true")
                    
                    //let today = new Date().toISOString().slice(0, 10)
                    
                }else{
                    $("#checkbox-init-"+ID).val("")
                };

                if($("#checkbox-end-"+ID).is(':checked')){
                    $("#checkbox-end-"+ID).val("true")
                    //let today = new Date().toISOString().slice(0, 10)
                    
                }else{
                    $("#checkbox-end-"+ID).val("")
                };

                var paramsIndenova = {"id": ID,
                "parameters": [
                    {
                        "domain": $('#domain-'+ID).val(),
                        "api-key": $('#api-key-'+ID).val(),
                        "client-id": $('#client-id-'+ID).val(),
                        "secret": $('#secret-'+ID).val(),
                        "proced-list": $('#proced-list-'+ID).val(),
                        "init-date": $('#init-date-'+ID).val(),
                        "end-date": $('#end-date-'+ID).val(),
                        "checkbox-end": $("#checkbox-end-"+ID).val(),
                        "checkbox-init": $("#checkbox-init-"+ID).val(),
                        "date-indenova":$('input:radio[name="date-indenova-'+ID+'"]:checked').val()
                    }
                ]};

                var formDataIndenova = new FormData();

                formDataIndenova.append('jsonParamsIndenova', JSON.stringify(paramsIndenova))
                $("#canvas-parent").css('cursor','wait');
                $.ajax({
					type: 'POST',
					url: '/gvsigonline/etl/etl_schema_indenova/',
					data: formDataIndenova,
					beforeSend:function(xhr){
						xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
					},
					cache: false, 
                    contentType: false, 
                    processData: false,
					success: function (data) {
                        paramsIndenova['schema'] = data
                        paramsIndenova['parameters'][0]['schema'] = data
                        
                        passSchemaToEdgeConnected(ID, listLabel, data, context.canvas)
                        
                        isAlreadyInCanvas(jsonParams, paramsIndenova, ID)

                        icon.setColor('#01b0a0')
                        
                        $('#dialog-input-indenova-'+ID).modal('hide')

                        $("#canvas-parent").css('cursor','default');
                        }
                    })
        

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function(optionalIndex)
    {
	   	 var label =new draw2d.shape.basic.Label({
	   	     text:gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:40, top:3, right:10, bottom:5},
	   	     fontColor:"#009688",
             resizeable:true
	   	 });

	     var output= label.createPort("output");
	     
         output.setName("output_"+label.id);
         
	     if($.isNumeric(optionalIndex)){
             this.add(label, null, optionalIndex+1);
	     }
	     else{
	         this.add(label);
	     }
         
         listLabel.push([this.id, [], [output.name]])
         
         return label;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes : getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});



//// INPUT CSV ////
input_Csv = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "input_Csv",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text:"CSV", 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#83d0c9", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
       
        var icon = new draw2d.shape.icon.Gear({ 
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)


        $('#canvas-parent').append('<div id="dialog-input-csv-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title">'+gettext('CSV Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column20">'+
                                '<label class="col-form-label" >'+gettext('Choose csv file:')+'</label><br>'+
                                '<a href="#" id="select-file-button-'+ID+'" class="btn btn-default btn-sm"><i class="fa fa-folder-open margin-r-5"></i>'+gettext('Select file')+'</a>'+
                            '</div>'+ 
                            '<div class="column60">'+
                                '<label class="col-form-label" >'+gettext('Path:')+'</label>'+
                                '<input type="text" id="csv-file-'+ID+'" name="file" class="form-control"></input>'+
                            '</div>'+ 
                            '<div class="column20">'+
                                '<label class="col-form-label">'+gettext('Separator:')+'</label>'+
                                '<select class="form-control" id="separator-'+ID+'">'+
                                    '<option value=";"> ; </option>'+
                                    '<option value=","> , </option>'+
                                '</select>'+
                            '</div>'+ 
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="input-csv-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        getPathFile('csv', ID)

        var context = this

        icon.on("click", function(){

            $('#dialog-input-csv-'+ID).modal('show')

            $('#input-csv-accept-'+ID).click(function() {

                var paramsCSV = {"id": ID,
                "parameters": [
                    {"csv-file": $('#csv-file-'+ID).val(),
                    "separator": $('#separator-'+ID).val()}
                ]}

                var formDataSchemaCSV = new FormData();

                formDataSchemaCSV.append('jsonParamsCSV', JSON.stringify(paramsCSV))

                $.ajax({
					type: 'POST',
					url: '/gvsigonline/etl/etl_schema_csv/',
					data: formDataSchemaCSV,
					beforeSend:function(xhr){
						xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
					},
					cache: false, 
                    contentType: false, 
                    processData: false,
					success: function (data) {
                        paramsCSV['schema'] = data
                        
                        passSchemaToEdgeConnected(ID, listLabel, data, context.canvas)
                        }
                    })
        
                isAlreadyInCanvas(jsonParams, paramsCSV, ID)

                icon.setColor('#01b0a0')
                
                $('#dialog-input-csv-'+ID).modal('hide')
            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function(optionalIndex)
    {
	   	 var label =new draw2d.shape.basic.Label({
	   	     text:gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:40, top:3, right:10, bottom:5},
	   	     fontColor:"#009688",
             resizeable:true
	   	 });

	     var output= label.createPort("output");
	     
         output.setName("output_"+label.id);
         
	     if($.isNumeric(optionalIndex)){
             this.add(label, null, optionalIndex+1);
	     }
	     else{
	         this.add(label);
	     }
         
         listLabel.push([this.id, [], [output.name]])
         
         return label;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes : getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// INPUT EXCEL ////

input_Excel = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "input_Excel",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3, width:1},attr));
        
        this.classLabel = new draw2d.shape.basic.Label({
            text:"Excel", 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#83d0c9", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });

        var icon = new draw2d.shape.icon.Gear({ 
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-input-excel-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title">'+gettext('Excel Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column20">'+
                                '<label for ="excel-file" class="col-form-label">'+gettext('Choose excel file:')+'</label><br>'+
                                '<a href="#" id="select-file-button-'+ID+'" class="btn btn-default btn-sm"><i class="fa fa-folder-open margin-r-5"></i>'+gettext('Select file')+'</a><br>'+
                            '</div>'+
                            '<div class="column80">'+
                                '<label class="col-form-label" >'+gettext('Path:')+'</label>'+
                                '<input type="text" id="excel-file-'+ID+'" name="file" class="form-control"></input>'+
                            '</div>'+
                            '<div class="column20">'+
                                '<label for ="excel-file" class="col-form-label">'+gettext('Load sheets')+':</label><br>'+
                                '<a href="#" id="get-sheets-'+ID+'" class="btn btn-default btn-sm"><i class="fa fa-file-excel-o margin-r-5"></i>'+gettext('Load sheets')+'</a><br>'+
                            '</div>'+
                            '<div class="column80">'+
                                '<label form="sheet-name" class="col-form-label">'+gettext('Sheet:')+'</label>'+
                                '<select class="form-control" id="sheet-name-'+ID+'"> </select>'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label form="usecols" class="col-form-label">'+gettext('Attribute columns:')+'</label>'+
                                '<input id="usecols-'+ID+'" type="text" value="" size="40" class="form-control" pattern="[A-Za-z]{3}" placeholder="A:H">'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label form="header" class="col-form-label">'+gettext('Skip header:')+'</label>'+
                                '<input type="number" id="header-'+ID+'" value=0 min="0" class="form-control" pattern="^[0-9]+">'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="input-excel-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        getPathFile('excel', ID)

        var context = this

        icon.on("click", function(){

            $('#dialog-input-excel-'+ID).modal('show')

            $('#get-sheets-'+ID).on("click", function(){
                                
                var formDataSheetExcel = new FormData();

                formDataSheetExcel.append('file', $('#excel-file-'+ID).val())

                $.ajax({
					type: 'POST',
					url: '/gvsigonline/etl/etl_sheet_excel/',
					data: formDataSheetExcel,
					beforeSend:function(xhr){
						xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
					},
					cache: false, 
                    contentType: false, 
                    processData: false,
					success: function (data) {

                        $('#sheet-name-'+ID).empty()

                        for (i = 0; i < data.length; i++){
                            $('#sheet-name-'+ID).append('<option>'+data[i]+'</option>')

                        }
                    }
                })
            });

            $('#input-excel-accept-'+ID).click(function() {
                
                var paramsExcel = {"id": ID,
                "parameters": [
                    { "excel-file": $('#excel-file-'+ID).val(),
                    "sheet-name": $('#sheet-name-'+ID).val(),
                    "usecols": $('#usecols-'+ID).val(),
                    "header": $('#header-'+ID).val() }
                ]}

                var formDataSchemaExcel = new FormData();
                
                formDataSchemaExcel.append('jsonParamsExcel', JSON.stringify(paramsExcel))

                $.ajax({
					type: 'POST',
					url: '/gvsigonline/etl/etl_schema_excel/',
					data: formDataSchemaExcel,
					beforeSend:function(xhr){
						xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
					},
					cache: false, 
                    contentType: false, 
                    processData: false,
					success: function (data) {
                        paramsExcel['schema'] = data
                        passSchemaToEdgeConnected(ID, listLabel, data, context.canvas)
                        
                        }
                    })
                
                isAlreadyInCanvas(jsonParams, paramsExcel, ID)

                icon.setColor('#01b0a0')

                $('#dialog-input-excel-'+ID).modal('hide')
            })
        })
    },
    
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function(optionalIndex)
    {
	   	 var label =new draw2d.shape.basic.Label({
	   	     text: gettext('Input'),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:40, top:3, right:10, bottom:5},
	   	     fontColor:"#009688",
	   	     resizeable:true
	   	 });

	     var output= label.createPort("output");
         
         output.setName("output_"+label.id);
         
	     if($.isNumeric(optionalIndex)){
             this.add(label, null, optionalIndex+1);
	     }
	     else{
	         this.add(label);
         }
         
         listLabel.push([this.id, [], [output.name]])

         return label;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes : getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }

});

//// INPUT SHAPEFILE ////

input_Shp = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "input_Shp",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text:"Shapefile", 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#83d0c9", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
       
        var icon = new draw2d.shape.icon.Gear({ 
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-input-shp-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title">'+gettext('Shapefile Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column20">'+
                                '<label for ="shp-file" class="col-form-label">'+gettext('Choose shapefile:')+'</label><br>'+
                                '<a href="#" id="select-file-button-'+ID+'" class="btn btn-default btn-sm"><i class="fa fa-folder-open margin-r-5"></i>'+gettext('Select file')+'</a><br>'+
                            '</div>'+
                            '<div class="column80">'+
                                '<label class="col-form-label" >'+gettext('Path:')+'</label>'+
                                '<input type="text" id="shp-file-'+ID+'" name="file" class="form-control"></input>'+
                            '</div>'+
                            '<div class="column20">'+
                                '<label class="col-form-label">Encoding:</label>'+
                                '<select id="encode-'+ID+'" class="form-control">'+ 
                                    '<option value="LATIN1">LATIN1</option>'+
                                    '<option value="UTF-8">UTF-8</option>'+
                                    '<option value="ISO-8859-15">ISO-8859-15</option>'+
                                    '<option value="WINDOWS-1252">WINDOWS-1252</option>'+
                                '</select>'+
                            '</div>'+
                            '<div class="column80">'+
                                '<label class="col-form-label">EPSG:</label>'+
                                '<select id="epsg-'+ID+'" class="form-control">'+ 
                                    '<option value="">'+gettext('Insert if PRJ is not loaded')+'</option>'+
                                '</select>'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="input-shp-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        for(i=0;i<srs.length;i++){

            epsg = srs[i].code.split(":")[1]

            $('#epsg-'+ID).append(
                '<option value="'+epsg+'">'+srs[i].code+' - '+srs[i].title+'</option>'
            );
        }

        getPathFile('shp', ID)

        var context = this

        icon.on("click", function(){

            $('#dialog-input-shp-'+ID).modal('show')

            $('#input-shp-accept-'+ID).click(function() {

                var paramsSHP = {"id": ID,
                "parameters": [
                { "shp-file": $('#shp-file-'+ID).val(),
                  "encode": $('#encode-'+ID).val(),
                  "epsg": $('#epsg-'+ID).val()}
                ]}

                

                var formDataSchemaShape = new FormData();
                formDataSchemaShape.append('file', $('#shp-file-'+ID).val())
                

                /*for (i = 0; i < $('#shp-file-'+ID)[0].files.length; i++) {

                    formData.append(ID+'_'+i, $('#shp-file-'+ID)[0].files[i])
                    formDataSchemaShape.append('file_'+i, $('#shp-file-'+ID)[0].files[i])

                    paramsSHP = paramsSHP+'{"shp-file_'+i+'":"'+$('#shp-file-'+ID)[0].files[i].name+'"},'

                }

                paramsSHP = paramsSHP.slice(0,-1) + ']}'
                
                var jsonParamsSHP = JSON.parse(paramsSHP)*/

                $.ajax({
					type: 'POST',
					url: '/gvsigonline/etl/etl_schema_shape/',
					data: formDataSchemaShape,
					beforeSend:function(xhr){
						xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
					},
					cache: false, 
                    contentType: false, 
                    processData: false,
					success: function (data) {
                        paramsSHP['schema'] = data
                        passSchemaToEdgeConnected(ID, listLabel, data, context.canvas)
                        }
                    })
        
                isAlreadyInCanvas(jsonParams, paramsSHP, ID)

                icon.setColor('#01b0a0')
                
                $('#dialog-input-shp-'+ID).modal('hide')
            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function(optionalIndex)
    {
	   	 var label =new draw2d.shape.basic.Label({
	   	     text:gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:40, top:3, right:10, bottom:5},
	   	     fontColor:"#009688",
             resizeable:true
	   	 });

	     var output= label.createPort("output");
	     
         output.setName("output_"+label.id);
         
	     if($.isNumeric(optionalIndex)){
             this.add(label, null, optionalIndex+1);
	     }
	     else{
	         this.add(label);
	     }
         
         listLabel.push([this.id, [], [output.name]])
         
         return label;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes : getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// INPUT ORACLE ////

input_Oracle = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "input_Oracle",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3, width:1},attr));
        
        this.classLabel = new draw2d.shape.basic.Label({
            text:"Oracle", 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#83d0c9", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });

        var icon = new draw2d.shape.icon.Gear({ 
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-input-oracle-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title">'+gettext('Oracle Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column30">'+
                                '<label form="username" class="col-form-label">'+gettext('User name:')+'</label>'+
                                '<input id="username-'+ID+'" type="text" value="" size="40" class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                            '<div class="column30">'+
                                '<label form="password" class="col-form-label">'+gettext('Password:')+'</label>'+
                                '<input type="password" id="password-'+ID+'" value="" size="40" class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                            '<div class="column40">'+
                                '<label form="dsn" class="col-form-label">'+gettext('Data source name:')+'</label>'+
                                '<input type="text" id="dsn-'+ID+'" value="" size="40" class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                            '<div class="column20">'+
                                '<label for ="get-owners" class="col-form-label">'+gettext('Get owners')+':</label><br>'+
                                '<a href="#" id="get-owners-'+ID+'" class="btn btn-default btn-sm">'+gettext('Get owners')+'</a><br>'+
                            '</div>'+
                            '<div class="column80">'+
                                '<label form="owner-name" class="col-form-label">'+gettext('Owners:')+'</label>'+
                                '<select class="form-control" id="owner-name-'+ID+'"> </select>'+
                            '</div>'+
                            '<div class="column20">'+
                                '<label for ="get-tables" class="col-form-label">'+gettext('Get tables')+':</label><br>'+
                                '<a href="#" id="get-tables-'+ID+'" class="btn btn-default btn-sm">'+gettext('Get tables')+'</a><br>'+
                            '</div>'+
                            '<div class="column80">'+
                                '<label form="table-name" class="col-form-label">'+gettext('Tables:')+'</label>'+
                                '<select class="form-control" id="table-name-'+ID+'"> </select>'+
                            '</div>'+
                            '<div class="col-md-12">'+
                                '<input type="checkbox" name="checkbox-oracle" id="checkbox-'+ID+'"/>'+
                                '<label for="checkbox">'+gettext('Do you want to write a SQL statement')+'</label>'+											
                            '</div>'+
                            '<div class="more-options-'+ID+'">'+
                                '<label class="col-form-label">'+gettext('SQL statement:')+'</label>'+
                                '<textarea id="sql-'+ID+'" rows="10" class="form-control" placeholder=""></textarea>'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" id="verify-oracle-'+ID+'">'+gettext('Verify connection')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="input-oracle-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        var context = this

        $(".more-options-"+ID).slideUp("slow")
        

        $("#checkbox-"+ID).change(function() {
            if($("#checkbox-"+ID).is(':checked')){
                $(".more-options-"+ID).slideDown("slow")
                $("#checkbox-"+ID).val("true")
            }else{
                $(".more-options-"+ID).slideUp("slow")
                $("#checkbox-"+ID).val("")
            }
        });
        
        
        $('#verify-oracle-'+ID).click(function() {
                
            var paramsOrcl = {"id": ID,
            "parameters": [
                {"username": $('#username-'+ID).val(),
                "dsn": $('#dsn-'+ID).val(),
                "password": $('#password-'+ID).val()
            }
            ]}

            var formDataOrcl = new FormData();
            
            formDataOrcl.append('jsonParamsOracle', JSON.stringify(paramsOrcl))

            $.ajax({
                type: 'POST',
                url: '/gvsigonline/etl/test_oracle_conexion/',
                data: formDataOrcl,
                beforeSend:function(xhr){
                    xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
                },
                cache: false, 
                contentType: false, 
                processData: false,
                success: function (response) {

                    if(response.result == true){
                        textConnection = gettext('Connection parameters are valids.')
                    }else{
                        textConnection = gettext('Connection parameters are not valids.')
                    }

                    $("#dialog-test-oracle-connection").remove();
                        
                    $('#canvas-parent').append('<div id="dialog-test-oracle-connection" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
                        '<div class="modal-dialog" role="document">'+
                            '<div class="modal-content">'+
                                '<div class="modal-header">'+
                                    '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                                        '<span aria-hidden="true">&times;</span>'+
                                    '</button>'+
                                    '<h4 class="modal-title">'+gettext('Response')+'</h4>'+
                                '</div>'+
                                '<div class="modal-body" align="center">'+textConnection+
                                '</div>'+
                                '<div class="modal-footer">'+
                                    '<button id= "close-test-oracle-connection" type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                                '</div>'+
                            '</div>'+
                        '</div>'+
                    '</div>')

                    $('#dialog-test-oracle-connection').modal('show')

                    $('#close-test-oracle-connection').click(function() {
                        
                        $('#dialog-test-oracle-connection').modal('hide')
                        
                    })
                }
            })
        });

        icon.on("click", function(){

            $('#dialog-input-oracle-'+ID).modal('show')

            if($("#checkbox-"+ID).is(':checked')){
                $(".more-options-"+ID).slideDown("slow")
                $("#checkbox-"+ID).val("true")
            }else{
                $(".more-options-"+ID).slideUp("slow")
                $("#checkbox-"+ID).val("")
            }
            
            $('#get-owners-'+ID).on("click", function(){
                                
                var paramsOracleOwners = {"id": ID,
                "parameters": [
                    {"username": $('#username-'+ID).val(),
                    "dsn": $('#dsn-'+ID).val(),
                    "password": $('#password-'+ID).val()}
                ]}
    
                var formDataOracleOwners = new FormData();
                
                formDataOracleOwners.append('jsonParamsOracle', JSON.stringify(paramsOracleOwners))

                $.ajax({
					type: 'POST',
					url: '/gvsigonline/etl/etl_owners_oracle/',
					data: formDataOracleOwners,
					beforeSend:function(xhr){
						xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
					},
					cache: false, 
                    contentType: false, 
                    processData: false,
					success: function (data) {

                        $('#owner-name-'+ID).empty()

                        for (i = 0; i < data.length; i++){
                            $('#owner-name-'+ID).append('<option>'+data[i]+'</option>')

                        }
                    }
                })
            });

            $('#get-tables-'+ID).on("click", function(){
                                
                var paramsOracleTables = {"id": ID,
                "parameters": [
                    {"username": $('#username-'+ID).val(),
                    "dsn": $('#dsn-'+ID).val(),
                    "password": $('#password-'+ID).val(),
                    "owner-name": $('#owner-name-'+ID).val()}
                ]}
    
                var formDataOracleTables = new FormData();
                
                formDataOracleTables.append('jsonParamsOracle', JSON.stringify(paramsOracleTables))

                $.ajax({
					type: 'POST',
					url: '/gvsigonline/etl/etl_tables_oracle/',
					data: formDataOracleTables,
					beforeSend:function(xhr){
						xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
					},
					cache: false, 
                    contentType: false, 
                    processData: false,
					success: function (data) {

                        $('#table-name-'+ID).empty()

                        for (i = 0; i < data.length; i++){
                            $('#table-name-'+ID).append('<option>'+data[i]+'</option>')

                        }
                    }
                })
            });


            $('#input-oracle-accept-'+ID).click(function() {
                
                var paramsOracle = {"id": ID,
                "parameters": [
                    {"username": $('#username-'+ID).val(),
                    "dsn": $('#dsn-'+ID).val(),
                    "password": $('#password-'+ID).val(),
                    "owner-name": $('#owner-name-'+ID).val(),
                    "table-name": $('#table-name-'+ID).val(),
                    "checkbox": $("#checkbox-"+ID).val(),
                    "sql": $('#sql-'+ID).val()}
                ]}

                var formDataSchemaOracle = new FormData();
                
                formDataSchemaOracle.append('jsonParamsOracle', JSON.stringify(paramsOracle))

                $.ajax({
					type: 'POST',
					url: '/gvsigonline/etl/etl_schema_oracle/',
					data: formDataSchemaOracle,
					beforeSend:function(xhr){
						xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
					},
					cache: false, 
                    contentType: false, 
                    processData: false,
					success: function (data) {
                        paramsOracle['schema'] = data

                        passSchemaToEdgeConnected(ID, listLabel, data, context.canvas)
                        
                        }
                    })
                
                isAlreadyInCanvas(jsonParams, paramsOracle, ID)

                icon.setColor('#01b0a0')

                $('#dialog-input-oracle-'+ID).modal('hide')
            })
        })
    },
    
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function(optionalIndex)
    {
	   	 var label =new draw2d.shape.basic.Label({
	   	     text: gettext('Input'),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:40, top:3, right:10, bottom:5},
	   	     fontColor:"#009688",
	   	     resizeable:true
	   	 });

	     var output= label.createPort("output");
         
         output.setName("output_"+label.id);
         
	     if($.isNumeric(optionalIndex)){
             this.add(label, null, optionalIndex+1);
	     }
	     else{
	         this.add(label);
         }
         
         listLabel.push([this.id, [], [output.name]])

         return label;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes : getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }

});


//// INPUT POSTGRES////

input_Postgres = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "input_Postgres",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3, width:1},attr));
        
        this.classLabel = new draw2d.shape.basic.Label({
            text:"PostgreSQL", 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#83d0c9", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });

        var icon = new draw2d.shape.icon.Gear({ 
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-input-postgis-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title">'+gettext('PostGIS Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column50">'+
                                '<label form="host" class="col-form-label">'+gettext('Host:')+'</label>'+
                                '<input id="host-'+ID+'" type="text" value="localhost" size="40" class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                            '<div class="column50">'+    
                                '<label form="port" class="col-form-label">'+gettext('Port:')+'</label>'+
                                '<input id="port-'+ID+'" type="text" value="5432" size="40" class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label form="database" class="col-form-label">'+gettext('Database:')+'</label>'+
                                '<input id="database-'+ID+'" type="text" value="" size="40" class="form-control" pattern="[A-Za-z]{3}" placeholder="'+gettext('Name of your database')+'">'+
                            '</div>'+
                            '<div class="column50">'+                                
                                '<label form="user" class="col-form-label">'+gettext('User:')+'</label>'+
                                '<input id="user-'+ID+'" type="text" value="postgres" size="40"  class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label form="password" class="col-form-label">'+gettext('Password:')+'</label>'+
                                '<input type="password" id = "password-'+ID+'" class="form-control" value="">'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label form="tablename" class="col-form-label">'+gettext('Table name:')+'</label>'+
                                '<input id="tablename-'+ID+'" type="text" value="" size="40" class="form-control" pattern="[A-Za-z]{3}" placeholder="'+gettext('schema.tablename')+'">'+
                            '</div>'+
                            '<div class="col-md-12">'+
                                '<input type="checkbox" name="checkbox-postgres" id="checkbox-'+ID+'"/>'+
                                '<label for="checkbox">'+gettext('Do you want to write a SQL WHERE Clause')+'</label>'+											
                            '</div>'+
                            '<div class="more-options-'+ID+'">'+
                                '<label class="col-form-label">'+gettext('SQL WHERE Clause:')+'</label>'+
                                '<textarea id="clause-'+ID+'" rows="1" class="form-control" placeholder=""></textarea>'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="verify-postgresql-'+ID+'">'+gettext('Verify connection')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="input-postgis-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')


        $("#checkbox-"+ID).change(function() {
            if($("#checkbox-"+ID).is(':checked')){
                $(".more-options-"+ID).slideDown("slow")
                $("#checkbox-"+ID).val("true")
            }else{
                $(".more-options-"+ID).slideUp("slow")
                $("#checkbox-"+ID).val("")
            }
        });

        var context = this

        $('#verify-postgresql-'+ID).click(function() {
                
            var paramsPostgres = {"id": ID,
                "parameters": [
                    {"host": $('#host-'+ID).val(),
                    "port": $('#port-'+ID).val(),
                    "database": $('#database-'+ID).val(),
                    "user": $('#user-'+ID).val(),
                    "password": $('#password-'+ID).val()}
                ]}
    
                var formDataPostgres = new FormData();
                
                formDataPostgres.append('jsonParamsPostgres', JSON.stringify(paramsPostgres))
    
                $.ajax({
                    type: 'POST',
                    url: '/gvsigonline/etl/test_postgres_conexion/',
                    data: formDataPostgres,
                    beforeSend:function(xhr){
                        xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
                    },
                    cache: false, 
                    contentType: false, 
                    processData: false,
                    success: function (response) {
    
                        if(response.result == true){
                            textConnection = gettext('Connection parameters are valids.')
                        }else{
                            textConnection = gettext('Connection parameters are not valids.')
                        }
    
                        $("#dialog-test-postgres-connection").remove();
                            
                        $('#canvas-parent').append('<div id="dialog-test-postgres-connection" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
                            '<div class="modal-dialog" role="document">'+
                                '<div class="modal-content">'+
                                    '<div class="modal-header">'+
                                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                                            '<span aria-hidden="true">&times;</span>'+
                                        '</button>'+
                                        '<h4 class="modal-title">'+gettext('Response')+'</h4>'+
                                    '</div>'+
                                    '<div class="modal-body" align="center">'+textConnection+
                                    '</div>'+
                                    '<div class="modal-footer">'+
                                        '<button id= "close-test-postgres-connection" type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                                    '</div>'+
                                '</div>'+
                            '</div>'+
                        '</div>')
    
                        $('#dialog-test-postgres-connection').modal('show')
    
                        $('#close-test-postgres-connection').click(function() {
                            
                            $('#dialog-test-postgres-connection').modal('hide')
                            
                        })
                    }
                })
            });

        icon.on("click", function(){

            $('#dialog-input-postgis-'+ID).modal('show')

            if($("#checkbox-"+ID).is(':checked')){
                $(".more-options-"+ID).slideDown("slow")
                $("#checkbox-"+ID).val("true")
            }else{
                $(".more-options-"+ID).slideUp("slow")
                $("#checkbox-"+ID).val("")
            }

            $('#input-postgis-accept-'+ID).click(function() {
                
                var paramsPostgis = {"id": ID,
                "parameters": [
                    {"host": $('#host-'+ID).val(),
                    "port": $('#port-'+ID).val(),
                    "database": $('#database-'+ID).val(),
                    "user": $('#user-'+ID).val(),
                    "password": $('#password-'+ID).val(),
                    "tablename": $('#tablename-'+ID).val(),
                    "checkbox": $("#checkbox-"+ID).val(),
                    "clause": $('#clause-'+ID).val()}
                ]}
    
                var formDataSchemaPostgis = new FormData();
                
                formDataSchemaPostgis.append('jsonParamsPostgres', JSON.stringify(paramsPostgis))

                $.ajax({
					type: 'POST',
					url: '/gvsigonline/etl/etl_schema_postgresql/',
					data: formDataSchemaPostgis,
					beforeSend:function(xhr){
						xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
					},
					cache: false, 
                    contentType: false, 
                    processData: false,
					success: function (data) {
                        paramsPostgis['schema'] = data
                        paramsPostgis['parameters'][0]['schema'] = data

                        passSchemaToEdgeConnected(ID, listLabel, data, context.canvas)
                        
                        isAlreadyInCanvas(jsonParams, paramsPostgis, ID)
                        
                        icon.setColor('#01b0a0')
                        
                        $('#dialog-input-postgis-'+ID).modal('hide')
                        
                        }
                    })
                

            })
        })
    },
    
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function(optionalIndex)
    {
	   	 var label =new draw2d.shape.basic.Label({
	   	     text: gettext('Input'),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:40, top:3, right:10, bottom:5},
	   	     fontColor:"#009688",
	   	     resizeable:true
	   	 });

	     var output= label.createPort("output");
         
         output.setName("output_"+label.id);
         
	     if($.isNumeric(optionalIndex)){
             this.add(label, null, optionalIndex+1);
	     }
	     else{
	         this.add(label);
         }
         
         listLabel.push([this.id, [], [output.name]])

         return label;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes : getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }

});


//// INPUT POSTGIS////

input_Postgis = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "input_Postgis",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3, width:1},attr));
        
        this.classLabel = new draw2d.shape.basic.Label({
            text:"PostGIS", 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#83d0c9", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });

        var icon = new draw2d.shape.icon.Gear({ 
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-input-postgis-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title">'+gettext('PostGIS Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column50">'+
                                '<label form="host" class="col-form-label">'+gettext('Host:')+'</label>'+
                                '<input id="host-'+ID+'" type="text" value="localhost" size="40" class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                            '<div class="column50">'+    
                                '<label form="port" class="col-form-label">'+gettext('Port:')+'</label>'+
                                '<input id="port-'+ID+'" type="text" value="5432" size="40" class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label form="database" class="col-form-label">'+gettext('Database:')+'</label>'+
                                '<input id="database-'+ID+'" type="text" value="" size="40" class="form-control" pattern="[A-Za-z]{3}" placeholder="'+gettext('Name of your database')+'">'+
                            '</div>'+
                            '<div class="column50">'+                                
                                '<label form="user" class="col-form-label">'+gettext('User:')+'</label>'+
                                '<input id="user-'+ID+'" type="text" value="postgres" size="40"  class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label form="password" class="col-form-label">'+gettext('Password:')+'</label>'+
                                '<input type="password" id = "password-'+ID+'" class="form-control" value="">'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label form="tablename" class="col-form-label">'+gettext('Table name:')+'</label>'+
                                '<input id="tablename-'+ID+'" type="text" value="" size="40" class="form-control" pattern="[A-Za-z]{3}" placeholder="'+gettext('schema.tablename')+'">'+
                            '</div>'+
                            '<div class="col-md-12">'+
                                '<input type="checkbox" name="checkbox-postgres" id="checkbox-'+ID+'"/>'+
                                '<label for="checkbox">'+gettext('Do you want to write a SQL WHERE Clause')+'</label>'+											
                            '</div>'+
                            '<div class="more-options-'+ID+'">'+
                                '<label class="col-form-label">'+gettext('SQL WHERE Clause:')+'</label>'+
                                '<textarea id="clause-'+ID+'" rows="1" class="form-control" placeholder=""></textarea>'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="verify-postgresql-'+ID+'">'+gettext('Verify connection')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="input-postgis-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')


        $("#checkbox-"+ID).change(function() {
            if($("#checkbox-"+ID).is(':checked')){
                $(".more-options-"+ID).slideDown("slow")
                $("#checkbox-"+ID).val("true")
            }else{
                $(".more-options-"+ID).slideUp("slow")
                $("#checkbox-"+ID).val("")
            }
        });

        var context = this

        $('#verify-postgresql-'+ID).click(function() {
                
            var paramsPostgres = {"id": ID,
                "parameters": [
                    {"host": $('#host-'+ID).val(),
                    "port": $('#port-'+ID).val(),
                    "database": $('#database-'+ID).val(),
                    "user": $('#user-'+ID).val(),
                    "password": $('#password-'+ID).val()}
                ]}
    
                var formDataPostgres = new FormData();
                
                formDataPostgres.append('jsonParamsPostgres', JSON.stringify(paramsPostgres))
    
                $.ajax({
                    type: 'POST',
                    url: '/gvsigonline/etl/test_postgres_conexion/',
                    data: formDataPostgres,
                    beforeSend:function(xhr){
                        xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
                    },
                    cache: false, 
                    contentType: false, 
                    processData: false,
                    success: function (response) {
    
                        if(response.result == true){
                            textConnection = gettext('Connection parameters are valids.')
                        }else{
                            textConnection = gettext('Connection parameters are not valids.')
                        }
    
                        $("#dialog-test-postgres-connection").remove();
                            
                        $('#canvas-parent').append('<div id="dialog-test-postgres-connection" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
                            '<div class="modal-dialog" role="document">'+
                                '<div class="modal-content">'+
                                    '<div class="modal-header">'+
                                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                                            '<span aria-hidden="true">&times;</span>'+
                                        '</button>'+
                                        '<h4 class="modal-title">'+gettext('Response')+'</h4>'+
                                    '</div>'+
                                    '<div class="modal-body" align="center">'+textConnection+
                                    '</div>'+
                                    '<div class="modal-footer">'+
                                        '<button id= "close-test-postgres-connection" type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                                    '</div>'+
                                '</div>'+
                            '</div>'+
                        '</div>')
    
                        $('#dialog-test-postgres-connection').modal('show')
    
                        $('#close-test-postgres-connection').click(function() {
                            
                            $('#dialog-test-postgres-connection').modal('hide')
                            
                        })
                    }
                })
            });

        icon.on("click", function(){

            $('#dialog-input-postgis-'+ID).modal('show')

            if($("#checkbox-"+ID).is(':checked')){
                $(".more-options-"+ID).slideDown("slow")
                $("#checkbox-"+ID).val("true")
            }else{
                $(".more-options-"+ID).slideUp("slow")
                $("#checkbox-"+ID).val("")
            }

            $('#input-postgis-accept-'+ID).click(function() {
                
                var paramsPostgis = {"id": ID,
                "parameters": [
                    {"host": $('#host-'+ID).val(),
                    "port": $('#port-'+ID).val(),
                    "database": $('#database-'+ID).val(),
                    "user": $('#user-'+ID).val(),
                    "password": $('#password-'+ID).val(),
                    "tablename": $('#tablename-'+ID).val(),
                    "checkbox": $("#checkbox-"+ID).val(),
                    "clause": $('#clause-'+ID).val()}
                ]}
    
                var formDataSchemaPostgis = new FormData();
                
                formDataSchemaPostgis.append('jsonParamsPostgres', JSON.stringify(paramsPostgis))

                $.ajax({
					type: 'POST',
					url: '/gvsigonline/etl/etl_schema_postgresql/',
					data: formDataSchemaPostgis,
					beforeSend:function(xhr){
						xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
					},
					cache: false, 
                    contentType: false, 
                    processData: false,
					success: function (data) {
                        paramsPostgis['schema'] = data
                        paramsPostgis['parameters'][0]['schema'] = data

                        passSchemaToEdgeConnected(ID, listLabel, data, context.canvas)
                        
                        isAlreadyInCanvas(jsonParams, paramsPostgis, ID)
                        
                        icon.setColor('#01b0a0')
                        
                        $('#dialog-input-postgis-'+ID).modal('hide')
                        
                        }
                    })
                

            })
        })
    },
    
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function(optionalIndex)
    {
	   	 var label =new draw2d.shape.basic.Label({
	   	     text: gettext('Input'),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:40, top:3, right:10, bottom:5},
	   	     fontColor:"#009688",
	   	     resizeable:true
	   	 });

	     var output= label.createPort("output");
         
         output.setName("output_"+label.id);
         
	     if($.isNumeric(optionalIndex)){
             this.add(label, null, optionalIndex+1);
	     }
	     else{
	         this.add(label);
         }
         
         listLabel.push([this.id, [], [output.name]])

         return label;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes : getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }

});

////////////////////////////////////////////////  TRANSFORMERS /////////////////////////////////////////////////////////
//// JOIN ////

trans_Join = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_Join",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
        
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext('Join'), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({ 
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-join-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext('Join Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column50">'+
                                '<label form="attr1" class="col-form-label">'+gettext('Main table attribute:')+'</label>'+
                                '<select class="form-control" id="attr1-'+ID+'"> </select>'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label form="attr2" class="col-form-label">'+gettext('Secondary table attribute:')+'</label>'+
                                '<select class="form-control" id="attr2-'+ID+'"> </select>'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="join-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')
        
        context = this

        icon.on("click", function(){
            
            setTimeout(function(){
                try{
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge
                   
                    $('#attr1-'+ID).empty()
                    $('#attr2-'+ID).empty()

                    for (i = 0; i < schema[0].length; i++){
                        $('#attr1-'+ID).append('<option>'+schema[0][i]+'</option>')
                    }
                    for (i = 0; i < schema[1].length; i++){
                        $('#attr2-'+ID).append('<option>'+schema[1][i]+'</option>')
                    }
                }

            },100);

            $('#dialog-join-'+ID).modal('show')

            $('#join-accept-'+ID).click(function() {

                var paramsJoin = {"id": ID,
                "parameters": [
                    {"attr1": $('#attr1-'+ID).val(),
                    "attr2": $('#attr2-'+ID).val(),
                    "schemas": schemaEdge}
                ]}

                paramsJoin['schema-old'] = schemaEdge

                if (Array.isArray(schemaEdge[0])){
                    
                    chars = schemaEdge[0].concat(schemaEdge[1])

                    let unique = chars.filter((c, index) => {
                        return chars.indexOf(c) === index;
                    });

                    schemaMod = [unique, schemaEdge[0],schemaEdge[1]]
                }
                else{
                    schemaMod = [...schemaEdge]
                }

                paramsJoin['schema'] = schemaMod

                passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)

                isAlreadyInCanvas(jsonParams, paramsJoin, ID)

                icon.setColor('#4682B4')
                
                $('#dialog-join-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext('Input Main'),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext('Input Sec.'),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:10, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

        var label3 =new draw2d.shape.basic.Label({
            text: gettext('Join'),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

        var label4 =new draw2d.shape.basic.Label({
            text: gettext("Main Not Used"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

        var label5 =new draw2d.shape.basic.Label({
            text: gettext("Sec. Not Used"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

        var input1 = label1.createPort("input");
        input1.setName("input_"+label1.id);

        var input2 = label2.createPort("input");
        input2.setName("input_"+label2.id);

	    var output1= label3.createPort("output");
        output1.setName("output_"+label3.id);

	    var output2= label4.createPort("output");
        output2.setName("output_"+label4.id);

	    var output3= label5.createPort("output");
        output3.setName("output_"+label5.id);

	    if($.isNumeric(optionalIndex)){
            this.add(label1, null, optionalIndex+1);
            this.add(label2, null, optionalIndex+1);
            this.add(label3, null, optionalIndex+1);
            this.add(label4, null, optionalIndex+1);
            this.add(label5, null, optionalIndex+1);
	    }
	    else{
            this.add(label1);
            this.add(label2);
            this.add(label3);
            this.add(label4);
            this.add(label5);
        }
         
        listLabel.push([this.id, [input1.name, input2.name], [output1.name, output2.name, output3.name]])

	    return label1, label2, label3, label4, label5;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     

     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes : getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});


//// COMPARE ROWS ////

trans_CompareRows = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_CompareRows",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
        
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext('Compare Rows'), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({ 
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-compare-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext('Compare Rows Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<label form="attr" class="col-form-label">'+gettext('Attribute:')+'</label>'+
                                '<select class="form-control" id="attr-'+ID+'"> </select>'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="compare-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')
        
        context = this

        icon.on("click", function(){
            
            setTimeout(function(){
                try{
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge
                   
                    $('#attr-'+ID).empty()

                    for (i = 0; i < schema[0].length; i++){
                        $('#attr-'+ID).append('<option>'+schema[0][i]+'</option>')
                    }
                }

            },100);

            $('#dialog-compare-'+ID).modal('show')

            $('#compare-accept-'+ID).click(function() {

                var paramsCompare = {"id": ID,
                "parameters": [
                    {"attr": $('#attr-'+ID).val(),
                    }
                ]}

                paramsCompare['schema-old'] = schemaEdge

                if (Array.isArray(schemaEdge[0])){
                    schemaMod = [schemaEdge[0], schemaEdge[0], schemaEdge[0], schemaEdge[1]]
                }
                else{
                    schemaMod = [...schemaEdge]
                }

                paramsCompare['schema'] = schemaMod

                passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)

                isAlreadyInCanvas(jsonParams, paramsCompare, ID)

                icon.setColor('#4682B4')
                
                $('#dialog-compare-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext('Input Main'),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext('Input to comp.'),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:10, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

        var label3 =new draw2d.shape.basic.Label({
            text: gettext('Equals'),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

        var label4 =new draw2d.shape.basic.Label({
            text: gettext("News"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

        var label5 =new draw2d.shape.basic.Label({
            text: gettext("Changes"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

        var label6 =new draw2d.shape.basic.Label({
            text: gettext("Comp. Not Used"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

        var input1 = label1.createPort("input");
        input1.setName("input_"+label1.id);

        var input2 = label2.createPort("input");
        input2.setName("input_"+label2.id);

	    var output1= label3.createPort("output");
        output1.setName("output_"+label3.id);

	    var output2= label4.createPort("output");
        output2.setName("output_"+label4.id);

	    var output3= label5.createPort("output");
        output3.setName("output_"+label5.id);
    
        var output4= label6.createPort("output");
        output4.setName("output_"+label6.id);

	    if($.isNumeric(optionalIndex)){
            this.add(label1, null, optionalIndex+1);
            this.add(label2, null, optionalIndex+1);
            this.add(label3, null, optionalIndex+1);
            this.add(label4, null, optionalIndex+1);
            this.add(label5, null, optionalIndex+1);
            this.add(label6, null, optionalIndex+1);
	    }
	    else{
            this.add(label1);
            this.add(label2);
            this.add(label3);
            this.add(label4);
            this.add(label5);
            this.add(label6);
        }
         
        listLabel.push([this.id, [input1.name, input2.name], [output1.name, output2.name, output3.name, output4.name]])

	    return label1, label2, label3, label4, label5, label6;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     

     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes : getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// REMOVE ATTRIBUTE ////

trans_RemoveAttr = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_RemoveAttr",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Remove Attribute"), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        context = this
        
        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        //adding dialog for choosing parameters of the transformer
        $('#canvas-parent').append('<div id="dialog-remove-attr-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext('Remove Attribute Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<label form="attr" class="col-form-label">'+gettext('Attribute to remove:')+'</label>'+
                            '<select class="form-control" size="8" multiple  id="attr-'+ID+'"> </select>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="remove-attr-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

       

        icon.on("click", function(){

            setTimeout(function(){
                
                try{
                    // if it's not the first time opening parameters dialog
                    //json figure task will has already the schemas
                    //old is the schema that came from the edge
                    //the other one is result schema depending of parameters chosen
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                //get schema from the edge
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                //if edge schema and old schema is not the same is the first time you open parameters or
                //something was changed in the edge so we hace to create a new schema option
                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge
                    $('#attr-'+ID).empty()

                    for (i = 0; i < schema.length; i++){
                        
                        $('#attr-'+ID).append('<option>'+schema[i]+'</option>')
                    }
                }

            },100);
            

            $('#dialog-remove-attr-'+ID).modal('show')

            $('#remove-attr-accept-'+ID).click(function() {

                //parameters selected to json
                var paramsRemove = {"id": ID,
                "parameters": [
                {"attr": $('#attr-'+ID).val()}
                ]}

                //schema handling depending the parameters chosen
                //this case we remove an attribute
                schemaMod =[...schemaEdge]
                //schemaMod.splice($('#attr-'+ID).prop('selectedIndex'), 1)
                
                for (oa = 0; oa < $('#attr-'+ID).val().length; oa++){
                    
                    _Attr = $('#attr-'+ID).val()[oa]
                    
                    schemaMod.splice(schemaMod.indexOf(_Attr), 1)

                }
                
                //updating schema-old and schema parameters in json
                paramsRemove['schema-old'] = schemaEdge
                paramsRemove['schema'] = schemaMod

                //add the schema to a later edge if it exists
                passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)
                
                //check if parameters are already in json canvas
                isAlreadyInCanvas(jsonParams, paramsRemove, ID)

                //set red color to another in order to know if parameters are checked
                icon.setColor('#4682B4')
                
                $('#dialog-remove-attr-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Output"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

	     var output= label2.createPort("output");
         output.setName("output_"+label2.id);

	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
	     }
	     else{
             this.add(label1);
             this.add(label2);
         }
         
         listLabel.push([this.id, [input.name], [output.name]])

	     return label1, label2;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes :getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// RENAME ATTRIBUTE ////

trans_RenameAttr = draw2d.shape.layout.VerticalLayout.extend({

    NAME: "trans_RenameAttr",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Rename Attribute"), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({ 
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-rename-attr-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext("Rename Attribute Parameters")+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<label class="col-form-label">'+gettext('Attribute to rename:')+'</label>'+
                                '<select class="form-control" size="8" multiple id="old-attr-'+ID+'"> </select>'+
                            '</div>'+
                            '<div>'+
                            '<label class="col-form-label">'+gettext('New name:')+'</label>'+
                                '<input id="new-attr-'+ID+'" type="text" size="40" value="" class="form-control" pattern="[A-Za-z]{3}" placeholder="'+gettext('New name')+'">'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="rename-attr-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')
        
        context = this

        icon.on("click", function(){

            setTimeout(function(){
                try{
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge
                    $('#old-attr-'+ID).empty()

                    for (i = 0; i < schema.length; i++){
                        
                        $('#old-attr-'+ID).append('<option>'+schema[i]+'</option>')
                    }
                }

            },100);

            $('#dialog-rename-attr-'+ID).modal('show')

            $('#rename-attr-accept-'+ID).click(function() {

                
                var paramsRename = {"id": ID,
                "parameters": [
                    {"old-attr": $('#old-attr-'+ID).val(),
                    "new-attr": $('#new-attr-'+ID).val() }
                ]}

                schemaMod =[...schemaEdge]
                
                for (oa = 0; oa < $('#old-attr-'+ID).val().length; oa++){
                    
                    oldAttr = $('#old-attr-'+ID).val()[oa]

                    newAttr = $('#new-attr-'+ID).val().split(" ")[oa]
                    
                    schemaMod.splice(schemaMod.indexOf(oldAttr), 1, newAttr)

                }
                
                paramsRename['schema-old'] = schemaEdge
                paramsRename['schema'] = schemaMod


                passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)

                isAlreadyInCanvas(jsonParams, paramsRename, ID)

                icon.setColor('#4682B4')
                
                $('#dialog-rename-attr-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Output"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

	     var output= label2.createPort("output");
         output.setName("output_"+label2.id);

	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
	     }
	     else{
             this.add(label1);
             this.add(label2);
	     }

         listLabel.push([this.id, [input.name], [output.name]])

	     return label1, label2;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes : getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// CONCATENATE ATTRIBUTES ////

trans_ConcatAttr = draw2d.shape.layout.VerticalLayout.extend({

    NAME: "trans_ConcatAttr",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Concatenate Attr."), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({ 
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-concat-attr-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext("Concatenate Attributes Parameters")+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<label class="col-form-label">'+gettext('Attributes to concatenate:')+'</label>'+
                                '<select class="form-control" size="8" multiple id="attr-'+ID+'"> </select>'+
                            '</div>'+
                            '<div class="column80">'+
                            '<label class="col-form-label">'+gettext('New attribute name:')+'</label>'+
                                '<input id="new-attr-'+ID+'" type="text" size="40" value="" class="form-control" pattern="[A-Za-z]{3}" placeholder="'+gettext('New attribute name')+'">'+
                            '</div>'+
                            '<div class="column20">'+
                            '<label class="col-form-label">'+gettext('Separator (opt.):')+'</label>'+
                                '<input id="separator-'+ID+'" type="text" value="" class="form-control" pattern="[A-Za-z]{3}" placeholder="'+gettext('Separator')+'">'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="concat-attr-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')
        
        context = this

        icon.on("click", function(){

            setTimeout(function(){
                try{
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge
                    $('#attr-'+ID).empty()

                    for (i = 0; i < schema.length; i++){
                        
                        $('#attr-'+ID).append('<option>'+schema[i]+'</option>')
                    }
                }

            },100);

            $('#dialog-concat-attr-'+ID).modal('show')

            $('#concat-attr-accept-'+ID).click(function() {

                
                var paramsConcat = {"id": ID,
                "parameters": [
                    {"attr": $('#attr-'+ID).val(),
                    "new-attr": $('#new-attr-'+ID).val(),
                    "separator": $('#separator-'+ID).val() }
                ]}

                schemaMod =[...schemaEdge]
                
                schemaMod.push($('#new-attr-'+ID).val())

                paramsConcat['schema-old'] = schemaEdge
                paramsConcat['schema'] = schemaMod


                passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)

                isAlreadyInCanvas(jsonParams, paramsConcat, ID)

                icon.setColor('#4682B4')
                
                $('#dialog-concat-attr-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Output"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

	     var output= label2.createPort("output");
         output.setName("output_"+label2.id);

	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
	     }
	     else{
             this.add(label1);
             this.add(label2);
	     }

         listLabel.push([this.id, [input.name], [output.name]])

	     return label1, label2;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes : getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// PAD ATTRIBUTE////

trans_PadAttr = draw2d.shape.layout.VerticalLayout.extend({

    NAME: "trans_PadAttr",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Pad Attribute"), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({ 
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-pad-attr-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext("Pad Attribute Parameters")+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<label class="col-form-label">'+gettext('Attribute to pad:')+'</label>'+
                                '<select class="form-control" id="attr-'+ID+'"> </select>'+
                            '</div>'+
                            '<div>'+
                                '<label class="col-form-label">'+gettext('Length desired:')+'</label>'+
                                '<input id="length-'+ID+'" type="number" value="0" class="form-control" >'+
                            '</div>'+
                            '<div>'+
                                '<label class="col-form-label">'+gettext('Side to pad:')+'</label>'+
                                '<select class="form-control" id="side-'+ID+'">' +
                                    '<option>'+gettext('Right')+'</option>'+
                                    '<option>'+gettext('Left')+'</option>'+
                                '</select>'+
                            '</div>'+
                            '<div>'+
                            '<label class="col-form-label">'+gettext('Pad String:')+'</label>'+
                                '<input id="string-'+ID+'" type="text" value="" class="form-control" pattern="[A-Za-z]{3}" >'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="pad-attr-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')
        
        context = this

        icon.on("click", function(){

            setTimeout(function(){
                try{
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge
                    $('#attr-'+ID).empty()

                    for (i = 0; i < schema.length; i++){
                        
                        $('#attr-'+ID).append('<option>'+schema[i]+'</option>')
                    }
                }

            },100);

            $('#dialog-pad-attr-'+ID).modal('show')

            $('#pad-attr-accept-'+ID).click(function() {

                
                var paramsPad = {"id": ID,
                "parameters": [
                    {"attr": $('#attr-'+ID).val(),
                    "length": $('#length-'+ID).val(),
                    "side": $('#side-'+ID).val(),
                    "string": $('#string-'+ID).val()}
                ]}

                //schemaMod =[...schemaEdge]
                
                //schemaMod.push($('#new-attr-'+ID).val())

                paramsPad['schema-old'] = schemaEdge
                paramsPad['schema'] = schemaEdge


                passSchemaToEdgeConnected(ID, listLabel, schemaEdge, context.canvas)

                isAlreadyInCanvas(jsonParams, paramsPad, ID)

                icon.setColor('#4682B4')
                
                $('#dialog-pad-attr-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Output"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

	     var output= label2.createPort("output");
         output.setName("output_"+label2.id);

	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
	     }
	     else{
             this.add(label1);
             this.add(label2);
	     }

         listLabel.push([this.id, [input.name], [output.name]])

	     return label1, label2;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes : getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// FILTER DUPLICATES ////

trans_FilterDupli = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_FilterDupli",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Filter Duplicate"), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        context = this
        
        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        //adding dialog for choosing parameters of the transformer
        $('#canvas-parent').append('<div id="dialog-filter-dupli-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext('Filter Duplicate Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<label form="attr" class="col-form-label">'+gettext('Attributes that must be uniques:')+'</label>'+
                            '<select class="form-control" size="8" multiple  id="attr-'+ID+'"> </select>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="filter-dupli-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        icon.on("click", function(){

            setTimeout(function(){
                
                try{
                    // if it's not the first time opening parameters dialog
                    //json figure task will has already the schemas
                    //old is the schema that came from the edge
                    //the other one is result schema depending of parameters chosen
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                //get schema from the edge
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                //if edge schema and old schema is not the same is the first time you open parameters or
                //something was changed in the edge so we hace to create a new schema option
                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge
                    $('#attr-'+ID).empty()

                    for (i = 0; i < schema.length; i++){
                        
                        $('#attr-'+ID).append('<option>'+schema[i]+'</option>')
                    }
                }

            },100);
            

            $('#dialog-filter-dupli-'+ID).modal('show')

            $('#filter-dupli-accept-'+ID).click(function() {

                //parameters selected to json
                var paramsRemove = {"id": ID,
                "parameters": [
                {"attr": $('#attr-'+ID).val()}
                ]}
                
                //updating schema-old and schema parameters in json
                paramsRemove['schema-old'] = schemaEdge
                paramsRemove['schema'] = schemaEdge

                //add the schema to a later edge if it exists
                passSchemaToEdgeConnected(ID, listLabel, schemaEdge, context.canvas)
                
                //check if parameters are already in json canvas
                isAlreadyInCanvas(jsonParams, paramsRemove, ID)

                //set red color to another in order to know if parameters are checked
                icon.setColor('#4682B4')
                
                $('#dialog-filter-dupli-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Unique"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

        var label3 =new draw2d.shape.basic.Label({
            text: gettext("Duplicated"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

	     var output= label2.createPort("output");
         output.setName("output_"+label2.id);

	     var output2= label3.createPort("output");
         output.setName("output_"+label3.id);

	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
             this.add(label3, null, optionalIndex+1);
	     }
	     else{
             this.add(label1);
             this.add(label2);
             this.add(label3);
         }
         
         listLabel.push([this.id, [input.name], [output.name, output2.name]])

	     return label1, label2, label3;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes :getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// MODIFY VALUE ATTRIBUTE ////

trans_ModifyValue = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_ModifyValue",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
        
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Modify Value"), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-modify-value-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext('Modify Value Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column50">'+
                                '<label class="col-form-label">'+gettext('Attribute to modify:')+'</label>'+
                                '<select class="form-control" id="attr-'+ID+'"> </select>'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label class="col-form-label">'+gettext('New value:')+'</label>'+
                                '<input id="value-'+ID+'" type="text" size="40" value="" class="form-control" pattern="[A-Za-z]{3}" placeholder="'+gettext('New attribute value')+'">'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="modify-value-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')
        
        context = this

        icon.on("click", function(){
            
            setTimeout(function(){
                try{
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge
                    $('#attr-'+ID).empty()

                    for (i = 0; i < schema.length; i++){
                        
                        $('#attr-'+ID).append('<option>'+schema[i]+'</option>')
                    }
                }

            },100);
            

            $('#dialog-modify-value-'+ID).modal('show')

            $('#modify-value-accept-'+ID).click(function() {

                var paramsModifyValue = {"id": ID,
                "parameters": [
                    {"attr": $('#attr-'+ID).val(),
                    "value": $('#value-'+ID).val() }
                ]}

                paramsModifyValue['schema-old'] = schemaEdge
                paramsModifyValue['schema'] = schema

                passSchemaToEdgeConnected(ID, listLabel, schema, context.canvas)
                isAlreadyInCanvas(jsonParams, paramsModifyValue, ID)

                icon.setColor('#4682B4')
                
                $('#dialog-modify-value-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Output"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

	     var output= label2.createPort("output");
         output.setName("output_"+label2.id);

	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
	     }
	     else{
             this.add(label1);
             this.add(label2);
         }
         
         listLabel.push([this.id,[input.name], [output.name]])

	     return label1, label2;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes :getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// COUNTER ////

trans_Counter = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_Counter",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
        
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Counter"), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-counter-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext('Counter Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column50">'+
                                '<label class="col-form-label">'+gettext('New counter attribute:')+'</label>'+
                                '<input id="attr-'+ID+'" type="text" size="40" value="_count" class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label class="col-form-label">'+gettext('Group by:')+'</label>'+
                                '<select class="form-control" id="group-by-attr-'+ID+'"> </select>'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="counter-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')
        
        context = this

        icon.on("click", function(){
            
            setTimeout(function(){
                try{
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge
                    $('#group-by-attr-'+ID).empty()
                    $('#group-by-attr-'+ID).append('<option> </option>')

                    for (i = 0; i < schema.length; i++){
                        
                        $('#group-by-attr-'+ID).append('<option>'+schema[i]+'</option>')
                    }
                }

            },100);
            

            $('#dialog-counter-'+ID).modal('show')

            $('#counter-accept-'+ID).click(function() {

                var paramsCounter = {"id": ID,
                "parameters": [
                    {"attr": $('#attr-'+ID).val(),
                    "group-by-attr": $('#group-by-attr-'+ID).val()}
                ]}

                schemaMod =[...schemaEdge]
                
                schemaMod.push($('#attr-'+ID).val())
                
                paramsCounter['schema'] = schemaMod
                paramsCounter['schema-old'] = schemaEdge
                

                passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)
                isAlreadyInCanvas(jsonParams, paramsCounter, ID)

                icon.setColor('#4682B4')
                
                $('#dialog-counter-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Output"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

	     var output= label2.createPort("output");
         output.setName("output_"+label2.id);

	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
	     }
	     else{
             this.add(label1);
             this.add(label2);
         }
         
         listLabel.push([this.id,[input.name], [output.name]])

	     return label1, label2;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     

     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes :getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// CALCULATOR ////

trans_Calculator = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_Calculator",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Calculator"), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-calculator-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext('Calculator Parameters')+'</h4>'+
                    '</div>'+
                    '<div  class="modal-body">'+
                        '<form>'+
                            '<div class="column33">'+
                                '<label class="col-form-label">'+gettext('Attribute:')+'</label>'+
                                '<select class="form-control" id="attr-'+ID+'"> </select>'+
                                '<label class="col-form-label">'+gettext('Math functions:')+'</label>'+
                                '<div id ="functions-calculator">'+
                                    '<ul id ="functions-'+ID+'" class="nav flex-column">'+
                                        '<li class="nav-item">'+
                                            '<a class="nav-link active" name="+">&#43;</a>'+
                                        '</li>'+
                                        '<li class="nav-item">'+
                                            '<a class="nav-link active" name="-">&#8722;</a>'+
                                        '</li>'+
                                        '<li class="nav-item">'+
                                            '<a class="nav-link active" name="*">&#215;</a>'+
                                        '</li>'+
                                        '<li class="nav-item">'+
                                            '<a class="nav-link active" name="/">&#247;</a>'+
                                        '</li>'+
                                        '<li class="nav-item">'+
                                            '<a class="nav-link active" name="|/">&#8730;x</a>'+
                                        '</li>'+
                                        '<li class="nav-item">'+
                                            '<a class="nav-link active" name="^2">x&#178;</a>'+
                                        '</li>'+
                                        '<li class="nav-item">'+
                                            '<a class="nav-link active" name="sin()">sin(x)</a>'+
                                        '</li>'+
                                        '<li class="nav-item">'+
                                            '<a class="nav-link active" name="cos()">cos(x)</a>'+
                                        '</li>'+
                                        '<li class="nav-item">'+
                                            '<a class="nav-link active" name="tan()">tan(x)</a>'+
                                        '</li>'+
                                        '<li class="nav-item">'+
                                            '<a class="nav-link active" name="pi()">&#960;</a>'+
                                        '</li>'+
                                    '</ul>'+
                                '</div><br><br><br><br><br><br><br><br><br><br>'+

                                '<label class="col-form-label">'+gettext('Attributes:')+'</label>'+
                                '<div id ="schema-calculator">'+
                                    '<ul id ="schema-calculator-'+ID+'" class="nav flex-column">'+
                                    '</ul>'+
                                '</div>'+
                            '</div>'+
                            '<div class="column66">'+
                                '<label class="col-form-label"><a href="https://www.postgresql.org/docs/9.0/functions-math.html" target="_blank">'+gettext('Expression:')+'</a></label>'+
                                '<textarea id="expression-'+ID+'" rows="20" class="form-control" placeholder="'+gettext('For more math functions check above link.')+'"></textarea>'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="calculator-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')
        
        context = this

        icon.on("click", function(){
            
            setTimeout(function(){
                try{
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                    
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge

                    $('#attr-'+ID).empty()
                    $('#schema-calculator-'+ID).empty()

                    for (i = 0; i < schema.length; i++){
                        $('#attr-'+ID).append('<option>'+schema[i]+'</option>')
                        $('#schema-calculator-'+ID).append('<li class="nav-item"><a class="nav-link active">'+schema[i]+'</a></li>')
                    }
                //this else only for this transformer for selecting attributes
                }else{
                    schema = schemaEdge
                    $('#schema-calculator-'+ID).empty()
                    for (i = 0; i < schema.length; i++){
                        $('#schema-calculator-'+ID).append('<li class="nav-item"><a class="nav-link active">'+schema[i]+'</a></li>')
                    }
                }

            },100);

            $(document).off("dblclick", "#schema-calculator-"+ID+" > li > a")

            $(document).on("dblclick", "#schema-calculator-"+ID+" > li > a", function(){
                var text = '"'+this.text+'"'
                var textarea = document.getElementById('expression-'+ID)
                
                if (textarea.value.charAt(textarea.value.length-1) == ')'){

                    textarea.value = textarea.value.substring(0,textarea.value.length-1) + text + ')'

                }else{

                    textarea.value = textarea.value + text

                }
             });
             
            $(document).off("dblclick", "#functions-"+ID+" > li > a")

            $(document).on("dblclick", "#functions-"+ID+" > li > a", function(){
                var text = this.name
                var textarea = document.getElementById('expression-'+ID)
                textarea.value = textarea.value + text
                var end = textarea.selectionEnd;
                
                if (textarea.value.charAt(textarea.value.length-1) == ')'){

                    textarea.focus()
                    textarea.selectionEnd= end - 1;

                };

            });
             
            
            $('#dialog-calculator-'+ID).modal('show')

            $('#calculator-accept-'+ID).click(function() {

                var paramsCalculator = {"id": ID,
                "parameters": [
                    {"attr": $('#attr-'+ID).val(),
                    "expression": $('#expression-'+ID).val()}
                ]}
               
                paramsCalculator['schema'] = schema
                paramsCalculator['schema-old'] = schemaEdge

                passSchemaToEdgeConnected(ID, listLabel, schema, context.canvas)
                isAlreadyInCanvas(jsonParams, paramsCalculator, ID)

                icon.setColor('#4682B4')
                
                $('#dialog-calculator-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Output"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

	     var output= label2.createPort("output");
         output.setName("output_"+label2.id);

	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
	     }
	     else{
             this.add(label1);
             this.add(label2);
         }
         
         listLabel.push([this.id,[input.name], [output.name]])

	     return label1, label2;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     

     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes :getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 
                 entity.id = e.id;
                 
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// EXECUTE SQL Postgres///

trans_ExecuteSQL = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_ExecuteSQL",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Execute SQL"), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-execute-sql-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext('Execute SQL Parameters')+'</h4>'+
                    '</div>'+
                    '<div  class="modal-body">'+
                        '<form>'+
                        
                            '<div class="column50">'+
                                '<label form="host" class="col-form-label">'+gettext('Host:')+'</label>'+
                                '<input id="host-'+ID+'" type="text" value="localhost" size="40" class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                            '<div class="column50">'+    
                                '<label form="port" class="col-form-label">'+gettext('Port:')+'</label>'+
                                '<input id="port-'+ID+'" type="text" value="5432" size="40" class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label form="database" class="col-form-label">'+gettext('Database:')+'</label>'+
                                '<input id="database-'+ID+'" type="text" value="" size="40" class="form-control" pattern="[A-Za-z]{3}" placeholder="'+gettext('Name of your database')+'">'+
                            '</div>'+
                            '<div class="column50">'+                                
                                '<label form="user" class="col-form-label">'+gettext('User:')+'</label>'+
                                '<input id="user-'+ID+'" type="text" value="postgres" size="40"  class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label form="password" class="col-form-label">'+gettext('Password:')+'</label>'+
                                '<input type="password" id = "password-'+ID+'" class="form-control" value="">'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label form="tablename" class="col-form-label">'+gettext('Table name:')+'</label>'+
                                '<input id="tablename-'+ID+'" type="text" value="" size="40" class="form-control" pattern="[A-Za-z]{3}" placeholder="'+gettext('schema.tablename')+'">'+
                            '</div>'+

                            '<div class="right">'+
                                '<button type="button" class="btn btn-default btn-sm" id="get-schema-'+ID+'">'+gettext('Get attributes')+'</button>'+
                            '</div>'+
                            
                            '<div class="column50">'+
                                '<label class="col-form-label">'+gettext('Attributes from input:')+'</label>'+
                                '<div id ="attrs-values">'+
                                    '<ul id ="attrs-values-'+ID+'" class="nav flex-column" style= "height:100px;">'+
                                    '</ul>'+
                                '</div>'+
                            '</div>'+

                            '<div class="column50">'+
                                '<label class="col-form-label">'+gettext('Attributes from new connection:')+'</label>'+
                                '<div id ="attrs-execute-sql">'+
                                    '<ul id ="attrs-execute-sql-'+ID+'" class="nav flex-column" style= "height:100px;">'+
                                    '</ul>'+
                                '</div>'+
                            '</div>'+

                            '<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>'+

                            '<div>'+
                                '<label class="col-form-label">'+gettext('Query:')+'</label>'+
                                '<textarea id="query-'+ID+'" rows="4" class="form-control" ></textarea>'+
                            '</div>'+   
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="verify-postgis-'+ID+'">'+gettext('Verify connection')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="execute-sql-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        $('#verify-postgis-'+ID).click(function() {
                
            var paramsPostgres = {"id": ID,
                "parameters": [
                    {"host": $('#host-'+ID).val(),
                    "port": $('#port-'+ID).val(),
                    "database": $('#database-'+ID).val(),
                    "user": $('#user-'+ID).val(),
                    "password": $('#password-'+ID).val()}
                ]}
    
                var formDataPostgres = new FormData();
                
                formDataPostgres.append('jsonParamsPostgres', JSON.stringify(paramsPostgres))
    
                $.ajax({
                    type: 'POST',
                    url: '/gvsigonline/etl/test_postgres_conexion/',
                    data: formDataPostgres,
                    beforeSend:function(xhr){
                        xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
                    },
                    cache: false, 
                    contentType: false, 
                    processData: false,
                    success: function (response) {
    
                        if(response.result == true){
                            textConnection = gettext('Connection parameters are valids.')
                        }else{
                            textConnection = gettext('Connection parameters are not valids.')
                        }
    
                        $("#dialog-test-postgres-connection").remove();
                            
                        $('#canvas-parent').append('<div id="dialog-test-postgres-connection" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
                            '<div class="modal-dialog" role="document">'+
                                '<div class="modal-content">'+
                                    '<div class="modal-header">'+
                                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                                            '<span aria-hidden="true">&times;</span>'+
                                        '</button>'+
                                        '<h4 class="modal-title">'+gettext('Response')+'</h4>'+
                                    '</div>'+
                                    '<div class="modal-body" align="center">'+textConnection+
                                    '</div>'+
                                    '<div class="modal-footer">'+
                                        '<button id= "close-test-postgres-connection" type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                                    '</div>'+
                                '</div>'+
                            '</div>'+
                        '</div>')
    
                        $('#dialog-test-postgres-connection').modal('show')
    
                        $('#close-test-postgres-connection').click(function() {
                            
                            $('#dialog-test-postgres-connection').modal('hide')
                            
                        })
                    }
                })
        });

        $('#get-schema-'+ID).click(function() {
            
            var paramsPostgis = {"id": ID,
            "parameters": [
                {"host": $('#host-'+ID).val(),
                "port": $('#port-'+ID).val(),
                "database": $('#database-'+ID).val(),
                "user": $('#user-'+ID).val(),
                "password": $('#password-'+ID).val(),
                "tablename": $('#tablename-'+ID).val()}
            ]}

            var formDataSchemaPostgis = new FormData();
            
            formDataSchemaPostgis.append('jsonParamsPostgres', JSON.stringify(paramsPostgis))

            $.ajax({
                type: 'POST',
                url: '/gvsigonline/etl/etl_schema_postgresql/',
                data: formDataSchemaPostgis,
                beforeSend:function(xhr){
                    xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
                },
                cache: false, 
                contentType: false, 
                processData: false,
                success: function (data) {

                    $('#attrs-execute-sql-'+ID).empty()

                    for (i = 0; i < data.length; i++){
                        $('#attrs-execute-sql-'+ID).append('<li class="nav-item"><a class="nav-link active">'+data[i]+'</a></li>')
                    }
                }
            })
        })
        
        context = this

        icon.on("click", function(){
            
            setTimeout(function(){
                try{
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                    
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge

                    $('#attrs-values-'+ID).empty()

                    for (i = 0; i < schema.length; i++){
                        $('#attrs-values-'+ID).append('<li class="nav-item"><a class="nav-link active">'+schema[i]+'</a></li>')
                    }
                //this "else" is only for this transformer for selecting attributes
                }else{
                    schema = schemaEdge
                    $('#attrs-values-'+ID).empty()
                    for (i = 0; i < schema.length; i++){
                        $('#attrs-values-'+ID).append('<li class="nav-item"><a class="nav-link active">'+schema[i]+'</a></li>')
                    }
                }

            },100);

            $(document).off("dblclick", "#attrs-values-"+ID+" > li > a")

            $(document).on("dblclick", "#attrs-values-"+ID+" > li > a", function(){
                var text = '##"'+this.text+'"##'
                var textarea = document.getElementById('query-'+ID)
                textarea.value = textarea.value + text

            });

             $(document).off("dblclick", "#attrs-execute-sql-"+ID+" > li > a")

             $(document).on("dblclick", "#attrs-execute-sql-"+ID+" > li > a", function(){
                 var text = '"'+this.text+'"'
                 var textarea = document.getElementById('query-'+ID)
                 textarea.value = textarea.value + text
 
            });
            
            $('#dialog-execute-sql-'+ID).modal('show')

            $('#execute-sql-accept-'+ID).click(function() {

                var paramsExecute= {"id": ID,
                "parameters": [
                    {"host": $('#host-'+ID).val(),
                    "port": $('#port-'+ID).val(),
                    "database": $('#database-'+ID).val(),
                    "user": $('#user-'+ID).val(),
                    "password": $('#password-'+ID).val(),
                    "tablename": $('#tablename-'+ID).val(),
                    "query": $('#query-'+ID).val()}
                ]}
    
                var formDataSchemaExecute = new FormData();
                
                formDataSchemaExecute.append('jsonParamsPostgres', JSON.stringify(paramsExecute))
    
                $.ajax({
                    type: 'POST',
                    url: '/gvsigonline/etl/etl_schema_postgresql/',
                    data: formDataSchemaExecute,
                    beforeSend:function(xhr){
                        xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
                    },
                    cache: false, 
                    contentType: false, 
                    processData: false,
                    success: function (data) {

                        schemaMod =[...schemaEdge]
                        
                        for (i = 0; i < data.length; i++){
                            schemaMod.push(data[i])
                        }
                        
                        paramsExecute['schema'] = schemaMod
                        paramsExecute['schema-old'] = schemaEdge

                    }
                })
               


                passSchemaToEdgeConnected(ID, listLabel, schema, context.canvas)
                isAlreadyInCanvas(jsonParams, paramsExecute, ID)

                icon.setColor('#4682B4')
                
                $('#dialog-execute-sql-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Output"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

	     var output= label2.createPort("output");
         output.setName("output_"+label2.id);

	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
	     }
	     else{
             this.add(label1);
             this.add(label2);
         }
         
         listLabel.push([this.id,[input.name], [output.name]])

	     return label1, label2;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     

     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes :getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 
                 entity.id = e.id;
                 
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// CREATE ATTRIBUTE ////

trans_CreateAttr = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_CreateAttr",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Create Attribute"), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-create-attr-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext("Create Attribute Parameters")+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column40">'+
                                '<label class="col-form-label">'+gettext("New attribute:")+'</label>'+
                                '<input id="attr-'+ID+'" type="text" size="40" value="_newattr" class="form-control" pattern="[A-Za-z]{3}" placeholder="'+gettext('New attribute name')+'">'+
                            '</div>'+
                            '<div class="column20">'+
                                '<label class="col-form-label">'+gettext('Data type:')+'</label>'+
                                '<select class="form-control" id="data-type-'+ID+'">'+
                                    '<option value="VARCHAR"> Varchar </option>'+
                                    '<option value="INTEGER"> Integer </option>'+
                                    '<option value="FLOAT"> Float </option>'+
                                '</select>'+
                            '</div>'+     
                            '<div class="column40">'+
                                '<label class="col-form-label">'+gettext("Value:")+'</label>'+
                                '<input id="value-'+ID+'" type="text" size="40" value="" class="form-control" pattern="[A-Za-z]{3}" placeholder="'+gettext('New attribute value')+'">'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="create-attr-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')
        
        context = this

        icon.on("click", function(){
            
            setTimeout(function(){
                try{
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)
                schema = schemaEdge

            },100);
            

            $('#dialog-create-attr-'+ID).modal('show')

            $('#create-attr-accept-'+ID).click(function() {

                var paramsCreateAttr = {"id": ID,
                "parameters": [
                    {"attr": $('#attr-'+ID).val(),
                    "value": $('#value-'+ID).val(),
                    "data-type": $('#data-type-'+ID).val()}
                ]}
                
                schemaMod =[...schemaEdge]
                
                schemaMod.push($('#attr-'+ID).val())
               
                paramsCreateAttr['schema'] = schemaMod

                passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)
                isAlreadyInCanvas(jsonParams, paramsCreateAttr, ID)

                icon.setColor('#4682B4')
                
                $('#dialog-create-attr-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Output"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

	     var output= label2.createPort("output");
         output.setName("output_"+label2.id);

	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
	     }
	     else{
             this.add(label1);
             this.add(label2);
         }
         
         listLabel.push([this.id,[input.name], [output.name]])

	     return label1, label2;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },

     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes :getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// FILTERING////

trans_Filter = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_Filter",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
        
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Filter"), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-filter-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext('Filter Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column40">'+
                                '<label form="attr" class="col-form-label">'+gettext('Attribute:')+'</label>'+
                                '<select class="form-control" id="attr-'+ID+'"> </select>'+
                            '</div>'+
                            '<div class="column20">'+
                                '<label class="col-form-label">'+gettext('Operator:')+'</label>'+
                                '<select class="form-control" id="operator-'+ID+'">'+
                                    '<option value="="> = </option>'+
                                    '<option value="!="> != </option>'+
                                    '<option value="<"> < </option>'+
                                    '<option value=">"> > </option>'+
                                    '<option value="<="> <= </option>'+
                                    '<option value=">="> >= </option>'+
                                    '<option value="starts-with">'+gettext('Starts with')+'</option>'+
                                    '<option value="ends-with">'+gettext('Ends with')+'</option>'+
                                    '<option value="contains">'+gettext('Contains')+'</option>'+
                                '</select>'+
                            '</div>'+                           
                            '<div class="column40">'+
                                '<label form="value" class="col-form-label">'+gettext('Value:')+'</label>'+
                                '<input id="value-'+ID+'" type="text" size="40" value="" class="form-control" pattern="[A-Za-z]{3}" placeholder="'+gettext('New attribute value')+'">'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="filter-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        context = this

        icon.on("click", function(){
            setTimeout(function(){
                try{
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge

                    $('#attr-'+ID).empty()

                    for (i = 0; i < schema.length; i++){
                        
                        $('#attr-'+ID).append('<option>'+schema[i]+'</option>')
                    }
                }

            },100);

            $('#dialog-filter-'+ID).modal('show')

            $('#filter-accept-'+ID).click(function() {

                var paramsFilter = {"id": ID,
                "parameters": [
                {"attr": $('#attr-'+ID).val(),
                "operator": $('#operator-'+ID).val(),
                "value": $('#value-'+ID).val()}
                ]}
                
                paramsFilter['schema-old'] = schemaEdge
                paramsFilter['schema'] = schema

                passSchemaToEdgeConnected(ID, listLabel, schema, context.canvas)

                isAlreadyInCanvas(jsonParams, paramsFilter, ID)

                icon.setColor('#4682B4')
                
                $('#dialog-filter-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("True"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

        var label3 =new draw2d.shape.basic.Label({
            text:gettext("False"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

         var output1 = label2.createPort("output");
         output1.setName("output_"+label2.id);

	     var output2= label3.createPort("output");
         output2.setName("output_"+label3.id);


	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
             this.add(label3, null, optionalIndex+1);

	     }
	     else{
             this.add(label1);
             this.add(label2);
             this.add(label3);
         }
         
         listLabel.push([this.id, [input.name], [output1.name, output2.name]])

	     return label1, label2, label3;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes : getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// INTERSECTION ////

trans_Intersection = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_Intersection",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
        
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Intersection"), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-intersection-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext('Intersection Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<input type="checkbox" name="merge" id="merge-'+ID+'" value=""/>'+
                                '<label for="checkbox">'+gettext('Merge attributes of the secondary input to the final output')+'</label>'+                         
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="intersection-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        context = this

        icon.on("click", function(){
            setTimeout(function(){
                try{
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

            },100);

            $('#dialog-intersection-'+ID).modal('show')

            $('#intersection-accept-'+ID).click(function() {

                

                if ($('#merge-'+ID).is(':checked')) {
                    $('#merge-'+ID).val('true')

                    if (Array.isArray(schemaEdge[0])){

                        chars = schemaEdge[0].concat(schemaEdge[1])

                        let unique = chars.filter((c, index) => {
                            return chars.indexOf(c) === index;
                        });

                        schemaMod = unique

                    }
                    else{
                        schemaMod = [...schemaEdge]
                    }

                }else{

                    $('#merge-'+ID).val('')

                    if (Array.isArray(schemaEdge[0])){
                        schemaMod = schemaEdge[0]
                    }
                    else{
                        schemaMod = [...schemaEdge]
                    }
                }

                var paramsInter = {"id": ID,
                "parameters": [
                {"merge": $('#merge-'+ID).val(),
                "schema": schemaEdge}
                ]}

                paramsInter['schema-old'] = schemaEdge
                paramsInter['schema'] = schemaMod

                passSchemaToEdgeConnected(ID, listLabel, schema, context.canvas)

                isAlreadyInCanvas(jsonParams, paramsInter, ID)

                icon.setColor('#4682B4')
                
                $('#dialog-intersection-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Main"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Second."),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:10, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

        var label3 =new draw2d.shape.basic.Label({
            text:gettext("Output"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

         var input2 = label2.createPort("input");
         input2.setName("input_"+label2.id);

	     var output= label3.createPort("output");
         output.setName("output_"+label3.id);


	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
             this.add(label3, null, optionalIndex+1);

	     }
	     else{
             this.add(label1);
             this.add(label2);
             this.add(label3);
         }
         
         listLabel.push([this.id, [input.name, input2.name], [output.name]])

	     return label1, label2, label3;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes : getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// SPATIALLY RELATE ////

trans_SpatialRel = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_SpatialRel",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
        
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Spatial Relation"), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-spatial-rel-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext('Spatial Relation Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<label class="col-form-label">'+gettext('Spatial relation')+'</label>'+
                                '<select class="form-control" id="rel-'+ID+'">'+
                                    '<option value="ST_CONTAINS"> Main Contains Secondary</option>'+
                                    '<option value="ST_EQUALS"> Main Equals Secondary</option>'+
                                    '<option value="ST_INTERSECTS"> Main Intersects Secondary</option>'+
                                    '<option value="ST_TOUCHES"> Main Touches Secondary</option>'+                                    
                                    '<option value="ST_WITHIN"> Main Within Secondary</option>'+
                                '</select>'+                  
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="spatial-rel-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        context = this

        icon.on("click", function(){
            setTimeout(function(){
                try{
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

            },100);

            $('#dialog-spatial-rel-'+ID).modal('show')

            $('#spatial-rel-accept-'+ID).click(function() {

                var paramsSpatialRel = {"id": ID,
                "parameters": [
                {"rel": $('#rel-'+ID).val()}
                ]}
                
                schemaMod =[...schemaEdge[0]]
                
                schemaMod.push('_related')
               
                paramsSpatialRel['schema-old'] = schemaEdge
                paramsSpatialRel['schema'] = schemaMod

                passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)

                isAlreadyInCanvas(jsonParams, paramsSpatialRel, ID)

                icon.setColor('#4682B4')
                
                $('#dialog-spatial-rel-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Main"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Second."),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:10, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

        var label3 =new draw2d.shape.basic.Label({
            text:gettext("Output"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

         var input2 = label2.createPort("input");
         input2.setName("input_"+label2.id);

	     var output= label3.createPort("output");
         output.setName("output_"+label3.id);


	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
             this.add(label3, null, optionalIndex+1);

	     }
	     else{
             this.add(label1);
             this.add(label2);
             this.add(label3);
         }
         
         listLabel.push([this.id, [input.name, input2.name], [output.name]])

	     return label1, label2, label3;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes : getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

/// KEEP ATTRIBUTE ////

trans_KeepAttr = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_KeepAttr",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
        
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Keep Attribute"), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-keep-attr-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext("Keep Attribute Parameters")+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<label form="attr" class="col-form-label">'+gettext("Attribute to keep:")+'</label>'+
                            '<select class="form-control" size = "8" multiple id="attr-'+ID+'"> </select>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext("Close")+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="keep-attr-accept-'+ID+'">'+gettext("Accept")+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        context = this

        icon.on("click", function(){

            setTimeout(function(){
                try{
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge
                    $('#attr-'+ID).empty()

                    for (i = 0; i < schema.length; i++){
                        $('#attr-'+ID).append('<option>'+schema[i]+'</option>')
                    }

                }

            },100);

            $('#dialog-keep-attr-'+ID).modal('show')

            $('#keep-attr-accept-'+ID).click(function() {

                var paramsKeep = {"id": ID,
                "parameters": [
                    {"attr": $('#attr-'+ID).val()}
                ]}

                schemaMod =$('#attr-'+ID).val()

                paramsKeep['schema-old'] = schemaEdge
                paramsKeep['schema'] = schemaMod

                passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)
                
                isAlreadyInCanvas(jsonParams, paramsKeep, ID)

                icon.setColor('#4682B4')
                
                $('#dialog-keep-attr-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Output"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

	     var output= label2.createPort("output");
         output.setName("output_"+label2.id);

	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
	     }
	     else{
             this.add(label1);
             this.add(label2);
	     }

         listLabel.push([this.id, [input.name], [output.name]])

	     return label1, label2;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes :getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// REPROJECT ////

trans_Reproject = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_Reproject",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
        
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Reproject"), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        //adding dialog for choosing parameters of the transformer
        $('#canvas-parent').append('<div id="dialog-reproject-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext('Reproject Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column50">'+
                                '<label class="col-form-label">'+gettext("Source EPSG:")+'</label>'+
                                '<select id="source-epsg-'+ID+'" class="form-control">'+
                                '<option value="">'+gettext("Empty to read from input layer")+'</option>'+
                                '</select>'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label class="col-form-label">'+gettext("Target EPSG:")+'</label>'+
                                '<select id="target-epsg-'+ID+'" class="form-control">'+ 
                                '<option value="">------</option>'+
                                '</select>'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="reproject-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        for(i=0;i<srs.length;i++){

            epsg = srs[i].code.split(":")[1]

            $('#source-epsg-'+ID).append(
                '<option value="'+epsg+'">'+srs[i].code+' - '+srs[i].title+'</option>'
            );

            $('#target-epsg-'+ID).append(
                '<option value="'+epsg+'">'+srs[i].code+' - '+srs[i].title+'</option>'
            );

        }

        context = this

        icon.on("click", function(){

            setTimeout(function(){
                
                try{
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                //get schema from the edge
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

            },100);
            

            $('#dialog-reproject-'+ID).modal('show')

            $('#reproject-accept-'+ID).click(function() {

                //parameters selected to json
                var paramsReproject = {"id": ID,
                "parameters": [
                {"source-epsg": $('#source-epsg-'+ID).val(),
                "target-epsg": $('#target-epsg-'+ID).val() }
                ]}
                
                //updating schema-old and schema parameters in json
                paramsReproject['schema-old'] = schemaEdge
                paramsReproject['schema'] = schemaEdge

                //add the schema to a later edge if it exists
                passSchemaToEdgeConnected(ID, listLabel, schemaEdge, context.canvas)
                
                //check if parameters are already in json canvas
                isAlreadyInCanvas(jsonParams, paramsReproject, ID)

                //set red color to another in order to know if parameters are checked
                icon.setColor('#4682B4')
                
                $('#dialog-reproject-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Output"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

	     var output= label2.createPort("output");
         output.setName("output_"+label2.id);

	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
	     }
	     else{
             this.add(label1);
             this.add(label2);
         }
         
         listLabel.push([this.id, [input.name], [output.name]])

	     return label1, label2;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes :getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// GET CADASTRAL GEOMETRY ////

trans_CadastralGeom = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_CadastralGeom",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Cadastral Geom."), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        context = this
        
        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        //adding dialog for choosing parameters of the transformer
        $('#canvas-parent').append('<div id="dialog-cadastral-geom-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext('Cadastral Geometry Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<label form="attr" class="col-form-label">'+gettext('Cadastral Reference Attribute:')+'</label>'+
                            '<select class="form-control" id="attr-'+ID+'"> </select>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="cadastral-geom-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        icon.on("click", function(){

            setTimeout(function(){
                
                try{
                    // if it's not the first time opening parameters dialog
                    //json figure task will has already the schemas
                    //old is the schema that came from the edge
                    //the other one is result schema depending of parameters chosen
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                //get schema from the edge
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                //if edge schema and old schema is not the same is the first time you open parameters or
                //something was changed in the edge so we hace to create a new schema option
                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge
                    $('#attr-'+ID).empty()

                    for (i = 0; i < schema.length; i++){
                        
                        $('#attr-'+ID).append('<option>'+schema[i]+'</option>')
                    }
                }

            },100);
            

            $('#dialog-cadastral-geom-'+ID).modal('show')

            $('#cadastral-geom-accept-'+ID).click(function() {

                //parameters selected to json
                var paramsCadGeom = {"id": ID,
                "parameters": [
                {"attr": $('#attr-'+ID).val()}
                ]}

                //updating schema-old and schema parameters in json
                paramsCadGeom['schema-old'] = schemaEdge
                paramsCadGeom['schema'] = schemaEdge

                //add the schema to a later edge if it exists
                passSchemaToEdgeConnected(ID, listLabel, schemaEdge, context.canvas)
                
                //check if parameters are already in json canvas
                isAlreadyInCanvas(jsonParams, paramsCadGeom, ID)

                //set red color to another in order to know if parameters are checked
                icon.setColor('#4682B4')
                
                $('#dialog-cadastral-geom-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Output"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

	     var output= label2.createPort("output");
         output.setName("output_"+label2.id);

	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
	     }
	     else{
             this.add(label1);
             this.add(label2);
         }
         
         listLabel.push([this.id, [input.name], [output.name]])

	     return label1, label2;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes :getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});


//// MGRS ////

trans_MGRS = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_MGRS",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("MGRS"), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        context = this
        
        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        //adding dialog for choosing parameters of the transformer
        $('#canvas-parent').append('<div id="dialog-mgrs-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext('MGRS Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<label form="attr" class="col-form-label">'+gettext('Select mode:')+'</label>'+
                            '<select class="form-control" id="select-mgrs'+ID+'">'+
                                '<option value="mgrstolatlon" selected>'+gettext('MGRS to geographic coordinates:')+'</option>'+
                                '<option value="latlontomgrs">'+gettext('Geographic coordinates to MGRS:')+'</option>'+
                            '</select>'+
                            '<div class="column50">'+
                                '<label form="attr" class="col-form-label">'+gettext('MGRS grid attribute:')+'</label>'+
                                '<select class="form-control" id="mgrs-'+ID+'"> </select>'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label form="attr" class="col-form-label">'+gettext('Longitude attribute:')+'</label>'+
                                '<select class="form-control" id="lon-'+ID+'"> </select>'+
                                '<label form="attr" class="col-form-label">'+gettext('Latitude attribute:')+'</label>'+
                                '<select class="form-control" id="lat-'+ID+'"> </select>'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="mgrs-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        $('#mgrs-'+ID).attr('disabled', false)
        $('#lon-'+ID).attr('disabled', true)
        $('#lat-'+ID).attr('disabled', true)

        $('#select-mgrs'+ID).on('change', function() {
            
            if (this.value=='mgrstolatlon'){
                $('#mgrs-'+ID).attr('disabled', false)
                $('#lon-'+ID).attr('disabled', true)
                $('#lat-'+ID).attr('disabled', true)
            }
            if (this.value=='latlontomgrs'){
                $('#mgrs-'+ID).attr('disabled', true)
                $('#lon-'+ID).attr('disabled', false)
                $('#lat-'+ID).attr('disabled', false)
            }
        });
       

        icon.on("click", function(){

            setTimeout(function(){
                
                try{
                    // if it's not the first time opening parameters dialog
                    //json figure task will has already the schemas
                    //old is the schema that came from the edge
                    //the other one is result schema depending of parameters chosen
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                //get schema from the edge
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                //if edge schema and old schema is not the same is the first time you open parameters or
                //something was changed in the edge so we hace to create a new schema option
                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge
                    $('#mgrs-'+ID).empty()
                    $('#lon-'+ID).empty()
                    $('#lat-'+ID).empty()

                    for (i = 0; i < schema.length; i++){
                        
                        $('#mgrs-'+ID).append('<option>'+schema[i]+'</option>')
                        $('#lon-'+ID).append('<option>'+schema[i]+'</option>')
                        $('#lat-'+ID).append('<option>'+schema[i]+'</option>')
                    }
                }

            },100);

            $('#dialog-mgrs-'+ID).modal('show')

            $('#mgrs-accept-'+ID).click(function() {

                //parameters selected to json
                var paramsMGRS = {"id": ID,
                    "parameters": [
                        {"select": $("#select-mgrs"+ID).val(),
                        "mgrs": $('#mgrs-'+ID).val(),
                        "lon": $('#lon-'+ID).val(),
                        "lat": $('#lat-'+ID).val()}
                    ]
                };

                schemaMod =[...schemaEdge]
                
                if ($('#select-mgrs'+ID).val()=='mgrstolatlon'){
                    schemaMod.push("_lon", "_lat")
                }else{
                    schemaMod.push("_mgrs_grid")
                }
                
                //updating schema-old and schema parameters in json
                paramsMGRS['schema-old'] = schemaEdge
                paramsMGRS['schema'] = schemaMod

                //add the schema to a later edge if it exists
                passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)
                
                //check if parameters are already in json canvas
                isAlreadyInCanvas(jsonParams, paramsMGRS, ID)

                //set red color to another in order to know if parameters are checked
                icon.setColor('#4682B4')
                
                $('#dialog-mgrs-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Output"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

	     var output= label2.createPort("output");
         output.setName("output_"+label2.id);

	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
	     }
	     else{
             this.add(label1);
             this.add(label2);
         }
         
         listLabel.push([this.id, [input.name], [output.name]])

	     return label1, label2;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes :getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});



//// Convert Text to Point ////

trans_TextToPoint = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_TextToPoint",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Text to Point"), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        context = this
        
        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        //adding dialog for choosing parameters of the transformer
        $('#canvas-parent').append('<div id="dialog-texttoepsg-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext('Text to Point Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column33">'+
                                '<label form="attr" class="col-form-label">'+gettext('Longitude attribute:')+'</label>'+
                                '<select class="form-control" id="lon-'+ID+'"> </select>'+
                            '</div>'+
                            '<div class="column33">'+
                                '<label form="attr" class="col-form-label">'+gettext('Latitude attribute:')+'</label>'+
                                '<select class="form-control" id="lat-'+ID+'"> </select>'+
                            '</div>'+
                            '<div class="column33">'+
                                '<label form="attr" class="col-form-label">'+gettext('Insert EPSG:')+'</label>'+
                                '<select id="epsg-'+ID+'" class="form-control">'+ 
                                    '<option value="">----</option>'+
                                '</select>'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="texttoepsg-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')


        for(i=0;i<srs.length;i++){

            epsg = srs[i].code.split(":")[1]

            $('#epsg-'+ID).append(
                '<option value="'+epsg+'">'+srs[i].code+' - '+srs[i].title+'</option>'
            );
        }

        icon.on("click", function(){

            setTimeout(function(){
                
                try{
                    // if it's not the first time opening parameters dialog
                    //json figure task will has already the schemas
                    //old is the schema that came from the edge
                    //the other one is result schema depending of parameters chosen
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                //get schema from the edge
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                //if edge schema and old schema is not the same is the first time you open parameters or
                //something was changed in the edge so we hace to create a new schema option
                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge

                    $('#lon-'+ID).empty()
                    $('#lat-'+ID).empty()

                    for (i = 0; i < schema.length; i++){
                        
                        $('#lon-'+ID).append('<option>'+schema[i]+'</option>')
                        $('#lat-'+ID).append('<option>'+schema[i]+'</option>')
                    }
                }

            },100);

            $('#dialog-texttoepsg-'+ID).modal('show')

            $('#texttoepsg-accept-'+ID).click(function() {

                //parameters selected to json
                var paramsTextToPoint = {"id": ID,
                    "parameters": [
                        {"epsg": $('#epsg-'+ID).val(),
                        "lon": $('#lon-'+ID).val(),
                        "lat": $('#lat-'+ID).val()}
                    ]
                };
                
                schemaMod =[...schemaEdge]
                
                //updating schema-old and schema parameters in json
                paramsTextToPoint['schema-old'] = schemaEdge
                paramsTextToPoint['schema'] = schemaMod

                //add the schema to a later edge if it exists
                passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)
                
                //check if parameters are already in json canvas
                isAlreadyInCanvas(jsonParams, paramsTextToPoint, ID)

                //set red color to another in order to know if parameters are checked
                icon.setColor('#4682B4')
                
                $('#dialog-texttoepsg-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Output"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

	     var output= label2.createPort("output");
         output.setName("output_"+label2.id);

	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
	     }
	     else{
             this.add(label1);
             this.add(label2);
         }
         
         listLabel.push([this.id, [input.name], [output.name]])

	     return label1, label2;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes :getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// WKT to GEOMetry ////

trans_WktGeom = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_WktGeom",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("WKT Geom."), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        context = this
        
        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        //adding dialog for choosing parameters of the transformer
        $('#canvas-parent').append('<div id="dialog-wkt-geom-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext('WKT to Geometry Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column66">'+
                                '<label form="attr" class="col-form-label">'+gettext('WKT string Attribute:')+'</label>'+
                                '<select class="form-control" id="attr-'+ID+'"> </select>'+
                            '</div>'+
                            '<div class="column33">'+
                                '<label form="attr" class="col-form-label">'+gettext('Insert EPSG:')+'</label>'+
                                '<select id="epsg-'+ID+'" class="form-control">'+ 
                                    '<option value="">----</option>'+
                                '</select>'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="wkt-geom-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')
        
        for(i=0;i<srs.length;i++){

            epsg = srs[i].code.split(":")[1]

            $('#epsg-'+ID).append(
                '<option value="'+epsg+'">'+srs[i].code+' - '+srs[i].title+'</option>'
            );
        }
        
        icon.on("click", function(){

            setTimeout(function(){
                
                try{
                    // if it's not the first time opening parameters dialog
                    //json figure task will has already the schemas
                    //old is the schema that came from the edge
                    //the other one is result schema depending of parameters chosen
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                //get schema from the edge
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                //if edge schema and old schema is not the same is the first time you open parameters or
                //something was changed in the edge so we hace to create a new schema option
                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge
                    $('#attr-'+ID).empty()

                    for (i = 0; i < schema.length; i++){
                        
                        $('#attr-'+ID).append('<option>'+schema[i]+'</option>')
                    }
                }

            },100);

            $('#dialog-wkt-geom-'+ID).modal('show')

            $('#wkt-geom-accept-'+ID).click(function() {

                //parameters selected to json
                var paramsWktGeom = {"id": ID,
                "parameters": [
                {"attr": $('#attr-'+ID).val(),
                "epsg": $('#epsg-'+ID).val()}
                ]}

                schemaMod =[...schemaEdge]
                schemaMod.splice($('#attr-'+ID).prop('selectedIndex'), 1)

                //updating schema-old and schema parameters in json
                paramsWktGeom['schema-old'] = schemaEdge
                paramsWktGeom['schema'] = schemaMod

                //add the schema to a later edge if it exists
                passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)
                
                //check if parameters are already in json canvas
                isAlreadyInCanvas(jsonParams, paramsWktGeom, ID)

                //set red color to another in order to know if parameters are checked
                icon.setColor('#4682B4')
                
                $('#dialog-wkt-geom-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Output"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

	     var output= label2.createPort("output");
         output.setName("output_"+label2.id);

	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
	     }
	     else{
             this.add(label1);
             this.add(label2);
         }
         
         listLabel.push([this.id, [input.name], [output.name]])

	     return label1, label2;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes :getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// Split Attribute////

trans_SplitAttr = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_SplitAttr",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Split Attribute"), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        context = this
        
        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        //adding dialog for choosing parameters of the transformer
        $('#canvas-parent').append('<div id="dialog-split-attr-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext('Split Attribute Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column33">'+
                                '<label form="attr" class="col-form-label">'+gettext('String Attribute:')+'</label>'+
                                '<select class="form-control" id="attr-'+ID+'"> </select>'+
                            '</div>'+
                            '<div class="column33">'+
                                '<label form="attr" class="col-form-label">'+gettext('List Name:')+'</label>'+
                                '<input id="list-'+ID+'" type="text" value="_list" size="40" class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                            '<div class="column33">'+
                                '<label form="attr" class="col-form-label">'+gettext('Split by:')+'</label>'+
                                '<input id="split-'+ID+'" type="text" value="" size="40" class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="split-attr-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')
        
        
        icon.on("click", function(){

            setTimeout(function(){
                
                try{
                    // if it's not the first time opening parameters dialog
                    //json figure task will has already the schemas
                    //old is the schema that came from the edge
                    //the other one is result schema depending of parameters chosen
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                //get schema from the edge
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                //if edge schema and old schema is not the same is the first time you open parameters or
                //something was changed in the edge so we hace to create a new schema option
                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge
                    $('#attr-'+ID).empty()

                    for (i = 0; i < schema.length; i++){
                        
                        $('#attr-'+ID).append('<option>'+schema[i]+'</option>')
                    }
                }

            },100);

            $('#dialog-split-attr-'+ID).modal('show')

            $('#split-attr-accept-'+ID).click(function() {

                //parameters selected to json
                var paramsSplitAttr = {"id": ID,
                "parameters": [
                {"attr": $('#attr-'+ID).val(),
                "list": $('#list-'+ID).val(),
                "split": $('#split-'+ID).val()}
                ]}

                schemaMod =[...schemaEdge]
                schemaMod.splice($('#attr-'+ID).prop('selectedIndex'), 1)
                schemaMod.push($('#list-'+ID).val())

                //updating schema-old and schema parameters in json
                paramsSplitAttr['schema-old'] = schemaEdge
                paramsSplitAttr['schema'] = schemaMod


                //add the schema to a later edge if it exists
                passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)
                
                //check if parameters are already in json canvas
                isAlreadyInCanvas(jsonParams, paramsSplitAttr, ID)

                //set red color to another in order to know if parameters are checked
                icon.setColor('#4682B4')
                
                $('#dialog-split-attr-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Output"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

	     var output= label2.createPort("output");
         output.setName("output_"+label2.id);

	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
	     }
	     else{
             this.add(label1);
             this.add(label2);
         }
         
         listLabel.push([this.id, [input.name], [output.name]])

	     return label1, label2;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes :getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// Explode List////

trans_ExplodeList = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_ExplodeList",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Explode List"),
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        context = this
        
        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        //adding dialog for choosing parameters of the transformer
        $('#canvas-parent').append('<div id="dialog-explode-list-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext('Explode List Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column33">'+
                                '<label form="list" class="col-form-label">'+gettext('List Name:')+'</label>'+
                                '<select class="form-control" id="list-'+ID+'"> </select>'+
                            '</div>'+
                            '<div class="column33">'+
                                '<label form="attr" class="col-form-label">'+gettext('Attribute Name:')+'</label>'+
                                '<input id="attr-'+ID+'" type="text" value="_attr" size="40" class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="explode-list-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')
        
        
        icon.on("click", function(){

            setTimeout(function(){
                
                try{
                    // if it's not the first time opening parameters dialog
                    //json figure task will has already the schemas
                    //old is the schema that came from the edge
                    //the other one is result schema depending of parameters chosen
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                //get schema from the edge
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                //if edge schema and old schema is not the same is the first time you open parameters or
                //something was changed in the edge so we hace to create a new schema option
                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge
                    $('#list-'+ID).empty()

                    for (i = 0; i < schema.length; i++){
                        
                        $('#list-'+ID).append('<option>'+schema[i]+'</option>')
                    }
                }

            },100);

            $('#dialog-explode-list-'+ID).modal('show')

            $('#explode-list-accept-'+ID).click(function() {

                //parameters selected to json
                var paramsSplitAttr = {"id": ID,
                "parameters": [
                {"attr": $('#attr-'+ID).val(),
                "list": $('#list-'+ID).val()}
                ]}

                schemaMod =[...schemaEdge]
                schemaMod.splice($('#list-'+ID).prop('selectedIndex'), 1)
                schemaMod.push($('#attr-'+ID).val())

                //updating schema-old and schema parameters in json
                paramsSplitAttr['schema-old'] = schemaEdge
                paramsSplitAttr['schema'] = schemaMod

                //add the schema to a later edge if it exists
                passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)
                
                //check if parameters are already in json canvas
                isAlreadyInCanvas(jsonParams, paramsSplitAttr, ID)

                //set red color to another in order to know if parameters are checked
                icon.setColor('#4682B4')
                
                $('#dialog-explode-list-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Output"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

	     var output= label2.createPort("output");
         output.setName("output_"+label2.id);

	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
	     }
	     else{
             this.add(label1);
             this.add(label2);
         }
         
         listLabel.push([this.id, [input.name], [output.name]])

	     return label1, label2;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes :getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// UNION ////

trans_Union = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_Union",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
        
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Union"), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-union-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext('Union Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<label class="col-form-label">'+gettext('Group by:')+'</label>'+
                                '<select class="form-control" id="group-by-attr-'+ID+'"> </select>'+
                            '</div>'+
                            /*'<div>'+
                                '<input type="checkbox" name="keep-attr" id="keep-attr-'+ID+'" value=""/>'+
                                '<label for="checkbox">'+gettext('Keep attributes of the first feature after union')+'</label>'+
                            '</div>'+*/
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="union-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')
        
        context = this

        icon.on("click", function(){
            
            setTimeout(function(){
                try{
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge
                    $('#group-by-attr-'+ID).empty()
                    $('#group-by-attr-'+ID).append('<option> </option>')

                    for (i = 0; i < schema.length; i++){
                        
                        $('#group-by-attr-'+ID).append('<option>'+schema[i]+'</option>')
                    }
                }

            },100);
            

            $('#dialog-union-'+ID).modal('show')

            $('#union-accept-'+ID).click(function() {

                /*if($("#keep-attr-"+ID).is(':checked')){
                    $("#keep-attr-"+ID).val("true")
                    
                }else{
                    $("#keep-attr-"+ID).val("")
                };*/

                var paramsUnion = {"id": ID,
                "parameters": [
                    {"group-by-attr": $('#group-by-attr-'+ID).val(),
                    /*"keep-attr": $('#keep-attr-'+ID).val()*/}
                ]}


                if($('#group-by-attr-'+ID).val()=== ""){
                    schemaMod =[...schemaEdge]
                }else{
                    schemaMod=[$('#group-by-attr-'+ID).val()]
                }

                paramsUnion['schema'] = schemaMod
                paramsUnion['schema-old'] = schemaEdge

                passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)
                isAlreadyInCanvas(jsonParams, paramsUnion, ID)

                icon.setColor('#4682B4')
                
                $('#dialog-union-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Output"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

	     var output= label2.createPort("output");
         output.setName("output_"+label2.id);

	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
	     }
	     else{
             this.add(label1);
             this.add(label2);
         }
         
         listLabel.push([this.id,[input.name], [output.name]])

	     return label1, label2;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     

     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes :getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// GEOMETRY FILTER ////

trans_FilterGeom = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_FilterGeom",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
        
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext('Filter Geom.'), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({ 
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)
        
        context = this

        icon.on("click", function(){
            schema = passSchemaWhenInputTask(context.canvas, listLabel, ID)

            var paramsFGeom = {"id": ID}

            paramsFGeom['schema-old'] = schema

            if (Array.isArray(schema[0])){
                schemaMod = [schema[0], schema[0], schema[0], schema[0], schema[0], schema[0]]
            }
            else{
                schemaMod = [...schema]
            }

            paramsFGeom['schema'] = schemaMod

            //console.log(schemaMod)

            passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)

            isAlreadyInCanvas(jsonParams, paramsFGeom, ID)

            icon.setColor('#4682B4')
                
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext('Input'),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext('Points'),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

        var label3 =new draw2d.shape.basic.Label({
            text: gettext('Multipoints'),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

        var label4 =new draw2d.shape.basic.Label({
            text: gettext("Lines"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

        var label5 =new draw2d.shape.basic.Label({
            text: gettext("Multilines"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

        var label6 =new draw2d.shape.basic.Label({
            text: gettext("Polygons"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

        var label7 =new draw2d.shape.basic.Label({
            text: gettext("Multipolygons"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

        var input1 = label1.createPort("input");
        input1.setName("input_"+label1.id);

        var output = label2.createPort("output");
        output.setName("output_"+label2.id);

	    var output1= label3.createPort("output");
        output1.setName("output_"+label3.id);

	    var output2= label4.createPort("output");
        output2.setName("output_"+label4.id);

	    var output3= label5.createPort("output");
        output3.setName("output_"+label5.id);
    
        var output4= label6.createPort("output");
        output4.setName("output_"+label6.id);

        var output5= label7.createPort("output");
        output5.setName("output_"+label7.id);

	    if($.isNumeric(optionalIndex)){
            this.add(label1, null, optionalIndex+1);
            this.add(label2, null, optionalIndex+1);
            this.add(label3, null, optionalIndex+1);
            this.add(label4, null, optionalIndex+1);
            this.add(label5, null, optionalIndex+1);
            this.add(label6, null, optionalIndex+1);
            this.add(label7, null, optionalIndex+1);
	    }
	    else{
            this.add(label1);
            this.add(label2);
            this.add(label3);
            this.add(label4);
            this.add(label5);
            this.add(label6);
            this.add(label7);
        }
         
        listLabel.push([this.id, [input1.name], [output.name, output1.name, output2.name, output3.name, output4.name, output5.name]])

	    return label1, label2, label3, label4, label5, label6;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     

     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes : getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});


//// EXPLODE GEOMETRY ////

trans_ExplodeGeom = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_ExplodeGeom",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
        
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Explode Geometry"), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)
        
        context = this

        icon.on("click", function(){
            
            setTimeout(function(){
                try{
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)


                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge
                }

            },100);
            
            var paramsExplodGeom = {"id": ID}
            
            paramsExplodGeom['schema'] = schemaEdge
            paramsExplodGeom['schema-old'] = schemaEdge

            passSchemaToEdgeConnected(ID, listLabel, schemaEdge, context.canvas)
            isAlreadyInCanvas(jsonParams, paramsExplodGeom, ID)

            icon.setColor('#4682B4')

        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Output"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

	     var output= label2.createPort("output");
         output.setName("output_"+label2.id);

	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
	     }
	     else{
             this.add(label1);
             this.add(label2);
         }
         
         listLabel.push([this.id,[input.name], [output.name]])

	     return label1, label2;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },

     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes :getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// CALCULATE AREA ////

trans_CalcArea = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_CalcArea",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
        
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Calculate Area"), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-calc-area-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext('Calculate Area Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<label class="col-form-label">'+gettext('New area attribute:')+'</label>'+
                                '<input id="attr-'+ID+'" type="text" size="40" value="_area" class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="calc-area--accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')
        
        context = this

        icon.on("click", function(){
            
            setTimeout(function(){
                try{
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]

                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge
                }

            },100);
            
            $('#dialog-calc-area-'+ID).modal('show')

            $('#calc-area--accept-'+ID).click(function() {

                var paramsCalcArea = {"id": ID,
                "parameters": [
                    {"attr": $('#attr-'+ID).val()}
                ]}

                schemaMod =[...schemaEdge]
                schemaMod.push($('#attr-'+ID).val())
                
                paramsCalcArea['schema'] = schemaMod
                paramsCalcArea['schema-old'] = schemaEdge
                
                passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)
                isAlreadyInCanvas(jsonParams, paramsCalcArea, ID)

                icon.setColor('#4682B4')
                
                $('#dialog-calc-area-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Output"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

	     var output= label2.createPort("output");
         output.setName("output_"+label2.id);

	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
	     }
	     else{
             this.add(label1);
             this.add(label2);
         }
         
         listLabel.push([this.id,[input.name], [output.name]])

	     return label1, label2;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     

     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes :getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// CURRENT DATE ////

trans_CurrentDate = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_CurrentDate",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
        
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Current Date"), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#71c7ec", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-current-date-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+gettext('Current Date Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<label class="col-form-label">'+gettext('New date attribute')+':</label>'+
                                '<input id="attr-'+ID+'" type="text" size="40" value="_date" class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                            /*'<div class="column50">'+
                                '<label class="col-form-label"><a href = "https://www.w3schools.com/python/python_datetime.asp" target="_blank">'+gettext('Format')+':</a></label>'+
                                '<input id="format-'+ID+'" type="text" size="40" value="%d/%m/%Y" class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+*/
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="current-date-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')
        
        context = this

        icon.on("click", function(){
            
            setTimeout(function(){
                try{
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge
                }

            },100);
            

            $('#dialog-current-date-'+ID).modal('show')

            $('#current-date-accept-'+ID).click(function() {

                var paramsDate = {"id": ID,
                "parameters": [
                    {"attr": $('#attr-'+ID).val(),
                    "format": $('#format-'+ID).val()}
                ]}

                schemaMod =[...schemaEdge]
                
                schemaMod.push($('#attr-'+ID).val())
                
                paramsDate['schema'] = schemaMod
                paramsDate['schema-old'] = schemaEdge

                passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)
                isAlreadyInCanvas(jsonParams, paramsDate, ID)

                icon.setColor('#4682B4')
                
                $('#dialog-current-date-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function( optionalIndex)
    {
	   	 var label1 =new draw2d.shape.basic.Label({
	   	     text: gettext("Input"),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:10, top:3, right:10, bottom:5},
	   	     fontColor:"#107dac",
             resizeable:true
	   	 });

	   	 var label2 =new draw2d.shape.basic.Label({
            text: gettext("Output"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

         var input = label1.createPort("input");
         input.setName("input_"+label1.id);

	     var output= label2.createPort("output");
         output.setName("output_"+label2.id);

	     if($.isNumeric(optionalIndex)){
             this.add(label1, null, optionalIndex+1);
             this.add(label2, null, optionalIndex+1);
	     }
	     else{
             this.add(label1);
             this.add(label2);
         }
         
         listLabel.push([this.id,[input.name], [output.name]])

	     return label1, label2;
    },
        /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        
        this.remove(this.children.get(index+1).figure);
        
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     

     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes :getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

////////////////////////////////////////////////  SALIDAS /////////////////////////////////////////////////////////

//// OUTPUT POSTGRESQL ////

output_Postgresql = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "output_Postgresql",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
        
        this.classLabel = new draw2d.shape.basic.Label({
            text:"PostgreSQL", 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#e8ca93", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        context = this

        $('#canvas-parent').append('<div id="dialog-output-postgresql-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title">'+gettext('PostgreSQL Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column50">'+
                                '<label form="host" class="col-form-label">'+gettext('Host:')+'</label>'+
                                '<input id="host-'+ID+'" type="text" value="localhost" size="40" class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                            '<div class="column50">'+    
                                '<label form="port" class="col-form-label">'+gettext('Port:')+'</label>'+
                                '<input id="port-'+ID+'" type="text" value="5432" size="40" class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label form="database" class="col-form-label">'+gettext('Database:')+'</label>'+
                                '<input id="database-'+ID+'" type="text" value="" size="40" class="form-control" pattern="[A-Za-z]{3}" placeholder="'+gettext('Name of your database')+'">'+
                            '</div>'+
                            '<div class="column50">'+                                
                                '<label form="user" class="col-form-label">'+gettext('User:')+'</label>'+
                                '<input id="user-'+ID+'" type="text" value="postgres" size="40"  class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label form="password" class="col-form-label">'+gettext('Password:')+'</label>'+
                                '<input type="password" id = "password-'+ID+'" class="form-control" value="">'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label form="tablename" class="col-form-label">'+gettext('Table name:')+'</label>'+
                                '<input id="tablename-'+ID+'" type="text" value="" size="40" class="form-control" pattern="[A-Za-z]{3}" placeholder="'+gettext('schema.tablename')+'">'+
                            '</div>'+
                            '<div class="column25">'+
                                '<label class="col-form-label">'+gettext('Operation:')+'</label>'+
                                '<div class="form-check">'+
                                    '<input type="radio" id="create" name="operation-'+ID+'" class="form-check-input" value="CREATE" checked="checked">'+
                                    '<label for="create" class="form-check-label">'+gettext('CREATE')+'</label>'+
                                '</div>'+
                                '<div class="form-check">'+
                                    '<input type="radio" id="append-'+ID+'" name="operation-'+ID+'" class="form-check-input" value="APPEND">'+
                                    '<label for="append" class="form-check-label">'+gettext('APPEND')+'</label>'+
                                '</div>'+
                                '<div class="form-check">'+
                                    '<input type="radio" id="overwrite" name="operation-'+ID+'" class="form-check-input" value="OVERWRITE">'+
                                    '<label for="overwrite" class="form-check-label">'+gettext('OVERWRITE')+'</label>'+
                                '</div>'+
                            '</div>'+
                            '<div class="column25">'+
                            '<br><br>'+
                                '<div class="form-check">'+
                                    '<input type="radio" id="update-'+ID+'" name="operation-'+ID+'" class="form-check-input" value="UPDATE">'+
                                    '<label for="update" class="form-check-label">'+gettext('UPDATE')+'</label>'+
                                '</div>'+
                                '<div class="form-check">'+
                                    '<input type="radio" id="delete" name="operation-'+ID+'" class="form-check-input" value="DELETE">'+
                                    '<label for="delete" class="form-check-label">'+gettext('DELETE')+'</label>'+
                                '</div>'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label class="col-form-label">'+gettext('Match column:')+'</label>'+
                                '<select class="form-control" id="match-'+ID+'" disabled> </select>'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="verify-postgresql-'+ID+'">'+gettext('Verify connection')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="output-postgresql-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        $('input:radio[name="operation-'+ID+'"]').change(function(){
            
            if ($(this).val()!='CREATE'){
                $('#match-'+ID).attr('disabled', false)
            }
            else{
                $('#match-'+ID).attr('disabled', true)
            }
        });
        
        $('#verify-postgresql-'+ID).click(function() {
                
        var paramsPostgres = {"id": ID,
            "parameters": [
                {"host": $('#host-'+ID).val(),
                "port": $('#port-'+ID).val(),
                "database": $('#database-'+ID).val(),
                "user": $('#user-'+ID).val(),
                "password": $('#password-'+ID).val()}
            ]}

            var formDataPostgres = new FormData();
            
            formDataPostgres.append('jsonParamsPostgres', JSON.stringify(paramsPostgres))

            $.ajax({
                type: 'POST',
                url: '/gvsigonline/etl/test_postgres_conexion/',
                data: formDataPostgres,
                beforeSend:function(xhr){
                    xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
                },
                cache: false, 
                contentType: false, 
                processData: false,
                success: function (response) {

                    if(response.result == true){
                        textConnection = gettext('Connection parameters are valids.')
                    }else{
                        textConnection = gettext('Connection parameters are not valids.')
                    }

                    $("#dialog-test-postgres-connection").remove();
                        
                    $('#canvas-parent').append('<div id="dialog-test-postgres-connection" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
                        '<div class="modal-dialog" role="document">'+
                            '<div class="modal-content">'+
                                '<div class="modal-header">'+
                                    '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                                        '<span aria-hidden="true">&times;</span>'+
                                    '</button>'+
                                    '<h4 class="modal-title">'+gettext('Response')+'</h4>'+
                                '</div>'+
                                '<div class="modal-body" align="center">'+textConnection+
                                '</div>'+
                                '<div class="modal-footer">'+
                                    '<button id= "close-test-postgres-connection" type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                                '</div>'+
                            '</div>'+
                        '</div>'+
                    '</div>')

                    $('#dialog-test-postgres-connection').modal('show')

                    $('#close-test-postgres-connection').click(function() {
                        
                        $('#dialog-test-postgres-connection').modal('hide')
                        
                    })
                }
            })
        });
        

        icon.on("click", function(){

            setTimeout(function(){
                try{
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge
                    $('#match-'+ID).empty()

                    for (i = 0; i < schema.length; i++){
                        $('#match-'+ID).append('<option>'+schema[i]+'</option>')
                    }
                }

            },100);

            $('#dialog-output-postgresql-'+ID).modal('show')

            $('#output-postgresql-accept-'+ID).click(function() {

                var paramsPostgreSQL = {"id": ID,
                "parameters": [
                    {"host": $('#host-'+ID).val(),
                    "port": $('#port-'+ID).val(),
                    "database": $('#database-'+ID).val(),
                    "user": $('#user-'+ID).val(),
                    "password": $('#password-'+ID).val(),
                    "tablename": $('#tablename-'+ID).val(),
                    "match": $('#match-'+ID).val(),
                    "operation": $('input:radio[name="operation-'+ID+'"]:checked').val()}
                ]}
                
                paramsPostgreSQL['schema-old'] = schemaEdge
                paramsPostgreSQL['schema'] = schema
                
                isAlreadyInCanvas(jsonParams, paramsPostgreSQL, ID)

                icon.setColor('#e79600')
                
                $('#dialog-output-postgresql-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function(optionalIndex)
    {
	   	var label =new draw2d.shape.basic.Label({
	   	    text: gettext("Output"),
	   	    stroke:0.2,
	   	    radius:0,
	   	    bgColor:"#ffffff",
	   	    padding:{left:10, top:3, right:40, bottom:5},
	   	    fontColor:"#9a8262",
            resizeable:true
            
	   	 });

	     var input= label.createPort("input");

         input.setName("input_"+label.id);
         
	     if($.isNumeric(optionalIndex)){
             this.add(label, null, optionalIndex+1);
	     }
	     else{
	         this.add(label);
	     }
         
         listLabel.push([this.id, [input.name], []])

	     return label;
    },

    /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes : getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});

//// OUTPUT POSTGIS ////

output_Postgis = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "output_Postgis",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
        
        this.classLabel = new draw2d.shape.basic.Label({
            text:"PostGIS", 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#e8ca93", 
            radius: this.getRadius(), 
            padding:10,
            resizeable:true,
            editor:new draw2d.ui.LabelInplaceEditor()
        });
        
        var icon = new draw2d.shape.icon.Gear({
            minWidth:13, 
            minHeight:13, 
            width:13, 
            height:13, 
            color:"#e2504c"
        });

        this.classLabel.add(icon, new draw2d.layout.locator.XYRelPortLocator(82, 8))

        this.add(this.classLabel);

        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        $('#canvas-parent').append('<div id="dialog-output-postgis-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title">'+gettext('PostGIS Parameters')+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column50">'+
                                '<label form="host" class="col-form-label">'+gettext('Host:')+'</label>'+
                                '<input id="host-'+ID+'" type="text" value="localhost" size="40" class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                            '<div class="column50">'+    
                                '<label form="port" class="col-form-label">'+gettext('Port:')+'</label>'+
                                '<input id="port-'+ID+'" type="text" value="5432" size="40" class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label form="database" class="col-form-label">'+gettext('Database:')+'</label>'+
                                '<input id="database-'+ID+'" type="text" value="" size="40" class="form-control" pattern="[A-Za-z]{3}" placeholder="'+gettext('Name of your database')+'">'+
                            '</div>'+
                            '<div class="column50">'+                                
                                '<label form="user" class="col-form-label">'+gettext('User:')+'</label>'+
                                '<input id="user-'+ID+'" type="text" value="postgres" size="40"  class="form-control" pattern="[A-Za-z]{3}">'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label form="password" class="col-form-label">'+gettext('Password:')+'</label>'+
                                '<input type="password" id = "password-'+ID+'" class="form-control" value="">'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label form="tablename" class="col-form-label">'+gettext('Table name:')+'</label>'+
                                '<input id="tablename-'+ID+'" type="text" value="" size="40" class="form-control" pattern="[A-Za-z]{3}" placeholder="'+gettext('schema.tablename')+'">'+
                            '</div>'+
                            '<div class="column25">'+
                                '<label class="col-form-label">'+gettext('Operation:')+'</label>'+
                                '<div class="form-check">'+
                                    '<input type="radio" id="create" name="operation-'+ID+'" class="form-check-input" value="CREATE" checked="checked">'+
                                    '<label for="create" class="form-check-label">'+gettext('CREATE')+'</label>'+
                                '</div>'+
                                '<div class="form-check">'+
                                    '<input type="radio" id="append-'+ID+'" name="operation-'+ID+'" class="form-check-input" value="APPEND">'+
                                    '<label for="append" class="form-check-label">'+gettext('APPEND')+'</label>'+
                                '</div>'+
                                '<div class="form-check">'+
                                    '<input type="radio" id="overwrite" name="operation-'+ID+'" class="form-check-input" value="OVERWRITE">'+
                                    '<label for="overwrite" class="form-check-label">'+gettext('OVERWRITE')+'</label>'+
                                '</div>'+
                            '</div>'+
                            '<div class="column25">'+
                            '<br><br>'+
                                '<div class="form-check">'+
                                    '<input type="radio" id="update-'+ID+'" name="operation-'+ID+'" class="form-check-input" value="UPDATE">'+
                                    '<label for="update" class="form-check-label">'+gettext('UPDATE')+'</label>'+
                                '</div>'+
                                '<div class="form-check">'+
                                    '<input type="radio" id="delete" name="operation-'+ID+'" class="form-check-input" value="DELETE">'+
                                    '<label for="delete" class="form-check-label">'+gettext('DELETE')+'</label>'+
                                '</div>'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label class="col-form-label">'+gettext('Match column:')+'</label>'+
                                '<select class="form-control" id="match-'+ID+'" disabled> </select>'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="verify-postgis-'+ID+'">'+gettext('Verify connection')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="output-postgis-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        $('input:radio[name="operation-'+ID+'"]').change(function(){
            
            if ($(this).val()=='UPDATE' || $(this).val()=='DELETE'){
                $('#match-'+ID).attr('disabled', false)
            }
            else{
                $('#match-'+ID).attr('disabled', true)
            }
        });
        
        $('#verify-postgis-'+ID).click(function() {
                
        var paramsPostgres = {"id": ID,
            "parameters": [
                {"host": $('#host-'+ID).val(),
                "port": $('#port-'+ID).val(),
                "database": $('#database-'+ID).val(),
                "user": $('#user-'+ID).val(),
                "password": $('#password-'+ID).val()}
            ]}

            var formDataPostgres = new FormData();
            
            formDataPostgres.append('jsonParamsPostgres', JSON.stringify(paramsPostgres))

            $.ajax({
                type: 'POST',
                url: '/gvsigonline/etl/test_postgres_conexion/',
                data: formDataPostgres,
                beforeSend:function(xhr){
                    xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
                },
                cache: false, 
                contentType: false, 
                processData: false,
                success: function (response) {

                    if(response.result == true){
                        textConnection = gettext('Connection parameters are valids.')
                    }else{
                        textConnection = gettext('Connection parameters are not valids.')
                    }

                    $("#dialog-test-postgres-connection").remove();
                        
                    $('#canvas-parent').append('<div id="dialog-test-postgres-connection" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
                        '<div class="modal-dialog" role="document">'+
                            '<div class="modal-content">'+
                                '<div class="modal-header">'+
                                    '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                                        '<span aria-hidden="true">&times;</span>'+
                                    '</button>'+
                                    '<h4 class="modal-title">'+gettext('Response')+'</h4>'+
                                '</div>'+
                                '<div class="modal-body" align="center">'+textConnection+
                                '</div>'+
                                '<div class="modal-footer">'+
                                    '<button id= "close-test-postgres-connection" type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                                '</div>'+
                            '</div>'+
                        '</div>'+
                    '</div>')

                    $('#dialog-test-postgres-connection').modal('show')

                    $('#close-test-postgres-connection').click(function() {
                        
                        $('#dialog-test-postgres-connection').modal('hide')
                        
                    })
                }
            })
        });
        
        context = this
        icon.on("click", function(){

            setTimeout(function(){
                try{
                    schemas = getOwnSchemas(context.canvas, ID)
                    schema = schemas[0]
                    schemaOld = schemas[1]
                
                }catch{ 
                    schema=[]
                    schemaOld =[]
                }
                
                schemaEdge = passSchemaWhenInputTask(context.canvas, listLabel, ID)

                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge
                    $('#match-'+ID).empty()

                    for (i = 0; i < schema.length; i++){
                        $('#match-'+ID).append('<option>'+schema[i]+'</option>')
                    }
                }

            },100);

            $('#dialog-output-postgis-'+ID).modal('show')

            $('#output-postgis-accept-'+ID).click(function() {

                var paramsPostgis = {"id": ID,
                "parameters": [
                    {"host": $('#host-'+ID).val(),
                    "port": $('#port-'+ID).val(),
                    "database": $('#database-'+ID).val(),
                    "user": $('#user-'+ID).val(),
                    "password": $('#password-'+ID).val(),
                    "tablename": $('#tablename-'+ID).val(),
                    "match": $('#match-'+ID).val(),
                    "operation": $('input:radio[name="operation-'+ID+'"]:checked').val()}
                ]}
                
                paramsPostgis['schema-old'] = schemaEdge
                paramsPostgis['schema'] = schema
                
                isAlreadyInCanvas(jsonParams, paramsPostgis, ID)

                icon.setColor('#e79600')
                
                $('#dialog-output-postgis-'+ID).modal('hide')

            })
        })
    },
     
    /**
     * @method
     * Add an entity to the db shape
     * 
     * @param {String} txt the label to show
     * @param {Number} [optionalIndex] index where to insert the entity
     */
    addEntity: function(optionalIndex)
    {
	   	var label =new draw2d.shape.basic.Label({
	   	    text: gettext("Output"),
	   	    stroke:0.2,
	   	    radius:0,
	   	    bgColor:"#ffffff",
	   	    padding:{left:10, top:3, right:40, bottom:5},
	   	    fontColor:"#9a8262",
            resizeable:true
            
	   	 });

	     var input= label.createPort("input");

         input.setName("input_"+label.id);
         
	     if($.isNumeric(optionalIndex)){
             this.add(label, null, optionalIndex+1);
	     }
	     else{
	         this.add(label);
	     }
         
         listLabel.push([this.id, [input.name], []])

	     return label;
    },

    /**
     * @method
     * Remove the entity with the given index from the DB table shape.<br>
     * This method removes the entity without care of existing connections. Use
     * a draw2d.command.CommandDelete command if you want to delete the connections to this entity too
     * 
     * @param {Number} index the index of the entity to remove
     */
    removeEntity: function(index)
    {
        this.remove(this.children.get(index+1).figure);
    },

    /**
     * @method
     * Returns the entity figure with the given index
     * 
     * @param {Number} index the index of the entity to return
     */
    getEntity: function(index)
    {
        return this.children.get(index+1).figure;
    },
     
     /**
      * @method
      * Set the name of the DB table. Visually it is the header of the shape
      * 
      * @param name
      */
     setName: function(name)
     {
         this.classLabel.setText(name);
         
         return this;
     },
     
     /**
      * @method 
      * Return an objects with all important attributes for XML or JSON serialization
      * 
      * @returns {Object}
      */
     getPersistentAttributes : getPerAttr,
     
     /**
      * @method 
      * Read all attributes from the serialized properties and transfer them into the shape.
      *
      * @param {Object} memento
      * @return
      */
     setPersistentAttributes : function(memento)
     {
         
         this._super(memento);
         
         this.setName(memento.name);

         if(typeof memento.entities !== "undefined"){
             $.each(memento.entities, $.proxy(function(i,e){
                 var entity =this.addEntity(e.text);
                 entity.id = e.id;
                 entity.getInputPort(0).setName("input_"+e.id);
                 entity.getOutputPort(0).setName("output_"+e.id);
             },this));
         }

         return this;
     }  

});