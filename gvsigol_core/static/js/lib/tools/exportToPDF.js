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
	
	var button = document.createElement('button');
	button.setAttribute("id", this.id);
	button.setAttribute("class", "toolbar-button");
	button.setAttribute("title", gettext('Export to PDF'));
	var icon = document.createElement('i');
	icon.setAttribute("class", "fa fa-print");
	button.appendChild(icon);
	
	this.$button = $(button);
	
	$('#toolbar').append(button);

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
	var self = this;
	e.preventDefault();
	//if( navigator.userAgent.toLowerCase().indexOf('firefox') > -1 || !this.conf.is_public_project){ 
		
		var body = '';
		body += '<div class="row">';
		body += 	'<div class="col-md-12 form-group">';
		body += 		'<label style="background-color: #3c8dbc !important; padding: 10px; border-radius: 5px; color: white; margin-bottom: 15px;" for="export-map-title">' + gettext('Map title') + '</label>';
		body += 		'<input placeholder="' + gettext('Map title') + '" name="export-map-title" id="export-map-title" type="text" class="form-control">';					
		body += 	'</div>';
		body += '</div>';
		
		body += '<div class="row">';
		body +=     '<div class="col-md-12 form-group" id="previewmap" style="width:600px;height:400px;"></div>';
		body += '</div>';
		
		$('#float-modal .modal-body').empty();
		$('#float-modal .modal-body').append(body);
		
		var buttons = '';
		buttons += '<button id="float-modal-cancel-print" type="button" class="btn btn-default" data-dismiss="modal">' + gettext('Cancel') + '</button>';
		buttons += '<button id="float-modal-accept-print" style="border:none; color: white;background-color: #07579E !important" type="button" class="btn btn-default">' + gettext('Exportar a PDF') + '</button>';
		
		$('#float-modal .modal-footer').empty();
		$('#float-modal .modal-footer').append(buttons);
		
		$("#float-modal").modal('show');
		
		var osm = new ol.layer.Tile({
    		source: new ol.source.OSM()
    	});
		var printMap = new ol.Map({
	        layers: this.map.getLayers(),
	        target: 'previewmap',
	        renderer: 'canvas',
	        view: new ol.View({
	            center: self.map.getView().getCenter(),
	            zoom: self.map.getView().getZoom() - 2
	        })
	    });
		
		var self = this;	
		$('#float-modal-accept-print').on('click', function () {
			var title = $('#export-map-title').val();
			
			window.map = printMap;
			window.title = title;
			window.open('/gvsigonline/core/export/' + self.conf.pid + '/');       
			window.focus();
			
			$('#float-modal').modal('hide');
		});

//	}else{
//		var body = '';
//		body += '<div class="row">';
//		body += 	'<div class="col-md-12 form-group">';
//		body += 		'<label for="export-map-title">' + gettext('Function not available') + '</label><br />';
//		body += 		'<label class="export-map-content" style="font-weight: normal;">' + gettext('This functionality is only available on Mozilla Firefox') + '</label>';					
//		body += 	'</div>';
//		body += '</div>';
//
//		$('#float-modal .modal-body').empty();
//		$('#float-modal .modal-body').append(body);
//
//		var buttons = '';
//		buttons += '<button id="float-modal-accept-print" type="button" class="btn btn-default">' + gettext('Accept') + '</button>';
//
//		$('#float-modal .modal-footer').empty();
//		$('#float-modal .modal-footer').append(buttons);
//
//		$("#float-modal").modal('show');
//
//		var self = this;	
//		$('#float-modal-accept-print').on('click', function () {
//			$('#float-modal').modal('hide');
//		});
//	}
};

/**
 * TODO
 */
exportToPDF.prototype.deactivate = function() {			
	this.$button.removeClass('button-active');
	this.active = false;
};