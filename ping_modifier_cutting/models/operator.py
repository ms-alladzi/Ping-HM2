from datetime import datetime
from dateutil import relativedelta
import time

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.addons.procurement.models import procurement
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round, float_is_zero

class CuttingOperator(models.Model):
    _name = 'cutting.operator'
    _order = 'sequence'
    
    sequence        = fields.Integer(string='Sequence')
    order_number    = fields.Integer(string='Order Number', required=True)
    name        = fields.Many2one('res.users', string='Employee', required=True)
    branch_id   = fields.Many2one('res.branch', string='Branch', required=True)
    state       = fields.Selection([
                    ('draft', 'Stand by'),
                    ('ready', 'Ready')], string='State',
                    copy=False, default='draft', track_visibility='onchange')
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Duplicate Operator'),
    ]
    
    @api.multi
    def ready(self):
        self.write({'state' : 'ready'})

    @api.multi
    def standby(self):
        self.write({'state' : 'draft', 'order_number' : 0})
