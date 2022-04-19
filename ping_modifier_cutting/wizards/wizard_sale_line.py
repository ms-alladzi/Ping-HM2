from datetime import datetime
from dateutil import relativedelta
import time

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.addons.procurement.models import procurement
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round, float_is_zero

class SaleLineSearchtWizz(models.TransientModel):
    _name = 'sale.line.search.wizz'
    
    product_id      = fields.Many2one('product.product', string='Product', required=True, readonly=True)
    product_type    = fields.Selection([('roll','Roll'),('piece','Piece')], string='Type Product',required=True, readonly=True)
    quantity_order  = fields.Float(string='Quantity Order', required=True, default=1.0, readonly=True)
    quantity        = fields.Float(string='Quantity', required=True, default=1.0, readonly=True)
    
    product_lot_ids1    = fields.One2many('searching.product.line.wizz', 'so_line_wizz_id', 'Lines', domain=[('type','=','1')])
    product_lot_ids2    = fields.One2many('searching.product.line.wizz', 'so_line_wizz_id', 'Lines', domain=[('type','=','2')])
    product_lot_ids3    = fields.One2many('searching.product.line.wizz', 'so_line_wizz_id', 'Lines', domain=[('type','=','3')])
    see_more            = fields.Boolean(string="See More (1)...")
    see_more3           = fields.Boolean(string="See More (2)...")
    
    sale_line_id        = fields.Many2one('sale.order.line', string='SO Line', required=True, readonly=True)
    
    @api.model
    def default_get(self, fields):
        sale_line_obj = self.env['sale.order.line']
        res = super(SaleLineSearchtWizz, self).default_get(fields)
        
        sale_line_id = sale_line_obj.browse(self.env.context.get('active_id'))
        
        res.update({
            'product_id'    : sale_line_id.product_id.id,
            'quantity_order': sale_line_id.quantity_order,    
            'quantity'      : sale_line_id.product_uom_qty,    
            'product_type'  : 'piece',
            'sale_line_id'  : sale_line_id.id
        })
        return res
    
    @api.multi
    def process(self):
        active_id = self.env.context.get('active_id')
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
                    
            print "lost_ids---->yyy", lost_ids  
            ##Get Lot Name
            batch_name = """"""
            if lost_ids:
                for lot in lost_ids:
                    batch_name = self.env['stock.production.lot'].browse([lot[1]]).batch_name
            
            old_lot_ids = []
            print "lost_ids---->xxxx", lost_ids
            for l in lost_ids:
                print "l----->>", l
                
                print "order vs stock", o.quantity , self.env['stock.production.lot'].browse(l[1]).available_qty
                
                if o.product_type=='piece' and o.quantity > self.env['stock.production.lot'].browse(l[1]).available_qty and abs(o.quantity - self.env['stock.production.lot'].browse(l[1]).available_qty) > 0.9:
                    raise UserError(_('Qty Available not Enought'))
                
                #Save Old Lots
                for old_lot in o.sale_line_id.sale_order_line_lots:
                    old_lot_ids.append(old_lot.id)
                    
                #Remove Old Lots
                #o.sale_line_id.sale_order_line_lots.unlink()
                #o.sale_line_id.write({'sale_order_line_lots' : False})
                
                #Put Net Lots
                print "l---->", l
                o.sale_line_id.write({'sale_order_line_lots' : [(6, 0, [l[1]])]})
                
                #Reload Available Qty
                search_old_cutting = self.env['material.cutting.line'].search([('cutting_id','=',o.sale_line_id.order_id.cutting_order_id.id),('sale_line_id','=',o.sale_line_id.id)])
                self.env['material.cutting.line'].browse(search_old_cutting.ids).write({'sale_line_id' : False})
                
                self.env['stock.production.lot'].browse(old_lot_ids).check_available_qty()
                new_lot_for_cutting = self.env['stock.production.lot'].browse(l[1])
                new_lot_for_cutting.check_available_qty()
                new_lot_for_cutting.write({'name' : new_lot_for_cutting.name})
                #Create New Cutting Order Line
                o.sale_line_id.create_cutting_line()

        #raise UserError(_('XXXt'))       
    
    @api.onchange('product_id','quantity_order','product_type')
    def onchange_product(self):
        quantity = self.quantity_order
        if self.product_type in ['piece']:
            quantity = self.quantity_order + 0.2
        
        self.quantity = quantity
        
        quantity_tolerance_min  = quantity - 0.9
        quantity_tolerance_max  = quantity + 0.9
        
        lot_obj = self.env['stock.production.lot']
        lot_ids1 = lot_obj.search([('product_id','=',self.product_id.id),('type','=','piece'),('available_qty','>=',quantity_tolerance_min),('available_qty','<=',quantity_tolerance_max)], order="available_qty,name")
        lot_ids2 = lot_obj.search([('product_id','=',self.product_id.id),('type','=','piece'),('id','not in',lot_ids1.ids),('available_qty','>',0.0)], order="available_qty,name")
        lot_ids3 = lot_obj.search([('product_id','=',self.product_id.id),('type','=','roll'),('available_qty','>',0.0)], order="available_qty,name")
        
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
    def process2(self):
        active_id = self.env.context.get('active_id')
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
                lot_id = self.env['stock.production.lot'].browse([l[1]])
                
                vals = {'product_id'    : o.product_id.id,
                        'product_type'  : o.product_type,
                        'quantity_order': o.quantity_order,
                        'quantity'      : o.quantity,
                        'lot_id'        : lot_id.id,
                        #'batch_name'    : lot_id.batch_name
                        }
                
