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
 
 
var ImportedSLD = function(workspace, layer, style, type, buttoncomp, panelcomp, fields, sldoperations, csrf_input) {
	this.workspace = workspace;
	this.layer = layer;
	this.layer_id = layer[0]["layer"][0].pk;
	this.style = style;
	this.type = type;
	this.legendId = "IM";
	this.currentData = null;
	this.fields = fields;
	
	this.symbologyUtils = new SymbologyUtils();
	this.formHelper = new SymbologyFormComponents();
	this.initializeButtonComponent(buttoncomp);
	
	this.previewMap = new  SymbologyPreviewMap(this.legendId, this.style);
	
	if(panelcomp != null){
		this.initializePanelComponent(panelcomp, csrf_input);
	}
};

ImportedSLD.prototype.initializeButtonComponent = function(component) {
	
	var ui = '';
	ui += '<li class="item">';
	ui += 		'<div class="product-icon text-primary">';
	ui += 			'<i class="fa fa-file-code-o"></i>';
	ui += 		'</div>';
	ui += 		'<div class="product-info">';
	ui += 			'<a id="' + this.getID() + '" href="#!" id="option1" class="product-title legend-button option-selection">';
	ui += 				gettext("SLD legend");							
	ui += 			'</a>';
	ui += 			'<span class="product-description">' + gettext("SLD legend description") + '</span>';
	ui += 		'</div>';
	ui += '</li>';
	$("#"+component).append(ui);
};

/**
 * Initialize component method
 */
ImportedSLD.prototype.initializePanelComponent = function(component, csrf_input) {
	var panel = $("<div>", {id: this.getID() + "-panel", class:"step-2"});
	var preview = $("<div>", {class:"map-preview col s6", style:"float:left;"});
	var mapImage = this.previewMap.createMap();
	preview.append(mapImage);
	
	var mainPanel = $("<div>", {class:"legend-main-panel"});
	var maintitle = $("<div>", {class:"legend-main-title", text:"Panel de símbolo único"});
	
	var titleDiv = $("<div>", {class:"legend-div-title"});
	var star = $("<i>", {class:"fa fa-star default-legend-element"});
	var title = $("<span>", {class:"legend-title", text: gettext("SLD leyenda")});
	titleDiv.append(title);
	titleDiv.append(star);
	mainPanel.append(titleDiv);
	var form = $("<form>", {id: this.getID() + "-form", role:"form", class:"col s12", method:"post", action:"/gvsigonline/style_update/"});
	
	var csrf = $.parseHTML( csrf_input )
	form.append(csrf);
	
	var realLayerInputDiv = $("<input>", {type:"hidden", value:""+this.layer_id, name:"layer_id", id:"layer_id"});	
	var realStyleInputDiv = $("<input>", {type:"hidden", value:""+this.style, name:"style_id", id:"style_id"});	
	var realNameInputDiv = $("<input>", {type:"hidden", value:"", name:"style_name", id:"style_name"});	
	var realSLDInputDiv = $("<input>", {type:"hidden", value:"", name:"style_sld", id:"style_sld"});	
	var nameinput = this.formHelper.createFormTextInput('Style name', "style_name2", "", true, false);
	var nameDivinput = $("<div>", {class:"hidden"});		
	nameDivinput.append(nameinput);
	
	var sldDiv = $("<div>", {class:"sld-editor row"});			
	var sldLabel = $("<div>", {class:"input-field col s12", text: gettext("SLD body")});					
	var sldBody = $("<div>", {class:"input-field col s12"});	
	
	var sldBodyEditor = $("<textarea>", {name:"sld-body", id: "sld-body", rows: 30});	
	sldBody.append(sldBodyEditor);		
	sldDiv.append(sldLabel);	
	sldDiv.append(sldBody);
	
	
	var sldFileDiv = $("<div>", {class:"file-selector row"});			
	var sldFileFieldDiv = $("<div>", {class:"file-field input-field"});		
	var sldFileBtnDiv = $("<div>", {class:"btn"});		
	var sldFileBtnLabelDiv = $("<span>", {text: gettext("Select SLD")});
	var sldFileBtnInputDiv = $("<input>", {type:"file", name:"sld", id:"sld-file"});
	sldFileBtnDiv.append(sldFileBtnLabelDiv);
	sldFileBtnDiv.append(sldFileBtnInputDiv);
	
	var sldFile2Div = $("<div>", {class:"file-path-wrapper"});
	var sldFile2InputDiv = $("<input>", {type:"text", class:"file-path validate"});		
	sldFile2Div.append(sldFile2InputDiv);	
				      	
	sldFileFieldDiv.append(sldFileBtnDiv);
	sldFileFieldDiv.append(sldFile2Div);
	
	sldFileDiv.append(sldFileFieldDiv);
	form.append(realNameInputDiv);
	form.append(realLayerInputDiv);
	form.append(realStyleInputDiv);
	form.append(realSLDInputDiv);
	
	form.append(nameDivinput);	
	form.append(sldFileDiv);	
	//form.append(sldDiv);	

		
	var separator = $("<div>", {class: "clearBoth"});
	mainPanel.append(form);
	
	
	panel.append(preview);
	panel.append(mainPanel);
	panel.append(separator);
	panel.append(sldDiv);

	$("#"+component).append(panel);
	
	var that = this;
	$('#sld-file').on("change", function(){ 
		that.loadPreview(); 
	});
};

ImportedSLD.prototype.getID = function() {
	return this.legendId;
};

/**
 * Load Data
 */
ImportedSLD.prototype.loadData = function(data) {
	this.currentData = data;
	if(data.sld_code == ""){
		$("form").attr("action", "/gvsigonline/style_upload/");
		$("form").attr("enctype", "multipart/form-data");
		$("#style_name").attr("value", data.name);
		$("#style_name2").attr("value", data.name);
		$("#style_name").attr("name", "style_name");
		$(".sld-editor").hide();
		
	}else{
		//$(".file-selector").hide();
		$(".sld-editor").show();
		$("form").attr("action", "/gvsigonline/style_update/"+data.name+"/");
		$("#style_name").val(data.name);
		$("#style_name2").val(data.name);
		
		if(this.codemirror == null){
			var sldBody = document.getElementById('sld-body');
			this.codemirror = CodeMirror.fromTextArea(sldBody, {
				value: data.sld_code,
				mode:  "xml",
				theme: "xq-dark",
				autoMatchParens: true,
				height: "1000px",
				minHeight: 1000,
				lineNumbers: true
			});
		}
		this.codemirror.setValue(data.sld_code);
	}
	this.previewMap.updateSLDLayer(data.sld_code);
};

ImportedSLD.prototype.loadPreviewMap = function(workspace, layer, username, password) {	
	this.previewMap.loadMap(workspace, layer, username, password);
};

ImportedSLD.prototype.submit = function() {
	var sldCode = this.codemirror.getValue();
	$("#style_sld").val(sldCode);
	$("#"+this.getID() + "-form").submit();
}

ImportedSLD.prototype.loadPreview = function() {
	var that = this;
	var file = document.getElementById("sld-file").files[0];
	if (file) {
	    var reader = new FileReader();
	    reader.readAsText(file, "UTF-8");
	    reader.onload = function (evt) {
	    	that.currentData['sld_code'] = evt.target.result;
	    	that.loadData(that.currentData);
	    }
	    reader.onerror = function (evt) {
	    	that.currentData['sld_code'] = "error reading file";
	    	that.loadData(that.currentData);
	    }
	}
};

/**
 * Get Data
 */
ImportedSLD.prototype.getData = function() {
	return this.currentData;
};
