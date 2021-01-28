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
 * @author: Francisco J. Peñarrubia <fjp@scolab.es>
 */

var measureAngle3d = function(wwd) {
	this.wwd = wwd;
	
	this.id = "measure-angle-3d";

	var button = document.createElement('button');
	button.setAttribute("id", this.id);
	button.setAttribute("class", "ol-btn-round");
	button.setAttribute("title", gettext('Measure angle'));
	var icon = document.createElement('i');
	icon.setAttribute("class", "icon-measure-angle");
	button.appendChild(icon);
	
	this.$button = $(button);
	
	$('#toolbar3d').append(button);

	var self = this;
  
	var handler = function(e) {
		self._handler(e);
	};

	button.addEventListener('click', handler, false);
	button.addEventListener('touchstart', handler, false);
	
	// 
    this.pathPositions = new Array();
    this.locations = new Array();
    // this.texts = new Array(); // array de text renderables, para poder borrarlos bien.

    this.overlayLayer = new WorldWind.RenderableLayer("Measures");
    this.overlayLayer2 = new WorldWind.RenderableLayer("Measures2");
    this.wwd.addLayer(this.overlayLayer);
    this.wwd.addLayer(this.overlayLayer2);
    
    // Define the path attributes.
    this.pathAttributes = new WorldWind.ShapeAttributes(null);        
    this.pathAttributes.outlineColor = new WorldWind.Color(0,0,1,0.9);
    this.pathAttributes.outlineWidth = 3;

    this.pathAttributes2 = new WorldWind.ShapeAttributes(null);
    this.pathAttributes2.outlineColor = new WorldWind.Color(1, 1, 1, 0.6);
    this.pathAttributes2.outlineWidth = 5;
        
    // Create our measuring objects.
    this.lengthMeasurer = new WorldWind.LengthMeasurer(this.wwd);

    this.clickRecognizer = new WorldWind.ClickRecognizer(this.wwd, this._onWWClick.bind(this));
    this.tapRecognizer = new WorldWind.TapRecognizer(this.wwd, this._onWWClick.bind(this));
    this.clickRecognizer.enabled = false;
    this.tapRecognizer.enabled = false;


};

measureAngle3d.prototype._formatDistance = function(dist) {
    var meters = dist;
    var km = meters / 1000.0;
    var formatted = meters.toLocaleString(navigator.language, { maximumFractionDigits: 2 }) + ' m';
    if (dist > 1000) {
        formatted = km.toLocaleString(navigator.language, { maximumFractionDigits: 1 }) + ' km';
    }
    return formatted;
}


measureAngle3d.prototype.active = false;

measureAngle3d.prototype.deactivable = true;

/**
 * @param {Event} e Browser event.
 */
measureAngle3d.prototype._handler = function(e) {
	e.preventDefault();
		
	if (this.active) {
		this.deactivate();
		
	} else {
		// alert('Activating tool');
		// this.$button.addClass('button-active');
		this.continueLineMsg = gettext('Click to continue measuring');
		this.active = true;
        this.$button.trigger('control-active', [this]);

        this.path = new WorldWind.SurfacePolyline(this.locations, this.pathAttributes);
        this.pathBorder = new WorldWind.SurfacePolyline(this.locations, this.pathAttributes2);    
        this.overlayLayer.addRenderable(this.pathBorder);
        this.overlayLayer.addRenderable(this.path);    
        this._addListeners();
	}
};

/**
 * TODO
 */
measureAngle3d.prototype.isActive = function() {
	return this.active;
};



