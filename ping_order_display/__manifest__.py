# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Ping Order Display',
    'version': '1.0',
    'category': 'Sale',
    'sequence': 6,
    'summary': 'Allow user to create new Setting Order Display',
    'description':"""
        Sales Order Invoice Status Dashboard
    """,
    'depends': ['base','sale','sales_team'],
    'website': 'https://www.hashmicro.com',
    'author':'HashMicro/Semir Worku',
    'data': [
        
        'views/views.xml',
        'views/assets.xml'
        
    ],
    'qweb': [
        
        
    ],
    'demo': [
        
    ],
    'installable': True,
    'auto_install': False,
}
