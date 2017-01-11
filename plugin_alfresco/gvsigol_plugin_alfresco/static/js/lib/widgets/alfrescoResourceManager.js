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
	var resourceFolder = this.getFeatureResources(feature)[0].url;
	var ui = '';
	ui += '<div class="input-group">';
	ui += 	'<input readonly type="text" name="message" class="form-control" value="' + resourceFolder + '">';
	ui += 	'<span class="input-group-btn">';
	ui += 		'<button id="open-explorer" type="button" class="btn btn-primary btn-flat"><i class="fa fa-folder margin-r-5"></i>' + gettext('Explore') + '</button>';
	ui += 	'</span>';
	ui += '</div>';
	
	return ui;
};

/**
 * TODO.
 */
AlfrescoResourceManager.prototype.registerEvents = function() {
	var self = this;
	$('#open-explorer').on('click', function () {
		self.openExplorer();
	});
};

/**
 * TODO
 */
AlfrescoResourceManager.prototype.openExplorer = function() {
	var self = this;
	$("body").overlay();
	
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
		var content = self.createContent(selectedSite['cmis:path'] + '/documentlibrary', selectedSite.folders);
		
		$('#explorer-content').empty();
		$('#explorer-content').append(content);
		
		$('.alfresco-link').click(function(){
			window.open('https://devel.gvsigonline.com/share/page/site/swsdp/documentlibrary','_blank','width=640,height=480,left=150,top=200,toolbar=0,status=0');
		});
		
		$('.select-resource-link').click(function(){
			console.log();
		});
	});
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
AlfrescoResourceManager.prototype.getSites = function() {
	var sites = null;
	$.ajax({
		type: 'POST',
		async: false,
	  	url: '/gvsigonline/alfresco/get_sites/',
	  	data: {},
	  	success	:function(response){
	  		sites = JSON.parse(response.sites);
	  	},
	  	error: function(){}
	});
	$.overlayout();
	return sites;
};

/**
 * TODO.
 */
AlfrescoResourceManager.prototype.getSiteContent = function(objectId) {
	$("body").overlay();
	var siteContent = null;
	$.ajax({
		type: 'POST',
		async: false,
	  	url: '/gvsigonline/alfresco/get_site_content/',
	  	data: {
	  		object_id: objectId
	  	},
	  	success	:function(response){
	  		siteContent = JSON.parse(response.site_content);
	  	},
	  	error: function(){}
	});
	$.overlayout();
	return siteContent;
};

/**
 * TODO.
 */
AlfrescoResourceManager.prototype.createContent = function(currentPath, folders) {
	var content = '';
	content += '<div class="box">';
	content += 	'<div class="box-header with-border">';
	content += 		'<h3 class="box-title">' + currentPath + '</h3>';
	content += 	'</div>';
	content += 	'<div class="box-body">';
	content += 		'<ul class="products-list product-list-in-box">';
	for (var i=0; i<folders.length; i++) {
		content += 		'<li class="item">';
		content += 			'<div class="product-img">';
		content += 				'<i class="fa fa-folder" style="font-size: 32px;"></i>';
		content += 			'</div>';
		content += 			'<div class="product-info">';
		content += 				'<a href="/gvsigonline/alfresco/get_folder_content/" class="product-title">' + folders[i].name + ' <span style="font-size: 100%; font-weight: 500; padding: .5em .5em .5em;" class="pull-right"><i class="fa fa-folder-open margin-r-5"></i> ' + gettext('Open') + '</span></a>';
		content += 				'<a href="javascript:void(0)" class="alfresco-link"><span style="font-size: 100%; font-weight: 500; padding: .5em .5em .5em;" class="pull-right"><i class="fa fa-external-link margin-r-5"></i> ' + gettext('Open in alfresco') + '</span></a>';
		content += 				'<a href="javascript:void(0)" class="select-resource-link"><span style="font-size: 100%; font-weight: 500; padding: .5em .5em .5em;" class="pull-right"><i class="fa fa-hand-pointer-o margin-r-5"></i> ' + gettext('Select') + '</span></a>';
		content += 				'<span class="product-description"> ' + folders[i].description + '</span>';
		content += 			'</div>';
		content += 		'</li>';
	}
	content += 		'</ul>';
	content += 	'</div>';
	content += '</div>';
	
	return content;
};