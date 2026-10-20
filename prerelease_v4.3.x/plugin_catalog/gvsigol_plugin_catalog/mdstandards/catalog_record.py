# -*- coding: utf-8 -*-
"""Canonical dict used by the catalog details HTML (views.get_metadata_as_html)."""


def empty_constraints():
    return {
        'useLimitations': [],
        'accessConstraints': [],
        'useConstraints': [],
        'otherConstraints': [],
    }


def empty_catalog_record():
    return {
        'metadata_id': '',
        'title': '',
        'abstract': '',
        'publish_date': '',
        'update_frequency': '',
        'resource_identifier': '',
        'languages': [],
        'geographic_place': [],
        'resource_status': '',
        'hierarchy_level': '',
        'character_set': '',
        'distribution_formats': [],
        'purpose': '',
        'metadata_standard_name': '',
        'metadata_standard_version': '',
        'metadata_profile': '',
        'date_stamp': '',
        'metadata_update_frequency': '',
        'update_scope': '',
        'keyword_groups': [],
        'period_start': '',
        'period_end': '',
        'categories': [],
        'keywords': [],
        'representation_type': '',
        'scale': '',
        'srs': '',
        'extent_west': '',
        'extent_east': '',
        'extent_south': '',
        'extent_north': '',
        'image_url': '',
        'thumbnails': [],
        'resources': [],
        'resource_constraints': empty_constraints(),
        'metadata_constraints': empty_constraints(),
        'contacts': {
            'metadata_contacts': [],
            'resource_contacts': [],
            'responsible_parties': [],
            'distributor_contacts': [],
        },
    }
