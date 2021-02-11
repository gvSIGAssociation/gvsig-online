
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

		// Inject the DELETE Button
		this.deleteButton  = $('<button id="button-remove" class="btn btn-default btn-sm"><i class="fa fa-times margin-r-5"></i>' + gettext('Remove') + '</button>');
		this.html.append(this.deleteButton);
		this.deleteButton.click($.proxy(function(){
			var node = this.view.getPrimarySelection();		
			var command= new draw2d.command.CommandDelete(node);
			this.view.getCommandStack().execute(command);
			this.disableButton(this.deleteButton, true);
		},this));

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
									'<div '+role+' align="center">'+message+
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

		// Inject the ZOOM IN Button and the callbacks
		this.zoomInButton  = $('<button id="button-zoom-in" class="btn btn-default btn-sm"><i class="fa fa-search-plus margin-r-5"></i>'+gettext('Zoom In')+'</button>');
		this.html.append(this.zoomInButton);
		this.zoomInButton.button().click($.proxy(function(){
			this.disableButton(this.zoomOutButton, false);
			this.disableButton(this.resetButton, false);
		      this.view.setZoom(this.view.getZoom()*0.7,true);
		      this.app.layout();
		},this));

		// Inject the RESET ZOOM Button
		this.resetButton  = $('<button id="button-zoom-in" class="btn btn-default btn-sm"><i class="fa fa-arrows-alt margin-r-5"></i> 1:1 </button>');
		this.html.append(this.resetButton);
		this.resetButton.button().click($.proxy(function(){
			this.disableButton(this.zoomOutButton, true);
			this.disableButton(this.resetButton, true);
		    this.view.setZoom(1.0, true);
            this.app.layout();
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
				
				this.app.layout();
			}

		},this));
		
        this.disableButton(this.undoButton, true);
        this.disableButton(this.redoButton, true);
		this.disableButton(this.deleteButton, true);
		this.disableButton(this.runButton, true);
		this.disableButton(this.zoomOutButton, true);
		this.disableButton(this.resetButton, true);

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