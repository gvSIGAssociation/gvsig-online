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

/**
 * TODO.
 */
messageBox.prototype.show = function(type, msg) {
	
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
	
	// remove any previous content
	$('#modal-error').remove();
	
	var ui = '';
	ui += '<div class="modal fade" id="modal-error" tabindex="-1" role="dialog" aria-labelledby="myModalLabel">';
	ui += 	'<div class="modal-dialog" role="document">';
	ui += 		'<div class="modal-content">';
	ui += 			'<div class="modal-body" style="padding: 0px !important;">';
	ui += 				'<div class="alert ' + style + ' alert-dismissible" style="border-radius: 0px !important;">';
	ui += 					'<button type="button" class="close" data-dismiss="modal" aria-hidden="true">×</button>';
	ui += 					'<h4><i class="icon fa ' + icon + '"></i> ' + title + '</h4>';
	ui += 					msg;
	ui += 				'</div>';
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	$('body').append(ui);
	$('#modal-error').modal('show');
};

/**
 * TODO.
 */
messageBox.prototype.showMultiLine = function(type, messages) {
	
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
	
	// remove any previous content
	$('#modal-error').remove();
	
	var ui = '';
	ui += '<div class="modal fade" id="modal-error" tabindex="-1" role="dialog" aria-labelledby="myModalLabel">';
	ui += 	'<div class="modal-dialog" role="document">';
	ui += 		'<div class="modal-content">';
	ui += 			'<div class="modal-body" style="padding: 0px !important;">';
	ui += 				'<div class="alert ' + style + ' alert-dismissible" style="border-radius: 0px !important;">';
	ui += 					'<button type="button" class="close" data-dismiss="modal" aria-hidden="true">×</button>';
	ui += 					'<h4><i class="icon fa ' + icon + '"></i> ' + title + '</h4>';
	ui +=					'<ul>'
	for (var i=0; i<messages.length; i++) {
		ui +=					'<li style="list-style-type: none;">' + messages[i] + '</li>';
	}
	ui +=					'</ul>'
	ui += 				'</div>';
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	$('body').append(ui);
	$('#modal-error').modal('show');
};