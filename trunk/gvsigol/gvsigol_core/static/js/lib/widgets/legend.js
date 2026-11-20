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
var legend = function(conf, map) {
	this.map = map;	
	this.conf = conf;
	this.legendContainer = $('#legend-tab');
	this.legendContainer.append('<div class="box-body" style="margin: 10px"><i class="fa fa-spinner fa-spin" aria-hidden="true"></i></div>');
	this._loaded = false;
};

/**
 * TODO.
 */
legend.prototype.loadLegend = function() {
	
	var self = this;
	if (!this._loaded) {
		this._loaded = true;
		this.legendContainer.empty();
		var legends = this.getLegendsFromVisibleLayers();
		this.legendContainer.append(legends);
		
		$('.user-block').on('click', function(){
			var legend = this.dataset.legend;
			var ui = '';
			ui += '<div class="box-body">';
			ui += 	'<img src="' + legend + '" alt="Photo">';
			ui += '</div>';
			
			$('#float-modal .modal-body').empty();
			$('#float-modal .modal-body').append(ui);
			$("#float-modal").modal('show');
		});
	}
};


/**
 * TODO.
 */
legend.prototype.reloadLegend = function() {
	
	var self = this;
	var legends = this.getLegendsFromVisibleLayers();
	this.legendContainer.empty();	
	this.legendContainer.append(legends);
	
	$('.user-block').on('click', function(){
		var legend = this.dataset.legend;
		var ui = '';
		ui += '<div class="box-body">';
		ui += 	'<img src="' + legend + '" alt="Photo">';
		ui += '</div>';
		
		$('#float-modal .modal-body').empty();
		$('#float-modal .modal-body').append(ui);
		$("#float-modal").modal('show');
	});
};

legend.prototype._loadLegendImg = function(image, src) {
	var xhr = new XMLHttpRequest();
	xhr.open("GET", src);
	if (this.conf.user && this.conf.user.token) {
		// FIXME: this is just an OIDC test. We must properly deal with refresh tokens etc
		var bearer_token = "Bearer " + this.conf.user.token;
		xhr.setRequestHeader('Authorization', bearer_token);
	}
	xhr.responseType = "blob";
	xhr.onload = function () {
		if (xhr.status == 401) {
			console.log(xhr.getAllResponseHeaders());
			messageBox.show("error", "Geoserver session has expired. Logout from gvSIG Online and login again to reset the session");
		}
		else if (xhr.status == 403) {
			console.log(xhr.getAllResponseHeaders());
			messageBox.show("error", "You are not allowed to read the layer or Geoserver session has expired. Logout from gvSIG Online and login again to reset the session");
		}
		else if (xhr.getResponseHeader("content-type").indexOf("application/vnd.ogc.se_xml") !== -1) {
			// returned in cross-domain requests instead of the 401 error
			console.log(xhr.status)
			console.log(xhr.getAllResponseHeaders());
			const reader = new FileReader();

			// This fires after the blob has been read/loaded.
			reader.addEventListener('loadend', (e) => {
				const text = reader.result;
				var parser = new DOMParser();
				xmlDoc = parser.parseFromString(text, "text/xml");
				var exception = xmlDoc.getElementsByTagName("ServiceException");
				if (exception && exception.length>0) {
					if (exception[0].getAttribute('code') == 'LayerNotDefined') {
						messageBox.show("error", "The layer does not exists or Geoserver session has expired. Logout from gvSIG Online and login again to reset the session");
					}
				}
			});
			reader.readAsText(this.response);
		}
		var urlCreator = window.URL || window.webkitURL;
		var imageUrl = urlCreator.createObjectURL(this.response);
		image.src = imageUrl;
	};
	xhr.send();
};


/**
 * TODO.
 */
legend.prototype.getLegendsFromVisibleLayers = function() {
	
	var html = '';
	html += '<div class="box">';
	html += '	<div class="box-body">';
	html += '	</div>';
	html += '</div>';
	html = $(html);
	var layerLegend, img;
	var layers = this.map.getLayers().getArray();
	for (var i=0; i<layers.length; i++) {
		if (!layers[i].baselayer) {
			if (layers[i].wms_url && layers[i].getVisible()) {
				if (layers[i].legend) {

					if (layers[i].legend.includes("??")) {
						layers[i].legend =  layers[i].legend.replace('??', '?');
					}

					if (layers[i].legend != "") {
						layerLegend = 		'<div class="box box-widget">';
						layerLegend += 			'<div class="box-header with-border">';
						layerLegend += 				'<div class="user-block" data-legend="' + layers[i].legend + '">';
						layerLegend += 					'<span class="username">' + layers[i].title + '</span>';
						layerLegend +=						'<i class="fa fa-expand"></i>';
						layerLegend += 				'</div>';
						layerLegend += 			'</div>';
						layerLegend += 			'<div class="box-body">';
						layerLegend += 				'<img class="img-responsive pad" src="" alt="Photo">';
						layerLegend += 			'</div>';
						layerLegend += 		'</div>';
						layerLegend = $(layerLegend);
						img = layerLegend.find('img')[0];
						if (this.conf.user && this.conf.user.token && !layers[i].external) {
							this._loadLegendImg(img, layers[i].legend);
						}
						else {
							img.src = layers[i].legend;
						}
						html.append(layerLegend);
					}	
				}
			}						
		}
	}
	
	return html;
};
