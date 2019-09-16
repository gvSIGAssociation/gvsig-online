/**
 * gvSIG Online.
 * Copyright (C) 2010-2019 SCOLAB.
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
 * @author: José Badía <jbadia@scolab.es>
 * @author: César Marinez <cmartinez@scolab.es>
 */

/**
 * TODO
 */
var CatalogView = function(mapViewer, config) {
	this.mapViewer = mapViewer;
	this.map = mapViewer.getMap();
	this.map_container = $("#container");	
	this.layerTree = mapViewer.getLayerTree();
	this.catalog_panel = null;
	this.catalog_map = null;
	this.data = {};
	this.config = config || {} ;
	this.config.facetsConfig = this.config.facetsConfig || {};
	this.config.facetsOrder = this.config.facetsOrder || [];
	this.config.disabledFacets = this.config.disabledFacets || [];
	
	var self = this;
	$('body').on('change-to-2D-event', function() {
		self.hidePanel();
	});
	
	$('body').on('change-to-3D-event', function() {
		self.hidePanel();
	});
	
};

CatalogView.prototype.initialization = function(){
	var self = this;
	var filters = this.getCatalogFilters("");

	var catalogPanel = '';
	catalogPanel += '<div id="catalog_container">';

	catalogPanel += '<div id="catalog_search_full" class="row">';
	catalogPanel += '	<div id="catalog_map_search" class="col-md-3">';
	catalogPanel += '		<div id="catalog_map_full">';
	catalogPanel += '			<div id="catalog_map" class="catalog_map"></div>';
	catalogPanel += '			<p class="catalog_map_text">' + gettext('Press Ctrl to mark an area') + '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a id="catalog_map_clean" href="#">' + gettext('Clean') + '</a></p>';
	catalogPanel += '		</div>';
	catalogPanel += '	</div>';
	catalogPanel += '	<div id="catalog_search" class="col-md-7">';
	catalogPanel += '		<div class="row">';
	catalogPanel += '			<div class="col-md-offset-1 col-md-10 relative">';
	catalogPanel += '				<div class="input-group gn-form-any">';
	catalogPanel += '					<input type="text" class="form-control input-lg" id="gn-any-field" placeholder="' + gettext('Search...') + '" data-typeahead="address for address in getAnySuggestions($viewValue)" data-typeahead-loading="anyLoading" data-typeahead-min-length="1" data-typeahead-focus-first="false" data-typeahead-wait-ms="300" aria-autocomplete="list" aria-expanded="false" aria-owns="typeahead-310-2994">';

	catalogPanel += '					<div class="input-group-btn">';
	catalogPanel += '						<button id="catalog-search-advanced-button" type="button" class="btn btn-default btn-lg ng-pristine ng-untouched ng-valid ng-not-empty" data-ng-model="searchObj.advancedMode" btn-checkbox="" btn-checkbox-true="1" btn-checkbox-false="0">';
	catalogPanel += '							<i class="fa fa-ellipsis-v"></i>';
	catalogPanel += '						</button>';

	catalogPanel += '						<button id="catalog-search-button" type="button" class="btn btn-primary btn-lg">';
	catalogPanel += '							&nbsp;&nbsp;';
	catalogPanel += '							<i class="fa fa-search"></i>';
	catalogPanel += '							&nbsp;&nbsp;';
	catalogPanel += '						</button>';
	catalogPanel += '						<button id="catalog-clear-button" type="button" title="' + gettext('Clean current search, filters and order') + '" class="btn btn-link btn-lg">';
	catalogPanel += '							<i class="fa fa-times"></i>';
	catalogPanel += '						</button>';
	catalogPanel += '					</div>';
	catalogPanel += '				</div>';
	catalogPanel += '			</div>';
	catalogPanel += '			<div class="col-lg-3">';
	catalogPanel += '			</div>';
	catalogPanel += '		</div>';
	catalogPanel += '	</div>';
	if (viewer.core.getDownloadManager().isManagerEnabled()) {
		catalogPanel += '	<div id="catalog_download_list_btn" class="col-md-1 catalog-download-list-btn">';
		catalogPanel += '		<div class="input-group"><span class="form-control  input-lg"><span class="download_list_count">0</span><i class="fa fa-shopping-cart fa-icon-button-right"></i></span>';
		catalogPanel += '		</div>';
		catalogPanel += '	</div>';
	}
	catalogPanel += '	<div id="catalog_search_advanced" class="row">';
	catalogPanel += '		<div class="catalog_search_advanced_col col-md-4">';
	catalogPanel += '			<div class="">';
	catalogPanel += '				<div class="btn-group btn-group-xs">';
	catalogPanel += '					<span data-translate="" class="ng-scope ng-binding"><strong>' + gettext('Categories') + '</strong>';
	catalogPanel += '				</div>';
	catalogPanel += '				<br>';
	catalogPanel += '				<input type="text" id="categoriesF" placeHolder="' + gettext('Separated by') + ' \';\'    P.ej: cat_1;cat_2;..." value="" class="form-control"/>';
	catalogPanel += '			</div>';
	catalogPanel += '			<div class="">';
	catalogPanel += '				<div class="btn-group btn-group-xs">';
	catalogPanel += '					<span data-translate="" class="ng-scope ng-binding"><strong>' + gettext('Keywords') + '</strong>';
	catalogPanel += '				</div>';
	catalogPanel += '				<br>';
	catalogPanel += '				<input type="text" id="keywordsF" placeHolder="' + gettext('Separated by') + ' \';\'    P.ej: cat_1;cat_2;..." value="" class="form-control"/>';
	catalogPanel += '			</div>';
	catalogPanel += '			<div class="">';
	catalogPanel += '				<div class="btn-group btn-group-xs">';
	catalogPanel += '					<span data-translate="" class="ng-scope ng-binding"><strong>' + gettext('Contact for the resource') + '</strong>';
	catalogPanel += '				</div>';
	catalogPanel += '				<br>';
	catalogPanel += '				<input type="text" id="orgNameF" placeHolder="' + gettext('Separated by') + ' \';\'    P.ej: cat_1;cat_2;..." value="" class="form-control"/>';
	catalogPanel += '			</div>';
	catalogPanel += '		</div>';
	catalogPanel += '		<div class="catalog_search_advanced_col col-md-4">';
	catalogPanel += '			<div data-gn-period-chooser="resourcesCreatedTheLast" data-date-from="searchObj.params.creationDateFrom" data-date-to="searchObj.params.creationDateTo" class="ng-isolate-scope">';
	catalogPanel += '				<div class="btn-group btn-group-xs">';
	catalogPanel += '					<span data-translate="" class="ng-scope ng-binding"><strong>' + gettext('Resources') + '</strong>';
	catalogPanel += '				</div>';
	catalogPanel += '				<br>';
	catalogPanel += '				<div class="row">';
	catalogPanel += '					<div class="col-md-6">';
	catalogPanel += '						<input id="catalog_resource_from" placeholder="' + gettext('From...') + '" data-provide="datepicker" class="form-control" data-date-format="yyyy-mm-dd" value="">';
	catalogPanel += '					</div>';
	catalogPanel += '					<div class="col-md-6">';
	catalogPanel += '						<input id="catalog_resource_to" placeholder="' + gettext('To...') + '" data-provide="datepicker" class="form-control" data-date-format="yyyy-mm-dd" value="">';
	catalogPanel += '					</div>';
	catalogPanel += '				</div>';
	catalogPanel += '				<div class="btn-group btn-group-xs">';
	catalogPanel += '					<span data-translate="" class="ng-scope ng-binding"><strong>' + gettext('Records') + '</strong>';
	catalogPanel += '				</div>';
	catalogPanel += '				<br>';
	catalogPanel += '				<div class="row">';
	catalogPanel += '					<div class="col-md-6">';
	catalogPanel += '						<input id="catalog_register_from" placeholder="' + gettext('From...') + '" data-provide="datepicker" class="form-control" data-date-format="yyyy-mm-dd" value="">';
	catalogPanel += '					</div>';
	catalogPanel += '					<div class="col-md-6">';
	catalogPanel += '						<input id="catalog_register_to" placeholder="' + gettext('To...') + '" data-provide="datepicker" class="form-control" data-date-format="yyyy-mm-dd" value="">';
	catalogPanel += '					</div>';
	catalogPanel += '				</div>';
	catalogPanel += '			</div>';
	catalogPanel += '		</div>';
	catalogPanel += '	</div>';
	catalogPanel += '</div>';


	catalogPanel += '<div class="col-md-3" id="catalog_filter">';
	catalogPanel += '</div>';

	catalogPanel += '<div class="col-md-9" id="catalog_content">';
	catalogPanel += '</div>';


	catalogPanel += '</div>';
	$("body").append(catalogPanel);

	this.catalog_panel = $("#catalog_container");


	$("#catalog-search-button").unbind("click").click(function(){
		self.filterCatalog();
	});
	
	$("#gn-any-field").off("keypress").on("keypress", function(e){
		if(e.keyCode == 13) {
			self.filterCatalog();
		}
	});

	$("#catalog-search-advanced-button").unbind("click").click(function(){
		$("#catalog_search_advanced").toggle();
		$("#catalog_map_full").toggle(); 
	});

	$("#catalog-clear-button").unbind("click").click(function(){
		$("#gn-any-field").val("");
		$("#categoriesF").val("");
		$("#keywordsF").val("");
		$("#orgNameF").val("");
		$("#catalog_resource_from").val("");
		$("#catalog_resource_to").val("");
		$("#catalog_register_from").val("");
		$("#catalog_register_to").val("");
		self.catalog_map.cleanData();
		self.launchQuery();
	});

	$("#catalog_map_clean").unbind("click").click(function(){
		self.catalog_map.cleanData();
		self.filterCatalog();
	});
}