measureAngle3d.prototype._onWWClick = function(recognizer) {			
    // Obtain the event location.
    var x = recognizer.clientX,
        y = recognizer.clientY;

    // Perform the pick. Must first convert from window coordinates to canvas coordinates, which are
    // relative to the upper left corner of the canvas rather than the upper left corner of the page.
    var pickList = recognizer.target.pick(recognizer.target.canvasCoordinates(x, y));

    // Search for terrain object
    var position = null;
    pickList.objects.forEach(function(obj) {
        if (obj.isTerrain) {
            position = obj.position;
        }
    });
    if (position) {               
    //    console.log(position.latitude + " " + position.longitude);
        this.pathPositions.push(position);
        var distance = this.lengthMeasurer.getLength(this.pathPositions, true, WorldWind.GREAT_CIRCLE);
        var loc = new WorldWind.MeasuredLocation(position.latitude, position.longitude, distance);
        this.locations.push(loc);
        var numPoints = this.pathPositions.length;
        if (numPoints > 1)
        {
            this.path.boundaries = this.locations;
            this.pathBorder.boundaries = this.locations;

            if (numPoints > 2) {
                var pA = this.pathPositions[numPoints-3];
                var pB = this.pathPositions[numPoints-2];
                var pC = this.pathPositions[numPoints-1];

                var v1 = new WorldWind.Vec3(0,0,0);
                var v2 = new WorldWind.Vec3(0,0,0);
                var v3 = new WorldWind.Vec3(0,0,0);

                this.wwd.globe.computePointFromPosition(pA.latitude, pA.longitude, pA.altitude, v1);
                this.wwd.globe.computePointFromPosition(pB.latitude, pB.longitude, pB.altitude, v2);
                this.wwd.globe.computePointFromPosition(pC.latitude, pC.longitude, pC.altitude, v3);

                // Be careful!. Subtract modifies the original vec3. This is the reason
                // we calculate vA after vB
                var vB = v3.subtract(v2);
                var vA = v2.subtract(v1);

                var angleRads = WorldWind.MeasurerUtils.angleBetweenVectors(vA,vB);
                var angleDegrees = angleRads * WorldWind.Angle.RADIANS_TO_DEGREES;
                var angleDMS = WorldWind.Angle.toDMSString(angleDegrees);

                var text = new WorldWind.GeographicText(pB, angleDMS);
                this.overlayLayer.addRenderable(text);
            }
            this.overlayLayer.refresh();
        }
        else {
            this.overlayLayer.removeAllRenderables();
            this.overlayLayer2.removeAllRenderables();
            this.overlayLayer.addRenderable(this.pathBorder);
            this.overlayLayer.addRenderable(this.path);
            this.path.boundaries = [];
            this.pathBorder.boundaries = [];
            this.overlayLayer.refresh();
            this.overlayLayer2.refresh();
        }
    }

};

measureAngle3d.prototype._keyListener = function(evt) {
    evt = evt || window.event;
    if (evt.keyCode == 27) {
        this.deactivate();
    }
}

measureAngle3d.prototype._doubleClickListener = function(evt) {
    this._removeOverlays();
}

measureAngle3d.prototype._addListeners = function() {

    document.addEventListener('keydown', this._keyListener.bind(this));   

    //evento de click (tb para mobiles)
    this.clickRecognizer.enabled = true;
    this.tapRecognizer.enabled = true;
        

    if (window.PointerEvent) {
        this.wwd.addEventListener("pointerdown", this._eventListener.bind(this));
        this.wwd.addEventListener("pointermove", this._eventListener.bind(this));
        this.wwd.addEventListener("pointerleave", this._eventListener.bind(this));
    } else {
        this.wwd.addEventListener("mousedown", this._eventListener.bind(this));
        this.wwd.addEventListener("mousemove", this._eventListener.bind(this));
        this.wwd.addEventListener("mouseleave", this._eventListener.bind(this));
        this.wwd.addEventListener("touchstart", this._eventListener.bind(this));
        this.wwd.addEventListener("touchmove", this._eventListener.bind(this));
    }

    this.wwd.addEventListener('dblclick', this._doubleClickListener.bind(this));
    
}

