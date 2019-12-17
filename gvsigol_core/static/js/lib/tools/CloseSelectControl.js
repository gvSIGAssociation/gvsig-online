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
var CloseSelectControl = function(map, toolbar) {
	var self = this;
	
	this.map = map;
	this.toolbar = toolbar;
	
	this.control = new ol.control.Toggle({	
		html: '<i class="fa fa-times" ></i>',
		className: "edit",
		title: gettext('Close selection tools'),
		onToggle: function(active){
			for (var i=0; i<toolbar.controlArray.length; i++) {
				toolbar.controlArray[i].deactivate();
			}
			map.removeControl(toolbar);
			$('#get-feature-info').attr("disabled", false);
			$('#get-feature-info').css("cursor", "pointer");
			this.toggle();
		}
	});
	toolbar.addControl(this.control);

};

CloseSelectControl.prototype.close = function(e) {
	for (var i=0; i<this.toolbar.controlArray.length; i++) {
		this.toolbar.controlArray[i].deactivate();
	}
	this.map.removeControl(this.toolbar);
	$('#get-feature-info').attr("disabled", false);
	$('#get-feature-info').css("cursor", "pointer");

};