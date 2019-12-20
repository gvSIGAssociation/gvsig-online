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
var MeasureToolBar = function(map) {
	var self = this;
	this.map = map;
	this.toolBar = new ol.control.Bar({ toggleOne: true, group:true });
	
	this.toolBar.controlArray = new Array();
	this.measureLengthControl = new MeasureLengthControl(this.map, this.toolBar);
	this.measureAreaControl = new MeasureAreaControl(this.map, this.toolBar);
	this.measureAngleControl = new MeasureAngleControl(this.map, this.toolBar);
	this.toolBar.controlArray.push(this.measureLengthControl);
	this.toolBar.controlArray.push(this.measureAreaControl);
	this.toolBar.controlArray.push(this.measureAngleControl);
	this.closeMeasureControl = new CloseMeasureControl(this.map, this.toolBar);
	
	this.toolBar.closeControl = this.closeMeasureControl;
	
	var button = '<li role="presentation"><a id="show_measure_toolbar" role="menuitem" tabindex="-1" href="#"><i style="margin-right: 8px;" class="icon-measure-length"></i>'+gettext("Show measure tools")+'</a></li>';
	$('#gvsigol-navbar-file-menu').append(button);
	
	$('#show_measure_toolbar').click(function(e){
		//self.map.addControl(self.toolBar);
		
		if (viewer.core.getActiveToolbar() != null) {
			viewer.core.getActiveToolbar().closeControl.close();
		}
		self.map.addControl(self.toolBar);
		viewer.core.setActiveToolbar(self.toolBar);
	});

};