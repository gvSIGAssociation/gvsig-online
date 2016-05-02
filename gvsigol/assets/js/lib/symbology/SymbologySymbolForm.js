/**
 * gvSIG Online.
 * Copyright (C) 2007-2015 gvSIG Association.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

/**
 * @author: José Badía <jbadia@scolab.es>
 */

var formHelper = null;
var layer = null;
var symbologyUtils = null;
var type = null;
var currentSymbol = null;
var currentSLD = null;
var legend = null
var symbolForm = null;

var SymbologySymbolForm = function(comp, layer) {	
	this.legend = comp;
	this.formHelper = new SymbologyFormComponents();
	this.symbologyUtils = new SymbologyUtils(this);
	this.libraryForm = new SymbologyLibraryForm(this);
	this.layer = layer;
	symbolForm = this;
};

SymbologySymbolForm.prototype.createForm_back = function( type, json, featureIndex, ruleIndex, symbolIndex, readOnly) {
    this.type = type;
    this.currentSymbol = json;

	var tabscontainer = $("<div>");

	var featureDiv = $("<div>", {class: "collection"});

	var tabClass =  "tab col s3";
	var tabActived = "active";
	
	var symbolName = $("<div>", {class: "symbol-panel-title"});
	var nameInput =  $("<input>", {id: "form-symbol-name", class: " form-control", type: "text", value: json.fields.name});
	symbolName.append(nameInput);
	
	
	var symbolizerClass = "";
	if(type && type=="PointSymbolizer"){
		symbolizerClass = "fa-map-marker";
	}

	if(type && type=="LineSymbolizer"){
		symbolizerClass = "fa-minus";
	}

	if(type && type=="PolygonSymbolizer"){
		symbolizerClass = "fa-globe";
	}
	
	if(type && type=="TextSymbolizer"){
		symbolizerClass = "fa-bold";
	}
	
	var symbolPreview = $("<div>", {id:"symbol-" + json.pk + "-preview", class: "symbol-editor symbol-panel-preview"});
	var pointTabIcon = $("<i>", {class: "fa " + symbolizerClass, style:"font-size: 40px;"});
	
	symbolPreview.append(pointTabIcon);
	
	$('#modal-symbology .modal-header').empty();
	$('#modal-symbology .modal-header').append(symbolPreview);
	$('#modal-symbology .modal-header').append(symbolName);

	var pointContent = $("<div>", {class:"col-md-12", id: "symbol-editor"});
	var sldjson = $.xml2json("<StoredSLD>" +
				json.fields.sld_code + "</StoredSLD>");
	var pointForm = this.makeSymbolForm(sldjson[type], type, readOnly);
	pointContent.append(pointForm);
	//tabscontainer.append(pointContent);
	
	var libraryContent = $("<div>", {class:"col-md-12 hidden", id: "library-chooser"}); 
	var libraryForm = this.libraryForm.makeLibraryForm(sldjson[type], type, readOnly);
	libraryContent.append(libraryForm);
	//tabscontainer.append(libraryContent);

    $('#modal-symbology .modal-footer').empty();
	var cancelText = gettext("Cancel");
	if(readOnly){
		cancelText = gettext("OK");
	}
	var libraryButton = $("<a>", {id: "formLibraryButton", class: "library-symbol-button modal-action waves-effect waves-green btn-flat", text: gettext("Library")});
	
	var acceptButton = $("<a>", {id: "formAcceptButton", class: "add-new-symbol-button modal-action modal-close waves-effect waves-green btn-flat", text: gettext("Aceptar")});
	var cancelButton = $("<a>", {id: "formCancelButton", class: "cancel-new-symbol-button modal-action modal-close waves-effect waves-green btn-flat", text: cancelText});
	if(!readOnly){
		$('#modal-symbology .modal-footer').append(libraryButton);
		$('#modal-symbology .modal-footer').append(acceptButton);
	}
	$('#modal-symbology .modal-footer').append(cancelButton);
	
	if(symbolIndex != null){
		var borrarButton = $("<a>", {id: "formDeleteButton",class: "delete-new-symbol-button modal-action modal-close waves-effect waves-green btn-flat", text: "Eliminar símbolo"});
		//$('#modal-symbology .modal-footer').append(borrarButton);
	}

	$('#modal-symbology .modal-body').empty();
	$('#modal-symbology .modal-body').append(this.makeSymbolForm(sldjson[type], type, readOnly));


	this.formFunctionality(readOnly);
	
	var that = this;
	$("#formAcceptButton").unbind("click").click(function(){
		var type = that.type;
		that.currentSymbol.fields.name = $("#form-symbol-name").val();
		var jsonSymbol = {};
		var jsonText = {};
		var hasLabel = true;
		if(that.currentSymbol.fields.sld_code != null && that.currentSymbol.fields.sld_code != ""){
			var sld = that.currentSymbol.fields.sld_code
			var sldjson = $.xml2json("<StoredSLD>" +
					json.fields.sld_code + "</StoredSLD>");
			jsonSymbol = sldjson[type];
			if(jsonSymbol == null){
				sldjson[type] = {};
				jsonSymbol = sldjson[type];
			}
		}
		var output =  that.getFormValues(jsonSymbol, type);
		
		var xmljson = "";
		for(var i=0; i<output.length; i++){
			xmljson += that.symbologyUtils.json2xml(output[i], type);
		}
		xmljson = xmljson.replace(/<CssParameter[^>]*><\/CssParameter>/g, "");
		
		that.currentSymbol.fields.sld_code = xmljson;
		console.log(that.currentSymbol.fields.sld_code);
		
	}); 

	$("#formCancelButton").unbind("click").click(function(){
	}); 
	
	$("#formLibraryButton").unbind("click").click(function(e){
		e.stopPropagation();
		$("#symbol-editor").toggle();
		$("#library-chooser").toggle();
		var label = $(this).text();
		if(label == gettext("Library")){
			$(this).text(gettext("Editor"));
			that.updatePreviewFunction();
			that.libraryForm.setData(that.currentSLD);
			that.libraryForm.loadLibraries();
		}else{
			$(this).text(gettext("Library"));
			that.updatePreviewFunction();
		}
	}); 

};


