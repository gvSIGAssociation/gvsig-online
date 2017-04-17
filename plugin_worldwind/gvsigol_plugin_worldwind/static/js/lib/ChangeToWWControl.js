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
 * @author: jvhigon <jvhigon@scolab.es>
 */

/**
 * WorldWind Control
 */
var ChangeToWWControl = function(map, provider) {

	this.map = map;
	this.provider = provider;
	
	this.id = "change-to-ww-control";
	

	var button = document.createElement('button');
	button.setAttribute("id", this.id);
	button.setAttribute("class", "toolbar-button");
	button.setAttribute("title", gettext('Change to 3D view'));
	var icon = document.createElement('i');
	icon.setAttribute("class", "icon-3d");
	button.appendChild(icon);
	
	this.$button = $(button);
	
	$('#toolbar').append(button);

	var this_ = this;
  
	var handler = function(e) {
		this_.handler(e);
	};

	button.addEventListener('click', handler, false);
	button.addEventListener('touchstart', handler, false);

	//objetos WW
	this.wwd = null;
	this.goToAnimator=null;
};

/**
 * TODO
 */
ChangeToWWControl.prototype.active = false;

/**
 * TODO
 */
ChangeToWWControl.prototype.deactivable = false;

/**
 * @param {Event} e Browser event.
 */
ChangeToWWControl.prototype.handler = function(e) {
	e.preventDefault();
	if (this.active) {
		this.deactivate();
		
	} else {
		if (this.wwd == null){
			this.initWW();		
		}

		this.$button.addClass('button-active');
		this.active = true;
		this.$button.trigger('control-active', [this]);		
		this.hideControls();
		//muestro el componente 
		$('#canvasWW').css("display","block");		
		// PRUEBA: mostrar propiedades de las capas
		//this.map.getLayers().forEach(function (lyr) {
	    //    console.log(lyr.layer_name);         
	    //    console.log(lyr.getVisible());         
	    //    console.log(lyr);         
	    //});
	}
};

/**
 * TODO
 */
ChangeToWWControl.prototype.hideControls = function() {		
	$('#export-to-pdf').css("display","none");
	$('#get-feature-info').css("display","none");
	$('#export-map-control').css("display","none");
	$('#measure-area').css("display","none");
	$('#measure-length').css("display","none");
	$('#mouse-position').css("display","none");
	//$('#intersect-by-radio-control').css("display","none");
	$('.ol-overviewmap').css("display","none");
	$('.ol-viewport').css("display","none");
	$('#base-layers').css("display","none");

};

/**
 * TODO
 */
ChangeToWWControl.prototype.resetControls = function() {		
	$('#export-to-pdf').css("display","block");
	$('#get-feature-info').css("display","block");
	$('#export-map-control').css("display","block");
	$('#measure-area').css("display","block");
	$('#measure-length').css("display","block");
	$('#mouse-position').css("display","block");
	//$('#intersect-by-radio-control').css("display","block");
	$('.ol-overviewmap').css("display","block");
	$('.ol-viewport').css("display","block");
	$('#base-layers').css("display","block");

};

/**
 * TODO: deberiamos desactivar el evento de OL3 de movimiento del mapa?
 * TODO: se calcula el zoom a partir del log(altitud). Deberíra realizarse una mejor aproximación.
 */
ChangeToWWControl.prototype.deactivate = function() {			
	this.$button.removeClass('button-active');
	this.active = false;	
	this.resetControls();
	$('#canvasWW').css("display","none");
	//set correct OL center
	var lat = this.wwd.navigator.lookAtLocation.latitude;
	var lon = this.wwd.navigator.lookAtLocation.longitude;	
	var alt = this.wwd.navigator.range;
	var rot = this.wwd.navigator.heading;
	var position = [lon,lat];
	var center = ol.proj.transform(position, 'EPSG:4326', 'EPSG:3857');
	this.map.getView().setCenter(center);
	//set correct zoom	
	var zoom = 20 - Math.floor(Math.log(alt));	
	this.map.getView().setZoom(zoom);
	//set correct rotation
	var rot_radians = rot * (Math.PI/180);
	this.map.getView().setRotation(rot_radians * -1);
	//console.log(this.wwd.navigator.range);
	//console.log(this.wwd.navigator.lookAtLocation.latitude);
	//console.log(this.wwd.navigator.lookAtLocation.longitude);
	//console.log(this.wwd.navigator.worldWindow.viewport.x);
};

