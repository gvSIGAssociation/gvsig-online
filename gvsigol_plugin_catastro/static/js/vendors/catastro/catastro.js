var CatastroForm = function(show){
	this.vectorSource = null;
	this.vectorLayer = null;

	this.createForm(show);
}

CatastroForm.prototype.createForm = function(show){

var self = this;

var	ui = '<ul class="nav nav-tabs">';
	ui += 	'<li class="active"><a class="tab-popup" data-name="cadastral-reference-sel" href="#tab-cadastral-reference" data-toggle="tab">' + gettext('Referencia catastral') + '</a></li>';
	ui += 	'<li><a class="tab-popup" data-name="location-sel" href="#tab-location" data-toggle="tab">' + gettext('Localización') + '</a></li>';
	//ui += 	'<li><a class="tab-popup" data-name="registral-code-sel" href="#tab-registral-code" data-toggle="tab">' + gettext('Código Registral Único') + '</a></li>';
	ui += '</ul><br />';

	ui += '<div class="tab-content">';
	ui += 	'<div class="cadastral-tab tab-pane active" id="tab-cadastral-reference">';
	ui += '<div class="row">';
	ui += 	'<div class="col-md-12 form-group">';
	ui += 		'<label>' + gettext('Referencia catastral') + '(*)</label>';
	ui += 		'<input type="text" id="cadastral_reference_input" class="form-control form-sel cadastral-reference-sel">';
	ui += 	'</div>';
	ui += '</div>';
	ui += 	'</div>';
	ui += 	'<div class="cadastral-tab tab-pane" id="tab-location">';
	ui += '<div class="row">';
	ui += 	'<div class="col-md-6 form-group">';
	ui += 		'<label>' + gettext('Provincia') + '(*)</label>';
	ui += 		'<select id="provincia-input" class="form-control form-sel location-sel js-example-basic-single"></select>';
	ui += 	'</div>';
	ui += 	'<div class="col-md-6 form-group">';
	ui += 		'<label>' + gettext('Municipio') + '(*)</label>';
	ui += 		'<select id="municipio-input" class="form-control form-sel location-sel js-example-basic-single"></select>';
	ui += 	'</div>';
	ui += 	'<div class="col-md-12 form-group">';
	ui += 		'<input type="radio" id="urban_radio" class="form-sel location-sel" name="urban_rustic_radio" value="urban_radio" checked>';
	ui += 		'<label>' + gettext('Urbanos') + '</label>';
	ui += 	'</div>';
	ui += 	'<div id="urban_div" class="col-md-12 form-group">';
	ui += 		'<div class="col-md-2 form-group">';
	ui += 			'<label>' + gettext('Tipo vía') + '(*)</label>';
	ui += 			'<input id="road-type-input" class="form-control form-sel" disabled readonly>';
	ui += 		'</div>';
	ui += 		'<div class="col-md-8 form-group">';
	ui += 			'<label>' + gettext('Nombre vía') + '(*)</label>';
	ui += 			'<select id="road-name-input" class="form-control form-sel location-sel urban-sel js-example-basic-single"></select>';
	ui += 		'</div>';
	ui += 		'<div class="col-md-2 form-group">';
	ui += 			'<label>' + gettext('Número') + '(**)</label>';
	ui += 			'<input type="text" id="road-number-input" class="form-control form-sel location-sel urban-sel">';
	ui += 		'</div>';

	ui += 		'<div class="col-md-3 form-group">';
	ui += 			'<label>' + gettext('Bloque') + '</label>';
	ui += 			'<input type="text" id="road-block-input" class="form-control form-sel location-sel urban-sel">';
	ui += 		'</div>';
	ui += 		'<div class="col-md-3 form-group">';
	ui += 			'<label>' + gettext('Escalera') + '</label>';
	ui += 			'<input type="text" id="road-stair-input" class="form-control form-sel location-sel urban-sel">';
	ui += 		'</div>';
	ui += 		'<div class="col-md-3 form-group">';
	ui += 			'<label>' + gettext('Planta') + '</label>';
	ui += 			'<input type="text" id="road-floor-input" class="form-control form-sel location-sel urban-sel">';
	ui += 		'</div>';
	ui += 		'<div class="col-md-3 form-group">';
	ui += 			'<label>' + gettext('Puerta') + '</label>';
	ui += 			'<input type="text" id="road-door-input" class="form-control form-sel location-sel urban-sel">';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="col-md-12 form-group">';
	ui += 		'<input type="radio" id="rustic_radio" class="form-sel location-sel" name="urban_rustic_radio" value="rustic_radio">';
	ui += 		'<label>' + gettext('Rústico') + '</label>';
	ui += 	'</div>';
	ui += 	'<div id="rustic_div" class="col-md-12 form-group">';
	ui += 		'<div class="col-md-6 form-group">';
	ui += 			'<label>' + gettext('Polígono') + '(*)</label>';
	ui += 			'<input type="text" id="road-polygon-input" class="form-control form-sel location-sel rustic-sel" disabled>';
	ui += 		'</div>';
	ui += 		'<div class="col-md-6 form-group">';
	ui += 			'<label>' + gettext('Parcela') + '(*)</label>';
	ui += 			'<input type="text" id="road-parcel-input" class="form-control form-sel location-sel rustic-sel" disabled>';
	ui += 		'</div>';
	ui += '</div>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="cadastral-tab tab-pane" id="tab-registral-code">';
	ui += '<div class="row">';
	ui += 	'<div class="col-md-12 form-group">';
	ui += 		'<label>' + gettext('Código Registral Único') + '(*)</label>';
	ui += 		'<input type="text" id="unic_registral_code_input" class="form-control form-sel registral-code-sel">';
	ui += 	'</div>';
	ui += 	'</div>';
	ui += '</div>';
	ui += '<div id="destination-inputs" class="row">';
	ui += '</div>';

	$('#float-modal .modal-body').empty();
	$('#float-modal .modal-body').append(ui);

	var buttons = '';
	buttons += '<button id="float-modal-cancel-coordcalc" type="button" class="btn btn-default" data-dismiss="modal">' + gettext('Cancel') + '</button>';
	buttons += '<button id="float-modal-accept-coordcalc" type="button" class="btn btn-default">' + gettext('Calculate') + '</button>';

	$('#float-modal .modal-footer').empty();
	$('#float-modal .modal-footer').append(buttons);

//	$('#float-modal .modal-header').empty();
//	$('#float-modal .modal-header').append(ui2);

	if (show)
		$("#float-modal").modal('show');

	$("#float-modal-accept-coordcalc").on('click', function(){
		var tab = $(".cadastral-tab.active").first().attr("id");

		var url = "";
		var params = "";

		var rc = "";
		var srs = "EPSG:4326";

		var type = null;
		var params = {};

		if(tab == "tab-cadastral-reference"){
			type = 'ref_catastral';
			params = {
				rc : $("#cadastral_reference_input").val()
			}
		}

		if(tab == "tab-registral-code"){
			type = 'reg_code';
			params = {
				cr: $("#unic_registral_code_input").val()
			}
		}


		if(tab == "tab-location"){
			type = 'location';
			params = {
				provincia : $("#provincia-input").val(),
				municipio : $("#municipio-input").val()
			}

			var provincia = $("#provincia-input").val();
			var municipio = $("#municipio-input").val();

			if($("#urban_radio").is(":checked")){
				params['urban_radio'] = true;
				params['tipovia'] = $("#road-type-input").val();
				params['nombrevia'] = $("#road-name-input").val();
				params['numerovia'] = $("#road-number-input").val();
				params['kmvia'] = $("#road-km-input").val();
				params['bloquevia'] = $("#road-block-input").val();
				params['escaleravia'] = $("#road-stair-input").val();
				params['plantavia'] = $("#road-floor-input").val();
				params['puertavia'] = $("#road-door-input").val();
			}

			if($("#rustic_radio").is(":checked")){
			    params['urban_radio'] = false;
				params['poligonovia'] = $("#road-polygon-input").val();
				params['parcelavia'] = $("#road-parcel-input").val();
			}
		}




		var final_url = '/gvsigonline/catastro/get_referencia_catastral/'
		$.ajax({
			type: 'POST',
			async: false,
		  	url: final_url,
		  	data: {
		  		'tipo': type,
		  		'params': JSON.stringify(params)
			},
		  	success	:function(data){
		  		$("#float-modal").modal('hide');

                var coordinate = ol.proj.transform([parseFloat(data['xcen']), parseFloat(data['ycen'])], data['srs'], 'EPSG:3857');
				var popup = new ol.Overlay.Popup();
				viewer.core.map.addOverlay(popup);
				var popupContent = '<p>'+data['address']+'</p><p>' + gettext("RC") + ':&nbsp;<span style="font-weight:bold">' + data['rc'] + '</span></p>';
				popup.show(coordinate, '<div id="popup-show-more-info" class="popup-wrapper">' + popupContent + '</div>');

				viewer.core.map.getView().setCenter(coordinate);
				viewer.core.map.getView().setZoom(18);
                self.getRefCatastralPolygon(data['rc']);

                $("#popup-show-more-info").click(function(){
                	self.getRefCatastralInfo(parseFloat(data['xcen']), parseFloat(data['ycen']), data['srs'])
                })
			},
		  	error: function(){
		  		console.log("Can't get RC");
		  		$("#float-modal").modal('hide');
		  	}
		});




	});

	$(".tab-popup").click(function(){
		var selector = $(this).attr("data-name");

		$(".form-sel").each(function(){
			if($(this).hasClass(selector)){
				$(this).prop('disabled', false);
			}else{
				$(this).prop('disabled', true);
			}
		});


		if(!$("#urban_radio").prop('disabled') && $("#urban_radio").is(":checked")){
			$(".urban-sel").each(function(){
				$(this).prop('disabled', false);
			});
			$(".rustic-sel").each(function(){
				$(this).prop('disabled', true);
			});
		}

		if(!$("#rustic_radio").prop('disabled') && $("#rustic_radio").is(":checked")){
			$(".urban-sel").each(function(){
				$(this).prop('disabled', true);
			});
			$(".rustic-sel").each(function(){
				$(this).prop('disabled', false);
			});
		}
	})

	$("input[name=urban_rustic_radio]").change(function(){
		if(!$("#urban_radio").prop('disabled') && $("#urban_radio").is(":checked")){
			$(".urban-sel").each(function(){
				$(this).prop('disabled', false);
			});
			$(".rustic-sel").each(function(){
				$(this).prop('disabled', true);
			});
		}

		if(!$("#rustic_radio").prop('disabled') && $("#rustic_radio").is(":checked")){
			$(".urban-sel").each(function(){
				$(this).prop('disabled', true);
			});
			$(".rustic-sel").each(function(){
				$(this).prop('disabled', false);
			});
		}
	})


	var provincias_url = '/gvsigonline/catastro/get_provincias/'
	$.ajax({
		type: 'POST',
		async: false,
		dataType: "xml",
	  	url: provincias_url,
		success: function(data){
	  		var options = "<option value=\"---\">---</option>";
	  		$(data).find('prov').each(function() {
                var key = $(this).find("cpine").text();
                var value = $(this).find("np").text();
                options += "<option value=\""+value+"\">"+value+"</option>";
            });
	  		$("#provincia-input").empty().html(options);
	  		$("#provincia-input").unbind("change").change(function(){
	  			self.onMunicipallyKeyPress($(this).attr("id"));
	  		})
	  		$(".js-example-basic-single").select2();
		},
	  	error: function(){
	  		console.log("Can't get provinces")
	  	}
	});
}

