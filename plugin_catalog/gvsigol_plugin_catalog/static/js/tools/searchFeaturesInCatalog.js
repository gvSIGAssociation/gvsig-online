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
 * @author: Cesar Martinez Izquierdo <cmartinez@scolab.es>
 */


/**
 * TODO
 */
var SearchFeaturesInCatalog = function(map, conf, extraParams) {

	this.map = map;
	this.conf = conf;

	this.id = "search-from-vector-features";

	var button = document.createElement('button');
	button.setAttribute("id", this.id);
	button.setAttribute("class", "toolbar-button");
	button.setAttribute("title", gettext('Search in catalog'));
	var icon = document.createElement('i');
	icon.setAttribute("class", "fa fa-newspaper-o");
	button.appendChild(icon);

	this.$button = $(button);

	$('#toolbar').append(button);

	var this_ = this;

	var handler = function(e) {
		this_.toggle(e);
	};

	button.addEventListener('click', handler, false);
	button.addEventListener('touchstart', handler, false);

};

/**
 * TODO
 */
SearchFeaturesInCatalog.prototype.active = false;

/**
 * TODO
 */
SearchFeaturesInCatalog.prototype.deactivable = true;

/**
 * TODO
 */
SearchFeaturesInCatalog.prototype.mapCoordinates = null;

/**
 * TODO
 */
SearchFeaturesInCatalog.prototype.popup = null;


SearchFeaturesInCatalog.prototype.activePage = 1;

SearchFeaturesInCatalog.prototype.selectedFeatures = null;

SearchFeaturesInCatalog.prototype.onSelect = null;


/**
 * @param {Event} e Browser event.
 */
SearchFeaturesInCatalog.prototype.toggle = function(e) {
	var self = this;
	e.preventDefault();
	if (this.active) {
		this.deactivate();
	} else {
		viewer.core.disableTools(this.id);
		if (this.popup == null) {
			this.popup = new ol.Overlay.Popup({
				closeBox: true,
				onclose: function(evt){
					self.selectInteraction.getFeatures().clear()
				}
			});
			this.popup.addPopupClass('search-in-catalog-popup');
			this.map.addOverlay(this.popup);
		}

		this.$button.addClass('button-active');
		this.active = true;
		this.$button.trigger('control-active', [this]);
		
		var selectClick = new ol.interaction.Select({
			condition: ol.events.condition.click
			});

		// select interaction working on "pointermove"
		var selectPointerMove = new ol.interaction.Select({
			condition: ol.events.condition.pointerMove
		});
		this.selectInteraction = selectClick;
		this.map.addInteraction(this.selectInteraction);
		
		this.map.un('click', this.clickHandler, this);
		this.map.on('click', this.clickHandler, this);
		
	}
};


/**
 * Handle pointer click.
 * @param {ol.MapBrowserEvent} evt
 */

SearchFeaturesInCatalog.prototype.clickHandler = function(evt) {
	//evt.preventDefault();
	var self = this;
	var mapCoordinates = evt.coordinate;
	if (this.selectInteraction!=null && this.onSelect!=null) {
		this.selectInteraction.un('select', this.onSelect);
	}
	this.onSelect = function(e) {
		self.showPopup(e.target.getFeatures(), mapCoordinates);
	}
	this.selectInteraction.on('select', this.onSelect);
};

SearchFeaturesInCatalog.prototype._updatePages = function(newPage, totalPages){
	if (newPage <= 1) {
		newPage = 1;
		$('#search_feat_in_catalog_previous').parent().addClass('disabled');
	}
	else {
		$('#search_feat_in_catalog_previous').parent().removeClass('disabled');
	}
	if (newPage >= totalPages) {
		newPage = totalPages;
		$('#search_feat_in_catalog_next').parent().addClass('disabled');
	}
	else {
		$('#search_feat_in_catalog_next').parent().removeClass('disabled');
	}
	this.activePage = newPage;

	$('#search_feat_in_catalog_current_page').html(newPage);
	$('.search_feat_in_catalog_page').each(function(index, element) {
		if ((index + 1) == newPage) {
			$(element).removeClass('hidden');
		}
		else {
			$(element).addClass('hidden');
		}
	});
};

/**
 * TODO
 */
