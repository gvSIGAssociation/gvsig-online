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
var SingleChart = function(map, layer, chart) {
    var self = this;	
	this.map = map;
	this.layer = layer;
	this.jsonChart = chart;

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
    this.vectorLayer.setZIndex(99999999);
	this.map.addLayer(this.vectorLayer);

	this.initialize();
};

SingleChart.prototype.initialize = function() {
    var self = this;
	
	var chartId = this.jsonChart.chart_id;

	var ui = '';
	ui += '<div id="floating-modal-chart-' + chartId + '">';
	ui += 	'<div class="box box-default">';
	ui += 		'<div class="box-header with-border">';
	ui += 			'<h3 class="box-title" id="single-chart-title-' + chartId + '"></h3>';
	ui += 			'<div id="single-tools-' + chartId + '" class="box-tools pull-right">';
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 		'<div id="single-chart-' + chartId + '" class="box-body">';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
    $('body').append(ui);
    $('#floating-modal-chart-' + chartId).dialog({
		width: 600,
		resizable: false,
		autoOpen: true,
		open: function (event, ui) {
		    //$('#floating-modal5').css('overflow', 'hidden');
		},
		close: function( event, ui ) {
			self.map.removeLayer(self.vectorLayer);
			$('.select-chart').prop("disabled", false);
			$('#floating-modal-chart-' + chartId).remove();
		}
	});

	this.loadVectorLayer();
	this.loadChart();
};

SingleChart.prototype.loadVectorLayer = function() {
    var self = this;
	
	$.ajax({
		type: 'POST',
		async: false,
	  	url: this.layer.layer_wfs_url,
	  	data: {
	  		service: 'WFS',
	  		version: '1.0.0',
	  		request: 'GetFeature',
	  		typename: this.layer.layer_workspace + ':' + this.layer.layer_name,
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
	  		
	  		/*var extent = self.vectorLayer.getSource().getExtent();
	    	self.map.getView().fit(extent, self.map.getSize());*/
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
					self.refreshChart(self.selected);
					
				} else {
					self.selected.splice(selIndex, 1);
					f.setStyle(null);
					self.refreshChart(self.selected);
				}
				
			} else {
				for (var i=0; i < self.source.getFeatures().length; i++) {
					self.source.getFeatures()[i].setStyle(null);
				}
				self.selected.push(f);
				f.setStyle(selectedStyle);
				self.refreshChart(self.selected);
			}
		});
	});
};

SingleChart.prototype.enableMultipleSelection = function() {
	var enable = false;
	if (this.jsonChart.chart_conf.dataset_type == 'multiple_selection') {
        enable = true;
    }
	return enable;
};

SingleChart.prototype.loadChart = function() {
	var self = this;

	var chartId = this.jsonChart.chart_id;

    $('#single-chart-' + chartId).append('<canvas id="chart-' + chartId + '"></canvas>');
	$('#single-chart-title-' + chartId).text(self.jsonChart.chart_title);
    var download = '';
    download += '<a style="color: #222222;" class="download-chart" data-chartid="' + chartId + '" id="download-' + chartId + '" download="' + this.layer.layer_title + '.png" href="" class="btn btn-primary float-right bg-flat-color-1">';
    download += 	'<i style="margin-right: 10px;" class="fa fa-download"></i>';
    download += '</a>';
    download += '<a style="color: #222222;" class="download-pdf-chart" data-chartid="' + chartId + '" id="download-pdf-' + chartId + '" href="" class="btn btn-primary float-right bg-flat-color-1">';
    download += 	'<i class="fa fa-file-pdf-o"></i>';
    download += '</a>';
    $('#single-tools-' + chartId).append(download);
    
    if (self.jsonChart.chart_type == 'barchart') {
        if (self.jsonChart.chart_conf.dataset_type == 'aggregated') {
            this.createAggregatedBarChart();
            
        } else {
            this.createBarChart();
        }			
        
    } else if (self.jsonChart.chart_type == 'linechart') {
        if (self.jsonChart.chart_conf.dataset_type == 'aggregated') {
            this.createAggregatedLineChart();
            
        } else {
            this.createLineChart();
        }
        
    } else if (self.jsonChart.chart_type == 'piechart') {
        if (self.jsonChart.chart_conf.dataset_type == 'aggregated') {
            this.createAggregatedPieChart();
            
        } else {
            this.createPieChart();
        }
    }
    $('.download-chart').on('click', function(){
        var chartId = this.dataset.chartid;
        var url_base64jp = document.getElementById('chart-' + chartId).toDataURL("image/png");
        var a =  document.getElementById('download-' + chartId);
        a.href = url_base64jp;
    });
    
    
    $('.download-pdf-chart').on('click', function(e){
        e.preventDefault();
        var canvas = document.querySelector('#chart-' + self.jsonChart.chart_id);
        var canvasImg = self.canvasToImage(canvas, '#ffffff');

        var doc = new jsPDF('landscape');
        doc.setFontSize(20);
        doc.text(15, 15, self.jsonChart.chart_title);
        doc.addImage(canvasImg, 'PNG', 10, 10, 280, 150 );
        
        var uri = doc.output('dataurlstring');
        self.openDataUriWindow(uri);
    });
};

