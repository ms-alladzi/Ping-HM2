from datetime import datetime
from dateutil import relativedelta
import time

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.addons.procurement.models import procurement
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round, float_is_zero

# from odoo import api, fields, models
# from odoo.tools.float_utils import float_compare, float_round
# from odoo.tools.translate import _
# from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
# from odoo.exceptions import UserError
# 
# import logging


class MaterialCutting(models.Model):
    _name = 'material.cutting'
    _order= 'name desc'
    
    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('material.cutting') or _('New')
        if values['sale_id']:
            sale_id = self.env['sale.order'].browse([values['sale_id']])
            if sale_id.partner_id.membership_product_id:
                cutting_order_code = sale_id.partner_id.membership_product_id.membership_cutting_sequence
            else:
                cutting_order_code = 'Z'
        else:
            cutting_order_code = 'Z'
        values['cutting_order_sequence']    = cutting_order_code + values['name'] 
        if not values.get('procurement_group_id'):
            values['procurement_group_id'] = self.env["procurement.group"].create({'name': values['name']}).id
        cutting_order = super(MaterialCutting, self).create(values)
        return cutting_order
    
    @api.multi
    #@api.depends('move_state','without_cutting')
    def _get_packing_netto(self):
        for o in self:
            netto = 0.0
            for lcut in o.move_cutting_ids:
                netto += lcut.quantity_done
                print "netto--->", netto
            o.netto_weight = netto
    
    @api.multi
    def dummy_button(self):
        return True
    
    @api.multi
    @api.depends('move_material_raw_ids.state', 'move_material_raw_ids.partially_available')
    def _compute_availability(self):
        for order in self:
            if not order.move_material_raw_ids:
                order.availability = 'none'
                continue
#             if order.bom_id.ready_to_produce == 'all_available':
#                 order.availability = any(move.state not in ('assigned', 'done', 'cancel') for move in order.move_raw_ids) and 'waiting' or 'assigned'
            partial_list = [x.partially_available and x.state in ('waiting', 'confirmed', 'assigned') for x in order.move_material_raw_ids]
            assigned_list = [x.state in ('assigned', 'done', 'cancel') for x in order.move_material_raw_ids]
            order.availability = (all(assigned_list) and 'assigned') or (any(partial_list) and 'partially_available') or 'waiting'
    
    def _get_return_move_count(self):
        for order in self:
            order.return_move_count = len(order.return_picking_ids)
    
    #Columns
    name        = fields.Char(string='Reference', required=True, readonly=True, default='New')
    cutting_order_sequence        = fields.Char(string='Cutting Order Seq', required=False, readonly=True)
    date        = fields.Date(string='Date', required=True)
    sale_id     = fields.Many2one('sale.order', string='Sale Order')
    move_transformation_ids         = fields.One2many('material.transformation', 'transformation_cutting_id', string='Transformations')
    move_cutting_ids                = fields.One2many('material.cutting.line', 'cutting_id', string='Cutting')
    
    move_material_raw_ids           = fields.One2many('stock.move', 'raw_material_cutting_id', domain=[('scrapped', '=', False)], string='Raw Materials', oldname='move_lines',)
    move_material_finished_ids      = fields.One2many('stock.move', 'cutting_id', domain=[('scrapped', '=', False)], string='Finished Materials')
    
    procurement_group_id = fields.Many2one(
        'procurement.group', 'Procurement Group',
        copy=False)
    company_id      = fields.Many2one('res.company', 'Company', required=True, index=True,default=lambda self: self.env.user.company_id.id)
    branch_id       = fields.Many2one('res.branch', 'Branch', required=True, index=True,default=lambda self: self.env.user.branch_id.id)
    operator_id     = fields.Many2one('cutting.operator', 'Operator')
    
    state = fields.Selection([
        ('draft', 'Planned'),
        ('start', 'Started'),
        ('finish', 'Finished'),
        ('cancel', 'Cancelled')], string='State',
        copy=False, default='draft', track_visibility='onchange')
    
    availability = fields.Selection([
        ('assigned', 'Available'),
        ('partially_available', 'Partially Available'),
        ('waiting', 'Waiting'),
        ('none', 'None')], string='Availability',
        compute='_compute_availability', store=True)
    
    packing_items_ids       = fields.One2many('packing.items', 'cutting_id', string='Packing Items')
    packing_product_ids     = fields.One2many('packing.product', 'cutting_id', string='Packing List')
    netto_weight            = fields.Float(string='Netto Weight', compute='_get_packing_netto')
    bruto_weight            = fields.Float(string='Bruto Weight')
    return_picking_ids      = fields.Many2many('stock.picking', string="Return Picking")
    return_move_count       = fields.Integer(string='Return Move Count', compute='_get_return_move_count')
    
    @api.multi
    def start_cutting(self):
        self.sale_id.write({'state' : 'cutting_process'})
        self.write({'state' : 'start'})
        
    @api.multi
    def finish_cutting(self):
        #Create SO Line
        for lpack in self.packing_items_ids:
            self.env['sale.order.line'].create({'product_id' : lpack.product_id.id, 
                                                'product_uom_qty' : lpack.quantity_done, 
                                                'type' : 'other',
                                                'cutting' : 'no',
                                                'order_id': self.sale_id.id})
        if not self.packing_product_ids:
            raise UserError(_('Please Finished Your Packaged First'))
        self.sale_id.action_confirm()
        self.sale_id.action_invoice_create()
        self.write({'state' : 'finish'})
    
    @api.multi
    def action_assign(self):
        for production in self:
            move_to_assign = production.move_material_raw_ids.filtered(lambda x: x.state in ('confirmed', 'waiting', 'assigned'))
            move_to_assign.action_assign()
        return True
    
    @api.multi
    def open_packing(self):
        view = self.env.ref('ping_modifier_cutting.view_packing_wizz_form')
