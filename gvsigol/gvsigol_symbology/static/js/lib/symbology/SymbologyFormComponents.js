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

var SymbologyFormComponents = function() {	
};


SymbologyFormComponents.prototype.createSubForm = function(data, json, type, readOnly, iter) {
	var subform = $("<div>", {class: "symbol-form"});
	var index = 0;
	if(iter){
		index = iter;
	}

	for(var key in json){
		if(json[key].type && json[key].type == "field-definition"){
			if(json[key].definition){
				var aux = this.createFormComponent(data, json[key].definition, type, readOnly, index);
				subform.append(aux);
			}
		}else{
			var newform = $("<ul>", {id: key+"-menu-"+type+"-form-"+index, class: key+"-menu-"+type+"-form collection subcollection collapsible", "data-collapsible":"expandable"});
			var newDivHeader = $("<div>", {class: "collapsible-header active", style:"font-size: 14px;", text: key});
			var baseLayersHeaderIcon = $("<i>", {class: "fa fa-angle-up"});
			newDivHeader.append(baseLayersHeaderIcon);
			var newDivBody = $("<div>", {class: "collapsible-body", style:"display: none;"});

			var aux = this.createSubForm(data, json[key], type, readOnly, index);
			newDivBody.append(aux);
			newform.append(newDivHeader);
			newform.append(newDivBody);
			subform.append(newform);
		}
	}

	return subform;
};

SymbologyFormComponents.prototype.createFormComponent = function(json, definition, type, readOnly, iter) {
	var formComponent = null;
	var value = definition.defaultValue;
	var selected = false;
	var edited = false;
	if(definition.mandatory){
		selected = definition.mandatory;
	}

	if(json != null && definition.jsonPath){
		var auxValue = jsonPath(json, definition.jsonPath);
		if(!auxValue){
			auxValue = jsonPath(json, definition.jsonPath.replace(/\[\?.*?\]/g, ""));
		}
		if(auxValue && auxValue.length > 0){
			value = auxValue[0];
			selected = true;
			edited = true;
		}	
	}
	
	if(definition.component == "alert-message"){
		formComponent = this.createAlertMessage(definition.type, definition.id, definition.defaultValue, iter, definition);
	}

	if(definition.component == "color-chooser"){
		formComponent = this.createFormColorChooser(definition.label, definition.id, value, readOnly, selected, iter, definition, edited);
	}

	if(definition.component == "range-input"){
		formComponent = this.createFormRange(definition.label, definition.id, value, definition.min, definition.max, definition.step, readOnly, selected, iter, definition);
	}

	if(definition.component == "number-input"){
		formComponent = this.createFormInput(definition.label, definition.id, "number",  definition.min, definition.max, value, readOnly, selected, iter, definition);
	}

	if(definition.component == "select-input"){
		formComponent = this.createSelectInput(definition.label, definition.id, value, definition.values, definition.initialOption, readOnly, selected, iter, definition);
	}

	if(definition.component == "text-input"){
		formComponent = this.createFormTextInput(definition.label, definition.id, value, readOnly, selected, iter, definition);
	}
	
	if(definition.component == "filter-input"){
		formComponent = this.createFormFilterInput(definition.label, definition.id, value, definition.values, definition.fieldvalues, definition.initialOption, readOnly, selected, iter, definition);
	}

	if(definition.component == "check-input"){
		formComponent = this.createCheckInput(definition.label, definition.id, definition.group, value, definition.classes, readOnly, selected, iter, definition);
	}
	
	if(definition.component == "image-picker-input"){
		formComponent = this.createImagePickerInput(definition.label, definition.id, value, definition.rootUrl, definition, iter, definition);
	}

	if(definition.component == "panel-chooser-input"){
		formComponent = this.createPanelChooserInput(
				definition.label, definition.id, definition.type, definition.optionNames, definition.values, value, definition.jsonPath, "", readOnly, json, definition, type, selected, iter, definition);
	}

	return formComponent;
};


SymbologyFormComponents.prototype.getImagePickerUrl = function() {
	var url = "/media/";
	var urlpaths = $(".url-selector").find("span");
	
	return url;
};