/**
 * Inicializamos WW
 * 
 */
ChangeToWWControl.prototype.initWW = function() {			

	// Iniciamos Window
    WorldWind.Logger.setLoggingLevel(WorldWind.Logger.LEVEL_INFO);
	this.wwd = new WorldWind.WorldWindow("canvasWW",this.getElevationModel());
	var coordsdisplay = new WorldWind.CoordinatesDisplayLayer(this.wwd);
	this.wwd.addLayer(coordsdisplay);
	var controls = new WorldWind.ViewControlsLayer(this.wwd);
	controls.placement = new WorldWind.Offset(WorldWind.OFFSET_FRACTION, 0.5, WorldWind.OFFSET_FRACTION, 0.1);
	controls.alignment = new WorldWind.Offset(WorldWind.OFFSET_FRACTION, 0.5, WorldWind.OFFSET_FRACTION, 1);

	this.wwd.addLayer(controls);
	//Start the view pointing to a longitude within the current time zone
    this.wwd.navigator.lookAtLocation.latitude = 44;
    this.wwd.navigator.lookAtLocation.longitude = -(180 / 12) * ((new Date()).getTimezoneOffset() / 60);

	//move smoothly
	this.goToAnimator = new WorldWind.GoToAnimator(this.wwd);
	
	//cargamos capa WMS de ejemplo
	//this.TestaddLayerWMS();
	
	//creamos polygon de prueba
	//this.createPolygon();
	//creamos geojson prueba
	//this.createGeoJSON();
	
	// evento de movimiento de mouse
    // Listen for mouse moves and highlight the placemarks that the cursor rolls over.
    // this.wwd.addEventListener("mousemove", this.onWWMouseMove);
    // Listen for taps on mobile devices and highlight the placemarks that the user taps.
    //var tapRecognizer = new WorldWind.TapRecognizer(this.wwd, this.onClick);
    
    //evento de click (tb para mobiles)
    new WorldWind.ClickRecognizer(this.wwd, this.onWWClick);
    new WorldWind.TapRecognizer(this.wwd, this.onWWClick);
    
    //TODO: no he conseguido gestionar el evento de cambio de rotación
    //new WorldWind.GestureRecognizer(this.wwd, this.onWWGesture);
        
	// Añadimos capas
	this.loadBaseLayer();
    this.loadLayers(this.map);
	
	// Añadimos eventos de movimiento de mapa de OL3
	this.map.on('moveend', this.onOLMoveEnd, this);
	this.map.getView().on('change:rotation', this.onOLRotation, this);
    
};

/**
 * Obtenemos el modelo de elevaciones
 */
ChangeToWWControl.prototype.getElevationModel = function() {	

	var provider =  this.provider;   
	//TODO: check if provider is null
	
	var CustomEarthElevationModel = function () {
		WorldWind.ElevationModel.call(this, WorldWind.Sector.FULL_SPHERE, new WorldWind.Location(45, 45), 12, "application/bil16", "EarthElevations256", 256, 256);
		this.displayName = "Earth Elevation Model";
		this.minElevation = -11000; // Depth of Marianas Trench, in meters
		this.maxElevation = 8850; // Height of Mt. Everest
		this.pixelIsPoint = false; // World Wind WMS elevation layers return pixel-as-area images
		this.urlBuilder = new WorldWind.WmsUrlBuilder(provider.provider_url,provider.provider_layers, "", provider.provider_version);
		
	     //this.urlBuilder = new WorldWind.WmsUrlBuilder("http://worldwind26.arc.nasa.gov/elev","GEBCO,aster_v2,USGS-NED", "", "1.3.0");
	     //No funciona con Geoserver
	     //this.urlBuilder = new WorldWind.WmsUrlBuilder("http://localhost/geoserver/elevation/wms","mdt05_0721", "", "1.3.0");
	     //this.urlBuilder.crs="CRS:84"
	     //this.urlBuilder = new WorldWind.WmsUrlBuilder("http://localhost/cgi-bin/mapserv?map=/home/jvhigon/test/worldwind/wms/mapfile.map","mdt05-0721-h30-lidar", "", "1.1.1");			
	 };
	
	 CustomEarthElevationModel.prototype = Object.create(WorldWind.ElevationModel.prototype);	
	 return new CustomEarthElevationModel();
};


