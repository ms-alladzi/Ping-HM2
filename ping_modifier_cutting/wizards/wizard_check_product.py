from odoo import models, fields, api, _


class SearchingProductWizz(models.TransientModel):
    _name = 'searching.product.wizz'
    
    product_id      = fields.Many2one('product.product', string='Product', required=True)
    quantity        = fields.Float(string='Quantity', required=True)
    type            = fields.Selection([('roll','Roll'),('piece','Eceran'),('other','Other')], string='Type', required=True)
    cutting         = fields.Selection([('yes','Yes'),('no','No')], string='Cutting', required=True)
    
    #product_lot_ids1 = fields.Many2many('stock.production.lot', 'search_product_lot_rel1', 'wizzard_id', 'lot_id',string="Search Product Lots 1")
    product_lot_ids1    = fields.One2many('searching.product.line.wizz', 'wizz_id', 'Lines')
    see_more        = fields.Boolean(string="See More...")
    product_lot_ids2 = fields.Many2many('stock.production.lot', 'search_product_lot_rel2', 'wizzard_id', 'lot_id',string="Search Product Lots 2")
    see_more3        = fields.Boolean(string="See More...")
    product_lot_ids3 = fields.Many2many('stock.production.lot', 'search_product_lot_rel3', 'wizzard_id', 'lot_id',string="Search Product Lots 3")
    
    @api.onchange('product_id','quantity')
    def onchange_product(self):
        
        quantity_tolerance_min  = self.quantity - 0.9
        quantity_tolerance_max  = self.quantity + 0.9
        lot_obj = self.env['stock.production.lot']
        lot_ids1 = lot_obj.search([('product_id','=',self.product_id.id),('type','=','piece'),('available_qty','>=',quantity_tolerance_min),('available_qty','<=',quantity_tolerance_max)], order="batch_name,available_qty,name")
        lot_ids2 = lot_obj.search([('product_id','=',self.product_id.id),('type','=','piece'),('id','not in',lot_ids1.ids)], order="batch_name,available_qty,name")
        lot_ids3 = lot_obj.search([('product_id','=',self.product_id.id),('type','=','roll')], order="batch_name,available_qty,name")
        
#         print "lot_ids--->", lot_ids.ids
#         
#         for i in lot_ids:
#             print i
        product_lot_ids1 = [(0, 0, {'product_lot_id' : lot.id,
                                    }) for lot in lot_ids1]
        
        
        
        product_lot_ids2 = [(4, lot.id, None) for lot in lot_ids2]
        product_lot_ids3 = [(4, lot.id, None) for lot in lot_ids3]
          
        self.product_lot_ids1 = product_lot_ids1
        self.product_lot_ids2 = product_lot_ids2
        self.product_lot_ids3 = product_lot_ids3
        self.see_more         = False
        self.see_more3        = False
        
    @api.multi
    def process(self):
        active_id = self.env.context.get('active_id')
        print "active_id--->", active_id
        for o in self:
            for l1 in o.product_lot_ids1:
                print "l1----->", l1
                lost_ids = [(4, l1.id, None)]
                
            self.env['sale.order.line'].create({'product_id'            : l1.product_lot_id.product_id.id, 
                                                'quantity_order'        : o.quantity,
                                                'type'                  : o.type,
                                                'cutting'               : o.cutting,
                                                'sale_order_line_lots'  : lost_ids,
                                                'order_id'              : active_id})
            
        
class SearchingProductLine1Wizz(models.TransientModel):
    _name = 'searching.product.line.wizz'
    
    @api.one
    def _get_qty_batch(self):
        if not self.product_lot_id.batch_name:
            self.qty_batch = 1
        elif self.product_lot_id.type=='piece':
            self.qty_batch = 1
        else:
            sql_query   = """SELECT batch_name, COALESCE(COUNT(id),0.0) as count, COALESCE(SUM(available_qty),0.0) as available_qty FROM stock_production_lot 
                                WHERE batch_name is not null AND available_qty>0.0 AND type='roll' AND batch_name =%s GROUP BY batch_name"""
            params      = (str(self.product_lot_id.batch_name),)
            self.env.cr.execute(sql_query, params)
            result_group = self.env.cr.dictfetchall()
            if result_group:
                #self.qty_batch = result_group[0]['count']
                self.available_qty_show_only = result_group[0]['available_qty']
            else:
                self.qty_batch = 1
    
    selected        = fields.Boolean(string='Select')
    product_lot_id  = fields.Many2one('stock.production.lot', string='Product lot',readonly=True)
    batch_name      = fields.Char(related='product_lot_id.batch_name', readonly=True, copy=False)
    lot_name        = fields.Char(related='product_lot_id.name', readonly=True, copy=False)
    
    available_qty   = fields.Float(string='Available Qty (Kg)', related='product_lot_id.available_qty', readonly=True)
    location_id     = fields.Many2one('stock.location', string='Location', related='product_lot_id.location_id',readonly=True)
    wizz_id         = fields.Many2one('searching.product.wizz', string='Wizard',)
    wizz_sample_id  = fields.Many2one('sample.request.wizz', string='Wizard',)
    type            = fields.Selection([('1','1'),('2','2'),('3','3')], string='Type')
    sale_order_id         = fields.Many2one('sale.order.line', string='SO Live',)
    so_line_wizz_id       = fields.Many2one('sale.line.search.wizz', string='SO Live Wizard',)
    qty_batch       = fields.Integer(string="Qty", compute='_get_qty_batch', readonly=True)
    available_qty_show_only       = fields.Float(string="Available Qty (Kg)", compute="_get_qty_batch", readonly=True)
    