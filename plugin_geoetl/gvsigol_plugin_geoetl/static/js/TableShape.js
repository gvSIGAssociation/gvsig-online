var jsonParams = [];

var formData = new FormData();

var listLabel=[];

var paramsTransTpl = gettext('Parameters: {}');

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
                }else if (type.startsWith('crea')){ 
                    icon.setColor("#8e57eb")
                }
                break;
            }
        } },1)

};

function getPathFile(fileType, ID){

    $('#select-file-button-'+ID).click(function (e) {
        window.open("/gvsigonline/filemanager/?popup=1","Ratting","width=640, height=480,left=150,top=200,toolbar=0,status=0,scrollbars=1");
    });

    $('#select-folder-button-'+ID).click(function (e) {
        window.open("/gvsigonline/filemanager/?popup=1","Ratting","width=640, height=480,left=150,top=200,toolbar=0,status=0,scrollbars=1");
    });

    window.filemanagerCallback = function(url) {

        if(fileType == 'csv' && url.endsWith('.csv')){
            $("#"+fileType+"-file-"+ID).val("file://" + fm_directory + url)
        }else if(fileType == 'json' && url.endsWith('.json') && ID != '0'){
            $("#"+fileType+"-file-"+ID).val("file://" + fm_directory + url)
        }else if(fileType == 'xml' && url.endsWith('.xml') && ID != '0'){
            $("#"+fileType+"-file-"+ID).val("file://" + fm_directory + url)
        }else if(fileType == 'excel' && (url.endsWith('.xls') || url.endsWith('.xlsx'))){
            $("#"+fileType+"-file-"+ID).val("file://" + fm_directory + url)
        } else if(fileType == 'shp' && url.endsWith('.shp')){
            $("#"+fileType+"-file-"+ID).val("file://" + fm_directory + url)
        } else if(fileType == 'kml-kmz' && (url.endsWith('.kml') || url.endsWith('.kmz'))){
            $("#"+fileType+"-file-"+ID).val("file://" + fm_directory + url)
        } else if(fileType == 'json' && url.endsWith('.json') && ID == '0'){
            $("#etl_json_upload").val("file://" + fm_directory + url)
        } else if(fileType.endsWith('/')){
            $("#"+fileType.replace('/', '')+"-file-"+ID).val(fm_directory + url)
        } else if(fileType=='folder'){
            $("#folder-"+ID).val(fm_directory + url)
            delete fileType
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
                        '<h4 class="modal-title">'+paramsTransTpl.replace('{}', gettext('InDenova'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<label form="db" class="col-form-label">'+gettext('API Connection:')+'</label>'+
                                '<select id="api-'+ID+'" class="form-control"></select>'+
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
                            '<div class="column40">'+
                                '<label class="col-form-label" >'+gettext('idTram:')+'</label>'+
                                '<input type="text" id="idtram-'+ID+'"  class="form-control"></input>'+
                            '</div>'+
                            '<div class="column40">'+
                                '<label class="col-form-label" >'+gettext('Description:')+'</label>'+
                                '<input type="text" id="description-'+ID+'"  class="form-control"></input>'+
                            '</div>'+
                            '<div class="column20">'+
                                '<label class="col-form-label" >'+gettext('Add Procedure:')+'</label>'+
                                '<button type="button"  class="btn btn-default btn-sm" id="add-proced-'+ID+'"><i class="fa fa-plus" aria-hidden="true"></i></button>'+
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
                            '<br><br><br><br><br><br><br><br><br><br><br><br><br><br>'+ 
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

        for(i=0;i<dbc.length;i++){

            if(dbc[i].type == 'indenova'){
                $('#api-'+ID).append(
                    '<option value="'+dbc[i].name+'">'+dbc[i].name+'</option>'
                );
            }
        };

        $("#add-proced-"+ID).click(function() {

            if($("#idtram-"+ID).val() != ''){                
                if (typeof get_ === 'undefined'){
                    get_ = []
                    $("#proced-list-"+ID+" option").each(function()
                        {  
                            if ($(this).val() != 'all'){
                                get_.push([$(this).val(), $(this).text()])
                            }
                        }
                    );
                }
                
                $('#proced-list-'+ID).append('<option value="'+$("#idtram-"+ID).val()+'">'+$("#idtram-"+ID).val()+' - '+$("#description-"+ID).val()+'</option>')
                get_.push([$("#idtram-"+ID).val(), $("#idtram-"+ID).val()+' - '+$("#description-"+ID).val()])

            }

        })

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
                {"api": $('#api-'+ID).val()}
                /*{"domain": $('#domain-'+ID).val(),
                "api-key": $('#api-key-'+ID).val(),
                "client-id": $('#client-id-'+ID).val(),
                "secret": $('#secret-'+ID).val()
                }*/
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

                    $('#proced-list-'+ID).empty()
                    $('#proced-list-'+ID).append('<option value="all">'+gettext('ALL')+'</option>')
                    
                    $('#get-proced-'+ID).hover(function(){
                        $(this).css('cursor','pointer');
                    });

                    get_ = []
                    
                    for(i=0;i<data.length;i++){
                        $('#proced-list-'+ID).append('<option value="'+data[i][0]+'">'+data[i][0]+' - '+data[i][1]+'</option>')
                        get_.push([data[i][0], data[i][0]+' - '+data[i][1]])
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
        });

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

            if (typeof get_ === 'undefined'){
                get_ = []
                $("#proced-list-"+ID+" option").each(function()
                    {  
                        if ($(this).val() != 'all'){
                            get_.push([$(this).val(), $(this).text()])
                        }
                        
                    }
                );
            }

            var paramsIndenova = {"id": ID,
            "parameters": [
                {   
                    "get_proced-list": get_,
                    "api": $('#api-'+ID).val(),
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
        });
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

//// INPUT SEGEX ////
input_Segex = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "input_Segex",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text:"SEGEX",
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

        $('#canvas-parent').append('<div id="dialog-input-segex-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title">'+paramsTransTpl.replace('{}', gettext('SEGEX'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+

                            '<div>'+
                                '<label form="db" class="col-form-label">'+gettext('API Connection:')+'</label>'+
                                '<select id="api-'+ID+'" class="form-control"></select>'+
                            '</div>'+

                            '<div>'+
                                '<label class="col-form-label" >'+gettext('Types of georeferences in the entity')+':</label><br>'+
                                '<a href="#" id="get-types-'+ID+'" class="btn btn-default btn-sm"><i class="fa fa-download margin-r-5"></i>'+gettext('Get types')+'</a>'+
                            '</div>'+
                            '<div class="box-tools">'+
                                '<br><select id="types-list-'+ID+'" name="types-list" multiple style="width: 100%; height:200px">'+
                                    '<option value="all">'+gettext('ALL')+'</option>'+
                                '</select>'+
                            '</div>'+

                            '<div>'+
                                '<label>'+gettext('Choose date')+'</label><br>'+
                                    '<div >'+
                                    
                                        '<input  type="radio" name="date-segex-'+ID+'"  id="check-no-date-'+ID+'" value="check-no-date">'+	
                                        '<label  for="no-date">'+gettext('No date, download all')+'</label>'+

                                        '<input  type="radio" name="date-segex-'+ID+'"  id="check-init-date-'+ID+'" value="check-init-date">'+	
                                        '<label  for="init-date">'+gettext('From an initial date')+'</label>'+

                                        '<input  type="radio" name="date-segex-'+ID+'"  id="check-init-end-date-'+ID+'" value="check-init-end-date">'+	
                                        '<label  for="init-end-date">'+gettext('Between dates')+'</label>'+

                                    '</div>'+
                            '</div>'+
                            
                            '<div class="input-group date">'+
                                '<div class="column50">'+
                                    '<label>'+gettext('Init date')+'</label>'+
                                    '<input type="datetime-local" class="form-control" id="init-date-'+ID+'" name="init-date"/>'+
                                '</div>'+
                                '<div class="column50">'+
                                    '<label>'+gettext('End date')+'</label>'+
                                    '<input type="datetime-local" class="form-control" id="end-date-'+ID+'" name="end-date"/>'+
                                '</div>'+
                            '</div>'+
                            
                            '<div>'+
                                '<input type="radio" name="init-segex-'+ID+'" id="init-'+ID+'" value="init"/>'+
                                '<input type="number" id="minute-before-'+ID+'" value="0" size ="3"/>'+
                                '<label for="radio"> '+gettext('Minutes before the current date for the init date')+'</label>'+
                            '</div>'+
                            '<div>'+
                                '<input type="radio" name="init-segex-'+ID+'" id="init-guaranteed-'+ID+'" value="init-guaranteed"/>'+
                                '<label for="radio" data-toggle-second="tooltip" data-placement="top" title="'+gettext('If files of the selected type of georeference have not been previously requested, this option will fail.')+'"> '+gettext('Last date guaranteed for the init date.')+'</label>'+
                            '</div>'+
                            '<div>'+
                                '<input type="checkbox" name="checkbox-end-segex" id="checkbox-end-'+ID+'" value=""/>'+
                                '<label for="checkbox">'+gettext('Current date for end')+'</label>'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="input-segex-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        var context = this

        for(i=0;i<dbc.length;i++){

            if(dbc[i].type == 'segex'){
                $('#api-'+ID).append(
                    '<option value="'+dbc[i].name+'">'+dbc[i].name+'</option>'
                );
            }
        };

        $('#init-date-'+ID).prop('disabled', true)
        $('#end-date-'+ID).prop('disabled', true)
        $("#init-"+ID).prop('disabled', true)
        $("#checkbox-end-"+ID).prop('disabled', true)
        $("#minute-before-"+ID).prop('disabled', true)

        $('input:radio[name="date-segex-'+ID+'"]').change(function(){
            if ($('#check-no-date-'+ID).is(':checked')){
                
                $('#init-date-'+ID).prop('disabled', true)
                $('#init-date-'+ID).val("")
                
                $('#end-date-'+ID).prop('disabled', true)
                $('#end-date-'+ID).val("")
                
                $("#init-"+ID).prop('disabled', true)
                $("#init-"+ID).prop('checked', false)

                $("#init-guaranteed-"+ID).prop('disabled', true)
                $("#init-guaranteed-"+ID).prop('checked', false)
                
                $("#checkbox-end-"+ID).prop('disabled', true)
                $("#checkbox-end-"+ID).prop('checked', false)
                
                $("#minute-before-"+ID).prop('disabled', true)
                $("#minute-before-"+ID).val(0)
                
            }
            
            else if ($('#check-init-date-'+ID).is(':checked')){
                
                $('#init-date-'+ID).prop('disabled', false)
                
                $('#end-date-'+ID).prop('disabled', true)
                $('#end-date-'+ID).val("")
                
                $("#init-"+ID).prop('disabled', false)

                $("#init-guaranteed-"+ID).prop('disabled', false)

                $("#checkbox-end-"+ID).prop('disabled', true)
                $("#checkbox-end-"+ID).prop('checked', false)
                
                $("#minute-before-"+ID).prop('disabled', false)
                
            }
            else{
            
                $('#init-date-'+ID).prop('disabled', false)
                
                $('#end-date-'+ID).prop('disabled', false)
                
                $("#init-"+ID).prop('disabled', false)
                $("#init-guaranteed-"+ID).prop('disabled', false)

                
                $("#checkbox-end-"+ID).prop('disabled', false)
                
                $("#minute-before-"+ID).prop('disabled', false)

            }
        });


        $("#checkbox-end-"+ID).click(function() {
            if($("#checkbox-end-"+ID).is(':checked')){
                $('#end-date-'+ID).val("")
            }
        });

        $("#init-"+ID).click(function() {
            if($("#init-"+ID).is(':checked')){
                $('#init-date-'+ID).val("")
            }else{

                $('#minute-before-'+ID).val(0)
            }
        });



        $('#types-list-'+ID).click(function(){
            if($(this).val()=='all'){
                $('#types-list-'+ID+' option').prop('selected', true)
            }
        });

        $('#get-types-'+ID).click(function(){
                
            $(this).hover(function(){
                $(this).css('cursor','wait');
                
            });
            
            var paramsTypes = {"id": ID,
            "parameters": [
                {"api": $('#api-'+ID).val()
                }
            ]};

            var formDataTypes = new FormData();

            formDataTypes.append('jsonParamsTypes', JSON.stringify(paramsTypes))

            $.ajax({
                type: 'POST',
                url: '/gvsigonline/etl/etl_types_segex/',
                data: formDataTypes,
                beforeSend:function(xhr){
                    xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
                },
                cache: false, 
                contentType: false, 
                processData: false,
                success: function (data) {

                    $('#types-list-'+ID).empty()
                    $('#types-list-'+ID).append('<option value="all">'+gettext('ALL')+'</option>')
                    
                    $('#get-types-'+ID).hover(function(){
                        $(this).css('cursor','pointer');
                    });

                    get_types = []
                    
                    for(i=0;i<data.length;i++){
                        $('#types-list-'+ID).append('<option value="'+data[i][0]+'">'+data[i][1]+'</option>')
                        get_types.push([data[i][0], data[i][1]])
                    };
                },
                error: function(){
                    $('#get-types-'+ID).hover(function(){
                        $(this).css('cursor','pointer');
                    });
                }
            })
        });
        
        icon.on("click", function(){

            $('#dialog-input-segex-'+ID).modal('show')

            if ($('#check-no-date-'+ID).is(':checked')){
                
                $('#init-date-'+ID).prop('disabled', true)
                $('#init-date-'+ID).val("")
                
                $('#end-date-'+ID).prop('disabled', true)
                $('#end-date-'+ID).val("")
                
                $("#init-"+ID).prop('disabled', true)
                $("#init-"+ID).prop('checked', false)

                $("#init-guaranteed-"+ID).prop('disabled', true)
                $("#init-guaranteed-"+ID).prop('checked', false)
                
                $("#checkbox-end-"+ID).prop('disabled', true)
                $("#checkbox-end-"+ID).prop('checked', false)
                
                $("#minute-before-"+ID).prop('disabled', true)
                $("#minute-before-"+ID).val(0)
                
            }
            
            else if ($('#check-init-date-'+ID).is(':checked')){
                
                $('#init-date-'+ID).prop('disabled', false)
                
                $('#end-date-'+ID).prop('disabled', true)
                $('#end-date-'+ID).val("")
                
                $("#init-"+ID).prop('disabled', false)

                $("#init-guaranteed-"+ID).prop('disabled', false)

                $("#checkbox-end-"+ID).prop('disabled', true)
                $("#checkbox-end-"+ID).prop('checked', false)
                
                $("#minute-before-"+ID).prop('disabled', false)

                
            }
            else if ($('#check-init-end-date-'+ID).is(':checked')){
            
                $('#init-date-'+ID).prop('disabled', false)
                
                $('#end-date-'+ID).prop('disabled', false)
                
                $("#init-"+ID).prop('disabled', false)
                $("#init-guaranteed-"+ID).prop('disabled', false)
                
                $("#checkbox-end-"+ID).prop('disabled', false)
                
                $("#minute-before-"+ID).prop('disabled', false)

            }
        });

        $('#input-segex-accept-'+ID).click(function() {

            if($("#checkbox-end-"+ID).is(':checked')){
                $("#checkbox-end-"+ID).val("true")
                
            }else{
                $("#checkbox-end-"+ID).val("")
            };



            if (typeof get_types === 'undefined'){
                get_types = []
                $("#types-list-"+ID+" option").each(function()

                    {  
    
                        if ($(this).val() != 'all'){
                            get_types.push([$(this).val(), $(this).text()])
                        }
                        
                    }
                );

            }

           if ($('input:radio[name="init-segex-'+ID+'"]:checked').val()=== undefined){
                init_date = 'False'
           }else{
                init_date = $('input:radio[name="init-segex-'+ID+'"]:checked').val()
           }

            var paramsSegex= {"id": ID,
            "parameters": [
                {   
                    "get_types-list": get_types,
                    "api": $('#api-'+ID).val(),
                    "types-list": $('#types-list-'+ID).val(),
                    "minute-before": $('#minute-before-'+ID).val(),
                    "init-date": $('#init-date-'+ID).val(),
                    "end-date": $('#end-date-'+ID).val(),
                    "checkbox-end": $("#checkbox-end-"+ID).val(),
                    "init-segex":init_date,
                    "date-segex":$('input:radio[name="date-segex-'+ID+'"]:checked').val()
                }
            ]};

            data = ['TipoGeorreferencia', 'IdGeorreferencia', 'Operacion', 'Descripcion', 'Observaciones', 'Latitud', 'Longitud', 'TipoReferenciaCatastral', 
                    'ReferenciaCatastral', 'IneMunicipioDireccion', 'ViaDireccion', 'NumeroViaDireccion', 'RestoDireccion',
                    'CodigoExpediente', 'TituloExpediente', 'UrlExpediente', 'EstadoExpediente', 'DescripcionEstadoExpediente',
                    'EstadoFinalizadoExpediente', 'DescripcionEstadoFinalizadoExpediente', 'ProcedimientoExpediente',
                    'TramitadorExpediente', 'FechaCreacionExpediente', 'FechaInicioExpediente', 'FechaFinalizacionExpediente']

            paramsSegex['schema'] = data
            paramsSegex['parameters'][0]['schema'] = data
            
            passSchemaToEdgeConnected(ID, listLabel, data, context.canvas)
            
            isAlreadyInCanvas(jsonParams, paramsSegex, ID)

            icon.setColor('#01b0a0')
            
            $('#dialog-input-segex-'+ID).modal('hide')
        });
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
                        '<h4 class="modal-title">'+paramsTransTpl.replace('{}', gettext('CSV'))+'</h4>'+
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
                            '<br><br><br>'+ 
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

        });

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
        });
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

//// INPUT JSON ////
input_Json = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "input_Json",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text:"JSON", 
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


        $('#canvas-parent').append('<div id="dialog-input-json-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title">'+paramsTransTpl.replace('{}', gettext('JSON'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column20">'+
                                '<label class="col-form-label" >'+gettext('Choose JSON file')+': </label><br>'+
                                '<a href="#" id="select-file-button-'+ID+'" class="btn btn-default btn-sm"><i class="fa fa-folder-open margin-r-5"></i>'+gettext('Select file')+'</a>'+
                            '</div>'+ 
                            '<div class="column80">'+
                                '<label class="col-form-label" >'+gettext('Path:')+'</label>'+
                                '<input type="text" id="json-file-'+ID+'" name="file" class="form-control"></input>'+
                            '</div>'+ 
                            '<div>'+
                                '<input type="checkbox" name="checkbox-json" id="api-rest-'+ID+'"/>'+
                                '<label for="checkbox">'+gettext('Do you want to load JSON data from an API REST?')+'</label>'+											
                            '</div>'+
                            '<div class="more-options-'+ID+'">'+
                                '<label class="col-form-label" >'+gettext('URL:')+'</label>'+
                                '<input type="text" id="url-'+ID+'" name="url" class="form-control"></input>'+
                                /*'<div>'+
                                    '<input type="checkbox" name="checkbox-json" id="is-pag-'+ID+'"/>'+
                                    '<label for="checkbox">'+gettext('Is paginated?')+'</label>'+										
                                '</div>'+
                                '<div class="column30">'+
                                    '<label class="col-form-label" >'+gettext('Pagination parameter:')+'</label>'+
                                    '<input type="text" id="pag-par-'+ID+'" name="pag-par" class="form-control"></input>'+
                                '</div>'+
                                '<div class="column30">'+
                                    '<label form="init" class="col-form-label">'+gettext('Starts in:')+'</label>'+
                                    '<input type="number" id="init-pag-'+ID+'" value=0 min="0" class="form-control" pattern="^[0-9]+">'+
                                '</div>'+*/
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="input-json-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')


        
        $("#api-rest-"+ID).change(function() {
            if($("#api-rest-"+ID).is(':checked')){
                $(".more-options-"+ID).slideDown("slow")
                $("#api-rest-"+ID).val("true")
                $("#json-file-"+ID).prop( "disabled", true );
                $("#select-file-button-"+ID).prop( "disabled", true );
            }else{
                $(".more-options-"+ID).slideUp("slow")
                $("#api-rest-"+ID).val("")
                $( "#json-file-"+ID ).prop( "disabled", false );
                $("#select-file-button-"+ID).prop( "disabled", false );
            }
        });

        /*$("#is-pag-"+ID).change(function() {
            if($("#is-pag-"+ID).is(':checked')){
                $("#is-pag-"+ID).val("true")
                $("#pag-par-"+ID).prop( "disabled", false );
                $("#init-pag-"+ID).prop( "disabled", false );
            }else{
                $("#is-pag-"+ID).val("")
                $("#pag-par-"+ID ).prop( "disabled", true );
                $("#init-pag-"+ID ).prop( "disabled", true );
            }
        });*/

        getPathFile('json', ID)

        var context = this

        icon.on("click", function(){

            if($("#api-rest-"+ID).is(':checked')){
                $(".more-options-"+ID).slideDown("slow")
                $("#api-rest-"+ID).val("true")
                $( "#json-file-"+ID ).prop( "disabled", true );
                $( "#select-file-button-"+ID ).prop( "disabled", true );
            }else{
                $(".more-options-"+ID).slideUp("slow")
                $("#api-rest-"+ID).val("")
                $( "#json-file-"+ID ).prop( "disabled", false );
                $( "#select-file-button-"+ID ).prop( "disabled", false );
            };

            /*if($("#is-pag-"+ID).is(':checked')){
                $("#is-pag-"+ID).val("true")
                $("#pag-par-"+ID).prop( "disabled", false );
                $("#init-pag-"+ID).prop( "disabled", false );
            }else{
                $("#is-pag-"+ID).val("")
                $("#pag-par-"+ID ).prop( "disabled", true );
                $("#init-pag-"+ID ).prop( "disabled", true );
            }*/

            $('#dialog-input-json-'+ID).modal('show')

        });

        $('#input-json-accept-'+ID).click(function() {

            var paramsJSON = {"id": ID,
            "parameters": [
                {"json-file": $('#json-file-'+ID).val(),
                "api-rest": $("#api-rest-"+ID).val(),
                "url": $('#url-'+ID).val(),
                /*"is-pag": $("#is-pag-"+ID).val(),
                "pag-par": $("#pag-par-"+ID ).val(),
                "init-pag": $("#init-pag-"+ID ).val()*/
                }
            ]}

            var formDataSchemaJSON = new FormData();

            formDataSchemaJSON.append('jsonParamsJSON', JSON.stringify(paramsJSON))

            $.ajax({
                type: 'POST',
                url: '/gvsigonline/etl/etl_schema_json/',
                data: formDataSchemaJSON,
                beforeSend:function(xhr){
                    xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
                },
                cache: false, 
                contentType: false, 
                processData: false,
                success: function (data) {
                    paramsJSON['schema'] = data
                    
                    passSchemaToEdgeConnected(ID, listLabel, data, context.canvas)
                    }
                })
    
            isAlreadyInCanvas(jsonParams, paramsJSON, ID)

            icon.setColor('#01b0a0')
            
            $('#dialog-input-json-'+ID).modal('hide')
        });
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


//// INPUT PADRON ALBACETE ////
input_PadronAlbacete = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "input_PadronAlbacete",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text:"Padrón Albacete", 
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


        $('#canvas-parent').append('<div id="dialog-input-padron-alba-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title">Parámetros del Padrón de Albacete</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<label class="col-form-label" > Servicio </label>'+
                                    '<select class="form-control" id="service-'+ID+'">'+
                                        '<option value="PRO"> Producción </option>'+
                                        '<option value="PRE"> Preproducción </option>'+
                                    '</select>'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="input-padron-alba-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        var context = this

        icon.on("click", function(){

            $('#dialog-input-padron-alba-'+ID).modal('show')

        });

        $('#input-padron-alba-accept-'+ID).click(function() {

            var paramsJSON = {"id": ID,
            "parameters": [
                {"service": $('#service-'+ID).val()
                }
            ]}

            var formDataSchemaJSON = new FormData();

            formDataSchemaJSON.append('jsonParamsJSON', JSON.stringify(paramsJSON))

            $.ajax({
                type: 'POST',
                url: '/gvsigonline/etl/etl_schema_padron_alba/',
                data: formDataSchemaJSON,
                beforeSend:function(xhr){
                    xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
                },
                cache: false, 
                contentType: false, 
                processData: false,
                success: function (data) {
                    paramsJSON['schema'] = data
                    
                    passSchemaToEdgeConnected(ID, listLabel, data, context.canvas)
                    }
                })
    
            isAlreadyInCanvas(jsonParams, paramsJSON, ID)

            icon.setColor('#01b0a0')
            
            $('#dialog-input-padron-alba-'+ID).modal('hide')
        });
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
                        '<h4 class="modal-title">'+paramsTransTpl.replace('{}', gettext('Excel'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column20">'+
                                '<label for ="excel-file" class="col-form-label">'+gettext('Choose path:')+'</label><br>'+
                                '<a href="#" id="select-file-button-'+ID+'" class="btn btn-default btn-sm"><i class="fa fa-folder-open margin-r-5"></i>'+gettext('Select path')+'</a><br>'+
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
                            '<br><br><br>'+
                            '<div>'+
                                '<label class="col-form-label" id ="advanced-param-'+ID+'">'+gettext('Advanced Parameters')+'</label>'+
                            '</div>'+
                            '<div id ="more-options-'+ID+'">'+
                                '<div class="column30">'+
                                    '<label class="col-form-label">'+gettext('Reading options:')+'</label>'+
                                    '<div class="form-check">'+
                                        '<input type="radio" id="single-'+ID+'" name="reading-'+ID+'" class="form-check-input" value="single" checked="checked">'+
                                        '<label for="single" class="form-check-label">'+gettext('Single excel file')+'</label>'+
                                    '</div>'+
                                    '<div class="form-check">'+
                                        '<input type="radio" id="multiple-'+ID+'" name="reading-'+ID+'" class="form-check-input" value="multiple">'+
                                        '<label for="multiple" class="form-check-label">'+gettext('All files in a folder')+'</label>'+
                                    '</div>'+
                                '</div>'+
                                '<div class="column70">'+
                                    '<input type="checkbox" name="checkbox-excel" id="move-'+ID+'"/>'+
                                    '<label for="checkbox">'+gettext('Do you want to (re)-move the files after the process is over?')+'</label>'+											
                                '</div>'+
                                '<div class="column20">'+
                                    '<label for ="folder" class="col-form-label">'+gettext('Choose path:')+'</label><br>'+
                                    '<a href="#" id="select-folder-button-'+ID+'" class="btn btn-default btn-sm"><i class="fa fa-folder-open margin-r-5"></i>'+gettext('Select folder')+'</a><br>'+
                                '</div>'+
                                '<div class="column50">'+
                                    '<label class="col-form-label" >'+gettext('Path:')+'</label>'+
                                    '<input type="text" id="folder-'+ID+'" name="folder" class="form-control" placeholder="'+gettext('For removing files leave this input empty')+'"></input>'+
                                '</div>'+
                                '<br><br><br>'+
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

        $("#advanced-param-"+ID).click(function(){
            $("#more-options-"+ID).slideToggle("slow");
        });

        var context = this

        $("#move-"+ID).change(function() {
            if($("#move-"+ID).is(':checked')){
                $("#select-folder-button-"+ID).attr('disabled', false)
                $("#folder-"+ID).attr('disabled', false)
                $("#move-"+ID).val('true')
            }else{
                $("#select-folder-button-"+ID).attr('disabled', true)
                $("#folder-"+ID).attr('disabled', true)
                $("#move-"+ID).val('')
            }
        });

        $('input:radio[name="reading-'+ID+'"]').change(function() {

            if($(this).val()=='single'){
                $("#move-"+ID).prop('checked', false)
                $("#move-"+ID).attr('disabled', true)
                $("#select-folder-button-"+ID).attr('disabled', true)
                $("#folder-"+ID).attr('disabled', true)
            }else{
                $("#move-"+ID).attr('disabled', false)

            }

        })

        icon.on("click", function(){

            $('#select-file-button-'+ID).click(function (e) {
                if ($('input:radio[name="reading-'+ID+'"]:checked').val()=='single'){
                    window.open("/gvsigonline/filemanager/?popup=1","Ratting","width=640, height=480,left=150,top=200,toolbar=0,status=0,scrollbars=1");

                    getPathFile('excel', ID)
                }else{
                    window.open("/gvsigonline/filemanager/?popup=1","Ratting","width=640, height=480,left=150,top=200,toolbar=0,status=0,scrollbars=1");

                    getPathFile('excel/', ID)
                }
            });

            $('#select-folder-button-'+ID).click(function (e) {
                window.open("/gvsigonline/filemanager/?popup=1","Ratting","width=640, height=480,left=150,top=200,toolbar=0,status=0,scrollbars=1");

                getPathFile('folder', ID)
            });

            if ($('input:radio[name="reading-'+ID+'"]:checked').val()=='single'){
                $("#move-"+ID).prop('checked', false)
                $("#move-"+ID).attr('disabled', true)
                $("#select-folder-button-"+ID).attr('disabled', true)
                $("#folder-"+ID).attr('disabled', true)
                $("#more-options-"+ID).slideUp("slow");
            }

            if($("#move-"+ID).is(':checked')){
                $("#select-folder-button-"+ID).attr('disabled', false)
                $("#folder-"+ID).attr('disabled', false)
                $("#move-"+ID).val('true')
            }else{
                $("#select-folder-button-"+ID).attr('disabled', true)
                $("#folder-"+ID).attr('disabled', true)
                $("#move-"+ID).val('')
            }

            $('#dialog-input-excel-'+ID).modal('show')

        });

        $('#get-sheets-'+ID).on("click", function(){
                                
            var formDataSheetExcel = new FormData();

            formDataSheetExcel.append('file', $('#excel-file-'+ID).val())
            formDataSheetExcel.append('reading', $('input:radio[name="reading-'+ID+'"]:checked').val())

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
                    get_ = []

                    for (i = 0; i < data.length; i++){
                        $('#sheet-name-'+ID).append('<option>'+data[i]+'</option>')
                        get_.push(data[i])

                    }
                }
            })
        });

        $('#input-excel-accept-'+ID).click(function() {

            if (typeof get_ === 'undefined'){
                get_ = []
                $("#sheet-name-"+ID+" option").each(function()
                    {
                        get_.push($(this).val())
                    });
            }
            
            var paramsExcel = {"id": ID,
            "parameters": [
                { "get_sheet-name":  get_ ,
                "excel-file": $('#excel-file-'+ID).val(),
                "sheet-name": $('#sheet-name-'+ID).val(),
                "usecols": $('#usecols-'+ID).val(),
                "header": $('#header-'+ID).val(),
                "reading": $('input:radio[name="reading-'+ID+'"]:checked').val(),
                "move": $('#move-'+ID).val(),
                "folder": $('#folder-'+ID).val()
                }
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



//// INPUT XML ////

input_Xml = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "input_Xml",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3, width:1},attr));
        
        this.classLabel = new draw2d.shape.basic.Label({
            text:"XML", 
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

        $('#canvas-parent').append('<div id="dialog-input-xml-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title">'+paramsTransTpl.replace('{}', gettext('XML'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column20">'+
                                '<label for ="xml-file" class="col-form-label">'+gettext('Choose path:')+'</label><br>'+
                                '<a href="#" id="select-file-button-'+ID+'" class="btn btn-default btn-sm"><i class="fa fa-folder-open margin-r-5"></i>'+gettext('Select path')+'</a><br>'+
                            '</div>'+
                            '<div class="column80">'+
                                '<label class="col-form-label" >'+gettext('Path:')+'</label>'+
                                '<input type="text" id="xml-file-'+ID+'" name="file" class="form-control"></input>'+
                            '</div>'+
                            '<div class="column20">'+
                                '<label for ="xml-file" class="col-form-label">'+gettext('Get tags')+':</label><br>'+
                                '<a href="#" id="get-tags-'+ID+'" class="btn btn-default btn-sm">'+gettext('Get tags')+'</a><br>'+
                            '</div>'+
                            '<div class="column80">'+
                                '<select id="tag-list-'+ID+'" multiple style="width: 100%; height:200px">'+
                                '</select>'+
                            '</div>'+
                            '<div>'+
                                '<button type="button" style="float: right;" class="btn btn-default btn-sm" id="quit-'+ID+'"><i class="fa fa-minus" aria-hidden="true"></i></button>'+
                                '<button type="button" style="float: right;" class="btn btn-default btn-sm" id="add-'+ID+'"><i class="fa fa-plus" aria-hidden="true"></i></button>'+
                            '</div><br>'+
                            '<div>'+
                                '<label class="col-form-label" >'+gettext('Schema:')+'</label>'+
                                '<input id="selected-schema-'+ID+'" class="form-control" readonly="readonly"></input>'+
                            '</div>'+
                            '<div>'+
                                '<input type="checkbox" id="add-tags-'+ID+'" value="false" />'+
                                '<label for="checkbox">'+gettext('Add other different tags than the selected schema to all records')+'</label>'+											
                            '</div>'+
                            '<div>'+
                                '<input id="other-tags-'+ID+'" class="form-control" readonly="readonly"></input>'+
                            '</div>'+
                            '<div>'+
                                '<label class="col-form-label" id ="advanced-param-'+ID+'">'+gettext('Advanced Parameters')+'</label>'+
                            '</div>'+
                            '<div id ="more-options-'+ID+'">'+
                                '<div class="column30">'+
                                    '<label class="col-form-label">'+gettext('Reading options:')+'</label>'+
                                    '<div class="form-check">'+
                                        '<input type="radio" id="single-'+ID+'" name="reading-'+ID+'" class="form-check-input" value="single" checked="checked">'+
                                        '<label for="single" class="form-check-label">'+gettext('Single XML file')+'</label>'+
                                    '</div>'+
                                    '<div class="form-check">'+
                                        '<input type="radio" id="multiple-'+ID+'" name="reading-'+ID+'" class="form-check-input" value="multiple">'+
                                        '<label for="multiple" class="form-check-label">'+gettext('All files in a folder')+'</label>'+
                                    '</div>'+
                                '</div>'+
                                '<div class="column70">'+
                                    '<input type="checkbox" name="checkbox-xml" id="move-'+ID+'"/>'+
                                    '<label for="checkbox">'+gettext('Do you want to (re)-move the files after the process is over?')+'</label>'+											
                                '</div>'+
                                '<div class="column20">'+
                                    '<label for ="folder" class="col-form-label">'+gettext('Choose path:')+'</label><br>'+
                                    '<a href="#" id="select-folder-button-'+ID+'" class="btn btn-default btn-sm"><i class="fa fa-folder-open margin-r-5"></i>'+gettext('Select folder')+'</a><br>'+
                                '</div>'+
                                '<div class="column50">'+
                                    '<label class="col-form-label" >'+gettext('Path:')+'</label>'+
                                    '<input type="text" id="folder-'+ID+'" name="folder" class="form-control" placeholder="'+gettext('For removing files leave this input empty')+'"></input>'+
                                '</div>'+
                                '<br><br><br>'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="input-xml-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>') 

        $("#advanced-param-"+ID).click(function(){
            $("#more-options-"+ID).slideToggle("slow");
        });

        var context = this

        $("#move-"+ID).change(function() {
            if($("#move-"+ID).is(':checked')){
                $("#select-folder-button-"+ID).attr('disabled', false)
                $("#folder-"+ID).attr('disabled', false)
                $("#move-"+ID).val('true')
            }else{
                $("#select-folder-button-"+ID).attr('disabled', true)
                $("#folder-"+ID).attr('disabled', true)
                $("#move-"+ID).val('')
            }
        });

        $('input:radio[name="reading-'+ID+'"]').change(function() {

            if($(this).val()=='single'){
                $("#move-"+ID).prop('checked', false)
                $("#move-"+ID).attr('disabled', true)
                $("#select-folder-button-"+ID).attr('disabled', true)
                $("#folder-"+ID).attr('disabled', true)
            }else{
                $("#move-"+ID).attr('disabled', false)
            }
        });

        icon.on("click", function(){


            $('#tag-list-'+ID+' option').each(function(){

                level = $(this).val().split('-')[0]
                tab = '\xa0\xa0\xa0\xa0'.repeat(level)

                $(this).text(tab+$(this).text())

            });

            $('#select-file-button-'+ID).click(function (e) {
                if ($('input:radio[name="reading-'+ID+'"]:checked').val()=='single'){
                    window.open("/gvsigonline/filemanager/?popup=1","Ratting","width=640, height=480,left=150,top=200,toolbar=0,status=0,scrollbars=1");

                    getPathFile('xml', ID)
                }else{
                    window.open("/gvsigonline/filemanager/?popup=1","Ratting","width=640, height=480,left=150,top=200,toolbar=0,status=0,scrollbars=1");

                    getPathFile('xml/', ID)
                }
            });

            $('#select-folder-button-'+ID).click(function (e) {
                window.open("/gvsigonline/filemanager/?popup=1","Ratting","width=640, height=480,left=150,top=200,toolbar=0,status=0,scrollbars=1");

                getPathFile('folder', ID)
            });

            if ($('input:radio[name="reading-'+ID+'"]:checked').val()=='single'){
                $("#move-"+ID).prop('checked', false)
                $("#move-"+ID).attr('disabled', true)
                $("#select-folder-button-"+ID).attr('disabled', true)
                $("#folder-"+ID).attr('disabled', true)
                $("#more-options-"+ID).slideUp("slow");
            }

            if($("#move-"+ID).is(':checked')){
                $("#select-folder-button-"+ID).attr('disabled', false)
                $("#folder-"+ID).attr('disabled', false)
                $("#move-"+ID).val('true')
            }else{
                $("#select-folder-button-"+ID).attr('disabled', true)
                $("#folder-"+ID).attr('disabled', true)
                $("#move-"+ID).val('')
            }

            if($("#add-tags-"+ID).is(':checked')){
                $("#add-tags-"+ID).val('true')
            }else{
                $("#add-tags-"+ID).val('false')

            };

            $("#add-tags-"+ID).change(function() {
                if($("#add-tags-"+ID).is(':checked')){
                    $("#add-tags-"+ID).val('true')
                }else{
                    $("#add-tags-"+ID).val('false')
    
                };
            });

            $('#dialog-input-xml-'+ID).modal('show')

        });


        $('#get-tags-'+ID).on("click", function(){
                                
            var formDataXmlTags = new FormData();

            formDataXmlTags.append('file', $('#xml-file-'+ID).val())
            formDataXmlTags.append('reading', $('input:radio[name="reading-'+ID+'"]:checked').val())

            $.ajax({
                type: 'POST',
                url: '/gvsigonline/etl/etl_xml_tags/',
                data: formDataXmlTags,
                beforeSend:function(xhr){
                    xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
                },
                cache: false, 
                contentType: false, 
                processData: false,
                success: function (data) {

                    $('#tag-list-'+ID).empty()
                    get_ = []

                    for (i = 0; i < data.length; i++){

                        level = parseInt(data[i][0].split('-')[0])

                        tab = '&emsp;'.repeat(level)

                        $('#tag-list-'+ID).append('<option value="'+data[i][0]+'">'+tab+data[i][1]+'</option>')
                        
                        get_.push(data[i])
                    }
                }
            })
        });


        $('#tag-list-'+ID).dblclick(function(){

            valueUnsel = $(this).val()
            
            level = String(parseInt($(this).val()[0].split('-')[0])+1)
            tag = $('#tag-list-'+ID+' option:selected').text().trim()

            $('#tag-list-'+ID+' option[value='+level+'-'+tag+']').prop("selected", true);
            $('#tag-list-'+ID+' option[value='+valueUnsel+']').prop("selected", false);
        
        });

        $( "#add-"+ID ).click(function() {

            textArray =[]

            $('#tag-list-'+ID+' option:selected').each(function()
                {
                    textArray.push($(this).text().trim())
                });

            if ($("#add-tags-"+ID).val()=='false'){
                //console.log($('#tag-list-'+ID+' option:selected').text())
                $('#selected-schema-'+ID).val(textArray)
            }else{

                if($('#other-tags-'+ID).val()==''){
                    $('#other-tags-'+ID).val(textArray)
                }else{
                    $('#other-tags-'+ID).val($('#other-tags-'+ID).val()+','+textArray)
                }
                
            }

        });

        $( "#quit-"+ID ).click(function() {

            if ($("#add-tags-"+ID).val()=='false'){
                $('#selected-schema-'+ID).val('')
            }else{

                tagsArray = $('#other-tags-'+ID).val().split(',')
                tagsArray.pop()
                $('#other-tags-'+ID).val(tagsArray)
                
            }

        });


        $('#input-xml-accept-'+ID).click(function() {

            if (typeof get_ === 'undefined'){
                get_ = []
                $("#tag-list-"+ID+" option").each(function()
                    {
                        get_.push([$(this).val(), $(this).text().trim()])
                    });
            }
            
            var paramsXml = {"id": ID,
            "parameters": [
                {"get_tag-list":  get_ ,
                "xml-file": $('#xml-file-'+ID).val(),
                "tag-list": [$('#tag-list-'+ID).val(), $('#tag-list-'+ID+' option:selected').text().trim()],
                "selected-schema": $('#selected-schema-'+ID).val(),
                "add-tags": $("#add-tags-"+ID).val(),
                "other-tags": $('#other-tags-'+ID).val(),
                "reading": $('input:radio[name="reading-'+ID+'"]:checked').val(),
                "move": $('#move-'+ID).val(),
                "folder": $('#folder-'+ID).val()
                }
            ]}

            
            var schema = $('#selected-schema-'+ID).val().split(',').concat($('#other-tags-'+ID).val().split(','))
            
            paramsXml['schema'] = schema
            paramsXml['parameters'][0]['schema'] = schema

            passSchemaToEdgeConnected(ID, listLabel, schema, context.canvas)

            var formDataSchemaXml = new FormData();
            
            formDataSchemaXml.append('jsonParamsXml', JSON.stringify(paramsXml))

            isAlreadyInCanvas(jsonParams, paramsXml, ID)

            icon.setColor('#01b0a0')

            $('#dialog-input-xml-'+ID).modal('hide')
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
                        '<h4 class="modal-title">'+paramsTransTpl.replace('{}', gettext('Shapefile'))+'</h4>'+
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
                                '<label class="col-form-label">'+gettext('Encoding:')+'</label>'+
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
                            '<br><br><br><br><br><br>'+
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

        });

        $('#input-shp-accept-'+ID).click(function() {

            var paramsSHP = {"id": ID,
            "parameters": [
            { "shp-file": $('#shp-file-'+ID).val(),
              "encode": $('#encode-'+ID).val(),
              "epsg": $('#epsg-'+ID).val()}
            ]}

            var formDataSchemaShape = new FormData();
            formDataSchemaShape.append('file', $('#shp-file-'+ID).val())

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
                    data.unshift('ogc_fid')
                    paramsSHP['schema'] = data
                    passSchemaToEdgeConnected(ID, listLabel, data, context.canvas)
                    }
                })
    
            isAlreadyInCanvas(jsonParams, paramsSHP, ID)

            icon.setColor('#01b0a0')
            
            $('#dialog-input-shp-'+ID).modal('hide')
        });
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
                        '<h4 class="modal-title">'+paramsTransTpl.replace('{}', gettext('Oracle'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<label form="db" class="col-form-label">'+gettext('DB Connection:')+'</label>'+
                                '<select id="db-'+ID+'" class="form-control"></select>'+
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
                            '<br><br><br>'+ 
                            '<div class="col-md-12">'+
                                '<input type="checkbox" name="checkbox-oracle" id="checkbox-'+ID+'"/>'+
                                '<label for="checkbox">'+gettext('Do you want to write a SQL statement?')+'</label>'+											
                            '</div>'+
                            '<div class="more-options-'+ID+'">'+
                                '<label class="col-form-label">'+gettext('SQL statement:')+'</label>'+
                                '<textarea id="sql-'+ID+'" rows="10" class="form-control" placeholder=""></textarea>'+
                            '</div>'+
                            
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="input-oracle-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        var context = this

        for(i=0;i<dbc.length;i++){

            if(dbc[i].type == 'Oracle'){
                $('#db-'+ID).append(
                    '<option value="'+dbc[i].name+'">'+dbc[i].name+'</option>'
                );
            }
        };

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
        

        icon.on("click", function(){

            optionList = []
            $('#db-'+ID+' option').each(function() {
                optionList.push($(this).val())
              });

            for(i=0;i<dbc.length;i++){

                if(dbc[i].type == 'Oracle'){

                    if (! optionList.includes(dbc[i].name)){
                        $('#db-'+ID).append(
                            '<option value="'+dbc[i].name+'">'+dbc[i].name+'</option>'
                        );
                    }

                }
            };

            $('#dialog-input-oracle-'+ID).modal('show')

            if($("#checkbox-"+ID).is(':checked')){
                $(".more-options-"+ID).slideDown("slow")
                $("#checkbox-"+ID).val("true")
            }else{
                $(".more-options-"+ID).slideUp("slow")
                $("#checkbox-"+ID).val("")
            }
            
        });

        $('#get-owners-'+ID).on("click", function(){
                                
            var paramsOracleOwners = {"id": ID,
            "parameters": [
                {"db": $('#db-'+ID).val()}
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
                {"db": $('#db-'+ID).val(),
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
                {"db": $('#db-'+ID).val(),
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
        });

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

//// INPUT SQL SERVER ////

input_SqlServer = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "input_SqlServer",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3, width:1},attr));
        
        this.classLabel = new draw2d.shape.basic.Label({
            text:"SQL Server", 
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

        $('#canvas-parent').append('<div id="dialog-input-sql-server-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title">'+paramsTransTpl.replace('{}', gettext('SQL Server'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<label form="db" class="col-form-label">'+gettext('DB Connection:')+'</label>'+
                                '<select id="db-'+ID+'" class="form-control"></select>'+
                            '</div>'+
                            '<div class="column20">'+
                                '<label for ="get-schemas" class="col-form-label">'+gettext('Get schemas')+':</label><br>'+
                                '<a href="#" id="get-schemas-'+ID+'" class="btn btn-default btn-sm">'+gettext('Get schemas')+'</a><br>'+
                            '</div>'+
                            '<div class="column80">'+
                                '<label form="schema-name" class="col-form-label">'+gettext('Schema')+':</label>'+
                                '<select class="form-control" id="schema-name-'+ID+'"> </select>'+
                            '</div>'+
                            '<div class="column20">'+
                                '<label for ="get-tables" class="col-form-label">'+gettext('Get tables')+':</label><br>'+
                                '<a href="#" id="get-tables-'+ID+'" class="btn btn-default btn-sm">'+gettext('Get tables')+'</a><br>'+
                            '</div>'+
                            '<div class="column80">'+
                                '<label form="table-name" class="col-form-label">'+gettext('Table')+':</label>'+
                                '<select class="form-control" id="table-name-'+ID+'"> </select>'+
                            '</div>'+
                            '<br><br><br>'+ 
                            '<div class="col-md-12">'+
                                '<input type="checkbox" name="checkbox-sql-server" id="checkbox-'+ID+'"/>'+
                                '<label for="checkbox">'+gettext('Do you want to write a SQL statement?')+'</label>'+											
                            '</div>'+
                            '<div class="more-options-'+ID+'">'+
                                '<label class="col-form-label">'+gettext('SQL statement:')+'</label>'+
                                '<textarea id="sql-'+ID+'" rows="10" class="form-control" placeholder=""></textarea>'+
                            '</div>'+
                            
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="input-sql-server-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        var context = this

        for(i=0;i<dbc.length;i++){

            if(dbc[i].type == 'SQLServer'){
                $('#db-'+ID).append(
                    '<option value="'+dbc[i].name+'">'+dbc[i].name+'</option>'
                );
            }
        };

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
        

        icon.on("click", function(){

            if (typeof get_sch === 'undefined'){

                get_sch = []
    
                $("#schema-name-"+ID+" option").each(function()
                    {  
                        get_sch.push($(this).val())
                    }
                );
            }
    
            if (typeof get_tbl === 'undefined'){
    
                get_tbl = []
    
                $("#table-name-"+ID+" option").each(function()
                    {  
                        get_tbl.push($(this).val())
                    }
                );
            }

            optionList = []
            $('#db-'+ID+' option').each(function() {
                optionList.push($(this).val())
              });

            for(i=0;i<dbc.length;i++){

                if(dbc[i].type == 'SQLServer'){

                    if (! optionList.includes(dbc[i].name)){
                        $('#db-'+ID).append(
                            '<option value="'+dbc[i].name+'">'+dbc[i].name+'</option>'
                        );
                    }

                }
            };

            $('#dialog-input-sql-server-'+ID).modal('show')

            if($("#checkbox-"+ID).is(':checked')){
                $(".more-options-"+ID).slideDown("slow")
                $("#checkbox-"+ID).val("true")
            }else{
                $(".more-options-"+ID).slideUp("slow")
                $("#checkbox-"+ID).val("")
            }
            
        });

        $('#get-schemas-'+ID).on("click", function(){
                                
            var paramsSQLServerSchemas = {"id": ID,
            "parameters": [
                {"db": $('#db-'+ID).val()}
            ]}

            var formDataSQLServerSchemas = new FormData();
            
            formDataSQLServerSchemas.append('jsonParamsSQLServer', JSON.stringify(paramsSQLServerSchemas))

            $.ajax({
                type: 'POST',
                url: '/gvsigonline/etl/etl_schemas_sqlserver/',
                data: formDataSQLServerSchemas,
                beforeSend:function(xhr){
                    xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
                },
                cache: false, 
                contentType: false, 
                processData: false,
                success: function (data) {

                    $('#schema-name-'+ID).empty()
                    get_sch = []

                    for (i = 0; i < data.length; i++){
                        $('#schema-name-'+ID).append('<option>'+data[i]+'</option>')
                        get_sch.push(data[i])

                    }
                }
            })
        });

        $('#get-tables-'+ID).on("click", function(){
                            
            var paramsSqlServerTables = {"id": ID,
            "parameters": [
                {"db": $('#db-'+ID).val(),
                "schema-name": $('#schema-name-'+ID).val()}
            ]}

            var formDataSqlServerTables = new FormData();
            
            formDataSqlServerTables.append('jsonParamsSQLServer', JSON.stringify(paramsSqlServerTables))

            $.ajax({
                type: 'POST',
                url: '/gvsigonline/etl/etl_tables_sqlserver/',
                data: formDataSqlServerTables,
                beforeSend:function(xhr){
                    xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
                },
                cache: false, 
                contentType: false, 
                processData: false,
                success: function (data) {

                    get_tbl = []
                    $('#table-name-'+ID).empty()

                    for (i = 0; i < data.length; i++){
                        $('#table-name-'+ID).append('<option>'+data[i]+'</option>')
                        get_tbl.push(data[i])

                    }
                }
            })
        });


        $('#input-sql-server-accept-'+ID).click(function() {
            
            var paramsDataSchemaSqlServer = {"id": ID,
            "parameters": [
                {"get_schema-name": get_sch,
                "get_table-name": get_tbl,
                "db": $('#db-'+ID).val(),
                "schema-name": $('#schema-name-'+ID).val(),
                "table-name": $('#table-name-'+ID).val(),
                "checkbox": $("#checkbox-"+ID).val(),
                "sql": $('#sql-'+ID).val()}
            ]}

            var formDataDataSchemaSqlServer = new FormData();
            
            formDataDataSchemaSqlServer.append('jsonSqlServer', JSON.stringify(paramsDataSchemaSqlServer))

            $.ajax({
                type: 'POST',
                url: '/gvsigonline/etl/etl_data_schema_sqlserver/',
                data: formDataDataSchemaSqlServer,
                beforeSend:function(xhr){
                    xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
                },
                cache: false, 
                contentType: false, 
                processData: false,
                success: function (data) {
                    paramsDataSchemaSqlServer['schema'] = data

                    passSchemaToEdgeConnected(ID, listLabel, data, context.canvas)
                    
                    }
                })
            
            isAlreadyInCanvas(jsonParams, paramsDataSchemaSqlServer, ID)

            icon.setColor('#01b0a0')

            $('#dialog-input-sql-server-'+ID).modal('hide')
        });

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
            text:"PgSQL/PostGIS", 
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
                        '<h4 class="modal-title">'+paramsTransTpl.replace('{}', gettext('PostGIS'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<label form="db" class="col-form-label">'+gettext('DB Connection:')+'</label>'+
                                '<select id="db-'+ID+'" class="form-control"></select>'+
                            '</div>'+
                            '<div class="column20">'+
                                '<label for ="get-schemas" class="col-form-label">'+gettext('Get schemas')+':</label><br>'+
                                '<a href="#" id="get-schemas-'+ID+'" class="btn btn-default btn-sm">'+gettext('Get schemas')+'</a><br>'+
                            '</div>'+

                            '<div class="column80">'+
                                '<label form="schema" class="col-form-label">'+gettext('Schema:')+'</label>'+
                                '<select id="schema-name-'+ID+'" class="form-control"></select>'+
                            '</div>'+

                            '<div class="column20">'+
                                '<label for ="get-tables" class="col-form-label">'+gettext('Get tables')+':</label><br>'+
                                '<a href="#" id="get-tables-'+ID+'" class="btn btn-default btn-sm">'+gettext('Get tables')+'</a><br>'+
                            '</div>'+

                            '<div class="column80">'+
                                '<label form="tablename" class="col-form-label">'+gettext('Table name:')+'</label>'+
                                '<select id="tablename-'+ID+'" class="form-control"></select>'+
                            '</div>'+
                            '<div class="col-md-12">'+
                                '<input type="checkbox" name="checkbox-postgres" id="checkbox-'+ID+'"/>'+
                                '<label for="checkbox">'+gettext('Do you want to write a SQL WHERE Clause?')+'</label>'+											
                            '</div>'+
                            '<div class="more-options-'+ID+'">'+
                                '<label class="col-form-label">'+gettext('SQL WHERE Clause:')+'</label>'+
                                '<textarea id="clause-'+ID+'" rows="1" class="form-control" placeholder=""></textarea>'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="input-postgis-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')


        for(i=0;i<dbc.length;i++){

            if(dbc[i].type == 'PostgreSQL'){
                $('#db-'+ID).append(
                    '<option value="'+dbc[i].name+'">'+dbc[i].name+'</option>'
                );
            }
        };


        $("#checkbox-"+ID).change(function() {
            if($("#checkbox-"+ID).is(':checked')){
                $(".more-options-"+ID).slideDown("slow")
                $("#checkbox-"+ID).val("true")
            }else{
                $(".more-options-"+ID).slideUp("slow")
                $("#checkbox-"+ID).val("")
            }
        });

        $('#get-schemas-'+ID).on("click", function(){
                                
            var paramsGetSchemas = {"id": ID,
            "parameters": [
                {"db": $('#db-'+ID).val()}
            ]}

            var formDataGetSchemas = new FormData();
            
            formDataGetSchemas.append('jsonParams', JSON.stringify(paramsGetSchemas))

            $.ajax({
                type: 'POST',
                url: '/gvsigonline/etl/etl_schemas_name_postgres/',
                data: formDataGetSchemas,
                beforeSend:function(xhr){
                    xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
                },
                cache: false, 
                contentType: false, 
                processData: false,
                success: function (data) {

                    $('#schema-name-'+ID).empty()
                    get_sch = []

                    for (i = 0; i < data.length; i++){
                        $('#schema-name-'+ID).append('<option>'+data[i]+'</option>')
                        get_sch.push(data[i])


                    }
                }
            })
        });


        $('#get-tables-'+ID).on("click", function(){
                                
            var paramsGetSchemas = {"id": ID,
            "parameters": [
                {"db": $('#db-'+ID).val(),
                "schema-name": $('#schema-name-'+ID).val()}
            ]}

            var formDataGetSchemas = new FormData();
            
            formDataGetSchemas.append('jsonParams', JSON.stringify(paramsGetSchemas))

            $.ajax({
                type: 'POST',
                url: '/gvsigonline/etl/etl_table_name_postgres/',
                data: formDataGetSchemas,
                beforeSend:function(xhr){
                    xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
                },
                cache: false, 
                contentType: false, 
                processData: false,
                success: function (data) {
                    get_tbl = []
                    $('#tablename-'+ID).empty()

                    for (i = 0; i < data.length; i++){
                        $('#tablename-'+ID).append('<option>'+data[i]+'</option>')
                        get_tbl.push(data[i])

                    }
                }
            })
        });

        var context = this

        icon.on("click", function(){

            if (typeof get_sch === 'undefined'){

                get_sch = []
    
                $("#schema-name-"+ID+" option").each(function()
                    {  
                        get_sch.push($(this).val())
                    }
                );
            }
    
            if (typeof get_tbl === 'undefined'){
    
                get_tbl = []
    
                $("#tablename-"+ID+" option").each(function()
                    {  
                        get_tbl.push($(this).val())
                    }
                );
            }

            optionList = []
            $('#db-'+ID+' option').each(function() {
                optionList.push($(this).val())
              });
    
            for(i=0;i<dbc.length;i++){
    
                if(dbc[i].type == 'PostgreSQL'){
    
                    if (! optionList.includes(dbc[i].name)){
                        $('#db-'+ID).append(
                            '<option value="'+dbc[i].name+'">'+dbc[i].name+'</option>'
                        );
                    }
    
                }
            };

            $('#dialog-input-postgis-'+ID).modal('show')

            if($("#checkbox-"+ID).is(':checked')){
                $(".more-options-"+ID).slideDown("slow")
                $("#checkbox-"+ID).val("true")
            }else{
                $(".more-options-"+ID).slideUp("slow")
                $("#checkbox-"+ID).val("")
            }
        });

        $('#input-postgis-accept-'+ID).click(function() {
                
            var paramsPostgis = {"id": ID,
            "parameters": [
                {"get_schema-name": get_sch,
                "get_tablename": get_tbl,
                "db": $('#db-'+ID).val(),
                "schema-name": $('#schema-name-'+ID).val(),
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
        });
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

//// INPUT KMZ/KML ////

input_Kml = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "input_Kml",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text:"KML/KMZ",
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

        $('#canvas-parent').append('<div id="dialog-input-kml-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title">'+paramsTransTpl.replace('{}', gettext('KML/KMZ'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column20">'+
                                '<label for ="shp-file" class="col-form-label">'+gettext('Choose file:')+'</label><br>'+
                                '<a href="#" id="select-file-button-'+ID+'" class="btn btn-default btn-sm"><i class="fa fa-folder-open margin-r-5"></i>'+gettext('Select file')+'</a><br>'+
                            '</div>'+
                            '<div class="column80">'+
                                '<label class="col-form-label" >'+gettext('Path:')+'</label>'+
                                '<input type="text" id="kml-kmz-file-'+ID+'" name="file" class="form-control"></input>'+
                            '</div>'+
                            '<div class="column20">'+
                                '<label class="col-form-label">'+gettext('Encoding:')+'</label>'+
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
                                    '<option value="">'+gettext('Insert if needed')+'</option>'+
                                '</select>'+
                            '</div>'+

                            '<br><br><br>'+
                            '<div>'+
                                '<label class="col-form-label" id ="advanced-param-'+ID+'">'+gettext('Advanced Parameters')+'</label>'+
                            '</div>'+
                            '<div id ="more-options-'+ID+'">'+
                                '<div>'+
                                    '<input type="checkbox" name="checkbox-excel" id="move-'+ID+'"/>'+
                                    '<label for="checkbox">'+gettext('Do you want to (re)-move the files after the process is over?')+'</label>'+											
                                '</div>'+
                                '<div class="column20">'+
                                    '<label for ="folder" class="col-form-label">'+gettext('Choose path:')+'</label><br>'+
                                    '<a href="#" id="select-folder-button-'+ID+'" class="btn btn-default btn-sm"><i class="fa fa-folder-open margin-r-5"></i>'+gettext('Select folder')+'</a><br>'+
                                '</div>'+
                                '<div class="column50">'+
                                    '<label class="col-form-label" >'+gettext('Path:')+'</label>'+
                                    '<input type="text" id="folder-'+ID+'" name="folder" class="form-control" placeholder="'+gettext('For removing files leave this input empty')+'"></input>'+
                                '</div>'+
                                '<br><br><br>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="input-kml-accept-'+ID+'">'+gettext('Accept')+'</button>'+
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

        getPathFile('kml-kmz', ID)

        var context = this

        $("#advanced-param-"+ID).click(function(){
            $("#more-options-"+ID).slideToggle("slow");
        });

        $("#move-"+ID).change(function() {
            if($("#move-"+ID).is(':checked')){
                $("#select-folder-button-"+ID).attr('disabled', false)
                $("#folder-"+ID).attr('disabled', false)
                $("#move-"+ID).val('true')
            }else{
                $("#select-folder-button-"+ID).attr('disabled', true)
                $("#folder-"+ID).attr('disabled', true)
                $("#move-"+ID).val('')
            }
        });


        icon.on("click", function(){

            $('#select-file-button-'+ID).click(function (e) {
                window.open("/gvsigonline/filemanager/?popup=1","Ratting","width=640, height=480,left=150,top=200,toolbar=0,status=0,scrollbars=1");

                getPathFile('kml-kmz', ID)

            });


            $('#select-folder-button-'+ID).click(function (e) {
                window.open("/gvsigonline/filemanager/?popup=1","Ratting","width=640, height=480,left=150,top=200,toolbar=0,status=0,scrollbars=1");

                getPathFile('folder', ID)
            });


            $("#more-options-"+ID).slideUp("slow");

            if($("#move-"+ID).is(':checked')){
                $("#select-folder-button-"+ID).attr('disabled', false)
                $("#folder-"+ID).attr('disabled', false)
                $("#move-"+ID).val('true')
                $("#more-options-"+ID).slideDown("slow");
            }else{
                $("#select-folder-button-"+ID).attr('disabled', true)
                $("#folder-"+ID).attr('disabled', true)
                $("#move-"+ID).val('')
            }

            $('#dialog-input-kml-'+ID).modal('show')
        })

        $('#input-kml-accept-'+ID).click(function() {

            var paramsKml = {"id": ID,
            "parameters": [
            { "kml-kmz-file": $('#kml-kmz-file-'+ID).val(),
              "encode": $('#encode-'+ID).val(),
              "epsg": $('#epsg-'+ID).val(),
              //"reading": $('input:radio[name="reading-'+ID+'"]:checked').val(),
              "move": $('#move-'+ID).val(),
              "folder": $('#folder-'+ID).val()}
            ]}

            var formDataSchemaKML = new FormData();
            formDataSchemaKML.append('file', $('#kml-kmz-file-'+ID).val())

            $.ajax({
                type: 'POST',
                url: '/gvsigonline/etl/etl_schema_kml/',
                data: formDataSchemaKML,
                beforeSend:function(xhr){
                    xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
                },
                cache: false, 
                contentType: false, 
                processData: false,
                success: function (data) {
                    paramsKml['schema'] = data
                    passSchemaToEdgeConnected(ID, listLabel, data, context.canvas)
                    }
                })
    
            isAlreadyInCanvas(jsonParams, paramsKml, ID)

            icon.setColor('#01b0a0')
            
            $('#dialog-input-kml-'+ID).modal('hide')
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

/////////////////////////////////////////////////// CREATORS ///////////////////////////////////////////////////////////
//// GRID ////

crea_Grid = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "crea_Grid",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3, width:1},attr));
        
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Grid"), 
            stroke:1,
            fontColor:"#ffffff",  
            bgColor:"#c1a7ed",
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

        $('#canvas-parent').append('<div id="dialog-create-grid-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title">'+paramsTransTpl.replace('{}', gettext('Grid'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+

                            '<div>'+
                                '<label class="col-form-label">'+gettext('How to create the grid?')+'</label>'+
                                '<div class="form-check">'+
                                    '<input type="radio" id="extent-'+ID+'" name="create-'+ID+'" class="form-check-input" value="Extent" checked="checked">'+
                                    '<label for="create" class="form-check-label">'+gettext('Grid from extent of input geometry')+'</label>'+
                                '</div>'+
                                
                                '<div class="form-check">'+
                                    '<input type="radio" id="coordinates-'+ID+'" name="create-'+ID+'" class="form-check-input" value="Coordinates">'+
                                    '<label for="create" class="form-check-label">'+gettext('Grid from initial coordinates (Lower left corner)')+'</label>'+
                                '</div>'+
                            '</div>'+

                            '<div class="column50">'+
                                '<label form="rows" class="col-form-label">'+gettext('Rows')+'</label>'+
                                '<input type="number" id="rows-'+ID+'" value=0 min="1" class="form-control" disabled pattern="^[0-9]+">'+
                            '</div>'+

                            '<div class="column50">'+
                                '<label form="columns" class="col-form-label">'+gettext('Columns')+'</label>'+
                                '<input type="number" id="columns-'+ID+'" value=0 min="1" class="form-control" disabled pattern="^[0-9]+">'+
                            '</div>'+

                            '<div class="column50">'+
                                '<label form="width" class="col-form-label">'+gettext('Width')+'</label>'+
                                '<input type="number" id="width-'+ID+'" value=0 min="0" class="form-control" pattern="^[0-9]+">'+
                            '</div>'+

                            '<div class="column50">'+
                                '<label form="height" class="col-form-label">'+gettext('Height')+'</label>'+
                                '<input type="number" id="height-'+ID+'" value=0 min="0" class="form-control" pattern="^[0-9]+">'+
                            '</div>'+

                            '<div class="column50">'+
                                '<label form="initial-x" class="col-form-label">'+gettext('Initial X')+'</label>'+
                                '<input type="number" id="init-x-'+ID+'" value=0 min="0" class="form-control" disabled pattern="^[0-9]+">'+
                            '</div>'+

                            '<div class="column50">'+
                                '<label form="initial-y" class="col-form-label">'+gettext('Initial Y')+'</label>'+
                                '<input type="number" id="init-y-'+ID+'" value=0 min="0" class="form-control" disabled pattern="^[0-9]+">'+
                            '</div>'+

                            '<div>'+
                                '<label class="col-form-label">'+gettext("EPSG")+'</label>'+
                                '<select id="epsg-'+ID+'" class="form-control">'+
                                    '<option value="">----</option>'+
                                '</select>'+
                            '</div>'+
                        
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="create-grid-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        var context = this

        for(i=0;i<srs.length;i++){

            epsg = srs[i].code.split(":")[1]

            $('#epsg-'+ID).append(
                '<option value="'+epsg+'">'+srs[i].code+' - '+srs[i].title+'</option>'
            );
        }

        $('input:radio[name="create-'+ID+'"]').change(function(){
            if ($(this).val() == 'Extent'){
                
                $('#rows-'+ID).prop('disabled', true)
                $('#columns-'+ID).prop('disabled', true)
                $('#init-x-'+ID).prop('disabled', true)
                $('#init-y-'+ID).prop('disabled', true)
                $('#epsg-'+ID).prop('disabled', true)
                
            }
            else if ($(this).val() == 'Coordinates'){
            
                $('#rows-'+ID).prop('disabled', false)
                $('#columns-'+ID).prop('disabled', false)
                $('#init-x-'+ID).prop('disabled', false)
                $('#init-y-'+ID).prop('disabled', false)
                $('#epsg-'+ID).prop('disabled', false)
            }
        });

        icon.on("click", function(){

            if ($('input:radio[name="create-'+ID+'"]:checked').val() == 'Extent'){

                $('#rows-'+ID).prop('disabled', true)
                $('#columns-'+ID).prop('disabled', true)
                $('#init-x-'+ID).prop('disabled', true)
                $('#init-y-'+ID).prop('disabled', true)
                $('#epsg-'+ID).prop('disabled', true)

            }
            else if ($('input:radio[name="create-'+ID+'"]:checked').val() == 'Coordinates'){
                
                $('#rows-'+ID).prop('disabled', false)
                $('#columns-'+ID).prop('disabled', false)
                $('#init-x-'+ID).prop('disabled', false)
                $('#init-y-'+ID).prop('disabled', false)
                $('#epsg-'+ID).prop('disabled', false)
            }

            $('#dialog-create-grid-'+ID).modal('show')

        });

        $('#create-grid-accept-'+ID).click(function() {
                
            var paramsGrid = {"id": ID,
            "parameters": [
                {"create": $('input:radio[name="create-'+ID+'"]:checked').val(),
                "rows": $('#rows-'+ID).val(),
                "columns": $('#columns-'+ID).val(),
                "width": $("#width-"+ID).val(),
                "height": $('#height-'+ID).val(),
                "init-x": $('#init-x-'+ID).val(),
                "init-y": $("#init-y-"+ID).val(),
                "epsg": $('#epsg-'+ID).val()}
            ]}

            data = ['_row', '_column']

            paramsGrid['schema'] = data
            paramsGrid['parameters'][0]['schema'] = data
            
            passSchemaToEdgeConnected(ID, listLabel, data, context.canvas)
            
            isAlreadyInCanvas(jsonParams, paramsGrid, ID)
            
            icon.setColor('#8e57eb')
                    
            $('#dialog-create-grid-'+ID).modal('hide')
        });
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
        var label1 =new draw2d.shape.basic.Label({
            text: gettext('Input')+' (Op.)',
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:10, top:3, right:10, bottom:5},
            fontColor:"#8e57eb",
         resizeable:true
        });

	   	 var label2 =new draw2d.shape.basic.Label({
	   	     text: gettext('Output'),
	   	     stroke:0.2,
	   	     radius:0,
	   	     bgColor:"#ffffff",
	   	     padding:{left:40, top:3, right:10, bottom:5},
	   	     fontColor:"#8e57eb",
	   	     resizeable:true
	   	 });

        var input1 = label1.createPort("input");
        input1.setName("input_"+label1.id);

        var output = label2.createPort("output");
        output.setName("output_"+label2.id);

	    if($.isNumeric(optionalIndex)){
            this.add(label1, null, optionalIndex+1);
            this.add(label2, null, optionalIndex+1);
	    }
	    else{
            this.add(label1);
            this.add(label2);

        }
         
        listLabel.push([this.id, [input1.name], [output.name]])

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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Join'))+'</h4>'+
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
                            '<br><br><br>'+
                            '<button type="button" style="float: right;" class="btn btn-default btn-sm" id="quit-'+ID+'"><i class="fa fa-minus" aria-hidden="true"></i></button>'+
                            '<button type="button" style="float: right;" class="btn btn-default btn-sm" id="add-'+ID+'"><i class="fa fa-plus" aria-hidden="true"></i></button>'+
                            
                            '<br><br><br>'+
                            '<div class="column50">'+
                                '<input id="attr-1-'+ID+'" type="text" size="40" value="" class="form-control" pattern="[A-Za-z]{3}" >'+
                            '</div>'+
                            '<div class="column50">'+
                                '<input id="attr-2-'+ID+'" type="text" size="40" value="" class="form-control" pattern="[A-Za-z]{3}" >'+
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

        $('#attr-1-'+ID).attr('disabled', true)
        $('#attr-2-'+ID).attr('disabled', true)
        
        $( "#add-"+ID ).click(function() {

            if ($("#attr-1-"+ID).val()=='' && $("#attr-2-"+ID).val()==''){
                $("#attr-1-"+ID).val($("#attr1-"+ID).val())
                $("#attr-2-"+ID).val($("#attr2-"+ID).val())
            }else{
                $("#attr-1-"+ID).val($("#attr-1-"+ID).val() +' '+ $("#attr1-"+ID).val())
                $("#attr-2-"+ID).val($("#attr-2-"+ID).val() +' ' +$("#attr2-"+ID).val())
            }

          });

          $( "#quit-"+ID ).click(function() {
            
            at1 = $("#attr-1-"+ID).val().split(" ")
            at1.pop()
            at1 = at1.join(" ")
            
            at2 = $("#attr-2-"+ID).val().split(" ")
            at2.pop()
            at2 = at2.join(" ")

            $("#attr-1-"+ID).val(at1)
            $("#attr-2-"+ID).val(at2)


          });
        
        
      var context = this

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

                    for (i = 0; i < schemaEdge[0].length; i++){
                        $('#attr1-'+ID).append('<option>'+schemaEdge[0][i]+'</option>')
                    }
                    for (i = 0; i < schemaEdge[1].length; i++){
                        $('#attr2-'+ID).append('<option>'+schemaEdge[1][i]+'</option>')
                    }
                }

            },100);

            $('#dialog-join-'+ID).modal('show')

        });

        $('#join-accept-'+ID).click(function() {
            //importante el orden de estos parametros, los mismos que en el formulario
            var paramsJoin = {"id": ID,
            "parameters": [
                {"attr1": $('#attr1-'+ID).val(),
                "attr2": $('#attr2-'+ID).val(),
                "attr-1": $('#attr-1-'+ID).val(),
                "attr-2": $('#attr-2-'+ID).val(),
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

        });
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

//// JOIN ////

trans_NearestNeighbor = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_NearestNeighbor",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
        
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext('Nearest Neighbor'), 
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

        $('#canvas-parent').append('<div id="dialog-neighbor-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Nearest Neighbor'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<label form="attr1" class="col-form-label">'+gettext('Group by:')+'</label>'+
                                '<select class="form-control" id="attr-'+ID+'">'+
                                '<option></option>'+
                                '</select>'+
                            '</div>'+
                            '<div>'+
                                '<label form="tol" class="col-form-label">'+gettext('Tolerance')+':</label>'+
                                '<input id="tol-'+ID+'" type="number" value="" min="0" step="0.010" class="form-control" >'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="neighbor-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')
        
        
      var context = this

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
                    $('#attr-'+ID).append('<option> </option>')
                    for (i = 0; i < schemaEdge[0].length; i++){
                        $('#attr-'+ID).append('<option>'+schemaEdge[0][i]+'</option>')
                    }
                }

            },100);

            $('#dialog-neighbor-'+ID).modal('show')

        });

        $('#neighbor-accept-'+ID).click(function() {
            //importante el orden de estos parametros, los mismos que en el formulario
            var paramsNeighbor = {"id": ID,
            "parameters": [
                {"attr": $('#attr-'+ID).val(),
                "tol": $('#tol-'+ID).val()}
            ]}

            paramsNeighbor['schema-old'] = schemaEdge

            if (Array.isArray(schemaEdge[0])){
                
                chars = schemaEdge[0].concat(schemaEdge[1])

                let unique = chars.filter((c, index) => {
                    return chars.indexOf(c) === index;
                });

                unique.push('_distance')

                schemaMod = [unique, schemaEdge[0],schemaEdge[1]]
            }
            else{
                schemaMod = [...schemaEdge]
            }

            paramsNeighbor['schema'] = schemaMod

            passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)

            isAlreadyInCanvas(jsonParams, paramsNeighbor, ID)

            icon.setColor('#4682B4')
            
            $('#dialog-neighbor-'+ID).modal('hide')

        });
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
            text: gettext('Matched'),
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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Compare Rows'))+'</h4>'+
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
        
      var context = this

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

        });

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

        });
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

      var context = this
        
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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Remove Attribute'))+'</h4>'+
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

        });

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

        });
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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext("Rename Attribute"))+'</h4>'+
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
        
      var context = this

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

        });

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

        });
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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext("Concatenate Attributes"))+'</h4>'+
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
        
      var context = this

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

        });

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

        });

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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext("Pad Attribute"))+'</h4>'+
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
                                '<select class="form-control" id="side-option-'+ID+'">' +
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
        
      var context = this

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

        });

        $('#pad-attr-accept-'+ID).click(function() {

            var paramsPad = {"id": ID,
            "parameters": [
                {"attr": $('#attr-'+ID).val(),
                "length": $('#length-'+ID).val(),
                "side-option": $('#side-option-'+ID).val(),
                "string": $('#string-'+ID).val()}
            ]}

            schemaMod =[...schemaEdge]
            schemaMod.splice(schemaMod.indexOf($('#attr-'+ID).val()), 1)
            schemaMod.push($('#attr-'+ID).val())

            paramsPad['schema-old'] = schemaEdge
            paramsPad['schema'] = schemaMod

            passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)

            isAlreadyInCanvas(jsonParams, paramsPad, ID)

            icon.setColor('#4682B4')
            
            $('#dialog-pad-attr-'+ID).modal('hide')

        });
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

      var context = this
        
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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Filter Duplicate'))+'</h4>'+
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

        });

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

        });

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

