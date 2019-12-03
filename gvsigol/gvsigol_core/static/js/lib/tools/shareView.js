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
var shareView = function(conf, map, layerTree) {
	var self = this;
	this.conf = conf;
	this.map = map;
	this.layerTree = layerTree;

	this.id = "share-view";
	
	var button = '<li role="presentation"><a id="share-view" role="menuitem" tabindex="-1" href="#"><i class="fa fa-share-alt m-r-5"></i>'+gettext("Share view")+'</a></li>';
	$('#gvsigol-navbar-file-menu').append(button);

	this.$button = $("#share-view");
	var handler = function(e) {self.handler(e);};
	this.$button.on('click', handler);
	this.$button.on('touchstart', handler);

};



/**
 * @param {Event} e Browser event.
 */
shareView.prototype.handler = function(e) {
	var self = this;
	e.preventDefault();
	
	var ui = '';
	ui += '<div class="row">';
	ui += 	'<div class="col-md-12 form-group">';	
	ui += 	'<label>' + gettext('Enter a description') + '</label>';
	//ui += 	'<textarea class="form-control" name="shareview-emails" id="shareview-emails" rows="3" placeholder"Enter email addresses separated by semicolons"></textarea>';
	ui += 	'<textarea class="form-control" name="shareview-description" id="shareview-description" rows="2"></textarea>';
	ui += 	'</div>';
	ui += '</div>';
	
	$('#float-modal .modal-body').empty();
	$('#float-modal .modal-body').append(ui);
	
	var buttons = '';
	buttons += '<button id="float-modal-cancel-shareview" type="button" class="btn btn-default" data-dismiss="modal">' + gettext('Cancel') + '</button>';
	buttons += '<button id="float-modal-accept-shareview" type="button" class="btn btn-default">' + gettext('Save') + '</button>';
	
	$('#float-modal .modal-footer').empty();
	$('#float-modal .modal-footer').append(buttons);
	
	$("#float-modal").modal('show');
	
	var self = this;	
	$('#float-modal-accept-shareview').on('click', function () {
		//var emails = $('#shareview-emails').val();
		var description = $('#shareview-description').val();
		self.save(description);
		$('#float-modal').modal('hide');
	});
};

/**
 * TODO
 */
shareView.prototype.save = function(description) {
	var self = this;
	
	var viewState = this.layerTree.getState();
	
	var center = map.getView().getCenter();
	var transformedCenter = ol.proj.transform(center, 'EPSG:3857', 'EPSG:4326');
	
	viewState['view'] = {
		"max_zoom_level": this.conf.view.max_zoom_level,
		"zoom": this.map.getView().getZoom(),
	    "center_lon": transformedCenter[0],      
	    "center_lat": transformedCenter[1]
	}
	
	$.ajax({
		type: 'POST',
		async: true,
	  	url: '/gvsigonline/core/save_shared_view/',
	  	beforeSend : function(xhr) {
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
	  	data: {
	  		'pid': self.conf.pid,
	  		'description': description,
			'view_state': JSON.stringify(viewState),
		},
	  	success	:function(response){
	  		messageBox.show('info', response.shared_url);
	  	},
	  	error: function(){}
	});
};
