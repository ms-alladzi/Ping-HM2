from odoo import api, fields, models, _


class sale_promotion(models.Model):
    _inherit = "sale.promotion"

    type = fields.Selection(selection_add=[('8_sale_free_gift', 'Sales Free Gift')])
    sale_free_gift_ids = fields.One2many('sale.promotion.sale.free.gift', 'promotion_id', 'Discounts')
    
    @api.model
    def default_get(self, fields):
        res = super(sale_promotion, self).default_get(fields)
        products = self.env['product.product'].search([('name', '=', 'Promotion service')])
        if products:
            res.update({'product_id': products[0].id})
        return res

class sale_promotion_sale_free_gift(models.Model):
    _name = "sale.promotion.sale.free.gift"
    _order = "minimum_amount, maximum_amount"

    minimum_amount = fields.Float('Minimum Amount', required=1, default=1.0)
    maximum_amount = fields.Float('Maximum Amount', required=1, default=1.0)
    quantity_free = fields.Float('Quantity free', required=1, default=1.0)
    free_product_id = fields.Many2one('product.product', string='Product', required=1)
    account_id = fields.Many2one('account.account', string='Account', domain=[('deprecated', '=', False)], required=1)
    promotion_id = fields.Many2one('sale.promotion', 'Promotion', required=1)
