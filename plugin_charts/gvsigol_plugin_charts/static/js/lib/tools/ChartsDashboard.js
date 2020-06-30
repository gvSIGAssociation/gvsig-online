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
var ChartsDashboard = function(layer, charts) {
	var self = this;
	this.layer = layer;
	this.jsonCharts = charts;
	this.charts = new Array();
	
	this.initialize();
	this.loadCharts();
	
};

ChartsDashboard.prototype.initialize = function() {
	var self = this;
	
	var ui = '';
	ui += '<div class="row" style="margin-top: 20px;">';
	ui += 	'<div class="col-md-6 form-group">';
	ui += 		'<div class="box">';
	ui += 			'<div class="box-header with-border">';
	ui += 				'<h3 class="box-title">' + gettext('Map') + '</h3>';
	ui += 				'<div class="box-tools pull-right">';
	ui += 					'<button type="button" class="btn btn-box-tool" data-widget="remove"><i class="fa fa-times"></i></button>';
	ui += 				'</div>';
	ui += 			'</div>';
	ui += 			'<div class="box-body">';
	ui += 				'<div id="charts-map" style="width: 100%; height: 350px;"></div>';
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="col-md-6 form-group">';
	ui += 		'<div class="box">';
	ui += 			'<div class="box-header with-border">';
	ui += 				'<h3 class="box-title" id="first-chart-title"></h3>';
	ui += 				'<div class="box-tools pull-right">';
	ui += 					'<button type="button" class="btn btn-box-tool" data-widget="remove"><i class="fa fa-times"></i></button>';
	ui += 				'</div>';
	ui += 			'</div>';
	ui += 			'<div id="first-chart" class="box-body">';
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	$('#charts-container').append(ui);
	
	this.map = new ol.Map({
		layers : [ new ol.layer.Tile({
			source : new ol.source.OSM({
		        "url" : "http://{a-c}.tile.openstreetmap.org/{z}/{x}/{y}.png"
		    })
		})],
		target : 'charts-map',
		view : new ol.View({
			center : [ 0, 0 ],
			zoom : 2
		})
	});
	
	this.source = new ol.source.Vector({
        format: new ol.format.GeoJSON(),
        features: []
	});
	var style = new ol.style.Style({
		fill: new ol.style.Fill({
			color: 'rgba(18, 195, 243, 0.5)'
		}),
    	stroke: new ol.style.Stroke({
    		color: 'rgba(18, 195, 243, 1.0)',
      		width: 2
    	})
    });
	var selectedStyle = new ol.style.Style({
		fill: new ol.style.Fill({
			color: 'rgba(243, 151, 18, 0.5)'
		}),
    	stroke: new ol.style.Stroke({
    		color: 'rgba(243, 151, 18, 1.0)',
      		width: 2
    	})
    });
	this.vectorLayer = new ol.layer.Vector({
		source: this.source,
		style: style
	});
	this.map.addLayer(this.vectorLayer);
	
	$.ajax({
		type: 'POST',
		async: false,
	  	url: self.layer.layer_wfs_url,
	  	data: {
	  		service: 'WFS',
	  		version: '1.0.0',
	  		request: 'GetFeature',
	  		typename: self.layer.layer_workspace + ':' + self.layer.layer_name,
	  		outputFormat: 'application/json'
	  	},
	  	success	:function(response){
	  		var geojson = new ol.format.GeoJSON();
	  		features = geojson.readFeatures(response);
	  		for (var i=0; i < features.length; i++) {
	  			var feat = features[i];
	  			var geom = feat.getGeometry().transform('EPSG:4326', 'EPSG:3857');
	  			feat.setGeometry(geom.clone());	
	  			self.vectorLayer.getSource().addFeature(feat);
	  		}
	  		
	  		var extent = self.vectorLayer.getSource().getExtent();
	    	self.map.getView().fit(extent, self.map.getSize());
		},
	  	error: function(e){
	  		console.log(e);
	  	}
	});
	
	this.selected = [];
	this.map.on('singleclick', function(e) {
		self.map.forEachFeatureAtPixel(e.pixel, function(f) {
			var selIndex = self.selected.indexOf(f);
		    if (selIndex < 0) {
		    	self.selected.push(f);
		    	f.setStyle(selectedStyle);
		    	self.refreshCharts(self.selected);
		    	
		    } else {
		    	self.selected.splice(selIndex, 1);
		    	f.setStyle(style);
		    	self.refreshCharts(self.selected);
		    }
		});
	});
	
};

ChartsDashboard.prototype.loadCharts = function() {
	for (var i=0; i < this.jsonCharts.length; i++) {
		if (i == 0) {
			var firstChart = this.jsonCharts[i];
			$('#first-chart').append('<canvas id="chart-' + firstChart.chart_id + '"></canvas>');
			$('#first-chart-title').text(firstChart.chart_title);
			
			if (firstChart.chart_type == 'barchart') {
				if (firstChart.chart_conf.dataset_type == 'sumarized') {
					this.createSumarizedBarChart(firstChart);
					
				} else {
					this.createBarChart(firstChart);
				}			
				
			} else if (firstChart.chart_type == 'linechart') {
				if (firstChart.chart_conf.dataset_type == 'sumarized') {
					this.createSumarizedLineChart(firstChart);
					
				} else {
					this.createLineChart(firstChart);
				}
				
			} else if (firstChart.chart_type == 'piechart') {
				if (firstChart.chart_conf.dataset_type == 'sumarized') {
					this.createSumarizedPieChart(firstChart);
					
				} else {
					this.createPieChart(firstChart);
				}
			}
			
		} else {
			
		}
	}
};