SymbologyFormComponents.prototype.loadImagePickerInput = function(url, comp) {
	var that = this;
	
	var rooturl = url;
	var restpath = url.replace(rooturl, "");
	
	var steps = restpath.split("/");
	var parentComp = $(".image-selector");
	if(comp){
		parentComp = comp;
	}
	
	parentComp.find(".url-selector").empty();
	var raiz = $("<span>", {class: "url-path", "src-dir": rooturl, text:gettext("/")});
	parentComp.find(".url-selector").append(raiz);
	
	
	for(var i=0; i<steps.length; i++){
		if(steps[i] != ""){
			var middelurl = rooturl;
			for(j=0;j<=i;j++){
				middelurl = middelurl + steps[j] + "/";
			}
			var separator = $("<span>", {class: "url-path-separator", text: " > "});
			parentComp.find(".url-selector").append(separator);
			var step = $("<span>", {class: "url-path", "src-dir": middelurl, text: decodeURI(steps[i]) });
			parentComp.find(".url-selector").append(step);
		}
	}
	
	$(".url-path").unbind("hover").hover(function(){
		$(this).addClass("top-operation-hover");	
	},function(){
		$(this).removeClass("top-operation-hover");	
	});
	
	$(".url-path").unbind("click").click(function(){
		var url = $(this).attr("src-dir");
		that.loadImagePickerInput(url, parentComp);
	});
	
	$(".symbol_input_file_open").unbind("click").click(function(e){
		$(this).parents(".image-selector").find(".symbol_input_file").trigger("click");
	});

	$.get(url, function( data ) {
		var optionsSelect = $("<select>", {class: "imagepicker image-picker show-labels show-html"});
		var options0 = $("<option>");
		optionsSelect.append(options0);
		var i=0;
	     $(data).find("td > a").each(function(){
	        var images = $(this).attr("href");
	        if(images.indexOf("/") != 0){
		        if(images.indexOf("/", images.length - 1) !== -1){
		        	var folderurl = images;
		        	if(images.indexOf("/") != 0){
		        		folderurl = url + images;
		        	}
		        	var options1 = $("<option>", {"data-img-src": "/icons/folder.gif", "data-img-label": decodeURI(images), value:i, text: images, "data-src": folderurl});
		        }else{
		        	if((images.indexOf(".gif", images.length - 4) !== -1) ||
		        		(images.indexOf(".png", images.length - 4) !== -1) ||
		        		(images.indexOf(".jpg", images.length - 4) !== -1)){
		        		var options1 = $("<option>", {"data-img-src":  url+images, "data-img-label": decodeURI(images), value:i, text: images, "data-src": url+images});
		        	}else{
		        		var options1 = $("<option>", {"data-img-src": "/icons/unknown.gif", "data-img-label": decodeURI(images), value:i, text: images, "data-src":  url+images});
		        	}
		        }
				optionsSelect.append(options1);
	        	i = i+1;
        	}
	     });
	     parentComp.find(".image-selector-container").empty();
	     parentComp.find(".image-selector-container").append(optionsSelect);
	     $("select.imagepicker").imagepicker(
			{show_label: true}
		);
		$(".image_picker_image").each(function(){
			$(this).attr("HEIGHT", 50);
		});
		
		$(".thumbnail").unbind("dblclick").dblclick(function(e) {
			e.stopPropagation();
			if($(this).find("img").attr("src") == "/icons/folder.gif"){
				var srcrootimage = that.getImagePickerUrl();
				var srcimage = $(this).find("img").attr("data");
				
				that.loadImagePickerInput(srcimage, parentComp);
			}else{
				var parent = $(this).parents(".image-selector").parent();
				
				var srcrootimage = that.getImagePickerUrl();
				var srcimage = $(this).find("img").attr("src");
				
				parent.find(".image-preview-preview").empty();
				var imgprev = $("<img>", {height: 40, src: srcimage});
				parent.find(".image-preview-preview").append(imgprev);
				
				parent.find(".image-preview-name").text(srcimage);
				parent.find(".image-preview-data input[type=hidden]").val(srcimage.replace("/media/", ""));
				parent.find(".image-selector").hide();
				
				$(this).parents(".panel-chooser-container").parent().find(".panel-chooser-radio").first().trigger("change");
			}
		});
		
		$(".thumbnail").unbind("click").click(function(){
			$(".thumbnail").each(function(){
				$(this).removeClass("top-operation-hover");	
			})
			$(this).addClass("top-operation-hover");
		});
		
		$(".symbol_input_file").off("change").on("change", function(e){
			var input  = $(this)[0].files[0];
			var filename = $(this)[0].files[0].name;
			
			var parent = $(this).parents(".image-selector");
			parent.find(".symbol_input_name").val(filename);
			parent.find(".symbol_input_name").show();
			parent.find(".symbol_input_submit").show();
		});
		
		
		$(".symbol_input_submit").unbind("click").click(function(){
			var parent = $(this).parents(".image-selector").find(".upload-form");
		    var formData = new FormData(parent[0]);
		    var files = $(".symbol_input_file").prop("files");
		    formData.append("name", $(".symbol_input_name").val());
		    
		    $.ajax({
	            type: "POST",
	            url: "/gvsigonline/symbol_upload/",
	            enctype: 'multipart/form-data',
	            data: formData,
	            processData: false,
    			contentType: false,
	            success: function (response) {
	            	var srcimage = response.content["main_url"] + response.content["filename"];
	                that.loadImagePickerInput(response.content["main_url"], parentComp);
	                $('ul.tabs').tabs('select_tab', 'opcion1');
	                
	                $(".image-preview-preview").empty();
					var imgprev = $("<img>", {height: 40, src: srcimage});
					$(".image-preview-preview").append(imgprev);
					
					$(".image-preview-name").text(srcimage);
					$(".image-preview-data input[type=hidden]").val(srcimage.replace("/media/", ""));
					$(".image-selector").hide();
	            }
	        });
		});
	});
}