SymbologySymbolForm.prototype.createForm = function( type, json, featureIndex, ruleIndex, symbolIndex, readOnly) {	
	var self = this;
	this.type = type;
    this.currentSymbol = json;
    
	var symbolizerClass = "";
	if(type && type=="PointSymbolizer"){
		symbolizerClass = "fa-map-marker";
		
	} else if(type && type=="LineSymbolizer"){
		symbolizerClass = "fa-minus";
		
	} else if(type && type=="PolygonSymbolizer"){
		symbolizerClass = "fa-globe";
	} else if(type && type=="TextSymbolizer"){
		symbolizerClass = "fa-bold";
	}
	
	var sldjson = $.xml2json("<StoredSLD>" + json.fields.sld_code + "</StoredSLD>");
	
	var ui = '';
	ui += '<div class="box box-default">';
	
	ui += 	'<div class="box-header with-border">';
	ui +=		'<i class="fa ' + symbolizerClass + '"></i>';
	ui += 		'<h3 class="box-title">' + json.fields.name + '</h3>';
	ui += 	'</div>';
	
	ui += 	'<div class="box-body">';
	ui +=	this.makeSymbolForm(sldjson[type], type, readOnly);
	ui += 	'</div>';
	
	ui += 	'<div class="box-footer text-center">';
	ui += 	'</div>';
	
	ui += '</div>';
	
	$('#modal-symbology .modal-body').empty();
	$('#modal-symbology .modal-body').append(ui);
	
	
	$("#modal-symbology").on('shown.bs.modal', function () {
		self.updatePreviewFunction();
	});
};


