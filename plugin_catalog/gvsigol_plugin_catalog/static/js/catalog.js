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
var CatalogView = function(map, layerTree) {
	this.map = map;
	this.map_container = $("#container");	
	this.layerTree = layerTree;
	this.catalog_panel = null;
	this.catalog_map = null;
	this.data = {};
	this.initialization();
};

CatalogView.prototype.initialization = function(){
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
	catalogPanel += '				<input type="text" class="form-control input-lg ng-pristine ng-untouched ng-valid ng-empty" id="gn-any-field" placeholder="Search..." data-ng-keyup="$event.keyCode == 13 &amp;&amp; triggerSearch()" data-typeahead="address for address in getAnySuggestions($viewValue)" data-typeahead-loading="anyLoading" data-typeahead-min-length="1" data-typeahead-focus-first="false" data-typeahead-wait-ms="300" aria-autocomplete="list" aria-expanded="false" aria-owns="typeahead-310-2994">';

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
	catalogPanel += '			<div class="">';
	catalogPanel += '               <div class="btn-group btn-group-xs">';
	catalogPanel += '      			     <span data-translate="" class="ng-scope ng-binding"><strong>Categorías</strong>';
	catalogPanel += ' 		        </div>';
	catalogPanel += ' 		        <br>';
	catalogPanel += '				<input type="text" id="categoriesF" placeHolder="Separado por \';\'    P.ej: cat_1;cat_2;..." value="" class="form-control"/>';
	catalogPanel += '   		</div>';
	catalogPanel += '			<div class="">';
	catalogPanel += '               <div class="btn-group btn-group-xs">';
	catalogPanel += '      			     <span data-translate="" class="ng-scope ng-binding"><strong>Palabras clave</strong>';
	catalogPanel += ' 		        </div>';
	catalogPanel += ' 		        <br>';
	catalogPanel += '       		<input type="text" id="keywordsF" placeHolder="Separado por \';\'    P.ej: cat_1;cat_2;..." value="" class="form-control"/>';
	catalogPanel += '	      	</div>';
	catalogPanel += '      		<div class="">';
	catalogPanel += '               <div class="btn-group btn-group-xs">';
	catalogPanel += '      			     <span data-translate="" class="ng-scope ng-binding"><strong>Contacto para el recurso</strong>';
	catalogPanel += ' 		        </div>';
	catalogPanel += ' 		        <br>';
	catalogPanel += ' 			    <input type="text" id="orgNameF" placeHolder="Separado por \';\'    P.ej: cat_1;cat_2;..." value="" class="form-control"/>';
	catalogPanel += '   		</div>';
	catalogPanel += ' 		</div>';
	catalogPanel += '    	<div class="catalog_search_advanced_col col-md-4">';
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

CatalogView.prototype.filterCatalog = function(){
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
		met += '			<img src="'+image_src+'" style="width:100%;"/>';
		met += '		</div>';
		met += '	</div>';
		met += '	<div class="col-md-12">';
		met += '			<div class="catalog_content_button_place col-md-4">';
		met += '				<a name="'+ metadata['geonet:info']['uuid'] +'" href="#" class="btn btn-block btn-social btn-custom-tool catalog_content_button catalog_details">';
		met += ' 					<i class="fa fa-search" aria-hidden="true"></i>Details';
		met += '				</a>';
		met += '			</div>';
		met += '			<div class="catalog_content_button_place col-md-4">';
		met += '				<a name="'+ metadata['geonet:info']['uuid'] +'" href="#" class="btn btn-block btn-social btn-custom-tool catalog_content_button catalog_linkmap">';
		met += ' 					<i class="fa fa-map-o" aria-hidden="true"></i>Map';
		met += '				</a>';
		met += '			</div>';
		met += '			<div class="catalog_content_button_place col-md-4">';
		met += '				<a name="'+ metadata['geonet:info']['uuid'] +'" href="#" class="btn btn-block btn-social btn-custom-tool catalog_content_button catalog_download">';
		met += ' 					<i class="fa fa-download" aria-hidden="true"></i>Download';
		met += '				</a>';
		met += '			</div>';
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
				content += '		<div class="catalog-link-button catalog_content_button">'+gettext("Download")+'</div>';
				content += '		<div style="clear:both"></div>';
				content += '	</a>';
				content += '</li>';
			}
		}
		
	}
	return content;
}


