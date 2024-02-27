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
		this.saveButton.off('click').on('click', function() {
			var searcheableRoleList = null;
			var id_wks= $(".modal-body #etl_id").val();
			if (id_wks == ""){
				id_wks=0; //todavia no se guardó el wks, es nuevo
			}
			$.ajax({
				type: 'POST',
				async: false,
				url: '/gvsigonline/etl/permissons_tab/' + id_wks + '/',
				beforeSend: function (xhr) {
					xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
				},
				success: function(data){
					document.getElementById("permission").innerHTML = data;
					searcheableRoleList = new List('read-list-box', {
						valueNames: ['product-title'],
						listClass:'list',
						searchClass: 'search',
						page: 5,
						pagination: false
					});
				}
				,error: function() {
				}
			});

			$('#dialog-save').modal('show')

			$("#save-etl").prop("disabled",false)
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

			$('#save-etl').off('click').on('click', function() {
				var formWorkspace = new FormData();

				formWorkspace.append('id', $('#etl_id').val())
				formWorkspace.append('name', $('#etl_name').val())
				formWorkspace.append('description', $('#etl_desc').val())

				formWorkspace.append('username', username)

				if($("#repeat_periodically").is(':checked')){
					formWorkspace.append("checked", true)
				} else {
					formWorkspace.append("checked", false)
				}

				if($("#change_superuser").is(':checked')){
					formWorkspace.append("superuser", true)
				} else {
					formWorkspace.append("superuser", false)
				}

				formWorkspace.append("day", $("#ws-program-day").val())
				formWorkspace.append("time", $("#ws-program-time").val())
				formWorkspace.append("interval", $("#ws-program-interval").val())
				formWorkspace.append("unit", $("#ws-program-unit").val())


				// access using the List since some elements are hidden and not available in the DOM
				var assigned_edit_roles = [];
				var assigned_execute_roles = [];
				var assigned_restricted_edit_roles = [];
				if (searcheableRoleList != null) {
					for(var i=0; i<searcheableRoleList.items.length; i++){
						var item = searcheableRoleList.items[i];
						var ws_edit_checkbox = $(item.elm).find(".ws-edit-checkbox").first();
						if (ws_edit_checkbox.is(":checked")) {
							var id = ws_edit_checkbox.attr("id");
							var nombre=	id.split("-")[2];
							assigned_edit_roles.push(nombre);
						}
						var ws_execute_checkbox = $(item.elm).find(".ws-execute-checkbox").first();
						if (ws_execute_checkbox.is(":checked")) {
							var id = ws_execute_checkbox.attr("id");
							var nombre=	id.split("-")[2];
							assigned_execute_roles.push(nombre);
						}
						var ws_restricted_edit_checkbox = $(item.elm).find(".ws-restricted-edit-checkbox").first();
						if (ws_restricted_edit_checkbox.is(":checked")) {
							var id = ws_restricted_edit_checkbox.attr("id");
							var nombre=	id.split("-")[2];
							assigned_restricted_edit_roles.push(nombre);
						}
					}
				}

				formWorkspace.append("editRoles",JSON.stringify(assigned_edit_roles));
				formWorkspace.append("executeRoles",JSON.stringify(assigned_execute_roles));
				formWorkspace.append("restrictedEditRoles",JSON.stringify(assigned_restricted_edit_roles));

				writer.marshal(view, function(json){

					jsonCanvas = JSON.stringify(json)

					formWorkspace.append('workspace',jsonCanvas)
				});

				if ($('#etl_id').val()==''){

					$.ajax({
						type: 'POST',
						url: '/gvsigonline/etl/etl_workspace_add/',
						data: formWorkspace,
						beforeSend:function(xhr){
							xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
						},
						cache: false,
						contentType: false,
						processData: false,
						success: function (response) {
							$('#dialog-save').modal('hide')
							if(response['exists']=="true"){
								$('#modal-ws-exists').modal('show')
							}else{
								location.href = '/gvsigonline/etl/etl_workspace_list/';
							}
						}
					});
				} else {
					$('#dialog-save').modal('hide')

					$('#modal-overwrite-workspace-etl').modal('show')

					$('#button-overwrite-workspace-accept').off('click').on('click', function() {

					$('#modal-overwrite-workspace-etl').modal('hide')

						$.ajax({
							type: 'POST',
							url: '/gvsigonline/etl/etl_workspace_update/',
							data: formWorkspace,
							beforeSend:function(xhr){
								xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
							},
							cache: false,
							contentType: false,
							processData: false,
							success	:function(response){
								$('#modal-overwrite-workspace-etl').modal('hide')
								$('#modal-update-workspace-etl').modal('hide');
								if(response['exists']=="true"){
									$('#modal-ws-exists').modal('show')
								}else{
									location.href = '/gvsigonline/etl/etl_workspace_list/';
								}
							},
							error: function(){}
						});
					});
				}
			});
		});

		// Inject the RUN Button
		this.runButton  = $('<button id="button-run" class="btn btn-default btn-sm"><i class="fa fa-play margin-r-5" ></i>' + gettext('Run') + '<i id ="icon-success" class="fa fa-check" aria-hidden="true"></i> <i id = "icon-running" class="fa fa-spinner fa-spin"></i> <i id ="icon-error" class="fa fa-times" aria-hidden="true" ></i></button>');
		this.html.append(this.runButton);

		this.runButton.click(function(){

            $("#button-run").attr("title", 'Running');
            $("#icon-success").css("display", "none");
            $("#icon-running").css("display", "inline-block");
            $("#icon-error").css("display", "none");

			var writer = new draw2d.io.json.Writer();

			writer.marshal(view, function(json){

				jsonCanvas = JSON.stringify(json)

				formData.append('jsonCanvas',jsonCanvas)
				formData.append('username',username)

				$.ajax({
					type: 'POST',
					url: '/gvsigonline/etl/etl_read_canvas/',
					data: formData,
					beforeSend:function(xhr){
						xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
					},
					cache: false,
                    contentType: false,
                    processData: false,
					success: function () {

					}
				});
			});
		});

		// Inject the Add Database Connection Button
		if (editablerestrictedly){
			this.bbddButton  = $('<button class="btn btn-default btn-sm" disabled><i class="fa fa-database margin-r-5" ></i>' + gettext('Add connection') + '</button>');
		}
		else{
			this.bbddButton  = $('<button id="button-add-bbdd" class="btn btn-default btn-sm"><i class="fa fa-database margin-r-5" ></i>' + gettext('Add connection') + '</button>');
		}
		this.html.append(this.bbddButton);
		this.bbddButton.click( function() {
			$('#modal-add-db').modal('show')
		})

		// Inject the DELETE Button
		this.deleteButton  = $('<button id="button-remove" class="btn btn-default btn-sm"><i class="fa fa-times margin-r-5"></i>' + gettext('Remove') + '</button>');
		this.html.append(this.deleteButton);
		this.deleteButton.click($.proxy(function(){
			var node = this.view.getPrimarySelection();
			//$('div[id*="'+node.id+'"]').remove()
			
			if (editablerestrictedly && (node.cssClass.startsWith('input_') || node.cssClass.startsWith('output_') || node.cssClass == 'trans_ExecuteSQL')){

			}else{
				var command= new draw2d.command.CommandDelete(node);
				this.view.getCommandStack().execute(command);
				this.disableButton(this.deleteButton, true);
			}

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

			for(o=0 ;o < cnv.length;o++){

				if (cnv[o]['type'] != 'draw2d.Connection'){

					

					type = cnv[o]['type']
					if (type == 'input_Postgres'){
						type = 'input_Postgis'

					}
					x = cnv[o]['x']
					y = cnv[o]['y']

					id = cnv[o]['id']
					ports = cnv[o]['ports']

					text = cnv[o]['name']

					parameters = cnv[o]['entities'][0]['parameters']
					schema = cnv[o]['entities'][0]['schema']
					schemaold = cnv[o]['entities'][0]['schemaold']

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

					if (parameters && parameters.length != 0){

					Object.keys(parameters[0]).forEach(function(key){

						try{
							if (parameters[0][key]){

								if ($('#'+key+'-'+figure.id).is('select') && !key.includes('epsg') && !key.includes('option') ){

									if ( typeof schemaold !== 'undefined'){

										if (Array.isArray(schemaold[multiIn])){
											for (k = 0; k < schemaold[multiIn].length; k++){
												$('#'+key+'-'+figure.id).append('<option>'+schemaold[multiIn][k]+'</option>')
											};
										}
										else{
											for (k = 0; k < schemaold.length; k++){
												$('#'+key+'-'+figure.id).append('<option>'+schemaold[k]+'</option>')
											};
										}
								}
								};

								if(key.startsWith('get_')){

									key_ = key.replace('get_', '')

									for (k = 0; k < parameters[0][key].length; k++){

										if (Array.isArray(parameters[0][key][k])){

											$('#'+key_+'-'+figure.id).append('<option value ="'+parameters[0][key][k][0]+'">'+parameters[0][key][k][1]+'</option>')

										}else{
											$('#'+key_+'-'+figure.id).append('<option>'+parameters[0][key][k]+'</option>')
										}
									};
								}

								multiIn = multiIn + 1

								if($('input:radio[name="'+key+'-'+figure.id+'"]').is(':radio')){

									$('#'+parameters[0][key].toLowerCase()+'-'+figure.id).attr('checked', true)
									$('#'+parameters[0][key].toLowerCase()+'-'+figure.id).val(parameters[0][key])

								}else if($('#'+key+'-'+figure.id).is(':checkbox')){

									$('#'+key+'-'+figure.id).attr('checked', true)
									$('#'+key+'-'+figure.id).val(parameters[0][key])

								}else{
									$('#'+key+'-'+figure.id).val(parameters[0][key]);
								}
							
								if ( (type.startsWith('input_') || type.startsWith('output_') || type == 'trans_ExecuteSQL')  && editablerestrictedly){
									
									$('#'+key+'-'+figure.id).prop("disabled", true)
									$('input:radio[name="'+key+'-'+figure.id+'"]').prop("disabled", true)
									href = $("[href]")
									$('[id$="accept-'+figure.id+'"]').prop("disabled", true)

									Object.entries(href).forEach(function(entry){
										if ((entry[1].id).includes(figure.id)){
											$("#"+entry[1].id).addClass('disabled')
										}
									})
									
								}
							
							
							}

						} catch {
						}
					})
				}

				}else{
					s = false
					t = false

					for(j=0;j<idRestore.length;j++){
						if(cnv[o]['source']['node'] == idRestore[j][0]){
							cnv[o]['source']['node'] = idRestore[j][1]
							for (k=0; k<idRestore[j][2].length;k++){
								if(idRestore[j][2][k]['name'] == cnv[o]['source']['port']){
									cnv[o]['source']['port'] = idRestore[j][3][k]
									break;
								};
							};

							s = true
						};

						if(cnv[o]['target']['node'] == idRestore[j][0]){
							cnv[o]['target']['node'] = idRestore[j][1]
							for (k=0; k<idRestore[j][2].length;k++){
								if(idRestore[j][2][k]['name'] == cnv[o]['target']['port']){
									cnv[o]['target']['port'] = idRestore[j][3][k]
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
					reader.unmarshal(view, [cnv[o]]);

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