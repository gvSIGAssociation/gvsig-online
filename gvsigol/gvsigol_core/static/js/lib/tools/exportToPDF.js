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
var exportToPDF = function(map) {

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
	
	var html = '';
	html += '<div class="row">';
	html += 	'<div class="col-xs-12 form-group">';
	html += 		'<label for="export-map-title">' + gettext('Map title') + '</label>';
	html += 		'<input placeholder="' + gettext('Map title') + '" name="export-map-title" id="export-map-title" type="text" class="form-control">';					
	html += 	'</div>';
	html += '</div>';
	
	$('#float-modal .modal-title').val("kk");
	
	$('#float-modal .modal-body').empty();
	$('#float-modal .modal-body').append(html);
	
	$("#float-modal").modal('show');
	
	var self = this;	
	$('#float-modal-accept').on('click', function () {
		var title = $('#export-map-title').val();
		
		window.map = self.map;
		window.title = title;
		window.open('/gvsigonline/core/export/');       
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