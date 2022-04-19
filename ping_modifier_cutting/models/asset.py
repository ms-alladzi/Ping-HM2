from datetime import datetime
from dateutil import relativedelta
import time

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.addons.procurement.models import procurement
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round, float_is_zero

class Asset(models.Model):
    _inherit = 'account.asset.asset'
    
    count_print_assetbarcode   = fields.Integer(string='Count Print Asset')

    @api.multi
    def func_count_print_assetbarcode(self):
        count_print_assetbarcode = self.count_print_assetbarcode + 1
        self.write({'count_print_assetbarcode' : count_print_assetbarcode})
        return self.count_print_assetbarcode