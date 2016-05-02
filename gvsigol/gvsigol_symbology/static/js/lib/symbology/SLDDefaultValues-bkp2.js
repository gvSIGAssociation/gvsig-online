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
				"Data-origin":{
				type: "field-definition",
				definition: {
					component: "panel-chooser-input",
					id: "point-panel-chooser-input-data-origin-input",
					label: "Fuente de datos",
					defaultValue: "0",
					optionNames: ["Vectorial symbol", "Marker"],
					values: [{
						WellKnownName:{
							type: "field-definition",
							definition: {
								component: "select-input",
								id: "point-select-input-marker-wellknownname-input",
								label: "WellKnownName",
								defaultValue: "circle",
								values: '{"circle":"Círculo", "square":"Cuadrado", "triangle": "Triángulo", "cross": "Cruz", "star": "Estrella", "x": "X"}',
								initialOption: "Elige una opción",
								jsonPath: "$.Graphic.Mark.WellKnownName",
								previewAttrName: "wellknownname",
								mandatory: true
							}
						},
						Fill:{
							fill: {
								type: "field-definition",
								definition: {
									component: "color-chooser",
									id: "point-color-chooser-fill-fill",
									label: "Color símbolo",
									defaultValue: "#26a69a",
									jsonPath: "$.Graphic.Mark.Fill.CssParameter[?(@.name=='fill')].text",
									previewAttrName: "fill",
									mandatory: true
								}
							},
							Opacity:{
								type: "field-definition",
								definition: {
									component: "range-input",
									id: "point-fill-opacity-range",
									label: 'Opacidad relleno',
									defaultValue: "1",
									min: "0",
									max: "1",
									step: "0.01",
									jsonPath: "$.Graphic.Mark.Fill.CssParameter[?(@.name=='fill-opacity')].text",
									previewAttrName: "fill-opacity",
									mandatory: true
								}
							}
						},
						StrokePanel:{
							type: "field-definition",
							definition: {
								component: "panel-chooser-input",
								id: "point-panel-chooser-input-data-origin-input",
								label: "Fuente de datos",
								defaultValue: "0",
								optionNames: ["Has Stroke?", ""],
								values: [{
									Stroke:{
										stroke: {
											type: "field-definition",
											definition: {
												component: "color-chooser",
												id: "point-color-chooser-stroke-stroke",
												label: "Color borde",
												defaultValue: "#000000",
												jsonPath: "$.Graphic.Mark.Stroke.CssParameter[?(@.name=='stroke')].text",
												previewAttrName: "stroke",
												mandatory: false
											}
										},
										"stroke-width":{
											type: "field-definition",
											definition: {
												component: "number-input",
												id: "point-size-input-stroke-width",
												label: 'Tamaño borde',
												defaultValue: "0",
												min: "0",
												max: "1000",
												step: "1",
												jsonPath: "$.Graphic.Mark.Stroke.CssParameter[?(@.name=='stroke-width')].text",
												previewAttrName: "stroke-width",
												mandatory: true
											}
										},
										"Stroke-opacity":{
											type: "field-definition",
											definition: {
												component: "range-input",
												id: "point-stroke-opacity-range",
												label: 'Opacidad borde',
												defaultValue: "1",
												min: "0",
												max: "1",
												step: "0.01",
												jsonPath: "$.Graphic.Mark.Stroke.CssParameter[?(@.name=='stroke-opacity')].text",
												previewAttrName: "stroke-opacity",
												mandatory: true
											}
										}
									}
								},
								{
								}]
									
								}
							}
					},
					{
						Selector:{
							type: "field-definition",
							definition: {
								component: "image-picker-input",
								id: "point-resource-image-picker",
								label: 'Selecciona imagen',
								selectedOption: false,
								jsonPath: "$.Graphic.ExternalGraphic",
								rootUrl: "/media/",
								previewAttrName: "src-image",
								mandatory: true
							}
						}
					}],
					mandatory: false
				}
				
			},
			/*
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
					jsonPath: "$.Graphic.Opacity",
					previewAttrName: "opacity",
					mandatory: true
				}
			},
			*/
			Size:{
				type: "field-definition",
				definition: {
					component: "number-input",
					id: "point-size-input",
					label: 'Tamaño punto',
					defaultValue: "15",
					min: "1",
					max: "1000",
					step: "1",
					jsonPath: "$.Graphic.Size",
					previewAttrName: "size",
					mandatory: true
				}
			},
			
			Geometry:{
				Function: {
					type: "field-definition",
					definition: {
						component: "filter-input",
						id: "point-input-geometry-function-input",
						label: "Geometry function",
						defaultValue: "",
						values: '{"centroid": "Centroide", "area": "Area", "convexhull": "ConvexHull"}',
						fieldvalues: "",
						initialOption: "Elige un campo",
						jsonPath: "$.Geometry",
						previewAttrName: "",
						mandatory: true
						}
				}
			}
		},

		"LineSymbolizer":{
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
					jsonPath: "$.Opacity",
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
						jsonPath: "$.Stroke.CssParameter[?(@.name=='stroke')].text",
						previewAttrName: "stroke",
						mandatory: false
					}
				},
				"stroke-width":{
					type: "field-definition",
					definition: {
						component: "number-input",
						id: "line-size-input-stroke-width",
						label: 'Tamaño línea',
						defaultValue: "0",
						min: "0",
						max: "1000",
						step: "1",
						jsonPath: "$.Stroke.CssParameter[?(@.name=='stroke-width')].text",
						previewAttrName: "stroke-width",
						mandatory: true
					}
				}
			},
			Geometry:{
				Function: {
					type: "field-definition",
					definition: {
						component: "filter-input",
						id: "line-input-geometry-function-input",
						label: "Geometry function",
						defaultValue: "",
						values: '{"centroid": "Centroide", "area": "Area", "convexhull": "ConvexHull"}',
						fieldvalues: "",
						initialOption: "Elige un campo",
						jsonPath: "$.Geometry",
						previewAttrName: "",
						mandatory: true
						}
				}
			}
		},
		"PolygonSymbolizer":{
			Fill:{
				fill: {
					type: "field-definition",
					definition: {
						component: "color-chooser",
						id: "polygon-color-chooser-fill-fill",
						label: "Color símbolo",
						defaultValue: "#26a69a",
						jsonPath: "$.Fill.CssParameter[?(@.name=='fill')].text",
						previewAttrName: "fill",
						mandatory: true
					}
				},
				Opacity:{
					type: "field-definition",
					definition: {
						component: "range-input",
						id: "polygon-fill-opacity-range",
						label: 'Opacidad relleno',
						defaultValue: "1",
						min: "0",
						max: "1",
						step: "0.01",
						jsonPath: "$.Fill.CssParameter[?(@.name=='fill-opacity')].text",
						previewAttrName: "fill-opacity",
						mandatory: true
					}
				}
			}, 
			Stroke:{
				stroke: {
					type: "field-definition",
					definition: {
						component: "color-chooser",
						id: "polygon-color-chooser-stroke-stroke",
						label: "Color borde",
						defaultValue: "#000000",
						jsonPath: "$.Stroke.CssParameter[?(@.name=='stroke')].text",
						previewAttrName: "stroke",
						mandatory: false
					}
				},
				Opacity:{
					type: "field-definition",
					definition: {
						component: "range-input",
						id: "polygon-stroke-opacity-range",
						label: 'Opacidad borde',
						defaultValue: "1",
						min: "0",
						max: "1",
						step: "0.01",
						jsonPath: "$.Stroke.CssParameter[?(@.name=='stroke-opacity')].text",
						previewAttrName: "stroke-opacity",
						mandatory: true
					}
				},
				"stroke-width":{
					type: "field-definition",
					definition: {
						component: "number-input",
						id: "polygon-stroke-stroke-width",
						label: 'Tamaño borde',
						defaultValue: "0",
						min: "0",
						max: "1000",
						step: "1",
						jsonPath: "$.Stroke.CssParameter[?(@.name=='stroke-width')].text",
						previewAttrName: "stroke-width",
						mandatory: true
					}
				},
				"stroke-type": {
					type: "field-definition",
					definition: {
						component: "select-input",
						id: "polygon-select-input-stroke-stroke-type",
						label: "Tipo de línea",
						defaultValue: "solid",
						values: '{"solid":"solido", "dotted":"punteado", "stripped":"rayado"}',
						initialOption: "Elige una opción",
						jsonPath: "$.Stroke.CssParameter[?(@.name=='solid-type')].text",
						previewAttrName: "stroke-linecal",
						mandatory: false
					}
				}
			
			},
			Geometry:{
				Function: {
					type: "field-definition",
					definition: {
						component: "filter-input",
						id: "line-input-geometry-function-input",
						label: "Geometry function",
						defaultValue: "",
						values: '{"centroid": "Centroide", "area": "Area", "convexhull": "ConvexHull"}',
						fieldvalues: "",
						initialOption: "Elige un campo",
						jsonPath: "$.Geometry",
						previewAttrName: "",
						mandatory: true
						}
				}
			}
		},
		"TextSymbolizer":{
				Label: {
					type: "field-definition",
					definition: {
						component: "select-input",
						id: "text-select-input-font-label-input",
						label: "Campo de las etiquetas",
						defaultValue: "",
						values: '',
						initialOption: "Elige un campo",
						jsonPath: "$.Label.PropertyName",
						previewAttrName: "",
						mandatory: true
						}
				},
				"font-family": {
					type: "field-definition",
					definition: {
						component: "select-input",
						id: "text-select-input-font-font-family-input",
						label: "Fuente",
						defaultValue: "Times New Roman",
						values: '{"Times New Roman":"Times new Roman", "Arial":"Arial"}',
						initialOption: "Elige una opción",
						jsonPath: "$.Font.CssParameter[?(@.name=='font-family')].text",
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
						jsonPath: "$.Font.CssParameter[?(@.name=='font-size')].text",
						previewAttrName: "font-size",
						mandatory: true
					}
				},
				fill: {
					type: "field-definition",
					definition: {
						component: "color-chooser",
						id: "text-color-chooser-fill-fill",
						label: "Color etiqueta",
						defaultValue: "#000000",
						jsonPath: "$.Fill.CssParameter[?(@.name=='fill')].text",
						previewAttrName: "fill",
						mandatory: true
					}
				},
				"font-weight": {
					type: "field-definition",
					definition: {
						component: "select-input",
						id: "text-select-input-font-font-weight-input",
						label: "Tipo de fuente",
						defaultValue: "plain",
						values: '{"plain":"Normal", "bold":"Negrita", "italic": "Cursiva", "bolditalic": "Negrita y cursiva"}',
						initialOption: "Elige una opción",
						jsonPath: "$.Font.CssParameter[?(@.name=='font-weight')].text",
						previewAttrName: "font-weight",
						mandatory: true
					}
			},
			Halo:{
				"halo-color": {
					type: "field-definition",
					definition: {
						component: "color-chooser",
						id: "halo-color-chooser-fill-fill",
						label: "Color halo",
						defaultValue: "#FFFFFF",
						jsonPath: "$.Halo.Fill.CssParameter[?(@.name=='fill')].text",
						previewAttrName: "",
						mandatory: true
					}
				},
				"halo-opacity": {
					type: "field-definition",
					definition: {
						component: "range-input",
						id: "halo-opacity-range",
						label: 'Opacidad halo',
						defaultValue: "0",
						min: "0",
						max: "1",
						step: "0.01",
						jsonPath: "$.Halo.Fill.CssParameter[?(@.name=='fill-opacity')].text",
						previewAttrName: "",
						mandatory: true
					}
				},
				"halo-radius": {
					type: "field-definition",
					definition: {
						component: "number-input",
						id: "halo-radius-size-number",
						label: 'Radio del halo',
						defaultValue: "1",
						min: "0",
						max: null,
						step: "1",
						jsonPath: "$.Halo.Radius",
						previewAttrName: "",
						mandatory: true
					}
				}
			}, 
			Vendor:{
				spaceAround: {
					type: "field-definition",
					definition: {
						component: "number-input",
						id: "text-vendor-space-around",
						label: 'Tamaño borde',
						defaultValue: "0",
						min: "-1000",
						max: "1000",
						step: "1",
						jsonPath: "$.VendorOption[?(@.name=='spaceAround')].text",
						previewAttrName: "",
						mandatory: false
					}
				},
				goodnessOfFit:{
					type: "field-definition",
					definition: {
						component: "number-input",
						id: "text-vendor-godness-on-fit",
						label: 'goodnessOfFit',
						defaultValue: "0",
						min: "-1000",
						max: "1000",
						step: "1",
						jsonPath: "$.VendorOption[?(@.name=='goodnessOfFit')].text",
						previewAttrName: "",
						mandatory: false
					}
				},
				conflictResolution:{
					type: "field-definition",
					definition: {
						component: "check-input",
						id: "text-vendor-conflict-resolution",
						group: "",
						classes: "with-gap",
						label: 'Resolución de conflictos',
						defaultValue: false,
						jsonPath: "$.VendorOption[?(@.name=='conflictResolution')].text",
						previewAttrName: "",
						mandatory: false
					}
				}
			},
			Geometry:{
				Function: {
					type: "field-definition",
					definition: {
						component: "filter-input",
						id: "line-input-geometry-function-input",
						label: "Geometry function",
						defaultValue: "",
						values: '{"centroid": "Centroide", "area": "Area", "convexhull": "ConvexHull"}',
						fieldvalues: "",
						initialOption: "Elige un campo",
						jsonPath: "$.Geometry",
						previewAttrName: "",
						mandatory: true
						}
				}
			}
		}
}