CatastroForm.prototype.clearCatastroLayer = function(){
	var self = this;
	if(self.vectorSource != null){
		self.vectorSource.clear();
		viewer.core.map.removeLayer(self.vectorLayer);
		self.vectorSource = null;
		self.vectorLayer = null;
	}

	$(".catastro-clear-button").each(function(){
		$(this).css("display", "none");
	});
}

CatastroForm.prototype.getRefCatastralInfo = function(coord_x, coord_y, srs){

	var final_url = '/gvsigonline/catastro/get_rc_info/';
	var popupContent = '';

	$.ajax({
		type: 'POST',
		async: false,
	  	url: final_url,
	  	data: {
	  		'xcen': coord_x,
	  		'ycen': coord_y,
	  		'srs': srs
		},
	  	success	:function(response){
	  		popupContent = response;
	  	}
	});

	var iframe = '<iframe id="iframe-catastro" style="overflow: hidden;" width="800" height="540" frameborder="0"></iframe>';

	$('#float-modal .modal-body').empty();
	$('#float-modal .modal-body').html(iframe);

	var buttons = '';
	buttons += '<button id="float-modal-cancel-coordcalc" type="button" class="btn btn-default" data-dismiss="modal">' + gettext('Accept') + '</button>';

	$('#float-modal .modal-footer').empty();
	$('#float-modal .modal-footer').append(buttons);

	$("#float-modal").modal('show');

	var iframe = document.getElementById('iframe-catastro');
	iframe = iframe.contentWindow || ( iframe.contentDocument.document || iframe.contentDocument);

	iframe.document.open();
	iframe.document.write(popupContent);
	iframe.document.close();
}

