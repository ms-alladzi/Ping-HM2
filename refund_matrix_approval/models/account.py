import json
from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang

from odoo.exceptions import UserError, RedirectWarning, ValidationError

import odoo.addons.decimal_precision as dp
import logging


class AccountInvoice(models.Model):
    _inherit = "account.invoice"
    
    state                       = fields.Selection(selection_add=[('refund_approve', 'Waiting Refund Approval')])
    refund_matrix_approval_conf_id    = fields.Many2one('refund.matrix.approval', string='Matrix Approval')
    allow_refund_approve_ids    = fields.One2many('refund.matrix.line', 'invoice_id', string='Refund Allow')
    #allow_refund_approve    = fields.Many2many('res.users', string='Refund Allow')
    
#     @api.onchange('refund_matrix_approval_conf_id')
#     def onchange_allow_refund_approve(self):
#         print "refund_matrix_approval_conf_id---->", self.refund_matrix_approval_conf_id
#         if self.refund_matrix_approval_conf_id:
#             amount_refund   = self.amount_total
#             for l in self.refund_matrix_approval_conf_id.line_ids:
#                 if  
# #         self.update({
# #                     'attendance_line': [(0, 0, {values})],
# #                 })
# #         (0, 0,  { values })
    
    @api.multi
    def action_invoice_refund(self):
        context = self._context
        current_uid = context.get('uid')
        print "current_uid--->", current_uid
        
        for inv in self:
            not_allowed     = False
            min_approver    = 0
            count_approved  = 0
            
            for lapproved in inv.allow_refund_approve_ids:
                print "lapproved---->", lapproved
                
                min_approver = lapproved.matrix_selected_line_id.min_approver
                
                if lapproved.user_id.id == current_uid:
                    not_allowed = True
                    if lapproved.approved==True:
                        raise UserError(_("You already Approved"))
                    lapproved.write({'approved': True})
                
                if lapproved.approved==True:
                    count_approved += 1
            
            if not_allowed==False:
                raise UserError(_("You not allowed Approved This Refund"))
            
            if count_approved < min_approver:
                return inv.write({'state': 'refund_approve'})
        
        
        ##Copied from action_invoice_open
        # lots of duplicate calls to action_invoice_open, so we remove those already open
        to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
        if to_open_invoices.filtered(lambda inv: inv.state not in ['proforma2', 'draft','refund_approve']):
            raise UserError(_("Invoice must be in draft or Pro-forma state in order to validate it."))
        to_open_invoices.action_date_assign()
        to_open_invoices.action_move_create()
        #return self.action_invoice_open()
        return to_open_invoices.invoice_validate()
        
    
    
    @api.multi
    def action_invoice_open(self):
        # lots of duplicate calls to action_invoice_open, so we remove those already open
        to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
        if to_open_invoices.filtered(lambda inv: inv.state not in ['proforma2', 'draft']):
            raise UserError(_("Invoice must be in draft or Pro-forma state in order to validate it."))
        to_open_invoices.action_date_assign()
        to_open_invoices.action_move_create()
        return to_open_invoices.invoice_validate()
    
    
        
    @api.multi
    def action_invoice_open(self):
        # lots of duplicate calls to action_invoice_open, so we remove those already open
        print "###Masuk action_invoice_open###"
        matrix_line_obj = self.env['refund.matrix.approval.line']
        for o in self:
            if o.type in ['out_refund','in_refund']:
                ###Check Matrix##
                amount_refund   = o.amount_total
                matrix_line_ids = matrix_line_obj.search([('min_amount','<=',amount_refund),('max_amount','>=',amount_refund),('refund_matrix_conf_id','=',o.refund_matrix_approval_conf_id.id)], limit=1)
                print "*** matrix_line_ids ***", matrix_line_ids
                vals_user_approve_ids = []
                if matrix_line_ids:
                    for user in matrix_line_ids.user_id:
                        vals_user_approve_ids.append((0, 0,  { 'user_id':  user.id, 'matrix_selected_line_id': matrix_line_ids.id}))
                ###
                print "/// vals_user_approve_ids ///", vals_user_approve_ids
                if o.type in ['in_refund','out_refund'] and o.state=='draft' and vals_user_approve_ids:
                    o.allow_refund_approve_ids.unlink()
                    return o.write({'state': 'refund_approve', 'allow_refund_approve_ids': vals_user_approve_ids})
        
        return super(AccountInvoice, self).action_invoice_open()
    
    

        
#         to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
#         if to_open_invoices.filtered(lambda inv: inv.state not in ['proforma2', 'draft'] and inv.type not in ['in_refund','out_refund']): 
#             raise UserError(_("Invoice must be in draft or Pro-forma state in order to validate it."))
#         to_open_invoices.action_date_assign()
#         to_open_invoices.action_move_create()
#         return to_open_invoices.invoice_validate()
    
    @api.multi
    def action_invoice_refund_cancel(self):
        return self.action_cancel()
    
class refundMatrixLine(models.Model):
    _name = "refund.matrix.line"
    
    invoice_id  = fields.Many2one('account.invoice', string='Invoice', ondelete='cascade')
    user_id     = fields.Many2one('res.users', string='User')
    matrix_selected_line_id     = fields.Many2one('refund.matrix.approval.line', string='Selected Matrix')
    approved    = fields.Boolean(string='Approved')
    