CatalogView.prototype.createResourceMap = function(id, links){
	var link = links.split('|');
	var content = '';
	if(link.length==6){
		var type = link[4].trim();
		if(!type.startsWith("text/") && type != "application/zip"){
			content += '<li class="catalog-link">';
			content += '	<a>';
			content += '		<i class="fa fa-map-o" aria-hidden="true"></i>';
			content += '		<span class="catalog-link-resource"><p>' + link[1] + '<br/><span class="catalog-entry-subtitle">' + link[0] + '</span></p></span>';
			content += '		<div data-id="'+ id +'" class="catalog-link-button catalog_content_button catalog_add_layer" url="'+link[2]+'" name="' + link[0] + '" title="' + link[1] + '">'+gettext("Add")+'</div>';
			content += '		<div style="clear:both"></div>';
			content += '	</a>';
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
		
		var catalogLayer = new ol.layer.Tile({
	          source: new ol.source.TileWMS({
	            url: url,
	            params: {
	            	'LAYERS': name, 
	            	'TILED': true, 
	            	'dataid': id
	            },
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


CatalogView.prototype.createLayerGroup = function() {
	var self = this;
	var groupId = 'geonetwork-group';
	
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
	
	$(".layer-tree-groups").sortable({
		placeholder: "sort-highlight",
		handle: ".handle",
		forcePlaceholderSize: true,
		zIndex: 999999
	});
	var self = this;
	$(".layer-tree-groups").on("sortupdate", function(event, ui){
		self.reorder(event, ui);
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


CatalogView.prototype.createLayer = function(name, title, group_visible, zIndex) {
	var self = this;
	
	var id = "geonetwork-" + name.replace(":", "-");
	var id2 = "geonetwork-" + name;
	
	var ui = '';
	ui += '<div id="layer-box-' + id + '" data-layerid="' + id2 + '" data-zindex="'+ (100 + zIndex) +'" class="box layer-box thin-border box-default collapsed-box">';
	ui += '		<div class="box-header with-border">';
	ui += '			<span class="handle"> ';
	ui += '				<i class="fa fa-ellipsis-v"></i>';
	ui += '				<i class="fa fa-ellipsis-v"></i>';
	ui += '			</span>';
	if (group_visible) {
		ui += '		<input type="checkbox" id="' + id2 + '" class="geonetwork-ck" disabled checked>';
	}else{
		ui += '		<input type="checkbox" id="' + id2 + '" class="geonetwork-ck" checked>';
	}
	ui += '			<span class="text">' + title + '</span>';
	ui += '			<div class="box-tools pull-right">';
	ui += '				<button class="btn btn-box-tool btn-box-tool-custom" data-widget="collapse">';
	ui += '					<i class="fa fa-plus"></i>';
	ui += '				</button>';
	ui += '			</div>';
	ui += '			</div>';
	ui += '		<div class="box-body" style="display: none;">';
	ui += '			<a id="show-metadata-' + id + '" data-layerid="' + id2 + '" class="btn btn-block btn-social btn-custom-tool show-metadata-link show-metadata-link2">';
	ui += '				<i class="fa fa-external-link"></i> ' + gettext('Layer metadata');
	ui += '			</a>';
	
	ui += '	<a id="zoom-to-layer-' + id + '" href="#" data-layerid="' + id2 + '" class="btn btn-block btn-social btn-custom-tool zoom-to-layer zoom-to-layer2">';
	ui += '		<i class="fa fa-search" aria-hidden="true"></i> ' + gettext('Zoom to layer');
	ui += '	</a>';
	
	ui += '			<a id="remove-metadata-' + id + '" data-layerid="' + id2 + '" class="btn btn-block btn-social btn-custom-tool remove-metadata-link">';
	ui += '				<i class="fa fa-times"></i> ' + gettext('Remove layer');
	ui += '			</a>';
		
	ui += '			<label style="display: block; margin-top: 8px; width: 95%;">' + gettext('Opacity') + '<span id="layer-opacity-output-' + id + '" class="margin-l-15 gol-slider-output">%</span></label>';
	ui += '			<div id="layer-opacity-slider" data-layerid="' + id2 + '" class="layer-opacity-slider"></div>';
	ui += '		</div>';
	ui += '</div>';
	
	$(".geonetwork-layer-group").append(ui);
	
	$(".geonetwork-ck").unbind("change").change(function (e) {
		try {
			var layers = self.map.getLayers();
			var id = $(this).attr("id");
			layers.forEach(function(layer){
				if (!layer.baselayer) {
					if (layer.get("id") === id) {
						if (layer.getVisible() == true) {
							layer.setVisible(false);
						} else {
							layer.setVisible(true);
						}
					}
				};
			}, this);
		} catch (e) {
			console.log(e);
		}
	});
	
	$(".remove-metadata-link").unbind("click").click(function (e) {
		var id = $(this).attr("data-layerid");
		var layers = self.map.getLayers();
		layers.forEach(function(layer){
			if (!layer.baselayer) {
				if (layer.get("id") === id) {
					layer.setVisible(false);
					self.map.removeLayer([layer]);
					$("#layer-box-" + id.replace(":", "-")).remove();
				}
			};
		}, this);
	});
	
	$( "#layer-box-" + id + " .layer-opacity-slider" ).slider({
	    min: 0,
	    max: 100,
	    value: 100,
	    slide: function( event, ui ) {
	    	var layers = self.map.getLayers();
			var id = this.dataset.layerid;
			layers.forEach(function(layer){
				if (!("baselayer" in layer) || layer.baselayer == false) {
					if (id===layer.get("id")) {
						layer.setOpacity(parseFloat(ui.value)/100);
						$("#layer-opacity-output-" + id).text(ui.value + '%');
					}
				}						
			}, this);
	    }
	});
	
	$(".opacity-range").unbind("change").on('change', function(e) {
		var layers = self.map.getLayers();
		var id = $(this).attr("data-layerid");
		layers.forEach(function(layer){
			if (!("baselayer" in layer) || layer.baselayer == false) {
				if (id===layer.get("id")) {
					layer.setOpacity(this.valueAsNumber/100);
				}
			}						
		}, this);
	});
	
	$(".zoom-to-layer2").unbind("click").on('click', function(e) {
		var layers = self.map.getLayers();
		var selectedLayer = null;
		var id = $(this).attr("data-layerid");
		layers.forEach(function(layer){
			if (!("baselayer" in layer) || layer.baselayer == false) {
				if (id===layer.get("id")) {
					selectedLayer = layer;
				}
			}						
		}, this);
		self.zoomToLayer(selectedLayer);
	});
	
	$(".show-metadata-link2").unbind("click").on('click', function(e) {
		var layers = self.map.getLayers();
		var selectedLayer = null;
		var id = $(this).attr("data-layerid");
		layers.forEach(function(layer){
			if (!("baselayer" in layer) || layer.baselayer == false) {
				if (id===layer.get("id")) {
					selectedLayer = layer;
					self.createDetailsPanel(selectedLayer.getSource().getParams()["dataid"]);
				}
			}						
		}, this);
		//self.showMetadata(selectedLayer);
	});
	

};

CatalogView.prototype.zoomToLayer = function(layer) {
	var self = this;
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

	//var url = 'http://localhost:8080/geonetwork/srv/spa/q?_content_type=json'+filters+'&bucket=s101&facet.q='+query+'&fast=index&resultType=details&sortBy=relevance';
	//var url = '/gvsigonline/catalog/get_query/?_content_type=json'+filters+'&bucket=s101&facet.q='+query+'&fast=index&resultType=details&sortBy=relevance';
	//var url = '/geonetwork/srv/eng/q?_content_type=json&bucket=s101&facet.q=&fast=index&from=1&resultType=details&sortBy=relevance';

	// TODO: move config to plugin settings
	var facetsConfig = {"orgName": {"title": "Organization"}, "sourceCatalog": {"title": "Source Catalog"},
"createDateYear": {"title": "Year"}, "spatialRepresentationType": {"title": "Representation type"}, "maintenanceAndUpdateFrequency": {"title": "Update frequencies"}, "denominator": {"title": "Scale"}, "serviceType": {"title": "Service type"}, "gemetKeyword": {"title": "GEMET keywords"}, "panaceaKeyword": [{"name": "interregMedProjects", "title": "INTERREG Med Projects", "labelPattern": ".* project$"}, {"name": "panaceaWorkingGroups", "title": "Working group", "labelPattern": "^(.(?! project$))+$"}]};
	var facetsOrder = ["panaceaWorkingGroups", "interregMedProjects", "type", "spatialRepresentationType"];
	var disabledFacets = ["mdActions"];

        // FIXME: this should be parametrized from config
	var url = '/geonetwork/srv/eng/q?_content_type=json&bucket=s101&facet.q='+query+'&fast=index&from=1&resultType=details&sortBy=relevance';
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
					self.data[metadata['geonet:info']['uuid']] = metadata;
				}
				$("#catalog_content").html(content_code);
				
				
				$(".catalog_details").unbind("click").click(function(){
					var id = $(this).attr("name");
					self.createDetailsPanel(id);
					
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
							aux_content += self.createResourceMap(id, links[i]);
						}
					}else{
						if(links){
							aux_content += self.createResourceMap(id, links);
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

CatalogView.prototype.createDetailsPanel = function(id){
	var self = this;
	
//	var links = self.data[id].link;
//	var content = "";	
//	var aux_content = "";
//	var data = self.data[id];
//	aux_content += '<div style="padding: 10px">';
//	aux_content += '<ul>';
//	for(var key in data){
//		aux_content += '<li class="catalog-link">';
//		aux_content += '	<a href="#">';
//		aux_content += '		<span class="catalog-link-resource"><p style="font-weight: bold">' + key + '';
//		if(Array.isArray(data[key])){
//			aux_content += '		</p></span>';
//			aux_content += '		<div style="clear:both"></div>';
//			aux_content += '		<ul>';
//			for(var i=0; i<data[key].length; i++){
//				aux_content += '		<li class="catalog-link-li catalog-entry-subtitle">' + data[key][i] + '</li>';
//			}
//			aux_content += '		</ul>';
//		}else{
//			aux_content += '		</p></span>';
//			aux_content += '		<div style="clear:both"></div>';
//			aux_content += '		<span class="catalog-entry-subtitle" style="float:left; margin-left: 20px">' + data[key] + '</span>';
//			aux_content += '		<div style="clear:both"></div>';
//		}
//		
//		aux_content += '	</a>';
//		aux_content += '</li>';
//	}
//	aux_content += '</ul>';
//	aux_content += '</div>';
	
	$.ajax({
		type: "GET",
		async: false,
		url: "/gvsigonline/catalog/get_metadata/"+id+"/?getPanel=true",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		success: function(response){
			if ("html" in response) {
				$('.modal-catalog-title').html(gettext("Details"));
				$('.modal-catalog-body').html(response['html']);
				$('#modal-catalog').modal('show');
			} else {
				alert('Error');
			}

		},
		error: function(){}
	});
	
	
	
}

CatalogView.prototype.showPanel = function(){
	this.catalog_panel.show();
	this.map_container.hide();
	if(!this.catalog_map){
		this.catalog_map = new CatalogMap(this, "catalog_map");
	}
}

CatalogView.prototype.hidePanel = function(){
	this.map_container.show();
	this.catalog_panel.hide();
}