/**
 * Evento de movimiento en el mapa.
 * Obtenemos el centro del mapa y empleamos como altura la distancia en x del extent 
 * 
 */
ChangeToWWControl.prototype.onOLMoveEnd = function(evt) {			
	var map = evt.map;
	var extent = map.getView().calculateExtent(map.getSize());
	var z;
	if (extent[0] > extent[2]){
		z = Math.abs(extent[0]-extent[2]);
	}else{
		z = Math.abs(extent[2]-extent[0]);
	}	 
	var center = map.getView().getCenter();
	var latlon = ol.proj.transform(center,'EPSG:3857', 'EPSG:4326');
	var zoom = map.getView().getZoom(); 
	this.goToAnimator.goTo(new WorldWind.Position(latlon[1], latlon[0], z));
	//console.log("Zoom actual: " + zoom);
};


/**
 * Evento de rotacion en el mapa.
 * 
 */
ChangeToWWControl.prototype.onOLRotation = function(evt) {			
	var mapview = evt.target;
	var rot = mapview.getRotation();
	var rot_deegree = rot * (180/Math.PI);
	this.wwd.navigator.heading = rot_deegree * -1;
	this.wwd.redraw();
};

/**
 * 
 */
ChangeToWWControl.prototype.loadBaseLayer = function() {
	if (this.provider.baseLayerType == 'Bing'){
		this.wwd.addLayer(new WorldWind.BingAerialWithLabelsLayer());
	}else{
		this.wwd.addLayer(new WorldWind.OpenStreetMapImageLayer());
	}
	//this.wwd.addLayer(new WorldWind.BMNGOneImageLayer());
	//this.wwd.addLayer(new WorldWind.BMNGLandsatLayer());	
	//this.wwd.addLayer(new WorldWind.CompassLayer());
};

/**
 * Load all layers in OL map
 */
ChangeToWWControl.prototype.loadLayers = function(map) {
	var layers = map.getLayers();
	for (var i = 0; i < layers.getLength(); i++) {
		var config;
		var lyr;
		l = layers.item(i)		
		//console.log(l);
	    //console.log(l.wms_url);
		//console.log(l.layer_name);
		//console.log(l.getExtent());
		//console.log(l.getVisible());
		//console.log(l.getProperties());		
		if (l.layer_name){
			
			//Añadimos a WW
			config = {service: l.wms_url, 
		            layerNames: l.layer_name,
		            sector: new WorldWind.Sector(-90,90,-180,180),
		            //levelZeroDelta: new WorldWind.Location(0,43),
		            levelZeroDelta: new WorldWind.Location(36,36),
		            format: 'image/png',
		            numLevels: 20,
		            size: 256,
		            coordinateSystem: 'EPSG:4326',
		            title: l.title,
		            version: '1.1.1'
		           	 };
			lyr = new WorldWind.WmsLayer(config,null );
			if (l.getVisible()){
				lyr.enabled = true;
			}else{
				lyr.enabled = false;
			}			
			this.wwd.addLayer(lyr);
			this.wwd.redraw();
			
			// Creamos listener
			l.on('propertychange', function (evt) {
				//console.log(evt.key);
			    if (evt.key === 'visible') {
			    	this.enabled = !evt.oldValue;
			    }
			    if (evt.key === 'opacity') {
			        //console.log('cambiando opacidad');			        
			        this.opacity = evt.target.getOpacity();
			    }
			},lyr);
		}
	}
};

/**
 * Carga una capa WMS
 */

ChangeToWWControl.prototype.TestaddLayerWMS = function() {			
	var config = {service: 'http://www.ign.es/wms-inspire/pnoa-ma', 
            layerNames: 'OI.OrthoimageCoverage',
            sector: new WorldWind.Sector(-90,90,-180,180),
            //levelZeroDelta: new WorldWind.Location(0,43),
            levelZeroDelta: new WorldWind.Location(36,36),
            format: 'image/png',
            numLevels: 20,
            size: 256,
            coordinateSystem: 'EPSG:4326',
            title: 'PNOA',
            version: '1.1.1'
           	 };
	var lyr = new WorldWind.WmsLayer(config,null );
	lyr.enabled = true;
	 this.wwd.addLayer(lyr);
	 this.wwd.redraw();
};



