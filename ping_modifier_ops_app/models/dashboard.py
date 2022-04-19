from odoo import models

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Main dashboard information - add Stock Count
    def get_main_dashboard_info(self):
        vals = {}
        vals['code'] = 'cutting_request'
        vals['name'] = 'Cutting Request'
        vals['planned'] = len(self.env['material.cutting'].search([('state', '=', 'draft')]))
        vals['started'] = len(self.env['material.cutting'].search([('state', '=', 'start')]))
        vals['finished'] = len(self.env['material.cutting'].search([('state', '=', 'finish')]))
        vals['cancelled'] = len(self.env['material.cutting'].search([('state', '=', 'cancel')]))
        return [vals] + super(StockPicking, self).get_main_dashboard_info()

    # Inventory dashboard
    def get_inventory_dashboard(self, wh_id):
        picking_type_list = super(StockPicking, self).get_inventory_dashboard(wh_id)
        picking_type_list.pop(picking_type_list.index(filter(lambda n: n.get('code') == 'adhoc', picking_type_list)[0]))
        return picking_type_list

StockPicking()