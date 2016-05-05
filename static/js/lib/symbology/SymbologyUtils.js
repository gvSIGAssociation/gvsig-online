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
 * @author: Javi Rodrigo <jrodrigo@scolab.es>
 */

var SymbologyUtils = function() {};

SymbologyUtils.prototype.createPointSymbolizer = function(element){
					
	var sld = '';
	sld += '<PointSymbolizer>';
	sld += 	'<Graphic>';
	sld += 		'<Mark>';
	sld += 			'<WellKnownName>' + element.shape + '</WellKnownName>';
	sld += 			'<Fill>';
	sld += 				'<CssParameter name="fill">' + element.fill_color + '</CssParameter>';
	sld += 				'<CssParameter name="fill-opacity">' + element.fill_opacity + '</CssParameter>';
	sld += 			'</Fill>';
	sld += 			'<Stroke>';
	sld += 				'<CssParameter name="stroke">' + element.border_color + '</CssParameter>';
	sld += 				'<CssParameter name="stroke-width">' + element.border_size + '</CssParameter>';
	sld += 				'<CssParameter name="stroke-opacity">' + element.border_opacity + '</CssParameter>';
	sld += 			'</Stroke>';
	sld += 		'</Mark>';
	sld += 	'</Graphic>';
	sld += '</PointSymbolizer>';
	
	var symbolizer = {
		name: element.name,
		sld_code: sld
	}
	
	return symbolizer;
};

SymbologyUtils.prototype.createLineSymbolizer = function(element){
	
	var sld = '';
	sld += '<LineSymbolizer>';
	sld += 	'<Stroke>';
	sld += 		'<CssParameter name="stroke">' + element.border_color + '</CssParameter>';
	sld += 		'<CssParameter name="stroke-width">' + element.border_size + '</CssParameter>';
	sld += 		'<CssParameter name="stroke-opacity">' + element.border_opacity + '</CssParameter>';
	sld += 	'</Stroke>';
	sld += '</LineSymbolizer>';
	
	var symbolizer = {
		name: element.name,
		sld_code: sld
	}
	
	return symbolizer;
};

SymbologyUtils.prototype.createPolygonSymbolizer = function(element){
	
	var sld = '';
	sld += '<PolygonSymbolizer>';
	sld += 	'<Fill>';
	sld += 		'<CssParameter name="fill">' + element.fill_color + '</CssParameter>';
	sld += 		'<CssParameter name="fill-opacity">' + element.fill_opacity + '</CssParameter>';
	sld += 	'</Fill>';
	sld += 	'<Stroke>';
	sld += 		'<CssParameter name="stroke">' + element.border_color + '</CssParameter>';
	sld += 		'<CssParameter name="stroke-width">' + element.border_size + '</CssParameter>';
	sld += 		'<CssParameter name="stroke-opacity">' + element.border_opacity + '</CssParameter>';
	sld += 	'</Stroke>';
	sld += '</PolygonSymbolizer>';
	
	var symbolizer = {
		name: element.name,
		sld_code: sld
	}
	return symbolizer;
};

SymbologyUtils.prototype.createRasterSymbolizer = function(element){
	
	var sld = '';
	sld += '<RasterSymbolizer>';
	sld += 	'<Opacity>1</Opacity>';
	sld += 	'<ColorMap></ColorMap>';
	sld += '</RasterSymbolizer>';
	
	var symbolizer = {
		name: element.name,
		sld_code: sld
	}
	
	return symbolizer;
};
	
SymbologyUtils.prototype.createTextSymbolizer = function(element){
	
	var sld = '';
	sld += '<TextSymbolizer>';
	sld += 	'<Label>';
	sld += 		'<PropertyName>' + element.field + '</PropertyName>';
	sld +=  '</Label>';
	sld += 	'<Font>';
	sld += 		'<CssParameter name="font-family">' + element.font_family + '</CssParameter>';
	sld += 		'<CssParameter name="font-size">' + element.font_size + '</CssParameter>';
	sld += 		'<CssParameter name="font-style">' + element.font_style + '</CssParameter>';
	sld += 	'</Font>';
	sld += 	'<Fill>';
	sld += 		'<CssParameter name="fill">' + element.font_color + '</CssParameter>';
	sld += 		'<CssParameter name="fill-opacity">1</CssParameter>';
	sld += 	'</Fill>';
	sld += '</TextSymbolizer>';
	
	var symbolizer = {
		name: element.name,
		sld_code: sld
	}
	
	return symbolizer;
}; 