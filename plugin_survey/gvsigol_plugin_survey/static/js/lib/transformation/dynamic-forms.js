function createDynamicForm(form_definition, component_chooser, div_destination){
	var html_div = "";
	$("#"+component_chooser).empty();
	for(var i=0; i<form_definition.length; i++){
		for(var key in form_definition[i]){
			var form = form_definition[i][key];
			if($("#"+component_chooser).is("select")){
				$("#"+component_chooser).append('<option value="'+key+'">'+form["description"]+'</option>');
			}
			if($("#"+component_chooser).is("ul")){
				$("#"+component_chooser).append('<li value="'+key+'">'+form["description"]+'</li>');
			}
		}
	}
	
	$("#"+component_chooser).on("change", function(){
		$("#"+div_destination).html("");
		if(this.value != ""){
			for(var i=0; i<form_definition.length; i++){
				if(this.value in form_definition[i]){
					var fields = form_definition[i][this.value]["fields"];
					for(var j=0; j<fields.length; j++){
						var field = fields[j];
						createFormComponent(div_destination, this.value, j, field);
					}
				}
			}
		}
	});
	
	$("#"+component_chooser).change();
}

function createFormComponent(div_destination, method, index, field){
	var id = method + "-" + index;
	var html = ''; 
	if(field["type"] == 'string'){
		html = '<div style="clear:both"></div><label for="'+id+'">'+field["key"]+'</label><br />'; 
		var value = "";
		if(field["value"]){
			value += 'value="'+field["value"]+'" ';
		}
		html +='<input id="'+id+'" name="'+id+'" type="text" class="form-control" '+value+'style="width: 100%"><br />';
	}
	
	if(field["type"] == 'combostring'){
		html = '<div style="clear:both"></div><label for="'+id+'">'+field["key"]+'</label><br />'; 
		var options = "";
		if(Array.isArray(field["values"])){
			for(var x=0; x<field["values"].length; x++){
				var field_value = field["values"][x];
				if(field_value.length >1){
					if(field_value[0] == field["value"]){
						options += '<option value="'+field_value[0]+'" selected>'+field_value[1]+'</options>';
					}else{
						options += '<option value="'+field_value[0]+'">'+field_value[1]+'</options>';
					}
				}
			}
		}else{
			var values = field["values"].split(";");
			for(var x=0; x<values.length; x++){
				if(values[x] == field["value"]){
					options += '<option value="'+values[x]+'" selected>'+values[x]+'</options>';
				}else{
					options += '<option value="'+values[x]+'">'+values[x]+'</options>';
				}
			}
		}
		html +='<select id="'+id+'" name="'+id+'" class="form-control '+ field["classes"] +'" '+value+'style="width: 100%">'+options+'</select><br />';
	}
	
	if(field["type"] == 'integer'){
		html = '<div style="clear:both"></div><label for="'+id+'">'+field["key"]+'</label><br />'; 
		var value = "";
		if(field["value"] != undefined){
			value += 'value="'+field["value"]+'" ';
		}
		if(field["min"] != undefined){
			value += 'min='+field["min"]+' ';
		}
		if(field["max"] != undefined){
			value += 'max='+field["max"]+' ';
		}
		value += 'step=1 ';
		html +='<input id="'+id+'" name="'+id+'" type="number" class="form-control" '+value+' style="width: 100%"><br />';
	}
	
	$("#"+div_destination).append(html);
	
	if(field["type"] == 'form'){
		var classes  = "";
		if(field["classes"]){
			classes = field["classes"];
		}
		$("#"+div_destination).append('<div class="'+classes+'"><label for="'+id+'">'+field["key"]+'</label><br /><select id="'+id+'-select" class="form-control" style="width: 100%"></select>'+
				'<div id="'+id+'-div" class="col-md-12 form-group" style="padding-top:10px;background-color:#eee"></div>'+
				'</div>');
		createDynamicForm(field["value"], id+"-select", id+"-div")
	}
}



function getParamsFromDynamicForm(form_definition, component_chooser, div_destination){
	var key = $("#"+component_chooser+" option:selected").val();
	var form = null;
	for (var i=0;i<form_definition.length; i++){
		if(key in form_definition[i]){
			form = form_definition[i][key];
			
			var fields = form["fields"];
			for(var j=0; j<fields.length; j++){
				var field = fields[j];
				var id = key + "-" + j;
				if(field["type"]=="combostring"){
					field["current-value"] = $("#"+div_destination+" #"+id+" option:selected").val();
				}else{
					field["current-value"] = $("#"+div_destination+" #"+id).val();
				}
				if(field["type"]=="form"){
					var keyl = $("#"+key+'-'+j+"-select option:selected").val();
					for (var l=0;l<field["value"].length; l++){
						if(keyl in field["value"][l]){
					       field["value"] = getParamsFromDynamicForm(field["value"], key+'-'+j+'-select',key+'-'+j+'-div');
						}
					}
				}
			}
		}
	}

	return form;
}

function setParamsFromDynamicForm(field_definition, component_chooser, div_destination){
	$("#"+component_chooser+" option[value="+field_definition["method_name"]+"]").attr('selected',true).change();
	
	var fields = field_definition["fields"];
	for(var i=0; i<fields.length; i++){
		var field = fields[i];
		var id = field_definition["method_name"] + "-" + i;
		if(field['type'] == 'form'){
			setParamsFromDynamicForm(field['value'], id+'-select', id+'-div');
		}else{
			if(field["current-value"] != undefined){
				$("#"+div_destination+" #"+id).val(field["current-value"]);
			}
		}
	}
}

