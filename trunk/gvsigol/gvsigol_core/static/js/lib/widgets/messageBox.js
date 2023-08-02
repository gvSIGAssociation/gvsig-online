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
var messageBox = function() {};

messageBox.prototype.createModal = function() {
	if ($('#modal-error').length == 0) {
		var ui = '';
		ui += '<div class="modal fade" id="modal-error" tabindex="-1" role="dialog" aria-labelledby="myModalLabel" style="display:none">';
		ui += 	'<div class="modal-dialog" role="document">';
		ui += 		'<div class="modal-content">';
		ui += 			'<div class="modal-body" style="padding: 0px !important;">';
		ui += 				'<div class="alert alert-dismissible" style="border-radius: 0px !important;">';
		ui += 					'<button type="button" class="close" data-dismiss="modal" aria-hidden="true">×</button>';
		ui += 					'<h4 class="messageBoxTitle"></h4>';
		ui += 					'<div class="messageBoxMsg"></div>';
		ui += 				'</div>';
		ui += 			'</div>';
		ui += 		'</div>';
		ui += 	'</div>';
		ui += '</div>';
		$('body').append(ui);
	}
}


/**
 * TODO.
 */
messageBox.prototype.show = function(type, msg) {
	this.createModal();
	var title = '';
	var style = '';
	var icon = '';
	
	if (type == 'info') {
		title = 'Info';
		style = 'alert-info';
		icon = 'fa-info';
		
	} else if (type == 'success') {
		title = gettext('Success');
		style = 'alert-success';
		icon = 'fa-check';
		
	} else if (type == 'warning') {
		title = gettext('Warning');
		style = 'alert-warning';
		icon = 'fa-warning';
		
	} else if (type == 'error') {
		title = 'Error';
		style = 'alert-danger';
		icon = 'fa-ban';
	}

	$('#modal-error .modal-body .alert').removeClass("alert-info alert-warning alert-danger alert-success").addClass(style);
	$('#modal-error h4.messageBoxTitle').html('<i class="icon fa ' + icon + '"></i> ' + title + '</h4>');
	$('#modal-error div.messageBoxMsg').text(msg);
	$('#modal-error').modal('show');
};


/**
 * TODO.
 */
messageBox.prototype.showMultiLine = function(type, messages) {
	this.createModal();
	var title = '';
	var style = '';
	var icon = '';
	
	if (type == 'info') {
		title = 'Info';
		style = 'alert-info';
		icon = 'fa-info';
		
	} else if (type == 'success') {
		title = gettext('Success');
		style = 'alert-success';
		icon = 'fa-check';
		
	} else if (type == 'warning') {
		title = gettext('Warning');
		style = 'alert-warning';
		icon = 'fa-warning';
		
	} else if (type == 'error') {
		title = 'Error';
		style = 'alert-danger';
		icon = 'fa-ban';
	}
	
	$('#modal-error .modal-body .alert').removeClass("alert-info alert-warning alert-danger alert-success").addClass(style);
	$('#modal-error h4.messageBoxTitle').html('<i class="icon fa ' + icon + '"></i> ' + title + '</h4>');
	var list = '';
	var ul = $('<ul></ul>');
	for (var i=0; i<messages.length; i++) {
		var li = $('<li style="list-style-type: none;"></li>');
		li.text(messages[i]);
		ul.append(li);
	}
	$('#modal-error div.messageBoxMsg').empty();
	$('#modal-error div.messageBoxMsg').append(ul);
	$('#modal-error').modal('show');
};
