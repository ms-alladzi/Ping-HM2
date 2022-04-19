# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang

import odoo.addons.decimal_precision as dp



class SaleOrder(models.Model):
	_inherit="sale.order"

	@api.model
	def get_refresh_interval(self,current_interval):
		ir_values_obj = self.env['ir.values']
		
		refresh_time = 0.2;
		no_of_tems = 3
		refresh_time = ir_values_obj.sudo().get_default('sale.order.display', "order_display_time")
		no_of_items = ir_values_obj.sudo().get_default('sale.order.display', "no_of_items")

		return str(refresh_time)+','+str(no_of_items);