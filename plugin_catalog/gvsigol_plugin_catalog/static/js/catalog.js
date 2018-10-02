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
 * @author: José Badía <jbadia@scolab.es>
 */

/**
 * TODO
 */
var catalog = function(map, layerTree) {
	this.map = map;
	this.map_container = $("#container");	
	this.layerTree = layerTree;
	this.catalog_panel = null;
	this.catalog_map = null;
	this.data = {};
	this.initialization();
};

catalog.prototype.initialization = function(){
	var self = this;
	var filters = this.getCatalogFilters("");
	
	var catalogPanel = '';
	catalogPanel += '<div id="catalog_container">';

	catalogPanel += '<div id="catalog_search_full" class="row">';
	catalogPanel += '<div id="catalog_map_search" class="col-md-3">';
	catalogPanel += '<div id="catalog_map_full">';
	catalogPanel += '<div id="catalog_map" class="catalog_map"></div>';
	catalogPanel += '<p class="catalog_map_text">Presiona Ctrl para marcar un área&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a id="catalog_map_clean" href="#">Limpiar</a></p>';
	catalogPanel += '</div>';
	catalogPanel += '</div>';
	catalogPanel += '<div id="catalog_search" class="col-md-9">';
	catalogPanel += '	<div class="row">';
	catalogPanel += '		<div class="col-md-offset-1 col-md-10 relative">';
	catalogPanel += '    		<div class="input-group gn-form-any">';
	catalogPanel += '				<input type="text" class="form-control input-lg ng-pristine ng-untouched ng-valid ng-empty" id="gn-any-field" placeholder="Buscar..." data-ng-keyup="$event.keyCode == 13 &amp;&amp; triggerSearch()" data-typeahead="address for address in getAnySuggestions($viewValue)" data-typeahead-loading="anyLoading" data-typeahead-min-length="1" data-typeahead-focus-first="false" data-typeahead-wait-ms="300" aria-autocomplete="list" aria-expanded="false" aria-owns="typeahead-310-2994">';

	catalogPanel += '				<div class="input-group-btn">';
	catalogPanel += '					<button id="catalog-search-advanced-button" type="button" class="btn btn-default btn-lg ng-pristine ng-untouched ng-valid ng-not-empty" data-ng-model="searchObj.advancedMode" btn-checkbox="" btn-checkbox-true="1" btn-checkbox-false="0">';
	catalogPanel += '						<i class="fa fa-ellipsis-v"></i>';
	catalogPanel += '					</button>';

	catalogPanel += '					<button id="catalog-search-button" type="button" class="btn btn-primary btn-lg">';
	catalogPanel += '						&nbsp;&nbsp;';
	catalogPanel += '						<i class="fa fa-search"></i>';
	catalogPanel += '             			&nbsp;&nbsp;';
	catalogPanel += '					</button>';
	catalogPanel += '					<button id="catalog-clear-button" type="button" title="Limpiar búsqueda actual, filtros y orden." class="btn btn-link btn-lg">';
	catalogPanel += '						<i class="fa fa-times"></i>';
	catalogPanel += '					</button>';
	catalogPanel += '				</div>';
	catalogPanel += '			</div>';
	catalogPanel += '		</div>';
	catalogPanel += '		<div class="col-lg-3">';
	catalogPanel += '		</div>';
	catalogPanel += '	</div>';
	catalogPanel += '</div>';
	catalogPanel += '	<div id="catalog_search_advanced" class="row">';
	catalogPanel += '		<div class="catalog_search_advanced_col col-md-4">';
	catalogPanel += '	    	<h3 data-translate="" class="ng-scope">¿Qué?</h3>';
	catalogPanel += '			<div class="form-group">';
	catalogPanel += '	        	<label for="categoriesF" class="col-md-4 col-sm-12 control-label ng-scope">Categorías</label>';
	catalogPanel += '				<div class="col-sm-8">';
	catalogPanel += '					<input type="text" id="categoriesF" placeHolder="Separado por \';\'    P.ej: cat_1;cat_2;..." value="" class="form-control ng-isolate-scope"/>';
	catalogPanel += '   			</div>';
	catalogPanel += '   		</div>';
	catalogPanel += '			<div class="form-group">';
	catalogPanel += '				<label for="keywordsF" class="col-md-4 col-sm-12 control-label ng-scope">Palabras Clave</label>';
	catalogPanel += '				<div class="col-sm-8">';
	catalogPanel += '       			<input type="text" id="keywordsF" placeHolder="Separado por \';\'    P.ej: cat_1;cat_2;..." value="" class="form-control ng-isolate-scope"/>';
	catalogPanel += '       		 </div>';
	catalogPanel += '	      	</div>';
	catalogPanel += '      		<div class="form-group">';
	catalogPanel += '  				<label for="orgNameF" class="col-md-4 col-sm-12 control-label ng-scope">Contacto para el recurso</label>';
	catalogPanel += '   			<div class="col-sm-8">';
	catalogPanel += ' 			        <input type="text" id="orgNameF" placeHolder="Separado por \';\'    P.ej: cat_1;cat_2;..." value="" class="form-control ng-isolate-scope"/>';
	catalogPanel += '   		    </div>';
	catalogPanel += '   		</div>';
	catalogPanel += ' 		</div>';
	catalogPanel += '    	<div class="catalog_search_advanced_col col-md-4">';
	catalogPanel += '     		<h3 class="ng-scope">¿Cuándo?</h3>';
	catalogPanel += '        <div data-gn-period-chooser="resourcesCreatedTheLast" data-date-from="searchObj.params.creationDateFrom" data-date-to="searchObj.params.creationDateTo" class="ng-isolate-scope">';
	catalogPanel += '		<div class="btn-group btn-group-xs">';
	catalogPanel += '      			<span data-translate="" class="ng-scope ng-binding"><strong>Recursos</strong>';
	catalogPanel += ' 		</div>';
	catalogPanel += ' 		<br>';
	catalogPanel += '  		<div class="row">';
	catalogPanel += '    			<div class="col-md-6">';
	catalogPanel += '        			<input id="catalog_resource_from" placeholder="De..." data-provide="datepicker" class="form-control" data-date-format="yyyy-mm-dd" value="">';
	catalogPanel += '    			</div>';
	catalogPanel += '    			<div class="col-md-6">';
	catalogPanel += '        			<input id="catalog_resource_to" placeholder="Hasta..." data-provide="datepicker" class="form-control" data-date-format="yyyy-mm-dd" value="">';
	catalogPanel += '    			</div>';
	catalogPanel += '  		</div>';
	catalogPanel += '		<div class="btn-group btn-group-xs">';
	catalogPanel += '      			<span data-translate="" class="ng-scope ng-binding"><strong>Registros</strong>';
	catalogPanel += ' 		</div>';
	catalogPanel += ' 		<br>';
	catalogPanel += '  		<div class="row">';
	catalogPanel += '    			<div class="col-md-6">';
	catalogPanel += '        			<input id="catalog_register_from" placeholder="De..." data-provide="datepicker" class="form-control" data-date-format="yyyy-mm-dd" value="">';
	catalogPanel += '    			</div>';
	catalogPanel += '    			<div class="col-md-6">';
	catalogPanel += '      				<input id="catalog_register_to" placeholder="Hasta..." data-provide="datepicker" class="form-control" data-date-format="yyyy-mm-dd" value="">';
	catalogPanel += '    			</div>';
	catalogPanel += '  		</div>';
	catalogPanel += '	   </div>';
	catalogPanel += '	   </div>';
	catalogPanel += '</div>';
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

catalog.prototype.filterCatalog = function(){
	var search = $("#gn-any-field").val();
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

catalog.prototype.launchQuery = function(search, categories, keywords, resources, creation_from, creation_to, date_from, date_to, extent){
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

catalog.prototype.getCatalogEntry = function(query, cat, entry){
	var entry_name = cat['@name'] + '%2F' + entry['@value'];
	var checked = "";
	var selected = "";
	if(query.includes(entry_name)){
		checked = " checked";
		selected = " catalog_filter_entry_ck_sel"
	}

	return '<li class="catalog_filter_entry' + selected + '"><input ' + checked + ' type="checkbox" class="catalog_filter_entry_ck" name="'+ entry_name + '"/>&nbsp;&nbsp;&nbsp;'+ entry['@label'] + ' (' + entry['@count'] +')</li>';
}

catalog.prototype.getMetadataEntry = function(metadata){
	var met = '';
	if(metadata){
		met += '<div class="catalog_content_layer col-md-6">';
		met += '	<div class="col-md-9">';
		met += '		<p class="catalog_content_title block-with-text">'+ metadata['defaultTitle'] +'</p>';
		met += '		<p class="catalog_content_abstract block-with-text">'+ metadata['abstract'] +'</p>';
		met += '	</div>';
		met += '	<div class="col-md-3 catalog_content_lateral">';
		met += '		<div class="catalog_content_thumbnail">';
		
		var image_src = "";
		if("image" in metadata){
			for(var i=0; i<metadata["image"].length; i++){
				var image_info = metadata["image"][i].split("|");
				if(image_info[0] == "overview"){
					image_src = image_info[1];
					break;
				}
			}
		}
		met += '			<img src="'+image_src+'" style="width:100%;" onerror="this.src=\'/gvsigonline/static/img/no_thumbnail.jpg\';"/>';
		met += '		</div>';
		met += '	</div>';
		met += '	<div class="col-md-12">';
		met += '			<div class="catalog_content_button_place col-md-4"><div name="'+ metadata['geonet:info']['uuid'] +'" class="catalog_content_button catalog_details">Details</div></div>';
		met += '			<div class="catalog_content_button_place col-md-4"><div name="'+ metadata['geonet:info']['uuid'] +'" class="catalog_content_button catalog_linkmap">Map</div></div>';
		met += '			<div class="catalog_content_button_place col-md-4"><div name="'+ metadata['geonet:info']['uuid'] +'" class="catalog_content_button catalog_download">Download</div></div>';
		met += '	</div>';
		met += '</div>';
	}else{
		met += '<div class="no_catalog_content col-md-12">';
		met += '<i class="fa fa-ban" aria-hidden="true"></i>   ';
		met += 'No se encontraron resultados';
		met += '</div>';
	}
	return met;
}

catalog.prototype.getKeywordQuery = function(keywords, key){
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

catalog.prototype.createResourceLink = function(links){
	var link = links.split('|');
	var content = '';
	if(link.length==6){
		var type = link[4].trim();
		if(type.startsWith("text/")){
			content += '<li class="catalog-link">';
			content += '	<a href="'+link[2]+'" target="_blank">';
			content += '		<i class="fa fa-globe" aria-hidden="true"></i>';
			content += '		<span>' + link[1] + '</span>';
			content += '		<div class="catalog-link-button catalog_content_button">'+gettext("Go")+'</div>';
			content += '		<div style="clear:both"></div>';
			content += '	</a>';
			content += '</li>';
		}else{
			if(type == "application/zip"){
				content += '<li class="catalog-link">';
				content += '	<a href="'+link[2]+'" target="_blank">';
				content += '		<i class="fa fa-file-archive-o" aria-hidden="true"></i>';
				content += '		<span class="catalog-link-resource"><p>' + link[1] + '<br/><span class="catalog-entry-subtitle">' + link[0] + '</span></p></span>';
				content += '		<div class="catalog-link-button catalog_content_button">'+gettext("Download")+'</div>';content += '		<div style="clear:both"></div>';
				content += '	</a>';
				content += '</li>';
			}
		}
		
	}
	return content;
}


catalog.prototype.createResourceMap = function(links){
	var link = links.split('|');
	var content = '';
	if(link.length==6){
		var type = link[4].trim();
		if(!type.startsWith("text/") && type != "application/zip"){
			content += '<li class="catalog-link">';
			content += '	<a>';
			content += '		<i class="fa fa-map-o" aria-hidden="true"></i>';
			content += '		<span class="catalog-link-resource"><p>' + link[1] + '<br/><span class="catalog-entry-subtitle">' + link[0] + '</span></p></span>';
			content += '		<div class="catalog-link-button catalog_content_button catalog_add_layer" url="'+link[2]+'" name="' + link[0] + '" title="' + link[1] + '">'+gettext("Add")+'</div>';
			content += '		<div style="clear:both"></div>';
			content += '	</a>';
			content += '</li>';
		}
		
	}
	return content;
}

catalog.prototype.linkResourceMap = function(){
	var self = this;
	
	$(".catalog_add_layer").unbind("click").click(function(){
		var url = $(this).attr("url");
		var name = $(this).attr("name");
		var title = $(this).attr("title");
		
		var catalogLayer = new ol.layer.Tile({
	          source: new ol.source.TileWMS({
	            url: url,
	            params: {'LAYERS': name, 'TILED': true},
	            serverType: 'geoserver',
	          }),
	          id : "geonetwork-" + name
		});
		
		self.map.addLayer(catalogLayer);
		
		var groupEntry = $("#geonetwork-group");
		if(groupEntry.length == 0){
			self.createLayerGroup();
		}
		
		var group_visible = false;
		group_visible = $("#layergroup-geonetwork-group").is(":checked");
		self.createLayer(name, title, group_visible, groupEntry.length);
		
		$('#modal-catalog').modal('hide');
		self.hidePanel();
	});
}


catalog.prototype.createLayerGroup = function() {
	var self = this;
	var groupId = 'geonetwork-group';
	
	var tree = '';
	tree += '			<li class="box box-default collapsed-box" id="' + groupId + '">';
	tree += '				<div class="box-header with-border">';
	tree += '					<input type="checkbox" class="layer-group" id="layergroup-' + groupId + '">';
	tree += '					<span class="text">' + gettext("Geonetwork layers") + '</span>';
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
	
	$(".layer-group").unbind("change").change(function (e) {
		var groupId = 'geonetwork-layer-group'; 
		var checked = this.checked;
		
		$("."+groupId+" .layer-box").each(function(){
			var id = $(this).attr("data-layerid");
			var layers = self.map.getLayers();
			
			layers.forEach(function(layer){
				if (!layer.baselayer) {
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
				};
			}, this);
		})
	});
}

catalog.prototype.createLayer = function(name, title, group_visible, zIndex) {
	var id = "geonetwork-" + name;
	
	var ui = '';
	ui += '<div id="layer-box-' + id + '" data-layerid="' + id + '" data-zindex="'+ (100 + zIndex) +'" class="box layer-box thin-border box-default collapsed-box">';
	ui += '		<div class="box-header with-border">';
	if (group_visible) {
		ui += '		<input type="checkbox" id="' + id + '" class="geonetwork-ck" disabled checked>';
	}else{
		ui += '		<input type="checkbox" id="' + id + '" class="geonetwork-ck" checked>';
	}
	ui += '			<span class="text">' + title + '</span>';
	ui += '		</div>';
	ui += '</div>';
	
	$(".geonetwork-layer-group").append(ui);
	
	$(".geonetwork-ck").unbind("change").change(function (e) {
		var layers = self.map.getLayers();
		layers.forEach(function(layer){
			if (!layer.baselayer) {
				if (layer.get("id") === this.id) {
					if (layer.getVisible() == true) {
						layer.setVisible(false);
					} else {
						layer.setVisible(true);
					}
				}
			};
		}, this);
	});
	

};

catalog.prototype.getCatalogFilters = function(query, search, categories, keywords, resources, creation_from, creation_to, date_from, date_to, extent){
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

	//var url = 'http://localhost:8080/geonetwork/srv/spa/q?_content_type=json'+filters+'&bucket=s101&facet.q='+query+'&fast=index&resultType=details&sortBy=relevance';
	var url = '/gvsigonline/catalog/get_query/?_content_type=json'+filters+'&bucket=s101&facet.q='+query+'&fast=index&resultType=details&sortBy=relevance';
	$.ajax({
		url: url,
		success: function(response) {
			try{
				response = JSON.parse(response);
				self.data = {};
				
				var filter_code = '';
				for(var idx = 0; idx < response.summary.dimension.length; idx++){
					var cat = response.summary.dimension[idx];
					if('category' in cat && Array.isArray(cat.category) && cat.category.length > 0){
						filter_code += '<ul class="catalog_filter_cat"><p class="catalog_filter_title">'+ cat['@label'] +'</p>';
						for(var idx2 = 0; idx2 < cat.category.length; idx2++){
							var entry = cat.category[idx2];
							filter_code += self.getCatalogEntry(query, cat, entry);
						}
						filter_code += '</ul>';
					}
					if('category' in cat && '@value' in cat.category){
						filter_code += '<ul class="catalog_filter_cat"><p class="catalog_filter_title">'+ cat['@label'] +'</p>';
						var entry = cat.category;
						filter_code += self.getCatalogEntry(query, cat, entry);
						filter_code += '</ul>';
					}
					
				}
				$("#catalog_filter").html(filter_code);
				
				
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
					self.data[metadata['geonet:info']['uuid']] = metadata;
				}
				$("#catalog_content").html(content_code);
				
				
				$(".catalog_details").unbind("click").click(function(){
					var id = $(this).attr("name");
					$('.modal-catalog-title').html(gettext("Details"));
					var links = self.data[id].link;
					
					var content = "";
//					var url = '/gvsigonline/catalog/get_editor/'+id+"/";	
//						$.ajax({
//						url: url,
//						success: function(response) {
//							console.log(response);
//							var aux_content = "";
//							aux_content += '<div style="padding: 10px">' + response;
//							aux_content += '<div style="clear:both"></div>';
//							aux_content += '</div>';
//							$('.modal-catalog-body').html(aux_content);
//							$('#modal-catalog').modal('show');
//						}
//					});
					
					var aux_content = "";
					var data = self.data[id];
					aux_content += '<div style="padding: 10px">';
					aux_content += '<ul>';
					for(var key in data){
						aux_content += '<li class="catalog-link">';
						aux_content += '	<a href="#">';
						aux_content += '		<span class="catalog-link-resource"><p style="font-weight: bold">' + key + '';
						if(Array.isArray(data[key])){
							aux_content += '		</p></span>';
							aux_content += '		<div style="clear:both"></div>';
							aux_content += '		<ul>';
							for(var i=0; i<data[key].length; i++){
								aux_content += '		<li class="catalog-link-li catalog-entry-subtitle">' + data[key][i] + '</li>';
							}
							aux_content += '		</ul>';
						}else{
							aux_content += '		</p></span>';
							aux_content += '		<div style="clear:both"></div>';
							aux_content += '		<span class="catalog-entry-subtitle" style="float:left; margin-left: 20px">' + data[key] + '</span>';
							aux_content += '		<div style="clear:both"></div>';
						}
						
						aux_content += '	</a>';
						aux_content += '</li>';
					}
					aux_content += '</ul>';
					aux_content += '</div>';
					$('.modal-catalog-body').html(aux_content);
					$('#modal-catalog').modal('show');
					
				});
				
				
				$(".catalog_download").unbind("click").click(function(){
					var id = $(this).attr("name");
					$('.modal-catalog-title').html(gettext("List of downloads"));
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
					content += aux_content + "<ul>";
					
					if(aux_content.length == 0){
						aux_content += '<div style="padding: 10px">';
						aux_content += '<div class="no_catalog_content col-md-12">';
						aux_content += '<i class="fa fa-ban" aria-hidden="true"></i>   ';
						aux_content += 'No se encontraron resultados';
						aux_content += '</div>';
						aux_content += '<div style="clear:both"></div>';
						aux_content += '</div>';
						
						content = aux_content;
					}
					
					$('.modal-catalog-body').html(content);
					$('#modal-catalog').modal('show');
				});
				
				$(".catalog_linkmap").unbind("click").click(function(){
					var id = $(this).attr("name");
					$('.modal-catalog-title').html(gettext("List of layers"));
					var links = self.data[id].link;
					
					var content = "<ul>";
					var aux_content = "";
					if(Array.isArray(links)){
						for(var i=0; i<links.length; i++){
							aux_content += self.createResourceMap(links[i]);
						}
					}else{
						if(links){
							aux_content += self.createResourceMap(links);
						}
					}
					content += aux_content + "<ul>";
					
					if(aux_content.length == 0){
						aux_content += '<div style="padding: 10px">';
						aux_content += '<div class="no_catalog_content col-md-12">';
						aux_content += '<i class="fa fa-ban" aria-hidden="true"></i>   ';
						aux_content += 'No se encontraron resultados';
						aux_content += '</div>';
						aux_content += '<div style="clear:both"></div>';
						aux_content += '</div>';
						
						content = aux_content;
					}
					
					$('.modal-catalog-body').html(content);
					$('#modal-catalog').modal('show');
					
					self.linkResourceMap();
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
			content_code = self.getMetadataEntry(null);
			$("#catalog_content").html(content_code);
		}
	});
}

catalog.prototype.showPanel = function(){
	this.catalog_panel.show();
	this.map_container.hide();
	if(!this.catalog_map){
		this.catalog_map = new CatalogMap(this, "catalog_map");
	}
}

catalog.prototype.hidePanel = function(){
	this.map_container.show();
	this.catalog_panel.hide();
}