/**
 * Creamos polígono de prueba 
 */
ChangeToWWControl.prototype.createPolygon = function() {			
	
	//Create a layer to hold the polygons.
	var polygonsLayer = new WorldWind.RenderableLayer();
	polygonsLayer.displayName = "Polygons";
	this.wwd.addLayer(polygonsLayer);
	
	// Polygon 1
	var boundaries = [];
	boundaries[0] = []; // outer boundary	
	boundaries[0].push(new WorldWind.Position(39.48,-0.59,  200));
	boundaries[0].push(new WorldWind.Position( 39.48,-0.57, 200));
	boundaries[0].push(new WorldWind.Position(39.49,-0.58,  200));	
	//boundaries[1] = []; // inner boundary
	//boundaries[1].push(new WorldWind.Position(41, -103, 1e5));
	//boundaries[1].push(new WorldWind.Position(44, -110, 1e5));
	//boundaries[1].push(new WorldWind.Position(41, -117, 1e5));
	
	// Create the polygon and assign its attributes.
	
	var polygon = new WorldWind.Polygon(boundaries, null);
	polygon.altitudeMode =WorldWind.RELATIVE_TO_GROUND;
	polygon.extrude = true; // extrude the polygon edges to the ground
	polygon.displayName ="Polygon 1"

	var polygonAttributes = new WorldWind.ShapeAttributes(null);
	polygonAttributes.drawInterior = true;
	polygonAttributes.drawOutline = true;
	polygonAttributes.outlineColor = WorldWind.Color.BLUE;
	polygonAttributes.interiorColor = new WorldWind.Color(0, 1, 1, 0.5);
	polygonAttributes.drawVerticals = polygon.extrude;
	polygonAttributes.applyLighting = true;
	polygon.attributes = polygonAttributes;

	// Polygon 2
	boundaries = [];
	boundaries[0] = []; // outer boundary	
	boundaries[0].push(new WorldWind.Position(39.49,-0.58,  400));
	boundaries[0].push(new WorldWind.Position(39.49,-0.575,  400));
	boundaries[0].push(new WorldWind.Position(39.485,-0.575,  400));		
	//boundaries[1] = []; // inner boundary
	//boundaries[1].push(new WorldWind.Position(41, -103, 1e5));
	//boundaries[1].push(new WorldWind.Position(44, -110, 1e5));
	//boundaries[1].push(new WorldWind.Position(41, -117, 1e5));
	
	// Create the polygon and assign its attributes.
	
	var polygon2 = new WorldWind.Polygon(boundaries, null);
	polygon2.altitudeMode =WorldWind.RELATIVE_TO_GROUND;
	polygon2.extrude = true; // extrude the polygon edges to the ground
	polygon2.displayName ="Polygon 2"
	
	var polygonAttributes2 = new WorldWind.ShapeAttributes(null);
	polygonAttributes2.drawInterior = true;
	polygonAttributes2.drawOutline = true;
	polygonAttributes2.outlineColor = WorldWind.Color.BLUE;
	polygonAttributes2.interiorColor = new WorldWind.Color(0, 1, 1, 0.5);
	polygonAttributes2.drawVerticals = polygon.extrude;
	polygonAttributes2.applyLighting = true;
	polygon2.attributes = polygonAttributes2;

	// Create and assign the polygon's highlight attributes.
	var highlightAttributes = new WorldWind.ShapeAttributes(polygonAttributes);
	highlightAttributes.outlineColor = WorldWind.Color.RED;
	highlightAttributes.interiorColor = new WorldWind.Color(1, 1, 1, 0.5);
	polygon.highlightAttributes = highlightAttributes;
	polygon2.highlightAttributes = highlightAttributes;

	
	// Add the polygon to the layer and the layer to the World Window's layer list.
	polygonsLayer.addRenderable(polygon);
	polygonsLayer.addRenderable(polygon2);

	
    // Now set up to handle highlighting.
    var highlightController = new WorldWind.HighlightController(this.wwd);
};