//// VALIDATE GEOMETRIES ////

trans_ValGeom = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_ValGeom",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Validate Geometry"), 
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

      var context = this
        
        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        //adding dialog for choosing parameters of the transformer
        $('#canvas-parent').append('<div id="dialog-val-geom-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Validate Geometry'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                        '<div>'+
                            '<input type="checkbox" id="stop-'+ID+'" value="false" />'+
                            '<label for="checkbox">'+gettext('Stop workspace if there are invalid geometries')+'</label>'+											
                        '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="val-geom-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        $("#stop-"+ID).change(function() {
            if ($('#stop-'+ID).is(':checked')) {
                $('#stop-'+ID).val('true')
            }else{
                $('#stop-'+ID).val('false')
            }
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
                }

            },100);
            
            $('#dialog-val-geom-'+ID).modal('show')

        });

        if ($('#stop-'+ID).is(':checked')) {
            $('#stop-'+ID).val('true')
        }else{
            $('#stop-'+ID).val('false')
        }

        console.log($('#stop-'+ID).val())

        $('#val-geom-accept-'+ID).click(function() {

            //parameters selected to json
            var paramsValGeom = {"id": ID,
            "parameters": [
            {"stop": $('#stop-'+ID).val()}
            ]}
            
            paramsValGeom['schema-old'] = schemaEdge

            schemaModA = [...schemaEdge]
            schemaModB = [...schemaEdge]
            
            schemaMod = [schemaModA.concat(['_valid']), schemaModB.concat(['_valid', '_reason', '_location'])]
            
            paramsValGeom['schema'] = schemaMod

            passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)
            
            isAlreadyInCanvas(jsonParams, paramsValGeom, ID)

            icon.setColor('#4682B4')
            
            $('#dialog-val-geom-'+ID).modal('hide')

        });

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
            text: gettext("Valid"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

        var label3 =new draw2d.shape.basic.Label({
            text: gettext("Invalid"),
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

//// SIMPLE GEOMETRIES ////

trans_SimpGeom = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_SimpGeom",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Simple Geometry"), 
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

      var context = this
        
        var ID = this.id

        setColorIfIsOpened(jsonParams, this.cssClass, ID, icon)

        //adding dialog for choosing parameters of the transformer
        $('#canvas-parent').append('<div id="dialog-simp-geom-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Simple Geometry'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                        '<div>'+
                            '<input type="checkbox" id="stop-'+ID+'" value="false" />'+
                            '<label for="checkbox">'+gettext('Stop workspace if some geometry is not simple')+'</label>'+											
                        '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="simp-geom-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        $("#stop-"+ID).change(function() {
            if ($('#stop-'+ID).is(':checked')) {
                $('#stop-'+ID).val('true')
            }else{
                $('#stop-'+ID).val('false')
            }
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
                }

            },100);
            
            $('#dialog-simp-geom-'+ID).modal('show')

        });

        if ($('#stop-'+ID).is(':checked')) {
            $('#stop-'+ID).val('true')
        }else{
            $('#stop-'+ID).val('false')
        }


        $('#simp-geom-accept-'+ID).click(function() {

            //parameters selected to json
            var paramsValGeom = {"id": ID,
            "parameters": [
            {"stop": $('#stop-'+ID).val()}
            ]}
            
            paramsValGeom['schema-old'] = schemaEdge

            schemaMod = [schemaEdge, schemaEdge]
            
            paramsValGeom['schema'] = schemaMod

            passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)
            
            isAlreadyInCanvas(jsonParams, paramsValGeom, ID)

            icon.setColor('#4682B4')
            
            $('#dialog-simp-geom-'+ID).modal('hide')

        });

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
            text: gettext("Simple"),
            stroke:0.2,
            radius:0,
            bgColor:"#ffffff",
            padding:{left:40, top:3, right:10, bottom:5},
            fontColor:"#107dac",
            resizeable:true
        });

        var label3 =new draw2d.shape.basic.Label({
            text: gettext("No simple"),
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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Modify Value'))+'</h4>'+
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
        
      var context = this

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

        });

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

        });

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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Counter'))+'</h4>'+
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
        
      var context = this

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

        });

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

        });
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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Calculator'))+'</h4>'+
                    '</div>'+
                    '<div  class="modal-body">'+
                        '<form>'+
                            '<div class="column33">'+
                                '<label class="col-form-label">'+gettext('Attribute:')+'</label>'+
                                '<select class="form-control" id="attr-'+ID+'"> </select>'+
                                '<label class="col-form-label">'+gettext('Attributes:')+'</label>'+
                                '<div id ="schema-calculator">'+
                                    '<ul id ="schema-calculator-'+ID+'" class="nav flex-column">'+
                                    '</ul>'+
                                '</div>'+
                            '</div>'+
                            '<div class="column33">'+
                                '<label class="col-form-label"><a href="https://www.postgresql.org/docs/9.1/functions-math.html" target="_blank">'+gettext('Math functions:')+'</a></label>'+
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
                                '</div>'+
                            '</div>'+
                            '<div class="column33">'+
                                '<label class="col-form-label"><a href="https://www.postgresql.org/docs/9.1/functions-string.html" target="_blank">'+gettext('String functions:')+'</a></label>'+
                                '<div id ="functions-string">'+
                                    '<ul id ="functions-'+ID+'" class="nav flex-column">'+
                                        '<li class="nav-item">'+
                                            '<a class="nav-link active" name="||">Concatenate string</a>'+
                                        '</li>'+
                                        '<li class="nav-item">'+
                                            '<a class="nav-link active" name="lower()">Lower case</a>'+
                                        '</li>'+
                                        '<li class="nav-item">'+
                                            '<a class="nav-link active" name="upper()">Upper case</a>'+
                                        '</li>'+
                                        '<li class="nav-item">'+
                                            '<a class="nav-link active" name="substring('+"'string'"+' from 2 for 3)">Substring</a>'+
                                        '</li>'+
                                        '<li class="nav-item">'+
                                            '<a class="nav-link active" name="trim(both '+ "'s'  from 'string')"+'">Trim string</a>'+
                                        '</li>'+
                                        '<li class="nav-item">'+
                                            '<a class="nav-link active" name="length()">Lenght string</a>'+
                                        '</li>'+
                                        '<li class="nav-item">'+
                                            '<a class="nav-link active" name="replace('+"'string', 'from', 'to'"+')">Replace</a>'+
                                        '</li>'+
                                    '</ul>'+
                                '</div>'+
                            '</div>'+
                            '<br><br><br><br><br><br><br><br><br><br><br><br><br><br>'+
                            '<div>'+
                                '<label class="col-form-label">'+gettext('Expression:')+'</a></label>'+
                                '<textarea id="expression-'+ID+'" rows="10" class="form-control" placeholder="'+gettext('For more math functions check above link.')+'"></textarea>'+
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
        
      var context = this

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
             
            
            $('#dialog-calculator-'+ID).modal('show')
        });

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

