from datetime import datetime
from dateutil import relativedelta
import time

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.addons.procurement.models import procurement
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round, float_is_zero

class CancelWizz(models.TransientModel):
    _name = 'cancel.wizz'
    
    active_model           = fields.Char(string='Model')
    active_id              = fields.Integer(string='ID')
    reason          = fields.Text(string='Reason', required=True)
    
    @api.model
    def default_get(self, fields):
        sale_id = False
        res = super(CancelWizz, self).default_get(fields)
        print "self.env.context----->>", self.env.context
        
        res.update({
            'active_model'    : self.env.context.get('active_model'),
            'active_id'       : self.env.context.get('active_id'),
            })
        return res
    
    
    @api.multi
    def confirm(self):
        #Sale Order
        if self.active_model=='sale.order':
            self.env[self.active_model].browse([self.active_id]).action_cancel()
            self.env[self.active_model].browse([self.active_id]).write({'reason' : self.reason})
        else:
            raise UserError(_('Please Contact Your Administrator'))