CatalogView.prototype.filterCatalog = function(){
	var searchTerms = $("#gn-any-field").val().split(" ");
	var search = '';
	for (var i=0; i<searchTerms.length; i++) {
		// add wildcards to search for partial terms
		if (searchTerms[i] != "") {
			search += searchTerms[i]+"* ";
		}
	}
	var categories = $("#categoriesF").val();
	var keywords = $("#keywordsF").val();
	var resources = $("#orgNameF").val();
	var creation_from = $("#catalog_resource_from").val();
	var creation_to = $("#catalog_resource_to").val();
	var date_from = $("#catalog_register_from").val();
	var date_to = $("#catalog_register_to").val();
	var extent = this.catalog_map.getSelectedArea();
	this.launchQuery(search, categories, keywords, resources, creation_from, creation_to, date_from, date_to, extent);

}

CatalogView.prototype.launchQuery = function(search, categories, keywords, resources, creation_from, creation_to, date_from, date_to, extent){
	var query = "";
	var is_first = true;
	$(".catalog_filter_entry_ck").each(function(){
		if($(this).is(':checked')){
			if(!is_first){
				query += "%26";
			}
			query += $(this).attr("name");
			is_first = false;
		}

	});
	this.getCatalogFilters(query, search, categories, keywords, resources, creation_from, creation_to, date_from, date_to, extent);
}

