Ficheros de configuración del servicio de OTP.
En el directorio
/otp/graphs/vlc
poner los ficheros. Hay dos de configuración, y el geojson define la zona 
donde los autobuses amarillos no pueden hacer trayectos dentro de esa zona.

Revisar los parámetros 
    "poisWfs"
y
    "externalGeocoder"
    
El primero sirve para cargar los puntos de interés desde un WFS en gvsigOnline
El segundo tiene que ver con el servicio de geocodificación del ICV.
Hacemos de proxy para calcular el punto que necesitamos (dentro de la calle buscada)
y no enviar las coordenadas de la calle al completo, para evitar tráfico innecesario.