ChartsDashboard.prototype.refreshCharts = function(selectedFeatures) {
	for (var i=0; i<this.charts.length; i++) {
		var chart = this.charts[i];
		var chartConf = this.getChartConf(chart.chart_id);
		
		chart.data.datasets = [];
		
		if (chartConf.chart_type == 'barchart' || chartConf.chart_type == 'linechart') {
			if (chartConf.chart_conf.dataset_type == 'single_selection') {
				var feature = selectedFeatures[0];
				
				var newDataset = {
					label: feature.getProperties()[chartConf.chart_conf.geographic_names_column],
					backgroundColor: this.getRandomColor(),
					borderColor: this.getRandomColor(),
					borderWidth: 1,
					data: []
				};		
				if (chartConf.chart_type == 'linechart') {
					newDataset.fill = false;
				}
				for (var i=0; i<chartConf.chart_conf.columns.length; i++) {
					newDataset.data.push(feature.getProperties()[chartConf.chart_conf.columns[i].name]);
				}
				chart.data.datasets.push(newDataset);
				chart.update();
				
			} else if (chartConf.chart_conf.dataset_type == 'multiple_selection') {
				for (var j=0; j<selectedFeatures.length; j++) {
					var feature = selectedFeatures[j];
					
					var newDataset = {
						label: feature.getProperties()[chartConf.chart_conf.geographic_names_column],
						backgroundColor: this.getRandomColor(),
						borderColor: this.getRandomColor(),
						borderWidth: 1,
						data: []
					};		
					if (chartConf.chart_type == 'linechart') {
						newDataset.fill = false;
					}
					for (var i=0; i<chartConf.chart_conf.columns.length; i++) {
						newDataset.data.push(feature.getProperties()[chartConf.chart_conf.columns[i].name]);
					}
					chart.data.datasets.push(newDataset);
					chart.update();
				}
			}
			
		} else {}
	}
	
};

ChartsDashboard.prototype.getChartConf = function(chartId) {
	for (var i=0; i < this.jsonCharts.length; i++) {
		if (this.jsonCharts[i].chart_id == chartId) {
			return this.jsonCharts[i];
		}
	}
};

ChartsDashboard.prototype.createBarChart = function(c) {
	var ctx = document.getElementById('chart-' + c.chart_id).getContext('2d');
	
	var labels = new Array();
	for (var i=0; i<c.chart_conf.columns.length; i++) {
		labels.push(c.chart_conf.columns[i].title);
	}
	var data = {
		labels: labels,
		datasets: []
	};
	var chart = new Chart(ctx, {
		type: 'bar',
		data: data,
		options: {
			responsive: true,
			legend: {
				position: 'right',
			},
			scales: {
				xAxes: [{
					display: true,
					scaleLabel: {
						display: true,
						labelString: c.chart_conf.x_axis_title
					}
				}],
				yAxes: [{
					display: true,
					scaleLabel: {
						display: true,
						labelString: c.chart_conf.y_axis_title
					}
				}]
			}
		}
	});
	chart.chart_id = c.chart_id;
	
	this.charts.push(chart);
};

ChartsDashboard.prototype.createSumarizedBarChart = function(c) {
};

ChartsDashboard.prototype.createLineChart = function(c) {
	var ctx = document.getElementById('chart-' + c.chart_id).getContext('2d');
	
	var labels = new Array();
	for (var i=0; i<c.chart_conf.columns.length; i++) {
		labels.push(c.chart_conf.columns[i].title);
	}
	var data = {
		labels: labels,
		datasets: []
	};
	var chart = new Chart(ctx, {
		type: 'line',
		data: data,
		options: {
			responsive: true,
			legend: {
				position: 'right',
			},
			scales: {
				xAxes: [{
					display: true,
					scaleLabel: {
						display: true,
						labelString: c.chart_conf.x_axis_title
					}
				}],
				yAxes: [{
					display: true,
					scaleLabel: {
						display: true,
						labelString: c.chart_conf.y_axis_title
					}
				}]
			}
		}
	});
	chart.chart_id = c.chart_id;
	
	this.charts.push(chart);
};

ChartsDashboard.prototype.createSumarizedLineChart = function(c) {
};

ChartsDashboard.prototype.createPieChart = function(c) {
};

ChartsDashboard.prototype.createSumarizedPieChart = function(c) {
};

ChartsDashboard.prototype.getRandomColor = function(c) {
	var letters = '0123456789ABCDEF'.split('');
    var color = '#';
    for (var i = 0; i < 6; i++ ) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
};