measureAngle3d.prototype._eventListener = function(event) {
    if (event.type.indexOf("pointer") !== -1) {
        this.eventType = event.pointerType; // possible values are "mouse", "pen" and "touch"
    } else if (event.type.indexOf("mouse") !== -1) {
        this.eventType = "mouse";
    } else if (event.type.indexOf("touch") !== -1) {
        this.eventType = "touch";
    }
    if (event.type.indexOf("leave") !== -1) {
        this.clientX = null; // clear the event coordinates when a pointer leaves the canvas
        this.clientY = null;
    } else {
        this.clientX = event.clientX;
        this.clientY = event.clientY;
    }
    var pickPoint,
        terrainObject;
    if ((this.eventType === "mouse" || this.eventType === "pen") && this.clientX && this.clientY) {
        pickPoint = this.wwd.canvasCoordinates(this.clientX, this.clientY);
        if (pickPoint[0] >= 0 && pickPoint[0] < this.wwd.canvas.width &&
            pickPoint[1] >= 0 && pickPoint[1] < this.wwd.canvas.height) {
            terrainObject = this.wwd.pickTerrain(pickPoint).terrainObject();
        }
    } else if (this.eventType === "touch") {
        pickPoint = new Vec2(this.wwd.canvas.width / 2, wwd.canvas.height / 2);
        terrainObject = this.wwd.pickTerrain(pickPoint).terrainObject();
    }
    this.terrainPosition = terrainObject ? terrainObject.position : null;          
    if (this.terrainPosition) {
        var position = this.terrainPosition;
        if (this.pathPositions.length > 0) {
            var tempPositions = this.pathPositions.slice(0);
            tempPositions.push(position);
            var distance = this.lengthMeasurer.getLength(tempPositions, true, WorldWind.GREAT_CIRCLE);
            var loc = new WorldWind.MeasuredLocation(position.latitude, position.longitude, distance);
            var tempLocations = [this.locations[this.pathPositions.length-1], loc];
            var tempPath = new WorldWind.SurfacePolyline(tempLocations, this.pathAttributes);
            var tempPathBorder = new WorldWind.SurfacePolyline(tempLocations, this.pathAttributes2);

            var text = new WorldWind.GeographicText(position, this._formatDistance(distance));

            this.overlayLayer2.removeAllRenderables();

            this.overlayLayer2.addRenderable(tempPath);
            this.overlayLayer2.addRenderable(tempPathBorder);
            this.overlayLayer2.addRenderable(text);

            this.overlayLayer2.refresh();                    
        }
    }

}

measureAngle3d.prototype._removeListeners = function() {
    document.removeEventListener('keydown', this._keyListener);   

    this.clickRecognizer.enabled = false;
    this.tapRecognizer.enabled = false;


    if (window.PointerEvent) {
        this.wwd.removeEventListener("pointerdown", this._eventListener);
        this.wwd.removeEventListener("pointermove", this._eventListener);
        this.wwd.removeEventListener("pointerleave", this._eventListener);
    } else {
        this.wwd.removeEventListener("mousedown", this._eventListener);
        this.wwd.removeEventListener("mousemove", this._eventListener);
        this.wwd.removeEventListener("mouseleave", this._eventListener);
        this.wwd.removeEventListener("touchstart", this._eventListener);
        this.wwd.removeEventListener("touchmove", this._eventListener);
    }

    this.wwd.removeEventListener('dblclick', this._doubleClickListener);

}

measureAngle3d.prototype.deactivate = function() {			
    this._removeOverlays(true);
    this._removeListeners();
    this.$button.blur();
	this.active = false;
};

/**
 * TODO
 */
measureAngle3d.prototype._removeOverlays = function(bRedraw) {
    this.pathPositions = [];
    this.locations = [];
    // this.path.boundaries = [];
    // this.pathBorder.boundaries = [];
    // this.overlayLayer2.removeAllRenderables();
    // Remove only texts
    // for(var i =0; i < this.texts.length; i++) {
    //     this.overlayLayer.removeRenderable(this.texts[i]);
    // };
    // this.texts = [];
    // this.overlayLayer.removeAllRenderables();    
    // this.overlayLayer.addRenderable(this.path);
    if (bRedraw) {
        this.wwd.redraw();
    }
};