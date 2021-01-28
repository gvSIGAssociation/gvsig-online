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
			if (typeof(uploader.delegatedOnSuccess)=='function') {
				uploader.delegatedOnSuccess(files, data, xhr);
			}
		},
		afterUploadAll: function(files,data,xhr){
			$.overlayout();
		},
		onError: function(files,status,errMsg){
			uploader.errors = uploader.errors.concat(files);
			if (uploader.getFileCount()==1) {
				$.overlayout();
				var errorMsg = gettext('Some files could not be uploaded:') + ' ' + uploader.errors.join(", ");
				uploader.errors = [];
				messageBox.show('error', errorMsg);
			}
	}
	});
	uploader.errors = [];
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
			var anchor = $('<a data-toggle="lightbox" data-gallery="example-gallery" data-type="image"></a>')
			var img =       $('<img class="img-fluid adjust-image">');
			anchor.attr("href", resources[i].url);
			img.attr("src", resources[i].url);
			anchor.append(img);
			resource += anchor.prop('outerHTML');
		} else if  (resources[i].type == 'pdf') {
			var anchor = $('<a target="_blank"><i style="font-size:24px;" class="fa fa-file-pdf-o margin-r-5"></i></a>');
			anchor.attr("href", resources[i].url);
			var span = $('<span style="color:#00c0ef;"></span>');
			span.text(resources[i].title);
			anchor.append(span);
			resource += anchor.prop('outerHTML');
		} else if  (resources[i].type == 'video') {
			var anchor = $('<a target="_blank"><i style="font-size:24px;" class="fa fa-file-video-o margin-r-5"></i></a>');
			anchor.attr("href", resources[i].url);
			var span = $('<span style="color:#00c0ef;"></span>');
			span.text(resources[i].title);
			anchor.append(span);
			resource += anchor.prop('outerHTML');
		} else if  (resources[i].type == 'file') {
			var anchor = $('<a target="_blank"><i style="font-size:24px;" class="fa fa-file margin-r-5"></i></a>');
			anchor.attr("href", resources[i].url);
			var span = $('<span style="color:#00c0ef;"></span>');
			span.text(resources[i].title);
			anchor.append(span);
			resource += anchor.prop('outerHTML');
		}
		resource += 	'</div>';
		resource += '</div>';
		
		resourceList.append(resource);
		
		$('#remove-resource-' + i).on('click', function () {
			feature.deletedResources_ = feature.deletedResources_ || [];
			var rid = this.dataset.rid;
			feature.deletedResources_.push(rid);
			var resourceBox = this.parentNode.parentNode.parentNode;
			resourceBox.remove();
		});
	}
	
};

/**
 * TODO.
 */
GvsigolResourceManager.prototype.deleteResource = function(rid) {
	var deleted = false;
	var self = this;
	var data = {
			rid: rid
	};
	// Feature version management is directly done in server-side delete_resource method
	if (self.feature.getProperties().feat_version_gvol !== undefined) {
		data.feat_version_gvol = self.feature.getProperties().feat_version_gvol;
	}
	if (self.feature.getProperties().feat_date_gvol !== undefined) {
		data.feat_date_gvol = self.feature.getProperties().feat_date_gvol;
	}
	$.ajax({
		type: 'POST',
		async: false,
		url: '/gvsigonline/services/delete_resource/',
		data: data,
		success	:function(response){
			if (response.deleted) {
				if (response.feat_version !== undefined) {
					self.feature.setProperties({
						"feat_date_gvol": response.feat_date,
						"feat_version_gvol": response.feat_version
					});
				}
				deleted = true;
			}
		}, 
		error: function(response){
			console.log(response);
			if(response.status == 409){
				messageBox.show('error', gettext('Version conflict: the feature was edited concurrently. Restart your editing session to get the last version.'));
			} else if(response.responseText && response.responseText != '') {
				messageBox.show('error', response.responseText);
			} else {
				messageBox.show('error', gettext('Error deleting resource'));
			}
		}
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
				/* deleteResources se llama cuando se borra una feature por lo que no es necesario mantener el control de versión */
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