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

MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
}

class Invoice(models.Model):
    _inherit = 'account.invoice'
    
    delivery_label      = fields.Selection([('free','Free Delivery')], string='Delivery Label')
    bank_account_id     = fields.Many2one('res.partner.bank')
    user_paid_id        = fields.Many2one('res.users', string='Paid by', readonly=True)
    count_print_invoice   = fields.Integer(string='Count Print Invoice')


    @api.multi
    def func_count_print_invoice(self):
        count_print_invoice = self.count_print_invoice + 1
        self.write({'count_print_invoice' : count_print_invoice})
        return self.count_print_invoice
    
    @api.multi
    def action_invoice_paid(self):
        # lots of duplicate calls to action_invoice_paid, so we remove those already paid
        to_pay_invoices = self.filtered(lambda inv: inv.state != 'paid')
        if to_pay_invoices.filtered(lambda inv: inv.state != 'open'):
            raise UserError(_('Invoice must be validated in order to set it to register payment.'))
        if to_pay_invoices.filtered(lambda inv: not inv.reconciled):
            raise UserError(_('You cannot pay an invoice which is partially paid. You need to reconcile payment entries first.'))
        ##Add Paid By
        return to_pay_invoices.write({'state': 'paid', 'user_paid_id': self.env.user.id})
    
    @api.multi
    def _get_payment_ids(self):
        self.ensure_one()
        if self.move_id:
            amount_paid = self.amount_total - self.residual
            return amount_paid
        else:
            return 0.0

class account_payment(models.Model):
    _inherit = "account.payment"


    @api.model
    def default_get(self, fields):
        rec = super(account_payment, self).default_get(fields)
        invoice_defaults = self.resolve_2many_commands('invoice_ids', rec.get('invoice_ids'))
        if invoice_defaults and len(invoice_defaults) == 1:
            invoice = invoice_defaults[0]
            rec['communication'] = invoice['origin'] or invoice['reference'] or invoice['name'] or invoice['number']
            rec['currency_id'] = invoice['currency_id'][0]
            rec['payment_type'] = invoice['type'] in ('out_invoice', 'in_refund') and 'inbound' or 'outbound'
            rec['partner_type'] = MAP_INVOICE_TYPE_PARTNER_TYPE[invoice['type']]
            rec['partner_id'] = invoice['partner_id'][0]
            rec['amount'] = invoice['residual']
        return rec