//// CHANGE ATTRIBUTE TYPE ////

trans_ChangeAttrType = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_ChangeAttrType",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Change Attr. Type"), 
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

        $('#canvas-parent').append('<div id="dialog-change-attr-type-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext("Change Attribute Type"))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column50">'+
                                '<label class="col-form-label">'+gettext('Attribute to change type:')+'</label>'+
                                '<select class="form-control" id="attr-'+ID+'"> </select>'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label class="col-form-label">'+gettext('To data type:')+'</label>'+
                                '<select class="form-control" id="data-type-option-'+ID+'">'+
                                    '<option value="VARCHAR"> '+gettext('Varchar')+'</option>'+
                                    '<option value="INTEGER"> '+gettext('Integer')+' </option>'+
                                    '<option value="FLOAT"> '+gettext('Float')+' </option>'+
                                    '<option value="DATE"> '+gettext('Date')+' </option>'+
                                    '<option value="TIMESTAMP"> '+gettext('Time Stamp')+' </option>'+
                                    '<option value="BOOLEAN"> '+gettext('Boolean')+' </option>'+
                                '</select>'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="change-attr-type-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')
        
      var context = this

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

                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge
                    $('#attr-'+ID).empty()
    
                    for (i = 0; i < schema.length; i++){
                        
                        $('#attr-'+ID).append('<option>'+schema[i]+'</option>')
                    }
                }   

            },100);

            $('#dialog-change-attr-type-'+ID).modal('show')
        })
        
        $('#change-attr-type-accept-'+ID).click(function() {

            var paramsCreateAttr = {"id": ID,
            "parameters": [
                {"attr": $('#attr-'+ID).val(),
                "data-type-option": $('#data-type-option-'+ID).val()}
            ]}
            
            schemaMod =[...schemaEdge]

            schemaMod.splice(schemaMod.indexOf($('#attr-'+ID).val()), 1)

            schemaMod.push($('#attr-'+ID).val())
           
            paramsCreateAttr['schema'] = schemaMod
            paramsCreateAttr['schema-old'] = schemaEdge

            passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)
            isAlreadyInCanvas(jsonParams, paramsCreateAttr, ID)

            icon.setColor('#4682B4')
            
            $('#dialog-change-attr-type-'+ID).modal('hide')

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

//// CORRECT SPELLING ////

trans_CorrectSpelling = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_CorrectSpelling",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Correct Spelling"), 
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

        $('#canvas-parent').append('<div id="dialog-correct-spelling-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext("Correct Spelling"))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<label class="col-form-label">'+gettext('Language')+':</label>'+
                                '<select class="form-control" id="lang-option-'+ID+'">'+
                                    '<option value="es_ES" selected> '+gettext('Spanish')+' - '+gettext('Spain')+'</option>'+
                                    '<option value="en_GB"> '+gettext('English')+' - '+gettext('British')+' </option>'+
                                '</select>'+
                            '</div>'+
                            '<div>'+
                                '<label class="col-form-label">'+gettext('String attribute to correct')+':</label>'+
                                '<select class="form-control" id="attr-'+ID+'"> </select>'+
                            '</div>'+
                            '<div>'+
                                '<input type="checkbox" id="accent-mark-'+ID+'" value="false" />'+
                                '<label for="checkbox">'+gettext('Correct only the accent marks')+'</label>'+											
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="correct-spelling-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')
        
      var context = this

      $("#accent-mark-"+ID).change(function() {
        if ($('#accent-mark-'+ID).is(':checked')) {
            $('#accent-mark-'+ID).val('true')
        }else{
            $('#accent-mark-'+ID).val('false')
        }
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
                schema = schemaEdge

                if (JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]){
                    schema = schemaEdge
                    $('#attr-'+ID).empty()
    
                    for (i = 0; i < schema.length; i++){
                        
                        $('#attr-'+ID).append('<option>'+schema[i]+'</option>')
                    }
                }   

            },100);

            $('#dialog-correct-spelling-'+ID).modal('show')
        })


        if ($('#accent-mark-'+ID).is(':checked')) {
            $('#accent-mark-'+ID).val('true')
        }else{
            $('#accent-mark-'+ID).val('false')
        }
        
        $('#correct-spelling-accept-'+ID).click(function() {

            var paramsCreateAttr = {"id": ID,
            "parameters": [
                {"attr": $('#attr-'+ID).val(),
                "lang-option": $('#lang-option-'+ID).val(),
                "accent-mark": $('#accent-mark-'+ID).val()}
            ]}
            
            schemaMod =[...schemaEdge]

            schemaMod.push('_corrected')
           
            paramsCreateAttr['schema'] = schemaMod
            paramsCreateAttr['schema-old'] = schemaEdge

            passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)
            isAlreadyInCanvas(jsonParams, paramsCreateAttr, ID)

            icon.setColor('#4682B4')
            
            $('#dialog-correct-spelling-'+ID).modal('hide')

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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Execute SQL'))+'</h4>'+
                    '</div>'+
                        '<div  class="modal-body">'+
                            '<form>'+

                            '<div>'+
                                
                                '<label form="db" class="col-form-label">'+gettext('DB Connection:')+'</label>'+
                                '<select id="db-'+ID+'" class="form-control"></select>'+
                            '</div>'+
                            '<div class="column20">'+
                                '<label for ="get-schemas" class="col-form-label">'+gettext('Get schemas')+':</label><br>'+
                                '<a href="#" id="get-schemas-'+ID+'" class="btn btn-default btn-sm">'+gettext('Get schemas')+'</a><br>'+
                            '</div>'+

                            '<div class="column80">'+
                                '<label form="schema" class="col-form-label">'+gettext('Schema:')+'</label>'+
                                '<select id="schema-name-'+ID+'" class="form-control"></select>'+
                            '</div>'+

                            '<div class="column20">'+
                                '<label for ="get-tables" class="col-form-label">'+gettext('Get tables')+':</label><br>'+
                                '<a href="#" id="get-tables-'+ID+'" class="btn btn-default btn-sm">'+gettext('Get tables')+'</a><br>'+
                            '</div>'+

                            '<div class="column80">'+
                                '<label form="tablename" class="col-form-label">'+gettext('Table name:')+'</label>'+
                                '<select id="tablename-'+ID+'" class="form-control"></select>'+
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
                        '<button type="button" class="btn btn-default btn-sm" id="execute-sql-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        for(i=0;i<dbc.length;i++){

            //if(dbc[i].type == 'PostgreSQL'){
                $('#db-'+ID).append(
                    '<option value="'+dbc[i].name+'" data-type = "'+dbc[i].type+'">'+dbc[i].name+'</option>'
                );
            //}
        };

        $('#db-'+ID).on('change', function() {

            if ($(this).find(":selected").data("type") == 'PostgreSQL'){

                $('#get-schemas-'+ID).removeAttr('disabled');
                $('#schema-name-'+ID).prop("disabled",false);
                $('#get-tables-'+ID).removeAttr('disabled');
                $('#tablename-'+ID).prop("disabled",false);
                $('#get-schema-'+ID).removeAttr('disabled');

            } else if ($(this).find(":selected").data("type") == 'Oracle'){

                $('#get-schemas-'+ID).attr('disabled','disabled')
                $('#schema-name-'+ID).prop("disabled",true);
                $('#get-tables-'+ID).attr('disabled','disabled')
                $('#tablename-'+ID).prop("disabled",true);
                $('#get-schema-'+ID).attr('disabled','disabled')

            }
        });

        $('#get-schemas-'+ID).on("click", function(){
                                
            var paramsGetSchemas = {"id": ID,
            "parameters": [
                {"db": $('#db-'+ID).val()}
            ]}

            var formDataGetSchemas = new FormData();
            
            formDataGetSchemas.append('jsonParams', JSON.stringify(paramsGetSchemas))

            $.ajax({
                type: 'POST',
                url: '/gvsigonline/etl/etl_schemas_name_postgres/',
                data: formDataGetSchemas,
                beforeSend:function(xhr){
                    xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
                },
                cache: false, 
                contentType: false, 
                processData: false,
                success: function (data) {

                    $('#schema-name-'+ID).empty()
                    get_sch = []

                    for (i = 0; i < data.length; i++){
                        $('#schema-name-'+ID).append('<option>'+data[i]+'</option>')
                        get_sch.push(data[i])


                    }
                }
            })
        });

        $('#get-tables-'+ID).on("click", function(){
                                
            var paramsGetSchemas = {"id": ID,
            "parameters": [
                {"db": $('#db-'+ID).val(),
                "schema-name": $('#schema-name-'+ID).val()}
            ]}

            var formDataGetSchemas = new FormData();
            
            formDataGetSchemas.append('jsonParams', JSON.stringify(paramsGetSchemas))

            $.ajax({
                type: 'POST',
                url: '/gvsigonline/etl/etl_table_name_postgres/',
                data: formDataGetSchemas,
                beforeSend:function(xhr){
                    xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
                },
                cache: false, 
                contentType: false, 
                processData: false,
                success: function (data) {
                    get_tbl = []
                    $('#tablename-'+ID).empty()

                    for (i = 0; i < data.length; i++){
                        $('#tablename-'+ID).append('<option>'+data[i]+'</option>')
                        get_tbl.push(data[i])

                    }
                }
            })
        });



        $('#get-schema-'+ID).click(function() {
            
            var paramsPostgis = {"id": ID,
            "parameters": [
                {"db": $('#db-'+ID).val(),
                "schema-name": $('#schema-name-'+ID).val(),
                "tablename": $('#tablename-'+ID).val(),
                //"query": $('#query-'+ID).val()
            }
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
        
      var context = this

        icon.on("click", function(){

            if (typeof get_sch === 'undefined'){
                get_sch = []
                $("#schema-name-"+ID+" option").each(function()
                    {  
                        get_sch.push($(this).val())
                    }
                );
            }
    
            if (typeof get_tbl === 'undefined'){
                get_tbl = []
                $("#tablename-"+ID+" option").each(function()
                    {  
                        get_tbl.push($(this).val())
                    }
                );
            }
            
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
            
            $('#dialog-execute-sql-'+ID).modal('show')

        });

        $(document).off("dblclick", "#attrs-values-"+ID+" > li > a")

        $(document).on("dblclick", "#attrs-values-"+ID+" > li > a", function(){
            var text = '##'+this.text+'##'
            var textarea = document.getElementById('query-'+ID)
            textarea.value = textarea.value + text

        });

         $(document).off("dblclick", "#attrs-execute-sql-"+ID+" > li > a")

         $(document).on("dblclick", "#attrs-execute-sql-"+ID+" > li > a", function(){
             var text = '"'+this.text+'"'
             var textarea = document.getElementById('query-'+ID)
             textarea.value = textarea.value + text

        });

        $('#execute-sql-accept-'+ID).click(function() {

            var paramsExecute= {"id": ID,
            "parameters": [
                {"get_schema-name": get_sch,
                "get_tablename": get_tbl,
                "db": $('#db-'+ID).val(),
                "schema-name": $('#schema-name-'+ID).val(),
                "tablename": $('#tablename-'+ID).val(),
                "query": $('#query-'+ID).val()}
            ]}

            var formDataSchemaExecute = new FormData();

            type_db = $('#db-'+ID).find(":selected").data("type")

            if (type_db == 'PostgreSQL'){
                formDataSchemaExecute.append('jsonParamsPostgres', JSON.stringify(paramsExecute))
                url_ = '/gvsigonline/etl/etl_schema_postgresql/'

            } else if (type_db == 'Oracle'){

                paramsExecute['parameters'][0]['checkbox'] = 'true'
                paramsExecute['parameters'][0]['sql'] = $('#query-'+ID).val().split('WHERE')[0]
                formDataSchemaExecute.append('jsonParamsOracle', JSON.stringify(paramsExecute))
                url_ = '/gvsigonline/etl/etl_schema_oracle/'
            }

            $.ajax({
                type: 'POST',
                url: url_,
                data: formDataSchemaExecute,
                beforeSend:function(xhr){
                    xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
                },
                cache: false, 
                contentType: false, 
                processData: false,
                success: function (data) {

                    var schemaMod =[...schemaEdge]
                    
                    for (i = 0; i < data.length; i++){
                        schemaMod.push(data[i])
                    }
                    
                    paramsExecute['schema'] = schemaMod
                    paramsExecute['schema-old'] = schemaEdge

                    passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)

                }
            })
            
            isAlreadyInCanvas(jsonParams, paramsExecute, ID)

            icon.setColor('#4682B4')
            
            $('#dialog-execute-sql-'+ID).modal('hide')

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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext("Create Attribute"))+'</h4>'+
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
                                '<option value="VARCHAR"> '+gettext('Varchar')+'</option>'+
                                '<option value="INTEGER"> '+gettext('Integer')+' </option>'+
                                '<option value="FLOAT"> '+gettext('Float')+' </option>'+
                                '<option value="DATE"> '+gettext('Date')+' </option>'+
                                '<option value="TIMESTAMP"> '+gettext('Time Stamp')+' </option>'+
                                '<option value="BOOLEAN"> '+gettext('Boolean')+' </option>'+
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
        
      var context = this

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
        })

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

//// EXPOSE ATTRIBUTE ////

trans_ExposeAttr = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_ExposeAttr",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Expose Attributes"), 
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

        $('#canvas-parent').append('<div id="dialog-expose-attr-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext("Expose Attribute"))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div >'+
                                '<label class="col-form-label">'+gettext("Attribute to expose:")+'</label>'+
                                '<input id="attr-'+ID+'" type="text" size="40" value="" class="form-control" pattern="[A-Za-z]{3}" placeholder="'+gettext('Write attributes to expose separated by space')+'">'+
                            '</div>'+
                            ''+
                            '<button type="button" style="float: right;" class="btn btn-default btn-sm" id="quit-'+ID+'"><i class="fa fa-minus" aria-hidden="true"></i></button>'+
                            '<button type="button" style="float: right;" class="btn btn-default btn-sm" id="add-'+ID+'"><i class="fa fa-plus" aria-hidden="true"></i></button>'+
                            ''+
                            '<div>'+
                                '<input id="attrs-'+ID+'" type="text" size="40" value="" class="form-control" pattern="[A-Za-z]{3}" >'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="expose-attr-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')
        
      var context = this

      $('#attrs-'+ID).attr('disabled', true)

      var input = $("#attrs-"+ID)

      $( "#add-"+ID ).click(function() {

          if (input.val() == ''){
              input.val($("#attr-"+ID).val())
          }else{
              input.val(input.val() +' '+ $("#attr-"+ID).val())
          }

      });

      $( "#quit-"+ID ).click(function() {
          
          attr = $("#attrs-"+ID).val().split(" ")
          attr.pop()
          attr = attr.join(" ")

          $("#attrs-"+ID).val(attr)

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
                schema = schemaEdge

            },100);
            

            $('#dialog-expose-attr-'+ID).modal('show')
        })

        $('#expose-attr-accept-'+ID).click(function() {
            
            schemaMod =[...schemaEdge]
            
            newSchemaAttr = $('#attrs-'+ID).val().split(" ")
            
            for(i=0;i<newSchemaAttr.length;i++){
                if(schemaMod.includes(newSchemaAttr[i]) == false){
                    schemaMod.push(newSchemaAttr[i])
                }
            };

            var paramsExposeAttr = {"id": ID,
            "parameters": [
                {"attr": $('#attr-'+ID).val(),
                "attrs": $('#attrs-'+ID).val(),
                "schema": schemaMod}
            ]}

            
           
            paramsExposeAttr['schema'] = schemaMod

            passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)
            isAlreadyInCanvas(jsonParams, paramsExposeAttr, ID)

            icon.setColor('#4682B4')
            
            $('#dialog-expose-attr-'+ID).modal('hide')

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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Filter'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div class="column40">'+
                                '<label form="attr" class="col-form-label">'+gettext('Attribute:')+'</label>'+
                                '<select class="form-control" id="attr-'+ID+'"> </select>'+
                            '</div>'+
                            '<div class="column20">'+
                                '<label class="col-form-label">'+gettext('Operator:')+'</label>'+
                                '<select class="form-control" id="option-'+ID+'">'+
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
                            '<div>'+
                                '<button type="button" style="float: right;" class="btn btn-default btn-sm" id="add-'+ID+'"><i class="fa fa-plus" aria-hidden="true"></i></button>'+
                                '<button type="button" style="float: right;" class="btn btn-default btn-sm" value = "AND" id="and-'+ID+'">AND</button>'+
                                '<button type="button" style="float: right;" class="btn btn-default btn-sm" value = "OR" id="or-'+ID+'">OR</button>'+
                                
                            '</div>'+
                            '<div>'+
                                '<label form="" class="col-form-label">'+gettext('Composite Filter:')+'</label>'+
                                '<input id="filter-expression-'+ID+'" type="text" size="40" value="" class="form-control" pattern="[A-Za-z]{3}" >'+
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

      var context = this

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
        })

        var input = $("#filter-expression-"+ID)

        $( "#add-"+ID ).click(function() {

            if($("#option-"+ID).val() == 'starts-with'){
                input.val(input.val() + '"'+$("#attr-"+ID).val()+'" ' + "LIKE '"+$("#value-"+ID).val()+"%' " )

            }else if($("#option-"+ID).val() == 'ends-with'){
                input.val(input.val() + '"'+$("#attr-"+ID).val()+'" ' + "LIKE '%"+$("#value-"+ID).val()+"' " )

            }else if($("#option-"+ID).val() == 'contains'){
                input.val(input.val() + '"'+$("#attr-"+ID).val()+'" ' + "LIKE '%"+$("#value-"+ID).val()+"%' " )
                
            }else if($("#value-"+ID).val() == 'NULL'){
                if($("#option-"+ID).val() == '='){
                    input.val(input.val() + '"'+$("#attr-"+ID).val()+'" IS '+$("#value-"+ID).val()+" " )
                }else if($("#option-"+ID).val() == '!='){
                    input.val(input.val() + '"'+$("#attr-"+ID).val()+'" IS NOT '+$("#value-"+ID).val()+" " )
                }else {
                    input.val(input.val() + '"'+$("#attr-"+ID).val()+'" ' + $("#option-"+ID).val() + " "+$("#value-"+ID).val()+" " )
                }
            }else {
                input.val(input.val() + '"'+$("#attr-"+ID).val()+'" ' + $("#option-"+ID).val() + " '"+$("#value-"+ID).val()+"' " )

            }

        });

        $( "#and-"+ID ).click(function() {
            input.val(input.val()+'AND ') 

        });

        $( "#or-"+ID ).click(function() {
            input.val(input.val()+'OR ') 

        });

        $('#filter-accept-'+ID).click(function() {

            var paramsFilter = {"id": ID,
            "parameters": [
            {"attr": $('#attr-'+ID).val(),
            "option": $('#option-'+ID).val(),
            "value": $('#value-'+ID).val(),
            "filter-expression": input.val()}
            ]}
            
            paramsFilter['schema-old'] = schemaEdge
            paramsFilter['schema'] = schema

            passSchemaToEdgeConnected(ID, listLabel, schema, context.canvas)

            isAlreadyInCanvas(jsonParams, paramsFilter, ID)

            icon.setColor('#4682B4')
            
            $('#dialog-filter-'+ID).modal('hide')

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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Intersection'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<input type="checkbox" name="merge" id="self-intersect-'+ID+'" value=""/>'+
                                '<label for="checkbox">'+gettext('Self intersect layer (Use only data from main input)')+'</label>'+                         
                            '</div>'+
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

        var context = this

        $("#self-intersect-"+ID).change(function() {
            if ($('#self-intersect-'+ID).is(':checked')) {
                $('#self-intersect-'+ID).val('true')
                $('#merge-'+ID).val('')
                $('#merge-'+ID).prop('checked', false)
                $('#merge-'+ID).prop('disabled', true)
            }else{
                $('#self-intersect-'+ID).val('')
                $('#merge-'+ID).prop('disabled', false)
            }
        });

        $("#merge-"+ID).change(function() {
            if ($('#merge-'+ID).is(':checked')) {
                $('#merge-'+ID).val('true')
                $('#self-intersect-'+ID).val('')
                $('#self-intersect-'+ID).prop('checked', false)
                $('#self-intersect-'+ID).prop('disabled', true)
            }else{
                $('#merge-'+ID).val('')
                $('#self-intersect-'+ID).prop('disabled', false)
            }
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

            },100);

            $('#dialog-intersection-'+ID).modal('show')

        });

        $('#intersection-accept-'+ID).click(function() {


            if ($('#self-intersect-'+ID).is(':checked')) {
                $('#self-intersect-'+ID).val('true')
            }else{
                $('#self-intersect-'+ID).val('')
            }

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
                {"self-intersect": $('#self-intersect-'+ID).val(),
                "merge": $('#merge-'+ID).val(),
                "schema": schemaEdge}
            ]}

            paramsInter['schema-old'] = schemaEdge
            paramsInter['schema'] = schemaMod

            passSchemaToEdgeConnected(ID, listLabel, schema, context.canvas)

            isAlreadyInCanvas(jsonParams, paramsInter, ID)

            icon.setColor('#4682B4')
            
            $('#dialog-intersection-'+ID).modal('hide')

        });
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
            text: gettext("Secondary"),
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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Spatial Relation'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<label class="col-form-label">'+gettext('Spatial Relation')+':</label>'+
                                '<select class="form-control" id="option-'+ID+'">'+
                                    '<option value="ST_CONTAINS">'+gettext('Main')+' '+gettext('Contains')+' '+gettext('Secondary')+'</option>'+
                                    '<option value="ST_EQUALS">'+gettext('Main')+' '+gettext('Equals')+' '+gettext('Secondary')+'</option>'+
                                    '<option value="ST_INTERSECTS">'+gettext('Main')+' '+gettext('Intersects')+' '+gettext('Secondary')+'</option>'+
                                    '<option value="ST_TOUCHES">'+gettext('Main')+' '+gettext('Touches')+' '+gettext('Secondary')+'</option>'+                                    
                                    '<option value="ST_WITHIN">'+gettext('Main')+' '+gettext('Within')+' '+gettext('Secondary')+'</option>'+
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

      var context = this

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

        });

        $('#spatial-rel-accept-'+ID).click(function() {

            var paramsSpatialRel = {"id": ID,
            "parameters": [
            {"option": $('#option-'+ID).val()}
            ]}
            
            schemaMod =[...schemaEdge[0]]
            
            schemaMod.push('_related')
           
            paramsSpatialRel['schema-old'] = schemaEdge
            paramsSpatialRel['schema'] = schemaMod

            passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)

            isAlreadyInCanvas(jsonParams, paramsSpatialRel, ID)

            icon.setColor('#4682B4')
            
            $('#dialog-spatial-rel-'+ID).modal('hide')

        });
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
            text: gettext("Secondary"),
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

