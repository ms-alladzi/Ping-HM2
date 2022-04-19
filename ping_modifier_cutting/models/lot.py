from odoo import fields, models, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
from werkzeug.contrib.profiler import available
from matplotlib.pyplot import spring

class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'
    
    @api.multi
    def name_get(self):
        x = self.env.context.get
        print "x---->", x
        result = []
        for lot in self:
            serial_number   = lot.name or ''
            batch_number    = lot.batch_name or ''
            name    = (batch_number != '' and batch_number+ ' - ' + serial_number) or serial_number 
            result.append((lot.id, name))
        return result
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('batch_name', operator, name)]
        lot = self.search(domain + args, limit=limit)
        return lot.name_get()
    
#     @api.model
#     def name_search(self, name, args=None, operator='ilike', limit=100):
#         args = args or []
#         recs = self.browse()
#         if name:
#             recs = self.search(['|',('name', operator, name),('batch_name', operator, name)] + args, limit=limit)
#         if not recs:
#             recs = self.search(['|',('name', operator, name),('batch_name', operator, name)] + args, limit=limit)
#         return recs.name_get()
    
#     @api.multi
#     @api.depends('name', 'brand_id')
#     def name_get(self):
#         res = []
#         for record in self:
#             name = record.name
#             if record.brand_id.name:
#                 name = record.brand_id.name + '/' + name
#             res.append((record.id, name))
#         return res


            #raise UserError(_('XXX'))
    
    count_print_lot   = fields.Integer(string='Count Print Lot')


    @api.multi
    def func_count_print_lot(self):
        count_print_lot = self.count_print_lot + 1
        self.write({'count_print_lot' : count_print_lot})
        return self.count_print_lot

    @api.multi
    def temp_execute(self):
        for i in self.search([]):
            print "S/N--->", i.name
            i.check_available_qty()
    
    
    @api.multi
    @api.depends('lot_reserved_ids','lot_reserved_ids.sale_line_id','lot_reserved_ids.lot_id','quant_ids','quant_ids.qty','quant_ids.lot_id','quant_ids.location_id','quant_ids.reservation_id')
    def check_available_qty(self):
        for o in self:
            print "self---->>check_available_qty", self
            try :
                current_id = self._origin.id
            except:
                current_id = o.id
                
            print "current_id----->", current_id
            
            if current_id:
#                 sql_query   = """SELECT COALESCE(SUM(line.product_uom_qty),0.0) as booked_qty
#                                     FROM sale_line_lot_rel rel 
#                                     LEFT JOIN sale_order_line line ON rel.sale_line_id=line.id 
#                                     WHERE rel.lot_id = %s AND line.state not in ('cancel','sale','done')"""
                
                sql_query   = """SELECT 
                                CASE 
                                 WHEN COALESCE(SUM(line.product_uom_qty),0.0) > (select COALESCE(available_qty,0.0) from stock_production_lot where id=%s) THEN (select COALESCE(available_qty,0.0) from stock_production_lot where id=%s)
                                 ELSE COALESCE(SUM(line.product_uom_qty),0.0)
                                END
                                AS booked_qty
                                    FROM sale_line_lot_rel rel 
                                    LEFT JOIN sale_order_line line ON rel.sale_line_id=line.id 
                                    WHERE rel.lot_id = %s AND line.state not in ('cancel','sale','done')"""
                
                params      = (str(current_id),str(current_id),str(current_id),) 
                self.env.cr.execute(sql_query, params)
                result = self.env.cr.dictfetchall()[0]
                booked_qty = result['booked_qty']
                o.booked_qty = result['booked_qty']
                         
                res = o.product_id._compute_quantities_dict(lot_id=o.id, owner_id=False, package_id=False, from_date=False, to_date=False)
                
                print "res---->>", res
                
                o.stock_qty = res[o.product_id.id]['qty_available']
                o.available_qty = res[o.product_id.id]['qty_available'] - result['booked_qty']
             
            #raise UserError(_('XXX'))
            
#     @api.multi        
#     @api.depends()
#     def check_booked_qty(self):
#         sql_query   = """SELECT SUM(line.product_uom_qty) as booked_qty
#                             FROM sale_line_lot_rel rel 
#                             LEFT JOIN sale_order_line line ON rel.sale_line_id=line.id 
#                             WHERE rel.lot_id = %s AND line.state != 'cancel'"""
#         params      = (str(self.id),) 
#         self.env.cr.execute(sql_query, params)
#         result = self.env.cr.dictfetchall()[0]
#         self.booked_qty = result['booked_qty']
    
    @api.multi
#     @api.depends('bom_id.routing_id', 'bom_id.routing_id.operation_ids')
    def _lot_stock_location(self):
        for lot in self:
            location_id = False
            for quant in lot.quant_ids.filtered(lambda r: r.location_id.usage == 'internal'):
                if quant.location_id.usage=='internal':
                    location_id = quant.location_id.id
            lot.location_id = location_id 
    #Columns
    receive_date= fields.Datetime('Receive Date')
    batch_name  = fields.Char('Batch Number')
    type        = fields.Selection([('roll','Roll'),('piece','Eceran')], string='Type', required=True, default='roll')
    location_id = fields.Many2one('stock.location', 'Location', compute='_lot_stock_location')
    stock_qty   = fields.Float('Stock Qty', compute='check_available_qty', store=True)
    booked_qty      = fields.Float('Booked Qty', compute='check_available_qty', store=True)
    available_qty   = fields.Float('Available Qty (Kg)', compute='check_available_qty', store=True)
    lot_reserved_ids= fields.One2many('lot.reserved', 'lot_id', string='SO Line Reserved')
#     sale_order_line_ids = fields.One2many('sale.order.line','')
    #quant_ids
    
class LotReserved(models.Model):
    _name   = 'lot.reserved'
    
    sale_line_id = fields.Many2one('sale.order.line', string='SO Line',ondelete='cascade')
    lot_id       = fields.Many2one('stock.production.lot', string='Lot')
    
    
    
    