CatalogView.prototype.getCatalogEntry = function(query, cat, entry, filterName){
	var entry_name;
	if (filterName) {
		entry_name = filterName + '%2F' + encodeURIComponent(encodeURIComponent(entry['@value']));
	}
	else {
		entry_name = cat['@name'] + '%2F' + encodeURIComponent(encodeURIComponent(entry['@value']));
	}
	var checked = "";
	var selected = "";
	if(query.includes(entry_name)){
		checked = " checked";
		selected = " catalog_filter_entry_ck_sel"
	}

	return '<div class="catalog_filter_entry' + selected + '"><input ' + checked + ' type="checkbox" class="catalog_filter_entry_ck" name="'+ entry_name + '"/>&nbsp;&nbsp;&nbsp;'+ entry['@label'] + ' (' + entry['@count'] +')</div>';
}

CatalogView.prototype.getFilterEntry = function(query, cat, filterTitle, filterName){
	var filter_code = '<ul class="catalog_filter_cat">'+
	'<li class="box box-default" style="list-style-type: none;">'+	
	'<div class="box-header with-border catalog_filter_title">'+
	'<span class="text">'+ 
	filterTitle +
	'</span>'+
	'<div class="box-tools pull-right">'+
	'<button class="btn btn-box-tool btn-box-tool-custom" data-widget="collapse">'+
	'<i class="fa fa-minus"></i>'+
	'</button>'+
	'</div>'+
	'</div>'+
	'<div id="baselayers-group" class="box-body" style="display:block">';
	if('category' in cat && Array.isArray(cat.category) && cat.category.length > 0){
		for(var idx = 0; idx < cat.category.length; idx++){
			var entry = cat.category[idx];
			filter_code += this.getCatalogEntry(query, cat, entry, filterName);
		}
	}
	if('category' in cat && '@value' in cat.category){
		var entry = cat.category;
		filter_code += this.getCatalogEntry(query, cat, entry, filterName);
	}
	filter_code += '</div></li></ul>';
	return filter_code;
}

CatalogView.prototype.applyPatternBasedCategories = function(entry, config, subcategories){
	for(var idx = 0; idx < config.length; idx++){
		var currentConf = config[idx];
		if (currentConf['labelPattern'] && entry['@label'].match(config[idx]['labelPattern'])) {
			if (!subcategories[currentConf['name']]) {
				subcategories[currentConf['name']] = {"@name": currentConf['name'], "@label": currentConf['title'], "category": []};
			}
			subcategories[currentConf['name']]["category"].push(entry);
		}
	}
}

CatalogView.prototype.getPatternBasedCategories = function(cat, config){
	var subCategories = {};
	if('category' in cat && Array.isArray(cat.category) && cat.category.length > 0){
		for(var idx = 0; idx < cat.category.length; idx++){
			var entry = cat.category[idx];
			this.applyPatternBasedCategories(entry, config, subCategories);
		}
	}
	else if('category' in cat && '@value' in cat.category){
		var entry = cat.category;
		this.applyPatternBasedCategories(entry, config, subCategories);
	}
	return subCategories;
}

