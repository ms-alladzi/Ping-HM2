from datetime import datetime
from dateutil import relativedelta
import time

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.addons.procurement.models import procurement
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round, float_is_zero

class RefundMatrixApproval(models.Model):
    _name = 'refund.matrix.approval'
    
    name        = fields.Char(string='Name', required=True)
    line_ids    = fields.One2many('refund.matrix.approval.line', 'refund_matrix_conf_id', string='Lines')

class RefundMatrixApprovalLine(models.Model):
    _name = 'refund.matrix.approval.line'
    
    sequence            = fields.Char("Sequence", required=True)
    min_approver        = fields.Integer('Minimum Approver',default=1, required=True)
    user_id             = fields.Many2many('res.users', string='User', required=True)
    min_amount          = fields.Float(string='Min Amount', required=True)
    max_amount          = fields.Float(string='Max Amount', required=True)
    refund_matrix_conf_id   = fields.Many2one('refund.matrix.approval', string='Refund Matrix', ondelete='cascade')

    