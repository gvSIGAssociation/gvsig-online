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
var StaticDownloads = function(url, conf, map) {
	var self = this;
	this.url = url;
	this.conf = conf;
	this.map = map;

	this.id = "staticdownloads";
	this.$button = $("#staticdownloads");

	var handler = function(e) {
		self.handler(e);
	};

	this.$button.on('click', handler);
	this.$button.on('touchstart', handler);

};

/**
 * TODO
 */
StaticDownloads.prototype.deactivable = true;

/**
 * @param {Event} e Browser event.
 */
StaticDownloads.prototype.handler = function(e) {
	e.preventDefault();
	//window.open(this.url,'_blank','width=780,height=600,left=150,top=200,toolbar=0,status=0');	
	
	
	e.preventDefault();
	if(self.modal == null){
		self.modal = '<div class="modal fade ui-draggable" id="modal-sd-dialog" tabindex="-1" role="dialog" aria-hidden="true" data-backdrop="">'+
		'	<div class="modal-dialog" role="document" style="width: 800px; height: 600px;">'+
		'		<div class="modal-content">'+
		'			<button id="close-modal-sd" type="button" class="close" data-dismiss="modal" aria-label="Close" style="float:right;font-size: 40px;margin-right: 10px;">'+
		'				<span aria-hidden="true">×</span>'+
		'			</button>'+
		'			<div id="modal-sd-custom_content" style="float:left" class="modal-body">Custom HTML content'+
		'			</div>'+
		' 			<div style="clear:both"></div>'+
		'		</div>'+
		'	</div>'+
		'</div>';
		$('body').append(self.modal);
		
		$("#modal-sd-dialog").modal('show');
		$('#modal-sd-custom_content').html(
			'<iframe width="760" height="600" src="'+ this.url +'" frameborder="0"></iframe>'
		);

		$('#close-modal-sd').unbind("click").click(function(){
			$("#modal-sd-dialog").modal('hide');
			self.modal = null;
		});
		
	} else {
		$("#modal-sd-dialog").modal('hide');
		self.modal = null;
		
	}
};

/**
 * TODO
 */
StaticDownloads.prototype.deactivate = function() {
};