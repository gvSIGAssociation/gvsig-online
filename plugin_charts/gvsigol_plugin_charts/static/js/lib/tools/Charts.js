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
var Charts = function(conf, map, chartLayers) {
	var self = this;
	this.conf = conf;
	this.map = map;
	this.chartLayers = chartLayers;
	
	this.initialize();
	this.registerEvents();
	
};

Charts.prototype.initialize = function() {
	var self = this;
	var layers = this.map.getLayers();
	
	layers.forEach(function(layer){
		if (layer.baselayer == false) {
			if (layer.is_vector) {
				var chartLayer = self.getChartLayer(layer);
				if (chartLayer != null) {
					if (chartLayer.charts.length > 1) {
						var ui = '';
						ui += '<div style="padding: 0px 12px !important;" class="btn btn-block btn-social btn-select btn-custom-tool">';
						ui += 	'<i class="fa fa-bar-chart" aria-hidden="true"></i>';
						ui += 	'<select id="chart-layer-' + chartLayer.id + '" class="select-chart btn btn-block btn-custom-tool">';
						ui += 		'<option value="__none__"><i class="aria-hidden="true"></i>'+ gettext('Select chart') +'...</option>';
						for(var i=0; i<chartLayer.charts.length; i++){
							var title = chartLayer.charts[i].title;
							ui += 	'<option value="' + chartLayer.charts[i].id + '"><i class="fa fa-search" aria-hidden="true"></i>'+ title +'</option>';
						}
						ui += 		'<option data-layerid="' + chartLayer.id + '" value="__charts_dashboard__"><i class="aria-hidden="true"></i>'+ gettext('Show dashboard (All)') +'</option>';
						ui += 	'</select>';
						ui += '</div>';
					}
	    			var selector = '#layer-box-' + layer.get('id') + ' .box-body';
	    			$(selector).prepend(ui);
				}
    			
		    }				
		}
	}, this);
};

Charts.prototype.getChartLayer = function(mapLayer) {
	var chartLayer = null;
	for (var i=0; i<this.chartLayers.length; i++) {
		if (this.chartLayers[i].name == mapLayer.layer_name && this.chartLayers[i].workspace == mapLayer.workspace) {
			chartLayer = this.chartLayers[i];
		}
	}
	return chartLayer;
};

Charts.prototype.registerEvents = function() {
	var self = this;
	
	$(".select-chart").change(function(e){
		var chartId = $('option:selected', $(this)).val();
		if (chartId == '__none__') {
			console.log('None');
			
		} else if (chartId == '__charts_dashboard__') {
			var layerId = $('option:selected', $(this)).data().layerid;
			self.showDashboard(layerId);
			
		} else {
			self.showChart(chartId);
		}
	});
};

Charts.prototype.showDashboard = function(layerId) {
	window.logo_url = document.getElementById('main-logo').src;
	window.open('/gvsigonline/charts/dashboard/' + layerId + '/');        
	window.focus();
	
};

Charts.prototype.showChart = function(chartId) {
	
};