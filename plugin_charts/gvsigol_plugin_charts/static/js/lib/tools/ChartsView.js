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
var ChartsView = function() {
	var self = this;	
	this.initialize();
	
	$('body').on('change-to-2D-event', function() {
		self.hide();
	});
	
	$('body').on('change-to-3D-event', function() {
		self.hide();
	});
	
	$('body').on('show-catalog-event', function() {
		self.hide();
	});
};

ChartsView.prototype.initialize = function() {
	var self = this;
	
	var ui = '';
	ui += '<ul id="charts-container" style="list-style-type: none; margin: 0; padding: 20px; width: 100%;">';
	ui += '</ul>';
	$('body').append(ui);
	this.chartsContainer = $("#charts-container");
	this.chartsContainer.sortable({
		cancel: "#charts-map"
	});
	this.chartsContainer.disableSelection();
};

ChartsView.prototype.createUI = function(layer, charts) {
	var self = this;
	
	this.layer = layer;
	this.jsonCharts = charts;
	this.charts = new Array();
	
	var title = '<span id="dashboard-layer-tile" style="position: relative;left: 35%;top: 5px;font-size: 24px;color: #ffffff;">' + gettext('Layer') + ': ' + this.layer.layer_title + '</span>';
	$('#viewer-navbar').append(title);
	
	this.chartsContainer.empty();
	var ui = '';
	ui += 	'<li class="ui-state-default" style="float: left; width: 47%; text-align: center; margin: 5px;">';
	ui += 		'<div class="box">';
	ui += 			'<div class="box-header with-border">';
	ui += 				'<h3 class="box-title">' + gettext('Map') + '</h3>';
	ui += 			'</div>';
	ui += 			'<div class="box-body">';
	ui += 				'<div id="charts-map" style="width: 100%;"></div>';
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 	'</li>';
	ui += 	'<li class="ui-state-default" style="float: left; width: 47%; text-align: center; margin: 5px;">';
	ui += 		'<div class="box">';
	ui += 			'<div class="box-header with-border">';
	ui += 				'<h3 class="box-title" id="first-chart-title"></h3>';
	ui += 				'<div id="first-tools" class="box-tools pull-right">';
	ui += 				'</div>';
	ui += 			'</div>';
	ui += 			'<div id="first-chart" class="box-body">';
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 	'</li>';
	this.chartsContainer.append(ui);
	this.chartsContainer.show();
	
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
	this.map.on("movestart", function(e) {
		e.preventDefault();
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
	this.vectorLayer = new ol.layer.Vector({
		source: this.source,
		style: this.styleFunction.bind(this)
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
				//CHANGE
				//var geom = feat.getGeometry().transform('EPSG:4326', 'EPSG:3857');
	  			var geom = feat.getGeometry().transform(self.layer.layer_native_srs, 'EPSG:3857');
	  			feat.setGeometry(geom.clone());	
	  			var props = feat.getProperties();
	  			props['custom_color'] = self.getRandomColor();
	  			feat.setProperties(props);
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
			var selectedStyle = new ol.style.Style({
				fill: new ol.style.Fill({
					color: 'rgba(247, 247, 18, 0.5)'
				}),
		    	stroke: new ol.style.Stroke({
		    		color: 'rgba(247, 247, 18, 1.0)',
		      		width: 2
		    	}),
		    	text: new ol.style.Text({
		    		textAlign: 'center',
		    		font: 'normal 12px/1 sans-serif',
		    		text: f.getProperties()['nome'],
		    		fill: new ol.style.Fill({color: '#ffffff'}),
		    		stroke: new ol.style.Stroke({color: '#000000', width: 1}),
		    		offsetX: 0,
		    		offsetY: 0,
		    		placement: 'point',
		    		rotation: 0
		    	})
			});
			if (self.enableMultipleSelection()) {
				if (selIndex < 0) {
					self.selected.push(f);
					f.setStyle(selectedStyle);
					self.refreshCharts(self.selected);
					
				} else {
					self.selected.splice(selIndex, 1);
					f.setStyle(null);
					self.refreshCharts(self.selected);
				}
				
			} else {
				for (var i=0; i < self.source.getFeatures().length; i++) {
					self.source.getFeatures()[i].setStyle(null);
				}
				self.selected.push(f);
				f.setStyle(selectedStyle);
				self.refreshCharts(self.selected);
			}
		});
	});
	
	var search = new ol.control.SearchFeature({
		placeholder: gettext('Search') + ' ...',
		source: this.source,
		property: this.jsonCharts[0].chart_conf.geographic_names_column
	});
	this.map.addControl (search);
	// Select feature when click on the reference index
	search.on('select', function(e){	
		var f = e.search;
		var selIndex = self.selected.indexOf(f);
		var selectedStyle = new ol.style.Style({
			fill: new ol.style.Fill({
				color: 'rgba(247, 247, 18, 0.5)'
			}),
	    	stroke: new ol.style.Stroke({
	    		color: 'rgba(247, 247, 18, 1.0)',
	      		width: 2
	    	}),
	    	text: new ol.style.Text({
	    		textAlign: 'center',
	    		font: 'normal 12px/1 sans-serif',
	    		text: f.getProperties()['nome'],
	    		fill: new ol.style.Fill({color: '#ffffff'}),
	    		stroke: new ol.style.Stroke({color: '#000000', width: 1}),
	    		offsetX: 0,
	    		offsetY: 0,
	    		placement: 'point',
	    		rotation: 0
	    	})
		});
		
		if (self.enableMultipleSelection()) {
			if (selIndex < 0) {
				self.selected.push(f);
				f.setStyle(selectedStyle);
				self.refreshCharts(self.selected);
				
			} else {
				self.selected.splice(selIndex, 1);
				f.setStyle(null);
				self.refreshCharts(self.selected);
			}

		} else {
			for (var i=0; i < self.source.getFeatures().length; i++) {
				self.source.getFeatures()[i].setStyle(null);
			}
			self.selected.push(f);
			f.setStyle(selectedStyle);
			self.refreshCharts(self.selected);
		}
		var p = e.search.getGeometry().getFirstCoordinate();
		self.map.getView().animate({ center:p });
		var extent = f.getGeometry().getExtent();
		self.map.getView().fit(extent, self.map.getSize());
	});
	var height = $('#charts-map').height();
	$('#charts-map').css('height', (height-8).toString() + 'px');
};

