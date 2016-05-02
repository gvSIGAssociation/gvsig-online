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

/**
 * TODO
 */

var SymbologyFilter = function(fields, parentData, rule, sldFilterValues) {	
	this.symbologyUtils = new SymbologyUtils();
	this.sldFilterValues = sldFilterValues;
	this.auxTranslations = [];
	this.parent = parentData;
	this.fields = fields;
	this.rule = rule;
	var that = this;
};

/**
 * TODO
 */
SymbologyFilter.prototype.initialize = function() {

};


/**
 * TODO
 */
SymbologyFilter.prototype.loadOperationsForKey = function(key){
	for(var operation in this.sldFilterValues[key]){
		if(!this.sldFilterValues[key][operation].hidden){
			var liOperation = $("<li>", {class: "li-operation", key: key, operation: operation});
			var spanNameOperation = $("<span>", {class: "operation-name", text: this.sldFilterValues[key][operation].name});
			var spanUsageOperation = $("<span>", {class: "operation-usage", text: this.sldFilterValues[key][operation].usage});
			var brOperation = $("<br>");
			liOperation.append(spanNameOperation);
			liOperation.append(brOperation);
			liOperation.append(spanUsageOperation);
			$("#ul-operations-list").append(liOperation);
		}
	}

} 
 
SymbologyFilter.prototype.loadOperations = function(key){
	$("#ul-operations-list").empty();
	$("#description-area").empty();
	var that = this;
	if(key == "All"){
		for(var key2 in this.sldFilterValues){
			this.loadOperationsForKey(key2);
		}
	}else{
		this.loadOperationsForKey(key);
	}
	
	
	$(".li-operation").unbind("click").click(function(){
		var key = $(this).attr("key");
		var operation = $(this).attr("operation");
		$(".li-operation").removeClass("selectedLi");
		$(this).addClass("selectedLi");
		$("#description-area").html(that.sldFilterValues[key][operation].description);
	});
	
	$(".li-operation").unbind("hover").hover(function(){
		$(this).addClass("hoverLi");
	},function(){
		$(this).removeClass("hoverLi");
	});
	
	$(".li-operation").unbind("dblclick").dblclick(function(){
		var key = $(this).attr("key");
		var operation = $(this).attr("operation");
		that.codemirror.replaceRange(
			that.sldFilterValues[key][operation].usage, 
			CodeMirror.Pos(that.codemirror.lastLine()));
	});
}
 


/**
 * TODO
 */