CatastroForm.prototype.getRefCatastralPolygon = function(ref_catastral, showPopup = true){
	var self = this;
	var final_url = '/gvsigonline/catastro/get_referencia_catastral_polygon/'
		$.ajax({
			type: 'POST',
			async: false,
		  	url: final_url,
		  	data: {
		  		'ref_catastral': ref_catastral
			},
			dataType: 'json',
		  	success	:function(response){
		  		var features = [];
				for(var i=0; i<response['featureCollection'].length; i++){
					var features_coords = response['featureCollection'][i]['coords'];
					var dimension = response['featureCollection'][i]['dimension'];
					var srs = response['featureCollection'][i]['srs'];

					var features_coords_split = features_coords.split(" ");
					var polyCoords = [];

					var j=0;
					while(j<features_coords_split.length) {
						var feat_coords = [];
						for(var k=0; k<parseInt(dimension); k++){
							feat_coords.push(parseFloat(features_coords_split[j]))
							j++;
						}
						feat_coords = feat_coords.reverse();
						polyCoords.push(ol.proj.transform(feat_coords, srs, 'EPSG:3857'));
					}

					var feature = new ol.Feature({
					    geometry: new ol.geom.Polygon([polyCoords])
					})
					features.push(feature);
				}



				if(self.vectorSource != null){
					self.vectorSource.addFeatures(features)
				}else{
					self.vectorSource = new ol.source.Vector({
				        features: features
				    });
				}

				if(self.vectorLayer == null){
					var styles = [

				        new ol.style.Style({
				          stroke: new ol.style.Stroke({
				            color: 'black',
				            width: 1
				          }),
				          fill: new ol.style.Fill({
				            color: 'rgba(0, 0, 0, 0.1)'
				          })
				        }),
				        new ol.style.Style({
				          image: new ol.style.Circle({
				            radius: 6,
				            fill: new ol.style.Fill({
				              color: 'black'
				            })
				          })

				        })
				      ];


					self.vectorLayer = new ol.layer.Vector({
						source: self.vectorSource,
			            name: 'catastro_layer',
			            style: styles
					});

					self.vectorLayer.setZIndex(99999998);
					viewer.core.map.addLayer(self.vectorLayer);

					$(".catastro-clear-button").each(function(){
						$(this).css("display", "block");
					});

					if (showPopup) {
						viewer.core.map.on("click", function(e) {
							viewer.core.map.forEachFeatureAtPixel(e.pixel, function (feature, layer) {
								if(layer.getProperties()['name'] == 'catastro_layer' && feature){
									var point = ol.proj.transform(e.coordinate, viewer.core.map.getView().getProjection().getCode(), 'EPSG:4326');
									var address_url = '/gvsigonline/catastro/get_rc_by_coords/';
									$.ajax({
										type: 'POST',
										async: false,
										url: address_url,
										data: {
											'xcen': point[0],
											'ycen': point[1],
											'srs': 'EPSG:4326'
										},
										success: function(data){
											var coordinate = ol.proj.transform([parseFloat(data['xcen']), parseFloat(data['ycen'])], data['srs'], 'EPSG:3857');
											var popup = new ol.Overlay.Popup();
											viewer.core.map.addOverlay(popup);
											var popupContent = '<p>'+data['address']+'</p><p>' + gettext("RC") + ':&nbsp;<span style="font-weight:bold">' + data['rc'] + '</span></p>';
											popup.show(coordinate, '<div id="popup-show-more-info" class="popup-wrapper">' + popupContent + '</div>');

											viewer.core.map.getView().setCenter(coordinate);
											viewer.core.map.getView().setZoom(18);
											self.getRefCatastralPolygon(data['rc']);

											$("#popup-show-more-info").click(function(){
												self.getRefCatastralInfo(parseFloat(data['xcen']), parseFloat(data['ycen']), data['srs'])
											})
										}
									});
								}
							});
						});
					} // showPopup
				}


			},
		  	error: function(){
		  		console.log("Can't get RC")
		  	}
		});


}


