from datetime import datetime
from dateutil import relativedelta
import time

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.addons.procurement.models import procurement
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round, float_is_zero

class DeliveryRequest(models.Model):
    _name = 'delivery.request'
    
    partner_id  = fields.Many2one('res.partner', string='Customer', required=True)
    name        = fields.Char(string='Reference', required=True, readonly=True, default='New')
    date        = fields.Date(string='Date', required=True)
    invoice_ids = fields.Many2many('account.invoice', 'delivery_invoice_rel', 'delivery_request_id', 'invoice_id',string="Invoice", copy=False)
    
    requestor_name = fields.Char(string='Requestor Name', required=True)
    
    fleet_id  = fields.Many2one('fleet.courier', string='Fleet', required=True)
    courier_id  = fields.Many2one('res.partner', string='Courier', required=True, domain=[('courier','=',True)])
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char()
    kecamatan_id  = fields.Many2one('vit.kecamatan', required=True)
    
    zone_id         = fields.Many2one('delivery.zone', string='Zone', readonly=True)
    delivery_fee    = fields.Float(string="Delivery Fee", readonly=True)
    invoice_id      = fields.Many2one('account.invoice', string='Invoice', readonly=True)
    
    company_id      = fields.Many2one('res.company', 'Company', required=True, index=True,default=lambda self: self.env.user.company_id.id)
    
    delivery_sale_ids   = fields.Many2many("sale.order", string='Sale Orders', compute="_get_sale_order", readonly=True, copy=False)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),], string='State',
        copy=False, default='draft', track_visibility='onchange')
    
    count_print_delivery   = fields.Integer(string='Count Print Delivery')


    @api.multi
    def func_count_print_delivery(self):
        count_print_delivery = self.count_print_delivery + 1
        self.write({'count_print_delivery' : count_print_delivery})
        return self.count_print_delivery
    
    
    @api.depends('state', 'invoice_ids')
    def _get_sale_order(self):
        order_line_obj  = self.env['sale.order.line']
        for delivery in self:
            sale_ids = []
            for inv in delivery.invoice_ids:
                sale_id = inv.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')
                
                sale_ids.append(sale_id.id)
            delivery.update({
                'delivery_sale_ids': sale_ids,
            })
    
    @api.multi
    def check_tarif(self):
        for req in self:
            coverage_ids = self.env['delivery.zone'].search([('coverage_area_ids','=',req.kecamatan_id.id)])
            if len(coverage_ids) >1:
                raise UserError(_("Multiple Coverage Area Please Check Delivery Zone Settings"))
            
            fleet_ids = self.env['delivery.zone.line'].search([('delivery_zone_id','=',coverage_ids.id),('fleet_id','=',req.fleet_id.id)])
            if len(fleet_ids) >1:
                raise UserError(_("Multiple Fleet Delivery Zone Settings"))
            
            req.write({'zone_id' : coverage_ids.id, 'delivery_fee' : fleet_ids.unit_price})
            
    @api.multi
    def confirm(self):
        for req in self:
            number = req.name
            if req.name =='New':
                number = self.env['ir.sequence'].next_by_code('delivery.request')
            
            invoice_id = req.create_invoice()
            req.write({'name': number, 'state' : 'confirm','invoice_id' : invoice_id.id})
            
    @api.multi
    def create_invoice(self):
        for req in self:
            total_invoice = sum(inv.amount_total for inv in req.invoice_ids)
            print "total_invoice---->", total_invoice   
            delivery_label = ''
            if total_invoice >= req.company_id.minimum_order_amount:
                delivery_label = 'free'
                
            vals_line = {'product_id'   : req.company_id.delivery_product_id.id,
                         'account_id'   : req.company_id.delivery_product_id.property_account_expense_id.id,
                         'name'         : "Delivery %s, %s" % (req.zone_id.name, req.kecamatan_id.name),
                         'price_unit'   : req.delivery_fee
                         }
            print "delivery_label--->", delivery_label
            vals = {'partner_id'    : req.partner_id.id,
                    'team_id'       : False,
                    'account_id'    : req.partner_id.property_account_payable_id.id,
                    'delivery_label': delivery_label,
                    'invoice_line_ids'  : [(0,0,vals_line)]
                    }
            invoice_id = self.env['account.invoice'].create(vals)
        return invoice_id
            
    
    
    
    
    
    
    
    
    
    
    
    
    
