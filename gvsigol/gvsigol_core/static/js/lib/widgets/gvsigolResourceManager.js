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
var GvsigolResourceManager = function(selectedLayer) {
	this.selectedLayer = selectedLayer;
	this.engine = 'gvsigol';
	this.initialize();
};

/**
 * TODO.
 */
GvsigolResourceManager.prototype.initialize = function() {
	var self = this;
};

/**
 * TODO.
 */
GvsigolResourceManager.prototype.getEngine = function() {
	return this.engine;
};

/**
 * TODO.
 */
GvsigolResourceManager.prototype.getUI = function() {
	var ui = '';
	ui += '<div class="box">';
	ui += 	'<div id="upload-resources">';
	ui += 		'<div id="fileupload-component" class="fileupload-component"></div>';
	ui += 	'</div>';
	ui += 	'<div style="margin-top: 15px;" id="resources-list">';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

/**
 * TODO.
 */
GvsigolResourceManager.prototype.registerEvents = function() {
	
};

/**
 * TODO.
 */
GvsigolResourceManager.prototype.createUploader = function() {
	var uploader = $('#fileupload-component');
	uploader.uploadFile({
	   	url: '/gvsigonline/services/upload_resources/',
	   	fileName: 'resource',
	   	multiple: true,
	   	autoSubmit:false,
	   	formData: {},
	   	showPreview: true,
	   	previewHeight: "100px",
	   	previewWidth: "100px",
	   	onSuccess: function(files,data,xhr){
	   		console.log('Update resource list');
    	},
	   	afterUploadAll: function(files,data,xhr){
	   		$.overlayout();
    		console.log('All resources has been uploaded');
    	},
    	onError: function(files,status,errMsg){}
	});
  	
  	return uploader;
};

/**
 * TODO.
 */
GvsigolResourceManager.prototype.loadResources = function(feature) {
	this.feature = feature;
	var self = this;
	var resourceList = $('#resources-list');
	var resources = this.getFeatureResources(feature);
	for (var i=0; i<resources.length; i++) {
		var resource = '';
		resource += '<div class="box box-default">';
		resource += 	'<div class="box-header">';
		resource += 		'<div class="box-tools pull-right">';
		resource += 			'<button type="button" data-rid="' + resources[i].rid + '" id="remove-resource-' + i + '" class="btn btn-box-tool"><i class="fa fa-times"></i></button>';
		resource += 		'</div>';
		resource += 	'</div>';
		resource += 	'<div class="box-body">';
		if (resources[i].type == 'image') {
			resource += '<a href="' + resources[i].url + '" data-toggle="lightbox" data-gallery="example-gallery">';
			resource += 	'<img src="' + resources[i].url + '" class="img-fluid adjust-image">';
			resource += '</a>';
		} else if  (resources[i].type == 'pdf') {
			resource += '<a href="' + resources[i].url + '" target="_blank">';
			resource += 	'<i style="font-size:24px;" class="fa fa-file-pdf-o margin-r-5"></i>';
			resource += 	'<span style="color:#00c0ef;">' + resources[i].name + '</span>';
			resource += '</a>';
			
		}  else if  (resources[i].type == 'video') {
			resource += '<a href="' + resources[i].url + '" target="_blank">';
			resource += 	'<i style="font-size:24px;" class="fa fa-file-video-o margin-r-5"></i>';
			resource += 	'<span style="color:#00c0ef;">' + resources[i].name + '</span>';
			resource += '</a>';
			
		}   else if  (resources[i].type == 'file') {
			resource += '<a href="' + resources[i].url + '" target="_blank">';
			resource += 	'<i style="font-size:24px;" class="fa fa-file margin-r-5"></i>';
			resource += 	'<span style="color:#00c0ef;">' + resources[i].name + '</span>';
			resource += '</a>';
		}
		resource += 	'</div>';
		resource += '</div>';
		
		resourceList.append(resource);
		
		$('#remove-resource-' + i).on('click', function () {
			var rid = this.dataset.rid;
			if (self.deleteResource(rid)) {
				var resourceBox = this.parentNode.parentNode.parentNode;
				resourceBox.remove();
			}
		});
	}
	
};

/**
 * TODO.
 */
GvsigolResourceManager.prototype.deleteResource = function(rid) {
	var deleted = false;
	var self = this;
	$.ajax({
		type: 'POST',
		async: false,
	  	url: '/gvsigonline/services/delete_resource/',
	  	data: {
	  		rid: rid
	  	},
	  	success	:function(response){
	  		if (response.deleted) {
	  			deleted = true;
				var checkversion = self.checkFeatureVersion(self.selectedLayer, response.featid, response.version, 5);
				if (checkversion <= 0) {
					return;
				}
				self.featureVersionManagement(response.lyrid, response.featid, response.url, self.feature);
	  		}
	  	}, 
	  	error: function(){}
	});
	
	return deleted;
};

/**
 * TODO.
 */
GvsigolResourceManager.prototype.deleteResources = function(feature) {
	var deleted = false;
	var self = this;
	$.ajax({
		type: 'POST',
		async: false,
	  	url: '/gvsigonline/services/delete_resources/',
	  	data: {
	  		query_layer: this.selectedLayer.layer_name,
	  		workspace: this.selectedLayer.workspace,
	  		fid: feature.getId().split('.')[1]
	  	},
	  	success	:function(response){
	  		if (response.deleted) {
	  			deleted = true;
	  			/* deleteResources se llama cuando se borra una feature por lo que no es necesario mantener el control de versión
	  			 if(response.featidlist) {
		  			for(var i = 0; i < response.featidlist.length; i++) {
		  				self.featureVersionManagement(response.lyridlist[i], response.featidlist[i], response.urllist[i], self.feature);
		  			}
	  			}*/
	  		}
	  	}, 
	  	error: function(){}
	});
	
	return deleted;
};

/**
 * TODO.
 */
GvsigolResourceManager.prototype.getFeatureResources = function(feature) {
	var resources = null;
	$.ajax({
		type: 'POST',
		async: false,
	  	url: '/gvsigonline/services/get_feature_resources/',
	  	data: {
	  		query_layer: this.selectedLayer.layer_name,
	  		workspace: this.selectedLayer.workspace,
	  		fid: feature.getId().split('.')[1]
	  	},
	  	success	:function(response){
	  		resources = response.resources;
	  	},
	  	error: function(){}
	});
	
	return resources;
};

GvsigolResourceManager.prototype.featureVersionManagement = function(lyrid, featid, path_, feat) {
	data = {
			"lyrid":lyrid,	
			"featid":featid,
			"operation":5,
			"path":path_
		}
	
	$.ajax({
		type: 'POST',
		async: false,
		data: data,
		url: '/gvsigonline/edition/feature_version_management/',
		beforeSend:function(xhr){
		    xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		success	:function(response) {
			//Actualiza las propiedades de versión de la feature en el  
			//cliente ya que se han cambiado en el servidor
			feat_version_gvol = response.feat_version_gvol
			feat_date_gvol = response.feat_date_gvol
			feat.setProperties({
				"feat_date_gvol": feat_date_gvol,
				"feat_version_gvol": feat_version_gvol
			})
		},
		error: function(response) {
			//console.log(response.statusText)
		}
	});
};

//Operation: 1-Create feat, 2-Update feat, 3-Delete feat, 4-Upload file, 5-Delete file
GvsigolResourceManager.prototype.checkFeatureVersion = function(selectedLayer, featid, version, operation) {
	var success = -1;
	data = {
			"featid":featid,
			"lyrname":selectedLayer.layer_name,
			"workspace":selectedLayer.workspace,
			"version":version,
			"operation":operation
		}
	
	$.ajax({
		type: 'POST',
		async: false,
		data: data,
		url: '/gvsigonline/edition/check_feat_version/',
		beforeSend:function(xhr){
		    xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		success	:function(response) {
			success = 1;//OK
		},
		error: function(response) {
			if(response.status == 404){
				success = 0; //No hay servidor
				return;
			} else if(response.responseText && response.responseText != '') {
				messageBox.show('error', response.responseText);
			} else {
				messageBox.show('error', gettext('Error validando la version'));
			}
			success = -1 //Error en la respuesta
			return;
		}
	});
	return success;
};