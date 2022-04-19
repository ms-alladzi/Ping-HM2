from datetime import datetime
from dateutil import relativedelta
import time

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.addons.procurement.models import procurement
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round, float_is_zero

class SampleRequest(models.Model):
    _name = 'sample.request'
    
    @api.one
    def _get_qty_batch(self):
        if not self.lot_id.batch_name:
            self.qty_batch = 1
        elif self.lot_id.type=='piece':
            self.qty_batch = 1
        else:
            sql_query   = """SELECT batch_name, COALESCE(COUNT(id),0.0) as count, COALESCE(SUM(available_qty),0.0) as available_qty FROM stock_production_lot 
                                WHERE batch_name is not null AND available_qty>0.0 AND type='roll' AND batch_name =%s GROUP BY batch_name"""
            params      = (str(self.lot_id.batch_name),)
            self.env.cr.execute(sql_query, params)
            result_group = self.env.cr.dictfetchall()
            if result_group:
                self.qty_batch = result_group[0]['count']
            else:
                self.qty_batch = 1
        self.qty_batch = 1
    
    name            = fields.Char(string='Reference', required=True, readonly=True, default='New')
    date            = fields.Date(string='Date', required=True)
    partner_id      = fields.Many2one('res.partner', string='Customer', domain=[('customer','=',True)])
    requestor       = fields.Char(string='Name', required=True)
    mobile          = fields.Char(string='Mobile Phone', required=True)
    product_id      = fields.Many2one('product.product', string='Product', readonly=True)
    lot_id          = fields.Many2one('stock.production.lot', string='Items', required=False, readonly=True)
    location_id     = fields.Many2one('stock.location', 'Location',readonly=True, related="lot_id.location_id")
    batch_name      = fields.Char('Batch',readonly=True, related="lot_id.batch_name")
    color_group_id  = fields.Many2one('product.color.group','Color Group',readonly=True, related="product_id.color_group_id")
    color_name      = fields.Many2one('product.color','Color',readonly=True, related="product_id.color_name")
    
    product_type    = fields.Selection([('roll','Roll'),('piece','Piece')], string='Type Product',required=False, readonly=True)
    quantity_order  = fields.Float(string='Quantity Order', required=True, default=1.0)
    quantity        = fields.Float(string='Quantity', required=False, readonly=True, default=1.0)
    qty_batch       = fields.Integer(string="Qty", compute="_get_qty_batch", readonly=True)
    #batch_name      = fields.Char(string='Batch No.', readonly=True)
    user_id         = fields.Many2one('res.users', string='Sales Name', default=lambda self: self.env.user.id)
    count_print_sample   = fields.Integer(string='Count Print Sample')
    
    @api.multi
    def func_count_print_sample(self):
        count_print_sample = self.count_print_sample + 1
        self.write({'count_print_sample' : count_print_sample})
        return self.count_print_sample
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('sample.request') or _('New')

        result = super(SampleRequest, self).create(vals)
        return result
    
    @api.multi
    def open_search_product(self):
        view = self.env.ref('ping_modifier_cutting.view_sample_request_wizz_form')