SymbologySymbolForm.prototype.formFunctionality = function(readOnly) {
	
	//$('ul.tabs').tabs();
	
	//this.formHelper.loadImagePickerInput("/media/");
	
	$(".collapsible-header").unbind("click").click(function (e) {
		var parent = $(this).parent();
		if (this.children[0].className == 'fa fa-angle-down') {
			this.children[0].className = this.children[0].className.replace('fa fa-angle-down', 'fa fa-angle-up');
			parent.find(".collapsible-body").css("display", "none");

		} else if (this.children[0].className == 'fa fa-angle-up'){
			this.children[0].className = this.children[0].className.replace('fa fa-angle-up', 'fa fa-angle-down');
			parent.find(".collapsible-body").css("display", "block");
		}
	});

	if(!readOnly){		
		$(".panel-chooser-radio").unbind("click").click(function(){
			var iden = $(this).attr('id');
			var group = $(this).attr('name');
			$(".panel-"+group).each(function(){
				if(!$(this).hasClass("panel-chooser-hidden")){
					$(this).addClass("panel-chooser-hidden");
				}
			});
			$("#"+"panel-"+iden).removeClass("panel-chooser-hidden");
		});
		
		$(".panel-chooser-checkbox").unbind("click").click(function(){
			var iden = $(this).attr('id');
			var group = $(this).attr('name');
			$(".panel-"+group).each(function(){
				if(!$(this).hasClass("panel-chooser-hidden")){
					$(this).addClass("panel-chooser-hidden");
				}
			});
			var checked = $(this).is(':checked');
			if(checked){
				$("#"+"panel-"+iden).removeClass("panel-chooser-hidden");
				symbolForm.formFunctionality();
			}
		});
	}

	$(".collection-item input").unbind("change").change(function(e){
		e.stopPropagation();
		var parent = $(this).closest(".collection-item");	
		if(!parent.hasClass("selectedField")){
			parent.addClass("selectedField");
		}
	}); 
	
	$(".collection-item input").unbind("dblclick").dblclick(function(e){
		e.stopPropagation();
	});
	
	$(".collection-item").unbind("dblclick").dblclick(function(e){
		e.stopPropagation();
		var parent = $(this).closest(".collection-item");	
		if(parent.hasClass("selectedField")){
			parent.removeClass("selectedField");
		}else{
			parent.addClass("selectedField");
		}
	}); 
	
	$(".image-preview-change").unbind("click").click(function() {
		var parent = $(this).parents(".image-preview-container");
		var comp = parent.parent().find(".image-selector")
		comp.toggle();
	});
	
	$(".imagepicker .caret").addClass("hidden");
	$(".imagepicker .select-dropdown").addClass("hidden");
	
   	$(".tab-container li").unbind("click").click(this.previewButtonFunction);
  	$(".tab-container li:first").addClass("selected");
  	
  	$(".up-tab").unbind("click").click(this.upButtonFunction);
  	$(".down-tab").unbind("click").click(this.downButtonFunction);
  	$(".delete-tab").unbind("click").click(this.deleteButtonFunction);
  	
  	$(".collection-item input").unbind("change").change(this.updatePreviewFunction);
  	$(".collection-item select").unbind("change").change(this.updatePreviewFunction);
};


SymbologySymbolForm.prototype.getData = function() {
	return this.currentSymbol;
};


SymbologySymbolForm.prototype.getType = function() {
	return this.type;
};

SymbologySymbolForm.prototype.updatePreviewFunction = function(){
		var label = $(this).parents(".preview-form").attr("label");
		if(label == null){
			label = [];
			$(".preview-form-tab-div").each(function(){
				label.push($(this).attr("label"));
			})
		}else{
			label = [label];
		}
		symbolForm.currentSLD = [];
		for(var i=0; i<label.length; i++){
	  		var index = parseInt(label[i]);
	  		var fType = JSON.parse(JSON.stringify(SLDDefaultValues[symbolForm.type]));
	  		var values = symbolForm.getsubFormValues({}, fType, index);
	  		symbolForm.currentSLD.push(values);
	  		
	  		var symbologyPreview = new SymbologyPreview(null);
	  		$("#preview-form-tab-div-"+label[i]).empty();
			var symbolPreview = symbologyPreview.renderPreview(
				values, 
				symbolForm.type, 
				"preview-form-tab-div-"+label[i]);
			if(symbolPreview != null){
				$("#preview-form-tab-div-"+label[i]).append(symbolPreview);
			}
		}
  	}

