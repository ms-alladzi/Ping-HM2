# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
{
    'name': 'Refund Matrix Approval',
    'version': '10.0.1.0.0',
    'author': 'Hashmicro - Arya',
    'maintainer': 'Hashmicro - Arya',
    'category': 'Tools',
    'license': 'AGPL-3',
    'complexity': 'Hard',
    'depends': ['account','consignment_notes'],
    'summary': 'Refund matrix Approval',
    #'images': ['static/description/Digital_Signature.jpg'],
    'description': '''
        Last Update 17-06-2020#1
         Textile Management
    ''',
    'data': ['views/matrix_approval_conf_view.xml',
             'views/account_view.xml',
        ],
    'website': 'http://www.hashmicro.com',
    #'qweb': ['static/src/xml/digital_sign.xml'],
    'installable': True,
    'auto_install': False,
}