//// DIFFERENCE ////

trans_Difference = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_Difference",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
        
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Difference"), 
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

      var context = this

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

                if (Array.isArray(schemaEdge[0])){
                    schemaMod = schemaEdge[0]
                }
                else{
                    schemaMod = [...schemaEdge]
                }

            },100);
            

            var paramsDiff = {"id": ID,
            "parameters": [
            {"schema": schemaMod}
            ]}

            paramsDiff['schema-old'] = schemaEdge
            paramsDiff['schema'] = schemaMod


            passSchemaToEdgeConnected(ID, listLabel, schema, context.canvas)

            isAlreadyInCanvas(jsonParams, paramsDiff, ID)

            icon.setColor('#4682B4')

        });


            

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
            text: gettext("Secondary"),
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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext("Keep Attribute"))+'</h4>'+
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

      var context = this

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

        });

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

        });

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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Reproject'))+'</h4>'+
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

      var context = this

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

        });

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

        });

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

      var context = this
        
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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Cadastral Geometry'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<label form="attr" class="col-form-label">'+gettext('Cadastral Reference Attribute (output in EPSG - 4326):')+'</label>'+
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

        });

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

        });
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

      var context = this
        
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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('MGRS'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<label form="attr" class="col-form-label">'+gettext('Select mode:')+'</label>'+
                            '<select class="form-control" id="select-mgrs'+ID+'">'+
                                '<option value="mgrstolatlon" selected>'+gettext('MGRS to geographic coordinates (EPSG - 4326):')+'</option>'+
                                '<option value="latlontomgrs">'+gettext('Geographic coordinates (EPSG - 4326) to MGRS:')+'</option>'+
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

        });

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

        });
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

      var context = this
        
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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Text to Point'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+

                            '<div>'+
                                '<label class="col-form-label">'+gettext('Mode')+':</label>'+
                                '<div class="form-check">'+
                                    '<input type="radio" id="txt-to-point-'+ID+'" name="txt-to-point-'+ID+'" class="form-check-input" value="txt-to-point" checked="checked">'+
                                    '<label class="form-check-label">'+gettext('Text to Point')+'</label>'+
                                '</div>'+

                                '<div class="form-check">'+
                                    '<input type="radio" id="point-to-txt-'+ID+'" name="txt-to-point-'+ID+'" class="form-check-input" value="point-to-txt">'+
                                    '<label class="form-check-label">'+gettext('Point to text')+'</label>'+
                                '</div>'+
                            '</div>'+

                            '<div class="column33">'+
                                '<label form="attr" class="col-form-label">'+gettext('Longitude attribute:')+' (X) </label>'+
                                '<select class="form-control" id="lon-'+ID+'"> </select>'+
                            '</div>'+
                            '<div class="column33">'+
                                '<label form="attr" class="col-form-label">'+gettext('Latitude attribute:')+' (Y) </label>'+
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


        $('input:radio[name="txt-to-point-'+ID+'" ]').change(function(){

            if ($(this).val() == 'txt-to-point'){
                
                $('#lon-'+ID).prop('disabled', false)
                $('#lat-'+ID).prop('disabled', false)
                $('#epsg-'+ID).prop('disabled', false)
                
                
            }
            else if ($(this).val() == 'point-to-txt'){
            
                $('#lon-'+ID).prop('disabled', true)
                $('#lat-'+ID).prop('disabled', true)
                $('#epsg-'+ID).prop('disabled', true)
            }
        });


        for(i=0;i<srs.length;i++){

            epsg = srs[i].code.split(":")[1]

            $('#epsg-'+ID).append(
                '<option value="'+epsg+'">'+srs[i].code+' - '+srs[i].title+'</option>'
            );
        }

        icon.on("click", function(){

            if ($('input:radio[name="txt-to-point-'+ID+'" ]:checked').val() == 'txt-to-point'){
                
                $('#lon-'+ID).prop('disabled', false)
                $('#lat-'+ID).prop('disabled', false)
                $('#epsg-'+ID).prop('disabled', false)
                
            }
            else if ($('input:radio[name="txt-to-point-'+ID+'" ]:checked').val() == 'point-to-txt'){
            
                $('#lon-'+ID).prop('disabled', true)
                $('#lat-'+ID).prop('disabled', true)
                $('#epsg-'+ID).prop('disabled', true)
            }


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

        });

        $('#texttoepsg-accept-'+ID).click(function() {

            //parameters selected to json
            var paramsTextToPoint = {"id": ID,
                "parameters": [
                    {"epsg": $('#epsg-'+ID).val(),
                    "lon": $('#lon-'+ID).val(),
                    "lat": $('#lat-'+ID).val(),
                    "txt-to-point": $('input:radio[name="txt-to-point-'+ID+'"]:checked').val()}
                ]
            };
            schemaMod =[...schemaEdge]

            console.log(paramsTextToPoint)
            
            if ($('input:radio[name="txt-to-point-'+ID+'" ]:checked').val() == 'point-to-txt'){
                schemaMod.push('_xlon')
                schemaMod.push('_ylat')

            }
            
            
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

        });
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

      var context = this
        
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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('WKT to Geometry'))+'</h4>'+
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

        });

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

        });
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

      var context = this
        
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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Split Attribute'))+'</h4>'+
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

        });

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

        });
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

      var context = this
        
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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Explode List'))+'</h4>'+
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

        });

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

        });

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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Union'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<label class="col-form-label">'+gettext('Group by:')+'</label>'+
                                '<select class="form-control" id="group-by-attr-'+ID+'"> </select>'+
                            '</div>'+
                            '<div>'+
                                '<input type="checkbox" name="multi" id="multi-'+ID+'" value=""/>'+
                                '<label for="checkbox">'+gettext('Multigeometry for all features of the output')+'</label>'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="union-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')
        
      var context = this

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

        });

        $('#union-accept-'+ID).click(function() {

            if($("#multi-"+ID).is(':checked')){
                $("#multi-"+ID).val("true")
                
            }else{
                $("#multi-"+ID).val("")
            };

            var paramsUnion = {"id": ID,
            "parameters": [
                {"group-by-attr": $('#group-by-attr-'+ID).val(),
                "multi": $('#multi-'+ID).val()}
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

        });
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

trans_RemoveGeom = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_RemoveGeom",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
        
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext('Remove Geom.'), 
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
        
      var context = this

        icon.on("click", function(){

            schema = passSchemaWhenInputTask(context.canvas, listLabel, ID)

            var paramsRGeom = {"id": ID}

            paramsRGeom['schema-old'] = schema

            schemaMod = [...schema]

            paramsRGeom['schema'] = schemaMod

            passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)

            isAlreadyInCanvas(jsonParams, paramsRGeom, ID)

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
            text: gettext('Output'),
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


	    if($.isNumeric(optionalIndex)){
            this.add(label1, null, optionalIndex+1);
            this.add(label2, null, optionalIndex+1);
	    }
	    else{
            this.add(label1);
            this.add(label2);

        }
         
        listLabel.push([this.id, [input1.name], [output.name]])

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
        
      var context = this

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
        
      var context = this

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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Calculate Area'))+'</h4>'+
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
        
      var context = this

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

        });

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

        });
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
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Current Date'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<label class="col-form-label">'+gettext('New date attribute')+':</label>'+
                                '<input id="attr-'+ID+'" type="text" size="40" value="_date" class="form-control" pattern="[A-Za-z]{3}">'+
                                '<input type="checkbox" name="checkbox" id="checkbox-'+ID+'" value=""/>'+
                                '<label for="checkbox">'+gettext('Time Stamp')+'</label>'+
                            
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="current-date-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')
        
      var context = this

    $("#checkbox-"+ID).click(function() {
        if($("#checkbox-"+ID).is(':checked')){
            $('#checkbox-'+ID).val("true")
        }else{
            $('#checkbox-'+ID).val("")
        }

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
                }

            },100);
            

            $('#dialog-current-date-'+ID).modal('show')

        });

        $('#current-date-accept-'+ID).click(function() {

            var paramsDate = {"id": ID,
            "parameters": [
                {"attr": $('#attr-'+ID).val(),
                "checkbox": $('#checkbox-'+ID).val(),
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

        });
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

//// GEOCODER////

trans_Geocoder = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_Geocoder",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
        
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Geocoder"), 
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

        $('#canvas-parent').append('<div id="dialog-geocoder-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Geocoder'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<label class="col-form-label">'+gettext('Engine')+'</label>'+
                                '<select class="form-control" id="engine-option-'+ID+'">'+
                                    '<option value="ICV"> Geocodificador ICV - EPSG:25830</option>'+
                                '</select>'+    
                            '</div>'+

                            '<div>'+
                                '<label class="col-form-label">'+gettext('Mode')+'</label>'+
                                '<select class="form-control" id="mode-option-'+ID+'">'+
                                    '<option value="direct" selected = "selected"> '+gettext('Direct')+'</option>'+
                                    '<option value="reverse"> '+gettext('Reverse')+'</option>'+
                                '</select>'+    
                            '</div>'+

                            '<div id = "direct-'+ID+'">'+

                                '<div class ="column80">'+
                                    '<label form="attr" class="col-form-label">'+gettext('Attribute:')+'</label>'+
                                    '<select class="form-control" id="attr-'+ID+'"> </select>'+
                                '</div>'+

                                '<div class ="column20">'+
                                '<br>'+
                                    '<button type="button" style="float: right;" class="btn btn-default btn-sm" id="quit-'+ID+'"><i class="fa fa-minus" aria-hidden="true"></i></button>'+
                                    '<button type="button" style="float: right;" class="btn btn-default btn-sm" id="add-'+ID+'"><i class="fa fa-plus" aria-hidden="true"></i></button>'+
                                '</div>'+

                                '<div>'+
                                    '<label form="" class="col-form-label">'+gettext('Attributes selected:')+'</label>'+
                                    '<input id="attr-selected-'+ID+'" type="text" size="40" value="" class="form-control" pattern="[A-Za-z]{3}" disabled>'+
                                '</div>'+
                            '</div>'+

                            '<div id = "reverse-'+ID+'">'+

                                '<div>'+
                                    '<label form="attr" class="col-form-label">'+gettext('Longitude attribute:')+' (X) </label>'+
                                    '<select class="form-control" id="x-'+ID+'"> </select>'+
                                '</div>'+
                                '<div>'+
                                    '<label form="attr" class="col-form-label">'+gettext('Latitude attribute:')+' (Y) </label>'+
                                    '<select class="form-control" id="y-'+ID+'"> </select>'+
                                '</div>'+
                            '</div>'+

                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="geocoder-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        for (i = 0; i < providers.length; i++){
                        
            if(providers[i].type.includes('cartociudad')){
                $('#engine-option-'+ID).append('<option value="'+providers[i].type+'"> '+providers[i].name+' - EPSG:4258</option>')
            }else{
                $('#engine-option-'+ID).append('<option value="'+providers[i].type+'"> '+providers[i].name+' - EPSG:4326</option>')

            }
        }

        $("#reverse-"+ID).slideUp("slow");

        var context = this

        $("#mode-option-"+ID).change(function() {
            if($("#mode-option-"+ID).val() == 'direct'){

                $("#direct-"+ID).slideDown("slow");
                $("#reverse-"+ID).slideUp("slow");

            }else if($("#mode-option-"+ID).val() == 'reverse'){

                $("#direct-"+ID).slideUp("slow");
                $("#reverse-"+ID).slideDown("slow");

            }
        });

        var input = $("#attr-selected-"+ID)

        $( "#add-"+ID ).click(function() {

            if (input.val() == ''){
                input.val($("#attr-"+ID).val())
            }else{
                input.val(input.val() +' '+ $("#attr-"+ID).val())
            }

        });

        $( "#quit-"+ID ).click(function() {
            
            attr = $("#attr-selected-"+ID).val().split(" ")
            attr.pop()
            attr = attr.join(" ")

            $("#attr-selected-"+ID).val(attr)

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

                    $('#attr-'+ID).empty()

                    for (i = 0; i < schema.length; i++){
                        
                        $('#attr-'+ID).append('<option>'+schema[i]+'</option>')
                        $('#x-'+ID).append('<option>'+schema[i]+'</option>')
                        $('#y-'+ID).append('<option>'+schema[i]+'</option>')
                    }
                }

            },100);

            if($("#mode-option-"+ID).val() == 'direct'){

                $("#direct-"+ID).slideDown("slow");
                $("#reverse-"+ID).slideUp("slow");

            }else if($("#mode-option-"+ID).val() == 'reverse'){

                $("#direct-"+ID).slideUp("slow");
                $("#reverse-"+ID).slideDown("slow");
            }
            
            $('#dialog-geocoder-'+ID).modal('show')

        });

        $('#geocoder-accept-'+ID).click(function() {

            var paramsGeocoder = {"id": ID,
            "parameters": [
                {
                "engine-option": $('#engine-option-'+ID).val(),
                "mode-option": $('#mode-option-'+ID).val(),
                "attr": $('#attr-'+ID).val(),
                "attr-selected": $('#attr-selected-'+ID).val(),
                "x": $('#x-'+ID).val(),
                "y": $('#y-'+ID).val()
                }
            ]};

            schemaMod =[...schemaEdge]

            if($("#mode-option-"+ID).val() == 'direct'){
                schemaMod.push('_X')
                schemaMod.push('_Y')
            }else{
                schemaMod.push('_ADDRESS')
            }
            
            paramsGeocoder['schema'] = schemaMod
            paramsGeocoder['schema-old'] = schemaEdge

            passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)
            isAlreadyInCanvas(jsonParams, paramsGeocoder, ID)

            icon.setColor('#4682B4')
            
            $('#dialog-geocoder-'+ID).modal('hide')

        });
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