ChangeToWWControl.prototype.createGeoJSON = function() {			
		
	/*  var url = "http://localhost/geoserver/test/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=test:edificios3d&maxFeatures=50&outputformat=application/json";
    url ="http://localhost/media/shp/test.json";
    var geometryCollectionLayer = new WorldWind.RenderableLayer("GeometryCollection");
    //GeoJSONConstants.WGS84_CRS='urn:ogc:def:crs:EPSG::4326';
    var jsonparser = new WorldWind.GeoJSONParser(url);
    Proj4 = proj4;
    proj4.defs([
                [
                    'urn:ogc:def:crs:EPSG::4326',
                    proj4.defs('EPSG:4326')
                ],
                [
                    'urn:ogc:def:crs:EPSG::3857',
                    proj4.defs('EPSG:3857')

                ]
            ]);
    //jsonparser.crs = new WorldWind.GeoJSONCRS('crs',);
    //geometryCollectionGeoJSON.load(this.shapeConfigurationCallback, geometryCollectionLayer);
    
    jsonparser.load(null, geometryCollectionLayer);
    this.wwd.addLayer(geometryCollectionLayer);*/
    
    
    /*var url ="http://localhost/media/shp/edificios_4326.shp";
    var shpLayer = new WorldWind.RenderableLayer("SHP");
    var shp = new WorldWind.Shapefile(url);    
    shp.load(null,null, shpLayer);
    this.wwd.addLayer(shpLayer);*/


};
ChangeToWWControl.prototype.shapeConfigurationCallback = function(evt) {
	console.log("Test Callback!!");
};
ChangeToWWControl.prototype.parseCall = function(evt) {
	console.log("Test Parse ...");
};
ChangeToWWControl.prototype.shapeCall = function(evt) {
	console.log("Test shape ...");
};


/**
 * Evento de click en el mapa (con evento js)
 * @deprecated
 */
ChangeToWWControl.prototype.onClickEvent = function(evt) {			
	 // The input argument is either an Event or a TapRecognizer. Both have the same properties for determining
    // the mouse or tap location.
    var x = evt.clientX;
    var y = evt.clientY;
    console.log(x);
    console.log(y);
    var cc = evt.worldWindow.canvasCoordinates(x, y);
    var pickList = evt.worldWindow.pick(cc);
    console.log(pickList.topPickedObject());
};

/**
 * Evento de click en el globo 
 */
ChangeToWWControl.prototype.onWWClick = function(recognizer) {			
    // Obtain the event location.
    var x = recognizer.clientX,
        y = recognizer.clientY;

    // Perform the pick. Must first convert from window coordinates to canvas coordinates, which are
    // relative to the upper left corner of the canvas rather than the upper left corner of the page.
    var pickList = recognizer.target.pick(recognizer.target.canvasCoordinates(x, y));

    // If only one thing is picked and it is the terrain, use a go-to animator to go to the picked location.
    //if (pickList.objects.length == 1 && pickList.objects[0].isTerrain) {
    //    var position = pickList.objects[0].position;
    //    var goToAnimator = new WorldWind.GoToAnimator(recognizer.target);
    //    goToAnimator.goTo(new WorldWind.Location(position.latitude, position.longitude));
    //}
    console.log(x);
    console.log(y);
    var top = pickList.topPickedObject();
    console.log(top.userObject.displayName);
    var terrain = pickList.terrainObject();
    //console.log(terrain.position.latitude + " " + terrain.position.longitude);
    //console.log("heading: " + recognizer.target.navigator.heading);

};
/**
 * Evento de rotación en el globo 
 */
ChangeToWWControl.prototype.onWWGesture = function(recognizer) {			
    
	var wwd = recognizer.target;
	console.log("Test onGesture !!!!");
};

/**
 * Evento de movimiento en el mapa 
 */
ChangeToWWControl.prototype.onWWMouseMove = function(evt) {			
	// The input argument is either an Event or a TapRecognizer. Both have the same properties for determining
    // the mouse or tap location.
    var x = evt.clientX;
    var y = evt.clientY;
    var cc = evt.worldWindow.canvasCoordinates(x, y);
    var pickList = evt.worldWindow.pick(cc);
    //console.log(pickList.topPickedObject());
    //TODO ver https://webworldwind.org/developers-guide/event-and-gesture-handling/
};
