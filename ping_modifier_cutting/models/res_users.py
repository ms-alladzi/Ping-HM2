import os
import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError

class ResUsers(models.Model):
    _inherit = 'res.users'
    
    branch_id       = fields.Many2one('res.branch', 'Branch', required=False)