ChartsView.prototype.enableMultipleSelection = function() {
	var enable = false;
	for (var i=0; i<this.jsonCharts.length; i++) {
		if (this.jsonCharts[i].chart_conf.dataset_type == 'multiple_selection') {
			enable = true;
		}
	}
	return enable;
};

ChartsView.prototype.hide = function() {
	this.chartsContainer.hide();
	$('#dashboard-layer-tile').remove();
	$('#container').show();
	$('.viewer-search-form').css("display","inline-block");
	$('#gvsigol-navbar-tools-dropdown').css("display","block");
};

ChartsView.prototype.loadCharts = function() {
	var self = this;
	for (var i=0; i < this.jsonCharts.length; i++) {
		if (i == 0) {
			var firstChart = this.jsonCharts[i];
			$('#first-chart').append('<canvas id="chart-' + firstChart.chart_id + '"></canvas>');
			$('#first-chart-title').text(firstChart.chart_title);
			var download = '';
			download += '<a class="download-chart" data-chartid="' + firstChart.chart_id + '" id="download-' + firstChart.chart_id + '" download="' + this.layer.layer_title + '.jpg" href="" class="btn btn-primary float-right bg-flat-color-1">';
			download += 	'<i style="margin-right: 10px;" class="fa fa-download"></i>';
			download += '</a>';
			download += '<a class="download-pdf-chart" data-chartid="' + firstChart.chart_id + '" id="download-pdf-' + firstChart.chart_id + '" href="" class="btn btn-primary float-right bg-flat-color-1">';
			download += 	'<i class="fa fa-file-pdf-o"></i>';
			download += '</a>';
			$('#first-tools').append(download);
			
			if (firstChart.chart_type == 'barchart') {
				if (firstChart.chart_conf.dataset_type == 'aggregated') {
					this.createAggregatedBarChart(firstChart);
					
				} else {
					this.createBarChart(firstChart);
				}			
				
			} else if (firstChart.chart_type == 'linechart') {
				if (firstChart.chart_conf.dataset_type == 'aggregated') {
					this.createAggregatedLineChart(firstChart);
					
				} else {
					this.createLineChart(firstChart);
				}
				
			} else if (firstChart.chart_type == 'piechart') {
				if (firstChart.chart_conf.dataset_type == 'aggregated') {
					this.createAggregatedPieChart(firstChart);
					
				} else {
					this.createPieChart(firstChart);
				}
			}
			
		} else {
			
			var chart = this.jsonCharts[i];

			var ui = '';
			
			ui += 	'<li class="ui-state-default" style="float: left; width: 47%; text-align: center;margin: 5px;">';
			ui += 		'<div class="box">';
			ui += 			'<div class="box-header with-border">';
			ui += 				'<h3 class="box-title">' + chart.chart_title + '</h3>';
			ui += 				'<div class="box-tools pull-right">';
			ui += 					'<a class="download-chart" data-chartid="' + chart.chart_id + '" id="download-' + chart.chart_id + '" download="' + this.layer.layer_title + '.jpg" href="" class="btn btn-primary float-right bg-flat-color-1">';
			ui += 						'<i style="margin-right: 10px;" class="fa fa-download"></i>';
			ui += 					'</a>';
			ui += 					'<a class="download-pdf-chart" data-chartid="' + chart.chart_id + '" id="download-pdf-' + chart.chart_id + '" href="" class="btn btn-primary float-right bg-flat-color-1">';
			ui += 						'<i class="fa fa-file-pdf-o"></i>';
			ui += 					'</a>';
			ui += 				'</div>';
			ui += 			'</div>';
			ui += 			'<div class="box-body">';
			ui += 				'<canvas id="chart-' + chart.chart_id + '"></canvas>';
			ui += 			'</div>';
			ui += 		'</div>';
			ui += 	'</li>';
			$('#charts-container').append(ui);
			
			if (chart.chart_type == 'barchart') {
				if (chart.chart_conf.dataset_type == 'aggregated') {
					this.createAggregatedBarChart(chart);
					
				} else {
					this.createBarChart(chart);
				}			
				
			} else if (chart.chart_type == 'linechart') {
				if (chart.chart_conf.dataset_type == 'aggregated') {
					this.createAggregatedLineChart(chart);
					
				} else {
					this.createLineChart(chart);
				}
				
			} else if (chart.chart_type == 'piechart') {
				if (chart.chart_conf.dataset_type == 'aggregated') {
					this.createAggregatedPieChart(chart);
					
				} else {
					this.createPieChart(chart);
				}
			}
			
		}
		$('.download-chart').on('click', function(){
			var chartId = this.dataset.chartid;
			var url_base64jp = document.getElementById('chart-' + chartId).toDataURL("image/jpg");
			var a =  document.getElementById('download-' + chartId);
			a.href = url_base64jp;
		});
		
		
		$('.download-pdf-chart').on('click', function(e){
			e.preventDefault();
			var chartId = this.dataset.chartid;
			var chartConf = self.getChartConf(chartId);
			var canvas = document.querySelector('#chart-' + chartId);
			//creates image
			var canvasImg = self.canvasToImage(canvas, '#ffffff');
		  
			//creates PDF from img
			var doc = new jsPDF('landscape');
			doc.setFontSize(20);
			doc.text(15, 15, chartConf.chart_title);
			doc.addImage(canvasImg, 'JPEG', 10, 10, 280, 150 );
			
			var uri = doc.output('dataurlstring');
	        self.openDataUriWindow(uri);
		});
		
	}
};

