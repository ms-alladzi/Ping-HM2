from odoo import fields, models, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError

class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    applied_on = fields.Selection([
        ('4_lot', 'Lot'),
        ('3_global', 'Global'),
        ('2_product_category', ' Product Category'),
        ('1_product', 'Product'),
        ('0_product_variant', 'Product Variant')], "Apply On",
        default='3_global', required=True,
        help='Pricelist Item applicable on selected option')
    
    lot_id      = fields.Many2one('stock.production.lot', string='Lot', required=True)