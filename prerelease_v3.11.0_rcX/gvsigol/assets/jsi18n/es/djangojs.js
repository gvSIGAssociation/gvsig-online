

(function(globals) {

  var django = globals.django || (globals.django = {});

  
  django.pluralidx = function(n) {
    var v=(n != 1);
    if (typeof(v) == 'boolean') {
      return v ? 1 : 0;
    } else {
      return v;
    }
  };
  

  /* gettext library */

  django.catalog = django.catalog || {};
  
  var newcatalog = {
    "%(sel)s of %(cnt)s selected": [
      "%(sel)s de %(cnt)s seleccionado", 
      "%(sel)s de  %(cnt)s seleccionados"
    ], 
    "3D View": "Vista 3D", 
    "6 a.m.": "6 a.m.", 
    "6 p.m.": "6 p.m.", 
    "A visible layer with temporal properties is needed": "Una capa visible con propiedades temporales es necesaria", 
    "Abort": "Abortar", 
    "Abstract": "Resumen", 
    "Accept": "Aceptar", 
    "Add expression": "A\\u00f1adir expresi\\u00f3n", 
    "Add line": "A\\u00f1adir linea", 
    "Add point": "A\\u00f1adr punto", 
    "Add point to center": "A\\u00f1adir punto al centro", 
    "Add polygon": "A\\u00f1adir pol\\u00edgono", 
    "Address": "Direcci\\u00f3n", 
    "Advanced filter": "Filtro avanzado", 
    "Append color map entry": "A\\u00f1adir entrada de color", 
    "Append symbolizer": "A\\u00f1adir simbolizador", 
    "Append textsymbolizer": "A\\u00f1adir simbolizador de texto", 
    "Apply filter": "Aplicar filtro", 
    "April": "Abril", 
    "Attribute details": "Detalles del atributo", 
    "Attribute table": "Tabla de atributos", 
    "August": "Agosto", 
    "AutoScale": "Escala Autom\\u00e1tica", 
    "Available %s": "%s Disponibles", 
    "Base layers": "Capas base", 
    "Bing aerial": "Bing a\\u00e9rea", 
    "Bing aerial with labels": "Bing a\\u00e9rea con etiquetas", 
    "Bing roads": "Bing carreteras", 
    "Blank": "Blanco", 
    "Bold": "Negrita", 
    "BoundingBox": "BoundingBox", 
    "Cancel": "Cancelar", 
    "Choose": "Elegir", 
    "Choose a Date": "Elija una fecha", 
    "Choose a Time": "Elija una hora", 
    "Choose a time": "Elija una hora", 
    "Choose all": "Selecciona todos", 
    "Chosen %s": "%s elegidos", 
    "Circle": "C\\u00edrculo", 
    "City": "Ciudad", 
    "Clean map": "Limpiar mapa", 
    "Clear filter": "Limpiar filtro", 
    "Clear selection": "Limpiar selecci\\u00f3n", 
    "Click to choose all %s at once.": "Haga clic para seleccionar todos los %s de una vez", 
    "Click to continue measuring": "Click para continuar midiendo", 
    "Click to remove all chosen %s at once.": "Haz clic para eliminar todos los %s elegidos", 
    "Click to start measuring": "Click para empezar a medir", 
    "Color": "Color", 
    "Color map entry": "Entrada de color", 
    "Contact person": "Persona de contacto", 
    "Contains": "Contiene", 
    "Continue": "Continuar", 
    "Coordinate Reference System": "Sistema de referencia de coordenadas", 
    "Coordinates": "Coordenadas", 
    "Country": "Pa\\u00eds", 
    "Create new layer": "Crear capa vac\\u00eda", 
    "Cross": "Cruz", 
    "Cursive": "Cursiva", 
    "December": "Diciembre", 
    "Default CRS": "CRS por defecto", 
    "Default group": "Grupo por defecto", 
    "Define custom scale denominators?": "Visible por escala", 
    "Delete": "Borrar", 
    "Details": "Detalles", 
    "Done": "Hecho", 
    "Download CSV": "Descargar CSV", 
    "Download GML": "Descargar GML", 
    "Download links": "Links de descarga", 
    "Download shapefile": "Descargar shapefile", 
    "Downloads": "Descargas", 
    "Drag files here": "Arrastrar archivos aqu\\u00ed", 
    "Edit feature": "Editar feature", 
    "Edit field": "Editar campo", 
    "Edit filter": "Editar filtro", 
    "Edit layer": "Editar capa", 
    "Edit node": "Editar nodo", 
    "Edit rule": "Editar regla", 
    "Email": "Correo electr\\u00f3nico", 
    "Enable temporary features": "Activar funciones temporales", 
    "Enumeration cannot contain point-colon": "los valores no pueden contener valores (;)", 
    "Error in GetCapabilities": "Error en GetCapabilities", 
    "Error loading print plugin": "Error cargando plugin de impresi\\u00f3n", 
    "Error starting edition": "Error comenzando edici\\u00f3n", 
    "Error trying to connect": "Error intentando conectar", 
    "Expressions": "Expresiones", 
    "Failed to remove layer lock": "Fallo al eliminar el bloqueo de la capa", 
    "Failed to save the new record. Please check values": "Fallo al guardar el nuevo registro. Comprobar valores", 
    "False": "Falso", 
    "Feature info": "Feature info", 
    "Feature properties": "Propiedades de la feature", 
    "Feature resources": "Recursos de la feature", 
    "February": "Febrero", 
    "Field name": "Nombre del campo", 
    "Fill": "Relleno", 
    "Fill color": "Color del relleno", 
    "Fill opacity": "Opacidad del relleno", 
    "Filter": "Filtro", 
    "Filter preview": "Previsualizar filtro", 
    "Filtering": "Filtrando", 
    "Find": "Encontrar", 
    "First": "Primero", 
    "Font": "Fuente", 
    "Font color": "Color de fuente", 
    "Font family": "Fam\\u00edlia de fuente", 
    "Font size": "Tama\\u00f1o de fuente", 
    "Font style": "Estilo de fuente", 
    "Font weight": "Grosor de fuente", 
    "Format": "Formato", 
    "From": "Desde", 
    "Function not available": "Herramienta no disponible", 
    "GeographicBoundingBox": "GeographicBoundingBox", 
    "Get current location": "Conseguir posici\\u00f3n actual", 
    "Graphic": "Gr\\u00e1fico", 
    "Habilitar caracter\\u00edsticas temporales": "Active temporal dimension", 
    "Halo": "Halo", 
    "Halo color": "Color de halo", 
    "Halo opacity": "Opacidad de halo", 
    "Halo radius": "Radio de halo", 
    "Has label": "Activar etiquetado", 
    "Hide": "Esconder", 
    "Image Mosaic": "Mosaico de im\\u00e1genes", 
    "Image symbols can only be edited from the library": "Los s\\u00edmbolos de tipo imagen solo pueden ser editados des de la biblioteca de s\\u00edmbolos", 
    "Import from library": "Importar desde lbrer\\u00eda", 
    "Insert item name": "Inserte nombre del item", 
    "Invalid identifier. Unable to get requested geometry": "Identificador inv\\u00e1lido. No se puede obtener la geometr\\u00eda solicitada", 
    "Invalid name: Identifiers must begin with a letter or an underscore (). Subsequent characters can be letters, underscores or numbers": "Nombre no v\\u00e1lido: Los identificadores deben empezar con una letra o gui\\u00f3n bajo (). Los siguientes caracteres pueden ser letras, gui\\u00f3n bajo o n\\u00fameros", 
    "Inverse geocoding": "Geocodificador inverso", 
    "Is between": "Est\\u00e1 entre", 
    "Is equal to": "Es igual a", 
    "Is greater than": "Es mayor que", 
    "Is greater than or equal to": "Es mayor que o igual", 
    "Is less than": "Es menor que", 
    "Is less than or equal to": "Es menor que o igual", 
    "Is master?": "Es maestro?", 
    "Is not equal": "No es igual", 
    "Is null": "Es nul", 
    "January": "Enero", 
    "July": "Julio", 
    "June": "Junio", 
    "Label": "Etiqueta", 
    "Label field": "Campo de etiqueta", 
    "Label filter expressions": "Etiqueta filtrada por expresi\\u00f3n", 
    "Last": "\\u00daltimo", 
    "Latitude": "Latitud", 
    "Layer metadata": "Metadatos de la capa", 
    "Layers": "Capas", 
    "Legal warning": "Aviso legal", 
    "Loading": "Cargando", 
    "Loading components. Please wait": "Cargando componentes. Por favor espere", 
    "Longitude": "Longitud", 
    "Map title": "T\\u00edtulo del mapa", 
    "March": "Marzo", 
    "MaxScaleDenominator": "MaxScaleDenominator", 
    "Maximum interval": "Intervalo m\\u00e1ximo", 
    "Maximum scale denominator": "Denominador m\\u00e1ximo de la escala", 
    "May": "Mayo", 
    "Measure area": "Medir \\u00e1rea", 
    "Measure length": "Medir distancia", 
    "Metadata": "Metadatos", 
    "Midnight": "Medianoche", 
    "MinScaleDenominator": "MinScaleDenominator", 
    "Minimum interval": "Intervalo m\\u00ednimo", 
    "Minimum scale denominator": "Denominador m\\u00ednimo de la escala", 
    "More element info": "M\\u00e1s informaci\\u00f3n del elemento", 
    "More info": "M\\u00e1s informaci\\u00f3n", 
    "Multimedia resources": "Recursos multimedia", 
    "Name": "Nombre", 
    "New feature": "Nueva feature", 
    "Next": "Siguiente", 
    "No layer": "Sin capa", 
    "No layers available": "No hay capas disponibles", 
    "No limit": "Sin l\\u00edmite", 
    "No records available": "No hay registros disponibles", 
    "None": "Nada", 
    "Noon": "Mediod\\u00eda", 
    "Normal": "Normal", 
    "Note: You are %s hour ahead of server time.": [
      "Nota: Usted esta a %s horas por delante de la hora del servidor.", 
      "Nota: Usted va %s horas por delante de la hora del servidor."
    ], 
    "Note: You are %s hour behind server time.": [
      "Nota: Usted esta a %s hora de retraso de tiempo de servidor.", 
      "Nota: Usted va %s horas por detr\\u00e1s de la hora del servidor."
    ], 
    "November": "Noviembre", 
    "Now": "Ahora", 
    "Oblique": "Oblicua", 
    "October": "Octubre", 
    "Only PRESENT is available in Instant mode. You need to define a RANGE to use relative intervals": "Solo PRESENTE est\\u00e1 disponible en modo instant\\u00e1neo. Necesitas definir un RANGO para usar intervalos relativos", 
    "Only relative intervals can be defined if the other field is PRESENT or a concrete date.": "Solo se pueden definir intervalos relativos si el otro campo es PRESENTE o una fecha concreta.", 
    "Opacity": "Opacidad", 
    "OpenStreetMap": "OpenStreetMap", 
    "Organization": "Organizaci\\u00f3n", 
    "Percentage": "Porcentaje", 
    "Point information": "Informaci\\u00f3n en el punto", 
    "Preview": "Previsualizar", 
    "Previous": "Previo", 
    "Print": "Imprimir", 
    "Print map": "Imprimir mapa", 
    "Print params": "Parametros de impresi\\u00f3n", 
    "Print selection": "Imprimir selecci\\u00f3n", 
    "Printing date": "Fecha de impresi\\u00f3n", 
    "Printing message": "Mensaje de impresi\\u00f3n", 
    "Processing request": "Procesando petici\\u00f3n", 
    "Project zoom": "Zoom del proyecto", 
    "Publish layer": "Publicar capa", 
    "Quantity": "Cantidad", 
    "Queryable": "Consultable", 
    "Range": "Rango", 
    "Remove": "Eliminar", 
    "Remove all": "Eliminar todos", 
    "Remove feature": "Eliminar feature", 
    "Requests": "Petici\\u00f3n", 
    "Resolution": "Resoluci\\u00f3n", 
    "Rotation": "Rotaci\\u00f3n", 
    "Rule": "Regla", 
    "Rule name": "Nombre de la regla", 
    "Rule title": "T\\u00edtulo de la regla", 
    "Save": "Guardar", 
    "Save field": "Guardar campo", 
    "Save filter": "Guardar filtro", 
    "Save node": "Guardar nodo", 
    "Scale": "Escala", 
    "Search": "Buscar", 
    "Search by coordinate": "Buscar coordenadas", 
    "Select": "Seleccionar", 
    "Select all": "Seleccionar todo", 
    "Select enumeration": "Seleccionar enumeraci\\u00f3n", 
    "Select field": "Seleccionar camp\u00f3", 
    "Select form": "Seleccionar formulario", 
    "Select multiple enumeration": "Seleccionar enumeraci\\u00f3n multiple", 
    "Select operation": "Seleccionar operaci\\u00f3n", 
    "Select pattern": "Seleccionar patr\\u00f3n", 
    "Select print template": "Seleccionar plantilla de impresi\\u00f3n", 
    "Select projection": "Seleccionar proyecci\\u00f3n", 
    "Select shape": "Seleccionar forma", 
    "Select template": "Seleccionar plantilla", 
    "Select type": "Seleccionar tipo", 
    "Select value": "Seleccionar valor", 
    "Selected symbol is not compatible with the layer": "El s\\u00edmbolo seleccionado no es compatible con la capa", 
    "September": "Septiembre", 
    "Share view": "Compartir vista", 
    "Show": "Mostrar", 
    "Show in geonetwork": "Mostrar en geonetwork", 
    "Show resources": "Mostrar recursos", 
    "Showing": "Mostrando", 
    "Showing from": "Mostrando desde", 
    "Single": "\\u00danico", 
    "Single feature": "Feature simple", 
    "Size": "Tama\\u00f1o", 
    "Sort ascending": "Orden ascendente", 
    "Sort descending": "Orden descendente", 
    "Square": "Cuadrado", 
    "Star": "Estrella", 
    "Status": "Estado", 
    "Step": "Paso", 
    "Stop edition": "Terminar edici\\u00f3n", 
    "Stroke": "Linea", 
    "Stroke color": "Color del linea", 
    "Stroke opacity": "Opacidad de linea", 
    "Stroke width": "Anchura de linea", 
    "Success": "\\u00c9xito", 
    "Summary": "Resumen", 
    "Supported CRS": "CRS soportados", 
    "Temporary layers": "Capas temporales", 
    "Temporary range": "Rango temporal", 
    "The layer you are trying to edit is locked": "La capa que intanta editar est\\u00e1 bloqueada", 
    "The number of intervals must be greater than 0": "El n\\u00famero de intervalos debe ser mayor que 0", 
    "There is no active geocoder": "No hay ning\\u00fan geocoder activo", 
    "This functionality is only available on Mozilla Firefox": "Esta funcionalidad est\\u00e1 s\\u00f3lo disponible en Mozilla Firefox", 
    "This is the list of available %s. You may choose some by selecting them in the box below and then clicking the \"Choose\" arrow between the two boxes.": "Esta es la lista de %s disponibles. Puede elegir algunos seleccion\\u00e1ndolos en la caja inferior y luego haciendo clic en la flecha \"Elegir\" que hay entre las dos cajas.", 
    "This is the list of chosen %s. You may remove some by selecting them in the box below and then clicking the \"Remove\" arrow between the two boxes.": "Esta es la lista de los %s elegidos. Puede elmininar algunos seleccion\\u00e1ndolos en la caja inferior y luego haciendo click en la flecha \"Eliminar\" que hay entre las dos cajas.", 
    "Title": "T\\u00edtulo", 
    "To": "Hasta", 
    "Today": "Hoy", 
    "Tomorrow": "Ma\\u00f1ana", 
    "Triangle": "Tri\\u00e1ngulo", 
    "True": "Verdadero", 
    "Two or more color definitions are required": "En caso de necesitar alguna, se requieren al menos dos definiciones en la tabla de color", 
    "Type into this box to filter down the list of available %s.": "Escriba en este cuadro para filtrar la lista de %s disponibles", 
    "URL": "URL", 
    "Value": "Valor", 
    "Value1": "Valor1", 
    "Value2": "Valor2", 
    "Version": "Versi\\u00f3n", 
    "View resources": "Ver recursos", 
    "Warning": "Aviso", 
    "Yesterday": "Ayer", 
    "You are editing the layer": "Usted est\\u00e1 editando la capa", 
    "You can not update a data store type GeoTIFF. Delete it and create it again": "No puede actualizar un almac\\u00e9n de tipo GeoTIFF. Borrelo y creelo de nuevo.", 
    "You have selected an action, and you haven't made any changes on individual fields. You're probably looking for the Go button rather than the Save button.": "Ha seleccionado una acci\\u00f3n y no hs hecho ning\\u00fan cambio en campos individuales. Probablemente est\\u00e9 buscando el bot\\u00f3n Ejecutar en lugar del bot\\u00f3n Guardar.", 
    "You have selected an action, but you haven't saved your changes to individual fields yet. Please click OK to save. You'll need to re-run the action.": "Ha seleccionado una acci\\u00f3n, pero no ha guardado los cambios en los campos individuales todav\\u00eda. Pulse OK para guardar. Tendr\\u00e1 que volver a ejecutar la acci\\u00f3n.", 
    "You have unsaved changes on individual editable fields. If you run an action, your unsaved changes will be lost.": "Tiene cambios sin guardar en campos editables individuales. Si ejecuta una acci\\u00f3n, los cambios no guardados se perder\\u00e1n.", 
    "You must select a field": "Debe seleccionar un campo", 
    "You must select a file": "Debe seleccionar un archivo", 
    "You must select a image": "Selecciona una imagen", 
    "You must select a template": "Ha de seleccionar una plantilla", 
    "You must select at least one row": "Debe seleccionar al menos una fila", 
    "Zoom to layer": "Zoom a la capa", 
    "Zoom to selection": "Zoom a la selecci\\u00f3n", 
    "active": "activo", 
    "apply relative date": "Aplicar fecha relativa", 
    "can't be empty": "No puede estar vac\\u00edo", 
    "can't be null": "No puede ser nulo", 
    "contains": "Contiene", 
    "day(s)": "d\\u00eda(s)", 
    "false": "Falso", 
    "features": "features", 
    "hour(s)": "hora(s)", 
    "inactive": "inactivo", 
    "inverse geocoding": "Geocodificador inverso", 
    "legalwarning": "Todos los contenidos cartogr\\u00e1ficos de este web y de los servicios que proporciona son propiedad de esta instituci\\u00f3n.La instituci\\u00f3n no es responsable de la informaci\\u00f3n que se puede obtener a trav\\u00e9s de enlaces a sistemas externos.", 
    "minute(s)": "minuto(s)", 
    "month(s)": "mes(es)", 
    "null_value": "Sin valor", 
    "of": "de", 
    "one letter Friday\\u0004F": "V", 
    "one letter Monday\\u0004M": "L", 
    "one letter Saturday\\u0004S": "S", 
    "one letter Sunday\\u0004S": "D", 
    "one letter Thursday\\u0004T": "J", 
    "one letter Tuesday\\u0004T": "M", 
    "one letter Wednesday\\u0004W": "M", 
    "registers": "Registros", 
    "remove": "eliminar", 
    "second(s)": "segundo(s)", 
    "temporary_endfield": "campo_temporal_final", 
    "temporary_field": "campo_temporal", 
    "to": "a", 
    "true": "Verdadero", 
    "year(s)": "a\\u00f1o(s)"
  };
  for (var key in newcatalog) {
    django.catalog[key] = newcatalog[key];
  }
  

  if (!django.jsi18n_initialized) {
    django.gettext = function(msgid) {
      var value = django.catalog[msgid];
      if (typeof(value) == 'undefined') {
        return msgid;
      } else {
        return (typeof(value) == 'string') ? value : value[0];
      }
    };

    django.ngettext = function(singular, plural, count) {
      var value = django.catalog[singular];
      if (typeof(value) == 'undefined') {
        return (count == 1) ? singular : plural;
      } else {
        return value[django.pluralidx(count)];
      }
    };

    django.gettext_noop = function(msgid) { return msgid; };

    django.pgettext = function(context, msgid) {
      var value = django.gettext(context + '\x04' + msgid);
      if (value.indexOf('\x04') != -1) {
        value = msgid;
      }
      return value;
    };

    django.npgettext = function(context, singular, plural, count) {
      var value = django.ngettext(context + '\x04' + singular, context + '\x04' + plural, count);
      if (value.indexOf('\x04') != -1) {
        value = django.ngettext(singular, plural, count);
      }
      return value;
    };

    django.interpolate = function(fmt, obj, named) {
      if (named) {
        return fmt.replace(/%\(\w+\)s/g, function(match){return String(obj[match.slice(2,-2)])});
      } else {
        return fmt.replace(/%s/g, function(match){return String(obj.shift())});
      }
    };


    /* formatting library */

    django.formats = {
    "DATETIME_FORMAT": "j \\d\\e F \\d\\e Y \\a \\l\\a\\s H:i", 
    "DATETIME_INPUT_FORMATS": [
      "%d/%m/%Y %H:%M:%S", 
      "%d/%m/%Y %H:%M:%S.%f", 
      "%d/%m/%Y %H:%M", 
      "%d/%m/%y %H:%M:%S", 
      "%d/%m/%y %H:%M:%S.%f", 
      "%d/%m/%y %H:%M", 
      "%Y-%m-%d %H:%M:%S", 
      "%Y-%m-%d %H:%M:%S.%f", 
      "%Y-%m-%d %H:%M", 
      "%Y-%m-%d"
    ], 
    "DATE_FORMAT": "j \\d\\e F \\d\\e Y", 
    "DATE_INPUT_FORMATS": [
      "%d/%m/%Y", 
      "%d/%m/%y", 
      "%Y-%m-%d"
    ], 
    "DECIMAL_SEPARATOR": ",", 
    "FIRST_DAY_OF_WEEK": "1", 
    "MONTH_DAY_FORMAT": "j \\d\\e F", 
    "NUMBER_GROUPING": "3", 
    "SHORT_DATETIME_FORMAT": "d/m/Y H:i", 
    "SHORT_DATE_FORMAT": "d/m/Y", 
    "THOUSAND_SEPARATOR": ".", 
    "TIME_FORMAT": "H:i", 
    "TIME_INPUT_FORMATS": [
      "%H:%M:%S", 
      "%H:%M:%S.%f", 
      "%H:%M"
    ], 
    "YEAR_MONTH_FORMAT": "F \\d\\e Y"
  };

    django.get_format = function(format_type) {
      var value = django.formats[format_type];
      if (typeof(value) == 'undefined') {
        return format_type;
      } else {
        return value;
      }
    };

    /* add to global namespace */
    globals.pluralidx = django.pluralidx;
    globals.gettext = django.gettext;
    globals.ngettext = django.ngettext;
    globals.gettext_noop = django.gettext_noop;
    globals.pgettext = django.pgettext;
    globals.npgettext = django.npgettext;
    globals.interpolate = django.interpolate;
    globals.get_format = django.get_format;

    django.jsi18n_initialized = true;
  }

}(this));

