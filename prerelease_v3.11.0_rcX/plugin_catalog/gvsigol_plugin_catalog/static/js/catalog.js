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
 * @author: César Martinez <cmartinez@scolab.es>
 */

/**
 * TODO
 */
var CatalogView = function(mapViewer, config) {
	this.mapViewer = mapViewer;
	this.map = mapViewer.getMap();
	this.map_container = $("#container");
	this.modalSelector = config.modalSelector || '#float-modal';
	this.layerTree = mapViewer.getLayerTree();
	this.catalog_panel = null;
	this.catalog_map = null;
	this.data = {};
	this.config = config || {} ;
	this.config.facetsConfig = this.config.facetsConfig || {};
	this.config.facetsOrder = this.config.facetsOrder || [];
	this.config.disabledFacets = this.config.disabledFacets || [];
	this.config.resultsPerPage = this.config.resultsPerPage || 20;
	this.config.searchField = this.config.searchField || 'any';
	this.config.customFiltersConfig = this.config.customFiltersConfig || {};
	this.fromResult = 1;
	this.sortBy = '&sortBy=relevance';
	
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
	var catalogPanel = '';
	catalogPanel += '<div id="catalog_container"><div class="container-fluid">';
	catalogPanel += '	<div id="catalog_search_full" class="row">';
	catalogPanel += '		<div id="catalog_map_search" class="col-sm-5">';
	catalogPanel += '			<div id="catalog_map_full">';
	catalogPanel += '				<div id="catalog_map" class="catalog_map"></div>';
	catalogPanel += '				<div class="checkbox">';
	catalogPanel += '					<label>';
	catalogPanel += '						<input type="checkbox" id="chck_mapareaoverlap" value="mapareaoverlap" checked>';
	catalogPanel += 						gettext('Include only results overlapping with the selected area');
	catalogPanel += '					</label>';
	catalogPanel += '				</div>';
	catalogPanel += '			</div>';
	catalogPanel += '		</div>';
	catalogPanel += '		<div class="col-sm-7">';
	catalogPanel = self.addCustomFilter(catalogPanel);
	catalogPanel += '			<div id="catalog_search"class="row">';
	catalogPanel += '				<div class="col-sm-12">';
	catalogPanel += '					<div class="input-group gn-form-any">';
	catalogPanel += '						<input type="text" class="form-control input-lg" id="gn-any-field" placeholder="' + gettext('Search...') + '" data-typeahead="address for address in getAnySuggestions($viewValue)" data-typeahead-loading="anyLoading" data-typeahead-min-length="1" data-typeahead-focus-first="false" data-typeahead-wait-ms="300" aria-autocomplete="list" aria-expanded="false" aria-owns="typeahead-310-2994">';
	catalogPanel += '						<div class="input-group-btn">';
	catalogPanel += '							<button id="catalog-search-advanced-button" type="button" class="btn btn-default btn-lg ng-pristine ng-untouched ng-valid ng-not-empty" data-ng-model="searchObj.advancedMode" btn-checkbox="" btn-checkbox-true="1" btn-checkbox-false="0">';
	catalogPanel += '								<i class="fa fa-ellipsis-v"></i>';
	catalogPanel += '							</button>';
	catalogPanel += '							<button id="catalog-search-button" type="button" class="btn btn-primary btn-lg">';
	catalogPanel += '								&nbsp;&nbsp;';
	catalogPanel += '								<i id="catalog-search-button-icon" class="fa fa-search"></i>';
	catalogPanel += '								&nbsp;&nbsp;';
	catalogPanel += '							</button>';
	catalogPanel += '							<button id="catalog-clear-button" type="button" title="' + gettext('Clean current search, filters and order') + '" class="btn btn-link btn-lg">';
	catalogPanel += '								<i class="fa fa-times"></i>';
	catalogPanel += '							</button>';
	catalogPanel += '						</div>';
	catalogPanel += '					</div>';
	catalogPanel += '				</div>';
	catalogPanel += '			</div>';
	catalogPanel += '			<div id="catalog_search_advanced" class="row">';
	catalogPanel += '				<div class="catalog_search_advanced_col col-md-4">';
	catalogPanel += '					<div class="">';
	catalogPanel += '						<div class="btn-group btn-group-xs">';
	catalogPanel += '							<span data-translate="" class="ng-scope ng-binding"><strong>' + gettext('Categories') + '</strong>';
	catalogPanel += '						</div>';
	catalogPanel += '						<br>';
	catalogPanel += '						<input type="text" id="categoriesF" placeHolder="' + gettext('Separated by') + ' \';\'	P.ej: cat_1;cat_2;..." value="" class="form-control"/>';
	catalogPanel += '					</div>';
	catalogPanel += '					<div class="">';
	catalogPanel += '						<div class="btn-group btn-group-xs">';
	catalogPanel += '						<span data-translate="" class="ng-scope ng-binding"><strong>' + gettext('Keywords') + '</strong>';
	catalogPanel += '						</div>';
	catalogPanel += '						<br>';
	catalogPanel += '						<input type="text" id="keywordsF" placeHolder="' + gettext('Separated by') + ' \';\'	P.ej: cat_1;cat_2;..." value="" class="form-control"/>';
	catalogPanel += '					</div>';
	catalogPanel += '					<div class="">';
	catalogPanel += '						<div class="btn-group btn-group-xs">';
	catalogPanel += '							<span data-translate="" class="ng-scope ng-binding"><strong>' + gettext('Contact for the resource') + '</strong>';
	catalogPanel += '						</div>';
	catalogPanel += '						<br>';
	catalogPanel += '						<input type="text" id="orgNameF" placeHolder="' + gettext('Separated by') + ' \';\'	P.ej: cat_1;cat_2;..." value="" class="form-control"/>';
	catalogPanel += '					</div>';
	catalogPanel += '				</div>';
	catalogPanel += '				<div class="catalog_search_advanced_col col-md-4">';
	catalogPanel += '					<div data-gn-period-chooser="resourcesCreatedTheLast" data-date-from="searchObj.params.creationDateFrom" data-date-to="searchObj.params.creationDateTo" class="ng-isolate-scope">';
	catalogPanel += '						<div class="btn-group btn-group-xs">';
	catalogPanel += '							<span data-translate="" class="ng-scope ng-binding"><strong>' + gettext('Resources') + '</strong>';
	catalogPanel += '						</div>';
	catalogPanel += '						<br>';
	catalogPanel += '						<div class="row">';
	catalogPanel += '							<div class="col-md-6">';
	catalogPanel += '								<input id="catalog_resource_from" placeholder="' + gettext('From...') + '" data-provide="datepicker" class="form-control" data-date-format="yyyy-mm-dd" value="">';
	catalogPanel += '							</div>';
	catalogPanel += '							<div class="col-md-6">';
	catalogPanel += '								<input id="catalog_resource_to" placeholder="' + gettext('To...') + '" data-provide="datepicker" class="form-control" data-date-format="yyyy-mm-dd" value="">';
	catalogPanel += '							</div>';
	catalogPanel += '						</div>';
	catalogPanel += '						<div class="btn-group btn-group-xs">';
	catalogPanel += '							<span data-translate="" class="ng-scope ng-binding"><strong>' + gettext('Records') + '</strong>';
	catalogPanel += '						</div>';
	catalogPanel += '						<br>';
	catalogPanel += '						<div class="row">';
	catalogPanel += '							<div class="col-md-6">';
	catalogPanel += '								<input id="catalog_register_from" placeholder="' + gettext('From...') + '" data-provide="datepicker" class="form-control" data-date-format="yyyy-mm-dd" value="">';
	catalogPanel += '							</div>';
	catalogPanel += '							<div class="col-md-6">';
	catalogPanel += '								<input id="catalog_register_to" placeholder="' + gettext('To...') + '" data-provide="datepicker" class="form-control" data-date-format="yyyy-mm-dd" value="">';
	catalogPanel += '							</div>';
	catalogPanel += '						</div>';
	catalogPanel += '					</div>';
	catalogPanel += '				</div>';
	catalogPanel += '			</div>';
	catalogPanel += '		</div>';
	catalogPanel += '	</div>';
	catalogPanel += '	<div id="catalog_results" class="row">';
	catalogPanel += '		<div class="col">';
	catalogPanel += '			<div class="row text-center form">';
	catalogPanel += '				<div class="col-md-2 center-block"></div>';
	catalogPanel += '				<div class="col-md-8 center-block"><ul class="catalog-pager pagination"></ul></div>';
	catalogPanel += '				<div class="col-md-2">';
	catalogPanel += '					<select class="form-control" id="search-results-order-btn" style="margin-top: 20px">';
	catalogPanel += '					<option val="&sortBy=relevance">' + gettext('Order by relevance') + '</option>';
	catalogPanel += '					<option val="&sortBy=changeDate">' + gettext('Order by modification date') + '</option>';
	catalogPanel += '					<option val="&sortBy=title&sortOrder=reverse">' + gettext('Order by title') + '</option>';
	catalogPanel += '					</select></div>';
	catalogPanel += '				</div>';
	catalogPanel += '			</div>';
	catalogPanel += '			<div class="row">';
	catalogPanel += '				<div class="col-sm-3" id="catalog_filter"></div>';
	catalogPanel += '				<div class="col-sm-9" id="catalog_content"></div>';
	catalogPanel += '			</div>';
	catalogPanel += '		</div>';
	catalogPanel += '	</div>';
	catalogPanel += '</div></div>';
	$("body").append(catalogPanel);
	$('.dropdown-multiselect .dropdown-menu').click(function(evt) {evt.stopPropagation()})
	
	if (this.config.customFiltersConfig.url && !this.config.customFiltersConfig.products) {
		$.ajax({
			url: self.config.customFiltersConfig.url,
			success: function(response) {
				self.config.customFiltersConfig.products = response.products;
				self.config.customFiltersConfig.adminAreas = response.adminAreas;
				self.addCustomFilterEntries();
			}
		});
	}
	
	this.catalog_panel = $("#catalog_container");
	if(!this.catalog_map){
		this.catalog_map = new CatalogMap(this, "catalog_map");
	}


	$("#catalog-search-button").unbind("click").click(function(){
		self.filterCatalog();
	});
	
	$("#search-results-order-btn").change(function(a, b, c) {
		var option = $("#search-results-order-btn option:selected").get(0);
		if (option) {
			self.sortBy = option.getAttribute("val");
			self.filterCatalog();
		}
	});
	
	$("#gn-any-field").off("keypress").on("keypress", function(e){
		if(e.keyCode == 13) {
			self.filterCatalog();
		}
	});

	$("#catalog-search-advanced-button").unbind("click").click(function(){
		$("#catalog_search_advanced").toggle();
		//$("#catalog_map_full").toggle(); 
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
		self.clearCustomFilters();
		self.launchQuery();
	});

	$("#catalog_map_clean").unbind("click").click(function(){
		self.catalog_map.cleanData();
		self.filterCatalog();
	});
	$("#chck_mapareaoverlap").unbind("click").click(function(){
		self.filterCatalog();
	});
}

