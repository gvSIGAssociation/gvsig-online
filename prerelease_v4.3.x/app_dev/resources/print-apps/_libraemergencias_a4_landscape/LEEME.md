# Notas sobre el diseño de este informe

Este documento resume las decisiones de diseño clave y las técnicas utilizadas en este proyecto de JasperReports para que sirvan como referencia futura.

Hemos dejado en el requestData-Default.json un json de ejemplo obtenido de una captura real de lo que envía la aplicación al servicio de impresión.

## Sobre el subreport con la tabla

Para añadir un subreport con la tabla se ha modificado el config.yaml:

* se ha añadido un processor prepareTable con un atributo "dynamic" a false 
* los atributos reportTemplate y reportKey en el createDataSource
* y dentro de los processors principales el tableData

```
    - !createDataSource
      reportTemplate: subreport_estado_carreteras.jrxml
      reportKey: reportTemplate
      processors:
        - !prepareTable
          dynamic: false
    tableData: jrDataSource
```

En el report principal, se añade el subreport pasándole "subreport_estado_carreteras.jasper" como "Expression" y $F{tableDataSource} como "Data Source Expression". Este subreport al añadirlo al report principal debe tener una altura de 0.

## Sobre informe con traducciones

Se ha añadido un parámetro al report principal `Locale` con valor por defecto "es" que podrá venir con valores como "es", "va", "en", etc. dependiendo del idioma en el que sacar el informe. De momento hemos tenido en cuenta solo "es" y "va".

Se ha añadido un parámetro `CustomProperties` al report principal con la siguiente expresión:

```
groovy.util.Eval.xy($P{JASPER_REPORTS_CONTEXT}, $P{Locale}, "import org.apache.commons.lang3.StringUtils; if (StringUtils.isBlank(y)){ y = \"es\"; }; def is = x.getExtensions(net.sf.jasperreports.repo.RepositoryService.class).get(0).getResource(\"variables-\"+y+\".properties\",net.sf.jasperreports.repo.InputStreamResource.class).getInputStream(); def r = new java.io.InputStreamReader(is, \"UTF-8\"); def props=new java.util.Properties(); props.load(r); r.close(); is.close(); props")
```
Esta expresión ejecuta un script de groovy mediante `groovy.util.Eval.xy(...)` pasándole los parámetros:

* x=`$P{JASPER_REPORTS_CONTEXT}`
* y=`$P{Locale}`

Hemos extraído el script de groovy aparte y formateado aquí para que se pueda entender mejor pero en el parámetro del report hay que dejarlo como está arriba.

```
import org.apache.commons.lang3.StringUtils; 
if (StringUtils.isBlank(y)){
    y = "es"; 
}; 
def repoService = x.getExtensions(net.sf.jasperreports.repo.RepositoryService.class).get(0);
def resource = reposService.getResource(
        "variables-"+y+".properties",
        net.sf.jasperreports.repo.InputStreamResource.class
    );
def is = resource.getInputStream(); 
def r = new java.io.InputStreamReader(is, "UTF-8"); 
def props=new java.util.Properties(); 
props.load(r); 
r.close(); 
is.close(); 
props
```

"Mapfish Print" registra en las extensiones del contexto del informe (`$P{JASPER_REPORTS_CONTEXT}`) la clase `MapfishPrintRepositoryService` que se encarga de cargar recursos que están junto al informe. Obtenida la instancia de esa clase, se le pide el recurso que queremos (ejemplo: "variables-es.properties") y se obtiene el InputStream asociado al recurso.

Si se quiere reconstruir el script para asignarlo al parámetro `CustomProperties` hay que tener en cuenta que la expresión:

* no puede tener saltos de líneas
* las comillas deben estar escapadas
* todas las líneas deben estar separadas por `;`

Este parámetro lo hemos hecho heredar al subreport, pinchando en el subreport, entrando a "Edit Parameters" y añadiendo un item al mapa de parámetros con CustomProperties como "Parameter Name" y  $P{CustomProperties} como "Parameter Expression".

Todo esto nos permite tener un archivo de traducciones por idioma que hemos llamado:

* variables-es.properties con (por ejemplo):
```
organismo=Dirección General de Infraestructuras Viarias
```
* variables-va.properties con (por ejemplo):
```
organismo=Direcció General d'infraestructures viàries
```

y en los sitios donde se necesite una traducción se debe usar una expresión como esta:
```
$P{CustomProperties}.getProperty("organismo")
```

Hemos quitado los parámetros colEstado, colDescripcion, colEquivalencia y piePagina tanto del report como del yaml usando el mecanismo explicado arriba. 

## Sobre el marcado con fondo azul de las líneas

Para marcar con fondo azul las líneas que han sido recientemente modificadas, hemos añadido un parámetro nuevo "recentlyModifiedMark", solo en el subreport no en el yaml ni en el json, que permite decidir qué caracter se va a utilizar para ello. Como valor por defecto hemos puesto "►".
Este caracter se debe poner al inicio del campo fecha.

Se han duplicado todos los TextField del subreport, en la copia hemos puesto el fondo azul y desmarcado el check "Transparent", dejando en el original el fondo blanco.
Con esto, en el TextField donde va la fecha en azul hemos puesto la siguiente expresión:

```
SUBSTITUTE($F{Fecha},$P{recentlyModifiedMark},"",1)
```
dejando la expresión normal para el TextField que va con fondo blanco.

```
$F{Fecha}
```

En todos los TextField con fondo azul hemos puesto en la "Print When Expression" la expresión:

```
$F{Fecha}.startsWith( $P{recentlyModifiedMark} )
```
mientras que en los originales con fondo blanco hemos puesto la expresión:

```
NOT($F{Fecha}.startsWith( $P{recentlyModifiedMark}))
```

## Previsualización del subinforme de la tabla en el JasperSoft Studio

Para poder previsualizar el subinforme dentro del JasperSoft Studio hemos creado un archivo json a partir del "requestData-Default.json" de ejemplo. Se lo hemos pedido a una IA con este prompt:

```
Te he adjuntado un archivo json y attributes/datasource/table tenemos dos campos que definen la tabla columns que es un array con los nombres de las columnas y data que es un  array con las lineas. ¿Puedes generarme un json con una lista de diccionarios por línea?
```
Por si hace falta modificarlo para hacer otras pruebas.

Hemos creado un DataAdapter en el JasperSoft Studio y lo hemos enlazado al subinforme desde la opción "Dataset and Query" del elemento raiz del outline del subinforme.
Con esto aparecen los campos en la sección Fields del Outline y se pueden arrastar al diseño del informe.