CatalogView.prototype.getMetadataEntry = function(metadata){
	var met = '';
	if(metadata){
		var title = metadata['defaultTitle'] || '';
		var abstract = metadata['abstract'] || '';
		met += '<div class="catalog_content_layer col-md-6">';
		met += '	<div class="col-md-9">';
		met += '		<p class="catalog_content_title block-with-text">'+ title +'</p>';
		met += '		<p class="catalog_content_abstract block-with-text">'+ abstract +'</p>';
		met += '	</div>';
		met += '	<div class="col-md-3 catalog_content_lateral">';
		met += '		<div class="catalog_content_thumbnail">';

		var image_src = "";
		if("image" in metadata){
			var image = metadata["image"];
			if(!Array.isArray(image)){
				image = [image];
			}
			for(var i=0; i< image.length; i++){
				var image_info = image[i].split("|");
				if (image_info[1] && // we want to avoid relative URLs for images
						(image_info[1].lastIndexOf("http://", 0) === 0 || image_info[1].lastIndexOf("https://", 0) === 0)) {
					image_src = image_info[1];
				}
				break;
			}
		}
		met += '			<img src="'+image_src+'" style="width:100%;"/>';
		met += '		</div>';
		met += '	</div>';
		met += '	<div class="col-md-12">';
		met += '			<div class="catalog_content_button_place col-md-4">';
		met += '				<a name="'+ metadata['geonet:info']['uuid'] +'" href="#" class="btn btn-block btn-social btn-custom-tool catalog_content_button catalog_details">';
		met += ' 					<i class="fa fa-search" aria-hidden="true"></i>' + gettext('Details');
		met += '				</a>';
		met += '			</div>';
		met += '			<div class="catalog_content_button_place col-md-4">';
		met += '				<a name="'+ metadata['geonet:info']['uuid'] +'" href="#" class="btn btn-block btn-social btn-custom-tool catalog_content_button catalog_linkmap">';
		met += ' 					<i class="fa fa-map-o" aria-hidden="true"></i>' + gettext('Map');
		met += '				</a>';
		met += '			</div>';
		met += '			<div class="catalog_content_button_place col-md-4">';
		met += '				<a name="'+ metadata['geonet:info']['uuid'] +'" href="#" class="btn btn-block btn-social btn-custom-tool catalog_content_button catalog_download">';
		met += ' 					<i class="fa fa-download" aria-hidden="true"></i>' + gettext('Download');
		met += '				</a>';
		met += '			</div>';
		met += '	</div>';
		met += '</div>';
	}else{
		met += '<div class="no_catalog_content col-md-12">';
		met += '<i class="fa fa-ban" aria-hidden="true"></i>   ';
		met += 	gettext('No results found');
		met += '</div>';
	}
	return met;
}

CatalogView.prototype.getKeywordQuery = function(keywords, key){
	var cat_array = keywords.split(";");
	var cats = "";
	for(var i=0; i<cat_array.length; i++){
		if(i==0){
			cats += "&"+key+"=";
		}else{
			cats += " or ";
		}
		cats += cat_array[i];
	}
	cats = cats.replace(new RegExp(' ', 'g'), '+');
	return cats;
}

CatalogView.prototype.createResourceLink = function(links){
	var link = links.split('|');
	var content = '';
	if(link.length==6){
		var type = link[4].trim();
		var link_url = link[2];
		var layer_name = link[0];
		var layer_title = link[1];
		if(type == "OGC:WFS"){
			var shapeLink = link_url + '?service=WFS&request=GetFeature&version=1.0.0&outputFormat=shape-zip&typeName=' + layer_name;
			var gmlLink = link_url + '?service=WFS&version=1.1.0&request=GetFeature&outputFormat=GML3&typeName=' + layer_name;
			var csvLink = link_url + '?service=WFS&version=1.1.0&request=GetFeature&outputFormat=csv&typeName=' + layer_name;
			content += '<li class="catalog-link">';
			content += '<div class="row">';
			content += '<div class="col-md-4 form-group">';	
			content +=   '<i class="fa fa-file-archive-o" aria-hidden="true"></i>';
			content +=   '<span class="catalog-link-resource"><p>' + layer_title + '<br/><span class="catalog-entry-subtitle">' + layer_name + '</span></p></span>';
			content += '</div>';
			content += 	'<div class="col-md-2 form-group">';	
			content += 		'<a href="' + shapeLink + '"><div class="download-btn"><i style="margin-right: 10px;" class="fa fa-download"></i>' + gettext('Download ShapeFile') + '</div></a>';
			content += 	'</div>';
			content += 	'<div class="col-md-2 form-group">';	
			content += 		'<a href="' + csvLink + '"><div class="download-btn"><i style="margin-right: 10px;" class="fa fa-download"></i>' + gettext('Download CSV') + '</div></a>';
			content += 	'</div>';
			content += 	'<div class="col-md-2 form-group">';	
			content += 		'<a target="_blank" href="' + gmlLink + '"><div class="download-btn"><i style="margin-right: 10px;" class="fa fa-download"></i>' + gettext('Download GML') + '</div></a>';
			content += 	'</div>';
			content += '</div>';
			content += '</li>';
		} else if(type == "OGC:WCS"){
			var wcs_link = link_url + '?service=WCS&version=2.0.0&request=GetCoverage&CoverageId='+layer_name;
			content += '<li class="catalog-link">';
			content += '<div class="row">';
			content += '<div class="col-md-4 form-group">';	
			content +=   '<i class="fa fa-file-archive-o" aria-hidden="true"></i>';
			content +=   '<span class="catalog-link-resource"><p>' + layer_title + '<br/><span class="catalog-entry-subtitle">' + layer_name + '</span></p></span>';
			content += '</div>';
			content += 	'<div class="col-md-2 form-group">';	
			content += 		'<a href="' + wcs_link + '"><div class="download-btn"><i style="margin-right: 10px;" class="fa fa-download"></i>' + gettext('Access raster data') + '</div></a>';
			content += 	'</div>';
			content += '</div>';
			content += '</li>';
		}
		else if(type.startsWith("text/") || type == 'application/zip' || type == 'application/pdf'){
			content += '<li class="catalog-link">';
			content += '<div class="row">';
			content += '<div class="col-md-6 form-group">';	
			content +=   '<i class="fa fa-file-archive-o" aria-hidden="true"></i>';
			content +=   '<span class="catalog-link-resource"><p>' + layer_title + '<br/><span class="catalog-entry-subtitle">' + layer_name + '</span></p></span>';
			content += '</div>';
			content += 	'<div class="col-md-2 form-group">';	
			content += 		'<a href="' + link_url + '"><div class="download-btn"><i style="margin-right: 10px;" class="fa fa-download"></i>' + gettext('Access resource') + '</div></a>';
			content += 	'</div>';
			content += '</div>';
			content += '</li>';
		}
	}
	return content;
}

