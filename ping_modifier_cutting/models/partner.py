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

class VendorOrderRules(models.Model):
    _name = "vendor.order.rules"
    
    partner_id  = fields.Many2one('res.partner', string='Vendor', ondelete='cascade')
    #Vendor
    min_order_by_color  = fields.Float(string='Min Order (Kg) by Color')
    max_order_by_color  = fields.Float(string='Max Order (Kg) by Color')
    vendor_color_group_id  = fields.Many2one('vendor.product.color.group', string='Vendor Color Groups', required=False)

class Partner(models.Model):
    _inherit = "res.partner"
    
    @api.multi
    @api.depends('member_lines')
    def _compute_membership_product(self):
        MemberLine = self.env['membership.membership_line']
        for partner in self:
            MemberLine = self.env['membership.membership_line'].search([('partner', '=', partner.id),('state','in',['free','paid'])], limit=1, order='date_to desc')
            partner.membership_product_id   = (MemberLine and MemberLine.membership_id.id) or False
    
    #Columns
    #Vendor
    customer_code     = fields.Char(string='Customer Code')
    #Vendor
    vendor_code     = fields.Char(string='Vendor Initial', size=3)
    
    #Membership
    membership_number               = fields.Char(string='Membership Number')
    card_membership_delivery_date   = fields.Date(string='Date Delivery')
    ##Additional Order Name
    same_address_membership         = fields.Boolean(string='Same Address')
    membership_delivery_street      = fields.Char()
    membership_delivery_street2     = fields.Char()
    membership_delivery_zip         = fields.Char(change_default=True)
    membership_delivery_city        = fields.Char()
    #membership_type = fields.Selection([('member','Member'),('non_member','Non Member')], string='Membership')
    
    #Expedition
    courier     = fields.Boolean(string='Courier')
    
    #Vendor
    min_order_by_color  = fields.Float(string='Min Order (Kg) by Color')
    max_order_by_color  = fields.Float(string='Max Order (Kg) by Color')
    
    membership_product_id   = fields.Many2one('product.product', string='Membership Product', compute="_compute_membership_product")
    customer_scoring        = fields.Selection([('good','Good customer'),('bad','Bad customer')], string='Customer Scoring')
    
    
    # image: all image fields are base64 encoded and PIL-supported
    image_background_membercard = fields.Binary("Image", attachment=True,
        help="This field holds the image used as avatar for this contact, limited to 1024x1024px",)
    image_background_membercard_medium = fields.Binary("Medium-sized image", attachment=True,
        help="Medium-sized image of this contact. It is automatically "\
             "resized as a 128x128px image, with aspect ratio preserved. "\
             "Use this field in form views or some kanban views.")
    image_background_membercard_small = fields.Binary("Small-sized image", attachment=True,
        help="Small-sized image of this contact. It is automatically "\
             "resized as a 64x64px image, with aspect ratio preserved. "\
             "Use this field anywhere a small image is required.")
    
    vendor_order_rules_ids  = fields.One2many('vendor.order.rules', 'partner_id',string='Vendor Order Rules')
    
    
    _sql_constraints = [
        ('customer_code_uniq', 'unique(customer,customer_code)', 'Duplicate Customer Code'),
    ]
    
    @api.onchange('payment_term_id', 'date_invoice')
    def _onchange_payment_term_date_invoice(self):
        date_invoice = self.date_invoice
        if not date_invoice:
            date_invoice = fields.Date.context_today(self)
        if not self.payment_term_id:
            # When no payment term defined
            self.date_due = self.date_due or date_invoice
        else:
            pterm = self.payment_term_id
            pterm_list = pterm.with_context(currency_id=self.company_id.currency_id.id).compute(value=1, date_ref=date_invoice)[0]
            self.date_due = max(line[0] for line in pterm_list)
    
    @api.onchange('same_address_membership')
    def _onchange_same_address_membership(self):
        print 'self----->', self, self.name, self.street, self.fax
        if self.same_address_membership:
            street      = self.street
            street2     = self.street2
            city        = self.city
        else:
            street      = None
            street2     = None
            city        = None
            
        self.membership_delivery_street      = street
        self.membership_delivery_street2             = street2
        self.membership_delivery_city                = city
                
    
    @api.onchange('discount_amount','price_unit')
    def onchange_discount_amount(self):
        if self.price_unit != 0.0 and self.discount_amount != 0.0:
            self.discount = (self.discount_amount/self.price_unit)*100
        else:
            self.discount = 0.0
    