ChartsView.prototype.canvasToImage = function(canvas, backgroundColor) {
	//cache height and width		
	var w = canvas.width;
	var h = canvas.height;
	
	var context = canvas.getContext("2d");
 
	var data;
 
	if(backgroundColor)
	{
		//get the current ImageData for the canvas.
		data = context.getImageData(0, 0, w, h);
 
		//store the current globalCompositeOperation
		var compositeOperation = context.globalCompositeOperation;
 
		//set to draw behind current content
		context.globalCompositeOperation = "destination-over";
 
		//set background color
		context.fillStyle = backgroundColor;
 
		//draw background / rect on entire canvas
		context.fillRect(0,0,w,h);
	}
 
	//get the image data from the canvas
	var imageData = canvas.toDataURL("image/jpeg", 1.0);
 
	if(backgroundColor)
	{
		//clear the canvas
		context.clearRect (0,0,w,h);
 
		//restore it with original / cached ImageData
		context.putImageData(data, 0,0);
 
		//reset the globalCompositeOperation to what it was
		context.globalCompositeOperation = compositeOperation;
	}
 
	//return the Base64 encoded data url string
	return imageData;
};

ChartsView.prototype.openDataUriWindow = function(url) {
	var html = '<html>' +
	    '<style>html, body { padding: 0; margin: 0; } iframe { width: 100%; height: 100%; border: 0;}  </style>' +
	    '<body>' +
	    '<iframe id="pdf-iframe" src="' + url + '"></iframe>' +
	    '</body></html>';
	a = window.open("", "_blank");
	a.document.write(html);
};