SymbologyFormComponents.prototype.createImagePickerInput = function(label, iden, url, defaultValue, definition, iter, definition) {
	var pointFormSizeLi = $("<li>", {class: "collection-item"});
	var imageContainer2 = $("<div>", {class: "image-preview-container"});
	var imageContainerPreview = $("<div>", {class: "image-preview-preview"});
	var imageContainerData = $("<div>", {id: "image-preview-data-"+iter, class: "image-preview-data"});
	
	if(!url || url == ""){
		var noImage = gettext("Sin imagen");
		definition["selectedOption"] = false;
	}else{
		var aux = "";
		if(url["OnlineResource"] && url["OnlineResource"]["xlink:href"]){
			this.xlink = url["OnlineResource"]["xlink:href"];
			var urlx = url["OnlineResource"]["xlink:href"];
			var url_parts = urlx.split("/media/");
			if(url_parts.length > 1){
				for(var i=1; i<url_parts.length; i++){
					aux = aux + "/media/" + url_parts[i];
				}
			}else{
				aux = urlx;
			}
			url = aux;
		}
		
		var noImage = url;
		if(!url.startsWith(defaultValue)){
			noImage = defaultValue + url;
		}
		var imgprev = $("<img>", {height: 40, src: noImage});
		imageContainerPreview.append(imgprev);
		definition["selectedOption"] = true;
	}
	var imageContainerName = $("<span>", {id: "image-preview-name-"+iter, class: "image-preview-name", text: noImage});
	var imageContainerBr = $("<br>");
	var imageContainerChange = $("<span>", {class: "image-preview-change", text:"Cambiar"});
	var imageContainerClear = $("<div>", {style: "clear:both;"});
	
	imageContainer2.append(imageContainerPreview);
	
	imageContainerData.append(imageContainerName);
	imageContainerData.append(imageContainerBr);
	imageContainerData.append(imageContainerChange);
	
	imageContainer2.append(imageContainerData);
	imageContainer2.append(imageContainerClear);
	pointFormSizeLi.append(imageContainer2);
	
	var imageTabsDiv = $("<div>", {class: "col s12"});
	var imageTabsUl = $("<ul>", {class: "tabs"});
	var imageTabsLi1 = $("<li>", {class: "tab col s3"});
	var imageTabsA1 = $("<a>", {href: "#opcion1-"+iter, class:"active", text: gettext("Simbolos cargados")});
	var imageTabsLi2 = $("<li>", {class: "tab col s3"});
	var imageTabsA2 = $("<a>", {href: "#opcion2-"+iter, text: gettext("Subir símbolo")});
	imageTabsLi1.append(imageTabsA1);
	imageTabsLi2.append(imageTabsA2);
	imageTabsUl.append(imageTabsLi1);
	imageTabsUl.append(imageTabsLi2);
	
	imageTabsDiv.append(imageTabsUl);
	
	
	var imageContainer = $("<div>", {class: "image-selector hidden"});
	imageContainer.append(imageTabsDiv);
	
	var imageContainer2 = $("<div>", {id:"opcion1-"+iter, class: "col s12"});
	var ruta = $("<div>", {class: "url-selector"});
	var optionsContainer = $("<div>", {class: "image-selector-container"});
	imageContainer2.append(ruta);
	imageContainer2.append(optionsContainer);
	
	
	var imageContainer3 = $("<div>", {id:"opcion2-"+iter, class: "col s12"});
	var form = $("<form>", {id: "upload-form-"+iter, class:"upload-form", method:"post", action:"/gvsigonline/symbol_upload/", enctype:"multipart/form-data"});
	

	var filebtnInput2 = $("<input>", {class:"symbol_input_file hidden", type: "file", name:"file", accept:"image/png"});
	var fileSubmit2 = $("<a>", {class:"waves-effect waves-light btn symbol_input_file_open float_left", text:gettext("Selecciona imagen")});	
	var rightdiv = $("<div>", {class:"name-input-div"});
	var fileNameInputDiv = $("<input>", {class:"symbol_input_name hidden", type:"text", value:"", name:"file_name", id:"file_name-"+iter});
	var fileClear2 = $("<div>", {class:"clearBoth"});
	form.append(filebtnInput2);
	form.append(fileSubmit2);
	rightdiv.append(fileNameInputDiv);
	form.append(rightdiv);
	form.append(fileClear2);
	
		
	var fileSubmit = $("<a>", {class:"waves-effect waves-light btn symbol_input_submit hidden float_right", text:gettext("Subir símbolo")});	
	var fileClear = $("<div>", {class:"clearBoth"});	
	form.append(fileSubmit);
	form.append(fileClear);
	
	imageContainer3.append(form);
	
	var imageInput = $("<input>", {id: iden+"-"+iter, type: "hidden", value: noImage.replace("/media/", "")});
	imageContainerData.append(imageInput);
	pointFormSizeLi.append(imageContainer);
	imageContainer.append(imageContainer2);
	imageContainer.append(imageContainer3);
	
	return pointFormSizeLi;
};