SingleChart.prototype.canvasToImage = function(canvas, backgroundColor) {
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
	var imageData = canvas.toDataURL("image/png", 1.0);
 
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

SingleChart.prototype.openDataUriWindow = function(url) {
	var html = '<html>' +
	    '<style>html, body { padding: 0; margin: 0; } iframe { width: 100%; height: 100%; border: 0;}  </style>' +
	    '<body>' +
	    '<iframe id="pdf-iframe" src="' + url + '"></iframe>' +
	    '</body></html>';
	a = window.open("", "_blank");
	a.document.write(html);
};

SingleChart.prototype.refreshChart = function(selectedFeatures) {
    var chart = this.chart;
	if (this.jsonChart.chart_type == 'barchart' || this.jsonChart.chart_type == 'linechart') {
        if (this.jsonChart.chart_conf.dataset_type == 'single_selection') {
            chart.data.datasets = [];
            var feature = selectedFeatures[selectedFeatures.length - 1];
            var color = feature.getProperties().custom_color;
            var newDataset = {
                label: feature.getProperties()[this.jsonChart.chart_conf.geographic_names_column],
                backgroundColor: color,
                borderColor: color,
                borderWidth: 1,
                data: []
            };		
            if (this.jsonChart.chart_type == 'linechart') {
                newDataset.fill = false;
            }
            for (var k=0; k<this.jsonChart.chart_conf.columns.length; k++) {
                newDataset.data.push(feature.getProperties()[this.jsonChart.chart_conf.columns[k].name]);
            }
            chart.data.datasets.push(newDataset);
            chart.update();
            
        } else if (this.jsonChart.chart_conf.dataset_type == 'multiple_selection') {
            chart.data.datasets = [];
            for (var j=0; j<selectedFeatures.length; j++) {
                var feature = selectedFeatures[j];
                var color = feature.getProperties().custom_color;
                var newDataset = {
                    label: feature.getProperties()[this.jsonChart.chart_conf.geographic_names_column],
                    backgroundColor: color,
                    borderColor: color,
                    borderWidth: 1,
                    data: []
                };		
                if (this.jsonChart.chart_type == 'linechart') {
                    newDataset.fill = false;
                }
                for (var l=0; l<this.jsonChart.chart_conf.columns.length; l++) {
                    newDataset.data.push(feature.getProperties()[this.jsonChart.chart_conf.columns[l].name]);
                }
                chart.data.datasets.push(newDataset);
                chart.update();
            }
        }
        
    } else if (this.jsonChart.chart_type == 'piechart'){
        if (this.jsonChart.chart_conf.dataset_type == 'single_selection') {
            chart.data.datasets = [];
            var feature = selectedFeatures[selectedFeatures.length - 1];
            var newDataset = {
                label: feature.getProperties()[this.jsonChart.chart_conf.geographic_names_column],
                backgroundColor: [],
                data: []
            };		
            for (var k=0; k<this.jsonChart.chart_conf.columns.length; k++) {
                newDataset.data.push(feature.getProperties()[this.jsonChart.chart_conf.columns[k].name]);
                newDataset.backgroundColor.push(this.getRandomColor());
            }
            chart.data.datasets.push(newDataset);
            chart.update();
        }
    }
	
};

SingleChart.prototype.getChartConf = function(chartId) {
	for (var i=0; i < this.jsonCharts.length; i++) {
		if (this.jsonCharts[i].chart_id == chartId) {
			return this.jsonCharts[i];
		}
	}
};

SingleChart.prototype.createBarChart = function() {
	var ctx = document.getElementById('chart-' + this.jsonChart.chart_id).getContext('2d');
	
	var labels = new Array();
	for (var i=0; i<this.jsonChart.chart_conf.columns.length; i++) {
		labels.push(this.jsonChart.chart_conf.columns[i].title);
	}
	var data = {
		labels: labels,
		datasets: []
	};
	this.chart = new Chart(ctx, {
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
						labelString: this.jsonChart.chart_conf.x_axis_title
					}
				}],
				yAxes: [{
					display: true,
					scaleLabel: {
						display: true,
						labelString: this.jsonChart.chart_conf.y_axis_title
					}
				}]
			}
		}
	});
    this.chart.chart_id = this.jsonChart.chart_id;
    this.chart.update();
};