SearchFeaturesInCatalog.prototype.showPopup = function(features, coordinates){
	if (!this.active) {
		return;
	}
	var self = this;
	this.activePage = 1;
	this.selectedFeatures = features.getArray();
	
	var html = '<div class="container-fluid">';
	html += '<div class="row"><div class="col-12"><h4>' + gettext('Catalog search') + '</h4></div></div>';
	html += '<div class="row"><div class="col-xs-8" style="padding-left: 0px; padding-right: 0px"><input id="input_search_feat_in_catalog" type="text" class="form-control"></div><div class="col-xs-4" style="padding-left: 0px"><button id="search_feat_in_catalog_button" class="btn btn-default" type="button">Search</button></div></div>';
	var featArray = features.getArray();
	/**
	 * for debugging multi-selection
	if (featArray.length==1) {
		featArray = [featArray0[0], featArray0[0], featArray0[0], featArray0[0]];
	}
	*/
	for (var i=0; i<featArray.length; i++) {
		if (i>0) {
			html += '<div class="search_feat_in_catalog_page row hidden" data-featid="' + i + '"><div class="col-12">';
		}
		else {
			html += '<div class="search_feat_in_catalog_page row" data-featid="' + i + '"><div class="col-12">';
		}
		
		var f = featArray[i];
		html += '<table class="table table-condensed" style="margin-bottom: 0px"><tr><th>Field</th><th>Value</th><th></th></tr>'
		var keys = f.getKeys();
		for (var j=0; j<keys.length; j++) {
			var key = keys[j];
			if (key != f.getGeometryName()) {
				var value = f.get(key);
				var keyHtml = $('<td></td>');
				/**
				 * Use text() and outerHTML to avoid code injection from external data
				 */
				keyHtml.text(key);
				var valueHtml = $('<td class="field-value"></td>');
				valueHtml.text(value);
				var btnHtml = $('<td><a class="add-to-search-button" href="#"><i class="fa fa-plus"></i></a></td>');
				var rowHtml = $('<tr></tr>');
				rowHtml.append(keyHtml);
				rowHtml.append(valueHtml);
				rowHtml.append(btnHtml);
				html += rowHtml[0].outerHTML;
			}
		}
		html += '</table></div></div>';
	};
	if (featArray.length>1) {
		html += '<div class="row"><div class="col-md-8 col-md-offset-4">';
		html += '<nav><ul id="search_feat_in_catalog_pager" class="pagination" style="margin-top: 10px">';
		html += '<li><a id="search_feat_in_catalog_previous" href="#" aria-label="Previous"><span aria-hidden="true">&laquo;</span></a></li>';
		html += '<li><span><span id="search_feat_in_catalog_current_page">1</span> / ' + featArray.length + '</span></li>';
		html += '<li><a id="search_feat_in_catalog_next" href="#" aria-label="Next"><span aria-hidden="true">&raquo;</span></a></li>';
		html += '</ul></nav>';
		html += '</div></div>';
	}
	this.map.addOverlay(this.popup);
	this.popup.show(coordinates, '<div class="popup-wrapper searchfeaturesincatalog-popup">' + html + '</div>');
	//self.map.getView().setCenter(coordinates);
	$('#search_feat_in_catalog_previous').off('click').on('click', function(evt){
		var newPage = self.activePage - 1;
		self._updatePages(newPage, featArray.length);
	});
	$('#search_feat_in_catalog_next').off('click').on('click', function(evt){
		var newPage = self.activePage + 1;
		self._updatePages(newPage, featArray.length);
	});
	
	$('.add-to-search-button').off('click').on('click', function(evt){
		var value = new $(this).parent().siblings('.field-value').first().text();
		var oldSearchString = $('#input_search_feat_in_catalog').val();
		if (oldSearchString!="") {
			$('#input_search_feat_in_catalog').val(oldSearchString + " " + value);
		}
		else {
			$('#input_search_feat_in_catalog').val(value);
		}  
	});
	
	$('#search_feat_in_catalog_button').off('click').on('click', function(evt){
		var value = $('#input_search_feat_in_catalog').val();
		var geom = null;
		$('.search_feat_in_catalog_page').each(function(index, element) {
			if (!$(element).hasClass('hidden')) {
				var theFeat = self.selectedFeatures[element.getAttribute('data-featid')];
				if (theFeat) {
					geom = theFeat.getGeometry();
				}
			}
		});

		viewer.core.catalog.showPanel(value, geom);
	});
};

SearchFeaturesInCatalog.prototype.deactivate = function() {
	this.$button.removeClass('button-active');
	this.map.un('click', this.clickHandler, this);
	if (this.selectInteraction != null) {
		if (this.onSelect != null) {
			this.selectInteraction.un('select', this.onSelect);
		}
		this.selectInteraction.getFeatures().clear()
		this.selectInteraction.setActive(false);
		var interct = this.map.removeInteraction(this.selectInteraction);
	}
	this.active = false;
};