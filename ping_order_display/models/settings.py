from odoo import api, fields, models, _

class OrderDisplay(models.TransientModel):
	_name = 'sale.order.display'
	_inherit = 'res.config.settings'

	order_display_time = fields.Char(string='Time (Minutes)',help="Order Display Refresh Time")
	no_of_items=fields.Integer(string="Items to Show")
	@api.model
	def get_order_display_time(self, fields):
		return self.env['ir.values'].get_default('sale.order.display', 'order_display_time')

	@api.multi
	def set_order_display_time(self):
		IrValues = self.env['ir.values']
		IrValues = IrValues.sudo()
		IrValues.set_default('sale.order.display', 'order_display_time', self.order_display_time)
	@api.model
	def get_no_of_items(self, fields):
		return self.env['ir.values'].get_default('sale.order.display', 'no_of_items')

	@api.multi
	def set_no_of_items(self):
		IrValues = self.env['ir.values']
		IrValues = IrValues.sudo()
		IrValues.set_default('sale.order.display', 'no_of_items', self.no_of_items)