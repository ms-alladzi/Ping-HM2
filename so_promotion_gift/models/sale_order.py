from openerp import api, fields, models, _
from odoo.exceptions import UserError

class sale_order(models.Model):
    _inherit = "sale.order"

    def filter_promotions(self):
        sale = self
        filter_ids = super(sale_order, self).filter_promotions()
        for rec in self.env['sale.promotion'].search([('active', '=', True), ('start_date', '<=', sale.date_order), '|', ('end_date', '>=', sale.date_order), ('end_date', '=', False)]):
            if rec.type ==  '8_sale_free_gift':
                for sale_condition in rec.sale_free_gift_ids:
                    if sale_condition.minimum_amount <= self.amount_total <= sale_condition.maximum_amount:
                        filter_ids.append(rec.id)
        return filter_ids

    @api.multi
    def apply_promotion_automatically(self):
        for sale in self:
            filter_ids = sale.filter_promotions()
            if len(filter_ids) > 1:
                raise UserError(_("There are multiple promotions applicable, please select manually the promotion to apply."))
            sale.apply_promotion(self.env['sale.promotion'].browse(filter_ids))
        return True
    
    def apply_promotion(self, rec):
        sale = self
        res = super(sale_order, self).apply_promotion(rec)
        #self.env['sale.order.line'].search([('order_id', '=', sale.id), ('promotion', '=', True)]).unlink()
        promotional_product_id = self.env.ref('so_promotion.promotion_service_01')
        total_discount_amount = 0.00
        
        if rec.type ==  '8_sale_free_gift':
            gift_free_ids = self.env['sale.promotion.sale.free.gift'].search([('promotion_id','=',rec.id),('minimum_amount','<=',sale.amount_total),('maximum_amount','>=',sale.amount_total)])
            print "gift_free_ids--->", gift_free_ids
            if gift_free_ids:
                for gift_free_id in gift_free_ids:
                    self.env['sale.order.line'].create({
                        'order_id': sale.id,
                        'product_id': gift_free_id.free_product_id.id,
                        'product_uom_qty': gift_free_id.quantity_free,
                        'product_uom': gift_free_id.free_product_id.uom_id.id,
                        'price_unit': 0.00,
                        'account_id': gift_free_id.account_id.id, 
                        'promotion': True,
                    })
        return res
        
