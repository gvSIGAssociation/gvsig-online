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

var ResourceDownloadParam = function(param_name, title, param_options, value) {
	this.name = param_name;
	this.title = title;
	this.options = param_options;
	if (value === undefined) {
		this.value = null;
	}
	else {
		this.value = value;
	}
}

var ResourceDownloadParamValue = function(resource_param, value) {
	this.param = resource_param;
	this.value = value;
}

var ResourceDescriptor = function(layer_id, layer_title, resource_name, title, direct_download_url, params) {
	this.layer_id = layer_id;
	this.layer_title = layer_title;
	this.name = resource_name;
	this.title = title;
	this.direct_download_url = direct_download_url || '';
	this.params = params || [];
}

var LayerDownloadDescriptor = function(download_res_id, resource_descriptor, param_values) {
	this.download_id = download_res_id;
	this.resource_descriptor = resource_descriptor;
	this.param_values = param_values;
}

var DownloadManagerClient = function(config) {
	this.config = config || {};
	this.config.baseQueryUrl = this.config.queryUrl || '/gvsigonline/downloadmanager/';
	this.config.timeout = this.config.timeout || 5000;
	this.nextDescriptorId = 0;
	this.layerList = [];
}

DownloadManagerClient.prototype.queryAvailableResources = function(layer_id, workspace_name, success_callback, error_callback, callback_context){
	var self = this;
	var queryUrl;
	if (workspace_name!=null) {
		queryUrl = self.config.baseQueryUrl + "layer/" + workspace_name + "/" + layer_id + "/";
	}
	else {
		queryUrl = self.config.baseQueryUrl + "layer/" + layer_id + "/";
	}
	
	console.log(queryUrl);
	/*
	 * We expect an array of objects like this:
	 * 
          [{
            "layer_id": 23,
            "layer_name": "blabla",
            "name": "RASTER_DATA_TYPE",
            "title": "Datos ráster",
            "direct_download": false,
            "params": [
              {
                "name": "format",
                "title": "Formato de fichero",
                 "options": [{
                   "name": "geotiff",
                   "title": "Geotiff (formato Tiff Georeferenciado)",
                }]
              },
              {
                "name": "crs",
                "title": "Sistema de referencia de coordenadas",
                "options": [{
                  "name": "EPSG:4326",
                  "title": "Coordinadas geográficas WGS84",
                },
                {
                  "name": "EPSG:3857",
                  "title": "Proyección Google Mercator",
                }]
                }]
          }]
	 */
	$.ajax({
		url: queryUrl,
		success: function(response) {
			try{
				var resources = [];
				for (var i=0; i<response.length; i++) {
					var res = response[i];
					var params = [];
					for (var j=0; j<res.params.length; j++) {
						downloadParam = new ResourceDownloadParam(res.params[j].name, res.params[j].title, res.params[j].options);
						params.push(downloadParam);
					}
					var resource = new ResourceDescriptor(response[i].layer_id, response[i].layer_title, response[i].name, response[i].title,  response[i].direct_download_url, params);
					resources.push(resource);
				}
			} catch (e) {
				error_callback.call(callback_context, e);
			}
			var params = [resources];
			success_callback.apply(callback_context, params);
		},
		error: function(jqXHR, textStatus) {
			console.log(textStatus);
			console.log(jqXHR);
			console.log(error_callback);
			if (error_callback) {
				error_callback.call(callback_context, textStatus);
			}
		},
		timeout: this.config.timeout
	});
}

DownloadManagerClient.prototype.startDownloadRequest = function(email, success_callback, error_callback, callback_context){
	var self = this;
	var queryUrl = self.config.baseQueryUrl + "request/";
	console.log(queryUrl);

	try {
		var request = {
			"resources": this.getDownloadList()
		}
		if (email !== null) {
			request["email"] = email;
		}
		var data = JSON.stringify(request);
	} catch (e) {console.log("error stringify"); console.log(e)}
	
	$.post(queryUrl, data).done(function(result) {
		console.log('success');
		console.log(result);
		if (result.status_code == 'QP') {
			console.log('qp');
			console.log(success_callback)
			success_callback.apply(callback_context, [result, true]);
			self.clearDownloadList();
			console.log('aaa');
		}
		else {
			error_callback.apply(callback_context, [result, false]);
		}
	
	})
	.fail(function(err) {
		console.log('failed');
		console.log(err);
		error_callback.apply(callback_context, err, false);
	})
	.always(function(val) {
		console.log('finished');
		 console.log(val);
	});
}