SymbologyFormComponents.prototype.createPanelChooserInput = function(label, iden, typex, names, values, defaultValue, jsonField, classes, readOnly, json, definition, type, selected, iter, definition) {
	var checked = false;
	
	var liClass = "collection-item";
	if(selected){
		liClass = liClass +" selectedField"
	}
	
	var pointFormSizeLi = $("<li>", {class: liClass});
	var optionsContainer = $("<div>", {});
	var panelContainer = $("<div>", {class: "panel-chooser-container"});
	var formContainer = $("<form>", {action: "#", class:"panel-chooser-select-"+typex});
	if(typex == "checkbox"){
		if(jsonPath(json, definition.jsonPath)){
			defaultValue = 0;
			checked = true;
		}
	}
	
	for(var i=0; i<names.length; i++){
		if(!(i != 0  && typex == "checkbox")){
			var pinput = $("<p>", {class:"panel-chooser-pinput"});
			if(readOnly){
				var pointSizeButton = $("<input>", {id: iden+"-"+iter+"-"+i, name: iden+"-"+iter, value: i+"",type: typex, class: "panel-chooser-"+typex+" "+classes, disabled: "disabled"});
			}else{
				var pointSizeButton = $("<input>", {id: iden+"-"+iter+"-"+i, name:  iden+"-"+iter, value: i+"",type: typex, class:"panel-chooser-"+typex+" "+classes});
			}
		
			var pointSizelabel = $("<label>", {for: iden+"-"+iter+"-"+i, text: names[i]});
			pinput.append(pointSizeButton);
			pinput.append(pointSizelabel);
			formContainer.append(pinput);
		}
		
		var panelChooser = $("<div>", {id: "panel-"+iden+"-"+iter+"-"+i, class: "panel-"+iden+"-"+iter + " collection-item panel-chooser panel-chooser-hidden"});
	
		panelChooser.append(this.createSubForm(json, definition.values[i], type, readOnly, iter));
		panelContainer.append(panelChooser);
	}
	
	var clearBoth = $("<div>", {class:"clearBoth"});
	formContainer.append(clearBoth);
	
	if(typex != "checkbox"){
		checked = true;
		for(var k=0; k<definition.values.length; k++){
			var opt = definition.values[k];
			for(var key in opt){
				if(opt[key].type && opt[key].type == "field-definition"){
					if(opt[key].definition["selectedOption"] != null && opt[key].definition["selectedOption"]){
						defaultValue = k;
					}
				}
			}
		}
	}
	
	if(formContainer[0].length > defaultValue && panelContainer[0].childNodes.length > defaultValue){
		if(checked){
			formContainer[0][defaultValue].checked = true;
			panelContainer[0].childNodes[defaultValue].className =  "panel-"+iden+"-"+iter + " collection-item panel-chooser";
		}
	}
	
	optionsContainer.append(formContainer);
	
	pointFormSizeLi.append(optionsContainer);
	pointFormSizeLi.append(panelContainer);
	return pointFormSizeLi;
};