SingleChart.prototype.createAggregatedBarChart = function() {
	var ctx = document.getElementById('chart-' + this.jsonChart.chart_id).getContext('2d');
	
	var labels = new Array();
	for (var i=0; i<this.jsonChart.chart_conf.columns.length; i++) {
		labels.push(this.jsonChart.chart_conf.columns[i].title);
	}
	
	var features = this.vectorLayer.getSource().getFeatures();
	var color = this.getRandomColor();
	var newDataset = {
		label: this.jsonChart.chart_title,
		backgroundColor: color,
		borderColor: color,
		borderWidth: 1,
		data: []
	};		
	for (var k=0; k<this.jsonChart.chart_conf.columns.length; k++) {
		var data = 0;
		for (var j=0; j<features.length; j++) {
			data += features[j].getProperties()[this.jsonChart.chart_conf.columns[k].name]
		}
		newDataset.data.push(data);
	}
	var data = {
		labels: labels,
		datasets: [newDataset]
	};
	this.chart = new Chart(ctx, {
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
						labelString: this.jsonChart.chart_conf.x_axis_title
					}
				}],
				yAxes: [{
					display: true,
					scaleLabel: {
						display: true,
						labelString: this.jsonChart.chart_conf.y_axis_title
					}
				}]
			}
		}
	});
	this.chart.chart_id = this.jsonChart.chart_id;
	this.chart.update();
};

SingleChart.prototype.createLineChart = function(c) {
	var ctx = document.getElementById('chart-' + this.jsonChart.chart_id).getContext('2d');
	
	var labels = new Array();
	for (var i=0; i<this.jsonChart.chart_conf.columns.length; i++) {
		labels.push(this.jsonChart.chart_conf.columns[i].title);
	}
	var data = {
		labels: labels,
		datasets: []
	};
	this.chart = new Chart(ctx, {
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
						labelString: this.jsonChart.chart_conf.x_axis_title
					}
				}],
				yAxes: [{
					display: true,
					scaleLabel: {
						display: true,
						labelString: this.jsonChart.chart_conf.y_axis_title
					}
				}]
			}
		}
	});
    this.chart.chart_id = this.jsonChart.chart_id;
    this.chart.update();
};

SingleChart.prototype.createAggregatedLineChart = function(c) {
};

SingleChart.prototype.createPieChart = function(c) {
	var ctx = document.getElementById('chart-' + this.jsonChart.chart_id).getContext('2d');
	
	var labels = new Array();
	for (var i=0; i<this.jsonChart.chart_conf.columns.length; i++) {
		labels.push(this.jsonChart.chart_conf.columns[i].title);
	}
	var data = {
		labels: labels,
		datasets: []
	};
	this.chart = new Chart(ctx, {
		type: 'pie',
		data: data,
		options: {
			responsive: true,
			legend: {
				position: 'right',
			},
			tooltips: {
				callbacks: {
					label: function(tooltipItem, data) {
						//get the concerned dataset
						var dataset = data.datasets[tooltipItem.datasetIndex];
						//calculate the total of this data set
						var total = dataset.data.reduce(function(previousValue, currentValue, currentIndex, array) {
						  return previousValue + currentValue;
						});
						//get the current items value
						var currentValue = dataset.data[tooltipItem.index];
						//calculate the precentage based on the total and current item, also this does a rough rounding to give a whole number
						var percentage = Math.floor(((currentValue/total) * 100)+0.5);
				  
						return percentage + "%";
					}
				}
			}
		}
	});
    this.chart.chart_id = this.jsonChart.chart_id;
    this.chart.update();
};

SingleChart.prototype.createAggregatedPieChart = function(c) {
	var ctx = document.getElementById('chart-' + this.jsonChart.chart_id).getContext('2d');
	
	var labels = new Array();
	for (var i=0; i<this.jsonChart.chart_conf.columns.length; i++) {
		labels.push(this.jsonChart.chart_conf.columns[i].title);
	}
	
	var features = this.vectorLayer.getSource().getFeatures();
	var color = this.getRandomColor();
	var newDataset = {
		label: this.jsonChart.chart_title,
		backgroundColor: [],
		data: []
	};		
	for (var k=0; k<this.jsonChart.chart_conf.columns.length; k++) {
		var data = 0;
		for (var j=0; j<features.length; j++) {
			data += features[j].getProperties()[this.jsonChart.chart_conf.columns[k].name]
		}
		newDataset.data.push(data);
		newDataset.backgroundColor.push(this.getRandomColor());
	}
	var data = {
		labels: labels,
		datasets: [newDataset]
	};
	this.chart = new Chart(ctx, {
		type: 'pie',
		data: data,
		options: {
			responsive: true,
			legend: {
				position: 'right',
			},
			tooltips: {
				callbacks: {
					label: function(tooltipItem, data) {
						//get the concerned dataset
						var dataset = data.datasets[tooltipItem.datasetIndex];
						//calculate the total of this data set
						var total = dataset.data.reduce(function(previousValue, currentValue, currentIndex, array) {
						  return previousValue + currentValue;
						});
						//get the current items value
						var currentValue = dataset.data[tooltipItem.index];
						//calculate the precentage based on the total and current item, also this does a rough rounding to give a whole number
						var percentage = Math.floor(((currentValue/total) * 100)+0.5);
				  
						return percentage + "%";
					}
				}
			}
		}
	});
	this.chart.chart_id = this.jsonChart.chart_id;
	this.chart.update();
};

SingleChart.prototype.getRandomColor = function(){
	var letters = '0123456789ABCDEF'.split('');
    var color = '#';
    for (var i = 0; i < 6; i++ ) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
};

SingleChart.prototype.hexToRgb = function(hex) {
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

SingleChart.prototype.styleFunction = function(feature, resolution) {
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