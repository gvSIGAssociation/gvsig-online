	
function validateRegex(pattern) {
	return /^[a-zA-Z_@][a-zA-Z0-9_@]*$/.test(pattern);
};

function getFieldTypes(enableEnums, enableForms) {
	var fieldTypes = [{
		key: 'boolean',
		value: 'Boolean'
	},{
		key: 'character_varying',
		value: 'Text'
	},{
		key: 'integer',
		value: 'Integer'
	},{
		key: 'double',
		value: 'Double'
	},{
		key: 'date',
		value: 'Date'
	},{
		key: 'time',
		value: 'Time'
	},{
		key: 'timestamp',
		value: 'Timestamp'
	},{
		key: 'cd_json',
		value: 'Complex type: JSON'
	}];
	if (enableEnums) {
		fieldTypes.push({
			key: 'enumeration',
			value: 'Enumeration'
		});
		
		fieldTypes.push({
			key: 'multiple_enumeration',
			value: 'Multiple enumeration '
		});
	}
	if (enableForms) {
		fieldTypes.push({
			key: 'form',
			value: 'Form'
		});
	}
	return fieldTypes;
}

function getFieldNameDiv(field_name, field_type, mode, id, defaultValue, enumerations, forms) {
	var ui = '';
	ui += '<div id="div-name" class="row">';
	ui +=    '<div class="col-md-12 form-group">';
	if ( field_type == 'enumeration') {
		ui += 	'<label>' + gettext('Select enumeration') + '</label>';
		ui += 	'<select id="field-default-value-'+id+'" class="form-control">';
		var e;
		for (var i=0; i<enumerations.length; i++) {
			e = enumerations[i]; 
			if ( e.id == defaultValue) {
				ui += '<option selected value="' + e.id + '">' + e.title + '</option>';
			} else {
				ui += '<option  value="' + e.id + '">' + e.title + '</option>';
			}
		}
		ui += 	'</select>';
		
	} else if ( field_type == 'multiple_enumeration') {
		ui += 	'<label>' + gettext('Select multiple enumeration') + '</label>';
		ui += 	'<select id="field-default-value-'+id+'" class="form-control">';
		var e;
		for (var i=0; i<enumerations.length; i++) {
			e = enumerations[i];
			if ( e.id == defaultValue) {
				ui += '<option selected value="' + e.id + '">' + e.title + '</option>';
			} else {
				ui += '<option value="' + e.id + '">' + e.title + '</option>';
			}
		}
		ui += 	'</select>';
	}else if ( field_type == 'form') {
		ui += 	'<label>' + gettext('Select form') + '</label>';
		ui += 	'<select id="field-default-value-'+id+'" class="form-control">';
				var f;
				for (var i=0; i<forms.length; i++) {
					f = forms[i];
					if ( f.name == defaultValue) {
						ui += '<option selected value="' + f.name + '">' + f.title + '</option>';
					} else {
						ui += '<option value="' + f.name + '">' + f.title + '</option>';
					}
				}
		ui += 	'</select>';
	}
	ui +=    '</div>';
	ui +=    '<div class="col-md-12 form-group">';
	ui +=      '<label>' + gettext('Field name') + '</label>';
	if (mode == 'create') {
		ui += 		'<input type="text" id="field-name-'+id+'" name="field-name-'+id+'" class="form-control">';
	} else if (mode == 'update') {
		ui += 		'<input type="text" id="field-name-'+id+'" name="field-name-'+id+'" class="form-control" value="' + field_name + '">';
	}
	ui +=    '</div>';
	ui += '</div>';
	return ui;
}