SymbologyFormComponents.prototype.createAlertMessage = function(type, iden, defaultvalue, iter, definition) {
	var pointFormSizeLi = $("<li>", {class: type + " collection-item"});
	var pointFormSizeI = $("<i>", {class: "fa fa-exclamation-circle"});
	var pointFormSizeSpan = $("<span>", {text: gettext(defaultvalue)});
	pointFormSizeLi.append(pointFormSizeI);
	pointFormSizeLi.append(pointFormSizeSpan);
	
	return pointFormSizeLi;
};

SymbologyFormComponents.prototype.createCheckInput = function(label, iden, group, defaultvalue, classes, readOnly, selected, iter, definition) {
	var liClass = iden + " collection-item";
	if(selected){
		liClass = liClass +" selectedField"
	}
	var pointFormSizeLi = $("<li>", {class: liClass});
	var tp = "checkbox";
	if(group && group.length> 0){
		tp="radio";
	}
	if(defaultvalue != null){
		if(readOnly){
			var pointSizeButton = $("<input>", {id: iden+"-"+iter, type: tp, checked: "checked", class:classes, disabled: "disabled"});
		}else{
			var pointSizeButton = $("<input>", {id: iden+"-"+iter, type: tp, checked: "checked", class:classes});
		}
	}else{
		if(readOnly){
			var pointSizeButton = $("<input>", {id: iden+"-"+iter, type: tp, class:classes, disabled: "disabled"});
		}else{
			var pointSizeButton = $("<input>", {id: iden+"-"+iter, type: tp, class:classes});
		}
	}
	if(readOnly){
		pointSizeButton.attr("disabled");
	}
	var pointFormSize = $("<label>", {text: gettext(label), for: iden+"-"+iter});
	pointFormSizeLi.append(pointSizeButton);
	pointFormSizeLi.append(pointFormSize);

	return pointFormSizeLi;
};

SymbologyFormComponents.prototype.createFormColorChooser = function(label, iden, defaultValue, readOnly, selected, iter, definition, edited) {
	var liClass = iden + " collection-item";
	if(selected){
		liClass = liClass +" selectedField"
	}
	if(defaultValue.startsWith('rgb')){
		var symbologyUtils = new SymbologyUtils();
		defaultValue = symbologyUtils.rgb2hex(defaultValue);
	}
	
	if(definition && definition["selectedOption"] != null){
		definition["selectedOption"] = edited;
	}
	
	var pointFormColorLi = $("<li>", {class: liClass});
	var pointFormColor = $("<div>", {text: " » " + gettext(label), style: "font-size: 12px; font-weight: 300; color:#9e9e9e;"});
	var pointFormColorInput = $("<input>", {id: iden+"-"+iter, type: "color", value: defaultValue, class:"waves-effect waves-light btn color-chooser", style:"display:block"});
	pointFormColor.append(pointFormColorInput);
	pointFormColorLi.append(pointFormColor);

	return pointFormColorLi;
};