CatalogView.prototype.getBaseUrl = function() {
	if (this.config.baseUrl) {
		return this.config.baseUrl;
	}
	return '/geonetwork'
}

CatalogView.prototype.getLocalizedEndpoint = function() {
	if (viewer.core.conf.language.iso639_2b) {
		url = this.getBaseUrl() + '/srv/' + viewer.core.conf.language.iso639_2b;	
	}
	else {
		url = this.getBaseUrl() + '/srv/eng';
	}
	return url;
}

CatalogView.prototype.filterCatalog = function(fromResult){
	if (fromResult) {
		this.fromResult = fromResult;
	}
	else {
		this.fromResult = 1;
	}
	var search = $("#gn-any-field").val();
	// hack: remove accents since Geonetwork index removes them
	// This should be fixed/configured in Geonetwork. What about Ñ??
	search = search.replace("á", "a");
	search = search.replace("Á", "A");
	search = search.replace("é", "e");
	search = search.replace("É", "E");
	search = search.replace("í", "i");
	search = search.replace("Í", "I");
	search = search.replace("ó", "o");
	search = search.replace("Ó", "O");
	search = search.replace("ú", "u");
	search = search.replace("Ú", "U");

	// allow using the "or" keyword as synonym of + sign
	search = search.replace(/[ \+][oO][rR][ \+]/g, "+");
	// remove extra blanks
	search = search.replace(/ +/g, " ");
	// remove blanks surrounding + signs
	search = search.replace(/ \+/g, "+");
	search = search.replace(/\+ /g, "+");
	var searchTerms = search.split(" ");
	var andWildcardSearchComponents = [];
	for (var i=0; i<searchTerms.length; i++) {
		// add wildcards to search for partial terms
		if (searchTerms[i] != "") {
			var term;
			orSearchTerms = searchTerms[i].split("+");
			for (j = 0; j<orSearchTerms.length; j++) {
				if (orSearchTerms[j] != "") {
					if (j==0) { // first
						term = orSearchTerms[j]+"*";
					}
					else {
						term = term + " or " + orSearchTerms[j]+"*";
					}
				}
			}
			andWildcardSearchComponents.push(term);
		}
	}

	var categories = $("#categoriesF").val();
	var keywords = $("#keywordsF").val();
	var resources = $("#orgNameF").val();
	var creation_from = $("#catalog_resource_from").val();
	var creation_to = $("#catalog_resource_to").val();
	var date_from = $("#catalog_register_from").val();
	var date_to = $("#catalog_register_to").val();
	var selectedArea = null;
	if (this.catalog_map.isSpatialFilterEnabled()) {
		var geom = this.catalog_map.getSelectedArea();
		if (geom != null) {
			// don't use the real geometry for filtering, use the bbox instead
			var extent = ol.geom.Polygon.fromExtent(geom.getExtent());
			var format = new ol.format.WKT();
			var selectedArea =  format.writeGeometry(extent, {dataProjection: 'EPSG:4326', featureProjection: this.catalog_map.map.getView().getProjection()});
		}
	}
	this.launchQuery(andWildcardSearchComponents, categories, keywords, resources, creation_from, creation_to, date_from, date_to, selectedArea);

}