#         view = self.env.ref('ping_modifier_cutting.view_searching_product_wizz_form')
#         wiz = self.env['change.dest.location'].create({'location_dest_id': self.location_dest_id.id,
#                                                        'picking_id' : self.id})
        # TDE FIXME: a return in a loop, what a good idea. Really.
        return {
            'name': _('Sample Search Product'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sample.request.wizz',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            #'res_id': wiz.id,
            #'context': {'view_sample_request': True},
            'context': {'type_menu': 'sample', 'default_type_menu': 'sample'}
        }

    
class SampleRequestWizz(models.TransientModel):
    _name = 'sample.request.wizz'
    
    product_id      = fields.Many2one('product.product', string='Product', required=True)
    color_group_id  = fields.Many2one('product.color.group','Color Group',readonly=True, related="product_id.color_group_id")
    color_name      = fields.Many2one('product.color','Color',readonly=True, related="product_id.color_name")
    product_type    = fields.Selection([('roll','Roll'),('piece','Piece')], string='Type Product',required=True)
    quantity_roll   = fields.Float(string='Quantity Roll')
    quantity_order  = fields.Float(string='Quantity Order', required=True, default=1.0)
    quantity        = fields.Float(string='Quantity', required=True, default=1.0)
    location_id     = fields.Many2one('stock.location', string='Location', required=True)
    
    product_lot_ids1    = fields.One2many('searching.product.line.wizz', 'wizz_sample_id', 'Lines', domain=[('type','=','1')])
    product_lot_ids2    = fields.One2many('searching.product.line.wizz', 'wizz_sample_id', 'Lines', domain=[('type','=','2')])
    product_lot_ids3    = fields.One2many('searching.product.line.wizz', 'wizz_sample_id', 'Lines', domain=[('type','=','3')])
    see_more            = fields.Boolean(string="See More (1)...")
    see_more3           = fields.Boolean(string="See More (2)...")
    filter_branch_id    = fields.Many2one('res.branch', string='Filter branch', default=lambda self: self.env.user.branch_id)
    type_menu           = fields.Selection([('sale','Sales'),('sample','Sample Request')], string='Type Menu')
    
    @api.onchange('product_id','quantity_order','product_type', 'quantity_roll','location_id')
    def onchange_product(self):
        print "### onchange_product ###"
        if self.quantity_roll > 0.0 and self.product_type=='roll' and self.product_id:
            temp_batch_name     = []
            product_lot_ids3    = []
            quantity = self.quantity_order
            if self.product_type in ['piece']:
                quantity = self.quantity_order + 0.2
            
            self.quantity = quantity
            
            quantity_tolerance_min  = quantity - 0.9
            quantity_tolerance_max  = quantity + 0.9
            
            lot_obj = self.env['stock.production.lot']
            lot_ids1 = lot_obj.search([('location_id','=',self.location_id.id),('product_id','=',self.product_id.id),('type','=','piece'),('available_qty','>=',quantity_tolerance_min),('available_qty','<=',quantity_tolerance_max)], order="available_qty,name")
            lot_ids2 = lot_obj.search([('location_id','=',self.location_id.id),('product_id','=',self.product_id.id),('type','=','piece'),('id','not in',lot_ids1.ids),('available_qty','>',0.0)], order="available_qty,name")
            
            sql_query = """SELECT GROUP_LOT.batch_name, GROUP_LOT.count, GROUP_LOT.available_qty
                            FROM 
                            (SELECT batch_name, COALESCE(COUNT(id),0.0) count, COALESCE(SUM(available_qty),0.0) available_qty FROM stock_production_lot 
                            WHERE type='roll' AND batch_name is not null AND available_qty>0.0 AND product_id=%s GROUP BY batch_name) AS GROUP_LOT
                            WHERE GROUP_LOT.count >= %s"""
            params      = (str(self.product_id.id),str(self.quantity_roll)) 
            self.env.cr.execute(sql_query, params)
            #result_group = map(lambda x: x, self.env.cr.fetchall())
            
            product_lot_ids1 = [(0, 0, {'product_lot_id' : lot.id,'type': '1'}) for lot in lot_ids1]
            product_lot_ids2 = [(0, 0, {'product_lot_id' : lot.id,'type': '2'}) for lot in lot_ids2]
            
            #batch_name_list = []
            for i in self.env.cr.fetchall():
                #batch_name_list.append(i[0])
                #print "batch_name_list=======>> ***", batch_name_list
                if self.product_id:
                    lot_ids = lot_obj.search([('location_id','=',self.location_id.id),('product_id','=',self.product_id.id),('type','=','roll'),('batch_name','=',i[0]),('available_qty','>',0.0)], order="available_qty,name")
                    count           = 0
                    available_qty   = 0
                    for lot in lot_ids:
                        count += 1
                        available_qty += lot.available_qty
                    if lot.batch_name not in temp_batch_name:
                        product_lot_ids3.append((0, 0, {'product_lot_id' : lot.id,'type': '3', 'batch_name': lot.batch_name, 'qty_batch': count, 'available_qty_show_only': available_qty}))
                        temp_batch_name.append(lot.batch_name)
            
            self.product_lot_ids1 = product_lot_ids1
            self.product_lot_ids2 = product_lot_ids2
            self.product_lot_ids3 = product_lot_ids3
            self.see_more         = False
            self.see_more3        = True
        else:
            quantity = self.quantity_order
            if self.product_type in ['piece']:
                quantity = self.quantity_order + 0.2
            
            self.quantity = quantity
            
            quantity_tolerance_min  = quantity - 0.9
            quantity_tolerance_max  = quantity + 0.9
            
            lot_obj = self.env['stock.production.lot']
            lot_ids1 = lot_obj.search([('location_id','=',self.location_id.id),('product_id','=',self.product_id.id),('type','=','piece'),('available_qty','>=',quantity_tolerance_min),('available_qty','<=',quantity_tolerance_max)], order="available_qty,name")
            lot_ids2 = lot_obj.search([('location_id','=',self.location_id.id),('product_id','=',self.product_id.id),('type','=','piece'),('id','not in',lot_ids1.ids),('available_qty','>',0.0)], order="available_qty,name")
            lot_ids3 = lot_obj.search([('location_id','=',self.location_id.id),('product_id','=',self.product_id.id),('type','=','roll'),('available_qty','>',0.0)], order="available_qty,name")
            
            product_lot_ids1 = [(0, 0, {'product_lot_id' : lot.id,'type': '1'}) for lot in lot_ids1]
            product_lot_ids2 = [(0, 0, {'product_lot_id' : lot.id,'type': '2'}) for lot in lot_ids2]
            product_lot_ids3 = [(0, 0, {'product_lot_id' : lot.id,'type': '3'}) for lot in lot_ids3]
        
            self.product_lot_ids1 = product_lot_ids1
            self.product_lot_ids2 = product_lot_ids2
            self.product_lot_ids3 = product_lot_ids3
            self.see_more         = False
            self.see_more3        = False
        
    @api.onchange('see_more')
    def onchange_seemore(self):
        if self.see_more==True:
            self.see_more3 = False

    @api.onchange('see_more3')
    def onchange_seemore(self):
        if self.see_more3==True:
            self.see_more = False
            
    @api.multi
    def process(self):
        active_id = self.env.context.get('active_id')
        print "active_id---->", active_id
        lost_ids = []
        
        for o in self:
            for l1 in o.product_lot_ids1:
                if l1.selected==True:
                    lost_ids.append((4, l1.product_lot_id.id))
            for l2 in o.product_lot_ids2:
                if l2.selected==True:
                    lost_ids.append((4, l2.product_lot_id.id))
            for l3 in o.product_lot_ids3:
                if l3.selected==True:
                    lost_ids.append((4, l3.product_lot_id.id))
            
            if len(lost_ids) > 1 or len(lost_ids)==0:
                raise UserError(_('Choose only 1 Item!'))
            
            for l in lost_ids:
                print "l---->", l, l[1]
                lot_id = self.env['stock.production.lot'].browse([l[1]])
                
                vals = {'product_id'    : o.product_id.id,
                        'product_type'  : o.product_type,
                        'quantity_order': o.quantity_order,
                        'quantity'      : o.quantity,
                        'lot_id'        : lot_id.id,
                        #'batch_name'    : lot_id.batch_name
                        }
                
                self.env['sample.request'].browse([active_id]).write(vals)

