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
	this.loadLegend();
};

/**
 * TODO.
 */
legend.prototype.loadLegend = function() {
	
	var self = this;
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
	xhr.responseType = "arraybuffer";
	xhr.onload = function () {
		var blob;
		var arrayBufferView = new Uint8Array(this.response);
		if (src.toLowerCase().indexOf("png") != -1) { // FIXME: weak format detection
			blob = new Blob([arrayBufferView], { type: 'image/png' });
		}
		else {
			blob = new Blob([arrayBufferView], { type: 'image/jpeg' });
		}
		var urlCreator = window.URL || window.webkitURL;
		var imageUrl = urlCreator.createObjectURL(blob);
		image.src = imageUrl;
	};
	xhr.send();
}

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