DownloadManagerClient.prototype.getDownloadList = function(){
	return this.layerList;
}

DownloadManagerClient.prototype.getDownloadListCount = function(){
	return this.layerList.length;
}


DownloadManagerClient.prototype.clearDownloadList = function(){
	this.layerList.splice(0);
}


DownloadManagerClient.prototype.addLayer = function(resourceDescriptor, param_values) {
	var descriptor = new LayerDownloadDescriptor(this.nextDescriptorId++, resourceDescriptor, param_values);
	this.layerList.push(descriptor);
	
	this.downloadListUpdated();
	return descriptor;
}

DownloadManagerClient.prototype.downloadListUpdated = function() {
	$('.download_list_count').text(this.layerList.length);
}

DownloadManagerClient.prototype.removeLayer = function(descriptor_id) {
	var id = parseInt(descriptor_id);
	for (var i=0; i<this.layerList.length; i++) {
		if (this.layerList[i].download_id == id) {
			this.layerList[i];
			this.layerList.splice(i, 1);
			this.downloadListUpdated();
			return;
		}
	}
}


if (typeof DownloadManagerUI === 'undefined') {
	var DownloadManagerUI = function(modalSelector, client) {
		this.modalSelector = modalSelector || '#float-modal';
		this.downloadClient = client || null;
	}
}

DownloadManagerUI.prototype.setClient = function(client) {
	this.downloadClient = client;
} 

DownloadManagerUI.prototype.setModalSelector = function(selector) {
	this.modalSelector = selector;
} 

DownloadManagerUI.prototype.createDownloadResource = function(downloadDescriptor) {
	var resourceDescriptor = downloadDescriptor.resource_descriptor;
	var downloadParams = downloadDescriptor.param_values;
	var param, paramOption;
	var value;

	var content = '<li class="downman-link downman-download-resource"  data-downloadid="' + downloadDescriptor.download_id + '" data-downloadresource="' + resourceDescriptor.name + '"><div class="form-inline"><div class="form-group"><div class="col-md-10">';
	content += '<i class="fa fa-file-archive-o download-resource" aria-hidden="true"></i><label class="control-label download-resource download-resource-title">' + resourceDescriptor.layer_title + " - " + resourceDescriptor.title + '</label>' ;

	for (var j=0; j<downloadParams.length; j++) {
		param = downloadParams[j].param;
		value = downloadParams[j].value;
		var param_name = param.name;
		var param_title = param.title;
		var paramHtml = '<label for="' + param_name + '" class="control-label">' + param_title + '</label>';
		paramHtml += '<p id="' + param_name +'" class="form-control-static">' + value + '</p>';
		content += paramHtml;
	}

	content += '	</div><div class="col-md-2">';
	//content += '<button class="btn btn-default remove-resource-btn" type="button" data-layerid="' + resource.layer_id + '" data-downloadresource="' + resource.name + '"><i class="fa fa-times fa-icon-button-left" aria-hidden="true"></i></button>';
	content += '<i class="fa fa-times fa-icon-button-left remove-resource-btn" aria-hidden="true" data-downloadid="' + downloadDescriptor.download_id + '"></i>';
	content += '</div></div></div></li>';
	return content;
}

DownloadManagerUI.prototype.createAvailableResource = function(resource) {
	var downloadParams = resource.params;
	var param, paramOption;

	var content = '<li class="downman-link downman-download-resource" data-downloadresource="' + resource.name + '"><div class="form-inline"><div class="form-group"><div class="col-md-10">';
	content += '<i class="fa fa-file-archive-o download-resource" aria-hidden="true"></i><label class="control-label download-resource download-resource-title">' + resource.title + '</label>' ;

	for (var j=0; j<downloadParams.length; j++) {
		param = downloadParams[j];
		var param_name = param.name;
		var param_title = param.title;
		var paramHtml = '<label for="' + param_name + '" class="control-label">' + param_title + '</label>';
		paramHtml += '<select class="form-control" data-paramname="' + param_name + '">';
		for (var k=0; k<param.options.length; k++) {
			paramOption = param.options[k];
			paramHtml += '<option value="' + paramOption.name + '">' + paramOption.title + '</option>';
		}
		paramHtml += '</select>';
		content += paramHtml;
	}

	content += '	</div><div class="col-md-2">';
	content += '<button class="btn btn-default downman-footer-button download-resource-btn" type="button" data-layerid="' + resource.layer_id + '" data-downloadresource="' + resource.name + '">'+gettext("Add to download list")+'</button>';
	content += '</div></div></div></li>';
	return content;
} 


