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
var symbologyUtils = null;
var type = null;
var currentSymbol = null;
var originalSymbol = null;
var symbolForm = null;


var SymbologyLibraryForm = function(symbolForm) {	
	this.formHelper = new SymbologyFormComponents();
	this.symbologyUtils = new SymbologyUtils(this);
	this.symbolForm = symbolForm;
	this.dataloaded = false;
};

SymbologyLibraryForm.prototype.formFunctionality = function() {
	var that = this;
	$(".library-link-preview").unbind("dblclick").dblclick(function(){
		var sym_id = $(this).attr("Symbol");
		var sldjson = $.xml2json("<StoredSLD>" +
				 that.data[sym_id].fields.sld_code + "</StoredSLD>");
		that.currentSymbol = sldjson[that.symbolForm.type];
		that.updatePreviewFunction("symbol-preview");
		
		var sForm = that.symbolForm.makeSymbolForm(that.currentSymbol, that.symbolForm.type, false);
		$("#symbol-editor").empty();
		$("#symbol-editor").append(sForm);
		$("#formLibraryButton").trigger("click");
		that.symbolForm.formFunctionality();
		that.symbolForm.updatePreviewFunction("symbol-preview");
	});
	
	
	$(".library-link-preview").unbind("click").click(function(){
		$(".library-link-preview").removeClass("symbol-selected");
		$(this).addClass("symbol-selected");
		
		var sym_id = $(this).attr("Symbol");
		var sldjson = $.xml2json("<StoredSLD>" +
				that.data[sym_id].fields.sld_code + "</StoredSLD>");
		that.currentSymbol = sldjson[that.symbolForm.type];
		that.updatePreviewFunction("symbol-preview");
		
		var sForm = that.symbolForm.makeSymbolForm(that.currentSymbol, that.symbolForm.type, false);
		$("#symbol-editor").empty();
		$("#symbol-editor").append(sForm);
		that.symbolForm.formFunctionality();
		that.symbolForm.updatePreviewFunction("symbol-preview");
	});
	$("#library-chooser .tab-container .library-link-preview").unbind("dblclick");
	$("#library-chooser .tab-container .library-link-preview").unbind("click");
	
	$("#library-chooser .tab-container .library-link-preview").unbind("click").click(function(){
		$("#formLibraryButton").trigger("click");
	})
	
	$(".add-library-button").unbind("click").click(function(){
			var symbol = that.currentSymbol;
			var i = $(".library-link-preview.library-edition.library-popup").length;
			if(symbol != null){
				var li1 = $("<li>", {class:"library-link-preview library-edition library-popup", symbol: i});
				var div1 = $("<div>", {class: "symbol-text-container"});
				var symbolPreview = $("<div>", {
					id:"symbol-preview-"+i, 
					class: "library-preview",
					symbol: i});
				var symbolPreviewName = $("<span>", {
					id: "symbol-name-"+i, 
					text: $("#form-symbol-name").val(), 
					symbol: i});
				var symbolPreviewDescription = $("<p>", {
					id: "symbol-description-"+i, 
					text: "", 
					symbol: i});
					
				li1.append(symbolPreview);
				div1.append(symbolPreviewName);
				div1.append(symbolPreviewDescription);	
							
				li1.append(div1);
				$(".library-symbols").append(li1);
				
				that.updatePreviewFunction("symbol-preview-"+i);
				//that.formFunctionality();
				
				var type = that.symbolForm.type;
				var result =  that.currentSymbol;
				
				var xmljson = "";
				for(var i=0; i<result.length; i++){
					xmljson += that.symbologyUtils.json2xml(result[i], type);
				}
				xmljson = xmljson.replace(/<CssParameter[^>]*><\/CssParameter>/g, "");
				
				ajaxPost("/gvsigonline/symbol_library_add/"+$("#library-field-input-0").val()+"/", {
						'title': $("#form-symbol-name").val(),
						'sld-code': xmljson,
						'type': type
					}, 
					function(content){
			            var field = $("#library-field-input-0").val();
						that.loadLibraryFunction(field);
			        }
			   );
				
				
			}
	});
};


SymbologyLibraryForm.prototype.setData = function(symbol) {
	if(symbol){
		this.currentSymbol = symbol;
	}
	this.updatePreviewFunction("symbol-preview");
};


SymbologyLibraryForm.prototype.getData = function() {
	return this.currentSymbol;
};

SymbologyLibraryForm.prototype.updatePreviewFunction = function(id){
	var symbologyPreview = new SymbologyPreview(null);
	$("#"+id).empty();
	var symbolPreview = symbologyPreview.renderPreview(
		this.currentSymbol, 
		this.symbolForm.type, 
		id);
	if(symbolPreview != null){
		$("#"+id).append(symbolPreview);
	}
};


SymbologyLibraryForm.prototype.refreshLibraryFunction = function() {
	this.dataloaded = false;
	this.loadLibraryFunction();
}