CatalogView.prototype.launchQuery = function(searchComponents, categories, keywords, resources, creation_from, creation_to, date_from, date_to, extent){
	var query = "";
	$(".catalog_filter_entry_ck").each(function(){
		if($(this).is(':checked')){
			if(query != ""){
				query += "%26";
			}
			query += $(this).attr("name");
		}

	});
	this.getCatalogFilters(query, searchComponents, categories, keywords, resources, creation_from, creation_to, date_from, date_to, extent);
}

CatalogView.prototype.getFacetEntryName = function(cat, entry, filterName){
	if (filterName) {
		return filterName + '%2F' + encodeURIComponent(encodeURIComponent(entry['@value']));
	}
	else {
		return cat['@name'] + '%2F' + encodeURIComponent(encodeURIComponent(entry['@value']));
	}
}

CatalogView.prototype.getFacetEntry = function(entry, entry_name, checked){
	var checkedStr = "";
	var selectedStr = "";
	if(checked){
		checkedStr = " checked";
		selectedStr = " catalog_filter_entry_ck_sel"
	}

	return '<div class="catalog_filter_entry' + selectedStr + '"><input ' + checkedStr + ' type="checkbox" class="catalog_filter_entry_ck" name="'+ entry_name + '"/>&nbsp;&nbsp;&nbsp;'+ entry['@label'] + ' (' + entry['@count'] +')</div>';
}

CatalogView.prototype.getFacetEntries = function(query, cat, filterName){
	var filter_code = '';
	var entryName, checked;
	if('category' in cat && Array.isArray(cat.category) && cat.category.length > 0){
		var facetEntriesCode = "";
		for(var idx = 0; idx < cat.category.length; idx++){
			var entry = cat.category[idx];
			entryName = this.getFacetEntryName(cat, entry, filterName);
			checked = query.includes(entryName);
			if (checked) {
				/**
				 * The catalog UI suggests that selection within a facet behaves
				 * as AND filters, but it actually behaves as OR filters.
				 * Therefore, we will only allow one entry selected by facet to
				 * avoid confusing the users.
				 */
				facetEntriesCode = this.getFacetEntry(entry, entryName, checked);
				break;
			}
			else {
				facetEntriesCode += this.getFacetEntry(entry, entryName, checked);
			}
		}
		filter_code += facetEntriesCode;
	}
	if('category' in cat && '@value' in cat.category){
		var entry = cat.category;
		entryName = this.getFacetEntryName(cat, entry, filterName);
		checked = query.includes(entryName);
		filter_code += this.getFacetEntry(entry, entryName, checked);
	}
	return filter_code;
}

