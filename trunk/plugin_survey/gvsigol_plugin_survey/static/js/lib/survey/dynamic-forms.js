function createDynamicSurveyForm(form_definition, component_chooser, div_destination){
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
						createSurveyFormComponent(div_destination, this.value, j, field);
					}
				}
			}
		}
		load_functions();
	});
	
	$("#"+component_chooser).change();
}

function create_stringcombo_item(id, name){
	var html = "";
//	html +='<div id="'+id+'" class="stringcombo-item">';
//	html +='<input type="text" name="'+id+'_item" class="form-control stringcombo-item-name" value="'+name+'" placeholder="'+gettext("Item group name")+'"><br/>';
//	html +='<input type="text" name="'+id+'" class="form-control combo-entry" style="width:80%;float:left" value="" placeholder="'+gettext("Escribe el item a añadir...")+'"><div class="add_li"><i class="fa fa-plus" aria-hidden="true"></i></div><div class="remove_li"><i class="fa fa-minus" aria-hidden="true"></i></div>';
//	html +='<div style="clear:both"></div>';
//	html +='<ul></ul>';
//	html +='</div>';
//	$("#"+id+"_div").append(html);
//	
	html +='<div id="'+id+'" class="stringcombo-item">';
	html +='<div class="col-md-12 form-group item-group-div">';
	html +='<label class="item-label">'+gettext("Item group")+'</label>';
	html +='<div class="pull-right stringcombo_item_remove_button item-close"><i class="fa fa-times margin-r-5" aria-hidden="true"></i></div>';
	html +='<input type="text" name="'+id+'_item" class="form-control stringcombo-item-name" value="'+name+'" placeholder="'+gettext("Item group name")+'"><br/>';
	html +='<div class="btn btn-default pull-right add_li" style="margin: 5px;"><i class="fa fa-plus margin-r-5" aria-hidden="true"></i>'+gettext("Add item")+'</div>';
	html +='<div style="clear:both"></div>';
	html +='<ul class="ul-item">';
	html +='</ul>';
	html +='</div>';
	html +='</div>';
	
	$("#"+id+"_div").append(html);
	
	load_functions();
}

function load_functions(){
	$(".add_li").unbind("click").click(function(){
		var parent = $(this).parent();
		var item = "";
		var li ='<li class="li-item"><span class="item-title">'+gettext("Item")+'</span><input type="text" class="form-control item-value" style="width:80%" value="" placeholder="'+gettext("Escribe el item a añadir...")+'"></span><div class="remove_li"><i class="fa fa-minus" aria-hidden="true"></i></div><div style="clear:both"></div></li>';

		parent.children("ul").append(li);
		parent.children(".combo-entry").val("");
		
		load_functions();
	});
	
	$(".remove_li").unbind("click").click(function(){
		var parent = $(this).parent();
		parent.remove();
	});
	
	$(".stringcombo_item_add_button").unbind("click").click(function(){
		var id = $(this).attr("name");
		var count = $("#"+id+"_div").find(".stringcombo-item").length;
		var name = 'items-'+count;
		create_stringcombo_item(id, name);
	});
	
	$(".stringcombo_item_remove_button").unbind("click").click(function(){
		var parent = $(this).parent();
		parent.remove();
		
		load_functions();
	});
}

