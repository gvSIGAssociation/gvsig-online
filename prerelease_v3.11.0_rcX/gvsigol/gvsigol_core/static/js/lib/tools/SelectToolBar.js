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
var SelectToolBar = function(map) {
	var self = this;
	this.map = map;
	this.toolBar = new ol.control.Bar({ toggleOne: true, group:true });
	
	this.toolBar.controlArray = new Array();
	this.selectFeatureControl = new SelectFeatureControl(this.map, this.toolBar);
	this.selectBoxControl = new SelectBoxControl(this.map, this.toolBar);
	this.selectByBufferControl = new SelectByBufferControl(this.map, this.toolBar);
	this.toolBar.controlArray.push(this.selectFeatureControl);
	this.toolBar.controlArray.push(this.selectBoxControl);
	this.toolBar.controlArray.push(this.selectByBufferControl);
	this.closeSelectControl = new CloseSelectControl(this.map, this.toolBar);
	
	this.toolBar.closeControl = this.closeSelectControl;
	
	var button = '<li role="presentation"><a id="show_select_toolbar" role="menuitem" tabindex="-1" href="#"><i style="margin-right: 8px;" class="fa fa-mouse-pointer"></i>'+gettext("Show selection tools")+'</a></li>';
	$('#gvsigol-navbar-file-menu').append(button);
	
	$('#show_select_toolbar').click(function(e){
		if (viewer.core.getActiveToolbar() != null) {
			viewer.core.getActiveToolbar().closeControl.close();
		}
		self.map.addControl(self.toolBar);
		viewer.core.setActiveToolbar(self.toolBar);		
	});

};