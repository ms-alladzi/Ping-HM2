from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from _ast import If

class AccountPaymentDeposit(models.Model):
    _inherit = 'account.payment'
    
    @api.multi
    @api.depends('amount_receipt','amount')
    def compute_amount_change(self):
        for o in self:
            if o.amount_receipt - o.amount < 0.0 and o.amount_receipt != 0.0:
                raise UserError(_("Amount Receipt must same or bigger than %s.") % o.amount)
            o.amount_change = o.amount_receipt - o.amount
    #Columns
    sale_id     = fields.Many2one('sale.order', string='Sale')
    journal_type_id = fields.Selection(selection=[('bank','Bank'),('cash','Cash')],related='journal_id.type', string='Journal Type', readonly=True)
    
    downpayment_amount_min = fields.Monetary(related='sale_id.downpayment_amount_min', string='Min. DP', readonly=True)
    downpayment_amount_max = fields.Monetary(related='sale_id.downpayment_amount_max', string='Max. DP', readonly=True)
    
    ##View Cashier
    amount_receipt  = fields.Monetary(string='Amount Receipt')
    amount_change   = fields.Monetary(string='Amount Change', compute='compute_amount_change', store=True)
    
    ##Attachment
    image_payment_attachment          = fields.Binary(string='Upload Payment')
    payment_attachment_name     = fields.Char(string='Payment Attachment')
    
#     image_ktp = fields.Binary('Upload KTP')
#     ktp_name = fields.Char('KTP Name', track_visibility='onchange')
    count_print_deposit   = fields.Integer(string='Count Print Deposit')


    @api.multi
    def func_count_print_deposit(self):
        count_print_deposit = self.count_print_deposit + 1
        self.write({'count_print_deposit' : count_print_deposit})
        return self.count_print_deposit

    
    @api.onchange('sale_id')
    def onchange_sale(self):
        sale = self.sale_id
        self.partner_id = sale.partner_id.id
        self.amount     = sale.downpayment_amount_min
        
    @api.onchange('amount','sale_id')
    def onchange_amount(self):
        if self.sale_id and (self.amount > self.sale_id.downpayment_amount_max):
            raise UserError(_("Max Payment %s.") % self.sale_id.downpayment_amount_max)
        if self.sale_id and (self.amount < self.sale_id.downpayment_amount_min) and self.amount != 0.0:
            raise UserError(_("Min Payment %s.") % self.sale_id.downpayment_amount_min)
        
        
        
    @api.multi
    def post(self):
        res = super(AccountPaymentDeposit, self).post()
        
        #Change SO DP -> Sale Order
        if self.sale_id:
            print "### Post Deposit ###"
            self.sale_id.create_request_cutting()
            self.sale_id.create_internal_move()
            return self.sale_id.write({'state' : 'cutting_ordered'})

class ReceiptPayment(models.Model):
    _inherit = 'receipt.payment'
    
    @api.multi
    @api.depends('line_cr_ids','line_cr_ids.amount','line_cr_ids.reconcile','line_dr_ids','line_dr_ids.amount','line_dr_ids.reconcile')
    def _get_amount_total(self):
        print "### _get_amount_total ###"
        
        for o in self:
            amount_total    = 0.0 
            amount_total_dr = 0.0 
            amount_total_cr = 0.0
            
            for lcr in o.line_cr_ids:
                amount_total_cr += lcr.amount 
            for ldr in o.line_dr_ids:
                amount_total_dr += ldr.amount 
            
            if o.type=='supplier':
                amount_total = amount_total_cr - amount_total_dr
            elif o.type=='customer':
                amount_total = amount_total_dr - amount_total_cr
            
            o.amount = amount_total
    
    amount = fields.Monetary(currency_field='currency_id', string='Total', compute='_get_amount_total', store=True)
    
    _sql_constraints = [
        ('payment_ref_uniq', 'unique(payment_ref)', 'Payment ref must be unique!'),
    ]
    
