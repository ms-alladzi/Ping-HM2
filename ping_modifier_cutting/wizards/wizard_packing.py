from odoo import models, fields, api, _


class PackingWizz(models.TransientModel):
    _name = 'packing.wizz'
    
    name    = fields.Char(string='Name', required=True)
    cutting_id      = fields.Many2one('material.cutting',string='Cutting', required=True)
    product_id      = fields.Many2one('product.product',string='Product Packing', required=True)
    cutting_line    = fields.Many2many('material.cutting.line', 'cutting_line_id',string="Cutting Line")
    sale_id         = fields.Many2one('sale.order', string='Sale Order', readonly=True)
    cutting_date    = fields.Date(string="Cutting Date", default=lambda self: fields.Date.today())
    
    #SO Related
    so_partner_id           = fields.Many2one('res.partner', related='sale_id.partner_id', string='Customer', readonly=True)
    so_name                 = fields.Char(related='sale_id.name', string='SO No.', readonly=True)
    
    
    @api.model
    def default_get(self, fields):
        res = super(PackingWizz, self).default_get(fields)
        cutting_id = self.env['material.cutting'].browse(self.env.context.get('active_id'))
        res.update({
            'sale_id'         : cutting_id.sale_id.id,
            })
        return res
    
    @api.multi
    def packing_process(self):
        active_id = self.env.context.get('active_id')
        for o in self:
            ##Insert Packing Cover
            packing_item_exist = self.env['packing.items'].search([('product_id','=',o.product_id.id),('cutting_id','=',o.cutting_id.id)])
            if packing_item_exist:
                packing_item_exist.write({'quantity_done' : packing_item_exist.quantity_done + 1})
            else:
                self.env['packing.items'].create({'product_id' : o.product_id.id, 'quantity_done': 1, 'cutting_id' : o.cutting_id.id})
            ##Insert Packing Items
            packing_product_id = self.env['packing.product'].create({'name' : o.name, 'cutting_id' : o.cutting_id.id})
            for l in o.cutting_line:
                l.write({'packing_product_id' : packing_product_id.id})
