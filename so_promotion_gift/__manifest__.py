{
    'name': "SO Promotions Gift",
    'version': '1.1.1',
    'category': 'Sale',
    'author': 'Hashmicro/Arya',
    'sequence': 0,
    'summary': 'SO Promotions',
    'description': 'SO Promotions',
    'depends': ['sale','so_promotion'],
    'data': [
            "security/ir.model.access.csv",
            "views/sale_promotion.xml",
    ],
    'website': 'http://hashmicro.com',
    'application': True,
    #'images': ['static/description/icon.png'],
    'license': 'LGPL-3',
}