//// BUFFER ////

trans_Buffer = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "trans_Buffer",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
        
      
        this.classLabel = new draw2d.shape.basic.Label({
            text: gettext("Buffer"), 
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

        $('#canvas-parent').append('<div id="dialog-buffer-'+ID+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
            '<div class="modal-dialog" role="document">'+
                '<div class="modal-content">'+
                    '<div class="modal-header">'+
                        '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
                            '<span aria-hidden="true">&times;</span>'+
                        '</button>'+
                        '<h4 class="modal-title" >'+paramsTransTpl.replace('{}', gettext('Buffer'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<label class="col-form-label">'+gettext('Mode')+'</label>'+
                                '<select class="form-control" id="mode-option-'+ID+'">'+
                                    '<option value="radius" selected = "selected"> '+gettext('Insert radius value')+'</option>'+
                                    '<option value="reach-area"> '+gettext('Make buffer to reach an area')+'</option>'+
                                '</select>'+    
                            '</div>'+

                            '<br>'+

                            '<div id = "radius-'+ID+'">'+

                                '<div>'+

                                    '<label class="col-form-label">'+gettext('Radius')+'</label>'+
                                    '<div class="form-check">'+
                                        '<input type="radio" id="value-'+ID+'" name="radio-radius-'+ID+'" class="form-check-input" value="value" checked="checked">'+
                                        '<label for="value-'+ID+' class="form-check-label">'+gettext('Insert radius value')+'</label>'+
                                    '</div>'+

                                    '<div class="form-check">'+
                                        '<input type="radio" id="attr-'+ID+'" name="radio-radius-'+ID+'" class="form-check-input" value="attr">'+
                                        '<label for="attr-'+ID+'" class="form-check-label">'+gettext('Select attribute with the radius value')+'</label>'+
                                    '</div>'+
                                '</div>'+

                                '<div>'+
                                    '<label form="" class="col-form-label">'+gettext('Radius value')+'</label>'+
                                    '<input id="radius-value-'+ID+'" type="text" size="40" value="" class="form-control" pattern="[A-Za-z]{3}" >'+
                                '</div>'+

                                '<div>'+
                                    '<label form="attr" class="col-form-label">'+gettext('Radius attribute')+':</label>'+
                                    '<select class="form-control" id="radius-attr-'+ID+'" disabled> </select>'+
                                '</div>'+


                            '</div>'+

                            '<div id = "reach-area-'+ID+'">'+

                                /*'<div>'+
                                    '<label form="attr" class="col-form-label">'+gettext('Current Area Attribute')+' </label>'+
                                    '<select class="form-control" id="current-area-attr-'+ID+'"> </select>'+
                                '</div>'+*/
                                '<div>'+
                                    '<label form="attr" class="col-form-label">'+gettext('Area attribute to reach')+' </label>'+
                                    '<select class="form-control" id="area-attr-reach-'+ID+'"> </select>'+
                                '</div>'+

                                '<div>'+
                                    '<label form="attr" class="col-form-label">'+gettext('Radius increase')+' </label>'+
                                    '<input id="radius-increase-'+ID+'" type="number" value="0.001" min="0" step="0.001" class="form-control" >'+
                                '</div>'+

                            '</div>'+

                            '<br>'+

                            '<div id = "style-params-'+ID+'">'+

                                '<label class="col-form-label">'+gettext('Buffer style parameters')+'</label>'+
                                '<br>'+

                                '<div class ="column50">'+
                                    '<label form="attr" class="col-form-label">'+gettext('Quadrant segments')+'</label>'+
                                    '<input id="quad-segs-'+ID+'" type="number" value="8" class="form-control" >'+
                                '</div>'+

                                '<div class ="column50">'+
                                    '<label form="attr" class="col-form-label">'+gettext('End cap style')+' </label>'+
                                    '<select class="form-control" id="end-cap-option-'+ID+'">'+
                                        '<option value="round">'+gettext('Round')+'</option>'+
                                        '<option value="flat">'+gettext('Flat')+'</option>'+
                                        '<option value="square">'+gettext('Square')+'</option>'+
                                    '</select>'+
                                '</div>'+

                                '<div class ="column50">'+
                                    '<label form="attr" class="col-form-label">'+gettext('Join style')+' </label>'+
                                    '<select class="form-control" id="join-option-'+ID+'">'+
                                        '<option value="round">'+gettext('Round')+'</option>'+
                                        '<option value="mitre">'+gettext('Mitre')+'</option>'+
                                        '<option value="bevel">'+gettext('Bevel')+'</option>'+
                                    '</select>'+
                                '</div>'+

                                '<div class ="column50">'+
                                    '<label form="attr" class="col-form-label">'+gettext('Mitre limit')+' </label>'+
                                    '<input id="mitre-limit-'+ID+'" type="number" value="5.0" step="0.1" class="form-control" >'+
                                '</div>'+

                                '<div>'+
                                    '<label form="attr" class="col-form-label">'+gettext('Side')+' </label>'+
                                    '<select class="form-control" id="side-option-'+ID+'">'+
                                        '<option value="both">'+gettext('Both')+'</option>'+
                                        '<option value="left">'+gettext('Left')+'</option>'+
                                        '<option value="right">'+gettext('Right')+'</option>'+
                                    '</select>'+
                                '</div>'+

                            '</div>'+

                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="buffer-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        $("#reach-area-"+ID).slideUp("slow");

        var context = this

        $("#mode-option-"+ID).change(function() {
            if($("#mode-option-"+ID).val() == 'radius'){

                $("#radius-"+ID).slideDown("slow");
                $("#reach-area-"+ID).slideUp("slow");

            }else if($("#mode-option-"+ID).val() == 'reach-area'){

                $("#radius-"+ID).slideUp("slow");
                $("#reach-area-"+ID).slideDown("slow");

            }
        });

        $('input:radio[name="radio-radius-'+ID+'"]').change(function(){

            if ($(this).val() == 'value'){
                
                $('#radius-value-'+ID).prop('disabled', false)
                $('#radius-attr-'+ID).prop('disabled', true)
                
            }
            else if ($(this).val() == 'attr'){
            
                $('#radius-value-'+ID).prop('disabled', true)
                $('#radius-attr-'+ID).prop('disabled', false)
            }
        });

        icon.on("click", function(){

            if ($('input:radio[name="radio-radius-'+ID+'"]:checked').val() == 'value'){
                
                $('#radius-value-'+ID).prop('disabled', false)
                $('#radius-attr-'+ID).prop('disabled', true)
                
            }
            else if ($('input:radio[name="radio-radius-'+ID+'"]:checked').val() == 'attr'){
            
                $('#radius-value-'+ID).prop('disabled', true)
                $('#radius-attr-'+ID).prop('disabled', false)
            }

            
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

                    $('#radius-attr-'+ID).empty()
                    //$('#current-area-attr-'+ID).empty()
                    $('#area-attr-reach-'+ID).empty()

                    for (i = 0; i < schema.length; i++){
                        
                        $('#radius-attr-'+ID).append('<option>'+schema[i]+'</option>')
                        //$('#current-area-attr-'+ID).append('<option>'+schema[i]+'</option>')
                        $('#area-attr-reach-'+ID).append('<option>'+schema[i]+'</option>')
                    }
                }

            },100);

            if($("#mode-option-"+ID).val() == 'radius'){
    
                $("#radius-"+ID).slideDown("slow");
                $("#reach-area-"+ID).slideUp("slow");

            }else if($("#mode-option-"+ID).val() == 'reach-area'){

                $("#radius-"+ID).slideUp("slow");
                $("#reach-area-"+ID).slideDown("slow");

            }
            
            $('#dialog-buffer-'+ID).modal('show')

        });

        $('#buffer-accept-'+ID).click(function() {

            var paramsBuffer = {"id": ID,
            "parameters": [
                {
                "mode-option": $('#mode-option-'+ID).val(),
                "radio-radius": $('input:radio[name="radio-radius-'+ID+'"]:checked').val(),
                "radius-value": $('#radius-value-'+ID).val(),
                "radius-attr": $('#radius-attr-'+ID).val(),
                //"current-area-attr": $('#current-area-attr-'+ID).val(),
                "area-attr-reach": $('#area-attr-reach-'+ID).val(),
                "quad-segs": $('#quad-segs-'+ID).val(),
                "end-cap-option": $('#end-cap-option-'+ID).val(),
                "join-option": $('#join-option-'+ID).val(),
                "mitre-limit": $('#mitre-limit-'+ID).val(),
                "side-option": $('#side-option-'+ID).val(),
                "radius-increase": $('#radius-increase-'+ID).val(),
                "schema": schemaEdge
                }
            ]};

            schemaMod =[...schemaEdge]
            
            paramsBuffer['schema'] = schemaMod
            paramsBuffer['schema-old'] = schemaEdge

            passSchemaToEdgeConnected(ID, listLabel, schemaMod, context.canvas)
            isAlreadyInCanvas(jsonParams, paramsBuffer, ID)

            icon.setColor('#4682B4')
            
            $('#dialog-buffer-'+ID).modal('hide')

        });
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

//// OUTPUT POSTGIS ////

output_Postgis = draw2d.shape.layout.VerticalLayout.extend({

	NAME: "output_Postgis",
	
    init : function(attr)
    {
    	this._super($.extend({bgColor:"#dbddde", color:"#d7d7d7", stroke:1, radius:3},attr));
        
        this.classLabel = new draw2d.shape.basic.Label({
            text:"PgSQL/PostGIS", 
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
                        '<h4 class="modal-title">'+paramsTransTpl.replace('{}', gettext('PostGIS'))+'</h4>'+
                    '</div>'+
                    '<div class="modal-body">'+
                        '<form>'+
                            '<div>'+
                                '<label form="db" class="col-form-label">'+gettext('DB Connection:')+'</label>'+
                                '<select id="db-option-'+ID+'" class="form-control"></select>'+
                            '</div>'+

                            '<div class="column20">'+
                                '<label for ="get-schemas" class="col-form-label">'+gettext('Get schemas')+':</label><br>'+
                                '<a href="#" id="get-schemas-'+ID+'" class="btn btn-default btn-sm">'+gettext('Get schemas')+'</a><br>'+
                            '</div>'+

                            '<div class="column80">'+
                                '<label form="schema-name" class="col-form-label">'+gettext('Schema:')+'</label>'+
                                '<select id="schema-name-option-'+ID+'" class="form-control"></select>'+
                            '</div>'+

                            '<div>'+
                                '<label form="tablename" class="col-form-label">'+gettext('Table name:')+'</label>'+
                                '<input id="tablename-'+ID+'" type="text" value="" class="form-control" pattern="[A-Za-z]{3}" >'+
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
                                    '<input type="radio" id="overwrite-'+ID+'"  name="operation-'+ID+'" class="form-check-input" value="OVERWRITE">'+
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
                                    '<input type="radio" id="delete-'+ID+'" name="operation-'+ID+'" class="form-check-input" value="DELETE">'+
                                    '<label for="delete" class="form-check-label">'+gettext('DELETE')+'</label>'+
                                '</div>'+
                            '</div>'+
                            '<div class="column50">'+
                                '<label class="col-form-label">'+gettext('Match column:')+'</label>'+
                                '<select class="form-control" id="match-'+ID+'" disabled> </select><br>'+
                                '<label class="col-form-label">'+gettext('Order')+':&nbsp</label>'+
                                '<input type="number" id="order-'+ID+'" value="0" size ="3"/>'+
                            '</div>'+
                        '</form>'+
                    '</div>'+
                    '<div class="modal-footer">'+
                        '<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
                        '<button type="button" class="btn btn-default btn-sm" id="output-postgis-accept-'+ID+'">'+gettext('Accept')+'</button>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>')

        for(i=0;i<dbc.length;i++){

            if(dbc[i].type == 'PostgreSQL'){
                $('#db-option-'+ID).append(
                    '<option value="'+dbc[i].name+'">'+dbc[i].name+'</option>'
                );
            }
        };

        $('input:radio[name="operation-'+ID+'"]').change(function(){
            
            if ($(this).val()=='UPDATE' || $(this).val()=='DELETE'){
                $('#match-'+ID).attr('disabled', false)
            }
            else{
                $('#match-'+ID).attr('disabled', true)
            }
        });
        
        $('#get-schemas-'+ID).on("click", function(){
                                
            var paramsGetSchemas = {"id": ID,
            "parameters": [
                {"db": $('#db-option-'+ID).val()}
            ]}

            var formDataGetSchemas = new FormData();
            
            formDataGetSchemas.append('jsonParams', JSON.stringify(paramsGetSchemas))

            $.ajax({
                type: 'POST',
                url: '/gvsigonline/etl/etl_schemas_name_postgres/',
                data: formDataGetSchemas,
                beforeSend:function(xhr){
                    xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
                },
                cache: false, 
                contentType: false, 
                processData: false,
                success: function (data) {

                    $('#schema-name-option-'+ID).empty()
                    get_sch = []

                    for (i = 0; i < data.length; i++){
                        $('#schema-name-option-'+ID).append('<option>'+data[i]+'</option>')
                        get_sch.push(data[i])


                    }
                }
            })
        });
        
      var context = this

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

                if ((JSON.stringify(schemaEdge) != JSON.stringify(schemaOld) || schema==[]) && !editablerestrictedly){
                    schema = schemaEdge
                    $('#match-'+ID).empty()

                    for (i = 0; i < schema.length; i++){
                        $('#match-'+ID).append('<option>'+schema[i]+'</option>')
                    }
                }

            },100);


            optionList = []
            $('#db-option-'+ID+' option').each(function() {
                optionList.push($(this).val())
              });

            for(i=0;i<dbc.length;i++){

                if(dbc[i].type == 'PostgreSQL'){

                    if (! optionList.includes(dbc[i].name)){
                        $('#db-option-'+ID).append(
                            '<option value="'+dbc[i].name+'">'+dbc[i].name+'</option>'
                        );
                    }
                }
            };

            $('#dialog-output-postgis-'+ID).modal('show')

        });

        $('#output-postgis-accept-'+ID).click(function() {


            if (typeof get_sch === 'undefined'){
                get_sch = []
                $("#schema-name-option-"+ID+" option").each(function()
                    {  
                        get_sch.push($(this).val())
                    }
                );
            }

            var paramsPostgis = {"id": ID,
            "parameters": [
                {"get_schema-name-option": get_sch,
                "db-option": $('#db-option-'+ID).val(),
                "schema-name-option": $('#schema-name-option-'+ID).val(),
                "tablename": $('#tablename-'+ID).val(),
                "match": $('#match-'+ID).val(),
                "operation": $('input:radio[name="operation-'+ID+'"]:checked').val(),
                "order": $('#order-'+ID).val()}
            ]}
            
            paramsPostgis['schema-old'] = schemaEdge
            paramsPostgis['schema'] = schema
            
            isAlreadyInCanvas(jsonParams, paramsPostgis, ID)

            icon.setColor('#e79600')
            
            $('#dialog-output-postgis-'+ID).modal('hide')

        });
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