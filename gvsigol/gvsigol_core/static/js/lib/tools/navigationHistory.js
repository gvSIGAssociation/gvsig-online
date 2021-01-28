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
var navigationHistory = function(map, conf) {
	var self = this;
	this.id = "navigation-history";
	
	this.map = map;
	this.conf = conf;
	
	this.history = new Array();        
	this.index = -1;        
	this.maxSize = 500;
	this.eventId = null;
	this.shouldSave = true;

	var nextButton = document.createElement('button');
	nextButton.setAttribute("id", this.id);
	nextButton.setAttribute("class", "toolbar-button");
	nextButton.setAttribute("title", gettext('Vista siguiente'));
	var icon = document.createElement('i');
	icon.setAttribute("class", "fa fa-caret-right");
	icon.setAttribute("aria-hidden", "true");
	nextButton.appendChild(icon);
	this.$nextButton = $(nextButton);
	
	var backButton = document.createElement('button');
	backButton.setAttribute("id", this.id);
	backButton.setAttribute("class", "toolbar-button");
	backButton.setAttribute("title", gettext('Vista anterior'));
	var icon = document.createElement('i');
	icon.setAttribute("class", "fa fa-caret-left");
	icon.setAttribute("aria-hidden", "true");
	backButton.appendChild(icon);
	this.$backButton = $(backButton);
	
	$('.ol-zoom').append(nextButton);
	$('.ol-zoom').append(backButton);

	var nextButtonHandler = function(e) {
		self.nextHandler(e);
	};
	nextButton.addEventListener('click', nextButtonHandler, false);
	nextButton.addEventListener('touchstart', nextButtonHandler, false);
	
	var backButtonHandler = function(e) {
		self.backHandler(e);
	};
	backButton.addEventListener('click', backButtonHandler, false);
	backButton.addEventListener('touchstart', backButtonHandler, false);
	
	this.registerEvents();

};

/**
 * TODO
 */
navigationHistory.prototype.deactivable = false;

/**
 * @param {Event} e Browser event.
 */
navigationHistory.prototype.nextHandler = function(e) {
	if (this.index < this.history.length - 1) {            
		this.index += 1; 
		this.indexChanged();
		this.shouldSave = false;           
		this.map.getView().setProperties(this.history[this.index]);        
	}

};

/**
 * @param {Event} e Browser event.
 */
navigationHistory.prototype.backHandler = function(e) {       
	if (this.index > 0) {            
		this.index -= 1;
		this.indexChanged();
		this.shouldSave = false            
		this.map.getView().setProperties(this.history[this.index]);        
	}
};

/**
 * @param {Event} e Browser event.
 */
navigationHistory.prototype.indexChanged = function() {       
	if (self.index === 0) {            
		this.$backButton.prop("disabled", true);		
	} else {            
		this.$backButton.prop("disabled", false);        
	}        
	
	if (self.history.length - 1 === self.index) {            
		this.$nextButton.prop("disabled", true);        
	} else {            
		this.$nextButton.prop("disabled", false);        
	} 
};

/**
 * @param {Event} e Browser event.
 */
navigationHistory.prototype.registerEvents = function(e) {
	var self = this;
	
	this.map.on('moveend', function (evt) {            
		if (self.shouldSave) {                
			var view = self.map.getView();                
			var viewStatus = {                    
				center: view.getCenter(),                    
				resolution: view.getResolution(),                    
				rotation: view.getRotation()                
			};                
               
			self.history.splice(self.index + 1, self.history.length - self.index - 1);                
			if (self.history.length === self.maxSize) {                    
				self.history.splice(0, 1);                
			} else {                    
				self.index += 1;
				self.indexChanged();
			}                
			self.history.push(viewStatus);
			
		} else {                
			self.shouldSave = true;            
		}        
	});
};