function createSurveyFormComponent(div_destination, method, index, field){
	var id = method + "-" + field["id"];
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
	
	if(field["type"] == 'double'){
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
		value += 'step=0.01 ';
		html +='<input id="'+id+'" name="'+id+'" type="number" class="form-control" '+value+' style="width: 100%"><br />';
	}
	
	if(field["type"] == 'boolean'){
		html = '<div style="clear:both"></div><label for="'+id+'">'+field["key"]+'</label><br />'; 
		var value = "";
		if(field["value"] != undefined && field["value"] == "true"){
			value += 'checked ';
		}
		
		html +='<input id="'+id+'" name="'+id+'" type="checkbox" '+value+'><br />';
	}
	
	if(field["type"] == 'date'){
		html = '<div style="clear:both"></div><label for="'+id+'">'+field["key"]+'</label><br />'; 
		var value = "";
		if(field["value"] != undefined){
			value += 'value="'+field["value"]+'" ';
		}
		
		html +='<input id="'+id+'" name="'+id+'" type="date" class="form-control" '+value+' style="width: 100%"><br />';
	}
	
	if(field["type"] == 'time'){
		html = '<div style="clear:both"></div><label for="'+id+'">'+field["key"]+'</label><br />'; 
		var value = "";
		if(field["value"] != undefined){
			value += 'value="'+field["value"]+'" ';
		}
		
		html +='<input id="'+id+'" name="'+id+'" type="time" class="form-control" '+value+' style="width: 100%"><br />';
	}

	if(field["type"] == 'stringcombo' || field["type"] == 'multistringcombo'){
		html +='<div id="'+id+'_div">';
		html +='<div id="'+id+'" class="stringcombo-item">';
		html +='<div class="col-md-12 form-group item-group-div">';
		html +='<label class="item-label">'+gettext("Item group")+'</label>';
		html +='<div class="pull-right stringcombo_item_remove_button item-close"><i class="fa fa-times margin-r-5" aria-hidden="true"></i></div>';
		html +='<input type="text" name="'+id+'_item" class="form-control stringcombo-item-name" value="items" disabled placeholder="'+gettext("Item group name")+'"><br/>';
		html +='<div class="btn btn-default pull-right add_li" style="margin: 5px;"><i class="fa fa-plus margin-r-5" aria-hidden="true"></i>'+gettext("Add item")+'</div>';
		html +='<div style="clear:both"></div>';
		html +='<ul class="ul-item">';
		html +='</ul>';
		html +='</div>';
		html +='</div>';
		html +='</div>';
	}
	
	if(field["type"] == 'connectedstringcombo'){
		html +='<div id="'+id+'_add_button"  name="'+id+'" class="btn btn-default pull-right stringcombo_item_add_button" style="margin: 5px;"><i class="fa fa-plus margin-r-5" aria-hidden="true"></i>'+gettext("Add item group")+'</div>';
		html +='<div id="'+id+'_div"></div>';
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
		createDynamicSurveyForm(field["value"], id+"-select", id+"-div")
	}
}



function getParamsFromDynamicSurveyForm(form_definition, component_chooser, div_destination){
	var key = $("#"+component_chooser+" option:selected").val();
	var form = null;
	for (var i=0;i<form_definition.length; i++){
		if(key in form_definition[i]){
			form = form_definition[i][key];
			
			var fields = form["fields"];
			for(var j=0; j<fields.length; j++){
				var field = fields[j];
				var id = key + "-" + field["id"];
				if(field["type"]=="combostring"){
					var vx = $("#"+div_destination+" #"+id+" option:selected").val();
					if(vx == "true" || vx == "false"){
						if(vx == "true"){
							field["current-value"] = true;
						}else{
							field["current-value"] = false;
						}
					}else{
						field["current-value"] = vx;
					}
				}else{
					if(field["type"]=="connectedstringcombo" || field["type"]=="stringcombo" || field["type"]=="multistringcombo"){
						var values_item = {};
						$(".stringcombo-item").each(function(){
							var item = $(this).find(".stringcombo-item-name")[0].value;
							var value_items = [];
							var li = $(this).find("ul li input").each(function(){
								var aux = {}
								var text = $(this).val();
								aux["item"] = text;
								value_items.push(aux);
							});
							values_item[item] = value_items;
						})
						field["current-value"] = values_item;
						field["values"] = values_item;
					}else{
						field["current-value"] = $("#"+div_destination+" #"+id).val();
					}
				}
				if(field["type"]=="form"){
					var keyl = $("#"+key+'-'+j+"-select option:selected").val();
					for (var l=0;l<field["value"].length; l++){
						if(keyl in field["value"][l]){
					       field["value"] = getParamsFromDynamicSurveyForm(field["value"], key+'-'+j+'-select',key+'-'+j+'-div');
						}
					}
				}
			}
		}
	}

	return form;
}

function setParamsFromDynamicSurveyForm(field_definition, component_chooser, div_destination){
	$("#"+component_chooser+" option[value="+field_definition["method_name"]+"]").attr('selected',true).change();
	
	var fields = field_definition["fields"];
	for(var i=0; i<fields.length; i++){
		var field = fields[i];
		var id = field_definition["method_name"] + "-" + field["id"];
		if(field['type'] == 'form'){
			setParamsFromDynamicSurveyForm(field['value'], id+'-select', id+'-div');
		}else{
			if(field["current-value"] != undefined){
				$("#"+div_destination+" #"+id).val(field["current-value"]);
			}
		}
	}
}