function createModalContent(fid, mode, title, config){
	var enumerations = config.enumerations;
	var forms = config.forms;
	var enableEnums = config.enableEnums;
	var enableForms = config.enableForms;
	var fieldTypes = getFieldTypes(enableEnums, enableForms);
	var modalSelector = config.modalSelector || '#modal-new-field'; 
	$(modalSelector).find('.modal-body').empty();
	$(modalSelector).find('.modal-title').text(title);
	
	var id = Math.random().toString(36).slice(2);
	var ui = '';
	
	var field = null;
	if (mode == 'update') {
		field = getFieldById(fid);
	}
	
	ui += '<div id="field-errors" class="row">';
	ui += '</div>';
	
	ui += '<div class="row">';
	ui += 	'<div class="col-md-12 form-group">';
	ui += 		'<label>' + gettext('Select type') + '</label>';
	ui += 		'<select id="field-db-type" class="form-control">';
	if (mode == 'create') {
		ui += 		'<option disabled selected value> -- ' + gettext('Select type') + ' -- </option>';
		for (var i=0; i<fieldTypes.length; i++) {
			ui += 	'<option value="' + fieldTypes[i].key + '">' + fieldTypes[i].value + '</option>';
		}
	} else if (mode == 'update') {
		for (var i=0; i<fieldTypes.length; i++) {
			if (fieldTypes[i].key == field.type) {
				ui += 	'<option selected value="' + fieldTypes[i].key + '">' + fieldTypes[i].value + '</option>';
			} else {
				ui += 	'<option value="' + fieldTypes[i].key + '">' + fieldTypes[i].value + '</option>';	
			}
		}
	}
	ui += 		'</select>';
	ui += 	'</div>';
	ui += '</div>';	
	
	
	if (mode == 'create') {
		ui += '<div id="div-name" class="row">';
		ui += '</div>';
		
	} else if (mode == 'update') {
		ui += getFieldNameDiv(field.name, field.type, mode, id, field.enumkey, enumerations, forms);
	}
	
	$(modalSelector).find('.modal-body').append(ui);
	
	var buttons = '';
	buttons += '<button id="add-field-cancel" type="button" class="btn btn-default" data-dismiss="modal">' + gettext('Cancel') + '</button>';
	if (mode == 'create') {
		buttons += '<button id="add-field-accept" type="button" class="btn btn-default">' + gettext('Save field') + '</button>';
		
	} else if (mode == 'update') {
		buttons += '<button id="update-field-accept" data-fieldid="'+field.id+'" type="button" class="btn btn-default">' + gettext('Edit field') + '</button>';
	}
	
	
	$(modalSelector).find('.modal-footer').empty();
	$(modalSelector).find('.modal-footer').append(buttons);
	
	$('#field-db-type').on('change', function(e) {
		var dvName = getFieldNameDiv('', $('#field-db-type').val(), 'create', id, null, enumerations, forms);
		$('#div-name').replaceWith(dvName);
	});
	
	$('#add-field-accept').on('click', function () {
		var name = $('#field-name-'+id).val();
		var type = $('#field-db-type').val();
		var enumkey = $('#field-default-value-'+id).val();
		
		if (validateRegex(name)) {
			var field = {
				id: id,
				name: name,
				type: type,
				enumkey: enumkey
			};
			addField(field);
			
			$(modalSelector).modal('hide');
			
		} else {
			var error = '<p class="text-muted" style="color: #ff0000; padding: 10px;">* ' + gettext('Invalid name: Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers') + '.</p>';
			$('#field-errors').empty();
			$('#field-errors').append(error);
		}
	});
	
	$('#update-field-accept').on('click', function () {
		var name = $('#field-name-'+id).val();
		var type = $('#field-db-type').val();
		var enumkey = $('#field-default-value-'+id).val();
		
		if (validateRegex(name)) {
			var field = {
				id: this.dataset.fieldid,
				name: name,
				type: type,
				enumkey: enumkey
			};
			
			updateField(field);
			
			$(modalSelector).modal('hide');
			
		} else {
			var error = '<p class="text-muted" style="color: #ff0000; padding: 10px;">* ' + gettext('Invalid name: Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers') + '.</p>';
			$('#field-errors').empty();
			$('#field-errors').append(error);
		}
		
	});
	
	$(modalSelector).modal('show');
};

