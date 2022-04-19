from datetime import datetime
from dateutil import relativedelta
import time

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.addons.procurement.models import procurement
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round, float_is_zero

class PickupRequest(models.Model):
    _name = 'pickup.request'
    
    name        = fields.Char(string='Reference', required=True, readonly=True, default='New')
    date        = fields.Date(string='Date', required=True)
    invoice_id  = fields.Many2one('account.invoice', required=True, domain=[('type','=','out_invoice'),('state','=','paid')])
    requestor_name  = fields.Char(string='Requestor Name', required=True)
    pickup_name     = fields.Char(string='Pickup Name', required=True)
    mobile          = fields.Char(string='Mobile', required=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),], string='State',
        copy=False, default='draft', track_visibility='onchange')
    
    
    @api.multi
    def confirm(self):
        number = self.name
        if self.name =='New':
            number = self.env['ir.sequence'].next_by_code('pickup.request')
        self.write({'name' : number, 'state' : 'confirm'})