ChartsView.prototype.refreshCharts = function(selectedFeatures) {
	for (var i=0; i<this.charts.length; i++) {
		var chart = this.charts[i];
		var chartConf = this.getChartConf(chart.chart_id);
		
		if (chartConf.chart_type == 'barchart' || chartConf.chart_type == 'linechart') {
			if (chartConf.chart_conf.dataset_type == 'single_selection') {
				chart.data.datasets = [];
				var feature = selectedFeatures[selectedFeatures.length - 1];
				var color = feature.getProperties().custom_color;
				var newDataset = {
					label: feature.getProperties()[chartConf.chart_conf.geographic_names_column],
					backgroundColor: color,
					borderColor: color,
					borderWidth: 1,
					data: []
				};		
				if (chartConf.chart_type == 'linechart') {
					newDataset.fill = false;
				}
				for (var k=0; k<chartConf.chart_conf.columns.length; k++) {
					newDataset.data.push(feature.getProperties()[chartConf.chart_conf.columns[k].name]);
				}
				chart.data.datasets.push(newDataset);
				chart.update();
				
			} else if (chartConf.chart_conf.dataset_type == 'multiple_selection') {
				chart.data.datasets = [];
				for (var j=0; j<selectedFeatures.length; j++) {
					var feature = selectedFeatures[j];
					var color = feature.getProperties().custom_color;
					var newDataset = {
						label: feature.getProperties()[chartConf.chart_conf.geographic_names_column],
						backgroundColor: color,
						borderColor: color,
						borderWidth: 1,
						data: []
					};		
					if (chartConf.chart_type == 'linechart') {
						newDataset.fill = false;
					}
					for (var l=0; l<chartConf.chart_conf.columns.length; l++) {
						newDataset.data.push(feature.getProperties()[chartConf.chart_conf.columns[l].name]);
					}
					chart.data.datasets.push(newDataset);
					chart.update();
				}
			}
			
		} else if (chartConf.chart_type == 'piechart'){
			if (chartConf.chart_conf.dataset_type == 'single_selection') {
				chart.data.datasets = [];
				var feature = selectedFeatures[selectedFeatures.length - 1];
				var newDataset = {
					label: feature.getProperties()[chartConf.chart_conf.geographic_names_column],
					backgroundColor: [],
					data: []
				};		
				for (var k=0; k<chartConf.chart_conf.columns.length; k++) {
					newDataset.data.push(feature.getProperties()[chartConf.chart_conf.columns[k].name]);
					newDataset.backgroundColor.push(this.getRandomColor());
				}
				chart.data.datasets.push(newDataset);
				chart.update();
			}
		}
	}
	
};

ChartsView.prototype.getChartConf = function(chartId) {
	for (var i=0; i < this.jsonCharts.length; i++) {
		if (this.jsonCharts[i].chart_id == chartId) {
			return this.jsonCharts[i];
		}
	}
};

