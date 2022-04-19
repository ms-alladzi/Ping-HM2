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


# class InternalMove(models.Model):
#     _name = 'internal.move'
#     
#     @api.model
#     def create(self, values):
#         values['name'] = self.env['ir.sequence'].next_by_code('internal.move') or _('New')
#         if not values.get('procurement_group_id'):
#             values['procurement_group_id'] = self.env["procurement.group"].create({'name': values['name']}).id
#         cutting_order = super(InternalMove, self).create(values)
#         return cutting_order
#     
#     #Columns
#     name        = fields.Char(string='Reference', required=True, readonly=True, default='New')
#     date        = fields.Date(string='Date', required=True)
#     sale_id     = fields.Many2one('sale.order', string='Sale Order')
#     move_lines  = fields.One2many('stock.move', 'internal_move_id', string='Cutting')
#     company_id      = fields.Many2one('res.company', 'Company', required=True, index=True,default=lambda self: self.env.user.company_id.id)
#     branch_id       = fields.Many2one('branch', 'Branch', required=True, index=True,default=lambda self: self.env.user.branch_id.id)
#     state = fields.Selection([
#         ('draft', 'Planned'),
#         ('confirm', 'Confirmed'),], string='State',
#         copy=False, default='draft', track_visibility='onchange')
#     
#     @api.multi
#     def confirm_assign(self):
#         for o in self:
#             for move in o.move_lines:
#                 move.action_confirm()
#                 move.action_assign()
#             o.write({'state': 'confirm'})
#     