SymbologyFormComponents.prototype.createSelectInput = function(label, iden, defaultvalue, values, initialoption, readOnly, selected, iter, definition) {
	var liClass = iden + " collection-item";
	if(selected){
		liClass = liClass +" selectedField"
	}
	var selectItem2 = $("<li>", {class: liClass});
	var selectItemDiv = this.createSelect(label, iden, defaultvalue, values, initialoption, readOnly, selected, iter, definition);
	selectItem2.append(selectItemDiv);

	return selectItem2;
};


SymbologyFormComponents.prototype.createSelect = function(label, iden, defaultvalue, values, initialoption, readOnly, selected, iter, definition) {
	var selectItemDiv = $("<div>");
	if(readOnly){
		var selectForm = $("<select>", {id:iden+"-"+iter, disabled: "disabled"});
	}else{
		var selectForm = $("<select>", {id:iden+"-"+iter});
	}
	if(values == ""){
		values = "{}";
	}
	var options = JSON.parse(values);
	var isFirst = true;

	if(initialoption.length > 0){
		var selectItem = $("<option>", {value: "", text: initialoption, disabled: "disabled", selected: "selected"});
		selectForm.append(selectItem);
	}
	if(definition && definition["selectedOption"] != null){
		definition["selectedOption"] = false;
	}
	for(k in options){
		if(k == defaultvalue){
			var selectItem = $("<option>", {value: k, text: options[k], selected: "selected"});
			if(definition && definition["selectedOption"] != null){
				definition["selectedOption"] = true;
			}
		}else{
			var selectItem = $("<option>", {value: k, text: options[k]});
		}
		selectForm.append(selectItem);
	}
	var selectLabel = $("<label>", {text: " » " + gettext(label)});
	selectItemDiv.append(selectLabel);
	selectItemDiv.append(selectForm);
	
	return selectItemDiv;
}

SymbologyFormComponents.prototype.createFormFilterInput = function(label, iden, defaultvalue, values, fieldvalues, initialoption, readOnly, selected, iter, definition) {
	var liClass = iden + " collection-item";
	if(selected){
		liClass = liClass +" selectedField"
	}
	var selectItemLi2 = $("<li>", {class: liClass});
	var selectItemDiv = $("<div>", {class: "col s6", style:"padding-right:5px;"});
	var selectItemDiv2 = $("<div>", {class: "col s6", style:"padding-left:5px;"});
	var defaultmethod = "";
	var defaultfield = "";
	
	var regex = new RegExp("([a-zA-Z0-9_\\-]*)\\(([^)]*)\\)", "g");
	if(defaultvalue != null && defaultvalue.match(regex)){
		var match = regex.exec(defaultvalue);
		if(match.length > 2){
			defaultmethod = match[1];
			defaultfield = match[2];
		}
	}
	var selectItem = this.createSelect("Función", iden+"-"+iter+"-method", defaultmethod, values, initialoption, readOnly, selected, iter, definition);
	var selectItem2 = this.createSelect("Campo geométrico", iden+"-"+iter+"-field", defaultfield, fieldvalues, initialoption, readOnly, selected, iter, definition);
	selectItemDiv.append(selectItem);
	selectItemDiv2.append(selectItem2);
	
	selectItemLi2.append(selectItemDiv);
	selectItemLi2.append(selectItemDiv2);
	var clearDiv = $("<div>", {style: "clear:both"});
	selectItemLi2.append(clearDiv);
	
	return selectItemLi2;
};