SymbologySymbolForm.prototype.deleteButtonFunction = function(){
	var label = $(this).attr("label");
	var selectedTab = $(".preview-button-form-"+label);
	var selectedForm = $("#menu-PointSymbolizer-form"+label);
	
	if($(".preview-button").length > 1){
		selectedTab.remove();
		selectedForm.remove();
		
		$(".tab-container li:first").trigger("click");
	}else{
		alert("Es la última definición, no se puede borrar");
	}
}

SymbologySymbolForm.prototype.upButtonFunction = function(){
	var label = $(this).attr("label");
	var selectedTab = $(".preview-button-form-"+label);
	var prevTab = selectedTab.prev();
	if(prevTab.length > 0){
		var auxsel = selectedTab.clone();
		var auxprev = prevTab.clone();
		prevTab.replaceWith(auxsel);
		selectedTab.replaceWith(auxprev);
		
		$(".tab-container li").unbind("click").click(symbolForm.previewButtonFunction);
	}
}

SymbologySymbolForm.prototype.downButtonFunction = function(){
	var label = $(this).attr("label");
	var selectedTab = $(".preview-button-form-"+label);
	var nextTab = selectedTab.next();
	if(nextTab.length > 0 && !nextTab.hasClass("preview-form-button-add")){
		var auxsel = selectedTab.clone();
		var auxnext = nextTab.clone();
		nextTab.replaceWith(auxsel);
		selectedTab.replaceWith(auxnext);
		
		$(".tab-container li").unbind("click").click(symbolForm.previewButtonFunction);
	}
}


SymbologySymbolForm.prototype.previewButtonFunction = function(){
		var label = $(this).attr("label");
		if(label == "add-symbol"){
			var i = $('.preview-button').length;
			var preview = $("<li>", {class:"preview-form-tab preview-button preview-button-form-"+i, label:""+i});
			var previewDiv = $("<div>", {id:"preview-form-tab-div-"+i, class:"preview-form-tab-div", label:""+i});
			preview.append(previewDiv);
			var form = $("<ul>", {id: "menu-"+symbolForm.type+"-form"+i, label: i+"", class: "menu-"+symbolForm.type+"-form collection preview-form preview-form-"+i, style:"display:none;"});
			var buttons = $("<div>", {class: "preview-form-buttons"});
			var buttonDelete = $("<i>", {class: "fa fa-ban tab-button delete-tab", label:""+i});
			var buttonDown = $("<i>", {class: "fa fa-chevron-down tab-button down-tab", label:""+i});
			var buttonUp = $("<i>", {class: "fa fa-chevron-up tab-button up-tab", label:""+i});
			buttons.append(buttonDelete);
			buttons.append(buttonDown);
			buttons.append(buttonUp);
			var buttonsClear = $("<div>", {class: "clearBoth"});
			buttons.append(buttonsClear);
			var new_symbol = symbolForm.symbologyUtils.createEmptySymbol("aux", symbolForm.type);
			var sldjson = $.xml2json("<StoredSLD>" +
						new_symbol.fields.sld_code + "</StoredSLD>");
			
			form.append(buttons);
			var fType = JSON.parse(JSON.stringify(SLDDefaultValues[symbolForm.type]));
			form.append(symbolForm.formHelper.createSubForm(new_symbol.fields.sld_code, fType, symbolForm.type, false, i));
			preview.insertBefore(".preview-form-button-add");
			form.insertBefore(".preview-form-add");
			$(".tab-container li").unbind("click").click(symbolForm.previewButtonFunction);
			
			$(".up-tab").unbind("click").click(symbolForm.upButtonFunction);
		  	$(".down-tab").unbind("click").click(symbolForm.downButtonFunction);
		  	$(".delete-tab").unbind("click").click(symbolForm.deleteButtonFunction);
		  	symbolForm.formFunctionality();
		  	
		  	var symbologyPreview = new SymbologyPreview(null);
			var symbolPreview = symbologyPreview.renderPreview(
				sldjson[symbolForm.type], 
				symbolForm.type, 
				"preview-form-tab-div-"+i);
			if(symbolPreview != null){
				$(".preview-form-tab-div-"+i).append(symbolPreview);
			}
			$("#menu-"+type+"-form"+i).find(".collection-item input").first().trigger("change");
		}else{
			$(".preview-form-tab").removeClass("selected");
			$(".preview-button-form-"+label).addClass("selected");
		  	$(".preview-form").hide();
	     	$(".preview-form-"+label).show();
     	}
}

