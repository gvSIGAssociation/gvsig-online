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
	
	this.id = "change-to-3d-view";
	this.$button = $("#change-to-3d-view");

	var this_ = this;
  
	var handler = function(e) {
		this_.handler(e);
	};

	this.$button.on('click', handler);
	this.$button.on('touchstart', handler);
	
	$('body').on('change-to-2D-event', function() {
		if (this_.active) {
			this_.deactivate();
		}
	});
	
	$('body').on('show-catalog-event', function() {
		if (this_.active) {
			this_.deactivate();
		}
	});

	//objetos WW
	this.wwd = null;
	this.goToAnimator=null;
	this.tools3d = new Array();
	
	// Diccionario con los capabilities
	this.dictCapabilities = {};
	
	
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
	if (this.wwd == null){
		this.initWW();		
	}
	this.active = true;
	this.$button.trigger('control-active', [this]);	
	$('body').trigger('change-to-3D-event', [this]);
	this.hideControls();
	$('#canvasWW').css("display","block");
	
	if (viewer.core.ifToolInConf('gvsigol_tool_measure')) {
		$('#toolbar3d').css("display","block");
	}
	
	$('body').css('background', 'black');
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
	$('#clean-map').css("display","none");
	$('.ol-overviewmap').css("display","none");
	$('.ol-viewport').css("display","none");
	$('#toolbar').css("display", "none");
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
	$('#clean-map').css("display","block");
	$('.ol-overviewmap').css("display","");
	$('.ol-viewport').css("display","block");
	$('#base-layers').css("display","block");
	$('#toolbar').css("display", "block");
};

/**
 * TODO: deberiamos desactivar el evento de OL3 de movimiento del mapa?
 * TODO: se calcula el zoom a partir del log(altitud). Deberíra realizarse una mejor aproximación.
 */
ChangeToWWControl.prototype.deactivate = function() {			
	this.active = false;	
	this.resetControls();
	$('#canvasWW').css("display","none");
	$('#toolbar3d').css("display","none");
	$('body').css('background', 'white');
	
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
	this.map.getView().setRotation(0);
};

/**
 * Inicializamos WW
 * 
 */
ChangeToWWControl.prototype.initWW = function() {			

	// Iniciamos Window
    WorldWind.Logger.setLoggingLevel(WorldWind.Logger.LEVEL_INFO);
	
	if (this.provider == null) {
		this.wwd = new WorldWind.WorldWindow("canvasWW"); // Usamos el modelo de alturas por defecto
	}
	else {
		this.wwd = new WorldWind.WorldWindow("canvasWW",this.getElevationModel()); // Usamos nuestro propio MDT desde Mapserver para obtener las alturas
	}

	var coordsdisplay = new WorldWind.CoordinatesDisplayLayer(this.wwd);
	this.wwd.addLayer(coordsdisplay);
	var controls = new WorldWind.ViewControlsLayer(this.wwd);
	//controls.placement = new WorldWind.Offset(WorldWind.OFFSET_FRACTION, 0.5, WorldWind.OFFSET_FRACTION, 0.1);
	//controls.alignment = new WorldWind.Offset(WorldWind.OFFSET_FRACTION, 0.5, WorldWind.OFFSET_FRACTION, 1);
	
	controls.placement = new WorldWind.Offset(WorldWind.OFFSET_FRACTION, 0.99, WorldWind.OFFSET_FRACTION, 0.98);
    controls.alignment = new WorldWind.Offset(WorldWind.OFFSET_FRACTION, 1, WorldWind.OFFSET_FRACTION, 1);

	this.wwd.addLayer(controls);
	//Start the view pointing to a longitude within the current time zone
    this.wwd.navigator.lookAtLocation.latitude = 44;
    this.wwd.navigator.lookAtLocation.longitude = -(180 / 12) * ((new Date()).getTimezoneOffset() / 60);

	//move smoothly
	this.goToAnimator = new WorldWind.GoToAnimator(this.wwd);
    
    //evento de click (tb para mobiles)
//    new WorldWind.ClickRecognizer(this.wwd, this.onWWClick);
//    new WorldWind.TapRecognizer(this.wwd, this.onWWClick);
    
    //TODO: no he conseguido gestionar el evento de cambio de rotación
    //new WorldWind.GestureRecognizer(this.wwd, this.onWWGesture);
    this.wwd.addLayer(new WorldWind.AtmosphereLayer());
    this.wwd.addLayer(new WorldWind.StarFieldLayer());
    var compassLayer = new WorldWind.CompassLayer();
    var wWidth  = window.innerWidth;
    var wHeight = window.innerHeight;
    
    compassLayer.compass.screenOffset = new WorldWind.Offset(WorldWind.OFFSET_FRACTION, 0.52, WorldWind.OFFSET_FRACTION, 0.9900);
    var pixelSize = 75;
    var desiredScale =  pixelSize / wWidth;
    compassLayer.compass.size = desiredScale;
    this.wwd.addLayer( compassLayer );
    
    if (viewer.core.ifToolInConf('gvsigol_tool_measure')) {
		this.tools3d.push(new measureLength3d(this.wwd));
		this.tools3d.push(new measureArea3d(this.wwd));
		this.tools3d.push(new measureAngle3d(this.wwd));
		var self = this;
		$('#toolbar3d').on( "control-active", function(e) {
			for (var i=0; i<self.tools3d.length; i++){
				if (e.target.id != self.tools3d[i].id) {
					if (self.tools3d[i].deactivable == true) {
						if (self.tools3d[i].active) {
							self.tools3d[i].deactivate();
						}
					}
				}
			}
	  });
	}

        
	// Añadimos capas
	// this.loadBaseLayer(this.map);
	//this.loadGrid();
    this.loadLayers(this.map);
	
	// Añadimos eventos de movimiento de mapa de OL3
	this.map.on('moveend', this.onOLMoveEnd, this);
	this.map.getView().on('change:rotation', this.onOLRotation, this);

	var zoom = this.map.getView().getZoom(); 
	var extent = this.map.getView().calculateExtent(this.map.getSize());
	var z;
	if (extent[0] > extent[2]){
		z = Math.abs(extent[0]-extent[2]);
	}else{
		z = Math.abs(extent[2]-extent[0]);
	}	 

	var center = this.map.getView().getCenter();
	var latlon = ol.proj.transform(center,'EPSG:3857', 'EPSG:4326');
	this.goToAnimator.goTo(new WorldWind.Position(latlon[1], latlon[0], z));

    
};


