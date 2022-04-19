from datetime import datetime
from dateutil import relativedelta
import time

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.addons.procurement.models import procurement
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round, float_is_zero

# from odoo import api, fields, models
# from odoo.tools.float_utils import float_compare, float_round
# from odoo.tools.translate import _
# from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
# from odoo.exceptions import UserError
# 
# import logging


class MaterialDictionaryHeader(models.Model):
    _name   = 'material.dictionary.header'
    
    product_id  = fields.Many2one('product.template', string='Product', required=True)
    name        = fields.Text(string='Description', required=True)
    create_uid      = fields.Many2one('res.users', string='Created by')
    create_date     = fields.Date(string='Created On')
    lines_ids       = fields.One2many('material.dictionary', 'header_id', string='Lines')
    
class MaterialDictionary(models.Model):
    _name   = 'material.dictionary'
    
    header_id   = fields.Many2one('material.dictionary.header', string='Header', required=True, ondelete="cascade")
    product_id  = fields.Many2one('product.template', string='Product', related='header_id.product_id', required=True)
    name        = fields.Text(string='Description', related='header_id.name', required=True)
    output      = fields.Char(string='Output', required=True)
    quantity    = fields.Float(string='Pcs Quantity', required=True)
    material_quantity    = fields.Float(string='Raw Quantity (kg)', required=True)
    