#     @api.multi
#     def create_membership_invoice(self, product_id=None, datas=None):
#         if self.membership_number == False:
#             membership_number = self.env['ir.sequence'].next_by_code('membership')
#             self.write({'membership_number' : membership_number})
#         return super(Partner, self).create_membership_invoice(product_id=None, datas=None)
    
    @api.multi
    def create_membership_invoice(self, product_id=None, datas=None):
        """ Create Customer Invoice of Membership for partners.
        @param datas: datas has dictionary value which consist Id of Membership product and Cost Amount of Membership.
                      datas = {'membership_product_id': None, 'amount': None}
        """
        product_id = product_id or datas.get('membership_product_id')
        amount = datas.get('amount', 0.0)
        invoice_list = []
        for partner in self:
            ##Update Membership Number
            branch_code = self.env.user.branch_id.code
            if partner.membership_number == False:
                membership_number = self.env['ir.sequence'].next_by_code('membership')
                partner.write({'membership_number' : branch_code + membership_number})
            ####
            
            addr = partner.address_get(['invoice'])
            if partner.free_member:
                raise UserError(_("Partner is a free Member."))
            if not addr.get('invoice', False):
                raise UserError(_("Partner doesn't have an address to make the invoice."))
            invoice = self.env['account.invoice'].create({
                'partner_id': partner.id,
                'account_id': partner.property_account_receivable_id.id,
                'fiscal_position_id': partner.property_account_position_id.id
            })
            line_values = {
                'product_id': product_id,
                'price_unit': amount,
                'invoice_id': invoice.id,
            }
            # create a record in cache, apply onchange then revert back to a dictionnary
            invoice_line = self.env['account.invoice.line'].new(line_values)
            invoice_line._onchange_product_id()
            line_values = invoice_line._convert_to_write({name: invoice_line[name] for name in invoice_line._cache})
            line_values['price_unit'] = amount
            invoice.write({'invoice_line_ids': [(0, 0, line_values)]})
            invoice_list.append(invoice.id)
            invoice.compute_taxes()
        return invoice_list
    
    @api.multi
    def open_membercard_wizz(self):
        ##Warning if non Member
        if self.membership_state not in ['free','paid']:
            raise UserError(_("Only Membership able to Print"))
        view = self.env.ref('ping_modifier_cutting.view_membercard_wizz')
        return {
            'name': _('Print Member Card'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'membercard.wizz',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            #'res_id': wiz.id,
            #'context': self.env.context,
            'context': {'default_partner_id': self.id}
        }
        
    @api.multi
    def create_reprint_invoice(self):
        product_id = self.company_id.reprint_membercard_product_id.id
        if not product_id:
            raise UserError(_("Please set Reprint Membership Card Product First on Menu Company"))
        #invoice_list = []
        for partner in self:
            invoice = self.env['account.invoice'].create({
                'partner_id': partner.id,
                'account_id': partner.property_account_receivable_id.id,
                'fiscal_position_id': partner.property_account_position_id.id
            })
            line_values = {
                'product_id': product_id,
                #'price_unit': amount,
                'invoice_id': invoice.id,
            }
            # create a record in cache, apply onchange then revert back to a dictionnary
            invoice_line = self.env['account.invoice.line'].new(line_values)
            invoice_line._onchange_product_id()
            line_values = invoice_line._convert_to_write({name: invoice_line[name] for name in invoice_line._cache})
            #line_values['price_unit'] = amount
            invoice.write({'invoice_line_ids': [(0, 0, line_values)]})
            #invoice_list.append(invoice.id)
            invoice.compute_taxes()
        return True
    
# class MembershipInvoice(models.Model):
#     _inherit = 'membership.invoice'
#     
#     