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
 * Estilos del modal de mensajes. Se inyectan una sola vez para no depender de
 * cada plantilla que carga este script (base, viewer, symbology, *_compress...).
 * Hay que sobrescribir con !important los colores de AdminLTE (.alert-success...).
 */
messageBox.prototype.injectStyles = function() {
	if ($('#messagebox-styles').length > 0) {
		return;
	}
	var css = '';
	css += '#modal-error .modal-dialog { max-width: 480px; width: auto; margin: 15vh auto 0; padding: 0 16px; }';
	css += '#modal-error .modal-content { border: none; border-radius: 8px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,.25); }';
	css += '#modal-error .modal-body .alert { --mb-accent: #285A8C; --mb-soft: #eaf0f7; margin: 0 !important; border: none !important; border-left: 5px solid var(--mb-accent) !important; border-radius: 0 !important; background: #fff !important; color: #444 !important; padding: 18px 44px 18px 20px; }';
	css += '#modal-error .modal-body .alert.alert-success { --mb-accent: #2e9e5b; --mb-soft: #e7f5ed; }';
	css += '#modal-error .modal-body .alert.alert-info { --mb-accent: #285A8C; --mb-soft: #eaf0f7; }';
	css += '#modal-error .modal-body .alert.alert-warning { --mb-accent: #e08e0b; --mb-soft: #fdf3e2; }';
	css += '#modal-error .modal-body .alert.alert-danger { --mb-accent: #d0423a; --mb-soft: #fbeaea; }';
	css += '#modal-error h4.messageBoxTitle { display: flex; align-items: center; margin: 0 0 6px; font-size: 16px; font-weight: 600; color: #222 !important; }';
	css += '#modal-error h4.messageBoxTitle .icon { display: inline-flex; align-items: center; justify-content: center; flex: 0 0 auto; width: 28px; height: 28px; margin-right: 10px; border-radius: 50%; font-size: 14px; background: var(--mb-soft); color: var(--mb-accent) !important; }';
	css += '#modal-error .messageBoxMsg { padding-left: 38px; font-size: 14px; line-height: 1.5; color: #555; overflow-wrap: anywhere; max-height: 50vh; overflow-y: auto; }';
	css += '#modal-error .messageBoxMsg ul { margin: 0; padding: 0; }';
	css += '#modal-error .messageBoxMsg li + li { margin-top: 4px; }';
	css += '#modal-error .alert .close { position: absolute; top: 14px; right: 16px; color: #888 !important; opacity: .7; text-shadow: none; font-size: 22px; }';
	css += '#modal-error .alert .close:hover, #modal-error .alert .close:focus { opacity: 1; color: #333 !important; }';
	css += '#modal-error .modal-body .alert { position: relative; }';
	$('head').append('<style id="messagebox-styles">' + css + '</style>');
};

messageBox.prototype.createModal = function() {
	this.injectStyles();
	if ($('#modal-error').length == 0) {
		var ui = '';
		ui += '<div class="modal fade" id="modal-error" tabindex="-1" role="dialog" aria-labelledby="myModalLabel" style="display:none">';
		ui += 	'<div class="modal-dialog" role="document">';
		ui += 		'<div class="modal-content">';
		ui += 			'<div class="modal-body" style="padding: 0px !important;">';
		ui += 				'<div class="alert alert-dismissible" role="alert">';
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
 * @param {string} type - info|success|warning|error
 * @param {string} msg
 * @param {string} [customTitle] - optional title override (e.g. SPA parity messages)
 */
messageBox.prototype.show = function(type, msg, customTitle) {
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
		icon = 'fa-exclamation';
		
	} else if (type == 'error') {
		title = 'Error';
		style = 'alert-danger';
		icon = 'fa-times';
	}

	if (customTitle) {
		title = customTitle;
	}

	$('#modal-error .modal-body .alert').removeClass("alert-info alert-warning alert-danger alert-success").addClass(style);
	$('#modal-error h4.messageBoxTitle').html('<i class="icon fa ' + icon + '"></i> ' + title);
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
		icon = 'fa-exclamation';
		
	} else if (type == 'error') {
		title = 'Error';
		style = 'alert-danger';
		icon = 'fa-times';
	}
	
	$('#modal-error .modal-body .alert').removeClass("alert-info alert-warning alert-danger alert-success").addClass(style);
	$('#modal-error h4.messageBoxTitle').html('<i class="icon fa ' + icon + '"></i> ' + title);
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