DownloadManagerUI.prototype._getSelectedResource = function(resource_name){
	for (var i=0; i<this.resources.length; i++) {
		if (this.resources[i].name == resource_name) {
			return this.resources[i];
		}
	}
	return null;
}

DownloadManagerUI.prototype._getParam = function(resource, param_name){
	for (var i=0; i<resource.params.length; i++) {
		if (resource.params[i].name == param_name) {
			return resource.params[i];
		}
	}
	return null;
}

DownloadManagerUI.prototype.initAvailableResources = function(downloadResources){
	var self = this;
	self.resources = downloadResources;
	var content = '';
	for (var i=0; i<downloadResources.length; i++) {
		content += this.createAvailableResource(downloadResources[i]);
	}
	if(downloadResources.length == 0){
		content += '<div style="padding: 10px">';
		content += '<div class="downman-no-content col-md-12">';
		content += '<i class="fa fa-ban" aria-hidden="true"></i>   ';
		content += gettext('No results found');
		content += '</div>';
		content += '<div style="clear:both"></div>';
		content += '</div>';
	}

	$(self.modalSelector).find('.modal-body').html(content);
	var footer = '	<button class="btn btn-default downman-footer-button catalog-download-list-btn" type="button"><span class="download_list_count">' + self.getClient().getDownloadListCount() + '</span><i class="fa fa-shopping-cart fa-icon-button-left fa-icon-button-right" aria-hidden="true"></i>'+gettext("Ver lista de descargas")+'</button>';
	//var footer = '	<button class="btn btn-default downman-footer-button catalog-download-list-btn" type="button"><i class="fa fa-shopping-cart fa-icon-button-left" aria-hidden="true"></i></button>';
	footer += '		<div style="clear:both"></div>';
	$(self.modalSelector).find('.modal-footer').html(footer);
	$(self.modalSelector).find('.modal-title').html(gettext("Available downloads"));
	
	$(".catalog-download-list-btn").unbind("click").click(function(){
		self.showDownloadList();
	});
	$(".download-resource-btn").unbind("click").click(function(event){
		var layer_id = event.currentTarget.getAttribute("data-layerid");
		var resource_name = event.currentTarget.getAttribute("data-downloadresource");
		var clickedResource = self._getSelectedResource(resource_name);
		var liElement = $('.downman-download-resource[data-downloadresource="'+resource_name+'"]');
		var values = [];
		liElement.find('select').each(function() {
			var currentParam = self._getParam(clickedResource, this.getAttribute("data-paramname"));
			var resVal = new ResourceDownloadParamValue(currentParam, $(this).val());
			values.push(resVal);
		});
		self.getClient().addLayer(clickedResource, values);
	});
	$(self.modalSelector + " .modal-dialog").LoadingOverlay("hide");
}

DownloadManagerUI.prototype.initAvailableResourcesError = function(){
	var content = '<div style="padding: 10px">';
	content += '<div class="downman-no-content col-md-12">';
	content += '<i class="fa fa-ban" aria-hidden="true"></i>   ';
	content += gettext('The list of downloads could not be retrieved. Try again later or contact the service administrator if the error persists');
	content += '</div>';
	content += '<div style="clear:both"></div>';
	content += '</div>';
	$(this.modalSelector).find('.modal-body').html(content);
	$(this.modalSelector).find('.modal-title').html(gettext("Available downloads"));	
	$(this.modalSelector + " .modal-dialog").LoadingOverlay("hide");
}

