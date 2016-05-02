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
 
 
var ImportedRMF = function(workspace, layer, style, type, buttoncomp, panelcomp, fields, sldoperations, csrf_input) {
	this.workspace = workspace;
	this.layer = layer;
	this.layer_id = layer[0]["layer"][0].pk;
	this.style = style;
	this.type = type;
	this.legendId = "IR";
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

ImportedRMF.prototype.initializeButtonComponent = function(component) {
var container = $("<li>", {class:"collection-item avatar"});
	
	var icon = $("<i>", {class:"material-icons circle fa fa-file-text"});
	var title = $("<span>", {text: gettext("RMF leyenda"), class:"title"});
    var desc = $("<p>", {html: gettext("RMF leyenda descripcion")});

	var aLink  = $("<a>", {id: this.getID(), href: "#!", class: "secondary-content legend-button"});
	var iLink  = $("<i>", {class: "go-icon fa fa-chevron-right"});
	aLink.append(iLink);

	container.append(icon);
	container.append(title);
	container.append(desc);
	container.append(aLink);
	
	$("#"+component).append(container);
};

/**
 * Initialize component method
 */
ImportedRMF.prototype.initializePanelComponent = function(component, csrf_input) {
	var panel = $("<div>", {id: this.getID() + "-panel", class:"step-2"});
	var preview = $("<div>", {class:"map-preview col s6", style:"float:left;"});
	var mapImage = this.previewMap.createMap();
	preview.append(mapImage);
	
	var mainPanel = $("<div>", {class:"legend-main-panel"});
	var maintitle = $("<div>", {class:"legend-main-title", text:"Panel de símbolo único"});
	
	var titleDiv = $("<div>", {class:"legend-div-title"});
	var star = $("<i>", {class:"fa fa-star default-legend-element"});
	var title = $("<span>", {class:"legend-title", text: gettext("RMF leyenda")});
	titleDiv.append(title);
	titleDiv.append(star);
	mainPanel.append(titleDiv);
	var form = $("<form>", {id: this.getID() + "-form",role:"form", class:"col s12", method:"post", action:"/gvsigonline/style_update/"});
	
	var csrf = $.parseHTML( csrf_input )
	form.append(csrf);
	
	var realLayerInputDiv = $("<input>", {type:"hidden", value:""+this.layer_id, name:"layer_id", id:"layer_id"});	
	var realStyleInputDiv = $("<input>", {type:"hidden", value:""+this.style, name:"style_id", id:"style_id"});	
	var realNameInputDiv = $("<input>", {type:"hidden", value:"", name:"style_name", id:"style_name"});	
	var realSLDInputDiv = $("<input>", {type:"hidden", value:"", name:"style_sld", id:"style_rmf_sld"});	
	var nameinput = this.formHelper.createFormTextInput('Style name', "style_name2", "", true, false);
	var nameDivinput = $("<div>", {class:"hidden"});		
	nameDivinput.append(nameinput);
	
	var sldDiv = $("<div>", {class:"rmf-editor row"});			
	var sldLabel = $("<div>", {class:"input-field col s12", text: gettext("SLD body")});					
	var sldBody = $("<div>", {class:"input-field col s12"});	
	
	var sldBodyEditor = $("<textarea>", {name:"rmf-body", id: "rmf-body", rows: 30});	
	sldBody.append(sldBodyEditor);		
	sldDiv.append(sldLabel);	
	sldDiv.append(sldBody);
	
	
	var sldFileDiv = $("<div>", {class:"file-selector row"});			
	var sldFileFieldDiv = $("<div>", {class:"file-field input-field"});		
	var sldFileBtnDiv = $("<div>", {class:"btn"});		
	var sldFileBtnLabelDiv = $("<span>", {text: gettext("Select SLD")});
	var sldFileBtnInputDiv = $("<input>", {type:"file", name:"rmf", id:"rmf-file"});
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
	$('#rmf-file').on("change", function(){ 
		that.loadPreview(); 
	});
};

ImportedRMF.prototype.getID = function() {
	return this.legendId;
};

/**
 * Load Data
 */
ImportedRMF.prototype.loadData = function(data) {
	this.currentData = data;
	if(data.sld_code == ""){
		$("form").attr("action", "/gvsigonline/style_upload/");
		$("form").attr("enctype", "multipart/form-data");
		$("#style_name").attr("value", data.name);
		$("#style_name2").attr("value", data.name);
		$("#style_name").attr("name", "style_name");
		$(".rmf-editor").hide();
		
	}else{
		//$(".file-selector").hide();
		$(".rmf-editor").show();
		$("form").attr("action", "/gvsigonline/style_update/"+data.name+"/");
		$("#style_name").val(data.name);
		$("#style_name2").val(data.name);
		
		if(this.codemirror == null){
			var sldBody = document.getElementById('rmf-body');
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

ImportedRMF.prototype.loadPreviewMap = function(workspace, layer, username, password) {	
	this.previewMap.loadMap(workspace, layer, username, password);
};

ImportedRMF.prototype.submit = function() {
	var sldCode = this.codemirror.getValue();
	$("#style_rmf_sld").val(sldCode);
	$("#"+this.getID() + "-form").submit();
}

ImportedRMF.prototype.loadPreview = function() {
	var that = this;
	var file = document.getElementById("rmf-file").files[0];
	if (file) {
	    var reader = new FileReader();
	    reader.readAsText(file, "UTF-8");
	    reader.onload = function (evt) {
		   	ajaxPost("/gvsigonline/load_rmf/", {data: evt.target.result}, function(data){
	            if (data.success) {
	            	if(that.codemirror){
		    			that.codemirror.setValue('');
		    		}
		    		var sld = '';
		    		sld += '<?xml version="1.0" encoding="ISO-8859-1"?> \n';
		    		sld += '<StyledLayerDescriptor version="1.0.0" \n';
		    		sld += 	'\t xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd" \n';
		    		sld += 	'\t xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" \n';
		    		sld += 	'\t xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"> \n';
		    		
		    		sld += '\t <NamedLayer> \n';
		    		sld += '\t\t <Name>raster</Name> \n';
		    		sld += '\t\t <UserStyle> \n';
		    		sld += '\t\t\t <Name>raster</Name> \n';
					sld += '\t\t\t <Title>raster</Title> \n';
					sld += '\t\t\t <Abstact>raster</Abstact> \n';
					sld += '\t\t\t <FeatureTypeStyle> \n';
					sld += '\t\t\t\t <Rule> \n';			
					sld += '\t\t\t\t\t <RasterSymbolizer> \n';
					sld += '\t\t\t\t\t\t <Opacity>1.0</Opacity> \n';
					sld += '\t\t\t\t\t\t <ColorMap> \n';
					for (var i=0; i<data.color_map.length; i++) {
						sld += '\t\t\t\t\t\t\t <ColorMapEntry color="' + data.color_map[i].color + '" quantity="' + data.color_map[i].quantity + '" label="' + data.color_map[i].label + '" opacity="' + data.color_map[i].opacity + '"/> \n';
					}
					sld += '\t\t\t\t\t\t </ColorMap> \n';
					sld += '\t\t\t\t\t </RasterSymbolizer> \n';			
					sld += '\t\t\t\t </Rule> \n';
					sld += '\t\t\t </FeatureTypeStyle> \n';
					sld += '\t\t </UserStyle> \n';
					sld += '\t </NamedLayer> \n';
					sld += '</StyledLayerDescriptor>';
					
					that.currentData['sld_code'] = sld;
					that.loadData(that.currentData);
					
	    		} else {
	    			alert(gettext('Invalid format'));
	    		}
	        })
		    	
		    	
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
ImportedRMF.prototype.getData = function() {
	return this.currentData;
};
