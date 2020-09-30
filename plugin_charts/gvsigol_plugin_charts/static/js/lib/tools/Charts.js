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
	this.chartsView = new ChartsView(this.map);
	
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
					if (chartLayer.charts.length > 0) {
						var ui = '';
						ui += '<div style="padding: 0px 12px !important;" class="btn btn-block btn-social btn-select btn-custom-tool">';
						ui += 	'<i class="fa fa-bar-chart" aria-hidden="true"></i>';
						ui += 	'<select id="chart-layer-' + chartLayer.id + '" class="select-chart btn btn-block btn-custom-tool">';
						ui += 		'<option value="__none__"><i class="aria-hidden="true"></i>'+ gettext('Select chart') +'...</option>';
						for(var i=0; i<chartLayer.charts.length; i++){
							var title = chartLayer.charts[i].title;
							ui += 	'<option data-layerid="' + chartLayer.id + '" value="' + chartLayer.charts[i].id + '"><i class="fa fa-search" aria-hidden="true"></i>'+ title +'</option>';
						}
						ui += 		'<option data-layerid="' + chartLayer.id + '" value="__charts_dashboard__"><i class="aria-hidden="true"></i>'+ gettext('Show charts view') +'</option>';
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
		var _this = this;
		var chartId = $('option:selected', $(this)).val();
		if (chartId == '__none__') {
			console.log('None');
			
		} else if (chartId == '__charts_dashboard__') {
			$('body').overlay();
			setTimeout(function(){
				var layerId = $('option:selected', $(_this)).data().layerid;
				self.showChartsView(layerId);
			}, 2000);	
			
		} else {
			$('body').overlay();
			setTimeout(function(){
				var layerId = $('option:selected', $(_this)).data().layerid;
				self.showSingleChart(layerId, chartId);
			}, 2000);
		}
	});
};

Charts.prototype.showChartsView = function(layerId) {
	var self = this;
	$.ajax({
		type: 'POST',
		async: false,
	  	url: '/gvsigonline/charts/view/',
	  	beforeSend : function(xhr) {
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
	  	data: {
	  		layer_id: layerId
	  	},
	  	success	:function(response){
	  		var layer = {
  				layer_id: response.layer_id,
  				layer_name: response.layer_name,
  				layer_title: response.layer_title,
  				layer_workspace: response.layer_workspace,
				layer_wfs_url: response.layer_wfs_url,
				layer_native_srs: response.layer_native_srs  
  			};
	  		var charts = response.charts;
	  		
	  		$('#container').hide();
	  		$('.viewer-search-form').css("display","none");
	  		$('#gvsigol-navbar-tools-dropdown').css("display","none");
			$('#chart-layer-' + layerId + ' option[value=__none__]').prop("selected", true);
			  
	  		self.chartsView.createUI(layer, charts);
			self.chartsView.loadCharts();
			$.overlayout();
		},
	  	error: function(e){
	  		console.log(e);
	  	}
	});
};

Charts.prototype.showSingleChart = function(layerId, chartId) {
	var self = this;
	$.ajax({
		type: 'POST',
		async: false,
	  	url: '/gvsigonline/charts/single_chart/',
	  	beforeSend : function(xhr) {
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
	  	data: {
			layer_id: layerId,
			chart_id: chartId  
	  	},
	  	success	:function(response){
	  		var layer = {
  				layer_id: response.layer_id,
  				layer_name: response.layer_name,
  				layer_title: response.layer_title,
  				layer_workspace: response.layer_workspace,
				layer_wfs_url: response.layer_wfs_url,
				layer_native_srs: response.layer_native_srs  
  			};
	  		var chart = response.chart;

			new SingleChart(self.map, layer, chart);
			$('#chart-layer-' + layerId + ' option[value=__none__]').prop("selected", true);
			$('.select-chart').prop("disabled", true);
			$.overlayout();
		},
	  	error: function(e){
	  		console.log(e);
	  	}
	});
};