#         view = self.env.ref('ping_modifier_cutting.view_searching_product_wizz_form')
#         wiz = self.env['change.dest.location'].create({'location_dest_id': self.location_dest_id.id,
#                                                        'picking_id' : self.id})
        # TDE FIXME: a return in a loop, what a good idea. Really.
        return {
            'name': _('Packing'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'packing.wizz',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            #'res_id': wiz.id,
            #'context': self.env.context,
            'context': {'default_cutting_id': self.id}
        }
    
    @api.multi
    def get_product_item_pack(self):
        for o in self:
            product_name = ""
            for pack in o.packing_product_ids:
                for cut_line_id in pack.lines:
                    product_name = (product_name and product_name +"; "+cut_line_id.product_id.name) or cut_line_id.product_id.name
        return product_name 

    @api.multi
    def get_pack_number(self):
        for o in self:
            packing_name = ""
            for pack in o.packing_product_ids:
                packing_name = (packing_name and packing_name +"; "+pack.name) or pack.name
        return packing_name 
    
    @api.multi
    def action_view_return_move(self):
        return_picking = self.mapped('return_picking_ids')
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        if len(return_picking) >= 1:
            action['domain'] = [('id', 'in', return_picking.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
    
class MaterialTransformation(models.Model):
    _name = 'material.transformation'
    
    lot_id          = fields.Many2one('stock.production.lot', 'Lot Product')
    quantity_done   = fields.Float(string='Quantity Done')
    transformation_cutting_id       = fields.Many2one('material.cutting', string='Material Cutting',ondelete='cascade')
    move_id         = fields.Many2one('stock.move', string='Move')
    product_id = fields.Many2one('product.product', 'Product',readonly=True, related="lot_id.product_id")
    stock_qty = fields.Float('Stock Qty',readonly=True)
    move_state = fields.Selection([('draft','New'),('cancel','Cancelled'),('waiting','Waiting Another Move'),
                                   ('confirmed','Waiting Availability'),('assigned','Available'),('done','Done')],
                                   'State',readonly=True, related="move_id.state")
    sale_line_id    = fields.Many2one('sale.order.line', string='Sale Line ID')
    
    @api.multi
    def check_transformation(self):
        move_obj = self.env['stock.move']
        for o in self:
            if o.transformation_cutting_id.state != 'start':
                raise UserError(_('Please Click Start Button First.'))
            if not o.move_id:
                move_lot_ids = []
                scrap_qty = o.lot_id.stock_qty - o.quantity_done
                if scrap_qty < 0.0:
                    raise UserError(_('You can not Process Qty Minus.')) 
                elif scrap_qty > 0.51:
                    print "scrap_qty--->", float(scrap_qty)
                    raise UserError(_('Max. Transformation = 0,5 Kg'))
                move_lot_ids.append((0,0,{'lot_id': o.lot_id.id,'quantity': scrap_qty}))
                
                vals = {'origin'        : o.transformation_cutting_id.name or "",
                        'name'          : o.lot_id.product_id.name or "",
                        'product_id'    : o.lot_id.product_id.id,
                        'ordered_qty'   : scrap_qty,
                        #'product_qty'   : o.quantity_done,
                        'product_uom_qty':scrap_qty ,
                        'product_uom'   : o.lot_id.product_id.uom_id.id,
                        'price_unit'    : o.lot_id.product_id.standard_price,
                        'location_id'   : o.transformation_cutting_id.branch_id.transformation_loc_src_id.id or o.transformation_cutting_id.company_id.transformation_loc_src_id.id,
                        'location_dest_id'   : o.transformation_cutting_id.branch_id.scrap_loc_dst_id.id or o.transformation_cutting_id.company_id.scrap_loc_dst_id.id,
                        'state'         : 'draft',
                        'active_move_lot_ids' : move_lot_ids,
                        'restrict_lot_id'     : o.lot_id.id,
                        #'transformation_cutting_id' : o.id,
                        }
                print "scrap_qty---->", vals
                move = move_obj.create(vals)
                move.action_confirm()
                move.action_assign()
                #move.action_done()
                o.write({'move_id' : move.id})
                #raise UserError(_('OK..'))
            else:
                o.move_id.action_assign()
                
    @api.multi
    def process_transformation_test(self):
        cutting_line_obj = self.env['material.cutting.line']
        for o in self:
            ##Change Name S/N Roll-> Ecer
            piece_name = o.lot_id.name
            if o.lot_id.type=='roll':
                if o.lot_id.name[0] in ['R','r']:
                    piece_name = 'E'+o.lot_id.name[1:]
                else:
                    piece_name = 'E'+o.lot_id.name
            o.lot_id.write({'name': piece_name, 'type' : 'piece'})
    
    
    
    @api.multi
    def process_transformation(self):
        cutting_line_obj = self.env['material.cutting.line']
        for o in self:
            o.move_id.action_done()
             ##Change Name S/N Roll-> Ecer
            piece_name = o.lot_id.name
            if o.lot_id.type=='roll':
                if o.lot_id.name[0] in ['R','r']:
                    piece_name = 'E'+o.lot_id.name[1:]
                else:
                    piece_name = 'E'+o.lot_id.name
            o.lot_id.write({'name': piece_name, 'type' : 'piece'})
            
        #Create Cutting Line
        
#         vals_cutting = [(0,0, {'lot_id' : o.lot_id.id, 'stock_qty': o.quantity_done, 'quantity_order_related': o.sale_line_id.quantity_order,
#                         'cutting_id' : o.transformation_cutting_id.id, 'sale_line_id': o.sale_line_id.id, 
#                         'transformation_id' : o.id,})]
#         
#         print "vals_cutting---->", vals_cutting
#         
#         o.transformation_cutting_id.write({'move_cutting_ids': vals_cutting})
        
        vals_cutting = {'src_lot_id' : o.lot_id.id, 'lot_id' : o.lot_id.id, 'stock_qty': o.quantity_done, 'quantity_order_related': o.sale_line_id.quantity_order,
                        #'quantity_done' : o.sale_line_id.quantity_order ,
                        'cutting_id' : o.transformation_cutting_id.id, 'sale_line_id': o.sale_line_id.id, 
                        'transformation_id' : o.id,}
        cutting_line_obj.create(vals_cutting)
        
        return {
                'type': 'ir.actions.act_window',
                'name': _('Cutting'),
                'res_model': 'material.cutting',
                'view_type' : 'form',
                'view_mode' : 'form,tree',
                'res_id': o.transformation_cutting_id.id,
                #'view_id' : view_id,
                'target' : 'current',
                #'nodestroy' : True,
            }
        
class MaterialCuttingLine(models.Model):
    _name = 'material.cutting.line'
    
    @api.one
    @api.constrains('flag_2','flag_3')
    def _check_flag_2_3x(self):
        # This constraint could possibly underline flaws in bank statement import (eg. inability to
        # support hacks such as using dummy transactions to give additional informations)
        if self.flag_2 == True and self.flag_3 == True:
            raise UserError(_('You can\'t Select Flag 2 & 3 in same time.'))
    
    @api.multi
    @api.depends('move_state','without_cutting')
    def _get_packing_status(self):
        for o in self:
            if o.move_state=='done':
                o.packing_status = 'ready'
            if o.without_cutting:
                o.packing_status = 'ready'
            
    
    src_lot_id      = fields.Many2one('stock.production.lot', 'Source Lot Product')
    lot_id          = fields.Many2one('stock.production.lot', 'Lot Product')
    quantity_done   = fields.Float(string='Quantity Done')
    cutting_id      = fields.Many2one('material.cutting', string='Material Cutting')
    move_id         = fields.Many2one('stock.move', string='Move')
    move_ids        = fields.One2many('stock.move','cutting_line_id', string='Moves')
    
    product_id = fields.Many2one('product.product', 'Product',readonly=True, related="lot_id.product_id")
    stock_qty = fields.Float('Stock Qty',readonly=True)
    move_state = fields.Selection([('draft','New'),('cancel','Cancelled'),('waiting','Waiting Another Move'),
                                   ('confirmed','Waiting Availability'),('assigned','Available'),('done','Done')],
                                   'State',readonly=True, related="move_id.state")
    sale_line_id    = fields.Many2one('sale.order.line', string='Sale Line ID')
    transformation_id    = fields.Many2one('material.transformation', string='Transformation',ondelete='cascade')
    quantity_order_related    = fields.Float(string='Quantity Order')
    packing_status  = fields.Selection([('ready','Ready to Pack')], compute='_get_packing_status')
    without_cutting = fields.Boolean(string='Without Cutting') 
    packing_product_id    = fields.Many2one('packing.product', string='Packing')
    return_move_id  = fields.Many2one('stock.move', string='Move')
    
    ##Boolean
    flag_1      = fields.Boolean(string='Flag 1', help="'kesalahan cutting' fungsinya agar bisa menginput qty done walau over/below toleransi")
    flag_2      = fields.Boolean(string='Flag 2', help="'delivery order' fungsinya untuk mengirim hasil cutting ke warehouse yang sesuai (finish good ecer)")
    flag_3      = fields.Boolean(string='Flag 3', help="'delivery to warehouse kesalahan cutting' fungsinya untuk mengirim kesalahan cutting ke warehouse khusus ")
    
    @api.multi
    def createNew_lot(self, product_id, lot_id):
        vals = {'name'          : 'E'+str(fields.Datetime.now()).replace('-','').replace(':','').replace(' ',''),
                'batch_name'    : lot_id.batch_name or '',
                'product_id'    : product_id,
                'type'          : 'piece'}
        new_lot = self.env['stock.production.lot'].create(vals)
        return new_lot
    
    @api.multi
    def check_cutting(self):
        move_obj = self.env['stock.move']
        for o in self:
            if o.cutting_id.state != 'start':
                raise UserError(_('Please Click Start Button First.'))
            #Check Toloransi
            if o.quantity_done <= 0.0:
                raise UserError(_('Quantity Done must more than 0 Kg'))
            if o.quantity_done > o.lot_id.stock_qty:
                raise UserError(_('Available Stock : %s, Qty Done must less than Available Stock') % (o.lot_id.stock_qty))
            #if (o.quantity_done - o.quantity_order_related) > 0.21 and (o.flag_1==False or o.flag_2==False or o.flag_3==False):
            if abs(o.quantity_done - o.quantity_order_related) > 0.21 and (o.flag_1==False and o.flag_2==False and o.flag_3==False):
                raise UserError(_('Max. & Min.Tolerance Cuttin = 0,2 Kg'))
            #Stock -> Virtual
            if not o.move_id:
                move_lot_ids = []
                move_lot_ids.append((0,0,{'lot_id': o.lot_id.id,'quantity': o.quantity_done}))
                vals = {'origin'        : o.cutting_id.name or "",
                        'name'          : o.lot_id.product_id.name or "",
                        'product_id'    : o.lot_id.product_id.id,
                        'ordered_qty'   : o.quantity_done,
                        #'product_qty'   : o.quantity_done,
                        'product_uom_qty':o.quantity_done ,
                        'product_uom'   : o.lot_id.product_id.uom_id.id,
                        'price_unit'    : o.lot_id.product_id.standard_price,
                        'location_id'           : o.cutting_id.branch_id.transformation_loc_src_id.id or o.cutting_id.company_id.transformation_loc_src_id.id,
                        'location_dest_id'      : o.cutting_id.branch_id.cutting_loc_src_id.id or o.cutting_id.company_id.cutting_loc_src_id.id,
                        'state'                 : 'draft',
                        'active_move_lot_ids'   : move_lot_ids,
                        'restrict_lot_id'     : o.lot_id.id,
                        #'transformation_cutting_id' : o.id,
                        }
                print "scrap_qty---->", vals
                move = move_obj.create(vals)
                move.action_confirm()
                move.action_assign()
                o.write({'move_id' : move.id})
            else:
                o.move_id.action_confirm()
                o.move_id.action_assign()
            
    @api.multi
    def process_cutting(self):
        move_obj = self.env['stock.move']
        for o in self:
            if o.cutting_id.state != 'start':
                raise UserError(_('Please Click Start Button First.'))
            #Check Toloransi
            if o.quantity_done <= 0.0:
                raise UserError(_('Quantity Done must more than 0 Kg'))
            if o.quantity_done > o.lot_id.stock_qty:
                raise UserError(_('Available Stock : %s, Qty Done must less than Available Stock') % (o.lot_id.stock_qty))
            #if (o.quantity_done - o.quantity_order_related) > 0.21 and (o.flag_1==False or o.flag_2==False or o.flag_3==False):
            if abs(o.quantity_done - o.quantity_order_related) > 0.21 and (o.flag_1==False and o.flag_2==False and o.flag_3==False):
                raise UserError(_('Max. & Min.Tolerance Cuttin = 0,2 Kg'))

            #Stock -> Virtual
            if o.move_id:
                o.move_id.action_done()
            #Virtual -> Stock
            move_lot_ids = []
            old_lot = o.lot_id
            new_lot = self.createNew_lot(o.lot_id.product_id.id, o.lot_id)
            move_lot_ids.append((0,0,{'lot_id': new_lot.id,'quantity': o.quantity_done}))
            
            print "new_lot.id--->", new_lot, new_lot.id
            print "Avai Qty : ", o.lot_id.stock_qty
            
            #Finish Goods Special Location
            if o.flag_3==True:
                dest_cutting_loc_id = o.cutting_id.branch_id.cutting_loc_dst_special_id.id or o.cutting_id.company_id.cutting_loc_dst_special_id.id
            else:
                dest_cutting_loc_id = o.cutting_id.branch_id.cutting_loc_dst_id.id or o.cutting_id.company_id.cutting_loc_dst_id.id
            
            vals = {'origin'        : o.cutting_id.name or "",
                    'name'          : o.lot_id.product_id.name or "",
                    'product_id'    : o.lot_id.product_id.id,
                    'ordered_qty'   : o.quantity_done,
                    #'product_qty'   : o.quantity_done,
                    'product_uom_qty':o.quantity_done ,
                    'product_uom'   : o.lot_id.product_id.uom_id.id,
                    'price_unit'    : o.lot_id.product_id.standard_price,
                    'location_id'   : o.cutting_id.branch_id.cutting_loc_src_id.id or o.cutting_id.company_id.cutting_loc_src_id.id,
                    'location_dest_id'   : dest_cutting_loc_id, 
                    'state'         : 'draft',
                    #'active_move_lot_ids' : move_lot_ids,
                    'restrict_lot_id'     : new_lot.id,
                    'cutting_line_id'     : o.id,
                    'type'          : 'piece',
                    }
            print "scrap_qty---->", vals
            move = move_obj.create(vals)
            move.action_confirm()
            #move.action_assign()
            move.action_done()
            if o.sale_line_id:
                #Update Old Lot -> New Lot in SO Line
                sql_query = """UPDATE sale_line_lot_rel SET lot_id = %s WHERE lot_id = %s AND sale_line_id = %s"""
                params      = (str(new_lot.id),str(old_lot.id),str(o.sale_line_id.id),) 
                self.env.cr.execute(sql_query, params)
    
                #Update Old Lot -> New Lot in SO Line
                sql_query = """UPDATE lot_reserved SET lot_id = %s WHERE lot_id = %s AND sale_line_id = %s"""
                params      = (str(new_lot.id),str(old_lot.id),str(o.sale_line_id.id),) 
                self.env.cr.execute(sql_query, params)
                
                #Update Qty di SO Live base on Hasil Cutting
                o.sale_line_id.write({'product_uom_qty' : o.quantity_done})
                o.transformation_id.write({'lot_id' : new_lot.id})
                o.write({'lot_id' : new_lot.id})
                
                old_lot.check_available_qty()
                new_lot.check_available_qty()
    
    @api.multi
    def create_return(self):
        for cuttingline in self:
            if not cuttingline.src_lot_id:
                raise UserError(_("Lot doesn't Exist"))
            ##Create Picking Internal Move
            move_lot_ids = []
            return_picking_ids = []
            
            location_id         = cuttingline.cutting_id.branch_id.transformation_loc_src_id.id
            location_dest_id    = cuttingline.cutting_id.branch_id.return_transformation_loc_src_id.id
            
            picking_id = self.env['stock.picking'].create({
                    #'date'              : fields.Datetime.now(),
                    'origin'            : cuttingline.cutting_id.name,
                    'picking_type_id'   : cuttingline.cutting_id.branch_id.int_picking_type_id.id,
                    'company_id'        : cuttingline.cutting_id.company_id.id,
                    'branch_id'         : cuttingline.cutting_id.branch_id.id,
                    'location_id'       : location_id,
                    'location_dest_id'  : location_dest_id,
                    })
            #return_picking_ids.append((4, picking_id.id))
            
            cuttingline.cutting_id.write({'return_picking_ids': [(4, picking_id.id)]})
            print "## Picking Internal Move Created"
            #picking_location_dict[line_lot.location_id.id] = picking_id.id
            #internal_move_ids.append((4,picking_id.id))
            move_lot_ids.append((0,0,{'lot_id': cuttingline.src_lot_id.id, 'quantity': cuttingline.src_lot_id.stock_qty, 'quantity_done': cuttingline.src_lot_id.stock_qty}))
            
            return_move = self.env['stock.move'].create({
                        'name'          : "Return-"+ cuttingline.cutting_id.name +"("+ cuttingline.src_lot_id.name+")", 
                        'date'          : fields.Datetime.now(),
                        'date_expected' : fields.Datetime.now(),
                        'product_id'    : cuttingline.product_id.id,
                        'product_uom'   : cuttingline.product_id.uom_id.id,
                        'product_uom_qty': cuttingline.src_lot_id.stock_qty,
                        'location_id'       : location_id,
                        'location_dest_id'  : location_dest_id,
                        #'move_dest_id': self.procurement_ids and self.procurement_ids[0].move_dest_id.id or False,
                        #'procurement_id': self.procurement_ids and self.procurement_ids[0].id or False,
                        'company_id'        : cuttingline.cutting_id.company_id.id,
                        'origin'            : cuttingline.cutting_id.name,
                        'restrict_lot_id'   : cuttingline.src_lot_id.id,
                        'picking_id'        : picking_id.id
                        #'group_id': self.order_id.l.procurement_group_id.id,
                        #'propagate': False,#self.propagate,
                        #'lot_ids'           : move_lot_ids,
                        #'internal_move_id'  : internal_move_id.id,
                        #'active_move_lot_ids' : move_lot_ids,
                    })
            ###
            cuttingline.write({'return_move_id': return_move.id})
            return {
                'type': 'ir.actions.act_window',
                'name': _('Cutting'),
                'res_model': 'material.cutting',
                'view_type' : 'form',
                'view_mode' : 'form,tree',
                'res_id': cuttingline.cutting_id.id,
                #'view_id' : view_id,
                'target' : 'current',
                #'nodestroy' : True,
            }
            
class StockMove(models.Model):
    _inherit = 'stock.move'
    
    #Columns
    raw_material_cutting_id         = fields.Many2one('material.cutting', string='Material Cutting')
    cutting_id                      = fields.Many2one('material.cutting', string='Material Cutting')
    cutting_line_id                 = fields.Many2one('material.cutting.line', string='Material Cutting Line')
    is_done = fields.Boolean(
        'Done', compute='_compute_is_done',
        store=True,
        help='Technical Field to order moves')
    active_move_lot_ids = fields.One2many('stock.move.cutting.lots', 'move_id', string='Lots')
    
    @api.multi
    @api.depends('state')
    def _compute_is_done(self):
        for move in self:
            move.is_done = (move.state in ('done', 'cancel'))
            
    @api.multi
    def action_assign(self, no_prepare=False):
        res = super(StockMove, self).action_assign(no_prepare=no_prepare)
#         self.check_move_lots()
        return res

    @api.multi
    def check_move_lots(self):
        moves_todo = self.filtered(lambda x: x.move_material_raw_ids and x.state not in ('done', 'cancel'))
        return moves_todo.create_lots()
    
    @api.multi
    def action_done(self):
        production_moves = self.filtered(lambda move: (move.raw_material_cutting_id) and not move.scrapped)
        production_moves.move_validate()
        return super(StockMove, self-production_moves).action_done()
    
    @api.multi
    def move_validate(self):
        ''' Validate moves based on a production order. '''
        quant_obj = self.env['stock.quant']
        moves_todo = self.env['stock.move']
        moves_to_unreserve = self.env['stock.move']
        # Create extra moves where necessary
        
        for move in self:
            main_domain = [('qty', '>', 0)]
            preferred_domain = [('reservation_id', '=', move.id)]
            fallback_domain = [('reservation_id', '=', False)]
            fallback_domain2 = ['&', ('reservation_id', '!=', move.id), ('reservation_id', '!=', False)]
            preferred_domain_list = [preferred_domain] + [fallback_domain] + [fallback_domain2]
            rounding = move.product_id.uom_id.rounding
            for movelot in move.active_move_lot_ids:
                if float_compare(movelot.quantity, 0, precision_rounding=rounding) > 0:
                    if not movelot.lot_id:
                        raise UserError(_('You need to supply a lot/serial number.'))
                    qty = move.product_uom._compute_quantity(movelot.quantity, move.product_id.uom_id)
                    quants = quant_obj.quants_get_preferred_domain(qty, move, lot_id=movelot.lot_id.id, domain=main_domain, preferred_domain_list=preferred_domain_list)
                    self.env['stock.quant'].quants_move(quants, move, move.location_dest_id, lot_id = movelot.lot_id.id, owner_id=move.restrict_partner_id.id)
    
    @api.multi
    def action_assign(self, no_prepare=False): 
        print "###action_assign###"
        """ Checks the product type and accordingly writes the state. """
        # TDE FIXME: remove decorator once everything is migrated
        # TDE FIXME: clean me, please
        main_domain = {}

        Quant = self.env['stock.quant']
        Uom = self.env['product.uom']
        moves_to_assign = self.env['stock.move']
        moves_to_do = self.env['stock.move']
        operations = self.env['stock.pack.operation']
        ancestors_list = {}

        # work only on in progress moves
        moves = self.filtered(lambda move: move.state in ['confirmed', 'waiting', 'assigned'])
        moves.filtered(lambda move: move.reserved_quant_ids).do_unreserve()
        for move in moves:
            if move.location_id.usage in ('supplier', 'inventory', 'production'):
                print "move--->#1 :: ", move, move.location_id.usage
                moves_to_assign |= move
                # TDE FIXME: what ?
                # in case the move is returned, we want to try to find quants before forcing the assignment
                if not move.origin_returned_move_id:
                    continue
            # if the move is preceeded, restrict the choice of quants in the ones moved previously in original move
            ancestors = move.find_move_ancestors()
            if move.product_id.type == 'consu' and not ancestors:
                moves_to_assign |= move
                continue
            else:
                print "move--->ELSE :: ", move
                moves_to_do |= move

                # we always search for yet unassigned quants
                main_domain[move.id] = [('reservation_id', '=', False), ('qty', '>', 0)]

                ancestors_list[move.id] = True if ancestors else False
                if move.state == 'waiting' and not ancestors:
                    # if the waiting move hasn't yet any ancestor (PO/MO not confirmed yet), don't find any quant available in stock
                    main_domain[move.id] += [('id', '=', False)]
                elif ancestors:
                    main_domain[move.id] += [('history_ids', 'in', ancestors.ids)]

                # if the move is returned from another, restrict the choice of quants to the ones that follow the returned move
                if move.origin_returned_move_id:
                    main_domain[move.id] += [('history_ids', 'in', move.origin_returned_move_id.id)]
                for link in move.linked_move_operation_ids:
                    operations |= link.operation_id
            
            print "move--->", move, moves_to_do, main_domain
            
            #raise UserError(_('XXXX'))
        # Check all ops and sort them: we want to process first the packages, then operations with lot then the rest
        operations = operations.sorted(key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.pack_lot_ids and -1 or 0))
        for ops in operations:
            # TDE FIXME: this code seems to be in action_done, isn't it ?
            # first try to find quants based on specific domains given by linked operations for the case where we want to rereserve according to existing pack operations
            if not (ops.product_id and ops.pack_lot_ids):
                for record in ops.linked_move_operation_ids:
                    move = record.move_id
                    if move.id in main_domain:
                        qty = record.qty
                        domain = main_domain[move.id]
                        if qty:
                            quants = Quant.quants_get_preferred_domain(qty, move, ops=ops, domain=domain, preferred_domain_list=[])
                            Quant.quants_reserve(quants, move, record)
            else:
                lot_qty = {}
                rounding = ops.product_id.uom_id.rounding
                for pack_lot in ops.pack_lot_ids:
                    lot_qty[pack_lot.lot_id.id] = ops.product_uom_id._compute_quantity(pack_lot.qty, ops.product_id.uom_id)
                for record in ops.linked_move_operation_ids:
                    move_qty = record.qty
                    move = record.move_id
                    domain = main_domain[move.id]
                    for lot in lot_qty:
                        if float_compare(lot_qty[lot], 0, precision_rounding=rounding) > 0 and float_compare(move_qty, 0, precision_rounding=rounding) > 0:
                            qty = min(lot_qty[lot], move_qty)
                            quants = Quant.quants_get_preferred_domain(qty, move, ops=ops, lot_id=lot, domain=domain, preferred_domain_list=[])
                            Quant.quants_reserve(quants, move, record)
                            lot_qty[lot] -= qty
                            move_qty -= qty
        
        ####
        lot = move.active_move_lot_ids and move.active_move_lot_ids[0].lot_id.id
        if move.state != 'assigned' and lot and not self.env.context.get('reserve_only_ops'):
            
            qty_already_assigned = move.reserved_availability
            qty = move.product_qty - qty_already_assigned
#             quants = Quant.quants_get_preferred_domain(qty, move, lot_id=lot, domain=domain, preferred_domain_list=[])
            print "lot---->", lot
            print "move---->", move
            print "qty---->", qty
            print "move---->", move
            print "lot---->", lot
            print "main_domain[move.id]---->", main_domain
            quants = Quant.quants_get_preferred_domain(qty, move, lot_id=lot, domain=main_domain[move.id], preferred_domain_list=[])
            print "quants---->", quants
            Quant.quants_reserve(quants, move)
        ####

        # Sort moves to reserve first the ones with ancestors, in case the same product is listed in
        # different stock moves.
        for move in sorted(moves_to_do, key=lambda x: -1 if ancestors_list.get(x.id) else 0):
            print "##Masuk ELSE##"
            # then if the move isn't totally assigned, try to find quants without any specific domain
            if move.state != 'assigned' and not self.env.context.get('reserve_only_ops'):
                qty_already_assigned = move.reserved_availability
                qty = move.product_qty - qty_already_assigned

                quants = Quant.quants_get_preferred_domain(qty, move, domain=main_domain[move.id], preferred_domain_list=[])
                Quant.quants_reserve(quants, move)

        # force assignation of consumable products and incoming from supplier/inventory/production
        # Do not take force_assign as it would create pack operations
        if moves_to_assign:
            moves_to_assign.write({'state': 'assigned'})
        if not no_prepare:
            self.check_recompute_pack_op()
#         raise UserError(_('### XXX ###'))
            
    @api.multi
    def action_done(self):
        """ Process completely the moves given and if all moves are done, it will finish the picking. """
        self.filtered(lambda move: move.state == 'draft').action_confirm()

        Uom = self.env['product.uom']
        Quant = self.env['stock.quant']

        pickings = self.env['stock.picking']
        procurements = self.env['procurement.order']
        operations = self.env['stock.pack.operation']

        remaining_move_qty = {}

        for move in self:
            if move.picking_id:
                pickings |= move.picking_id
            remaining_move_qty[move.id] = move.product_qty
            for link in move.linked_move_operation_ids:
                operations |= link.operation_id
                pickings |= link.operation_id.picking_id

        # Sort operations according to entire packages first, then package + lot, package only, lot only
        operations = operations.sorted(key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.pack_lot_ids and -1 or 0))

        for operation in operations:

            # product given: result put immediately in the result package (if False: without package)
            # but if pack moved entirely, quants should not be written anything for the destination package
            quant_dest_package_id = operation.product_id and operation.result_package_id.id or False
            entire_pack = not operation.product_id and True or False

            # compute quantities for each lot + check quantities match
            lot_quantities = dict((pack_lot.lot_id.id, operation.product_uom_id._compute_quantity(pack_lot.qty, operation.product_id.uom_id)
            ) for pack_lot in operation.pack_lot_ids)

            qty = operation.product_qty
            if operation.product_uom_id and operation.product_uom_id != operation.product_id.uom_id:
                qty = operation.product_uom_id._compute_quantity(qty, operation.product_id.uom_id)
            if operation.pack_lot_ids and float_compare(sum(lot_quantities.values()), qty, precision_rounding=operation.product_id.uom_id.rounding) != 0.0:
                raise UserError(_('You have a difference between the quantity on the operation and the quantities specified for the lots. '))

            quants_taken = []
            false_quants = []
            lot_move_qty = {}

            prout_move_qty = {}
            for link in operation.linked_move_operation_ids:
                prout_move_qty[link.move_id] = prout_move_qty.get(link.move_id, 0.0) + link.qty

            # Process every move only once for every pack operation
            for move in prout_move_qty.keys():
                # TDE FIXME: do in batch ?
                move.check_tracking(operation)

                # TDE FIXME: I bet the message error is wrong
                if not remaining_move_qty.get(move.id):
                    raise UserError(_("The roundings of your unit of measure %s on the move vs. %s on the product don't allow to do these operations or you are not transferring the picking at once. ") % (move.product_uom.name, move.product_id.uom_id.name))

                if not operation.pack_lot_ids:
                    preferred_domain_list = [[('reservation_id', '=', move.id)], [('reservation_id', '=', False)], ['&', ('reservation_id', '!=', move.id), ('reservation_id', '!=', False)]]
                    quants = Quant.quants_get_preferred_domain(
                        prout_move_qty[move], move, ops=operation, domain=[('qty', '>', 0)],
                        preferred_domain_list=preferred_domain_list)
                    Quant.quants_move(quants, move, operation.location_dest_id, location_from=operation.location_id,
                                      lot_id=False, owner_id=operation.owner_id.id, src_package_id=operation.package_id.id,
                                      dest_package_id=quant_dest_package_id, entire_pack=entire_pack)
                else:
                    # Check what you can do with reserved quants already
                    qty_on_link = prout_move_qty[move]
                    rounding = operation.product_id.uom_id.rounding
                    for reserved_quant in move.reserved_quant_ids:
                        if (reserved_quant.owner_id.id != operation.owner_id.id) or (reserved_quant.location_id.id != operation.location_id.id) or \
                                (reserved_quant.package_id.id != operation.package_id.id):
                            continue
                        if not reserved_quant.lot_id:
                            false_quants += [reserved_quant]
                        elif float_compare(lot_quantities.get(reserved_quant.lot_id.id, 0), 0, precision_rounding=rounding) > 0:
                            if float_compare(lot_quantities[reserved_quant.lot_id.id], reserved_quant.qty, precision_rounding=rounding) >= 0:
                                qty_taken = min(reserved_quant.qty, qty_on_link)
                                lot_quantities[reserved_quant.lot_id.id] -= qty_taken
                                quants_taken += [(reserved_quant, qty_taken)]
                                qty_on_link -= qty_taken
                            else:
                                qty_taken = min(qty_on_link, lot_quantities[reserved_quant.lot_id.id])
                                quants_taken += [(reserved_quant, qty_taken)]
                                lot_quantities[reserved_quant.lot_id.id] -= qty_taken
                                qty_on_link -= qty_taken
                    lot_move_qty[move.id] = qty_on_link

                remaining_move_qty[move.id] -= prout_move_qty[move]

            # Handle lots separately
            if operation.pack_lot_ids:
                # TDE FIXME: fix call to move_quants_by_lot to ease understanding
                self._move_quants_by_lot(operation, lot_quantities, quants_taken, false_quants, lot_move_qty, quant_dest_package_id)

            # Handle pack in pack
            if not operation.product_id and operation.package_id and operation.result_package_id.id != operation.package_id.parent_id.id:
                operation.package_id.sudo().write({'parent_id': operation.result_package_id.id})

        # Check for remaining qtys and unreserve/check move_dest_id in
        move_dest_ids = set()
        for move in self:
            if float_compare(remaining_move_qty[move.id], 0, precision_rounding=move.product_id.uom_id.rounding) > 0:  # In case no pack operations in picking
                move.check_tracking(False)  # TDE: do in batch ? redone ? check this

                preferred_domain_list = [[('reservation_id', '=', move.id)], [('reservation_id', '=', False)], ['&', ('reservation_id', '!=', move.id), ('reservation_id', '!=', False)]]
                quants = Quant.quants_get_preferred_domain(
                    remaining_move_qty[move.id], move, domain=[('qty', '>', 0)],
                    preferred_domain_list=preferred_domain_list)
                Quant.quants_move(
                    quants, move, move.location_dest_id,
                    lot_id=move.restrict_lot_id.id, owner_id=move.restrict_partner_id.id)

            # If the move has a destination, add it to the list to reserve
            if move.move_dest_id and move.move_dest_id.state in ('waiting', 'confirmed'):
                move_dest_ids.add(move.move_dest_id.id)

            if move.procurement_id:
                procurements |= move.procurement_id

            # unreserve the quants and make them available for other operations/moves
            move.quants_unreserve()

        # Check the packages have been placed in the correct locations
        self.mapped('quant_ids').filtered(lambda quant: quant.package_id and quant.qty > 0).mapped('package_id')._check_location_constraint()

        # set the move as done
        self.write({'state': 'done', 'date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
        procurements.check()
        # assign destination moves
        if move_dest_ids:
            # TDE FIXME: record setise me
            self.browse(list(move_dest_ids)).action_assign()

        pickings.filtered(lambda picking: picking.state == 'done' and not picking.date_done).write({'date_done': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})

        return True
    
class StockMoveCuttingLots(models.Model):
    _name = 'stock.move.cutting.lots'
    _description = "Quantities to Process by lots"

    move_id         = fields.Many2one('stock.move', 'Move')
    
    raw_material_cutting_id         = fields.Many2one('material.cutting', string='Material Cutting')
    cutting_id                      = fields.Many2one('material.cutting', string='Material Cutting')
    
    
    lot_id = fields.Many2one(
        'stock.production.lot', 'Lot',
        domain="[('product_id', '=', parent.product_id)]")
    lot_produced_id = fields.Many2one('stock.production.lot', 'Finished Lot')
    lot_produced_qty = fields.Float(
        'Quantity Finished Product', digits=dp.get_precision('Product Unit of Measure'),
        help="Informative, not used in matching")
    quantity        = fields.Float('To Do', default=1.0, digits=dp.get_precision('Product Unit of Measure'))
    quantity_done = fields.Float('Done', digits=dp.get_precision('Product Unit of Measure'))
    
    product_id = fields.Many2one(
        'product.product', 'Product',
        readonly=True, related="move_id.product_id", store=True)
    done_cutting = fields.Boolean('Done for Work Order', default=True, help="Technical Field which is False when temporarily filled in in work order")  # TDE FIXME: naming
    done_move = fields.Boolean('Move Done', related='move_id.is_done', store=True)  # TDE FIXME: naming

class PackingItems(models.Model):
    _name = 'packing.items'
    
    product_id          = fields.Many2one('product.product', 'Product')
    quantity_done       = fields.Float('Done', digits=dp.get_precision('Product Unit of Measure'))
    cutting_id    = fields.Many2one('material.cutting', required=True)
    
class PackingProduct(models.Model):
    _name = 'packing.product'
    
    name            = fields.Char(string='Packing No.', required=True)
    cutting_id      = fields.Many2one('material.cutting', required=True)
    lines           = fields.One2many('material.cutting.line', 'packing_product_id', string='Lines')
    count_print_packing   = fields.Integer(string='Count Print Packing')

    @api.multi
    def func_count_print_packing(self):
        count_print_packing = self.count_print_packing + 1
        self.write({'count_print_packing' : count_print_packing})
        return self.count_print_packing
    
    @api.multi
    def print_packing_barcode(self):
#         self.filtered(lambda s: s.state == 'draft').write({'state': 'sent'})
        return self.env['report'].get_action(self, 'ping_modifier_cutting.report_barcode_packing_ping')


