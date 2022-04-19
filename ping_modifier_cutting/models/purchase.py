from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.exceptions import UserError, AccessError
from odoo.tools.misc import formatLang
from odoo.addons.base.res.res_partner import WARNING_MESSAGE, WARNING_HELP
import odoo.addons.decimal_precision as dp
import math

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    
    #Columns
    
    @api.multi
    def button_confirm(self):
        for order in self:
            color_group_order_list = []
            sql_query = """
                SELECT template.vendor_color_group_id as color_group, SUM(lpo.product_qty) as qty_order FROM purchase_order_line lpo
                    LEFT JOIN product_product product ON lpo.product_id = product.id
                    LEFT JOIN product_template template ON product.product_tmpl_id=template.id 
                    WHERE template.vendor_color_group_id is not null and lpo.order_id = %s
                    GROUP by template.vendor_color_group_id
            """
            params      = (str(order.id),)
            self.env.cr.execute(sql_query, params)
            color_group_order_list = self.env.cr.dictfetchall()
            
            for color in color_group_order_list:
                map_search = self.env['vendor.order.rules'].search([('partner_id','=',order.partner_id.id),('vendor_color_group_id','=',color['color_group'])])
                if not map_search:
                    raise UserError(_('Please check Color Group Order & Vendor Rules'))
                
                if color['qty_order'] < map_search.min_order_by_color or color['qty_order'] > map_search.max_order_by_color:
                    raise UserError(_('Min. Order Qty : %s and Max. Order Qty : %s') % 
                                    (map_search.min_order_by_color, map_search.max_order_by_color))
        res = super(PurchaseOrder, self).button_confirm()
        return res
    
class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"
    
    #Columns
    color_name              = fields.Many2one('product.color','Color',readonly=True, related="product_id.color_name")
    qty_roll_received       = fields.Float(compute='_compute_qty_received', string="Received Roll Qty", digits=dp.get_precision('Product Unit of Measure'), store=False)
    quantity_order_roll     = fields.Integer(string='Ordered Roll Qty', digits=dp.get_precision('Product Unit of Measure'), required=True, default=0)
    
    @api.depends('order_id.state', 'move_ids.state')
    def _compute_qty_received(self):
        print "###_compute_qty_received###"
        for line in self:
            kg_roll = line.product_id.vendor_kg_roll
            if line.order_id.state not in ['purchase', 'done']:
                line.qty_received = 0.0
                continue
            if line.product_id.type not in ['consu', 'product']:
                line.qty_received = line.product_qty
                continue
            total = 0.0
            total_roll = 0.0
            for move in line.move_ids:
                if move.state == 'done':
                    if move.product_uom != line.product_uom:
                        total += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
                    else:
                        total += move.product_uom_qty
                    total_roll += len(move.lot_ids)
            line.qty_received = total
            line.qty_roll_received  = total_roll
    
    @api.onchange('quantity_order_roll', 'product_id')
    def onchange_product_roll(self):
        print " ### onchange_product_roll"
        if self.quantity_order_roll >= 1:
            self.product_qty = self.quantity_order_roll * self.product_id.vendor_kg_roll

#     @api.onchange('product_qty', 'product_id')
#     def onchange_product_qty(self):
#         print " onchange_product_qty ###"
#         if self.product_qty >= 1:
#             self.quantity_order_roll = math.ceil(self.product_qty / self.product_id.vendor_kg_roll)
    
    @api.onchange('product_id')
    def onchange_product_id(self):
        result = {}
        if not self.product_id:
            return result

        # Reset date, price and quantity since _onchange_quantity will provide default values
        self.date_planned = datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        self.price_unit = self.product_qty = 0.0
        self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        result['domain'] = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}

        product_lang = self.product_id.with_context(
            lang=self.partner_id.lang,
            partner_id=self.partner_id.id,
        )
        self.name = (product_lang.vendor_original_name and product_lang.vendor_original_name.name or '') \
                    + (product_lang.vendor_color_group_id and ' '+product_lang.vendor_color_group_id.name or '') \
                    + (product_lang.vendor_color_name and ' '+product_lang.vendor_color_name.name or '')
        #self.name = product_lang.display_name
#         if product_lang.description_purchase:
#             self.name += '\n' + product_lang.description_purchase

        fpos = self.order_id.fiscal_position_id
        if self.env.uid == SUPERUSER_ID:
            company_id = self.env.user.company_id.id
            self.taxes_id = fpos.map_tax(self.product_id.supplier_taxes_id.filtered(lambda r: r.company_id.id == company_id))
        else:
            self.taxes_id = fpos.map_tax(self.product_id.supplier_taxes_id)

        self._suggest_quantity()
        self._onchange_quantity()

        return result