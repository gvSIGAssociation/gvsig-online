idRestore = []

gvsigolETL.Toolbar = Class.extend({
	
	init:function(elementId, view)
	{
		this.html = $("#"+elementId);
		this.view = view;
		
		// register this class as event listener for the bar
		// CommandStack. This is required to update the state of 
		// the Undo/Redo Buttons.
		view.getCommandStack().addEventListener(this);

		// Register a Selection listener for the state hnadling
		// of the Delete Button
		view.on("select", $.proxy(this.onSelectionChanged,this));

		// Inject the new empty canvas Button
		this.emptyButton  = $('<button id="button-new-empty-canvas" class="btn btn-default btn-sm"><i class="fa fa-file-o margin-r-5"></i>' + gettext('New') + '</button>');
		this.html.append(this.emptyButton);
		this.emptyButton.click( function() {

			$("#modal-new-empy-canvas").remove();
			
			$('#canvas-parent').append('<div class="modal fade" id="modal-new-empy-canvas" tabindex="-1" role="dialog" aria-labelledby="myModalLabel">'+
				'<div class="modal-dialog" role="document">'+
					'<div class="modal-content">'+
						'<div class="modal-header">'+
							'<button type="button" class="close" data-dismiss="modal"'+
								'aria-label="Close">'+
								'<span aria-hidden="true">&times;</span>'+
							'</button>'+
							'<h4 class="modal-title" id="myModalLabel">' + gettext('Are you sure?')+'</h4>'+
						'</div>'+
						'<div class="modal-body">'+
							'<div class="row">'+
								'<div class="col-md-12 form-group">'+
									'<p style="font-weight: 600;">' + gettext('If you open a new empty canvas you will lost your current canvas if you have not saved it before')+'</p>'+
								'</div>'+
							'</div>'+
						'</div>'+
						'<div class="modal-footer">'+
							'<button id="button-empty-canvas-cancel" type="button" class="btn btn-default" data-dismiss="modal">' + gettext('Cancel')+'</button>'+
							'<button id="button-empty-canvas-accept" type="button" class="btn btn-default">' + gettext('Accept')+'</button>'+
						'</div>'+
					'</div>'+
				'</div>'+
			'</div>')

			$('#modal-new-empy-canvas').modal('show')

			$('#button-empty-canvas-accept').click(function() {
				location.href = '/gvsigonline/etl/etl_canvas/';

			})

		});

		// Inject the OPEN Button
		this.openButton  = $('<button id="button-open" class="btn btn-default btn-sm"><i class="fa fa-folder-open margin-r-5"></i>' + gettext('Open') + '</button>');
		this.html.append(this.openButton);
		this.openButton.click( function() {

			location.href = '/gvsigonline/etl/etl_workspace_list/';
		});

		
		// Inject the SAVE Button
		this.saveButton  = $('<button id="button-save" class="btn btn-default btn-sm"><i class="fa fa-save margin-r-5"></i>' + gettext('Save') + '</button>');
		this.html.append(this.saveButton);
		this.saveButton.click( function() {

			$("#dialog-save").remove();
			
			$('#canvas-parent').append('<div id="dialog-save" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
				'<div class="modal-dialog" role="document">'+
					'<div class="modal-content">'+
						'<div class="modal-header">'+
							'<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
								'<span aria-hidden="true">&times;</span>'+
							'</button>'+
							'<h4 class="modal-title">'+gettext('Save ETL workspace')+'</h4>'+
						'</div>'+

						'<div class="modal-body">'+
							'<form id="layer-group-form" role="form">'+

								'<div class="row">'+
									'<div class="col-md-12">'+
										'<label for="etl_id" >ID</label>'+
										'<input value ="'+lgid+'" placeholder="'+gettext('ETL workspace ID')+'" name="etl_id" id="etl_id" type="text" class="form-control">'+
									'</div>'+
								'</div>'+

								'<div class="row">'+
									'<div class="col-md-12">'+
										'<label for="etl_name">'+gettext('Name')+'</label>'+
										'<input value ="'+name_ws+'" placeholder="'+gettext('ETL workspace name')+'" name="etl_name" id="etl_name" type="text" class="form-control">'+									
									'</div>'+
								'</div>'+

								'<div class="row">'+
									'<div class="col-md-12">'+
										'<label for="etl_desc">'+gettext('Description')+'</label>'+
										'<input value ="'+description_ws+'" placeholder="'+gettext('ETL workspace description')+'" name="etl_desc" id="etl_desc" type="text" class="form-control">'+									
									'</div>'+
								'</div>'+					

							'</form>'+
						'</div>'+
						'<div class="modal-footer">'+
							'<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
							'<button type="button" class="btn btn-default btn-sm" id="save-etl" title="'+gettext('Set parameters of all tasks before save')+'">'+gettext('Save')+'</button>'+
						'</div>'+
					'</div>'+
				'</div>'+
			'</div>')

			$('#dialog-save').modal('show')

			$("#save-etl").prop("disabled",false);
			$('#save-etl').attr('data-toggle','');

			var writer = new draw2d.io.json.Writer();
			
			writer.marshal(view, function(json){

				for(i=0;i<json.length;i++){
					if (json[i] == null){
						$("#save-etl").prop("disabled",true);
						$('#save-etl').attr('data-toggle','tooltip');
						break;
					}
				}
			});
			
			$('#save-etl').click(function() {
				var formWorkspace = new FormData();

				formWorkspace.append('id', $('#etl_id').val())
				formWorkspace.append('name', $('#etl_name').val())
				formWorkspace.append('description', $('#etl_desc').val())
			
				writer.marshal(view, function(json){
	
					jsonCanvas = JSON.stringify(json)
	
					formWorkspace.append('workspace',jsonCanvas)
				});
			
				$.ajax({
					type: 'POST',
					url: '/gvsigonline/etl/etl_workspace_add/',
					data: formWorkspace,
					beforeSend:function(xhr){
						xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
					},
					cache: false, 
					contentType: false, 
					processData: false,
					success: function () {
						$('#dialog-save').modal('hide')
						location.href = '/gvsigonline/etl/etl_workspace_list/';
					}
				});		
			});
		});

		// Inject the RUN Button
		this.runButton  = $('<button id="button-run" class="btn btn-default btn-sm"><i class="fa fa-play margin-r-5"></i>' + gettext('Run') + '</button>');
		this.html.append(this.runButton);

		this.runButton.click(function(){
			var writer = new draw2d.io.json.Writer();

			writer.marshal(view, function(json){
				jsonCanvas = JSON.stringify(json)
				
				formData.append('jsonCanvas',jsonCanvas)

				$.ajax({
					type: 'POST',
					url: '/gvsigonline/etl/etl_read_canvas/',
					data: formData,
					beforeSend:function(xhr){
						xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
					},
					cache: false, 
                    contentType: false, 
                    processData: false,
					success: function (result) {

						if(result != null){
							message = result.error
							role = 'class="alert alert-danger" role = "alert"'
						}else{
							message = gettext('Process has been executed succesfully')
							role = 'class="alert alert-success" role = "alert"'
						}

						$("#dialog-response").remove();

						$('#canvas-parent').append('<div id="dialog-response" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">'+
							'<div class="modal-dialog" role="document">'+
								'<div class="modal-content">'+
									'<div class="modal-header">'+
										'<button type="button" class="close" data-dismiss="modal" aria-label="Close">'+
											'<span aria-hidden="true">&times;</span>'+
										'</button>'+
										'<h4 class="modal-title">'+gettext('Response')+'</h4>'+
									'</div>'+
									'<div '+role+' align="center"> <p style="font-weight: 600;">'+message+'</p>'+
									'</div>'+
									'<div class="modal-footer">'+
										'<button type="button" class="btn btn-default btn-sm" data-dismiss="modal">'+gettext('Close')+'</button>'+
									'</div>'+
								'</div>'+
							'</div>'+
						'</div>')

						$('#dialog-response').modal('show')
					}
				});
			});
		});

		// Inject the DELETE Button
		this.deleteButton  = $('<button id="button-remove" class="btn btn-default btn-sm"><i class="fa fa-times margin-r-5"></i>' + gettext('Remove') + '</button>');
		this.html.append(this.deleteButton);
		this.deleteButton.click($.proxy(function(){
			var node = this.view.getPrimarySelection();		
			var command= new draw2d.command.CommandDelete(node);
			this.view.getCommandStack().execute(command);
			this.disableButton(this.deleteButton, true);
		},this));
		
		// Inject the UNDO Button and the callbacks
		this.undoButton  = $('<button id="button-undo" class="btn btn-default btn-sm"><i class="fa fa-reply margin-r-5"></i>' + gettext('Undo') + '</button>');
		this.html.append(this.undoButton);
		this.undoButton.click($.proxy(function(){
			   this.view.getCommandStack().undo();
		},this));

		// Inject the REDO Button and the callback
		this.redoButton  = $('<button id="button-redo" class="btn btn-default btn-sm"><i class="fa fa-share margin-r-5"></i>' + gettext('Redo') + '</button>');
		this.html.append(this.redoButton);
		this.redoButton.click($.proxy(function(){
		    this.view.getCommandStack().redo();
		},this));

		// Inject the ZOOM IN Button and the callbacks
		this.zoomInButton  = $('<button id="button-zoom-in" class="btn btn-default btn-sm"><i class="fa fa-search-plus margin-r-5"></i>'+gettext('Zoom In')+'</button>');
		this.html.append(this.zoomInButton);
		this.zoomInButton.button().click($.proxy(function(){
			this.disableButton(this.zoomOutButton, false);
			this.disableButton(this.resetButton, false);
		      this.view.setZoom(this.view.getZoom()*0.7,true);
		      
		},this));

		// Inject the RESET ZOOM Button
		this.resetButton  = $('<button id="button-zoom-in" class="btn btn-default btn-sm"><i class="fa fa-arrows-alt margin-r-5"></i> 1:1 </button>');
		this.html.append(this.resetButton);
		this.resetButton.button().click($.proxy(function(){
			this.disableButton(this.zoomOutButton, true);
			this.disableButton(this.resetButton, true);
		    this.view.setZoom(1.0, true);
           
		},this));
		
		// Inject the ZOOM OUT Button and the callback
		this.zoomOutButton  = $('<button id="button-zoom-in" class="btn btn-default btn-sm"><i class="fa fa-search-minus margin-r-5"></i>'+gettext('Zoom Out')+'</button>');
		this.html.append(this.zoomOutButton);
		this.zoomOutButton.button().click($.proxy(function(){
			if(this.view.getZoom()<1 ){
				zoom=this.view.getZoom()*1.3
				if(zoom>1){
					this.view.setZoom(1, true);
					this.disableButton(this.zoomOutButton, true);
					this.disableButton(this.resetButton, true);
				}else{
					this.view.setZoom(zoom, true);
				}
				
			}

		},this));

        this.disableButton(this.undoButton, true);
        this.disableButton(this.redoButton, true);
		this.disableButton(this.deleteButton, true);
		this.disableButton(this.runButton, true);
		this.disableButton(this.zoomOutButton, true);
		this.disableButton(this.resetButton, true);
		this.disableButton(this.saveButton, true);
		this.disableButton(this.emptyButton, true);

		
		/*Draw Nodes if a workspace is restored*/
		if (cnv != null){

			for(i=0 ;i < cnv.length;i++){

				if (cnv[i]['type'] != 'draw2d.Connection'){
					
					type = cnv[i]['type']
					x = cnv[i]['x']
					y = cnv[i]['y']
	
					id = cnv[i]['id']
					ports = cnv[i]['ports']

					parameters = cnv[i]['entities'][0]['parameters']
					schema = cnv[i]['entities'][0]['schema']
					schemaold = cnv[i]['entities'][0]['schemaold']
				
					var figure = eval("new "+type+"();");
					
					figure.addEntity("id");

					for(j=0;j<listLabel.length;j++){
						if(listLabel[j][0]==figure.id){
							arrayPorts = listLabel[j][1].concat(listLabel[j][2])
							break;
						};
					};
	
					idRestore.push([id, figure.id, ports, arrayPorts])
					
					taskparameters = {"id": figure.id, "parameters": parameters, "schema": schema, "schema-old": schemaold}

					isAlreadyInCanvas(jsonParams, taskparameters, figure.id)
					
					// create a command for the undo/redo support
					var command = new draw2d.command.CommandAdd(view, figure, x, y);
					view.getCommandStack().execute(command);
					
					multiIn = 0
					Object.keys(parameters[0]).forEach(function(key){
						
						try{
							if (parameters[0][key]){
								if ($('#'+key+'-'+figure.id).is('select')){
									if (Array.isArray(schemaold[multiIn])){
										for (k = 0; k < schemaold[multiIn].length; k++){
											$('#'+key+'-'+figure.id).append('<option>'+schemaold[multiIn][k]+'</option>')
										};
										
									}else{
										for (k = 0; k < schemaold.length; k++){
											$('#'+key+'-'+figure.id).append('<option>'+schemaold[k]+'</option>')
										};
									}
								}

								multiIn = multiIn + 1
								
								$('#'+key+'-'+figure.id).val(parameters[0][key]);
							}

						}catch{
						}
					})
			
				}else{
					
					s = false
					t = false
	
					for(j=0;j<idRestore.length;j++){
						if(cnv[i]['source']['node'] == idRestore[j][0]){
							cnv[i]['source']['node'] = idRestore[j][1]
							for (k=0; k<idRestore[j][2].length;k++){
								if(idRestore[j][2][k]['name'] == cnv[i]['source']['port']){
									cnv[i]['source']['port'] = idRestore[j][3][k]
									break;
								};
							};
	
							s = true
						};
	
						if(cnv[i]['target']['node'] == idRestore[j][0]){
							cnv[i]['target']['node'] = idRestore[j][1]
							for (k=0; k<idRestore[j][2].length;k++){
								if(idRestore[j][2][k]['name'] == cnv[i]['target']['port']){
									cnv[i]['target']['port'] = idRestore[j][3][k]
									break;
								};
							};
	
							t = true
						};
	
						if(s == true && t == true){
							break;
						};
					};

					var reader = new draw2d.io.json.Reader();
					reader.unmarshal(view, [cnv[i]]);

				};
			};
		};
    },

	/**
	 * @method
	 * Called if the selection in the cnavas has been changed. You must register this
	 * class on the canvas to receive this event.
	 *
	 * @param {draw2d.Canvas} emitter
	 * @param {Object} event
	 * @param {draw2d.Figure} event.figure
	 */
	onSelectionChanged : function(event)
	{
		this.disableButton(this.deleteButton,event.figure===null);
	},
	
	/**
	 * @method
	 * Sent when an event occurs on the command stack. draw2d.command.CommandStackEvent.getDetail() 
	 * can be used to identify the type of event which has occurred.
	 * 
	 * @template
	 * 
	 * @param {draw2d.command.CommandStackEvent} event
	 **/
	stackChanged:function(event)
	{
        this.disableButton(this.undoButton, !event.getStack().canUndo());
		this.disableButton(this.redoButton, !event.getStack().canRedo());
		this.disableButton(this.runButton, false);
		this.disableButton(this.saveButton, false);
		this.disableButton(this.emptyButton, false);
	
	},
	
	disableButton:function(button, flag)
	{
	   button.prop("disabled", flag);
       if(flag){
            button.addClass("disabled");
        }
        else{
            button.removeClass("disabled");
        }
	}
});