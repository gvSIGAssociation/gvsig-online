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
 * @author: lsanjaime <lsanjaime@scolab.es>
 */

/**
 * Plugin MediaDisplay - Filtra la interacción del mapa para mostrar solo capas multimedia
 */
var MediaDisplay = function(config, conf, map) {
	var self = this;
	this.config = config;
	this.conf = conf;
	this.map = map;
	this.enabledLayers = config.enabled_layers || [];

	this.id = "mediadisplay";
	this.$button = $("#mediadisplay");

	var this_ = this;
	var handler = function(e) {
		this_.handler(e);
	};

	this.$button.on('click', handler);
	this.$button.on('touchstart', handler);

	// Inicializar filtrado de capas
	this.initializeLayerFiltering();
};

/**
 * Estado activo del plugin
 */
MediaDisplay.prototype.active = false;

/**
 * Plugin desactivatable
 */
MediaDisplay.prototype.deactivable = true;

/**
 * Inicializar el filtrado de capas
 */
MediaDisplay.prototype.initializeLayerFiltering = function() {
	console.log('MediaDisplay initialized with layers:', this.enabledLayers);
	
	// Si no hay capas configuradas, deshabilitar el botón
	if (this.enabledLayers.length === 0) {
		this.$button.addClass('disabled');
		this.$button.attr('title', gettext('No hay capas multimedia configuradas'));
	}
};

/**
 * Manejar clic en el botón
 */
MediaDisplay.prototype.handler = function(e) {
	e.preventDefault();
	var self = this;

	if (this.enabledLayers.length === 0) {
		messageBox.show('warning', gettext('No hay capas multimedia configuradas. Configure las capas en el panel de administración.'));
		return;
	}

	if (!this.active) {
		this.activate();
	} else {
		this.deactivate();
	}
};

/**
 * Activar modo multimedia
 */
MediaDisplay.prototype.activate = function() {
	this.active = true;
	this.$button.addClass('button-active');
	
	// Filtrar la interacción del mapa para solo las capas multimedia
	this.filterMapInteraction();
	
	// Mostrar mensaje
	messageBox.show('info', gettext('Modo multimedia activado. Solo se interactúa con capas multimedia.'));
};

/**
 * Desactivar modo multimedia
 */
MediaDisplay.prototype.deactivate = function() {
	this.active = false;
	this.$button.removeClass('button-active');
	
	// Restaurar interacción normal del mapa
	this.restoreMapInteraction();
	
	// Mostrar mensaje
	messageBox.show('info', gettext('Modo multimedia desactivado. Interacción normal restaurada.'));
};

/**
 * Filtrar la interacción del mapa para solo capas multimedia
 */
MediaDisplay.prototype.filterMapInteraction = function() {
	var self = this;
	
	// Interceptar eventos de clic en el mapa
	this.map.on('click', function(event) {
		self.handleMapClick(event);
	});
	
	// Interceptar eventos de hover en el mapa
	this.map.on('pointermove', function(event) {
		self.handleMapHover(event);
	});
	
	console.log('Map interaction filtered for multimedia layers:', this.enabledLayers);
};

/**
 * Restaurar interacción normal del mapa
 */
MediaDisplay.prototype.restoreMapInteraction = function() {
	// Remover listeners específicos del plugin
	this.map.un('click', this.handleMapClick);
	this.map.un('pointermove', this.handleMapHover);
	
	console.log('Map interaction restored to normal');
};

/**
 * Manejar clic en el mapa
 */
MediaDisplay.prototype.handleMapClick = function(event) {
	var self = this;
	
	// Obtener features en el punto de clic
	var features = this.map.getFeaturesAtPixel(event.pixel);
	
	if (features.length > 0) {
		// Filtrar solo features de capas multimedia
		var multimediaFeatures = features.filter(function(feature) {
			var layerName = self.getLayerNameFromFeature(feature);
			return self.enabledLayers.indexOf(layerName) !== -1;
		});
		
		if (multimediaFeatures.length > 0) {
			// Mostrar información de features multimedia
			this.showMultimediaInfo(multimediaFeatures);
		} else {
			messageBox.show('info', gettext('No hay recursos multimedia en esta ubicación.'));
		}
	}
};

/**
 * Manejar hover en el mapa
 */
MediaDisplay.prototype.handleMapHover = function(event) {
	// Implementar lógica de hover si es necesaria
	// Por ejemplo, cambiar cursor cuando hay features multimedia
};

/**
 * Obtener nombre de capa desde un feature
 */
MediaDisplay.prototype.getLayerNameFromFeature = function(feature) {
	// Esta función depende de cómo esté implementado el sistema de capas
	// en gvSIG Online. Necesitarás adaptarla según la estructura real.
	
	// Ejemplo genérico - ajustar según la implementación real
	if (feature.get('layer_name')) {
		return feature.get('layer_name');
	}
	
	// Buscar en las propiedades del feature
	var properties = feature.getProperties();
	if (properties.layer_name) {
		return properties.layer_name;
	}
	
	// Si no se encuentra, retornar null
	return null;
};

/**
 * Mostrar información multimedia
 */
MediaDisplay.prototype.showMultimediaInfo = function(features) {
	var info = [];
	
	features.forEach(function(feature) {
		var properties = feature.getProperties();
		var layerName = this.getLayerNameFromFeature(feature);
		
		// Buscar campos que puedan contener multimedia
		Object.keys(properties).forEach(function(key) {
			var value = properties[key];
			if (this.isMediaField(key, value)) {
				info.push({
					layer: layerName,
					field: key,
					value: value
				});
			}
		}.bind(this));
	}.bind(this));
	
	if (info.length > 0) {
		this.displayMultimediaPopup(info);
	}
};

/**
 * Verificar si un campo contiene multimedia
 */
MediaDisplay.prototype.isMediaField = function(fieldName, value) {
	// Verificar por nombre de campo
	var mediaFieldNames = ['image', 'photo', 'foto', 'imagen', 'media', 'multimedia', 'url', 'path'];
	var isMediaField = mediaFieldNames.some(function(name) {
		return fieldName.toLowerCase().indexOf(name) !== -1;
	});
	
	// Verificar por valor (URLs de imágenes, etc.)
	var isMediaValue = false;
	if (typeof value === 'string') {
		var mediaExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'];
		isMediaValue = mediaExtensions.some(function(ext) {
			return value.toLowerCase().indexOf(ext) !== -1;
		});
	}
	
	return isMediaField || isMediaValue;
};

/**
 * Mostrar popup con información multimedia
 */
MediaDisplay.prototype.displayMultimediaPopup = function(info) {
	var content = '<div class="multimedia-popup">';
	content += '<h4>' + gettext('Recursos Multimedia') + '</h4>';
	
	info.forEach(function(item) {
		content += '<div class="multimedia-item">';
		content += '<strong>' + item.layer + '</strong><br>';
		content += '<strong>' + item.field + ':</strong> ';
		
		if (this.isImageUrl(item.value)) {
			content += '<img src="' + item.value + '" style="max-width: 200px; max-height: 150px;"><br>';
		} else {
			content += item.value + '<br>';
		}
		
		content += '</div><br>';
	}.bind(this));
	
	content += '</div>';
	
	// Mostrar popup (ajustar según el sistema de popups de gvSIG Online)
	messageBox.show('info', content);
};

/**
 * Verificar si una URL es una imagen
 */
MediaDisplay.prototype.isImageUrl = function(url) {
	var imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'];
	return imageExtensions.some(function(ext) {
		return url.toLowerCase().indexOf(ext) !== -1;
	});
};