CatalogView.prototype.linkResourceMap = function(){
	var self = this;

	$(".catalog_add_layer").unbind("click").click(function(){
		var url = $(this).attr("url");
		var name = $(this).attr("name");
		var title = $(this).attr("title");
		var id = $(this).attr("data-id");

		var group_visible = false;
		group_visible = $("#layergroup-geonetwork-group").is(":checked");
		try {
			self.createLayer(name, title, url, id, null, group_visible);
		}
		catch (error) {
			console.log(error);
		}
		$('#modal-catalog').modal('hide');
		self.hidePanel();
	});
}


CatalogView.prototype.createLayerGroup = function() {
	var self = this;
	var groupId = 'gvsigol-geonetwork-group';

	var tree = '';
	tree += '			<li class="box box-default collapsed-box" id="' + groupId + '">';
	tree += '				<div class="box-header with-border">';
	tree += '					<input type="checkbox" class="layer-group" id="layergroup-' + groupId + '">';
	tree += '					<span class="text">' + gettext("Catalog layers") + '</span>';
	tree += '					<div class="box-tools pull-right">';
	tree += '						<button class="btn btn-box-tool btn-box-tool-custom group-collapsed-button" data-widget="collapse">';
	tree += '							<i class="fa fa-plus"></i>';
	tree += '						</button>';
	tree += '					</div>';
	tree += '				</div>';
	tree += '				<div data-groupnumber="' + (100 * 100) + '" class="box-body layer-tree-groups geonetwork-layer-group" style="display: none;">';
	tree += '				</div>';
	tree += '			</li>';

	$(".layer-tree").append(tree);
	
	$("#layergroup-gvsigol-geonetwork-group").unbind("change").change(function (e) {
		var groupId = 'layergroup-geonetwork-group'; 
		var checked = this.checked;

		$("#gvsigol-geonetwork-group").find(".layer-box").each(function(idx, el) {
			var id = el.getAttribute("data-layerid");
			var layerCheckbox = document.getElementById(id);
			var layers = self.map.getLayers();
			layers.forEach(function(layer){
				if (!layer.baselayer && !layer.external) {
					if (layer.get("id") === id) {
						var layerCheckbox = document.getElementById(id);
						if (checked) {
							layer.setVisible(true);
							layerCheckbox.checked = true;
							layerCheckbox.disabled = true;
						} else {
							layer.setVisible(false);
							layerCheckbox.checked = false;
							layerCheckbox.disabled = false;
						}
					}
				}
			});
		});
	});
}


CatalogView.prototype.reorder = function(event,ui) {
	var groupNumber = ui.item[0].parentNode.dataset.groupnumber;
	var groupLayers = ui.item[0].parentNode.children;
	var mapLayers = this.map.getLayers();

	var zindex = parseInt(groupNumber);
	var mapLayers_length = mapLayers.getLength();

	for (var i=0; i<groupLayers.length; i++) {
		var layerid = groupLayers[i].dataset.layerid;
		mapLayers.forEach(function(layer){
			if (layer.get('id') == layerid) {
				layer.setZIndex(parseInt(zindex) + mapLayers_length);
				mapLayers_length--;
			}
		}, this);
	}
};

