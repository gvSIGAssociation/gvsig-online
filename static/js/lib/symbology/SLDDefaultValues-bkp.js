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
 * @author: José Badía <jbadia@scolab.es>
 */

var SLDDefaultValues = SLDDefaultValues || {};

/**
 * Clase que especifica las características de los valores SLD.
 * Los campos que definen cada propiedad son los siguientes:
 *     - type: tipo de componente del formulario (text-input, number-input, range, color-chooser, etc)
 *     
 *     - id: identificador del componente
 *     - label: etiqueta para el componente
 *     
 *     - jsonPath: ruta dentro del SLD donde se encuentra esta propiedad
 *     
 *     - defaultValue: valor por defecto (si corresponde)
 *     - min: valor mínimo (sólo numéricos)
 *     - max: valor máximo (sólo numéricos)
 *     
 *     - mandatory: si es obligatorio
 *      
 */
SLDDefaultValues = {
		"PointSymbolizer":{
			WellKnownName:{
				type: "field-definition",
				definition: {
					component: "select-input",
					id: "point-select-input-marker-wellknownname-input",
					label: "WellKnownName",
					defaultValue: "circle",
					values: '{"circle":"Círculo", "square":"Cuadrado", "triangle": "Triángulo", "cross": "Cruz", "star": "Estrella", "x": "X"}',
					initialOption: "Elige una opción",
					jsonPath: "$.Graphic[0].Mark[0].WellKnownName[0].text",
					previewAttrName: "wellknownname",
					mandatory: true
				}
				
			},
			"Data-origin":{
				type: "field-definition",
				definition: {
					component: "panel-chooser-input",
					id: "point-panel-chooser-input-data-origin-input",
					label: "Fuente de datos",
					defaultValue: "0",
					optionNames: ["Paneles A", "Paneles B"],
					values: [{
						"Panel-A1":{
							fill: {
								type: "field-definition",
								definition: {
									component: "color-chooser",
									id: "point-color-chooser-fill-fill",
									label: "Color símbolo",
									defaultValue: "#26a69a",
									jsonPath: "$.Graphic[0].Mark[0].Fill[0].CssParameter[?(@.name=='fill')].text",
									previewAttrName: "fill",
									mandatory: true
								}
							},
							"fill-opacity":{
								type: "field-definition",
								definition: {
									component: "range-input",
									id: "point-opacity-range-fill-fill-opacity",
									label: 'Opacidad relleno punto',
									defaultValue: "1",
									min: "0",
									max: "1",
									step: "0.01",
									jsonPath: "$.Graphic[0].Mark[0].Fill[0].CssParameter[?(@.name=='fill-opacity')].text",
									previewAttrName: "fill-opacity",
									mandatory: false
								}
							}
						},
						"Panel-A2":{
							Size:{
								type: "field-definition",
								definition: {
									component: "number-input",
									id: "point-size-number",
									label: 'Tamaño punto',
									defaultValue: "10",
									min: "0",
									max: null,
									step: "1",
									jsonPath: "$.Size[0].text",
									previewAttrName: "size",
									mandatory: true
								}
							}
						}
					},
					{
						"Panel-B":{
							Opacity:{
								type: "field-definition",
								definition: {
									component: "range-input",
									id: "point-opacity-range",
									label: 'Opacidad punto',
									defaultValue: "1",
									min: "0",
									max: "1",
									step: "0.01",
									jsonPath: "$.Opacity[0].text",
									previewAttrName: "opacity",
									mandatory: true
								}
							}
						}
					}],
					mandatory: false
				}
				
			},
			Stroke:{
				stroke: {
					type: "field-definition",
					definition: {
						component: "color-chooser",
						id: "point-color-chooser-stroke-stroke",
						label: "Color borde",
						defaultValue: "#000000",
						jsonPath: "$.Graphic[0].Mark[0].Stroke[0].CssParameter[?(@.name=='stroke')].text",
						previewAttrName: "stroke",
						mandatory: false
					}
				}
			}
		},

		"LineSymbolizer":{
			Fill:{
				fill: {
					type: "field-definition",
					definition: {
						component: "color-chooser",
						id: "line-color-chooser-fill-fill",
						label: "Color línea",
						defaultValue: "#26a69a",
						jsonPath: "$.Fill[0].CssParameter[?(@.name=='fill')].text",
						previewAttrName: "fill",
						mandatory: true
					}
				},
				"fill-opacity":{
					type: "field-definition",
					definition: {
						component: "range-input",
						id: "line-opacity-range-fill-fill-opacity",
						label: 'Opacidad relleno linea',
						defaultValue: "1",
						min: "0",
						max: "1",
						step: "0.01",
						jsonPath: "$.Fill[0].CssParameter[?(@.name=='fill-opacity')].text",
						previewAttrName: "fill-opacity",
						mandatory: false
					}
				}
			}, 
			Opacity:{
				type: "field-definition",
				definition: {
					component: "range-input",
					id: "line-opacity-range",
					label: 'Opacidad linea',
					defaultValue: "1",
					min: "0",
					max: "1",
					step: "0.01",
					jsonPath: "$.Opacity[0].text",
					previewAttrName: "opacity",
					mandatory: true
				}
			},
			Stroke:{
				stroke: {
					type: "field-definition",
					definition: {
						component: "color-chooser",
						id: "line-color-chooser-stroke-stroke",
						label: "Color línea",
						defaultValue: "#000000",
						jsonPath: "$.Stroke[0].CssParameter[?(@.name=='stroke')].text",
						previewAttrName: "stroke",
						mandatory: false
					}
				}
			}
		},
		"PolygonSymbolizer":{
			Opacity:{
				type: "field-definition",
				definition: {
					component: "range-input",
					id: "polygon-opacity-range",
					label: 'Opacidad punto',
					defaultValue: "1",
					min: "0",
					max: "1",
					step: "0.01",
					jsonPath: "$.Opacity[0].text",
					previewAttrName: "fill-opacity",
					mandatory: true
				}
			},
			Size:{
				type: "field-definition",
				definition: {
					component: "number-input",
					id: "polygon-size-number",
					label: 'Tamaño punto',
					defaultValue: "1",
					min: "0",
					max: null,
					step: "1",
					jsonPath: "$.Size[0].text",
					previewAttrName: "size",
					mandatory: true
				}
			},
			Rotation:{
				type: "field-definition",
				definition: {
					component: "range-input",
					id: "polygon-rotation-range",
					label: 'Rotación',
					defaultValue: "0",
					min: "0",
					max: "360",
					step: "1",
					jsonPath: "$.Rotation[0].text",
					previewAttrName: "rotation",
					mandatory: true
				}
			},
			Fill:{
				fill: {
					type: "field-definition",
					definition: {
						component: "color-chooser",
						id: "polygon-color-chooser-fill-fill",
						label: "Color símbolo",
						defaultValue: "#26a69a",
						jsonPath: "$.Fill[0].CssParameter[?(@.name=='fill')].text",
						previewAttrName: "fill",
						mandatory: true
					}
				}/*,
				"fill-opacity":{
					type: "field-definition",
					definition: {
						component: "range-input",
						id: "opacity-range-fill-fill-opacity",
						label: 'Opacidad punto',
						defaultValue: "1",
						min: "0",
						max: "1",
						step: "0.01",
						jsonPath: "$.Fill[0].CssParameter[?(@.name=='fill-opacity')].text",
						previewAttrName: "fill-opacity",
						mandatory: false
						}
				}*/
			}, 
			Stroke:{
				stroke: {
					type: "field-definition",
					definition: {
						component: "color-chooser",
						id: "polygon-color-chooser-stroke-stroke",
						label: "Color borde",
						defaultValue: "#000000",
						jsonPath: "$.Stroke[0].CssParameter[?(@.name=='stroke')].text",
						previewAttrName: "stroke",
						mandatory: false
					}
				},
				"stroke-type": {
					type: "field-definition",
					definition: {
						component: "select-input",
						id: "polygon-select-input-stroke-stroke-type",
						label: "Tipo de línea",
						defaultValue: "dotted",
						values: '{"solid":"solido", "dotted":"punteado", "stripped":"rayado"}',
						initialOption: "Elige una opción",
						jsonPath: "$.Stroke[0].CssParameter[?(@.name=='solid-type')].text",
						previewAttrName: "stroke-linecal",
						mandatory: false
					}
				}
			},
			Label:{
				Label:{
					type: "field-definition",
					definition: {
						component: "text-input",
						id: "polygon-label-input",
						label: 'Etiqueta',
						defaultValue: "",
						jsonPath: "$.Label[0].Label[0].text",
						mandatory: false
					}
				},
				Show:{
					type: "field-definition",
					definition: {
						component: "check-input",
						id: "polygon-label-show-check",
						group: "test",
						classes: "with-gap",
						label: 'Mostrar etiqueta',
						defaultValue: true,
						jsonPath: "$.Label[0].Show[0].text",
						mandatory: true
					}
				}
			}
		},
		"TextSymbolizer":{
			Font:{
				"font-family": {
					type: "field-definition",
					definition: {
						component: "select-input",
						id: "text-select-input-font-font-family-input",
						label: "Fuente",
						defaultValue: "Times New Roman",
						values: '{"Times New Roman":"Times new Roman", "Arial":"Arial"}',
						initialOption: "Elige una opción",
						jsonPath: "$.Font[0].CssParameter[?(@.name=='font-family')].text",
						previewAttrName: "font-family",
						mandatory: true
					}
				},
				"font-size": {
					type: "field-definition",
					definition: {
						component: "number-input",
						id: "text-font-size-number",
						label: 'Tamaño etiqueta',
						defaultValue: "10",
						min: "0",
						max: null,
						step: "1",
						jsonPath: "$.Font[0].CssParameter[?(@.name=='font-size')].text",
						previewAttrName: "font-size",
						mandatory: true
					}
				},
				"font-type": {
					type: "field-definition",
					definition: {
						component: "select-input",
						id: "text-select-input-font-font-family-input",
						label: "Fuente",
						defaultValue: "Normal",
						values: '{"Normal":"normal", "Negrita":"bold", "Cursiva": "italic"}',
						initialOption: "Elige una opción",
						jsonPath: "$.Font[0].CssParameter[?(@.name=='font-type')].text",
						previewAttrName: "font-type",
						mandatory: true
					}
				}
			},
			Fill:{
				fill: {
					type: "field-definition",
					definition: {
						component: "color-chooser",
						id: "text-color-chooser-fill-fill",
						label: "Color etiqueta",
						defaultValue: "#26a69a",
						jsonPath: "$.Fill[0].CssParameter[?(@.name=='fill')].text",
						previewAttrName: "fill",
						mandatory: true
					}
				}
			}
		}
}