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
	this.tool = new gvsigol.tools.ShareView(conf, map, layerTree);
	this.id = "share-view";
	this.installUI();
};

shareView.prototype.installUI = function() {
	var button = '<li role="presentation"><a id="share-view" role="menuitem" tabindex="-1" href="#"><i class="fa fa-share-alt m-r-5"></i>'+gettext("Share view")+'</a></li>';
	$('#gvsigol-navbar-file-menu').append(button);

	this.$button = $("#share-view");
	var self = this;
	var handler = function(e) {self.tool.handle(e)};
	this.$button.on('click', handler);
	this.$button.on('touchstart', handler);
}
 

/**
 * We define the tool that can be used independently from UI
 */
var gvsigol = gvsigol || {};
gvsigol.tools = gvsigol.tools || {};
gvsigol.tools.ShareView = function(conf, map, layerTree) {
	this.conf = conf;
	this.map = map;
	this.layerTree = layerTree;
}

/**
 * @param {Event} e Browser event.
 */
gvsigol.tools.ShareView.prototype.handle = function(e) {
	var self = this;
	e.preventDefault();
	var description = $('#shareview-description').val();
	self.save(description);
	$('#float-modal').modal('hide');
};

gvsigol.tools.ShareView.prototype.getViewState = function() {
	var viewState = this.layerTree.getState();
	var center = this.map.getView().getCenter();
	var transformedCenter = ol.proj.transform(center, 'EPSG:3857', 'EPSG:4326');
	viewState['view'] = {
			"max_zoom_level": this.conf.view.max_zoom_level,
			"zoom": this.map.getView().getZoom(),
			"center_lon": transformedCenter[0],
			"center_lat": transformedCenter[1]
		}
	return viewState;
}

gvsigol.tools.ShareView.prototype.getSharedViewState = function(description) {
	return {
		'pid': this.conf.pid,
		'description': description,
		'view_state': JSON.stringify(this.getViewState())
	};
}

/**
 * TODO
 */
gvsigol.tools.ShareView.prototype.save = function(description) {
	var self = this;
	var viewState = this.getViewState();
	desc = this.getSharedViewState(description)
	
	$.ajax({
		type: 'POST',
		async: true,
	  	url: '/gvsigonline/core/create_shared_view/',
	  	beforeSend : function(xhr) {
			xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
		},
	  	data: desc,
	  	success	:function(response){
	  		var ui = '';
	  		ui += '<div class="row">';
	  		ui += 	'<div class="col-md-12 form-group">';	
	  		ui +=   	'<input id="url-to-copy" type="text" class="form-control url-to-copy" disabled value="' + response.shared_url + '"></input>';
			ui +=       '<input type="checkbox" id="no-expiration"> <label for="cbox2">' + gettext('Marque para que la URL no expire') +'</label>';
	  		ui += 	'</div>';
	  		ui += '</div>';
	  		
	  		$('#float-modal .modal-body').empty();
	  		$('#float-modal .modal-body').append(ui);
	  		
	  		var buttons = '';
			
	  		buttons += '<button id="float-modal-save-shareview" type="button" class="btn btn-default">' + gettext('Guardar URL') + '</button>';
			buttons += '<button id="float-modal-copy-shareview" type="button" class="btn btn-default" disabled >' + gettext('Copiar URL') + '</button>';
	  		
	  		$('#float-modal .modal-footer').empty();
	  		$('#float-modal .modal-footer').append(buttons);
	  		
	  		$("#float-modal").modal('show');
	  		
	  		var self = this;	
	  		
			$('#float-modal-copy-shareview').on('click', function () {
				$('#url-to-copy').prop('disabled', false);
	  			var urlToCopy = document.querySelector('.url-to-copy');
	  			urlToCopy.select();
	  			
	  			try {
	  			    var successful = document.execCommand('cut');
	  			    $(".url-to-copy").val(response.shared_url);
	  			    
	  			  } catch(err) {
	  			    console.log('Oops, unable to cut');
	  			  }
				
				$('#url-to-copy').prop('disabled', true);
	  		});

			$('#float-modal-save-shareview').on('click', function () {

				desc['shared_url'] = response.shared_url
				
				if ($("#no-expiration").is(':checked')){
					desc['checked'] = 'true'
				}else{
					desc['checked'] = 'false'
				}

				$.ajax({
					type: 'POST',
					async: true,
					  url: '/gvsigonline/core/save_shared_view/',
					  beforeSend : function(xhr) {
						xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
					},
					  data: desc,
					  success	:function(response){
						$('#float-modal-copy-shareview').prop('disabled', false);
						
					  },
					  error: function(){}
				});
				
			})


	  	},
	  	error: function(){}
	});
};
