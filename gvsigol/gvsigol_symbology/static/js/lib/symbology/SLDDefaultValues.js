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
					type: "radio",
					jsonPath: null,
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
						"Stroke":{
							type: "field-definition",
							definition: {
								component: "panel-chooser-input",
								id: "point-panel-chooser-input-border-input",
								label: "Borde",
								defaultValue: "0",
								type: "checkbox",
								jsonPath: "$.Graphic.Mark.Stroke",
								optionNames: ["Con borde", "Sin borde"],
								values: [{
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
												defaultValue: "1",
												min: "1",
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
								},
								{
									
								}],
								mandatory: true
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
						values: '{"null": "", "centroid": "Centroide", "area": "Area", "convexhull": "ConvexHull"}',
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
			"LineType":{
				type: "field-definition",
				definition: {
					component: "panel-chooser-input",
					id: "point-panel-chooser-input-data-origin-input",
					label: "Tipo de relleno",
					type: "radio",
					jsonPath: null,
					defaultValue: "0",
					optionNames: ["Línea sólida", "Línea con patrones"],
					values: [{
						Stroke:{
							stroke: {
								type: "field-definition",
								definition: {
									component: "color-chooser",
									id: "line-color-chooser-stroke-stroke",
									label: "Color línea",
									selectedOption: false,
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
						}
					},
					{
						WellKnownName:{
							type: "field-definition",
							definition: {
								component: "select-input",
								id: "line-select-input-marker-wellknownname-input",
								label: "Tramado de línea",
								selectedOption: false,
								defaultValue: "",
								values: '{"circle":"Círculo", "square":"Cuadrado", "triangle": "Triángulo", "cross": "Cruz", "star": "Estrella", "x": "X", "shape://vertline":"Líneas verticales", "shape://horline":"Líneas horizontales", "shape://slash": "Barra", "shape://backslash": "Contrabarra", "shape://plus": "Cruz", "shape://times": "X", "shape://dot": "Punteado", "shape://oarrow": "Flecha abierta", "shape://carrow": "Flecha cerrada"}',
								initialOption: "Elige una opción",
								jsonPath: "$.Stroke.GraphicStroke.Graphic.Mark.WellKnownName",
								previewAttrName: "wellknownname",
								mandatory: true
							}
						},
						Size:{
							type: "field-definition",
							definition: {
								component: "number-input",
								id: "polygon-size-input",
								label: 'Tamaño imagen',
								defaultValue: "15",
								min: "1",
								max: "1000",
								step: "1",
								jsonPath: "$.Stroke.GraphicStroke.Graphic.Size",
								previewAttrName: "size",
								mandatory: true
							}
						},
						fill: {
							type: "field-definition",
							definition: {
								component: "color-chooser",
								id: "line-color-chooser-fill-fill",
								label: "Color símbolo",
								defaultValue: "#26a69a",
								jsonPath: "$.Stroke.GraphicStroke.Graphic.Mark.Fill.CssParameter[?(@.name=='fill')].text",
								previewAttrName: "fill",
								mandatory: true
							}
						}
					}]
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
					jsonPath: "$.Graphic.Opacity",
					previewAttrName: "opacity",
					mandatory: true
				}
			},
/*			PerpendicularOffset:{
				type: "field-definition",
				definition: {
					component: "number-input",
					id: "line-perpendicularoffset-input",
					label: 'Offset respecto línea original',
					defaultValue: "0",
					min: "-1000",
					max: "1000",
					step: "1",
					jsonPath:  "$.VendorOption[?(@.name=='perpendicular-offset')].text",
					previewAttrName: "",
					mandatory: true
				}
			},
*/			DashArray: {
				type: "field-definition",
				definition: {
					component: "text-input",
					id: "line-dasharray-input",
					label: 'Patrón pintado (en píxeles, separado por espacios)',
					defaultValue: "",
					jsonPath: "$.Stroke.CssParameter[?(@.name=='stroke-dasharray')].text",
					previewAttrName: "",
					mandatory: true
				}
			},
			
			DashOffset: {
				type: "field-definition",
				definition: {
					component: "number-input",
					id: "line-dashoffset-input",
					label: 'Offset patrón (píxeles)',
					defaultValue: "0",
					min: "0",
					max: "1000",
					step: "1",
					jsonPath: "$.Stroke.CssParameter[?(@.name=='stroke-dashoffset')].text",
					previewAttrName: "",
					mandatory: true
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
						values: '{"null": "", "centroid": "Centroide", "area": "Area", "convexhull": "ConvexHull"}',
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
			"Data-origin":{
				type: "field-definition",
				definition: {
					component: "panel-chooser-input",
					id: "point-panel-chooser-input-data-origin-input",
					label: "Tipo de relleno",
					type: "radio",
					jsonPath: null,
					defaultValue: "0",
					optionNames: ["Color sólido", "Patrón lineal", "Patrón TTF", "Imagen en mosaico"],
					values: [{
						Fill:{
							fill: {
								type: "field-definition",
								definition: {
									component: "color-chooser",
									id: "polygon-color-chooser-fill-fill",
									label: "Color símbolo",
									defaultValue: "#26a69a",
									selectedOption: false,
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
						}
					},
					{
						Alert:{
							type: "field-definition",
							definition: {
								component: "alert-message",
								id: "polygon-alert-mesasage",
								type: "alert",
								defaultValue: "La previsualización del símbolo no funciona con polígonos tramados",
								jsonPath: "",
								previewAttrName: "",
								mandatory: true
							}
						},
						WellKnownName:{
							type: "field-definition",
							definition: {
								component: "select-input",
								id: "polygon-select-input-marker-wellknownname-input",
								label: "Tramado de relleno",
								selectedOption: false,
								defaultValue: "",
								values: '{"shape://vertline":"Líneas verticales", "shape://horline":"Líneas horizontales", "shape://slash": "Barra", "shape://backslash": "Contrabarra", "shape://plus": "Cruz", "shape://times": "X", "shape://dot": "Punteado", "shape://oarrow": "Flecha abierta", "shape://carrow": "Flecha cerrada"}',
								initialOption: "Elige una opción",
								jsonPath: "$.Fill.GraphicFill.Graphic.Mark.WellKnownName",
								previewAttrName: "wellknownname",
								mandatory: true
							}
						},
						Relleno:{
							fill: {
								type: "field-definition",
								definition: {
									component: "color-chooser",
									id: "polygon-color-chooser-stroke-fill",
									label: "Color línea relleno",
									defaultValue: "#26a69a",
									jsonPath: "$.Fill.GraphicFill.Graphic.Mark.Stroke.CssParameter[?(@.name=='stroke')].text",
									previewAttrName: "fill",
									mandatory: true
								}
							},
							width:{
								type: "field-definition",
								definition: {
									component: "number-input",
									id: "polygon-stroke-width-input",
									label: 'Tamaño línea relleno',
									defaultValue: "1",
									min: "0",
									max: "100",
									step: "1",
									jsonPath: "$.Fill.GraphicFill.Graphic.Mark.Stroke.CssParameter[?(@.name=='stroke-width')].text",
									previewAttrName: "",
									mandatory: true
								}
							}
						},
						Size:{
							type: "field-definition",
							definition: {
								component: "number-input",
								id: "polygon-size-input",
								label: 'Tamaño imagen',
								defaultValue: "15",
								min: "1",
								max: "1000",
								step: "1",
								jsonPath: "$.Fill.GraphicFill.Graphic.Size",
								previewAttrName: "size",
								mandatory: true
							}
						}
					},
					{
						Alert:{
							type: "field-definition",
							definition: {
								component: "alert-message",
								id: "polygon-alert-message",
								type: "alert",
								defaultValue: "En construcción. No funciona",
								jsonPath: "",
								previewAttrName: "",
								mandatory: true
							}
						},
						WellKnownName:{
							type: "field-definition",
							definition: {
								component: "text-input",
								id: "polygon-ttf-input",
								label: 'Caracter patrón (TTF)',
								placeHolder: 'ttf://<fontname>#<hexcode>',
								selectedOption: false,
								defaultValue: "",
								jsonPath: "$.Graphic.Mark.WellKnownName",
								mandatory: true
							}
						},
						Size:{
							type: "field-definition",
							definition: {
								component: "number-input",
								id: "polygon-ttf-size-input",
								label: 'Tamaño caracter',
								defaultValue: "15",
								min: "1",
								max: "1000",
								step: "1",
								jsonPath: "$.Fill.GraphicFill.Graphic.Size",
								previewAttrName: "size",
								mandatory: true
							}
						},
						Vendor:{
							type: "field-definition",
							definition: {
								component: "number-input",
								id: "text-vendor-space-around",
								label: 'Offset entre patrones',
								defaultValue: "0",
								min: "0",
								max: "1000",
								step: "1",
								jsonPath: "$.VendorOption[?(@.name=='graphic-margin')].text",
								previewAttrName: "",
								mandatory: false
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
								jsonPath: "$.Fill.GraphicFill.Graphic.ExternalGraphic",
								rootUrl: "/media/",
								previewAttrName: "src-image",
								mandatory: true
							}
						},
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
								jsonPath: "$.Fill.GraphicFill.Graphic.Size",
								previewAttrName: "size",
								mandatory: true
							}
						}
					}],
					mandatory: false
				}
				
			},
			Stroke:{
				type: "field-definition",
				definition: {
					component: "panel-chooser-input",
					id: "polygon-panel-chooser-input-border-input",
					label: "Borde",
					jsonPath: "$.Stroke",
					type: "checkbox",
					defaultValue: "0",
					optionNames: ["Con borde", "Sin borde"],
					values: [{
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
							"stroke-width":{
								type: "field-definition",
								definition: {
									component: "number-input",
									id: "polygon-size-input-stroke-width",
									label: 'Tamaño borde',
									defaultValue: "1",
									min: "1",
									max: "1000",
									step: "1",
									jsonPath: "$.Stroke.CssParameter[?(@.name=='stroke-width')].text",
									previewAttrName: "stroke-width",
									mandatory: true
								}
							},
							"Stroke-opacity":{
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
					{
						
					}],
					mandatory: true
				}
			},
			Rotation:{
				type: "field-definition",
				definition: {
					component: "range-input",
					id: "polygon-rotation-range",
					label: 'Rotación símbolo',
					defaultValue: "1",
					min: "0",
					max: "360",
					step: "1",
					jsonPath: "$.Rotation",
					previewAttrName: "rotation",
					mandatory: true
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
						values: '{"null": "", "centroid": "Centroide", "area": "Area", "convexhull": "ConvexHull"}',
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
						label: "Grosor de fuente",
						defaultValue: "normal",
						values: '{"normal":"Normal", "bold":"Negrita"}',
						initialOption: "Elige una opción",
						jsonPath: "$.Font.CssParameter[?(@.name=='font-weight')].text",
						previewAttrName: "font-weight",
						mandatory: true
					}
				},
				"font-style": {
					type: "field-definition",
					definition: {
						component: "select-input",
						id: "text-select-input-font-font-style-input",
						label: "Estilo de fuente",
						defaultValue: "normal",
						values: '{"normal":"Normal", "italic": "Cursiva", "oblique": "Oblicua"}',
						initialOption: "Elige una opción",
						jsonPath: "$.Font.CssParameter[?(@.name=='font-style')].text",
						previewAttrName: "font-style",
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
				maxRepetitions: {
					type: "field-definition",
					definition: {
						component: "number-input",
						id: "text-vendor-max-repetitions",
						label: 'Máximo número de repeticiones',
						defaultValue: "1",
						min: "0",
						max: "1000",
						step: "1",
						jsonPath: "$.VendorOption[?(@.name=='repeat')].text",
						previewAttrName: "",
						mandatory: false
					}
				},
				autoWrap: {
					type: "field-definition",
					definition: {
						component: "number-input",
						id: "text-vendor-autowrap",
						label: 'Máxima longitud de etiqueta (píxeles)',
						defaultValue: "100",
						min: "0",
						max: "1000",
						step: "1",
						jsonPath: "$.VendorOption[?(@.name=='autoWrap')].text",
						previewAttrName: "",
						mandatory: false
					}
				},
				spaceAround: {
					type: "field-definition",
					definition: {
						component: "number-input",
						id: "text-vendor-space-around",
						label: 'Espacio mínimo envolvente de la etiqueta',
						defaultValue: "0",
						min: "-1000",
						max: "1000",
						step: "1",
						jsonPath: "$.VendorOption[?(@.name=='spaceAround')].text",
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
						label: 'Resolución de conflictos entre etiquetas solapadas',
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
						values: '{"null": "", "centroid": "Centroide", "area": "Area", "convexhull": "ConvexHull"}',
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