SymbologySymbolForm.prototype.loadPreviews = function(previews) {
	for(var i=0; i<previews.length; i++){
		var symbologyPreview = new SymbologyPreview(null);
		var symbolPreview = symbologyPreview.renderPreview(
			previews[i], 
			this.type, 
			"preview-form-tab-div-"+i);
		if(symbolPreview != null){
			$(".preview-form-tab-div-"+i).append(symbolPreview);
		}
		
	}
	
	$(".collection-item input").first().trigger("change");
};

SymbologySymbolForm.prototype.makeSymbolForm_back = function(data, type, readOnly) {
	var divForm = $("<div>");
	var divTabForm = $("<div>", {class:"nav-tabs-custom"});
	var divTabULForm = $("<ul>", {class:"nav nav-tabs"});
	var divContentForm = $("<div>", {class:"tab-content-container main-container"});
	var classUL = "collection";
	var featureType = JSON.parse(JSON.stringify(SLDDefaultValues[type]));
		
	if(!$.isArray(data)){
		data = [data];
	}
	
	for(var i=0; i<data.length; i++){
		var styledata = "display:block;";
		if(i>0){
			styledata = "display:none;";
		}
		var preview = $("<li>", {class:"preview-form-tab preview-button preview-button-form-"+i, label:""+i});
		var previewDiv = $("<div>", {id:"preview-form-tab-div-"+i, class:"preview-form-tab-div", label:""+i});
		preview.append(previewDiv);
		var form = $("<ul>", {id: "menu-"+type+"-form"+i, label: i+"", class: classUL+" preview-form preview-form-"+i+" menu-"+type+"-form" , style: styledata});
		var buttons = $("<div>", {class: "preview-form-buttons"});
		var buttonDelete = $("<i>", {class: "fa fa-ban tab-button delete-tab", label:""+i});
		var buttonDown = $("<i>", {class: "fa fa-chevron-down tab-button down-tab", label:""+i});
		var buttonUp = $("<i>", {class: "fa fa-chevron-up tab-button up-tab", label:""+i});
		buttons.append(buttonDelete);
		buttons.append(buttonDown);
		buttons.append(buttonUp);
		var buttonsClear = $("<div>", {class: "clearBoth"});
		buttons.append(buttonsClear);
		form.append(buttons);
		form.append(this.formHelper.createSubForm(data[i], featureType, type, readOnly, i));
		divTabULForm.append(preview);
		divContentForm.append(form);
	}
	
	var preview = $("<li>", {class:"preview-form-tab preview-form-button-add", label:"add-symbol"});
	var previewaddicon = $("<i>", {class:"fa fa-plus-circle preview-form-icon-add"});
	preview.append(previewaddicon);
	var form = $("<ul>", {id: "menu-"+type+"-form-add", class: classUL+" preview-form preview-form-add"});
	divTabULForm.append(preview);
	divContentForm.append(form);
	
	
	divTabForm.append(divTabULForm);
	divForm.append(divTabForm);
	divForm.append(divContentForm);

	return divTabForm;
};