CatalogView.prototype._createOLLayer = function(url, name, title, dataId, bbox, wfs_url, wcs_url) {
	var self = this;
	
	if (url.endsWith("?")) {
		url = url.substring(0, url.length-1);
	}
	
	var catalogLayer = new ol.layer.Tile({
		source: new ol.source.TileWMS({
			url: url,
			params: {
				'LAYERS': name, 
				'TILED': true, 
				'dataid': dataId
			},
			serverType: 'geoserver'
		}),
		id: dataId
	});
	catalogLayer.baselayer = false;
	catalogLayer.dataid = dataId;
	catalogLayer.id = dataId;
	catalogLayer.layer_name = name;
	catalogLayer.legend = url + '?SERVICE=WMS&VERSION=1.1.1&layer=' + name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on';
	catalogLayer.queryable = true;
	catalogLayer.title = title;
	catalogLayer.visible = true;
	catalogLayer.allow_download = true;
	catalogLayer.wms_url = url;
	catalogLayer.metadata = '';
	if (wcs_url) {
		catalogLayer.wcs_url = wcs_url;
	}
	if (wfs_url) {
		catalogLayer.wfs_url = wfs_url;
	}
	if (bbox != null && bbox.length>0) {
		catalogLayer.bboxwgs84 = bbox;		
	}
	catalogLayer.on('change:visible', function(){
		self.mapViewer.getLegend().reloadLegend();
	});

	self.map.addLayer(catalogLayer);
	return catalogLayer;
}



CatalogView.prototype.createLayer = function(name, title, url, dataId, bbox, group_visible, wfs_url, wcs_url) {
	var self = this;
	var newLayer = self._createOLLayer(url, name, title, dataId, bbox, wfs_url, wcs_url);
	
	var groupId = "gvsigol-geonetwork-group";
	var groupEntry = $("#"+groupId);
	var zIndex = groupEntry.length;
	if(zIndex == 0){
		self.createLayerGroup();
	}

	var layerTree = self.mapViewer.getLayerTree();
	
	var removeLayerButtonUI = '<a id="remove-catalog-layer-' + dataId + '" data-layerid="' + dataId + '" class="btn btn-block btn-social btn-custom-tool remove-catalog-layer-btn">';
	removeLayerButtonUI +=    '	<i class="fa fa-times"></i> ' + gettext('Remove layer');
	removeLayerButtonUI +=    '</a>';
	
	var newLayerUI = $(layerTree.createOverlayUI(newLayer, $("#layergroup-"+groupId).is(":checked")));
	newLayerUI.find(".box-body .zoom-to-layer").after(removeLayerButtonUI);
	$(".geonetwork-layer-group").append(newLayerUI);
	layerTree.setLayerEvents();
	
	$(".show-metadata-link").unbind("click").on('click', function(e) {
		var layers = self.map.getLayers();
		var selectedLayer = null;
		var layerContainer = $(this).parents('.layer-box');
		var id = layerContainer.first().attr("data-layerid");
		layers.forEach(function(layer){
			if (!layer.baselayer && !layer.external) {
				if (id===layer.get("id")) {
					selectedLayer = layer;
					var dataid = selectedLayer.getSource().getParams()["dataid"];
					if (dataid) {
						// layer was created from catalog, it may not be registerd on gvSIGOL
						self.createDetailsPanel(selectedLayer.getSource().getParams()["dataid"]);
					}
					else {
						// normal layer, we can use the layer tree methods
						viewer.core.layerTree.showMetadata(selectedLayer);
					}
				}
			}
		}, this);
	});
	

	$(".remove-catalog-layer-btn").unbind("click").click(function (e) {
		var id = $(this).attr("data-layerid");
		var layers = self.map.getLayers();
		layers.forEach(function(layer){
			if (!layer.baselayer && !layer.external) {
				if (layer.get("id") === id) {
					layer.setVisible(false);
					self.map.removeLayer([layer]);
					$("#layer-box-" + id).remove();
				}
			};
		}, this);
	});
	
	self.mapViewer.getLegend().reloadLegend();
};
/*
CatalogView.prototype.zoomToLayer = function(layer) {
	var self = this;
	if (layer.bboxwgs84) { // use extent from metadata if available
		var extent = ol.proj.transformExtent(layer.bboxwgs84, ol.proj.get('EPSG:4326'), ol.proj.get('EPSG:3857'));
		self.map.getView().fit(extent, self.map.getSize());
	}
	else { // query getCapabilities otherwise
		var layer_name = layer.get("id").replace("geonetwork-", "");
	
		var url = layer.getSource().urls[0]+'?request=GetCapabilities&service=WMS';
		var parser = new ol.format.WMSCapabilities();
		$.ajax(url).then(function(response) {
			var result = parser.read(response);
			var Layers = result.Capability.Layer.Layer; 
			var extent;
			for (var i=0, len = Layers.length; i<len; i++) {
				var layerobj = Layers[i];
				//if (layerobj.Name == layer_name) {
				extent = layerobj.EX_GeographicBoundingBox;
				break;
				//}
			}
			if((extent[0]==0 && extent[1]==0 && extent[2]==-1 && extent[3]==-1 )||
					(extent[0]==-1 && extent[1]==-1 && extent[2]==0 && extent[3]==0 )){
				return;
			}
			var ext = ol.proj.transformExtent(extent, ol.proj.get('EPSG:4326'), ol.proj.get('EPSG:3857'));
			self.map.getView().fit(ext, self.map.getSize());
		});
	}
}*/

