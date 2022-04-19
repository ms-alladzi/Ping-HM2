import base64
import datetime
import hashlib
import pytz
import threading

from email.utils import formataddr

import requests
from lxml import etree
from werkzeug import urls

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.modules import get_module_resource
from odoo.osv.expression import get_unaccent_wrapper
from odoo.exceptions import UserError, ValidationError

class Branch(models.Model):
    _inherit = 'res.branch'
    
    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Branch', required=True)
    
    #Transformation Location
    transformation_loc_src_id = fields.Many2one('stock.location', string='Transformation Source Location', required="True")
    scrap_loc_dst_id          = fields.Many2one('stock.location', string='Scrap Location', required="True")
    return_transformation_loc_src_id = fields.Many2one('stock.location', string='Return Transformation Source Location', required="True")

    
    cutting_loc_src_id       = fields.Many2one('stock.location', string='Source Cutting Goods Location', required="True")
    cutting_loc_dst_id       = fields.Many2one('stock.location', string='Destination Cutting Goods Location', required="True")
    cutting_loc_dst_special_id       = fields.Many2one('stock.location', string='Destination Cutting Goods Special Location', required="True")
    
    int_picking_type_id      = fields.Many2one('stock.picking.type', string='Internal Picking Type', required="True")