/**
 * Obtenemos el modelo de elevaciones ** NOT USED ** 
 */
ChangeToWWControl.prototype.getElevationModel = function() {	

	var provider =  this.provider;   
	//TODO: check if provider is null
	
	var CustomEarthElevationModel = function () {
		// WorldWind.TiledElevationCoverage.call(this, {
		// 	coverageSector: WorldWind.Sector.FULL_SPHERE,
		// 	resolution: 0.008333333333333,
		// 	retrievalImageFormat: "application/bil16",
		// 	minElevation: -11000,
		// 	maxElevation: 8850,
		// 	urlBuilder: new WorldWind.WmsUrlBuilder(provider.provider_url,/* provider.provider_layers */ 'GEBCO', "", provider.provider_version)
		// });
		// // WorldWind.TiledElevationCoverage.call(this, WorldWind.Sector.FULL_SPHERE, new WorldWind.Location(45, 45), 12, "application/bil16", "EarthElevations256", 256, 256);
		// this.displayName = "Earth Elevation Model";

		WorldWind.ElevationModel.call(this);

//		this.addCoverage(new WorldWind.GebcoElevationCoverage());
		// this.addCoverage(new WorldWind.AsterV2ElevationCoverage());
		// this.addCoverage(new WorldWind.UsgsNedElevationCoverage());
		// this.addCoverage(new WorldWind.UsgsNedHiElevationCoverage());

		// NOTA: Probar qué pasa con el provider que definimos nosotros. Probablemente
		// no podemos mezclar varios layers. Quizás con el default GEBCO sería suficiente.
		
		// TEST ALTURAS URUGUAY
		// https://mapas.ide.uy/cgi-bin/relieve?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&
		//      FORMAT=application/bil16&TRANSPARENT=true&
		//      LAYERS=mdt_nacional&WIDTH=256&HEIGHT=256&SRS=EPSG%3A3857&STYLES=&
		//      BBOX=-6105178.323193599%2C-4050551.002888061%2C-6085610.443952593%2C-4030983.123647056
		// var heightUrlUruguay = 'https://mapas.ide.uy/cgi-bin/relieve?'; 
		var heightUrl = provider.provider_url;
		// TODO: REVISAR CON CHEVI SI LA CAPA ES mdt_nacional O mdt_nacional_10m
		// TODO: REVISAR el parámetro resolution y si devuelve info de punto o el pixel es de tipo area. (Ver docs de WW)
		
		var customCoverage = new WorldWind.TiledElevationCoverage({
			coverageSector: WorldWind.Sector.FULL_SPHERE,
			resolution: 0.008333333333333,
			retrievalImageFormat: "application/bil16",
			minElevation: -11000,
			maxElevation: 8850,
			urlBuilder: new WorldWind.WmsUrlBuilder(heightUrl, provider.provider_layers /*'mdt_nacional'*/, "", provider.provider_version)
		});
		customCoverage.lastLevel = 20;
		customCoverage.numLevels = 20;
		customCoverage.levels = new WorldWind.LevelSet(customCoverage.coverageSector, new WorldWind.Location(45, 45),
				customCoverage.numLevels, 256, 256);


//		var customCoverage = new WorldWind.TiledElevationCoverage({
//			coverageSector: WorldWind.Sector.FULL_SPHERE,
//			resolution: 0.008333333333333,
//			retrievalImageFormat: "application/bil16",
//			minElevation: -11000,
//			maxElevation: 8850,
//			urlBuilder: new WorldWind.WmsUrlBuilder(provider.provider_url, 'GEBCO' /*provider.provider_layers*/, "", provider.provider_version)
//		});
		this.addCoverage(customCoverage);


		// this.minElevation = -11000; // Depth of Marianas Trench, in meters
		// this.maxElevation = 8850; // Height of Mt. Everest
		// this.pixelIsPoint = false; // World Wind WMS elevation layers return pixel-as-area images
		// this.urlBuilder = new WorldWind.WmsUrlBuilder(provider.provider_url,provider.provider_layers, "", provider.provider_version);
	 };
	
	 // CustomEarthElevationModel.prototype = Object.create(WorldWind.TiledElevationCoverage.prototype);	
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

ChangeToWWControl.prototype.myResourceUrlForTile = function (tile, imageFormat) {
    var url;
    if (this.resourceUrl) {
    	url = this.resourceUrl;
        if (this.styleIdentifier) {
        	var styleSearch = /{Style}/i;
            url = url.replace(styleSearch, this.styleIdentifier);
        }
        if (tile.level) {
        	var z = tile.level.levelNumber+1; //Math.pow(2, tile.level.levelNumber);
        	var y = tile.column; //(1 << z) - tile.row -1;
        	var x = tile.row; //tile.column;
            url = url.replace("{TileMatrix}", z);
            url = url.replace("{TileCol}", y).replace("{TileRow}", x); 
        }        
        if (tile.tileMatrix) {
            url = url.replace("{TileCol}", tile.column).replace("{TileRow}", tile.row);
            url = url.replace("{TileMatrix}", tile.tileMatrix.identifier);
        }        
        if (this.tileMatrixSet) {
            url = url.replace("{TileMatrixSet}", this.tileMatrixSet.identifier);
        }
        if (this.timeString) {
            url = url.replace("{Time}", this.timeString);
        }
    } else {
        url = this.serviceUrl + "service=WMTS&request=GetTile&version=1.0.0";
        url += "&Layer=" + this.layerIdentifier;
        if (this.styleIdentifier) {
            url += "&Style=" + this.styleIdentifier;
        }
        url += "&Format=" + imageFormat;
        if (this.timeString) {
            url += "&Time=" + this.timeString;
        }
        url += "&TileMatrixSet=" + this.tileMatrixSet.identifier;
        url += "&TileMatrix=" + tile.tileMatrix.identifier;
        url += "&TileRow=" + tile.row;
        url += "&TileCol=" + tile.column;
    }
    return url;
};


ChangeToWWControl.prototype.loadLayer = function(l) {
//	if (l.baselayer){			
		var p = l.getProperties();
		var lyr;
		var config;
		if (p.label == 'Vacía'){
			config = {service: this.provider.provider_url, 
	            layerNames: "grid",
	            sector: new WorldWind.Sector(-90,90,-180,180),
	            //levelZeroDelta: new WorldWind.Location(0,43),
	            levelZeroDelta: new WorldWind.Location(36,36),
	            format: 'image/png',
	            numLevels: 20,
	            size: 256,
	            coordinateSystem: 'EPSG:4326',
	            title: "grid",
	            version: '1.1.1'
	         };
			lyr = new WorldWind.WmsLayer(config,null );
		} else 	if (l.getSource() instanceof ol.source.XYZ){
			if (l.getSource() instanceof ol.source.OSM){
				// FJP: No sé si va a funcionar esto. En WorldWind hacen un poco de trampa
				// y la capa OSM es en realidad un WMTS que sirven ellos en
				// https://tiles.maps.eox.at/wmts/1.0.0/WMTSCapabilities.xml
				lyr = new WorldWind.OpenStreetMapImageLayer();
				// lyr = new WorldWind.BMNGLandsatLayer();
			} else{
				// TODO: Basarnos en RestTiledImageLayer para leer las de tipo xyz
				var url = l.getSource().urls[0];
				if (!url.endsWith('?'))
				{
					if (-1 == url.indexOf('?')) // No está por enmedio
						url = url + '?';
					else
						url = url + '&';
				}
				lyr = new WorldWind.MercatorTiledImageLayer(
						new WorldWind.Sector(-90, 90, -180, 180), 
						new WorldWind.Location(90, 180),
						20,	'image/png', l.getProperties().label, 256, 256		
				);
				
	            lyr.urlBuilder = {
	            		urlTemplate: url,
	                    urlForTile: function (tile, imageFormat) {
                            return this.urlTemplate.replace(
                                "{z}",
                                (tile.level.levelNumber + 1)).replace("{x}",
                                tile.column).replace("{y}",
                                tile.row
                            );
	                    }
	                };

				
				// Trick
				lyr.imageSize = 256;
				lyr.mapSizeForLevel = function (levelNumber) {
		            return 256 << (levelNumber + 1);
		        };
		        // End trick

			}
		} else 	if (l.getSource() instanceof ol.source.WMTS){
	        // Web Map Tiling Service information from
			var url = l.getSource().urls[0];
			if (!url.endsWith('?'))
			{
				if (-1 == url.indexOf('?')) // No está por enmedio
					url = url + '?';
				else
					url = url + '&';
			}
			if (-1 != url.indexOf('TileRow')) {
				// Test. Ojo, ArcGis va al revés que mapbox. Mapbox va con x/y, como OSM y Planet.
				// url = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{TileMatrix}/{TileCol}/{TileRow}';
				// url = 'https://api.mapbox.com/styles/v1/mapbox/streets-v11/tiles/{TileMatrix}/{TileCol}/{TileRow}?access_token=pk.eyJ1IjoiZnBlbmFycnUiLCJhIjoiY2poMXprMHg0MGIydjJ3cnluam1nMmRuMyJ9.abnLDxLCophGfhRpAmasEg';				
				
				lyr = new WorldWind.MercatorTiledImageLayer(
						new WorldWind.Sector(-90, 90, -180, 180), 
						new WorldWind.Location(90, 180),
						20,	l.getSource().getFormat(), l.getSource().getLayer(), 256, 256		
				);


				// Trick
				lyr.imageSize = 256;
				lyr.mapSizeForLevel = function (levelNumber) {
		            return 256 << (levelNumber + 1);
		        };

				lyr.resourceUrl = url;
		        lyr.resourceUrlForTile = this.myResourceUrlForTile;
		        // End trick
			}
			else
			{
		        var serviceAddress =  url + "SERVICE=WMTS&REQUEST=GetCapabilities&VERSION=1.0.0";
		        // Layer displaying Global Hillshade based on GMTED2010
		        var layerIdentifier = l.getSource().getLayer();
	
		        var wmtsCapabilities = this.dictCapabilities[serviceAddress];
		        if (!wmtsCapabilities) {	        		        
			        // Called synchronously to parse and create the WMTS layer
			        var request = new XMLHttpRequest();
			        request.open('GET', serviceAddress, false);  // `false` makes the request synchronous
			        request.send(null);
			        if (request.status === 200) {
			          // console.log(request.responseText);
		              // Create a WmtsCapabilities object from the XML DOM
			          wmtsCapabilities = new WorldWind.WmtsCapabilities(request.responseXML);
			          this.dictCapabilities[serviceAddress] = wmtsCapabilities;
			        }
			        else
			        {
			        	console.debug("Error cargando Capabilities de la capa " + layerIdentifier);
			        	return;
			        }
		        }
		        // Retrieve a WmtsLayerCapabilities object by the desired layer name
		        var wmtsLayerCapabilities = wmtsCapabilities.getLayer(layerIdentifier);
		        // Form a configuration object from the WmtsLayerCapabilities object
		        var wmtsConfig = WorldWind.WmtsLayer.formLayerConfiguration(wmtsLayerCapabilities);
		        // Create the WMTS Layer from the configuration object
		        lyr = new WorldWind.WmtsLayer(wmtsConfig);
		        lyr.resourceUrlForTile = this.myResourceUrlForTile;
			}
	        
		} else 	if (l.getSource() instanceof ol.source.TileWMS){
			var wms_url = l.wms_url_no_auth;
			if (wms_url === undefined)
				wms_url = l.wms_url;
			
			if (l.cached)
			{
				// TODO: ADD WMTS
				console.debug("Deberías tener en cuenta que es cacheada")
			}

			config = {service: l.getSource().urls[0], 
	            layerNames: l.getSource().getParams().LAYERS,
	            sector: new WorldWind.Sector(-90,90,-180,180),
	            //levelZeroDelta: new WorldWind.Location(0,43),
	            levelZeroDelta: new WorldWind.Location(36,36),
	            format: l.getSource().getParams().FORMAT,
	            numLevels: 20,
	            size: 256,
	            coordinateSystem: 'EPSG:4326',
	            title: l.title,
	            version:  l.getSource().getParams().VERSION
	        };
	        lyr = new WorldWind.WmsLayer(config,null );
		} else 	if (l.getSource() instanceof ol.source.BingMaps){
			var apikey = l.getSource().apiKey_;
			if (p.label == 'Road'){
				//lyr = new WorldWind.BingRoadsLayer(apikey);
				lyr = new WorldWind.BingRoadsLayer(apikey);
			} else {					
				//lyr = new WorldWind.BingAerialWithLabelsLayer(apikey);
				lyr = new WorldWind.BingAerialWithLabelsLayer(apikey);
			}
		} else {
			console.debug("Hacer Otro tipo de capa");
			return; 
		}		
		if (!lyr) return;
		// add layer
		if (l.getVisible()){
			lyr.enabled = true;
		}else{
			lyr.enabled = false;
		}			
		this.wwd.addLayer(lyr);
		// this.wwd.redraw();	
		
		// Create listener
		l.on('propertychange', function (evt) {
		    if (evt.key === 'visible') {
		    	this.enabled = !evt.oldValue;
		    }
		},lyr);
//	}	
}

/**
 * 
 */
//ChangeToWWControl.prototype.loadBaseLayer = function(map) {
//	var layers = map.getLayers();
//	// var terrainLayer = new WorldWind.BMNGLandsatLayer();
//	// this.addLayer(terrainLayer);
//	for (var i = 0; i < layers.getLength(); i++) {
//		l = layers.item(i);
//		this.loadLayer(l);
//	}
//};

/**
 * Load WMS grid Layer
 */
//ChangeToWWControl.prototype.loadGrid = function(map) {
//		config = {service: this.provider.provider_url, 
//		            layerNames: "grid",
//		            sector: new WorldWind.Sector(-90,90,-180,180),
//		            //levelZeroDelta: new WorldWind.Location(0,43),
//		            levelZeroDelta: new WorldWind.Location(36,36),
//		            format: 'image/png',
//		            numLevels: 20,
//		            size: 256,
//		            coordinateSystem: 'EPSG:4326',
//		            title: "grid",
//		            version: '1.1.1'
//		           	 };
//			lyr = new WorldWind.WmsLayer(config,null );
//			//if (l.getVisible()){
//				lyr.enabled = true;
//			//}else{
//			//	lyr.enabled = false;
//			//}			
//			this.wwd.addLayer(lyr);
//			this.wwd.redraw();
//			
//}

/**
 * Load all layers in OL map
 */
ChangeToWWControl.prototype.loadLayers = function(map) {
	var layers = map.getLayers();
	for (var i = layers.getLength(); i >= 0; --i) {
		var config;
		var lyr;
		l = layers.item(i)		
		console.log(l);
//	    console.log(l.wms_url);
//		console.log(l.layer_name);
//		console.log(l.getExtent());
//		console.log(l.getVisible());
//		console.log(l.getProperties());		
		if (l){
			this.loadLayer(l);
		}		
	}
	this.wwd.redraw();	
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




