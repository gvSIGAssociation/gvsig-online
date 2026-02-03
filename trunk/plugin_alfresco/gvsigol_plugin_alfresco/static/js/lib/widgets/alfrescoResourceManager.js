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
var AlfrescoResourceManager = function(selectedLayer) {
	this.selectedLayer = selectedLayer;
	this.engine = 'alfresco';
	this.initialize();
};

/**
 * TODO.
 */
AlfrescoResourceManager.prototype.initialize = function() {
	var self = this;
};

/**
 * TODO.
 */
AlfrescoResourceManager.prototype.getEngine = function() {
	return this.engine;
};

/**
 * TODO.
 */
AlfrescoResourceManager.prototype.getUI = function(feature) {
	var resourceFolderUrl = '#';
	var resourcePath = '';
	var folderName = ' ... ';
	var showRemove = false;
	var rid = null;
	if (feature.getId()) {
		var resources = this.getFeatureResources(feature);
		if (resources.length > 0) {
			resourceFolderUrl = resources[0].url;
			resourcePath = resourceFolderUrl.split('|')[1];
			var splitedPath = resourcePath.split('/');
			folderName = splitedPath[splitedPath.length-1];
			showRemove = true;
			rid = resources[0].rid;
		}
		
	}
	
	var ui = '';
	ui += '<div class="box box-primary">';
	ui += 	'<div class="box-body">';
	ui += 		'<ul class="products-list product-list-in-box">';
	ui += 			'<li class="item">';
	ui += 				'<div class="product-img">';
	ui += 					'<i style="font-size: 48px; color: #f39c12 !important;" class="fa fa-folder-open"></i>';
	ui += 				'</div>';
	ui += 				'<div class="product-info">';
	ui += 					'<a id="resource-title" href="javascript:void(0)" class="product-title">' + folderName + '</a>';
	ui += 					'<span id="resource-description" class="product-description">' + resourcePath + '</span>';
	ui += 				'</div>';
	ui += 			'</li>';
	ui += 		'</ul>';
	ui += 	'</div>';
	ui += 	'<div class="box-footer text-center">';
	ui += 		'<a id="open-explorer" href="javascript:void(0)" style="margin-right: 10px;"><i class="fa fa-folder-open"></i> ' + gettext('Select resource folder') + '</a>';
	ui += 		'<a id="view-resources" data-url="' + resourceFolderUrl + '" href="javascript:void(0)" style="margin-right: 10px;"><i class="fa fa-eye"></i> ' + gettext('View resources') + '</a>';
	if (showRemove) {
		ui += 	'<a id="remove-resource" data-rid="' + rid + '" href="javascript:void(0)" style="margin-right: 10px;"><i class="fa fa-trash"></i> ' + gettext('Delete') + '</a>';
	}
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

/**
 * TODO.
 */
AlfrescoResourceManager.prototype.registerEvents = function() {
	var self = this;
	$('#open-explorer').on('click', function (e) {
		e.preventDefault();
		self.openExplorer();
	});
	
	$('#view-resources').on('click', function (e) {
		e.preventDefault();
		var url = this.dataset.url
		if (url != '#') {
			window.open(url,'_blank','width=780,height=600,left=150,top=200,toolbar=0,status=0');
		}
	});
	
	$('#remove-resource').on('click', function (e) {
		e.preventDefault();
		if (self.deleteResource(this.dataset.rid)) {
			$('#resource-title').text(' ... ');
			$('#resource-description').text('');
			$('#view-resources').attr('data-url', '#');
		}
		
	});
};

/**
 * TODO
 */
AlfrescoResourceManager.prototype.openExplorer = function() {
	var self = this;
	var sites = this.getSites();
	
	var select = '';
	select += '<div class="row">';
	select += 	'<div class="form-group">';
	select += 		'<label>' + gettext('Sites') + '</label>';
	select += 		'<select id="select-site" class="form-control">';
	select += 			'<option value="" disabled selected> -- ' + gettext('Select site') + ' --</option>';
	for (var i=0; i<sites.length; i++) {
		select += 		'<option value="' + sites[i]['cmis:objectId'] + '">' + sites[i]['cmis:name'] + '</option>';
	}
	select += 		'</select>';
	select += 	'</div>';
	select += '</div>';
	
	var explorer = '';
	explorer += '<div class="row">';
	explorer += 	'<div id="explorer-content">';
	explorer += 	'</div>';
	explorer += '</div>';
	
	var container = '';
	container += '<div style="padding: 10px 40px 10px 40px;">';
	container += 	select;
	container += 	explorer;
	container += '</div>';
	
	$('#float-modal .modal-body').empty();
	$('#float-modal .modal-body').append(container);
	
	var buttons = '';
	buttons += '<button id="float-modal-close-explorer" type="button" class="btn btn-default" data-dismiss="modal">' + gettext('Close') + '</button>';
	
	$('#float-modal .modal-footer').empty();
	$('#float-modal .modal-footer').append(buttons);
	
	$("#float-modal").modal('show');
	
	$('#select-site').on('change', function(e) {
		
		var siteId = $('#select-site').val();
		var selectedSite = null;
		for (var i=0; i<sites.length; i++) {
			if (sites[i]['cmis:objectId'] == siteId) {
				selectedSite = sites[i];
			}
		}
		self.createContent(selectedSite['isSite'], selectedSite['cmis:parentId'], selectedSite['cmis:path'] + '/documentlibrary', selectedSite.folders);
	});
};

/**
 * TODO.
 */
AlfrescoResourceManager.prototype.saveResource = function(fid) {
	var self = this;
	var resourcePath = $('#resource-description').text();
	if (resourcePath != '') {
		$.ajax({
			type: 'POST',
			async: false,
		  	url: '/gvsigonline/alfresco/save_resource/',
		  	data: {
		  		path: resourcePath,
		  		layer_name: self.selectedLayer.layer_name,
				workspace: self.selectedLayer.workspace,
				fid: fid
		  	},
		  	success	:function(response){},
		  	error: function(){
		  		messageBox.show('error', gettext('Error saving resource'));
		  	}
		});
	}
};

/**
 * TODO.
 */
AlfrescoResourceManager.prototype.updateResource = function(fid) {
	var self = this;
	var resourcePath = $('#resource-description').text();
	if (resourcePath != '') {
		$.ajax({
			type: 'POST',
			async: false,
		  	url: '/gvsigonline/alfresco/update_resource/',
		  	data: {
		  		path: resourcePath,
		  		layer_name: self.selectedLayer.layer_name,
				workspace: self.selectedLayer.workspace,
				fid: fid
		  	},
		  	success	:function(response){},
		  	error: function(){
		  		messageBox.show('error', gettext('Error saving resource'));
		  	}
		});
	}
};

/**
 * TODO.
 */
AlfrescoResourceManager.prototype.getFeatureResources = function(feature) {
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
	  	beforeSend: function(){
	  		$("body").overlay();
	  	},
	  	success	:function(response){
	  		resources = response.resources;
	  	},
	  	error: function(){}
	});
	$.overlayout();
	return resources;
};