CatalogView.prototype.getCatalogFilters = function(query, search, categories, keywords, resources, creation_from, creation_to, date_from, date_to, extent){
	var self = this;
	var filters = ""
		if(search && search.length > 0){
			filters += "&any="+search;
		}
	if(resources && resources.length > 0){
		filters += this.getKeywordQuery(resources, "orgName");
	}
	if(keywords && keywords.length > 0){
		filters += this.getKeywordQuery(keywords, "keyword");
	}
	if(categories && categories.length > 0){
		filters += this.getKeywordQuery(categories, "_cat");
	}
	if(creation_from && creation_from.length > 0){
		filters += "&creationDateFrom="+creation_from;
	}
	if(creation_to && creation_to.length > 0){
		filters += "&creationDateTo="+creation_to;
	}
	if(date_from && date_from.length > 0){
		filters += "&dateFrom="+date_from;
	}
	if(date_to && date_to.length > 0){
		filters += "&dateTo="+date_to;
	}
	if(extent && extent.length > 0){
		filters += "&geometry="+extent;
	}
	
	var facetsConfig = self.config.facetsConfig;
	var facetsOrder = self.config.facetsOrder;
	var disabledFacets = self.config.disabledFacets;
	
	var url;
	if (self.config.queryUrl) {
		url = self.config.queryUrl;
	}
	else {
		url = '/geonetwork/srv/eng/q';
	}
	// TODO: authentication
	url = url + '?_content_type=json' + filters + '&bucket=s101&facet.q=' + query + '&fast=index&from=1&resultType=details&sortBy=relevance';
	//var url = '/gvsigonline/catalog/get_query/?_content_type=json&bucket=s101&facet.q='+query+'&fast=index&from=1&resultType=details&sortBy=relevance';
	$.ajax({
		url: url,
		success: function(response) {
			try{
				//response = JSON.parse(response);
				self.data = {};

				var all_filters_code = '';
				var shownFilters = {};
				for(var idx = 0; idx < response.summary.dimension.length; idx++){
					var cat = response.summary.dimension[idx];
					if('category' in cat && '@label' in cat && '@name' in cat && !(disabledFacets.includes(cat['@name']))) {
						if (Array.isArray(facetsConfig[cat['@name']])) { // pattern based configuration
							var subFilters = self.getPatternBasedCategories(cat, facetsConfig[cat['@name']]);
							for(var subFilterName in subFilters){
								var subFilter = subFilters[subFilterName];
								shownFilters[subFilter['@name']] = self.getFilterEntry(query, subFilter, subFilter['@label'], cat['@name']);
							}
						}
						else {
							if (facetsConfig[cat['@name']]) {
								var filterLabel = facetsConfig[cat['@name']]['title'];
							}
							else {
								var filterLabel = cat['@label'];
							}
							shownFilters[cat['@name']] = self.getFilterEntry(query, cat, filterLabel);
						}
					}
				}
				// insert filters in defined order
				for(var idx = 0; idx < facetsOrder.length; idx++){
					if (shownFilters[facetsOrder[idx]]) {
						all_filters_code += shownFilters[facetsOrder[idx]];
						delete shownFilters[facetsOrder[idx]];
					}
				}
				// insert the rest of filters
				for (var filterName in shownFilters) {
					all_filters_code += shownFilters[filterName];
				}

				$("#catalog_filter").html(all_filters_code);


				var content_code = '';
				if(Array.isArray(response.metadata)){
					for(var idx = 0; idx < response.metadata.length; idx++){
						var metadata = response.metadata[idx];
						content_code += self.getMetadataEntry(metadata);
						self.data[metadata['geonet:info']['uuid']] = metadata;
					}
				}else{
					var metadata = response.metadata;
					content_code += self.getMetadataEntry(metadata);
					if (metadata) {
						self.data[metadata['geonet:info']['uuid']] = metadata;	
					}
					else {
						self.data = {};
					}
					
				}
				$("#catalog_content").html(content_code);


				$(".catalog_details").unbind("click").click(function(){
					var id = $(this).attr("name");
					self.createDetailsPanel(id);

				});

				if (viewer.core.getDownloadManager().isManagerEnabled()) {
					$(".catalog-download-list-btn").unbind("click").click(function(){
						// we will use a different modal so we create a new clientUI
						var ui = new DownloadManagerUI('#modal-catalog', viewer.core.getDownloadManager().getClient());
						//viewer.core.getDownloadManager().initDownloadList($('.modal-catalog-content'));
						ui.initDownloadList();
						$('#modal-catalog').modal('show');
						setTimeout(function() {
							$(ui.modalSelector).LoadingOverlay("hide");
						}, ui.getClient().config.timeout);

					});
				}

				$(".catalog_download").unbind("click").click(function(){
					var id = $(this).attr("name");
					if (viewer.core.getDownloadManager().isManagerEnabled()) {
						// we will use a different modal so we create a new clientUI
						var ui = new DownloadManagerUI('#modal-catalog', viewer.core.getDownloadManager().getClient());
						ui.layerDownloads(id);
					}
					else {
						$('#modal-catalog .modal-title').html(gettext("List of downloads"));
						var links = self.data[id].link;
						var content = "<ul>";
						var aux_content = "";
						if(Array.isArray(links)){
							for(var i=0; i<links.length; i++){
								aux_content += self.createResourceLink(links[i]);
							}
						}else{
							if(links){
								aux_content += self.createResourceLink(links);
							}
						}
						content += aux_content + "</ul>";
	
						if(aux_content.length == 0){
							aux_content += '<div style="padding: 10px">';
							aux_content += '<div class="no_catalog_content col-md-12">';
							aux_content += '<i class="fa fa-ban" aria-hidden="true"></i>   ';
							aux_content += gettext('No results found');
							aux_content += '</div>';
							aux_content += '<div style="clear:both"></div>';
							aux_content += '</div>';
	
							content = aux_content;
						}
	
						$('#modal-catalog .modal-body').html(content);
						$('#modal-catalog').modal('show');
					}
				});

				$(".catalog_linkmap").unbind("click").click(function(){
					var id = $(this).attr("name");

					var links = self.data[id].link;
					try {
						var geoBox = [];
						if (self.data[id].geoBox) {
							if (Array.isArray(self.data[id].geoBox)) {
								// TODO: merge all the bboxes in this case
								var geoBoxStrList = self.data[id].geoBox[0].split("|");
							}
							else {
								var geoBoxStrList = self.data[id].geoBox.split("|");
							}
							for (var i=0; i<geoBoxStrList.length; i++) {
								var bboxValue = parseFloat(geoBoxStrList[i]);
								geoBox.push(bboxValue);
							}
						}
					}
					catch (e) {}
					if(!Array.isArray(links)){
						links = [links];
					}
					var wms = {};
					var wcs_url = '';
					var wfs_url = '';
					for(var i=0; i<links.length; i++){
						var link = links[i].split('|');
						var content = '';
						if(link.length==6){
							var type = link[3].trim().substring(0, 7);
							if(type == "OGC:WMS"){
								wms.url = link[2];
								wms.name = link[0];
								wms.title = link[1];
								if (wms.title=="") {
									wms.title = self.data[id].title;
								}
								if (wms.title=="") {
									wms.title = name;
								}
							}
							else if (type == "OGC:WFS"){
								wfs_url = link[2];
							}
							else if (type == "OGC:WCS"){
								wcs_url = link[2];
							}
						}
					}
					if (wms.url) {
						var group_visible = false;
						group_visible = $("#layergroup-geonetwork-group").is(":checked");
						try {
							self.createLayer(wms.name, wms.title, wms.url, id, geoBox, group_visible, wfs_url, wcs_url);
						}
						catch(error) {
							console.log(error);
						}
						
						self.hidePanel();
					}
				});

				$(".catalog_filter_entry_ck").unbind("click").click(function(){
					var search = $("#gn-any-field").val();
					var categories = $("#categoriesF").val();
					var keywords = $("#keywordsF").val();
					var resources = $("#orgNameF").val();
					self.launchQuery(search, categories, keywords, resources);
				})

			} catch (e) {
				console.log(e);
			}
		},
		error: function(jqXHR, textStatus) {
			console.log(textStatus);
			console.log(jqXHR);
			content_code = self.getMetadataEntry(null);
			$("#catalog_content").html(content_code);
		}
	});
}

CatalogView.prototype.createDetailsPanel = function(id){
	var self = this;
	$.ajax({
		type: "GET",
		async: false,
		url: "/gvsigonline/catalog/get_metadata/"+id,
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		success: function(response){
			if ("html" in response) {
				$('#modal-catalog .modal-title').html(gettext("Details"));
				$('#modal-catalog .modal-body').html(response['html']);
				$('#modal-catalog .modal-footer').html("");
				$('#modal-catalog').modal('show');
			} else {
				alert('Error');
			}

		},
		error: function(jqXHR, textStatus){
			console.log(textStatus);
			console.log(jqXHR);
		}
	});
}

CatalogView.prototype.showPanel = function(){
	if (this.catalog_panel===null) {
		this.initialization();
	}
	this.catalog_panel.show();
	this.map_container.hide();
	$('.viewer-search-form').css("display","none");
	if(!this.catalog_map){
		this.catalog_map = new CatalogMap(this, "catalog_map");
	}
}

CatalogView.prototype.hidePanel = function(){
	this.map_container.show();
	if (this.catalog_panel) {
		this.catalog_panel.hide();
	}
	$('.viewer-search-form').css("display","inline-block");
}

