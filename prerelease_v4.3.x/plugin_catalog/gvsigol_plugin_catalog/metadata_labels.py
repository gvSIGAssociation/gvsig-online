# -*- coding: utf-8 -*-
from django.utils.translation import gettext as _


def translate_metadata_code(value):
    if value is None:
        return ''
    text_value = str(value).strip()
    if not text_value:
        return ''
    translated = _(text_value)
    if translated == text_value and text_value in _FALLBACK_TRANSLATIONS:
        return _FALLBACK_TRANSLATIONS[text_value]
    return translated


def translate_language_code(value):
    if value is None:
        return ''
    text_value = str(value).strip().lower()
    if not text_value:
        return ''
    msgid = 'lang_' + text_value
    translated = _(msgid)
    if translated == msgid and text_value in _LANGUAGE_FALLBACKS:
        return _LANGUAGE_FALLBACKS[text_value]
    return translated


def translate_language_codes(values):
    if not values:
        return []
    if isinstance(values, str):
        values = [values]
    return [translate_language_code(value) for value in values if value]


_FALLBACK_TRANSLATIONS = {
    'Update frequency': 'Frecuencia de actualización',
    'Place': 'Lugar',
    'Resource identifier': 'Identificador de recurso',
    'Language': 'Idioma',
    'Resource status': 'Estado del recurso',
    'Hierarchy level': 'Nivel jerárquico',
    'Character set': 'Juego de caracteres',
    'Distribution format': 'Formato de distribución',
    'Purpose': 'Propósito',
    'Metadata standard': 'Estándar de metadatos',
    'Metadata standard version': 'Versión del estándar de metadatos',
    'Metadata date stamp': 'Fecha de actualización del metadato',
    'Metadata update frequency': 'Frecuencia de actualización del metadato',
    'Update scope': 'Ámbito de actualización',
    'Geographic bounding box': 'Caja geográfica',
    'West': 'Oeste',
    'East': 'Este',
    'South': 'Sur',
    'North': 'Norte',
    'Responsible parties': 'Partes responsables',
    'Distributor contacts': 'Contactos del distribuidor',
    'Metadata constraints': 'Restricciones del metadato',
    'Thesaurus keywords': 'Palabras clave de tesauro',
    'Copy URL': 'Copiar URL',
    'Show in Catalog': 'Mostrar en Catálogo',
    'place': 'Lugar',
    'theme': 'Tema',
    'stratum': 'Estrato',
    'temporal': 'Temporal',
    'discipline': 'Disciplina',
    'biannually': 'Semestral',
    'continual': 'Continua',
    'daily': 'Diaria',
    'weekly': 'Semanal',
    'fortnightly': 'Quincenal',
    'monthly': 'Mensual',
    'quarterly': 'Trimestral',
    'annually': 'Anual',
    'asNeeded': 'Según necesidad',
    'irregular': 'Irregular',
    'never': 'Nunca',
    'unknown': 'Desconocida',
    'completed': 'Completado',
    'onHold': 'En espera',
    'planned': 'Planificado',
    'underDevelopment': 'En desarrollo',
    'required': 'Obligatorio',
    'final': 'Final',
    'historicalArchive': 'Archivo histórico',
    'obsolete': 'Obsoleto',
    'dataset': 'Conjunto de datos',
    'series': 'Serie',
    'service': 'Servicio',
    'utf8': 'UTF-8',
    'ucs2': 'UCS-2',
    'vector': 'Vectorial',
}

_LANGUAGE_FALLBACKS = {
    'eng': 'Inglés',
    'spa': 'Español',
    'cat': 'Catalán',
    'glg': 'Gallego',
    'eus': 'Euskera',
    'por': 'Portugués',
    'fra': 'Francés',
    'deu': 'Alemán',
    'ita': 'Italiano',
}


def register_translations_for_makemessages():
    """ISO 19115 / 19139 codelist values shown in catalog metadata details."""
    # CI_RoleCode
    _('pointOfContact')
    _('author')
    _('owner')
    _('Contact')
    _('resourceProvider')
    _('custodian')
    _('originator')
    _('publisher')
    _('distributor')
    _('user')
    _('processor')
    _('sponsor')
    _('collaborator')

    # MD_SpatialRepresentationTypeCode
    _('vector')
    _('grid')
    _('textTable')
    _('tin')
    _('stereoModel')
    _('video')

    # MD_RestrictionCode
    _('copyright')
    _('patent')
    _('patentPending')
    _('trademark')
    _('license')
    _('intellectualPropertyRights')
    _('restricted')
    _('otherRestrictions')

    # MD_TopicCategoryCode (common values)
    _('farming')
    _('biota')
    _('boundaries')
    _('climatologyMeteorologyAtmosphere')
    _('climateMeteorologyAtmosphere')
    _('economy')
    _('elevation')
    _('environment')
    _('geoscientificInformation')
    _('health')
    _('imageryBaseMapsEarthCover')
    _('intelligenceMilitary')
    _('inlandWaters')
    _('location')
    _('oceans')
    _('planningCadastre')
    _('society')
    _('structure')
    _('transportation')
    _('utilitiesCommunication')

    # Detail panel labels
    _('Use limitation')
    _('Access constraint')
    _('Use constraint type')
    _('Constraint description')
    _('Update frequency')
    _('Place')
    _('Resource identifier')
    _('Language')
    _('Resource status')
    _('Hierarchy level')
    _('Character set')
    _('Distribution format')
    _('Purpose')
    _('Metadata standard')
    _('Metadata standard version')
    _('Metadata date stamp')
    _('Metadata update frequency')
    _('Update scope')
    _('Geographic bounding box')
    _('West')
    _('East')
    _('South')
    _('North')
    _('Responsible parties')
    _('Distributor contacts')
    _('Metadata constraints')
    _('Thesaurus keywords')
    _('Copy URL')
    _('Show in Catalog')

    # MD_KeywordTypeCode
    _('place')
    _('theme')
    _('stratum')
    _('temporal')
    _('discipline')

    # ISO 639-2/B language codes
    _('lang_eng')
    _('lang_spa')
    _('lang_cat')
    _('lang_glg')
    _('lang_eus')
    _('lang_por')
    _('lang_fra')
    _('lang_deu')
    _('lang_ita')

    # MD_MaintenanceFrequencyCode
    _('continual')
    _('daily')
    _('weekly')
    _('fortnightly')
    _('monthly')
    _('quarterly')
    _('biannually')
    _('annually')
    _('asNeeded')
    _('irregular')
    _('never')
    _('unknown')

    # MD_ProgressCode
    _('completed')
    _('onHold')
    _('planned')
    _('underDevelopment')
    _('required')
    _('final')
    _('historicalArchive')
    _('obsolete')

    # MD_ScopeCode
    _('dataset')
    _('series')
    _('service')

    # MD_CharacterSetCode
    _('utf8')
    _('ucs2')
