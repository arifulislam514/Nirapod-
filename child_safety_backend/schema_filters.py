"""
Postprocessing hook for drf-spectacular.
Renames auto-generated tags from Djoser and DRF routers
to match our numbered tag groups so everything appears
in the correct section in Swagger UI.
"""

TAG_RENAMES = {
    'auth':       '1. Authentication',
    'users':      '1. Authentication',
    'jwt':        '1. Authentication',
    'devices':    '2. Devices',
    'locations':  '3. Locations',
    'alerts':     '4. Alerts',
    'geofences':  '5. Geofences',
}


def remap_tags(result, generator, request, public):
    """Rename auto-generated tags to our numbered groups."""
    # Rename tags on every operation
    for path, methods in result.get('paths', {}).items():
        for method, operation in methods.items():
            if not isinstance(operation, dict):
                continue
            old_tags = operation.get('tags', [])
            new_tags = []
            for tag in old_tags:
                new_tags.append(TAG_RENAMES.get(tag.lower(), tag))
            operation['tags'] = list(dict.fromkeys(new_tags))  # deduplicate, keep order

    # Remove auto-generated tag entries and keep only ours
    result['tags'] = [
        {'name': '1. Authentication', 'description': 'Register, login, token management, password reset, profile management'},
        {'name': '2. Devices',        'description': 'Register and manage ESP32 devices'},
        {'name': '3. Locations',      'description': 'GPS reading history and live position'},
        {'name': '4. Alerts',         'description': 'Safety alert events and resolution'},
        {'name': '5. Geofences',      'description': 'Safe zone management'},
    ]

    return result