CatastroForm.prototype.onAddressKeyPress = function(){
	var self = this;
	var component = $("#provincia-input").select2('data');
	var province = "";
	if(Array.isArray(component)){
		province = component[0].text;
	}else{
		province = component.text;
	}
	var component2 = $("#municipio-input").select2('data');
	var municipio = "";
	if(Array.isArray(component2)){
		municipio = component2[0].text;
	}else{
		municipio = component2.text;
	}

	var address_url = '/gvsigonline/catastro/get_vias/';

	$.ajax({
		type: 'POST',
		async: false,
	  	url: address_url,
	  	data: {
	  		'provincia': province,
	  		'municipio': municipio
		},
		success: function(data){
	  		var options = "<option value=\"---\">---</option>";;

	  		$(data).find('dir').each(function() {
                var key = $(this).find("cv").text();
                var type = $(this).find("tv").text();
                var value = $(this).find("nv").text();
                options += "<option data-name=\""+value+"\" data-type=\""+type+"\" value=\""+value+"\">"+value+"</option>";
            });
	  		$("#road-name-input").empty().html(options)

	  		$("#road-name-input.js-example-basic-single").select2();

	  		$("#road-name-input").unbind("change").change(function(){
	  			var component = $("#road-name-input").select2('data');
	  			var value = "";
	  			if(Array.isArray(component)){
	  				value = component[0].text;
	  			}else{
	  				value = component.text;
	  			};
	  			var type = "";

	  			var option = $("#road-name-input option[data-name=\""+value+"\"]")
	  			if(option.length > 0){
	  				type = option.first().attr("data-type")
	  			}

	  			$("#road-type-input").val(type);
	  		})
		},
	  	error: function(){
	  		console.log("Can't get addresses")
	  	}
	});
}



CatastroForm.prototype.onMunicipallyKeyPress = function(id){
	var self = this;
	var component = $("#"+id).select2('data');
	var province = "";
	if(Array.isArray(component)){
		province = component[0].text;
	}else{
		province = component.text;
	}
    var suffix = id.substring("provincia-".length);

	var municipio_url = '/gvsigonline/catastro/get_municipios/';

	$.ajax({
		type: 'POST',
		async: false,
	  	url: municipio_url,
	  	data: {
	  		'provincia': province
		},
	  	success	:function(data){
	  		var options = "<option value=\"---\">---</option>";

	  		$(data).find('muni').each(function() {
                var value = $(this).find("nm").text();
                options += "<option value=\""+value+"\">"+value+"</option>";
            });
	  		$("#municipio-" + suffix).empty().html(options)

	  		$("#municipio-" + suffix+".js-example-basic-single").select2();

	  		$("#municipio-input").unbind("change").change(function(){
	  			self.onAddressKeyPress();
	  		})
		},
	  	error: function(){
	  		console.log("Can't get municipios")
	  	}
	});

}
