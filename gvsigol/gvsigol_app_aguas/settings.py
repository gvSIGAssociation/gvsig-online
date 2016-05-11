# -*- coding: utf-8 -*-

AGUAVAL_MUNI_DB = {
    'dbhost': 'test.scolab.eu',
    'dbport': '6433',
    'dbname': 'municipios',
    'dbuser': 'municipios',
    'dbpassword': 'municipios104'
}

AGUAVAL_TABLE_DEFINITION = {
    ### GRUPO REFERENCIAS CARTOGRÁFICAS ###
    'Poblacion_Contorno.shp': {
        'name': 'poblacion_contorno',
        'title': 'Población',
        'group': 'referencias_cartograficas'
    },
    'Provincia_Contorno.shp': {
        'name': 'provincia_contorno',
        'title': 'Provincia',
        'group': 'referencias_cartograficas'
    },

    ### GRUPO AGUA POTABLE ###
    'Acceso_Obra_Civil_Posicion.shp': {
        'name': 'acceso_obra_civil_posicion',
        'title': 'Acceso obra civil (Posición)',
        'group': 'agua_potable'
    },
    'Boca_Riego_Linea.shp': {
        'name': 'boca_riego_linea',
        'title': 'Boca riego (Línea)',
        'group': 'agua_potable'
    },
    'Boca_Riego_Posicion.shp': {
        'name': 'boca_riego_posicion',
        'title': 'Boca riego (Posición)',
        'group': 'agua_potable'
    },
    'Canal_Trazado.shp': {
        'name': 'canal_trazado',
        'title': 'Canal trazado',
        'group': 'agua_potable'
    },
    'Caudalimetro_Linea.shp': {
        'name': 'caudalimetro_linea',
        'title': 'Caudalimetro (Línea)',
        'group': 'agua_potable'
    },
    'Caudalimetro_Posicion.shp': {
        'name': 'caudalimetro_posicion',
        'title': 'Caudalimetro (Posición)',
        'group': 'agua_potable'
    },
    'Clorador_Linea.shp': {
        'name': 'clorador_linea',
        'title': 'Clorador (Línea)',
        'group': 'agua_potable'
    },
    'Clorador_Posicion.shp': {
        'name': 'clorador_posicion',
        'title': 'Clorador (Posición)',
        'group': 'agua_potable'
    },
    'Contador_Alta_Linea.shp': {
        'name': 'contador_alta_linea',
        'title': 'Contador alta (Línea)',
        'group': 'agua_potable'
    },
    'Contador_Alta_Posicion.shp': {
        'name': 'contador_alta_posicion',
        'title': 'Contador alta (Posición)',
        'group': 'agua_potable'
    },
    'Deposito_Linea.shp': {
        'name': 'deposito_linea',
        'title': 'Depósito (Línea)',
        'group': 'agua_potable'
    },
    'Deposito_Posicion.shp': {
        'name': 'deposito_posicion',
        'title': 'Depósito (Posición)',
        'group': 'agua_potable'
    },
    'Derivacion_Agua_en_Alta_Abandonada.shp': {
        'name': 'derivacion_agua_en_alta_abandonada',
        'title': 'Derivación agua en alta (Abandonada)',
        'group': 'agua_potable'
    },
    'Derivacion_Agua_en_Alta_Linea.shp': {
        'name': 'derivacion_agua_en_alta_linea',
        'title': 'Derivación agua en alta (Línea)',
        'group': 'agua_potable'
    },
    'Derivacion_Agua_en_Alta_Posicion.shp': {
        'name': 'derivacion_agua_en_alta_posicion',
        'title': 'Derivación agua en alta (Posición)',
        'group': 'agua_potable'
    },
    'Derivacion_Agua_en_Alta_Proyectada_Detalle.shp': {
        'name': 'derivacion_agua_en_alta_proyectada_detalle',
        'title': 'Derivación agua en alta (Proyectada detalle)',
        'group': 'agua_potable'
    },
    'Derivacion_Agua_en_Alta_Proyectada_Ejecucion.shp': {
        'name': 'derivacion_agua_en_alta_proyectada_ejecucion',
        'title': 'Derivación agua en alta (Proyectada ejecución)',
        'group': 'agua_potable'
    },
    'Derivacion_Agua_en_Alta_Proyectada_Programada.shp': {
        'name': 'derivacion_agua_en_alta_proyectada_programada',
        'title': 'Derivación agua en alta (Proyectada programada)',
        'group': 'agua_potable'
    },
    'Derivacion_Agua_en_Alta_Servicio_Provisional.shp': {
        'name': 'derivacion_agua_en_alta_proyectada_provisional',
        'title': 'Derivación agua en alta (Proyectada Provisional)',
        'group': 'agua_potable'
    },
    'Derivacion_Agua_en_Alta_Servicio.shp': {
        'name': 'derivacion_agua_en_alta_servicio',
        'title': 'Derivación agua en alta (Servicio)',
        'group': 'agua_potable'
    },
    'Desague_Alta_Linea.shp': {
        'name': 'desague_alta_linea',
        'title': 'Desagüe alta (Línea)',
        'group': 'agua_potable'
    },
    'Desague_Alta_Posicion.shp': {
        'name': 'desague_alta_posicion',
        'title': 'Desagüe alta (Posición)',
        'group': 'agua_potable'
    },
    'Estacion_de_muestreo_Linea.shp': {
        'name': 'estacion_de_muestreo_linea',
        'title': 'Estación de muestreo (Línea)',
        'group': 'agua_potable'
    },
    'Estacion_de_muestreo_Posicion.shp': {
        'name': 'estacion_de_muestreo_posicion',
        'title': 'Estación de muestreo (Posición)',
        'group': 'agua_potable'
    },
    'Estacion_Muestreo_Linea_Etiqueta.shp': {
        'name': 'estacion_muestreo_linea_etiqueta',
        'title': 'Estación muestreo (Linea etiqueta)',
        'group': 'agua_potable'
    },  
    'Estacion_Muestreo_Posicion.shp': {
        'name': 'estacion_muestreo_posicion',
        'title': 'Estación muestreo (Posición)',
        'group': 'agua_potable'
    },
    'Filtro_Linea.shp': {
        'name': 'filtro_linea',
        'title': 'Filtro (Línea)',
        'group': 'agua_potable'
    },  
    'Filtro_Posicion.shp': {
        'name': 'filtro_posicion',
        'title': 'Filtro (Posición)',
        'group': 'agua_potable'
    },
    'Grifo_Abandonada.shp': {
        'name': 'grifo_abandonada',
        'title': 'Grifo (Abandonada)',
        'group': 'agua_potable'
    },
    'Grifo_Posicion.shp': {
        'name': 'grifo_posicion',
        'title': 'Grifo (Posición)',
        'group': 'agua_potable'
    },
    'Grifo_Servicio_Provisional.shp': {
        'name': 'grifo_servicio_provisional',
        'title': 'Grifo servicio provisional',
        'group': 'agua_potable'
    },
    'Grifo_Servicio.shp': {
        'name': 'grifo_servicio',
        'title': 'Grifo servicio',
        'group': 'agua_potable'
    },
    'Grupo_de_impulsion_Linea.shp': {
        'name': 'grupo_de_impulsion_linea',
        'title': 'Grupo de impulsión (Línea)',
        'group': 'agua_potable'
    },
    'Grupo_de_impulsion_Posicion.shp': {
        'name': 'grupo_de_impulsion_posicion',
        'title': 'Grupo de impulsión (Posición)',
        'group': 'agua_potable'
    },
    'Hidrante_Alta_Linea.shp': {
        'name': 'hidrante_alta_linea',
        'title': 'Hidrante alta (Línea)',
        'group': 'agua_potable'
    },
    'Hidrante_Alta_Posicion.shp': {
        'name': 'hidrante_alta_posicion',
        'title': 'Hidrante alta (Posición)',
        'group': 'agua_potable'
    },
    'Nudo_Posicion.shp': {
        'name': 'nudo_posicion',
        'title': 'Nudo (Posición)',
        'group': 'agua_potable'
    },
    'Obra_Civil_Contorno.shp': {
        'name': 'obra_civil_contorno',
        'title': 'Obra civil (Contorno)',
        'group': 'agua_potable'
    },
    'Pozo_Linea.shp': {
        'name': 'pozo_linea',
        'title': 'Pozo (Línea)',
        'group': 'agua_potable'
    },
    'Pozo_Posicion.shp': {
        'name': 'pozo_posicion',
        'title': 'Pozo (Posición)',
        'group': 'agua_potable'
    },
    'Ramal_Abonado_Punta.shp': {
        'name': 'ramal_abonado_punta',
        'title': 'Ramal abonado (Punta)',
        'group': 'agua_potable'
    },
    'Ramal_Abonado_Trazado.shp': {
        'name': 'ramal_abonado_trazado',
        'title': 'Ramal abonado (Trazado)',
        'group': 'agua_potable'
    },
    'Sector_Superficie.shp': {
        'name': 'sector_superficie',
        'title': 'Sector superficie',
        'group': 'agua_potable'
    },
    'Toma_de_Presion_Linea.shp': {
        'name': 'toma_de_presion_linea',
        'title': 'Toma de presión (Línea)',
        'group': 'agua_potable'
    },
    'Toma_de_Presion_Posicion.shp': {
        'name': 'toma_de_presion_posicion',
        'title': 'Toma de presión (Posición)',
        'group': 'agua_potable'
    },
    'Tuberia_Alta_Trazado.shp': {
        'name': 'tuberia_alta_trazado',
        'title': 'Tubería alta (Trazado)',
        'group': 'agua_potable'
    },
    'Valvula_Hidraulica_Alta_Linea.shp': {
        'name': 'valvula_hidraulica_alta_linea',
        'title': 'Válvula hidráulica alta (Línea)',
        'group': 'agua_potable'
    },
    'Valvula_Hidraulica_Alta_Posicion.shp': {
        'name': 'valvula_hidraulica_alta_posicion',
        'title': 'Válvula hidráulica alta (Posición)',
        'group': 'agua_potable'
    },
    'Valvula_manual_Alta_Linea.shp': {
        'name': 'valvula_manual_alta_linea',
        'title': 'Válvula manual alta (Línea)',
        'group': 'agua_potable'
    },
    'Valvula_manual_Alta_Posicion.shp': {
        'name': 'valvula_manual_alta_posicion',
        'title': 'Válvula manual alta (Posición)',
        'group': 'agua_potable'
    },
    'Valvula_motorizada_Alta_Linea.shp': {
        'name': 'valvula_motorizada_alta_linea',
        'title': 'Vávula motorizada alta (Línea)',
        'group': 'agua_potable'
    },
    'Valvula_motorizada_Alta_Posicion.shp': {
        'name': 'valvula_motorizada_alta_posicion',
        'title': 'Vávula motorizada alta (Posición)',
        'group': 'agua_potable'
    },
    'Valvula_retencion_Alta_Linea.shp': {
        'name': 'valvula_retencion_alta_linea',
        'title': 'Válvula retención alta (Línea)',
        'group': 'agua_potable'
    },
    'Valvula_retencion_Alta_Posicion.shp': {
        'name': 'valvula_retencion_alta_posicion',
        'title': 'Válvula retención alta (Posición)',
        'group': 'agua_potable'
    },
    'Ventosa_Alta_Linea.shp': {
        'name': 'ventosa_alta_linea',
        'title': 'Ventosa alta (Línea)',
        'group': 'agua_potable'
    },
    'Ventosa_Alta_Posicion.shp': {
        'name': 'ventosa_alta_posicion',
        'title': 'Ventosa alta (Posición)',
        'group': 'agua_potable'
    },


    ### GRUPO RED RIEGO ###
    'Acceso_Obra_Civil_(2)_Posicion.shp': {
        'name': 'acceso_obra_civil_2_posicion',
        'title': 'Acceso obra civil (Posición)',
        'group': 'red_riego'
    },
    'Boca_Riego_(2)_Linea.shp': {
        'name': 'boca_riego_2_linea',
        'title': 'Boca riego (Línea)',
        'group': 'red_riego'
    },
    'Boca_Riego_(2)_Posicion.shp': {
        'name': 'boca_riego_2_posicion',
        'title': 'Boca riego (Posición)',
        'group': 'red_riego'
    },
    'Canal_(2)_Trazado.shp': {
        'name': 'canal_2_trazado',
        'title': 'Canal trazado',
        'group': 'red_riego'
    },
    'Caudalimetro_(2)_Linea.shp': {
        'name': 'caudalimetro_2_linea',
        'title': 'Caudalímetro (Línea)',
        'group': 'red_riego'
    },
    'Caudalimetro_(2)_Posicion.shp': {
        'name': 'caudalimetro_2_posicion',
        'title': 'Caudalímetro (Posición)',
        'group': 'red_riego'
    },
    'Clorador_(2)_Linea.shp': {
        'name': 'clorador_2_linea',
        'title': 'Clorador (Línea)',
        'group': 'red_riego'
    },
    'Clorador_(2)_Posicion.shp': {
        'name': 'clorador_2_posicion',
        'title': 'Clorador (Posición)',
        'group': 'red_riego'
    },
    'Contador_Baja_Linea.shp': {
        'name': 'contador_baja_linea',
        'title': 'Contador baja (Línea)',
        'group': 'red_riego'
    },
    'Contador_Baja_Posicion.shp': {
        'name': 'contador_baja_posicion',
        'title': 'Contador baja (Posición)',
        'group': 'red_riego'
    },
    'Deposito_(2)_Linea.shp': {
        'name': 'deposito_2_linea',
        'title': 'Depósito (Línea)',
        'group': 'red_riego'
    },
    'Deposito_(2)_Posicion.shp': {
        'name': 'deposito_2_posicion',
        'title': 'Depósito (Posición)',
        'group': 'red_riego'
    },
    'Derivacion_Agua_en_Alta_(2)_Abandonada.shp': {
        'name': 'derivacion_agua_en_alta_2_abandonada',
        'title': 'Derivación agua en alta (Abandonada)',
        'group': 'red_riego'
    },
    'Derivacion_Agua_en_Alta_(2)_Linea.shp': {
        'name': 'derivacion_agua_en_alta_2_linea',
        'title': 'Derivación agua en alta (Línea)',
        'group': 'red_riego'
    },
    'Derivacion_Agua_en_Alta_(2)_Posicion.shp': {
        'name': 'derivacion_agua_en_alta_2_posicion',
        'title': 'Derivación agua en alta (Posición)',
        'group': 'red_riego'
    },
    'Derivacion_Agua_en_Alta_(2)_Proyectada_Detalle.shp': {
        'name': 'derivacion_agua_en_alta_2_proyectada_detalle',
        'title': 'Derivación agua en alta (Proyectada detalle)',
        'group': 'red_riego'
    },
    'Derivacion_Agua_en_Alta_(2)_Proyectada_Ejecucion.shp': {
        'name': 'derivacion_agua_en_alta_2_proyectada_ejecucion',
        'title': 'Derivación agua en alta (Proyectada ejecución)',
        'group': 'red_riego'
    },
    'Derivacion_Agua_en_Alta_(2)_Proyectada_Programada.shp': {
        'name': 'derivacion_agua_en_alta_2_proyectada_programada',
        'title': 'Derivación agua en alta (Proyectada programada)',
        'group': 'red_riego'
    },
    'Derivacion_Agua_en_Alta_(2)_Servicio_Provisional.shp': {
        'name': 'derivacion_agua_en_alta_2_servicio_provisional',
        'title': 'Derivación agua en alta (Servicio provisional)',
        'group': 'red_riego'
    },
    'Derivacion_Agua_en_Alta_(2)_Servicio.shp': {
        'name': 'derivacion_agua_en_alta_2_Servicio',
        'title': 'Derivación agua en alta (Servicio)',
        'group': 'red_riego'
    },
    'Desague_Baja_Linea.shp': {
        'name': 'desague_baja_linea',
        'title': 'Desagüe baja (Línea)',
        'group': 'red_riego'
    },
    'Desague_Baja_Posicion.shp': {
        'name': 'desague_baja_posicion',
        'title': 'Desagüe baja (Posición)',
        'group': 'red_riego'
    },
    'Estacion_de_muestreo_(2)_Linea.shp': {
        'name': 'estacion_de_muestreo_2_linea',
        'title': 'Estación de muestreo (Línea)',
        'group': 'red_riego'
    },
    'Estacion_de_muestreo_(2)_Posicion.shp': {
        'name': 'estacion_de_muestreo_2_posicion',
        'title': 'Estación de muestreo (Posición)',
        'group': 'red_riego'
    },
    'Filtro_(2)_Linea.shp': {
        'name': 'filtro_2_Linea',
        'title': 'Filtro (Línea)',
        'group': 'red_riego'
    },
    'Filtro_(2)_Posicion.shp': {
        'name': 'filtro_2_posicion',
        'title': 'Filtro (Posición)',
        'group': 'red_riego'
    },
    'Grifo_(2)_Abandonada.shp': {
        'name': 'grifo_2_abandonada',
        'title': 'Grifo (Abandonada)',
        'group': 'red_riego'
    },
    'Grifo_(2)_Posicion.shp': {
        'name': 'grifo_2_posicion',
        'title': 'Grifo (Posición)',
        'group': 'red_riego'
    },
    'Grifo_(2)_Servicio_Provisional.shp': {
        'name': 'grifo_2_servicio_provisional',
        'title': 'Grifo (Servicio provisional)',
        'group': 'red_riego'
    },
    'Grifo_(2)_Servicio.shp': {
        'name': 'grifo_2_servicio',
        'title': 'Grifo (Servicio)',
        'group': 'red_riego'
    },
    'Hidrante_Baja_Linea.shp': {
        'name': 'hidrante_baja_linea',
        'title': 'Hidrante baja (Línea)',
        'group': 'red_riego'
    },
    'Hidrante_Baja_Posicion.shp': {
        'name': 'hidrante_baja_posicion',
        'title': 'Hidrante baja (Posición)',
        'group': 'red_riego'
    },
    'Grupo_de_impulsion_(2)_Linea.shp': {
        'name': 'grupo_de_impulsion_2_linea',
        'title': 'Grupo de impulsión (Línea)',
        'group': 'red_riego'
    },
    'Grupo_de_impulsion_(2)_Posicion.shp': {
        'name': 'grupo_de_impulsion_2_posicion',
        'title': 'Grupo de impulsión (Posición)',
        'group': 'red_riego'
    },
    'Nudo_(2)_Posicion.shp': {
        'name': 'nudo_2_posicion',
        'title': 'Nudo (Posición)',
        'group': 'red_riego'
    },
    'Obra_Civil_(2)_Contorno.shp': {
        'name': 'obra_civil_2_contorno',
        'title': 'Obra civil (Contorno)',
        'group': 'red_riego'
    },
    'Pozo_(2)_Linea.shp': {
        'name': 'pozo_2_linea',
        'title': 'Pozo (Línea)',
        'group': 'red_riego'
    },
    'Pozo_(2)_Posicion.shp': {
        'name': 'pozo_2_posicion',
        'title': 'Pozo (Posición)',
        'group': 'red_riego'
    },
    'Ramal_Abonado_(2)_Punta.shp': {
        'name': 'ramal_abonado_2_punta',
        'title': 'Ramal abonado (Punta)',
        'group': 'red_riego'
    },
    'Ramal_Abonado_(2)_Trazado.shp': {
        'name': 'ramal_abonado_2_trazado',
        'title': 'Ramal abonado (Trazado)',
        'group': 'red_riego'
    },
    'Toma_de_Presion_(2)_Linea.shp': {
        'name': 'toma_de_presion_2_linea',
        'title': 'Toma de presión (Línea)',
        'group': 'red_riego'
    },
    'Toma_de_Presion_(2)_Posicion.shp': {
        'name': 'toma_de_presion_2_posicion',
        'title': 'Toma de presión (Posición)',
        'group': 'red_riego'
    },
    'Sector_Baja_Superficie.shp': {
        'name': 'sector_baja_superficie',
        'title': 'Sector baja superficie',
        'group': 'red_riego'
    },
    'Tuberia_Baja_Trazado.shp': {
        'name': 'tuberia_baja_trazado',
        'title': 'Tubería baja (Trazado)',
        'group': 'red_riego'
    },
    'Valvula_Hidraulica_Baja_Linea.shp': {
        'name': 'valvula_hidraulica_baja_linea',
        'title': 'Válvula hidráulica baja (Línea)',
        'group': 'red_riego'
    },
    'Valvula_Hidraulica_Baja_Posicion.shp': {
        'name': 'valvula_hidraulica_baja_posicion',
        'title': 'Válvula hidráulica baja (Posición)',
        'group': 'red_riego'
    },
    'Valvula_manual_Baja_Linea.shp': {
        'name': 'valvula_manual_baja_linea',
        'title': 'Válvula manual baja (Línea)',
        'group': 'red_riego'
    },
    'Valvula_manual_Baja_Posicion.shp': {
        'name': 'valvula_manual_baja_posicion',
        'title': 'Válvula manual baja (Posición)',
        'group': 'red_riego'
    },
    'Valvula_motorizada_Baja_Linea.shp': {
        'name': 'valvula_motorizada_baja_linea',
        'title': 'Válvula motorizada baja (Línea)',
        'group': 'red_riego'
    },
    'Valvula_motorizada_Baja_Posicion.shp': {
        'name': 'valvula_motorizada_baja_posicion',
        'title': 'Válvula motorizada baja (Posición)',
        'group': 'red_riego'
    },
    'Valvula_retencion_Baja_Linea.shp': {
        'name': 'valvula_retencion_baja_linea',
        'title': 'Válvula retención baja (Línea)',
        'group': 'red_riego'
    },
    'Valvula_retencion_Baja_Posicion.shp': {
        'name': 'valvula_retencion_baja_posicion',
        'title': 'Válvula retención baja (Posición)',
        'group': 'red_riego'
    },
    'Ventosa_Baja_Linea.shp': {
        'name': 'ventosa_baja_linea',
        'title': 'Ventosa baja (Línea)',
        'group': 'red_riego'
    },
    'Ventosa_Baja_Posicion.shp': {
        'name': 'ventosa_baja_posicion',
        'title': 'Ventosa baja (Posición)',
        'group': 'red_riego'
    },

    ### GRUPO OTRAS REDES ###
    'Acceso_Obra_Civil_(3)_Posicion.shp': {
        'name': 'acceso_obra_civil_3_posicion',
        'title': 'Acceso obra civil (Posición)',
        'group': 'otras_redes'
    },
    'Boca_Riego_(3)_Linea.shp': {
        'name': 'boca_riego_3_linea',
        'title': 'Boca riego (Línea)',
        'group': 'otras_redes'
    },
    'Boca_Riego_(3)_Posicion.shp': {
        'name': 'boca_riego_3_posicion',
        'title': 'Boca riego (Posición)',
        'group': 'otras_redes'
    },
    'Canal_(3)_Trazado.shp': {
        'name': 'canal_3_trazado',
        'title': ' Canal (Trazado)',
        'group': 'otras_redes'
    },
    'Caudalimetro_(3)_Posicion.shp': {
        'name': 'caudalimetro_3_posicion',
        'title': 'Caudalímetro (Posición)',
        'group': 'otras_redes'
    },
    'Clorador_(3)_Linea.shp': {
        'name': 'clorador_3_linea',
        'title': 'Clorador (Línea)',
        'group': 'otras_redes'
    },
    'Clorador_(3)_Posicion.shp': {
        'name': 'clorador_3_posicion',
        'title': 'Clorador (Posición)',
        'group': 'otras_redes'
    },
    'Contador_(3)_Linea.shp': {
        'name': 'contador_3_linea',
        'title': 'Contador (Línea)',
        'group': 'otras_redes'
    },
    'Contador_(3)_Posicion.shp': {
        'name': 'contador_3_posicion',
        'title': 'Contador (Posición)',
        'group': 'otras_redes'
    },
    'Deposito_(3)_Linea.shp': {
        'name': 'deposito_3_linea',
        'title': 'Depósito (Línea)',
        'group': 'otras_redes'
    },
    'Deposito_(3)_Posicion.shp': {
        'name': 'deposito_3_posicion',
        'title': 'Depósito (Posición)',
        'group': 'otras_redes'
    },
    'Derivacion_Agua_en_Alta_(3)_Abandonada.shp': {
        'name': 'derivacion_agua_en_alta_3_abandonada',
        'title': 'Derivación agua en alta (Abandonada)',
        'group': 'otras_redes'
    },
    'Derivacion_Agua_en_Alta_(3)_Linea.shp': {
        'name': 'derivacion_agua_en_alta_3_linea',
        'title': 'Derivación agua en alta (Línea)',
        'group': 'otras_redes'
    },
    'Derivacion_Agua_en_Alta_(3)_Posicion.shp': {
        'name': 'derivacion_agua_en_alta_3_posicion',
        'title': 'Derivación agua en alta (Posición)',
        'group': 'otras_redes'
    },
    'Derivacion_Agua_en_Alta_(3)_Proyectada_Detalle.shp': {
        'name': 'derivacion_agua_en_alta_3_proyectada_detalle',
        'title': 'Derivación agua en alta (Proyectada detalle)',
        'group': 'otras_redes'
    },
    'Derivacion_Agua_en_Alta_(3)_Proyectada_Ejecucion.shp': {
        'name': 'derivacion_agua_en_alta_3_proyectada_ejecucion',
        'title': 'Derivación agua en alta (Proyectada ejecución)',
        'group': 'otras_redes'
    },
    'Derivacion_Agua_en_Alta_(3)_Proyectada_Programada.shp': {
        'name': 'derivacion_agua_en_alta_3_proyectada_programada',
        'title': 'Derivación agua en alta (Proyectada programada)',
        'group': 'otras_redes'
    },
    'Derivacion_Agua_en_Alta_(3)_Servicio_Provisional.shp': {
        'name': 'derivacion_agua_en_alta_3_servicio_provisional',
        'title': 'Derivación agua en alta (Servicio provisional)',
        'group': 'otras_redes'
    },
    'Derivacion_Agua_en_Alta_(3)_Servicio.shp': {
        'name': 'derivacion_agua_en_alta_3_servicio',
        'title': 'Derivación agua en alta (Servicio)',
        'group': 'otras_redes'
    },
    'Desague_(3)_Linea.shp': {
        'name': 'desague_3_linea',
        'title': 'Desagüe (Línea)',
        'group': 'otras_redes'
    },
    'Desague_(3)_Posicion.shp': {
        'name': 'desague_3_posicion',
        'title': 'Desagüe (Posición)',
        'group': 'otras_redes'
    },
    'Estacion_de_muestreo_(3)_Linea.shp': {
        'name': 'estacion_de_muestreo_3_linea',
        'title': 'Estación de muestreo (Línea)',
        'group': 'otras_redes'
    },
    'Estacion_de_muestreo_(3)_Posicion.shp': {
        'name': 'estacion_de_muestreo_3_posicion',
        'title': 'Estación de muestreo (Posición)',
        'group': 'otras_redes'
    },
    'Filtro_(3)_Linea.shp': {
        'name': 'filtro_3_linea',
        'title': 'Filtro (Línea)',
        'group': 'otras_redes'
    },
    'Filtro_(3)_Posicion.shp': {
        'name': 'filtro_3_posicion',
        'title': 'Filtro (Posición)',
        'group': 'otras_redes'
    },
    'Grifo_(3)_Abandonada.shp': {
        'name': 'grifo_3_abandonada',
        'title': 'Grifo (Abandonada)',
        'group': 'otras_redes'
    },
    'Grifo_(3)_Posicion.shp': {
        'name': 'grifo_3_posicion',
        'title': 'Grifo (Posición)',
        'group': 'otras_redes'
    },
    'Grifo_(3)_Servicio_Provisional.shp': {
        'name': 'grifo_3_servicio_provisional',
        'title': 'Grifo (Servicio provisional)',
        'group': 'otras_redes'
    },
    'Grifo_(3)_Servicio.shp': {
        'name': 'grifo_3_servicio',
        'title': 'Grifo (Servicio)',
        'group': 'otras_redes'
    },
    'Grupo_de_impulsion_(3)_Linea.shp': {
        'name': 'grupo_de_impulsion_3_linea',
        'title': 'Grupo de impulsión (Línea)',
        'group': 'otras_redes'
    },
    'Grupo_de_impulsion_(3)_Posicion.shp': {
        'name': 'grupo_de_impulsion_3_posicion',
        'title': 'Grupo de impulsión (Posición)',
        'group': 'otras_redes'
    },
    'Hidrante_(3)_Linea.shp': {
        'name': 'hidrante_3_linea',
        'title': 'Hidrante (Línea)',
        'group': 'otras_redes'
    },
    'Hidrante_(3)_Posicion.shp': {
        'name': 'hidrante_3_posicion',
        'title': 'Hidrante (Posición)',
        'group': 'otras_redes'
    },
    'Nudo_(3)_Posicion.shp': {
        'name': 'nudo_3_posicion',
        'title': 'Nudo (Posición)',
        'group': 'otras_redes'
    },
    'Obra_Civil_(3)_Contorno.shp': {
        'name': 'obra_civil_3_contorno',
        'title': 'Obra civil (Contorno)',
        'group': 'otras_redes'
    },
    'Pozo_(3)_Linea_Auxiliar.shp': {
        'name': 'pozo_3_linea_auxiliar',
        'title': 'Pozo (Línea auxiliar)',
        'group': 'otras_redes'
    },
    'Pozo_(3)_Posicion.shp': {
        'name': 'pozo_3_posicion',
        'title': 'Pozo (Posición)',
        'group': 'otras_redes'
    },
    'Ramal_Abonado_(3)_Punta.shp': {
        'name': 'ramal_abonado_3_punta',
        'title': 'Ramal abonado (Punta)',
        'group': 'otras_redes'
    },
    'Ramal_Abonado_(3)_Trazado.shp': {
        'name': 'ramal_abonado_3_trazado',
        'title': 'Ramal abonado (Trazado)',
        'group': 'otras_redes'
    },
    'Sector_(3)_Superficie.shp': {
        'name': 'sector_3_superficie',
        'title': 'Sector (Superficie)',
        'group': 'otras_redes'
    },
    'Toma_de_Presion_(3)_Linea.shp': {
        'name': 'toma_de_presion_3_linea',
        'title': 'Toma de presión (Línea)',
        'group': 'otras_redes'
    },
    'Toma_de_Presion_(3)_Posicion.shp': {
        'name': 'toma_de_presion_3_posicion',
        'title': 'Toma de presión (Posición)',
        'group': 'otras_redes'
    },
    'Tuberia_(3)_Trazado.shp': {
        'name': 'tuberia_3_trazado',
        'title': 'Tubería (Trazado)',
        'group': 'otras_redes'
    },
    'Valvula_Hidraulica_(3)_Linea.shp': {
        'name': 'valvula_hidraulica_3_linea',
        'title': 'Válvula hidráulica (Línea)',
        'group': 'otras_redes'
    },
    'Valvula_Hidraulica_(3)_Posicion.shp': {
        'name': 'valvula_hidraulica_3_posicion',
        'title': 'Válvula hidráulica (Posición)',
        'group': 'otras_redes'
    },
    'Valvula_manual_(3)_Linea.shp': {
        'name': 'valvula_manual_3_linea',
        'title': 'Válvula manual (Línea)',
        'group': 'otras_redes'
    },
    'Valvula_manual_(3)_Posicion.shp': {
        'name': 'valvula_manual_3_posicion',
        'title': 'Válvula manual (Posición)',
        'group': 'otras_redes'
    },
    'Valvula_motorizada_(3)_Linea.shp': {
        'name': 'valvula_motorizada_3_linea',
        'title': 'Válvula motorizada (Línea)',
        'group': 'otras_redes'
    },
    'Valvula_motorizada_(3)_Posicion.shp': {
        'name': 'valvula_motorizada_posicion',
        'title': 'Válvula motorizada (Posición)',
        'group': 'otras_redes'
    },
    'Valvula_retencion_(3)_Linea.shp': {
        'name': 'valvula_retencion_3_linea',
        'title': 'Válvula retención (Línea)',
        'group': 'otras_redes'
    },
    'Valvula_retencion_(3)_Posicion.shp': {
        'name': 'valvula_retencion_3_posicion',
        'title': 'Válvula retención (Posición)',
        'group': 'otras_redes'
    },
    'Ventosa_(3)_Linea.shp': {
        'name': 'ventosa_3_linea',
        'title': 'Ventosa (Línea)',
        'group': 'otras_redes'
    },
    'Ventosa_(3)_Posicion.shp': {
        'name': 'ventosa_3_posicion',
        'title': 'Ventosa (Posición)',
        'group': 'otras_redes'
    },

    ### GRUPO SANEAMIENTO ###
    'Acometida_de_Imbornal_Trazado.shp': {
        'name': 'acometida_de_imbornal_trazado',
        'title': 'Acometida de imbornal (Trazado)',
        'group': 'saneamiento'
    },
    'Acometida_Domiciliaria_Trazado.shp': {
        'name': 'acometida_domiciliaria_trazado',
        'title': 'Acometida domiciliaria (Trazado)',
        'group': 'saneamiento'
    },
    'Aliviadero_Linea_Auxiliar.shp': {
        'name': 'aliviadero_linea_auxiliar',
        'title': 'Aliviadero (Línea auxiliar)',
        'group': 'saneamiento'
    },
    'Aliviadero_Trazado.shp': {
        'name': 'aliviadero_trazado',
        'title': 'Aliviadero (Trazado)',
        'group': 'saneamiento'
    },
    'Arqueta_Posicion.shp': {
        'name': 'arqueta_posicion',
        'title': 'Arqueta (Posición)',
        'group': 'saneamiento'
    },
    'Bomba_(3)_Posicion.shp': {
        'name': 'bomba_3_posicion',
        'title': 'Bomba (Posición)',
        'group': 'saneamiento'
    },
    'Caudalimetro_(4)_Linea.shp': {
        'name': 'caudalimetro_4_linea',
        'title': 'Caudalimetro (Línea)',
        'group': 'saneamiento'
    },
    'Caudalimetro_(4)_Posicion.shp': {
        'name': 'caudalimetro_4_posicion',
        'title': 'Caudalimetro (Posición)',
        'group': 'saneamiento'
    },
    'Compuerta_Posicion.shp': {
        'name': 'compuerta_posicion',
        'title': 'Compuerta (Posición)',
        'group': 'saneamiento'
    },
    'Entronque_Linea_Auxiliar.shp': {
        'name': 'entronque_linea_auxiliar',
        'title': 'Entronque (Línea auxiliar)',
        'group': 'saneamiento'
    },
    'Entronque_Posicion.shp': {
        'name': 'entronque_posicion',
        'title': 'Entronque (Posición)',
        'group': 'saneamiento'
    },
    'Imbornal_Linea_Caces.shp': {
        'name': 'imbornal_linea_caces',
        'title': 'Imbornal (Línea caces)',
        'group': 'saneamiento'
    },
    'Imbornal_Posicion.shp': {
        'name': 'imbornal_posicion',
        'title': 'Imbornal (Posición)',
        'group': 'saneamiento'
    },
    'Pozo_(4)_Linea.shp': {
        'name': 'pozo_4_linea',
        'title': 'Pozo (Línea)',
        'group': 'saneamiento'
    },
    'Pozo_(4)_Posicion.shp': {
        'name': 'pozo_4_posicion',
        'title': 'Pozo (Posición)',
        'group': 'saneamiento'
    },
    'Punto_de_Medida_Localizacion.shp': {
        'name': 'punto_de_medida_localizacion',
        'title': 'Punto de medida (Localización)',
        'group': 'saneamiento'
    },
    'Puesto_Control_Central_(MTU)_Posicion.shp': {
        'name': 'puesto_control_central_mtu_posicion',
        'title': 'Puesto de control central MTU (Posición)',
        'group': 'saneamiento'
    },
    'Punto_Vertido_Extraordinario_Linea_Etiqueta.shp': {
        'name': 'punto_vertido_extraordinario_linea_etiqueta',
        'title': 'Punto de vertido extraordinario (Línea etiqueta)',
        'group': 'saneamiento'
    },
    'Punto_Vertido_Extraordinario_Posicion.shp': {
        'name': 'punto_vertido_extraordinario_posicion',
        'title': 'Punto de vertido extraordinario (Posición)',
        'group': 'saneamiento'
    },
    'Punto_Vertido_Final_Linea_Auxiliar.shp': {
        'name': 'punto_vertido_final_linea_auxiliar',
        'title': 'Punto de vertido final (Línea auxiliar)',
        'group': 'saneamiento'
    },
    'Punto_Vertido_Final_Posicion.shp': {
        'name': 'punto_vertido_final_posicion',
        'title': 'Punto de vertido final (Posición)',
        'group': 'saneamiento'
    },
    'Punto_Vertido_Linea_Etiqueta.shp': {
        'name': 'punto_vertido_linea_etiqueta',
        'title': 'Punto de vertido (Línea etiqueta)',
        'group': 'saneamiento'
    },
    'Punto_Vertido_Posicion.shp': {
        'name': 'punto_vertido_posicion',
        'title': 'Punto de vertido (Posición)',
        'group': 'saneamiento'
    },
    'Radar_Meteorologico_Posicion.shp': {
        'name': 'radar_meteorologico_posicion',
        'title': 'Radar meteorológico (Posición)',
        'group': 'saneamiento'
    },
    'Texto_Tramo_Colector_Linea_Auxiliar.shp': {
        'name': 'texto_tramo_colector_linea_auxiliar',
        'title': 'Texto tramo colector (Línea auxiliar)',
        'group': 'saneamiento'
    },
    'Tramo_de_Colector_Sentido.shp': {
        'name': 'tramo_de_colector_sentido',
        'title': 'Tramo de colector (Sentido)',
        'group': 'saneamiento'
    },
    'Tramo_de_Colector_Trazado.shp': {
        'name': 'tramo_de_colector_trazado',
        'title': 'Tramo de colector (Trazado)',
        'group': 'saneamiento'
    },
    'Estacion_Bombeo_Posicion.shp': {
        'name': 'estacion_bombeo_posicion',
        'title': 'Estación bombeo (Posición)',
        'group': 'saneamiento'
    },
    'Valvula_Reguladora_Caudal_Posicion.shp': {
        'name': 'valvula_reguladora_caudal_posicion',
        'title': 'Válvula reguladora de caudal (Posición)',
        'group': 'saneamiento'
    },
    'Velocimetro_Posicion.shp': {
        'name': 'velocimetro_posicion',
        'title': 'Velocímetro (Posición)',
        'group': 'saneamiento'
    },
    'Vertedero_Posicion.shp': {
        'name': 'vertedero_posicion',
        'title': 'Vertedero (Posición)',
        'group': 'saneamiento'
    },

    ### GRUPO CARTOGRAFÍA ###
    'red_colector_Trazado.shp': {
        'name': 'red_colector_trazado',
        'title': 'Red colector (Trazado)',
        'group': 'cartografia'
    },
    'red_elec_Trazado.shp': {
        'name': 'red_elec_trazado',
        'title': 'Red eléctrica (Trazado)',
        'group': 'cartografia'
    },
    'red_galerias_Trazado.shp': {
        'name': 'red_galerias_trazado',
        'title': 'Red galerías (Trazado)',
        'group': 'cartografia'
    },
    'red_gas_Trazado.shp': {
        'name': 'red_gas_trazado',
        'title': 'Red gas (Trazado)',
        'group': 'cartografia'
    },
    'Red_semaforos_Trazado.shp': {
        'name': 'red_semaforos_trazado',
        'title': 'Red semáforos (Trazado)',
        'group': 'cartografia'
    },
    'red_telef_Trazado.shp': {
        'name': 'red_telef_trazado',
        'title': 'Red telefonía (Trazado)',
        'group': 'cartografia'
    }
}