/**
 * TODO.
 */
AlfrescoResourceManager.prototype.deleteResources = function(feature) {
	var deleted = false;
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
	  		}
	  	}, 
	  	error: function(){}
	});
	
	return deleted;
};

/**
 * TODO.
 */
AlfrescoResourceManager.prototype.deleteResource = function(rid) {
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
AlfrescoResourceManager.prototype.getSites = function() {
	var sites = null;
	$.ajax({
		type: 'POST',
		async: false,
	  	url: '/gvsigonline/alfresco/get_sites/',
	  	data: {},
	  	beforeSend: function(){
	  		$("body").overlay();
	  	},
	  	success	:function(response){
	  		sites = response.sites;
	  	},
	  	error: function(){}
	});
	$.overlayout();
	return sites;
};

/**
 * TODO.
 */
AlfrescoResourceManager.prototype.getFolderContent = function(objectId) {
	var folderContent = null;
	$.ajax({
		type: 'POST',
		async: false,
	  	url: '/gvsigonline/alfresco/get_folder_content/',
	  	data: {
	  		object_id: objectId
	  	},
	  	beforeSend: function(){
	  		$("body").overlay();
	  	},
	  	success	:function(response){
	  		folderContent = response.folder_content;
	  	},
	  	error: function(){}
	});
	$.overlayout();
	return folderContent;
};

/**
 * TODO.
 */
AlfrescoResourceManager.prototype.createContent = function(isSite, parent, currentPath, folders) {
	var content = '';
	content += '<div class="box">';
	content += 	'<div class="box-header with-border">';
	content += 		'<h3 class="box-title">' + currentPath + '</h3>';
	if (!isSite) {
		content += 		'<div class="box-tools pull-right">';
		content += 			'<button id="button-parent-directory" data-parentid="' + parent + '" class="btn btn-box-tool"><i class="fa fa-chevron-up margin-r-5"></i> ' + gettext('Parent directory') + '</button>';
		content += 		'</div>';
	}
	content += 	'</div>';
	content += 	'<div class="box-body" style="max-height: 200px; overflow: auto;">';
	content += 		'<ul class="products-list product-list-in-box">';
	for (var i=0; i<folders.length; i++) {
		content += 		'<li class="item">';
		content += 			'<div class="product-img">';
		content += 				'<i class="fa fa-folder" style="font-size: 32px; color: #f39c12 !important;"></i>';
		content += 			'</div>';
		content += 			'<div class="product-info">';
		content += 				'<a href="javascript:void(0)" data-objectid="' + folders[i].objectId + '" class="open-folder product-title">' + folders[i].name + ' <span style="font-size: 100%; font-weight: 500; padding: .5em .5em .5em;" class="pull-right"><i class="fa fa-folder-open margin-r-5"></i> ' + gettext('Open') + '</span></a>';
		content += 				'<a href="javascript:void(0)" data-externallink="' + folders[i].url + '" class="alfresco-link"><span style="font-size: 100%; font-weight: 500; padding: .5em .5em .5em;" class="pull-right"><i class="fa fa-external-link margin-r-5"></i> ' + gettext('Open in alfresco') + '</span></a>';
		content += 				'<a href="javascript:void(0)" data-resourcepath="' + folders[i].path + '" data-externallink="' + folders[i].url + '" class="select-resource-link"><span style="font-size: 100%; font-weight: 500; padding: .5em .5em .5em;" class="pull-right"><i class="fa fa-hand-pointer-o margin-r-5"></i> ' + gettext('Select') + '</span></a>';
		content += 				'<span class="product-description"> ' + folders[i].description + '</span>';
		content += 			'</div>';
		content += 		'</li>';
	}
	content += 		'</ul>';
	content += 	'</div>';
	content += '</div>';
	
	$('#explorer-content').empty();
	$('#explorer-content').append(content);
	
	this.registerFolderEvents();
};

/**
 * TODO.
 */
AlfrescoResourceManager.prototype.registerFolderEvents = function() {
	var self = this;
	
	$('#button-parent-directory').click(function(e){
		e.preventDefault();
		var parentId = this.dataset.parentid;
		var folderContent = self.getFolderContent(parentId);
		self.createContent(folderContent['isSite'], folderContent['cmis:parentId'], folderContent['cmis:path'], folderContent.folders);
	});
	
	$('.open-folder').click(function(e){
		e.preventDefault();
		var objectId = this.dataset.objectid;
		var folderContent = self.getFolderContent(objectId);
		self.createContent(folderContent['isSite'], folderContent['cmis:parentId'], folderContent['cmis:path'], folderContent.folders);
	});
	
	$('.alfresco-link').click(function(e){
		e.preventDefault();
		var externalLink = this.dataset.externallink;
		window.open(externalLink,'_blank','width=780,height=600,left=150,top=200,toolbar=0,status=0');
	});
	
	$('.select-resource-link').click(function(e){
		e.preventDefault();
		var resourcePath = this.dataset.resourcepath;
		var externalLink = this.dataset.externallink;
		var splitedPath = resourcePath.split('/')
		var folderName = splitedPath[splitedPath.length-1]
		$('#resource-title').text(folderName);
		$('#resource-description').text(resourcePath);
		$('#view-resources').attr('data-url', externalLink);
	});
};