CatalogView.prototype.getFacet = function(filterTitle, filterName, filterEntries){
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
	'<div class="box-body" style="display:block">';
	filter_code += filterEntries;
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


CatalogView.prototype.sanitizeHtmlText = function(text){
	var placeHolder = $('<ph></ph>');
	var result = placeHolder.text(text).html();
	result = result.replace(/"/g, '&#x22;');
	result = result.replace(/'/g, "&#x27;");
	result = result.replace(/`/g, "&#x60;");
	return result;
}

CatalogView.prototype.getMetadataEntry = function(metadata){
	var met = '';
	if(metadata){
		var title = this.sanitizeHtmlText(metadata['defaultTitle']) || '';
		var abstract = this.sanitizeHtmlText(metadata['abstract']) || '';
		met += '<div class="catalog_content_layer col-md-6">';
		met += '	<div class="col-sm-9">';
		met += '		<p class="catalog_content_title block-with-text">'+ title +'</p>';
		met += '		<p class="catalog_content_abstract block-with-text">'+ abstract +'</p>';
		met += '	</div>';
		met += '	<div class="col-sm-3 catalog_content_lateral">';
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
		
		var md_url = this.sanitizeHtmlText(this.getMetadataUrl(metadata['geonet:info']['uuid']));
		met += '			<img src="'+this.sanitizeHtmlText(image_src)+'" style="width:100%;"/>';
		met += '		</div>';
		met += '	</div>';
		met += '	<div class="col-sm-12">';
		met += '			<div class="catalog_content_button_place col-sm-3">';
		met += '				<a name="'+ metadata['geonet:info']['uuid'] +'" href="" class="btn btn-block btn-social catalog_content_button btn-custom-tool catalog_details">';
		met += ' 					<i class="fa fa-search" aria-hidden="true"></i><span>' + gettext('Details') + '</span>';
		met += '				</a>';
		met += '			</div>';
		met += '			<div class="catalog_content_button_place col-sm-3">';
		met += '				<a name="'+ metadata['geonet:info']['uuid'] +'" href="" class="btn btn-block btn-social catalog_content_button btn-custom-tool catalog_linkmap">';
		met += ' 					<i class="fa fa-map-o" aria-hidden="true"></i><span>' + gettext('Map') + '</span>';
		met += '				</a>';
		met += '			</div>';
		met += '			<div class="catalog_content_button_place col-sm-3">';
		met += '				<a name="'+ metadata['geonet:info']['uuid'] +'" href="" class="btn btn-block btn-social catalog_content_button btn-custom-tool catalog_download">';
		met += ' 					<i class="fa fa-download" aria-hidden="true"></i><span>' + gettext('Download') + '</span>';
		met += '				</a>';
		met += '			</div>';
		met += '			<div class="catalog_content_button_place col-sm-3">';
		met += '				<a target="_blank" name="'+ metadata['geonet:info']['uuid'] +'" href="' + md_url + '" class="btn btn-block btn-social btn-custom-tool catalog_content_button catalog_catalogmd">';
		met += ' 					<i class="fa fa-newspaper-o" aria-hidden="true"></i><span>' + gettext('Metadatum') + '</span>';
		met += '				</a>';
		met += '			</div>';
		met += '	</div>';
		met += '</div>';
	}else{
		this.fromResult = 1;
		this.updatePager(0);
		met += '<div class="no_catalog_content col-sm-12">';
		met += '<i class="fa fa-ban" aria-hidden="true"></i> ';
		met += 	gettext('No results found');
		met += '</div>';
	}
	return met;
}

CatalogView.prototype.getKeywordAndQuery = function(keywords, key){
	var cat_array = keywords.split(";");
	var cats = "";
	for(var i=0; i<cat_array.length; i++){
		cats += "&"+key+"="+cat_array[i];;
	}
	cats = cats.replace(new RegExp(' ', 'g'), '+');
	return cats;
}

CatalogView.prototype.getKeywordOrQuery = function(keywords, key){
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

CatalogView.prototype._getSearchingContent = function() {
	var content = '<div class="no_catalog_content col-sm-12">';
	content += '<i class="fa fa-spinner fa-spin" aria-hidden="true"></i>&nbsp;';
	content += 	gettext('The search is running...');
	content += '</div>';
	return content;
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
			content += '<i class="fa fa-file-archive-o" aria-hidden="true"></i>';
			content += '<span class="catalog-link-resource"><p>' + layer_title + '<br/><span class="catalog-entry-subtitle">' + layer_name + '</span></p></span>';
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
			content += '<i class="fa fa-file-archive-o" aria-hidden="true"></i>';
			content += '<span class="catalog-link-resource"><p>' + layer_title + '<br/><span class="catalog-entry-subtitle">' + layer_name + '</span></p></span>';
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
			content += '<i class="fa fa-file-archive-o" aria-hidden="true"></i>';
			content += '<span class="catalog-link-resource"><p>' + layer_title + '<br/><span class="catalog-entry-subtitle">' + layer_name + '</span></p></span>';
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

CatalogView.prototype.onAddLayerButtonClick = function(targetBtn){
	if (this.onAddLayerButtonClickRunning) {
		// prevent the button to be clicked twice, it creates problems with the messageBox modal
		return;
	}
	this.onAddLayerButtonClickRunning = true;
	var self = this;

	var id = targetBtn.attr("name");
	var layerSummary = self.data[id];
	targetBtn.find("i.fa").removeClass('fa-map-o').addClass('fa-spinner fa-spin');
	var links = layerSummary.link || [];
	var title = layerSummary.title || layerSummary.defaultTitle || layerSummary.name || '';
	var abstract = layerSummary.abstract || title;
	try {
		var geoBox = [];
		if (layerSummary.geoBox) {
			if (Array.isArray(layerSummary.geoBox)) {
				// TODO: merge all the bboxes in this case
				var geoBoxStrList = layerSummary.geoBox[0].split("|");
			}
			else {
				var geoBoxStrList = layerSummary.geoBox.split("|");
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
	//console.log(geoBox);
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
				wms.title = title;
				wms.abstract = abstract;
				// TODO: if several services are available, we should query all of them to get available layers
			}
			else if (type == "OGC:WFS"){
				wfs_url = link[2];
			}
			else if (type == "OGC:WCS"){
				wcs_url = link[2];
			}
			// TODO: support WMTS
		}
	}
	if (wms.url) {
		var group_visible = false;
		group_visible = $("#layergroup-geonetwork-group").is(":checked");
		var name = wms.name || null;
		try {
			self.getAvailableLayers(wms.url, name).then(function(url, layers, formats) {
				targetBtn.find("i.fa").removeClass('fa-spinner fa-spin').addClass('fa-map-o');
				self.createSelectLayersPanel(layers, formats).then(function(selectedLayer) {
					self.createLayer(selectedLayer.Name, selectedLayer.Title, selectedLayer.Abstract, url, id, geoBox, group_visible, wfs_url, wcs_url);
					self.hidePanel();
				});
			}).catch(function(error) {
				messageBox.show('warning', gettext("No layers available"));
			}).finally(function() {
				self.onAddLayerButtonClickRunning = false;
				targetBtn.find("i.fa").removeClass('fa-spinner fa-spin').addClass('fa-map-o');
			});
		}
		catch(error) {
			console.log(error);
			targetBtn.find("i.fa").removeClass('fa-spinner fa-spin').addClass('fa-map-o');
			self.onAddLayerButtonClickRunning = false;
		}
	}
	else {
		messageBox.show('warning', gettext("No layers available"));
		targetBtn.find("i.fa").removeClass('fa-spinner fa-spin').addClass('fa-map-o');
		self.onAddLayerButtonClickRunning = false;
	}
	//targetBtn.find("i.fa").removeClass('fa-spinner fa-spin').addClass('fa-map-o');
	
}

CatalogView.prototype.getMaxGroupOrder = function() {
	var maxGroupOrder = 0;
	for (var i=0; i<viewer.core.conf.layerGroups.length; i++) {
		var group = viewer.core.conf.layerGroups[i];
		if (group.groupOrder > maxGroupOrder) {
			maxGroupOrder = group.groupOrder; 
		}
	}
	return maxGroupOrder;
}
CatalogView.prototype.getCatalogGroupOrder = function() {
	return this.getMaxGroupOrder() + 1000;
}

CatalogView.prototype.createLayerGroup = function() {
	var self = this;
	var groupId = 'gvsigol-geonetwork-group';
	var groupOrder = this.getCatalogGroupOrder();

	var tree = '';
	tree += '			<li class="box box-default collapsed-box" id="' + groupId + '">';
	tree += '				<div class="box-header with-border">';
	if (viewer.core.conf.selectable_groups) {
		tree += '				<input type="checkbox" class="layer-group" id="layergroup-' + groupId + '">';		
	}
	tree += '					<i style="cursor: pointer;" class="layertree-folder-icon fa fa-folder-o"></i>';
	tree += '					<span class="text">' + gettext("Catalog layers") + '</span>';
	tree += '					<div class="box-tools pull-right">';
	tree += '						<button class="btn btn-box-tool btn-box-tool-custom group-collapsed-button" data-widget="collapse">';
	tree += '							<i class="fa fa-plus"></i>';
	tree += '						</button>';
	tree += '					</div>';
	tree += '				</div>';
	tree += '				<div data-grouporder="' + groupOrder + '" data-groupnumber="' + groupOrder + '" class="box-body layer-tree-groups geonetwork-layer-group" style="display: none;">';
	tree += '				</div>';
	tree += '			</li>';

	$(".layer-tree").append(tree);
	
	$(".layertree-folder-icon").click(function(){
		if (this.parentNode.parentNode.className == 'box box-default') {
			this.parentNode.parentNode.className = 'box box-default collapsed-box';
			$(this.parentNode.parentNode.children[1]).css('display', 'none');
			this.parentNode.parentNode.children[0].children[0].className = "layertree-folder-icon fa fa-folder-o";
			if (this.parentNode.parentNode.children[0].children[2].children[0].children[0].className == "fa fa-minus") {
				this.parentNode.parentNode.children[0].children[2].children[0].children[0].className = "fa fa-plus";
			} else if (this.parentNode.parentNode.children[0].children[2].children[0].children[0].className == "fa fa-plus"){
				this.parentNode.parentNode.children[0].children[2].children[0].children[0].className = "fa fa-minus";
			}
		} else if (this.parentNode.parentNode.className == 'box box-default collapsed-box') {
			this.parentNode.parentNode.className = 'box box-default';
			$(this.parentNode.parentNode.children[1]).css('display', 'block');
			this.parentNode.parentNode.children[0].children[2].children[0].children[0].className = "fa fa-plus";
			this.parentNode.parentNode.children[0].children[0].className = "layertree-folder-icon fa fa-folder-open-o";
			if (this.parentNode.parentNode.children[0].children[2].children[0].children[0].className == "fa fa-minus") {
				this.parentNode.parentNode.children[0].children[2].children[0].children[0].className = "fa fa-plus";
			} else if (this.parentNode.parentNode.children[0].children[2].children[0].children[0].className == "fa fa-plus"){
				this.parentNode.parentNode.children[0].children[2].children[0].children[0].className = "fa fa-minus";
			}
		}
	});
	
	$("[data-widget='collapse']").click(function(){
		if (this.parentNode.parentNode.children[0].className == 'layertree-folder-icon fa fa-folder-o') {
			this.parentNode.parentNode.children[0].className = 'layertree-folder-icon fa fa-folder-open-o';
		} else if (this.parentNode.parentNode.children[0].className == 'layertree-folder-icon fa fa-folder-open-o') {
			this.parentNode.parentNode.children[0].className = 'layertree-folder-icon fa fa-folder-o';
		}
	});
	
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

CatalogView.prototype._createOLLayer = function(url, name, title, abstract, dataId, bbox, wfs_url, wcs_url) {
	var self = this;
	
	if (url.endsWith("?")) {
		url = url.substring(0, url.length-1);
	}
	var zIndex = $("#layer-tree-tab #gvsigol-geonetwork-group .layer-box").length + this.getCatalogGroupOrder();
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
		id: dataId,
		zIndex: zIndex
	});
	catalogLayer.baselayer = false;
	catalogLayer.dataid = dataId;
	catalogLayer.id = dataId;
	catalogLayer.layer_name = name;
	catalogLayer.legend = url + '?SERVICE=WMS&VERSION=1.1.1&layer=' + name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on';
	catalogLayer.queryable = true;
	catalogLayer.abstract = abstract;
	catalogLayer.title = title;
	catalogLayer.visible = true;
	catalogLayer.allow_download = true;
	catalogLayer.wms_url = url;
	catalogLayer.metadata = dataId;
	catalogLayer.metadata_url = this.getMetadataUrl(dataId);
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

CatalogView.prototype.createSelectLayersPanel = function(layers, formats) {
	var self = this;
	var onSuccess = function() {}
	var onError = function() {}
	var onFinally = function() {};
	var layerMap = [];

	for(var i=0; i<layers.length; i++) {
		var sanitizedName = self.sanitizeHtmlText(layers[i].Name);
		layerMap[sanitizedName] = layers[i];
		var content = '<div class="container-fluid">';
		content += '<div class="row">';
		content += '  <div class="col-sm-4">';
		content += '    <label class="form-label">' + self.sanitizeHtmlText(layers[i].Title) + '</label>';
		content += '    <div class="layer-name" style="padding: 6px 4px 6px 0px">'+ sanitizedName + '</div>';
		content += '  </div>';
		content += '  <div class="col-sm-4">';
		if (formats.length>0) {
			content += '    <select class="form-control">';
			for (var j=0; j<formats.length; j++) {
				content += '      <option val="' + self.sanitizeHtmlText(formats[j]) + '">' + self.sanitizeHtmlText(formats[j]) + '</option>';
			}
		}
		content += '    </select>';
		content += '  </div>';
		content += '  <div class="col-sm-4">';
		content += '    <button class="btn btn-default add-to-map-btn" type="button">' + gettext("Add to map") + '</button>';
		content += '  </div>';
		content += '</div>';
	}

	$(self.modalSelector).find('.modal-body').html(content);
	$(self.modalSelector).find('.modal-title').html(gettext("Add layer to map"));
	$('.add-to-map-btn').click(function() {
		var selectedLayerName = $(this).parents('div.row').find('.layer-name').text();
		var selectedStyle = $(this).parents('div.row').find('select').val();
		var selectedLayer = layerMap[selectedLayerName];
		$(self.modalSelector).modal('hide');
		onSuccess(selectedLayer, selectedStyle);
		onFinally(selectedLayer, selectedStyle);
	});
	$(self.modalSelector).find('.modal-footer').html('');
	$(self.modalSelector).modal('show');
	$(self.modalSelector).on('hidden.bs.modal', function (e) {
		onError(e);
		onFinally(e);
	})
	var response = {
		then: function (callback) {
			if (typeof(callback)==='function') onSuccess = callback;
			return response;
		},
		catch: function (callback) {
			if (typeof(callback)==='function') onError = callback;
			return response;
		},
		finally: function (callback) {
			if (typeof(callback)==='function') onFinally = callback;
			return response;
		}
	}
	return response;
}

CatalogView.prototype.getAvailableLayers = function(baseUrl, layerName) {
	var self = this;
	var onSuccess = function() {}
	var onError = function() {}
	var onFinally = function() {};
	
	var url = baseUrl + "?service=WMS&request=GetCapabilities&version=1.1.1";
	var parser = new ol.format.WMSCapabilities();
    var headers = {};
	if (viewer.core.conf.user && viewer.core.conf.user.token) {
        // FIXME: this is just an OIDC test. We must properly deal with refresh tokens etc
		headers["Authorization"] = 'Bearer ' + viewer.core.conf.user.token;
	};
	$.ajax({
		url: url,
		headers: headers,
		success: function(response) {
			var result = parser.read(response);
			var url = baseUrl;
			try {
				var getMapDCPTypes = result.Capability.Request.GetMap.DCPType;
				for (var i=0; i<getMapDCPTypes.length; i++) {
					if (getMapDCPTypes[i]["HTTP"] && getMapDCPTypes[i]["HTTP"]["Get"]) {
						url = getMapDCPTypes[i]["HTTP"]["Get"].OnlineResource;
						url.split("?")[0];
						break;
					}
				}
			}
			catch(e) {}
			var formats = [];
			try {
				var allFormats = result.Capability.Request.GetMap.Format;
				for (var i=0; i<allFormats.length; i++) {
					if (allFormats[i].toLowerCase().indexOf('png', 0) !== -1 ||
						allFormats[i].toLowerCase().indexOf('jpeg', 0) !== -1) {
						formats.push(allFormats[i]);
					}
				}
			}
			catch(e) {}
			
			var layers = result.Capability.Layer.Layer; 
			
			var layer = null;
			if (layerName) {
				var layer = null;
				for (var i=0, len = layers.length; i<len; i++) {
					if (layers[i].Name == layerName) {
						layer = layers[i];
					}
				}
			}
			if (layer != null) {
				layers = [layer];
			}
			else {
				// try removing the workspace name
				var layerNameParts = layerName.split(":");
				if (layerNameParts.length>1) {
					var nqLayerName = layerNameParts[1];
					for (var i=0, len = layers.length; i<len; i++) {
						if (layers[i].Name == nqLayerName) {
							layer = layers[i];
						}
					}
					if (layer != null) {
						layers = [layer];
					}
				}

			}
			onSuccess(url, layers, formats);
			onFinally(url, layers, formats);
			/*
			var extent;
			if((extent[0]==0 && extent[1]==0 && extent[2]==-1 && extent[3]==-1 )||
					(extent[0]==-1 && extent[1]==-1 && extent[2]==0 && extent[3]==0 )){
				return;
			}
			var ext = ol.proj.transformExtent(extent, ol.proj.get('EPSG:4326'), ol.proj.get('EPSG:3857'));
			self.map.getView().fit(ext, self.map.getSize());
			*/
		},
		error: function(jqXHR, textStatus) {
			onError(jqXHR, textStatus);
			onFinally(jqXHR, textStatus);
		}
	});

	var response = {
		then: function (callback) {
			if (typeof(callback)==='function') onSuccess = callback;
			return response;
		},
		catch: function (callback) {
			if (typeof(callback)==='function') onError = callback;
			return response;
		},
		finally: function (callback) {
			if (typeof(callback)==='function') onFinally = callback;
			return response;
		}
	}
	return response;
}


CatalogView.prototype.createLayer = function(name, title, abstract, url, dataId, bbox, group_visible, wfs_url, wcs_url) {
	var self = this;
	var newLayer = self._createOLLayer(url, name, title, abstract, dataId, bbox, wfs_url, wcs_url);
	
	var groupId = "gvsigol-geonetwork-group";
	var groupEntry = $("#"+groupId);
	if(groupEntry.length == 0){
		self.createLayerGroup();
	}
	var layerTree = self.mapViewer.getLayerTree();
	
	var removeLayerButtonUI = '<a id="remove-catalog-layer-' + dataId + '" data-layerid="' + dataId + '" class="btn btn-block btn-social btn-custom-tool remove-catalog-layer-btn">';
	removeLayerButtonUI +=	'	<i class="fa fa-times"></i> ' + gettext('Remove layer');
	removeLayerButtonUI +=	'</a>';
	
	var newLayerUI = $(layerTree.createOverlayUI(newLayer, $("#layergroup-"+groupId).is(":checked")));
	newLayerUI.find(".box-body .zoom-to-layer").after(removeLayerButtonUI);
	$(".geonetwork-layer-group").prepend(newLayerUI);
	layerTree.setLayerEvents();
	this._replaceMetadataBtnEvents();

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

CatalogView.prototype.updatePager = function(totalCount) {
	var self = this;
	var pagerEntries = '';
	if (self.fromResult==1) {
		pagerEntries += '<li class="disabled"><a href="#">&laquo;</a></li>';
	}
	else {
		pagerEntries += '<li><a href="#" class="prev-result-page">&laquo;</a></li>';
	}
	var currentPage = Math.ceil(self.fromResult/self.config.resultsPerPage);
	var numPages = Math.ceil(totalCount / self.config.resultsPerPage);
	if (numPages<1) numPages = 1;
	pagerEntries += '<li class="disabled"><a hef="#">' + currentPage + ' / ' + numPages +'</a></li>';
	if ((self.fromResult + self.config.resultsPerPage-1) <= totalCount) {
		pagerEntries += '<li><a href="#" class="next-result-page">&raquo;</a></li>';
	}
	else {
		pagerEntries += '<li class="disabled"><a href="#">&raquo;</a></li>';
	}
	$('.catalog-pager').html(pagerEntries);
	$(".next-result-page").unbind("click").click(function(){
		self.fromResult = self.fromResult + self.config.resultsPerPage;
		self.filterCatalog(self.fromResult);
	});
	$(".prev-result-page").unbind("click").click(function(){
		var fromResult = self.fromResult - self.config.resultsPerPage;
		if (fromResult<1) {
			self.fromResult = 1;
		}
		else {
			self.fromResult = fromResult;
		}
		self.filterCatalog(self.fromResult);
	});
}

CatalogView.prototype.getCatalogFilters = function(query, searchComponents, categories, keywords, resources, creation_from, creation_to, date_from, date_to, extent){
	$('#catalog-search-button-icon').removeClass('fa-search').addClass('fa-spinner fa-spin');
	$("#catalog_content").html(this._getSearchingContent());

	var self = this;
	var filters = "";
	if (searchComponents && searchComponents.length>0) {
		for (var i=0; i<searchComponents.length; i++) {
			filters += "&" + this.config.searchField + "=" + searchComponents[i];
		}
	}
	if(resources && resources.length > 0){
		filters += this.getKeywordAndQuery(resources, "orgName");
	}
	query = this.addCustomAreaFilter(query);
	filters += this.addCustomKeywordFilter(filters);
	if(keywords && keywords.length > 0){
		filters += this.getKeywordAndQuery(keywords, "keyword");
	}
	if(categories && categories.length > 0){
		filters += this.getKeywordAndQuery(categories, "_cat");
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
	filters += "&from="+self.fromResult;
	var to = self.fromResult + self.config.resultsPerPage - 1;
	filters += "&to="+to;
	
	var facetsConfig = self.config.facetsConfig;
	var facetsOrder = self.config.facetsOrder;
	var disabledFacets = self.config.disabledFacets;
	
	var url = self.getLocalizedEndpoint() + "/q";
	// TODO: authentication
	url = url + '?_content_type=json' + filters + '&bucket=s101&facet.q=' + query + '&fast=index&resultType=details' + self.sortBy;
	//var url = '/gvsigonline/catalog/get_query/?_content_type=json&bucket=s101&facet.q='+query+'&fast=index&from=1&resultType=details&sortBy=relevance';
	$.ajax({
		url: url,
		success: function(response) {
			try{
				$('#catalog-search-button-icon').removeClass('fa-spinner fa-spin').addClass('fa-search');
				//response = JSON.parse(response);
				self.data = {};
				
				self.updatePager(response.summary['@count']);
				var all_filters_code = '';
				var shownFilters = {};
				for(var idx = 0; idx < response.summary.dimension.length; idx++){
					var cat = response.summary.dimension[idx];
					if ('@label' in cat && '@name' in cat && !(disabledFacets.includes(cat['@name']))) {
						var customFacetEntries = self.getCustomFacetEntries(cat['@name']);
						if (customFacetEntries) {
							shownFilters[cat['@name']] = self.getFacet(cat['@label'], cat['@name'], customFacetEntries);
						}
						else if('category' in cat) {
							if (Array.isArray(facetsConfig[cat['@name']])) { // pattern based configuration
								var subFilters = self.getPatternBasedCategories(cat, facetsConfig[cat['@name']]);
								var facetEntries;
								for(var subFilterName in subFilters){
									var subFilter = subFilters[subFilterName];
									facetEntries = self.getFacetEntries(query, subFilter, cat['@name']);
									shownFilters[subFilter['@name']] = self.getFacet(gettext(subFilter['@label']), cat['@name'], facetEntries);
								}
							}
							else {
								if (facetsConfig[cat['@name']]) {
									var filterLabel = facetsConfig[cat['@name']]['title'];
								}
								else {
									var filterLabel = cat['@label'];
								}
								console.log(filterLabel);
								var facetEntries = self.getFacetEntries(query, cat, cat['@name']);
								shownFilters[cat['@name']] = self.getFacet(gettext(filterLabel), cat['@name'], facetEntries);
							}
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


				$(".catalog_details").unbind("click").click(function(evt){
					evt.preventDefault();
					var id = $(this).attr("name");
					self.createDetailsPanel(id);

				});

				if (viewer.core.getDownloadManager().isManagerEnabled()) {
					$(".catalog-download-list-btn").unbind("click").click(function(){
						viewer.core.getDownloadManager().showDownloadList();
					});
				}

				$(".catalog_download").unbind("click").click(function(evt){
					evt.preventDefault();
					var id = $(this).attr("name");
					if (viewer.core.getDownloadManager().isManagerEnabled()) {
						viewer.core.getDownloadManager().layerDownloads(id);
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
							aux_content += '<i class="fa fa-ban" aria-hidden="true"></i> ';
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
				
				self.onAddLayerButtonClickRunning = false;
				$(".catalog_linkmap").unbind("click").click(function(evt){
					evt.preventDefault();
					var targetBtn = $(this);
					self.onAddLayerButtonClick(targetBtn);
				});

				$(".catalog_filter_entry_ck").unbind("click").click(function(){
					self.filterCatalog();
				})

			} catch (e) {
				console.log(e);
			}
		},
		error: function(jqXHR, textStatus) {
			console.log(textStatus);
			console.log(jqXHR);
			content_code = self.getMetadataEntry(null);
			$('#catalog-search-button-icon').removeClass('fa-spinner fa-spin').addClass('fa-search');
			$("#catalog_content").html(content_code);
			self.updatePager(1);
		}
	});
}

CatalogView.prototype.createDetailsPanel = function(layer){
	var url;
	if (!layer) {
		return;
	}
	if (typeof layer === 'string') {
		// it is a metadata uuid
		url = "/gvsigonline/catalog/get_metadata/"+layer;
	}
	else {
		url = "/gvsigonline/catalog/get_metadata_id/"+layer.workspace+"/"+layer.layer_name+"/";
	}
	var self = this;
	$.ajax({
		type: "GET",
		async: false,
		url: url,
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
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

CatalogView.prototype.isActivePanel = function(){
	if (this.catalog_panel
			&& this.catalog_panel.css('display')!='none') {
		return true;
	}
	return false;
}

CatalogView.prototype.showPanel = function(searchString, geomFilter){
	if (this.catalog_panel===null) {
		var firstTime = true;
		this.initialization();
	}
	else {
		var firstTime = false;
	}
	this.catalog_panel.show();
	this.catalog_map.map.updateSize();
	if (firstTime && !geomFilter) {
		geomFilter = ol.geom.Polygon.fromExtent(viewer.core.getMap().getView().calculateExtent(viewer.core.getMap().getSize()));
	}
	this.catalog_map.setSpatialFilter(geomFilter);
	this.catalog_map.zoomToSelection();
	$('.viewer-search-form').css("display","none");
	if (searchString) {
		$("#gn-any-field").val(searchString);
	}
	this.map_container.hide();

	if (firstTime || searchString || geomFilter) {
		// apply filters after the map has been loaded
		this.filterCatalog();
	}
}

CatalogView.prototype.hidePanel = function(){
	this.map_container.show();
	if (this.catalog_panel) {
		this.catalog_panel.hide();
	}
	$('.viewer-search-form').css("display","inline-block");
}

CatalogView.prototype.getMetadataUrl = function(uuid) {
	return this.getLocalizedEndpoint() + '/catalog.search#/metadata/' + uuid;
}

CatalogView.prototype._replaceMetadataBtnEvents = function() {
	var self = this;
	if (self.config.metadata_viewer_button == 'LINK') {
		// when LINK mode is enabled, remove metadata buttons for layers not having linked metadata
		$("a.show-metadata-link").each(function(index, element) {
			var layers = self.map.getLayers();
			layers.forEach(function(layer){
				if (!layer.baselayer) {
					if (element.id===("show-metadata-" + layer.get("id"))) {
						selectedLayer = layer;
						if (!layer.metadata) {
							element.remove();
						}
					}
				}
			});
		});
	}
	
	$(".show-metadata-link").unbind("click").on('click', function(e) {
		var layers = self.map.getLayers();
		var selectedLayer = null;
		var layerContainer = $(this).parents('.layer-box');
		var id = layerContainer.first().attr("data-layerid");
		layers.forEach(function(layer){
			if (!layer.baselayer) {
				if (id===layer.get("id")) {
					selectedLayer = layer;
					if (self.config.metadata_viewer_button == 'LINK') {
						if (layer.metadata) {
							var url = self.getMetadataUrl(layer.metadata);
							var win = window.open(url, '_blank');
							if (win) win.focus();
						}
					}
					else if (self.config.metadata_viewer_button == 'BRIEF') {
						viewer.core.layerTree.showMetadata(selectedLayer);
					}
					else { // 'FULL'
						if (layer.metadata) {
							// layer was created from catalog, it may not be registerd on gvSIGOL so we use uuid
							self.createDetailsPanel(layer.metadata);
						}
						else { // workspace and layer name will be used to retrieve metadata
							viewer.core.layerTree.showMetadata(selectedLayer);
						}
					}
				}
			}
		}, this);
	});
}

CatalogView.prototype.install = function() {
	var self = this;
	
	var modal = '';
	modal += '<div class="modal fade" id="modal-catalog" tabindex="-1" role="dialog" aria-labelledby="myModalLabel">';
	modal += '	<div class="modal-dialog" role="document" style="width:auto;margin:30px 50px 30px 50px;">';
	modal += '		<div class="modal-content">';
	modal += '			<div class="modal-header">';
	modal += '				<button type="button" class="close" data-dismiss="modal"';
	modal += '					aria-label="Close">';
	modal += '					<span aria-hidden="true">&times;</span>';
	modal += '				</button>';
	modal += '				<h4 class="modal-title" id="myModalLabel"></h4>';
	modal += '			</div>';
	modal += '			<div class="modal-body">';
	modal += '			</div>';
	modal += '			<div class="modal-footer">';
	modal += '			</div>';
	modal += '		</div>';
	modal += '	</div>';
	modal += '</div>';
	
	$("body").append(modal);
	
	$("#show_catalog").click(function(){
		$("body").trigger('show-catalog-event');
		self.showPanel();
	});
	
	$("#show_map").click(function(){
		self.hidePanel()
	});
	
	this._replaceMetadataBtnEvents();
}

CatalogView.prototype.addCustomFilter = function(catalogPanel) {
	if (this.config.customFiltersConfig.url) {
		var adminAreasConf = this.config.customFiltersConfig.adminAreas;
		
		catalogPanel += '<div id="catalog_search"class="row">';
		catalogPanel += '	<div id="admin_areas_div" class="col-sm-6">';
		catalogPanel += '		<label for="admin_areas_btn"></label>';
		catalogPanel += '		<div class="dropdown dropdown-multiselect admin_areas_multiselect">';
		catalogPanel += '		<button class="btn btn-default btn-wrap-text dropdown-toggle form-control" type="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="true">';
		catalogPanel += '			<span id="admin_areas_label">' + gettext('Loading...') + '</span>&nbsp;<span class="caret"></span>';
		catalogPanel += '		</button>';
		catalogPanel += '		<ul class="dropdown-menu" aria-labelledby="admin_areas_label">';
		catalogPanel += '		</ul>';
		catalogPanel += '		</div>';
		catalogPanel += '	</div>';
		catalogPanel += '	<div class="col-sm-6">';
		catalogPanel += '		<label for="products_select"></label>';
		catalogPanel += '		<select class="form-control" id="products_select" name="products_select">';
		var productsConf = this.config.customFiltersConfig.products;
		if (productsConf && productsConf.def) {
			var def;
			for (var i=0; i<productsConf.def.length; i++) {
				def = productsConf.products.def[i];
				if (typeof(def) == 'string') {
					var name = def;
					var title = def;
				}
				else {
					var name = def.name;
					var title = def.title;
				}
				catalogPanel += '					<option value="' + name +'" selected>' + title + '</option>';
			}
		}
		else {
			catalogPanel += '					<option value="" selected>' + gettext('Loading...') + '</option>';
		}
		catalogPanel += '					</select>';
		catalogPanel += '				</div>';
		catalogPanel += '			</div>';
	}
	return catalogPanel;
}

CatalogView.prototype.addCustomAreaFilter = function(facetQuery) {
	$("#admin_areas_div * ul li").each(function() {
		var selOption = $(this).find("input")[0];
		if (selOption.checked) {
			if (facetQuery == '') {
				facetQuery = "keyword/" + selOption.value;
			}
			else {
				facetQuery += "%26keyword/" + selOption.value;
			}
		}
	});
	return facetQuery;
}

CatalogView.prototype.addCustomKeywordFilter = function(filters) {
	var keywords = '';
	$("#products_select").each(function() {
		if ($(this)[0].value != '') {
			if (keywords == '') {
				keywords = $(this)[0].value;
			}
			else {
				keywords += ";" + $(this)[0].value;
			}
		}
	});
	if (keywords != '') {
		return this.getKeywordAndQuery(keywords, "keyword");
	}
	return "";
}

CatalogView.prototype.addCustomFilterEntries = function() {
	var self = this;
	var areaDef;
	var optionStr;
	var not_filtered_str = gettext("Not filtered");

	$('.admin_areas_multiselect ul').empty();
	$('#admin_areas_label').text(not_filtered_str);
	$('.admin_areas_multiselect').siblings().text(this.config.customFiltersConfig.adminAreas.label);
	for (var i=0; i<this.config.customFiltersConfig.adminAreas.entries.length; i++) {
		def = this.config.customFiltersConfig.adminAreas.entries[i];
		if (typeof(def) == 'string') {
			var name = def;
			var title = def;
		}
		else {
			var name = def.name;
			var title = def.title;
		}
		optionStr = '<li class="checkbox">';
		optionStr += '	<label>';
		optionStr += '		<input type="checkbox" class="cr" value="' + name +'">';
		optionStr += '		<span class="cr cr-noborder"><i class="cr-icon glyphicon glyphicon-ok"></i></span>';
		optionStr += '		<span class="option-title">' + title + '</span>';
		optionStr += '	</label>';
		optionStr += '</li>';
		$('.admin_areas_multiselect ul').append(optionStr);
	}
	
	$('#admin_areas_div input').change(function() {
		var text = '';
		$("#admin_areas_div * ul li").each(function() {
			if ($(this).find("input")[0].checked) {
				if (text != '') {
					text += ", " + $(this).find("span.option-title").text();
				}
				else {
					text += $(this).find("span.option-title").text();
				}
			}
		});
		if (text == '') {
			text = not_filtered_str;
		}
		$('#admin_areas_label').text(text);
	});
	$('.admin_areas_multiselect').on('hide.bs.dropdown', function() {
		self.filterCatalog();
	});
	
	var productDef;
	$('#products_select').empty()
	$('#products_select').siblings().text(this.config.customFiltersConfig.products.label);
	optionStr = '<option value="" selected></option>';
	$('#products_select').append(optionStr);
	for (var i=0; i<this.config.customFiltersConfig.products.entries.length; i++) {
		def = this.config.customFiltersConfig.products.entries[i];
		if (typeof(def) == 'string') {
			var name = def;
			var title = def;
		}
		else {
			var name = def.name;
			var title = def.title;
		}
		optionStr = '<option value="' + name +'">' + title + '</option>';
		$('#products_select').append(optionStr);
	}
	$('#products_select').change(function() {
		self.filterCatalog();
	});
}

CatalogView.prototype.getCustomFacetEntries = function(filterName) {
	var facetEntries = "";
	if (filterName == 'keyword') {
		$("#admin_areas_div * ul li").each(function() {
			if ($(this).find("input")[0].checked) {
				var entry_label = $(this).find("span.option-title").text();
				facetEntries += '<div><input disabled checked type="checkbox" name="'+ entry_label + '"/>&nbsp;&nbsp;&nbsp;'+ entry_label + '</div>';
			}
		});
	}
	return facetEntries;
}


CatalogView.prototype.clearCustomFilters = function() {
	$('#products_select').val("");
	$('.admin_areas_multiselect ul * input').prop( "checked", false );
	$('#admin_areas_label').text(gettext("Not filtered"));
}

CatalogView.prototype.installNavBars = function() {
	var self = this;
	
	var html = '';
	
	/*html += '<ul class="nav navbar-nav">';
	html += '	<li><a href="#" id="show_map" class="dropdown-toggle">Map</a></li>';
	html += '</ul>'
	html += '<ul class="nav navbar-nav">';
	html += '	<li><a href="#" id="show_catalog" class="dropdown-toggle">Catalog</a></li>';
	html += '</ul>';
	
	$("#viewer-navbar").append(html);*/
	
	/*
	html += '<li class="dropdown">';
	html += 	'<a class="dropdown-toggle" data-toggle="dropdown" href="#">';
	html += 		gettext('Catalog') + ' <span class="caret"></span>';
	html += 	'</a>';
	html += 	'<ul id="gvsigol-navbar-views-menu" class="dropdown-menu">';
	html += 		'<li id="show_catalog" role="presentation"><a role="menuitem" tabindex="-1" href="#"><i class="fa fa-newspaper-o m-r-5"></i>' + gettext('Catalog and downloads') + '</a></li>';
	html += 	'</ul>';
	html += '</li>';
	
	$("#gvsigol-navbar-menus").append(html);*/
	
	var button = '<li id="show_catalog" role="presentation"><a role="menuitem" tabindex="-1" href="#"><i class="fa fa-newspaper-o m-r-5"></i>' + gettext('Catalog') + '</a></li>';
	$('#gvsigol-navbar-views-menu').append(button);
	
	$("#show_catalog").click(function(){
		$("body").trigger('show-catalog-event');
		self.showPanel();
	});
	
	$("#show_map").click(function(){
		self.hidePanel()
	});
}