SymbologyLibraryForm.prototype.loadLibraries = function() {
	
	var that = this;
	if(!this.dataloaded){
		this.dataloaded = true;
		$.get("/gvsigonline/get_libraries/", 
			{"type": that.symbolForm.type},  
			function( response ) {
				data = response.content;
				var divContentForm = $("#library-chooser .tab-content-container.main-container");
				var divContentInput = that.formHelper.createSelectInput(gettext("Library"), "library-field-input", "", data, gettext("Selecciona biblioteca de símbolos"), false, false, 0);
				var symbolContentForm = $("<div>", {class:"symbol-content-container symbol-container"});
				divContentForm.empty();
				divContentForm.append(divContentInput);
				divContentForm.append(symbolContentForm);
				
				
				divContentInput.unbind("change").change(function() {
					var field = $("#library-field-input-0").val();
					that.loadLibraryFunction(field);
					$(".add-library-button").show();
				});
				
				 $('select').material_select();
		});
	}
}

SymbologyLibraryForm.prototype.loadLibraryFunction = function(library_id) {
	var that = this;
	this.data = [];
	$.get("/gvsigonline/get_library_symbols/"+library_id+"/", function( response ) {
		that.data = response.content;
		var container = $("#library-chooser .tab-content-container.main-container .symbol-content-container.symbol-container");
		var ul = $("<ul>", {class: "library-symbols"});
		
		for(var i=0; i<that.data.length; i++){
			if(that.data[i].fields.type == that.symbolForm.type){
				var symbol = that.data[i];		
				var li1 = $("<li>", {class:"library-link-preview library-edition library-popup", symbol: i});
				var div1 = $("<div>", {class: "symbol-text-container"});
				var symbolPreview = $("<div>", {
					id:"symbol-preview-"+i, 
					class: "library-preview",
					symbol: i});
				var symbolPreviewName = $("<span>", {
					id: "symbol-name-"+i, 
					text: that.data[i].fields.name, 
					symbol: i});
				var symbolPreviewDescription = $("<p>", {
					id: "symbol-description-"+i, 
					text: that.data[i].fields.description, 
					symbol: i});
					
				li1.append(symbolPreview);
				div1.append(symbolPreviewName);
				div1.append(symbolPreviewDescription);	
							
				li1.append(div1);
				ul.append(li1);
			}
		}
		container.empty();
		container.append(ul);
		var clearB = $("<div>", {class: "clearBoth"});
		container.append(clearB);
	}).done(function() {
    	that.loadPreviews(that.data);
    	that.dataloaded = true;
  	});
	
};

SymbologyLibraryForm.prototype.loadPreviews = function(previews) {
	for(var i=0; i<previews.length; i++){
		if(previews[i].fields.type == this.symbolForm.type){
			var symbologyPreview = new SymbologyPreview(null);
			var sldjson = $.xml2json("<StoredSLD>" +
						previews[i].fields.sld_code + "</StoredSLD>");
				
			var symbolPreview = symbologyPreview.renderPreview(
					sldjson[previews[i].fields.type], 
					previews[i].fields.type, 
					"symbol-preview-"+i);
			if(symbolPreview != null){
				$("#symbol-preview-"+i).append(symbolPreview);
			}
		}
	}
	
	this.formFunctionality(previews);

};

SymbologyLibraryForm.prototype.makeLibraryForm = function(data, type, readOnly) {
	var divForm = $("<div>");
	var divTabForm = $("<ul>", {class:"tab-container side-nav"});
	var divContentForm = $("<div>", {class:"tab-content-container main-container"});
	var divContentInput = this.formHelper.createSelectInput(gettext("Library"), "library-field-input", "", "{}", gettext("Selecciona biblioteca de símbolos"), false, false, 0);
	var symbolContentForm = $("<div>", {class:"symbol-content-container symbol-container"});
	divContentForm.append(divContentInput);
	divContentForm.append(symbolContentForm);
	
	var featureType = SLDDefaultValues[type];
	this.currentSymbol = data;
	this.originalSymbol = data;
	
	var li1 = $("<li>", {class:"library-link-preview"});
	var spp = $("<span>", {class:"library-link-preview-label", text: gettext("Símbolo actual:")});
	var symbolPreview = $("<div>", {
		id:"symbol-preview", 
		class: "library-preview"});
	li1.append(spp);
	li1.append(symbolPreview);
	var addCurrentDiv = $("<div>", {class:"add-library-button", style:"display:none;"});
	var addCurrentI = $("<i>", {style: "float:right; margin-top: 5px;", class:"fa fa-chevron-right"});
	var addCurrentSpan = $("<span>", { style: "margin-right: 5px;", text: "    "+gettext("Añadir a biblioteca")});
	addCurrentDiv.append(addCurrentSpan);
	addCurrentDiv.append(addCurrentI);
	
		
	var li2 = $("<li>");
	var alink = $("<a>", {href: "#", class:"library-link"});
	var spanlink = $("<span>", {class:"library-link-span", text: "Añadir"});
	var ilink = $("<i>", {class:"fa fa-chevron-right right dash-secondary-icon"});
	alink.append(spanlink);
	alink.append(ilink);
	li2.append(alink);
	
	var li3 = $("<li>");
	var alink3 = $("<a>", {href: "#", class:"library-link"});
	var spanlink3 = $("<span>", {class:"library-link-span", text: "Importar"});
	var ilink3 = $("<i>", {class:"fa fa-users right dash-secondary-icon"});
	alink3.append(spanlink3);
	alink3.append(ilink3);
	li3.append(alink3);
	
	
	divTabForm.append(li1);
	divTabForm.append(addCurrentDiv);
	//divTabForm.append(li2);
	//divTabForm.append(li3);
	
	divForm.append(divTabForm);
	divForm.append(divContentForm);

	return divForm;
};