DownloadManagerUI.prototype.initDownloadList = function(){
	var downloadResources = this.getClient().getDownloadList();
	var self = this;
	var content = '';
	for (var i=0; i<downloadResources.length; i++) {
		content += this.createDownloadResource(downloadResources[i]);
	}
	if(downloadResources.length == 0){
		content += '<div style="padding: 10px">';
		content += '<div class="downman-no-content col-md-12">';
		content += '<i class="fa fa-ban" aria-hidden="true"></i>   ';
		content += gettext('No layers have been selected for download');
		content += '</div>';
		content += '<div style="clear:both"></div>';
		content += '</div>';
	}

	$(self.modalSelector).find('.modal-body').html(content);
	$(self.modalSelector).find('.modal-title').html(gettext("List of downloads"));
	
	var footer = '	<button class="btn btn-default downman-footer-button start-downloading-btn" type="button"><i class="fa file-download fa-icon-button-left" aria-hidden="true"></i></span>'+gettext("Start downloading")+'</button>';
	footer += '		<div style="clear:both"></div>';
	$(self.modalSelector).find('.modal-footer').html(footer);
	$(".remove-resource-btn").unbind("click").click(function(){
		var download_id = event.currentTarget.getAttribute("data-downloadid");
		self.getClient().removeLayer(download_id);
		$(".modal-body").find('li[data-downloadid="'+download_id+'"]').remove();
	});
	
	$(".start-downloading-btn").unbind("click").click(function(){
		alert('No disponible temporalmente');
		// deshabilitamos para evitar ir creando peticiones que todavía no gestionamos al 100%
		//self.getClient().startDownloadRequest(null, DownloadManagerUI.prototype.showDownloadQueued, DownloadManagerUI.prototype.showDownloadQueued, self);
	});
}

DownloadManagerUI.prototype.showDownloadList = function() {
	this.initDownloadList();
	$(this.modalSelector).modal('show');
}

DownloadManagerUI.prototype.getClient = function() {
	if (this.downloadClient === null) {
		this.downloadClient = new DownloadManagerClient();
	}
	return this.downloadClient; 
}

DownloadManagerUI.prototype.showDownloadQueued = function(json_result, success){
	console.log("showDownloadQueued");
	var content = '';
	content += '<div style="padding: 10px">';
	if (success) {
		content += '<div class="alert alert-success col-md-12">';
		content += '<i class="fa fa-envelope fa-icon-button-left" aria-hidden="true"></i>';
		content += gettext('Your download request has been registered. You will receive an email when your request is ready for download.');
		content += gettext('You can also use this tracking link to get updates about your request:');
		content += gettext('<a target="_blank" href="' + json_result.tracking_url + '">' + json_result.tracking_url + '</a>');
		$(this.modalSelector).find('.modal-footer').empty();
	}
	else {
		content += '<div class="alert alert-danger col-md-12">';
		content += '<i class="fa fa-exclamation-circle fa-icon-button-left" aria-hidden="true"></i>';
		content += gettext('There was an error processing your download request. Please, try again later');
		var footer = '	<button class="btn btn-default downman-footer-button catalog-download-list-btn" type="button"><span class="download_list_count">' + self.getClient().getDownloadListCount() + '</span><i class="fa fa-shopping-cart fa-icon-button-left fa-icon-button-right" aria-hidden="true"></i>'+gettext("Ver lista de descargas")+'</button>';
		footer += '		<div style="clear:both"></div>';
		$(self.modalSelector).find('.modal-footer').html(footer);
		$(".catalog-download-list-btn").unbind("click").click(function(){
			self.showDownloadList();
		});
	}
	content += '</div>';
	content += '<div style="clear:both"></div>';
	content += '</div>';
	console.log(this.modalSelector);
	console.log($(this.modalSelector));

	$(this.modalSelector).find('.modal-body').html(content);
	$(this.modalSelector).find('.modal-title').html(gettext("Download request"));
	$(this.modalSelector).modal('show');
	console.log("showDownloadQueued end");
}

DownloadManagerUI.prototype.layerAvailableDownloads = function(layer) {
	var self = this;
	var workspace_name, layer_id;
	if (typeof layer === 'string' || layer instanceof String || typeof layer === 'number') {
		layer_id = layer;
		workspace_name = null;
	}
	else if (layer.metadata){
		layer_id = layer.metadata;
		workspace_name = null;
	}
	else {
		console.log("assumed to be internal");
		console.log(layer);
		//var layer_id = layer.get("id");
		workspace_name = layer.workspace;
		layer_id = layer.layer_name;
	}
	$(this.modalSelector).find('.modal-title').html(gettext("Available downloads"));
	$(this.modalSelector).find('.modal-body').empty();
	$(this.modalSelector).find('.modal-footer').empty();
	$(this.modalSelector + " .modal-dialog").LoadingOverlay("show");
	$(this.modalSelector).modal('show');
	this.getClient().queryAvailableResources(layer_id, workspace_name, this.initAvailableResources, this.initAvailableResourcesError, this);
	setTimeout(function() {
		$(self.modalSelector).LoadingOverlay("hide");
	}, this.getClient().config.timeout);
}

