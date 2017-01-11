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
var AlfrescoResourceManager = function() {
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
AlfrescoResourceManager.prototype.getUI = function() {
	var repository = this.getRepository();
	var ui = '';
	ui += '<div class="box">';
	ui += '</div>';
	
	return ui;
};

/**
 * TODO.
 */
AlfrescoResourceManager.prototype.getRepository = function() {
	var repository = null;
	$.ajax({
		type: 'POST',
		async: false,
	  	url: '/gvsigonline/alfresco/get_repository/',
	  	data: {},
	  	success	:function(response){
	  		repository = response.repository;
	  	},
	  	error: function(){}
	});
	
	return repository;
};