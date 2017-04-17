/**
 * gvSIG Online.
 * Copyright (C) 2010-2017 SCOLAB.
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
var exportToPDF = function(conf, map) {

	this.conf = conf;
	this.map = map;
	
	this.id = "export-to-pdf";
	
	this.$button = $("#export-to-pdf");

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
exportToPDF.prototype.active = false;

/**
 * TODO
 */
exportToPDF.prototype.deactivable = true;

/**
 * @param {Event} e Browser event.
 */
exportToPDF.prototype.handler = function(e) {
	e.preventDefault();
	
	var body = '';
	body += '<div class="row">';
	body += 	'<div class="col-md-12 form-group">';
	body += 		'<label for="export-map-title">' + gettext('Map title') + '</label>';
	body += 		'<input placeholder="' + gettext('Map title') + '" name="export-map-title" id="export-map-title" type="text" class="form-control">';					
	body += 	'</div>';
	body += '</div>';
	
	$('#float-modal .modal-body').empty();
	$('#float-modal .modal-body').append(body);
	
	var buttons = '';
	buttons += '<button id="float-modal-cancel-print" type="button" class="btn btn-default" data-dismiss="modal">' + gettext('Cancel') + '</button>';
	buttons += '<button id="float-modal-accept-print" type="button" class="btn btn-default">' + gettext('Print') + '</button>';
	
	$('#float-modal .modal-footer').empty();
	$('#float-modal .modal-footer').append(buttons);
	
	$("#float-modal").modal('show');
	
	var self = this;	
	$('#float-modal-accept-print').on('click', function () {
		var title = $('#export-map-title').val();
		
		window.map = self.map;
		window.title = title;
		window.open('/gvsigonline/core/export/' + self.conf.pid + '/');       
		window.focus();
		
		$('#float-modal').modal('hide');
	});
};

/**
 * TODO
 */
exportToPDF.prototype.deactivate = function() {			
	this.$button.removeClass('button-active');
	this.active = false;
};