SymbologyFormComponents.prototype.createFormRange = function(label, iden, defaultvalue, min, max, step, readOnly, selected, iter, definition) {
	var liClass = iden + " collection-item";
	if(selected){
		liClass = liClass +" selectedField"
	}
	var opcityItem = $("<li>", {class: liClass});
	var opcityItemDiv = $("<div>");
	var opacityRangeForm = $("<form>", {action: "#"});
	var opacityRangeP = $("<p>", {class: "range-field", text: " » " + gettext(label), style: "font-size: 12px; font-weight: 300; color: #9e9e9e;"});
	if(readOnly){
		var opacityRange = $("<input>", {type: "range", id: iden+"-"+iter, class: "opacity-range", disabled: "disabled"});
	}else{
		var opacityRange = $("<input>", {type: "range", id: iden+"-"+iter, class: "opacity-range"});
	}
	opacityRange.attr("min", min);
	opacityRange.attr("max", max);
	opacityRange.attr("step", step);
	opacityRange.attr("value", defaultvalue);
	opacityRangeP.append(opacityRange);
	opacityRangeForm.append(opacityRangeP);
	opcityItemDiv.append(opacityRangeForm);
	opcityItem.append(opcityItemDiv);

	return opcityItem;
};

SymbologyFormComponents.prototype.createFormTextInput = function(label, iden, defaultvalue, readOnly, selected, iter, definition) {
	return this.createFormInput(label, iden, "text", null, null, defaultvalue, readOnly, selected, iter, definition);
};
SymbologyFormComponents.prototype.createFormInput = function(label, iden, tp, min, max, defaultvalue, readOnly, selected, iter, definition) {
	var liClass = iden + " collection-item";
	if(selected){
		liClass = liClass +" selectedField"
	}
	var placeHolder = "";
	if(definition && definition["placeHolder"]){
		placeHolder = definition["placeHolder"]
	}
	
	var pointFormSizeLi = $("<li>", {class: liClass});
	if(tp == "number"){
		if(readOnly){
			var pointSizeButton = $("<input>", {id: iden+"-"+iter, class: "validate", type: tp, min: min, max: max, value: defaultvalue, disabled: "disabled", placeholder: placeHolder});
		}else{
			var pointSizeButton = $("<input>", {id: iden+"-"+iter, class: "validate", type: tp, min: min, max: max, value: defaultvalue, placeholder: placeHolder});
		}
	}else{
		if(readOnly){
			var pointSizeButton = $("<input>", {id: iden+"-"+iter, class: "validate", type: tp, value: defaultvalue, disabled: "disabled", placeholder: placeHolder});
		}else{
			var pointSizeButton = $("<input>", {id: iden+"-"+iter, class: "validate", type: tp, value: defaultvalue, placeholder: placeHolder});
		}
	}
	if(defaultvalue != "" && definition && definition["selectedOption"]){
		definition["selectedOption"] = true;
	}
	
	var pointFormSize = $("<label>", {text: " » " + gettext(label), for: iden+"-"+iter});
	pointFormSize.append(pointSizeButton);
	pointFormSizeLi.append(pointFormSize);

	return pointFormSizeLi;
};


SymbologyFormComponents.prototype.createFormInputArea = function(label, iden, defaultvalue, readOnly, filas, selected, iter, definition) {
	if(!filas){
		filas = "8";
	}
	var liClass = iden + " collection-item";
	if(selected){
		liClass = liClass +" selectedField"
	}
	var pointFormSizeLi = $("<li>", {class: liClass});
	var pointSizeButton = $("<textarea>", {id: iden+"-"+iter, class: "validate text-area", text: defaultvalue, rows: filas});
	if(readOnly){
		var pointSizeButton = $("<textarea>", {id: iden+"-"+iter, class: "validate text-area", text: defaultvalue, rows: filas, disabled: "disabled"});
	}else{
		var pointSizeButton = $("<textarea>", {id: iden+"-"+iter, class: "validate text-area", text: defaultvalue, rows: filas});
	}
	var pointFormSize = $("<label>", {text: " » " + gettext(label), for: iden+"-"+iter});
	pointFormSize.append(pointSizeButton);
	pointFormSizeLi.append(pointFormSize);

	return pointFormSizeLi;
};