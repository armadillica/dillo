products_schema = {
    'name': {
        'type': 'string',
        'required': True,
    },
    'category': {
        'type': 'string',
        'allowed': ['nuts', 'cocoa'],
    },
    'price_kg': {
        'type': 'integer',
    },
    'amount_kg': {
        'type': 'integer',
        }
    }

_products = {
    'schema': products_schema,
}

DOMAIN = {
    'pistacchio_products': _products,
}
