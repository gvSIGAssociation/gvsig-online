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

var viewer = viewer || {};

/**
 * TODO
 */
viewer.core = {
		
	map: null,
	
	layerCount: 0,
		
    initialize: function(conf) {
    	this._createMap(conf);
    	this._createToc(conf);
    },
    
    _createMap: function(conf) {
    	
    	var osm = new ol.layer.Tile({
    		id: this._nextLayerId(),
        	label: gettext('OpenStreetMap'),
          	visible: true,
          	source: new ol.source.OSM()
        });
		osm.baselayer = true;
		
		this.map = new ol.Map({
			interactions: ol.interaction.defaults().extend([
			    new ol.interaction.DragRotateAndZoom()
			]),
      		controls: [
				new ol.control.Zoom(),
				//new ol.control.ScaleLine(),					
      			new ol.control.OverviewMap({collapsed: false})
      		],
      		renderer: 'canvas',
      		target: 'map',
      		layers: [osm],
			view: new ol.View({
        		center: ol.proj.transform([40.39676430557205, -3.4716796875000004], 'EPSG:4326', 'EPSG:3857'),
        		minZoom: 0,
        		maxZoom: 19,
            	zoom: 6
        	})
		});
    },
    
    _createToc: function(conf) {   
    	//jQuery UI sortable for the todo list
    	$(".layer-tree").sortable({
    		placeholder: "sort-highlight",
    		handle: ".handle",
    		forcePlaceholderSize: true,
    		zIndex: 999999
    	});
    	/* The todo list plugin */
    	$(".layer-tree").layerTree({
    		onCheck: function (ele) {
    			window.console.log("The element has been checked");
    			return ele;
    		},
    		onUncheck: function (ele) {
    			window.console.log("The element has been unchecked");
    			return ele;
    		}
    	});
    },
    
    _nextLayerId: function() {
    	return "gol-layer-" + this.layerCount++;
    }
}