SymbologySymbolForm.prototype.makeSymbolForm = function(data, type, readOnly) {
	
	var featureType = JSON.parse(JSON.stringify(SLDDefaultValues[type]));	
	if(!$.isArray(data)){
		data = [data];
	}
	
	var ui = '';
	ui += '<div class="nav-tabs-custom">';
	ui += 	'<ul class="nav nav-tabs">';
	ui +=		'<li><a href="#" class="text-muted"><i class="fa fa-plus"></i></a></li>';
	for(var i=0; i<data.length; i++){
		if (i==0) {
			ui += '<li class="active preview-button-form-' + i + '" label="' + i + '">';
		} else {
			ui += '<li class="preview-button-form-' + i + '" label="' + i + '">';
		}
		ui +=		'<a href="#' + i + '" data-toggle="tab">';
		ui +=			'<div id="preview-form-tab-div-' + i +'" class="preview-form-tab-div" label="' + i + '">';
		ui +=		'</a>';
		ui +=	'</li>';
	}
	ui += 	'</ul>';
	ui += 	'<div class="tab-content">';
	for(var i=0; i<data.length; i++){
		ui += 		'<div class="tab-pane active" id="tab_1-1">';
		ui += 		'</div>';
	}
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

SymbologySymbolForm.prototype.getFormValues = function(data, type) {
	var featureType = JSON.parse(JSON.stringify(SLDDefaultValues[type]));
	var auxdata = [];
	var that = this;
	
	$(".tab-container li.preview-button").each(function(){
		var label = $(this).attr("label");
		var index = parseInt(label);
		if(index == null){
			index = 0;
		}
		if(!Array.isArray(data)){
			data = [data];
		}
		if(data.length > index){
			auxdata.push(that.getsubFormValues(data[index], featureType, index));
		}else{
			auxdata.push(that.getsubFormValues({}, featureType, index));
		}
		label = "0";
	})
	
	return auxdata;
};

SymbologySymbolForm.prototype.removesubFormValues = function(data, json, label) {
	for(var key in json){
		if(json[key].type){
			if(json[key].definition && json[key].definition.component == "panel-chooser-input"){
				for(var idx = 0; idx < json[key].definition.values.length; idx++){
					data = this.removesubFormValues(data, json[key].definition.values[idx], label);
				}
			}else{
				var auxPath = jsonPath(data, json[key].definition.jsonPath, {resultType:"PATH"});
				if(!auxPath){
					auxPath = jsonPath(data, json[key].definition.jsonPath.replace(/\[\?.*?\]/g, ""), {resultType:"PATH"});
				}
				if(auxPath){
					if(json[key].definition["selectedOption"] !=null){
							json[key].definition["selectedOption"] = false;
					}
					eval( "delete " + auxPath[0].replace("$", "data"));
				}
			}
		}else{
			data = this.removesubFormValues(data, json[key], label);
		}	
	}

	return data;
};

SymbologySymbolForm.prototype.getsubFormValues = function(data, json, label) {
	for(var key in json){
		if(json[key].type){
			if(json[key].definition && json[key].definition.component != "panel-chooser-input"){
					var auxValue = null;
					if(json[key].definition["selectedOption"] !=null){
							json[key].definition["selectedOption"] = true;
					}
					
					if(json[key].definition.component == "color-chooser"){
						auxValue = "" + $("#"+json[key].definition.id+"-"+label).val();
					}
					if(json[key].definition.component == "range-input" || 
							json[key].definition.component == "number-input" ||
							json[key].definition.component == "text-input"){
						auxValue = "" + $("#"+json[key].definition.id+"-"+label).val() + "";
					}
					
					if(json[key].definition.component == "select-input"){
						auxValue = $("#"+json[key].definition.id+"-"+label).val();
					}
					
					if(json[key].definition.component == "image-picker-input"){
						auxValue = $("#"+json[key].definition.id+"-"+label).val();
					}
					
					if(json[key].definition.component == "check-input"){
						auxValue = $("#"+json[key].definition.id+"-"+label).val();
						if(auxValue == "on" || auxValue == "true"){
							auxValue = true;
						}else{
							auxValue = false;
						}
					}
					
					if(json[key].definition.component == "filter-input"){
						auxValueMethod = $("#"+json[key].definition.id+"-"+label+"-method"+"-"+label).val();
						auxValueField = $("#"+json[key].definition.id+"-"+label+"-field"+"-"+label).val();
						if(auxValueMethod != null && auxValueField != null && auxValueMethod != "" && auxValueField != ""  && auxValueMethod != "null"){
							auxValue = auxValueMethod + "(" + auxValueField + ")";
						}
						
						if(auxValueMethod == "" || auxValueField == "" || auxValueMethod == "null"){
							auxValue = "";
						}
						
					}
					
					
					if(auxValue != null){
						var auxPath = jsonPath(data, json[key].definition.jsonPath, {resultType:"PATH"});
						if(!auxPath){
							auxPath = jsonPath(data, json[key].definition.jsonPath.replace(/\[\?.*?\]/g, ""), {resultType:"PATH"});
						}
						if(!auxPath){
							this.createAccessByString(data, json[key].definition.jsonPath, auxValue);
							auxPath = jsonPath(data, json[key].definition.jsonPath, {resultType:"PATH"});
							if(!auxPath){
								auxPath = jsonPath(data, json[key].definition.jsonPath.replace(/\[\?.*?\]/g, ""), {resultType:"PATH"});
							}
						}
		
						if(auxPath){
							eval( auxPath[0].replace("$", "data") + "='"+ auxValue +"'");
						}
					}
					
			}
			if(json[key].definition && json[key].definition.component == "panel-chooser-input"){
				if(json[key].definition.type == "radio"){
					var index = $("input:radio[name ='"+ json[key].definition.id+"-"+label +"']:checked").val();
				}else{
					var index = -1;
					var checked = $("#"+json[key].definition.id+"-"+label+"-0").is(":checked");
					if(checked){
						index = 0;
					}
				}
				for(var idx = 0; idx < json[key].definition.values.length; idx++){
					if(idx != parseInt(index)){				
						data = this.removesubFormValues(data, json[key].definition.values[idx], label);
					}
				}
				if(index >= 0 && json[key].definition.values.length > index){
					data = this.getsubFormValues(data, json[key].definition.values[parseInt(index)], label);
				}
			}
		}else{
			data = this.getsubFormValues(data, json[key], label);
		}
	}

	return data;
};


SymbologySymbolForm.prototype.createAccessByString = function(o, s, value) {
	s = s.replace(/^\$\./, '');           // strip a leading dot
	s = s.replace(/\['(\w+)\']/g, '.$1'); // convert indexes to properties
	s = s.replace(/\[(\w+)\]/g, '.$1'); // convert indexes to properties
	s = s.replace(/\?\(@\.(.+)\)/g, '$1');          
	s = s.replace(/(\w+)\[(\w+==.+)\]/g, '$1.$2'); // convert indexes to properties
	var a = s.split('.');
	this.createSubAccessByString(o, a, value)
};

SymbologySymbolForm.prototype.createSubAccessByString = function(o, a, value) {
	if(a.length == 0){
		o = value;
		return o;
	}
	
	var k = a[0];

	if(k.indexOf("==") > -1){
		var par = k.split("==");
		var key = par[0];
		var auxObj = {};
		auxObj[key] = par[1].replace(/\'/g, "");

		var founded = false;
		
		// Si es un Object
		if(((typeof o) != "string")){
			if(o[par[0]] == auxObj[par[0]]){
				founded = true;
			}
		}
		
		//Si es un Array
		for(var l=0; l<o.length; l++){
			if(o[l][par[0]] == auxObj[par[0]]){
				founded = true;
				//o = o[l];
				o[l] = this.createSubAccessByString(o[l], a.slice(1,a.length), value);
			}
		}
		if(!founded && ((typeof o) != "string") ){
			var elFounded = -1;
			if(!(o instanceof Array)){
				o = [o];
			}
			for(var m=0; m<o.length; m++){
				if(o[m][key] == auxObj[key]){
					elFounded = m;
				}
			}
			if(elFounded < 0){
				var aux = {};
				for (var attrname in auxObj) { 
					aux[attrname] = auxObj[attrname]; 
				}
				o.push(aux);
				elFounded = o.length-1;
			}
			//o = o[o.length-1];
			//o[o.length-1] = this.createSubAccessByString(o[o.length-1], a.slice(1,a.length), value);
			o[elFounded] = this.createSubAccessByString(o[elFounded], a.slice(1,a.length), value);
		}
	}else{
		if(o[k] == "" || o[k] == null){
			o[k] = {};
		}
		o[k] = this.createSubAccessByString(o[k], a.slice(1,a.length), value);
	}
	
	return o;
};