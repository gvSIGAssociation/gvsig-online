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
var bottomPanel = function(layer, map) {	
	this.isVisible = false;
	this.animationDuration = 500;
	this.animationEasing = 'linear';
	
	this.initialize();
};

/**
 * TODO
 */
bottomPanel.prototype.initialize = function() {
};

/**
 * TODO
 */
bottomPanel.prototype.hidePanel = function() {
    $('.panel-wrapper').animate(
    	{bottom : -(bottomPanel.getAnimationOffset())}, 
    	bottomPanel.animationDuration, 
    	bottomPanel.animationEasing, function() {
    		bottomPanel.isVisible = false;
    	}
    );
};

/**
 * TODO
 */
bottomPanel.prototype.showPanel = function() {
	$('.panel-wrapper').animate(
		{bottom : 0}, 
		bottomPanel.animationDuration, 
		bottomPanel.animationEasing, function() {
			bottomPanel.isVisible = true;
		}
	);
};


/**
 * TODO
 */
bottomPanel.prototype.togglePanel = function() {
	((this.isVisible) ? this.hidePanel : this.showPanel)();
};

/**
 * TODO
 */
bottomPanel.prototype.getAnimationOffset = function() {
	return $('.panel-content').height();
};