SymbologyFilter.prototype.show = function(data) {
		var symbologyFormComponents = new SymbologyFormComponents();
		var filter = data;
		if(data == null){
			filter = this.parent.currentData[this.rule].rule[0].fields.filter;
		}
		var fields = this.fields;
		var that = this;

		var content1 = $("<div>", {class: "input-field help-panel hidden col s12"});
		var content0a = $("<div>", {class: "col s7"});
		var content0aa = $("<span>", {class: "subtitle-modal", text: gettext("Operaciones")});
		content0a.append(content0aa);
		var content0b = $("<div>", {class: "col s5"});
		var content0bb = $("<span>", {class: "subtitle-modal", text: gettext("Campos de capa")});
		content0b.append(content0bb);
		var content1a = $("<div>", {class: "col s5"});
		var types = symbologyFormComponents.createSelectInput(
			"", 
			"functions-selector", 
			"All", 
			'{"All": "'+gettext("All")+'", "Logical": "'+gettext("Logicas")+'", "Comparative": "'+gettext("Comparativas")+'", "Arithmetics": "'+gettext("Aritmeticas")+'", "Functions": "'+gettext("Funciones")+'"}', 
			"Operaciones", false, false);
		var content1b = $("<div>", {class: "col s2", style: "height: 50px;"});
		
		var content1ab = $("<div>", {class: "description-div"});
		var descriptionDiv = $("<div>", {id: "description-area"});
		
		var operationDiv = $("<div>", {class: "operation-area"});
		var ulOperation = $("<ul>", {id: "ul-operations-list", class: ""});
		operationDiv.append(ulOperation);
		
		var fieldDiv = $("<div>", {class: "field-area col s5"});
		var ulFields = $("<ul>", {id: "ul-field-list", class: ""});
		fieldDiv.append(ulFields);
		
		for(var idx in fields){
			var field = fields[idx];
			var index = field.binding.lastIndexOf(".");
			if(index == -1){
				index = 0;
			}
			var type = field.binding.substring(index, field.binding.length); 
		
			var liField = $("<li>", {class: "li-field", field: field.name});
			var spanNameOperation = $("<span>", {class: "operation-name", text: field.name});
			var spanUsageOperation = $("<span>", {class: "operation-usage", text: type});
			var brOperation = $("<br>");
			liField.append(spanNameOperation);
			liField.append(brOperation);
			liField.append(spanUsageOperation);
			ulFields.append(liField);
		}
		
		
		
		
		
		content1a.append(types);
		
		content1a.append(operationDiv);
		content1a.append(content1ab);
		content1ab.append(descriptionDiv);
		content1.append(content0a);
		content1.append(content0b);
		content1.append(content1a);
		content1.append(content1b);
		content1.append(fieldDiv);
		
		var clearBoth = $("<div>", {style: "clear:both;"});
		content1.append(clearBoth);

		var content = $("<div>", {class: "col s12"});
		var contentTit = $("<div>", {class: "col s12"});
		var contentTit0 = $("<span>", {class: "subtitle-modal", text: gettext("Condiciones filtro")});
		var contentTit1 = $("<i>", {class: "right filter-help fa fa-question-circle"});
		contentTit.append(contentTit0);
		contentTit.append(contentTit1);
		content.append(contentTit);
		var sldEditor = $("<textarea>", {name: "sld-body", id: "sld-body2", rows:"10", text: filter});
		content.append(sldEditor);
		this.codemirror = null;
		
		if(data == null){
			var content3 = $("<div>", {class: "col s12", style:"margin-top: 15px;"});
			var content33 = $("<div>", {class: "col s12"});
			var contentTit3 = $("<span>", {class: "subtitle-modal col s12", text: gettext("Escala")});
			var content3a = $("<div>", {class: "col s6", style:"padding-right:5px;"});
			var content3b = $("<div>", {class: "col s6", style:"padding-left:5px;"});
			var legendMinScale = that.parent.currentData[that.rule].rule[0].fields.minscale;
			var legendMaxScale = that.parent.currentData[that.rule].rule[0].fields.maxscale;
			var minContainer = symbologyFormComponents.createFormInput(gettext("Escala minima"), "layer-minscale", "number", null, null, legendMinScale, false, false, 0);
			content3a.append(minContainer);
			
			var maxContainer = symbologyFormComponents.createFormInput(gettext("Escala maxima"), "layer-maxscale", "number", null, null, legendMaxScale, false, false, 0);
			content3b.append(maxContainer);
			content33.append(contentTit3);
			content3.append(content33);
			content3.append(content3a);
			content3.append(content3b);
		}
		
		var onReadyFunction = function(){
			var sldBody = document.getElementById('sld-body2');
			that.codemirror = CodeMirror.fromTextArea(sldBody, {
				value: "",
				mode:  "xml",
				theme: "xq-dark",
				autoMatchParens: true,
				height: "1000px",
				minHeight: 1000,
				lineNumbers: true
			});
			that.codemirror.setValue(filter);
		};

		var asignFunction = function(){
			if($('.filter-help').hasClass("hover")){
				$('.filter-help').removeClass("hover");
				$(".help-panel").slideUp();
			}
			if(that.codemirror){
				that.parent.updateFilterField(that.rule, that.codemirror.getValue(),  $("#layer-minscale-0").val(), $("#layer-maxscale-0").val());
			}
		};
		
		this.symbologyUtils.showModal(
			"sld-editor", 
			gettext("Editar filtro titulo"), 
			"", 
			asignFunction, 
			true,
			onReadyFunction);
		
		$("#sld-editor .modal-content").append(content);
		$("#sld-editor .modal-content").append(content1);
		$("#sld-editor .modal-content").append(content3);
		
		$('select').material_select();
		this.loadOperations("All");
		
		
		$('#functions-selector').change(function(){
			var value = $('#functions-selector').val();
			that.loadOperations(value);
		});
		
		$('.filter-help').click(function(){
			if(!$(this).hasClass("hover")){
				$(this).addClass("hover");
				$(".help-panel").slideDown();
			}else{
				$(this).removeClass("hover");
				$(".help-panel").slideUp();
			}
		});
		
		$(".li-field").unbind("dblclick").dblclick(function(){
			var field = $(this).attr("field");
			that.codemirror.replaceRange(
				field, 
				CodeMirror.Pos(that.codemirror.lastLine()));
		});
};