ChartsView.prototype.createBarChart = function(c) {
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

ChartsView.prototype.createAggregatedBarChart = function(c) {
	var ctx = document.getElementById('chart-' + c.chart_id).getContext('2d');
	
	var labels = new Array();
	for (var i=0; i<c.chart_conf.columns.length; i++) {
		labels.push(c.chart_conf.columns[i].title);
	}
	
	var features = this.vectorLayer.getSource().getFeatures();
	var color = this.getRandomColor();
	var newDataset = {
		label: c.chart_title,
		backgroundColor: color,
		borderColor: color,
		borderWidth: 1,
		data: []
	};		
	for (var k=0; k<c.chart_conf.columns.length; k++) {
		var data = 0;
		for (var j=0; j<features.length; j++) {
			data += features[j].getProperties()[c.chart_conf.columns[k].name]
		}
		newDataset.data.push(data);
	}
	var data = {
		labels: labels,
		datasets: [newDataset]
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
	chart.update();
	this.charts.push(chart);
};

ChartsView.prototype.createLineChart = function(c) {
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

ChartsView.prototype.createAggregatedLineChart = function(c) {
};

ChartsView.prototype.createPieChart = function(c) {
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
		type: 'pie',
		data: data,
		options: {
			responsive: true,
			legend: {
				position: 'right',
			}
		}
	});
	chart.chart_id = c.chart_id;
	
	this.charts.push(chart);
};

ChartsView.prototype.createAggregatedPieChart = function(c) {
	var ctx = document.getElementById('chart-' + c.chart_id).getContext('2d');
	
	var labels = new Array();
	for (var i=0; i<c.chart_conf.columns.length; i++) {
		labels.push(c.chart_conf.columns[i].title);
	}
	
	var features = this.vectorLayer.getSource().getFeatures();
	var color = this.getRandomColor();
	var newDataset = {
		label: c.chart_title,
		backgroundColor: [],
		data: []
	};		
	for (var k=0; k<c.chart_conf.columns.length; k++) {
		var data = 0;
		for (var j=0; j<features.length; j++) {
			data += features[j].getProperties()[c.chart_conf.columns[k].name]
		}
		newDataset.data.push(data);
		newDataset.backgroundColor.push(this.getRandomColor());
	}
	var data = {
		labels: labels,
		datasets: [newDataset]
	};
	var chart = new Chart(ctx, {
		type: 'pie',
		data: data,
		options: {
			responsive: true,
			legend: {
				position: 'right',
			}
		}
	});
	chart.chart_id = c.chart_id;
	chart.update();
	this.charts.push(chart);
};

ChartsView.prototype.getRandomColor = function(){
	var letters = '0123456789ABCDEF'.split('');
    var color = '#';
    for (var i = 0; i < 6; i++ ) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
};

ChartsView.prototype.hexToRgb = function(hex) {
	// Expand shorthand form (e.g. "03F") to full form (e.g. "0033FF")
	var shorthandRegex = /^#?([a-f\d])([a-f\d])([a-f\d])$/i;
	hex = hex.replace(shorthandRegex, function(m, r, g, b) {
		return r + r + g + g + b + b;
	});

	var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
	return result ? {
		r: parseInt(result[1], 16),
		g: parseInt(result[2], 16),
		b: parseInt(result[3], 16)
	} : null;
};

ChartsView.prototype.styleFunction = function(feature, resolution) {
	//var color = this.getRandomColor();
	
	var fillColor = this.hexToRgb(feature.getProperties()['custom_color']);
	var fill = new ol.style.Fill({
		color: 'rgba(' + fillColor.r + ',' + fillColor.g + ',' + fillColor.b + ',0.2)'
		//color: 'rgba(32, 206, 88, 0.5)'
	});
	var stroke = new ol.style.Stroke({
		color: 'rgba(' + fillColor.r + ',' + fillColor.g + ',' + fillColor.b + ',1.0)',
		//color: 'rgba(32, 206, 88, 1.0)',
  		width: 1
	});
	var text = new ol.style.Text({
		textAlign: 'center',
		font: 'normal 12px/1 sans-serif',
		text: feature.getProperties()['nome'],
		fill: new ol.style.Fill({color: '#ffffff'}),
		stroke: new ol.style.Stroke({color: '#000000', width: 1}),
		offsetX: 0,
		offsetY: 0,
		placement: 'point',
		rotation: 0
	});
	
	var style = new ol.style.Style({
		fill: fill,
    	stroke: stroke,
    	text: text
    });	

	return [style];
};