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


/**
 * TODO.
 */
legend.prototype.getLegendsFromVisibleLayers = function() {
	
	var html = '';
	html += '<div class="box">';
	html += '	<div class="box-body">';
	var layers = this.map.getLayers().getArray();
	for (var i=0; i<layers.length; i++) {
		if (!layers[i].baselayer) {
			if (layers[i].wms_url && layers[i].getVisible()) {
				if (layers[i].legend) {
					if (layers[i].legend != "") {
						html += 		'<div class="box box-widget">';
						html += 			'<div class="box-header with-border">';
						html += 				'<div class="user-block" data-legend="' + layers[i].legend + '">';
						html += 					'<span class="username">' + layers[i].title + '</span>';
						html +=						'<i class="fa fa-expand"></i>';
						html += 				'</div>';
						html += 			'</div>';
						html += 			'<div class="box-body">';
						html += 				'<img class="img-responsive pad" src="' + layers[i].legend + '" alt="Photo">';
						html += 			'</div>';
						html += 		'</div>';
					}	
				}
			}						
		}
	}	
	html += '	</div>';
	html += '</div>';
	
	return html;
};