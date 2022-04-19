from odoo import models, api
from odoo.exceptions import ValidationError

class StockMove(models.Model):
    _inherit = 'stock.move'

    # @api.constrains('product_id', 'picking_id')
    # def _check_product_duplication(self):
    #     for record in self:
    #         if record.picking_id:
    #             ids = self.env['stock.move'].search([('product_id', '=', record.product_id.id), ('picking_id', '=', record.picking_id.id)])
    #             if len(ids) > 1:
    #                 raise ValidationError('Duplicate Products is not allowed.')

    def get_available_qty(self, location_name):
        self.ensure_one()
        location_id = self.get_location_id(location_name)
        domain = [('location_id', '=', location_id), ('product_id', '=', self.product_id.id)]
        quants = self.env['stock.quant'].search(domain + [('reservation_id', '=', self.id)])
        if quants:
            return sum([x.qty for x in quants])
        return 0.0

    def get_unreserved_quants(self, location_name):
        if not self:
            return []
        self.ensure_one()
        quants_dict = {}
        lot_dict = {}
        location_id = self.get_location_id(location_name)
        domain = [('location_id', '=', location_id), ('product_id', '=', self.product_id.id)]
        quants = self.env['stock.quant'].search(domain + [('reservation_id', '=', self.id), ('lot_id', '!=', False)])
        for pack_id in self.picking_id.pack_operation_product_ids.filtered(lambda x: x.product_id == self.product_id):
            for pack_lot in pack_id.pack_lot_ids.filtered(lambda y: y.qty > 0):
                if pack_lot.lot_id.id in lot_dict:
                    lot_dict[pack_lot.lot_id.id] += pack_lot.qty
                else:
                    lot_dict[pack_lot.lot_id.id] = pack_lot.qty
        for quant in quants:
            lot_id = quant.lot_id
            if lot_id.id in quants_dict:
                quants_dict[lot_id.id]['qty'] += quant.qty
            else:
                vals = {}
                vals['lot_name'] = lot_id.name
                vals['lot_id'] = lot_id.id
                vals['qty'] = quant.qty
                vals['scanned_qty'] = 0
                if lot_id.id in lot_dict:
                    vals['scanned_qty'] = lot_dict[lot_id.id]
                quants_dict[lot_id.id] = vals
        quant_list = []
        for key in quants_dict.keys():
            quant_list.append(quants_dict[key])
        return quant_list

StockMove()