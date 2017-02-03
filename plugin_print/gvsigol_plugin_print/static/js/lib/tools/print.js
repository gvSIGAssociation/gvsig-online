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
 * @author: Javier Rodrigo <jrodrigo@scolab.es>
 */

/**
 * TODO
 */
var print = function(conf, map) {

	this.conf = conf;
	this.map = map;
	
	this.id = "print";
	
	this.$button = $("#print");

	var this_ = this;
  
	var handler = function(e) {
		this_.handler(e);
	};

	this.$button.on('click', handler);
	this.$button.on('touchstart', handler);

};

/**
 * TODO
 */
print.prototype.active = false;

/**
 * TODO
 */
print.prototype.deactivable = true;

/**
 * @param {Event} e Browser event.
 */
print.prototype.handler = function(e) {
	e.preventDefault();
	var self = this;
	
	var templates = this.getTemplates();
	
	var ui = '';
	ui += '<div id="field-errors" class="row">';
	ui += '</div>';
	ui += '<div class="row">';
	ui += 	'<div class="col-md-12 form-group">';
	ui += 		'<label>' + gettext('Select print template') + '</label>';
	ui += 		'<select id="print-template" class="form-control">';
	ui += 			'<option disabled selected value> -- ' + gettext('Select template') + ' -- </option>';
	for (var i=0; i<templates.length; i++) {
		ui += 		'<option value="' + templates[i] + '">' + templates[i] + '</option>';
	}
	ui += 		'</select>';
	ui += 	'</div>';
	ui += '</div>';
	ui += '<div id="capabilities-form" class="row">';
	ui += '</div>';
	
	$('#float-modal .modal-body').empty();
	$('#float-modal .modal-body').append(ui);
	
	var buttons = '';
	buttons += '<button id="float-modal-cancel-print" type="button" class="btn btn-default" data-dismiss="modal">' + gettext('Cancel') + '</button>';
	buttons += '<button id="float-modal-accept-print" type="button" class="btn btn-default">' + gettext('Print') + '</button>';
	
	$('#float-modal .modal-footer').empty();
	$('#float-modal .modal-footer').append(buttons);
	
	$("#float-modal").modal('show');
	
	$('#print-template').on('change', function(e) {
		var template = $('#print-template').val();
		
		var capabilities = self.getCapabilities(template);
		
		var form = '';
		form += '<div class="col-md-12 form-group">';
		/*form += 	'<label>' + gettext('Select enumeration') + '</label>';
		form += 	'<select id="field-name-'+id+'" class="form-control">';
				'{% for enum in enumerations %}'
		form += 	'<option value="{{enum.name}}">{{enum.title}}</option>';
				'{% endfor%}'
		form += 	'</select>';*/
		form += '</div>';
		
		$('#capabilities-form').empty();
		$('#capabilities-form').append(form);
	});
	
	$('#float-modal-accept-print').on('click', function () {
		console.log('print');
		$('#float-modal').modal('hide');
	});
};

/**
 * TODO
 */
print.prototype.getTemplates = function() {
	var templates = null;
	$.ajax({
		type: 'GET',
		async: false,
	  	url: 'https://localhost/print/print/apps.json',
	  	success	:function(response){
	  		templates = response;
	  	},
	  	error: function(){}
	});
	return templates;
};

/**
 * TODO
 */
print.prototype.getCapabilities = function(template) {
	var capabilities = null;
	$.ajax({
		type: 'GET',
		async: false,
	  	url: 'https://localhost/print/print/' + template + '/capabilities.json',
	  	success	:function(response){
	  		capabilities = response;
	  	},
	  	error: function(){}
	});
	return capabilities;
};

/**
 * TODO
 */
print.prototype.deactivate = function() {			
	this.$button.removeClass('button-active');
	this.active = false;
};