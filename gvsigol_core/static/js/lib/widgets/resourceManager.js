/**
 * gvSIG Online.
 * Copyright (C) 2007-2015 gvSIG Association.
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
var ResourceManager = function(conf) {
	this.conf = conf;
	this.initialize();
};

/**
 * TODO.
 */
ResourceManager.prototype.initialize = function() {
	var self = this;
};

/**
 * TODO.
 */
ResourceManager.prototype.getUI = function() {
	var ui = '';
	if (this.conf.resource_manager.ENGINE == 'gvsigol') {
		ui = this.getCustomUI();
	} else if (this.conf.resource_manager.ENGINE == 'alfresco') {
		ui = this.getAlfrescoUI();
	}
	
	return ui;
};

/**
 * TODO.
 */
ResourceManager.prototype.getCustomUI = function() {
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
ResourceManager.prototype.createUploader = function() {
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
ResourceManager.prototype.loadResources = function(layer, feature) {
	var self = this;
	var resourceList = $('#resources-list');
	var resources = this.getFeatureResources(layer, feature);
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
ResourceManager.prototype.deleteResource = function(rid) {
	var deleted = false;
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
	  		}
	  	}, 
	  	error: function(){}
	});
	
	return deleted;
};

/**
 * TODO.
 */
ResourceManager.prototype.deleteResources = function(layer, feature) {
	var deleted = false;
	$.ajax({
		type: 'POST',
		async: false,
	  	url: '/gvsigonline/services/delete_resources/',
	  	data: {
	  		query_layer: layer.layer_name,
	  		workspace: layer.workspace,
	  		fid: feature.getId().split('.')[1]
	  	},
	  	success	:function(response){
	  		if (response.deleted) {
	  			deleted = true;
	  		}
	  	}, 
	  	error: function(){}
	});
	
	return deleted;
};

/**
 * TODO.
 */
ResourceManager.prototype.getFeatureResources = function(layer, feature) {
	var resources = null;
	$.ajax({
		type: 'POST',
		async: false,
	  	url: '/gvsigonline/services/get_feature_resources/',
	  	data: {
	  		query_layer: layer.layer_name,
	  		workspace: layer.workspace,
	  		fid: feature.getId().split('.')[1]
	  	},
	  	success	:function(response){
	  		resources = response.resources;
	  	},
	  	error: function(){}
	});
	
	return resources;
};

/**
 * TODO.
 */
ResourceManager.prototype.getAlfrescoUI = function() {
	var ui = '';
	ui += '<div class="box">';
	ui += 	'<div id="upload-resources">';
	ui += 		'<div id="fileupload-component" class="fileupload-component"></div>';
	ui += 	'</div>';
	ui += 	'<div id="resources-list">';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};