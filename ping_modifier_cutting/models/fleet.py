from datetime import datetime
from dateutil import relativedelta
import time

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.addons.procurement.models import procurement
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round, float_is_zero

class fleetCourier(models.Model):
    _name = 'fleet.courier'
    
    name        = fields.Char(string='Name', required=True)
    
class DeliveryZone(models.Model):
    _name = 'delivery.zone'
    
    name        = fields.Char(string='Name', required=True)
    lines       = fields.One2many('delivery.zone.line', 'delivery_zone_id', 'Lines')
    coverage_area_ids = fields.Many2many('vit.kecamatan','zone_kecamatan_rel','zone_id','kecamatan_id')
    
class DeliveryZoneLine(models.Model):
    _name = 'delivery.zone.line'
    
    fleet_id    = fields.Many2one('fleet.courier', string='Fleet', required=True)
    unit_price  = fields.Float(String='Price')
    delivery_zone_id    = fields.Many2one('delivery.zone', string='Zone')