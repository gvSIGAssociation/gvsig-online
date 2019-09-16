/**
 * gvSIG Online.
 * Copyright (C) 2019 SCOLAB.
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
 * @author: César Martinez <cmartinez@scolab.es>
 */


/**
 * This class is extended when the DownloadManager plugin is enabled
 */
if (typeof DownloadManagerUI === 'undefined') {
	var DownloadManagerUI = function(modalSelector, client) {
		this.modalSelector = modalSelector || '#float-modal';
		this.downloadClient = client || null;
	}
}

DownloadManagerUI.prototype.isManagerEnabled = function() {
	return viewer.core.ifToolInConf('gvsigol_plugin_downloadman');
	/*
	console.log(new Error().stack);
	console.log(DownloadManagerUI.layerAvailableDownloads);
	console.log(this.layerAvailableDownloads);
	console.log(viewer.core.getDownloadManager().layerAvailableDownloads);
	// prototype will be extended by the download manager plugin when available
	if (this.layerAvailableDownloads === undefined) {
		return false;
	}*/
}

DownloadManagerUI.prototype.layerDownloads = function(layer) {
	if (this.isManagerEnabled()) {
		this.layerAvailableDownloads(layer);
	}
	else {
		this.layerDirectDownloads(layer);
	}
}

DownloadManagerUI.prototype.layerDirectDownloads = function(layer) {
	console.log(layer);
	if (!layer.baselayer) {
		console.log(layer.wfs_url);
		console.log(layer.wcs_url)
		if (layer.wfs_url) {
			var shapeLink = layer.wfs_url + '?service=WFS&request=GetFeature&version=1.0.0&outputFormat=shape-zip&typeName=' + layer.layer_name;
			var gmlLink = layer.wfs_url + '?service=WFS&version=1.1.0&request=GetFeature&outputFormat=GML3&typeName=' + layer.layer_name;
			var csvLink = layer.wfs_url + '?service=WFS&version=1.1.0&request=GetFeature&outputFormat=csv&typeName=' + layer.layer_name;
			var ui = '';
			ui += '<div class="row">';
			ui += 	'<div class="col-md-12 form-group">';	
			ui += 	'<span>' + gettext('Download links') + '</span>';
			ui += 	'</div>';
			ui += '</div>';
			ui += '<div class="row">';
			ui += 	'<div class="col-md-4 form-group download-btn">';	
			ui += 		'<a href="' + shapeLink + '"><div><i style="margin-right: 10px;" class="fa fa-download"></i>' + gettext('Download ShapeFile') + '</div></a>';
			ui += 	'</div>';
			ui += 	'<div class="col-md-4 form-group download-btn">';	
			ui += 		'<a href="' + csvLink + '"><div><i style="margin-right: 10px;" class="fa fa-download"></i>' + gettext('Download CSV') + '</div></a>';
			ui += 	'</div>';
			ui += 	'<div class="col-md-4 form-group download-btn">';	
			ui += 		'<a target="_blank" href="' + gmlLink + '"><div><i style="margin-right: 10px;" class="fa fa-download"></i>' + gettext('Download GML') + '</div></a>';
			ui += 	'</div>';
			ui += '</div>';
			
			$('#float-modal .modal-body').empty();
			$('#float-modal .modal-body').append(ui);
			$('#float-modal').modal('show');
		}
		else if (layer.wcs_url) {
			var rasterLink = layer.wcs_url + '?service=WCS&version=2.0.0&request=GetCoverage&CoverageId=' + layer.layer_name;
			var ui = '';
			ui += '<div class="row">';
			ui += 	'<div class="col-md-12 form-group">';	
			ui += 	'<span>' + gettext('Download links') + '</span>';
			ui += 	'</div>';
			ui += '</div>';
			ui += '<div class="row">';
			ui += 	'<div class="col-md-4 form-group">';
			ui += 		'<a href="' + rasterLink + '"><div><i style="margin-right: 10px;" class="fa fa-download"></i>' + gettext('Download raster data') + '</div></a>';
			ui += 	'</div>';
			ui += '</div>';
			
			$('#float-modal .modal-body').empty();
			$('#float-modal .modal-body').append(ui);
			$('#float-modal').modal('show');
		}
	}
}
