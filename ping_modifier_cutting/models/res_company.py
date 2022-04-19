import os
import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError


class Company(models.Model):
    _inherit = "res.company"
    
    #Rounding
    rounding_product_id     = fields.Many2one('product.product', string='Rounding', required="True")
    #Handling Fee
    handling_fee_product_id = fields.Many2one('product.product', string='Products', required="True")
    handling_fee_conf_ids   = fields.One2many('handling.fee.config', 'company_id', string='Handling Fee')
    
    #Transformation Location
    transformation_loc_src_id = fields.Many2one('stock.location', string='Transformation Source Location', required="True")
    scrap_loc_dst_id          = fields.Many2one('stock.location', string='Scrap Location', required="True")
    return_transformation_loc_src_id = fields.Many2one('stock.location', string='Return Transformation Source Location', required="True")
    
    cutting_loc_src_id       = fields.Many2one('stock.location', string='Source Cutting Goods Location', required="True")
    cutting_loc_dst_id       = fields.Many2one('stock.location', string='Destination Cutting Goods Location', required="True")
    cutting_loc_dst_special_id       = fields.Many2one('stock.location', string='Destination Cutting Goods Special Location', required="True")
    
    #Delivery
    delivery_product_id     = fields.Many2one('product.product', string='Delivery', required="True")
    minimum_order_amount    = fields.Float(string='Free Delivery Min.Order', required="True")
    
    #Reprint Membersip
    reprint_membercard_product_id     = fields.Many2one('product.product', string='Reprint Membership', required="True")
    
    #Min/Max Downpayment
    minimum_downpayment    = fields.Float(string='Min.Downpayment %', required="True", default=50)
    maximum_downpayment    = fields.Float(string='Max.Downpayment %', required="True", default=80)

class HandlingFeeConfig(models.Model):
    _name = "handling.fee.config"
    
    min         = fields.Float(string='Min', required="True")
    max         = fields.Float(string='Max', required="True")
    handling_fee_amount = fields.Float(string='Amount', required="True")
    company_id  = fields.Many2one('res.company', string='Company', required="True")
