# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import namedtuple
import json
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare
from odoo.addons.procurement.models import procurement
from odoo.exceptions import UserError
import math


class StockLocation(models.Model):
    _inherit = "stock.location"
    
    branch_id          = fields.Many2one('res.branch', string='Branch')

class Picking(models.Model):
    _inherit = "stock.picking"

    @api.depends('partner_id','partner_id.vendor_code','do_vendor_date','do_vendor_ref')
    @api.multi
    def _get_batch_name(self):
        batch_name = ''
        for record in self:
            partner_code    = record.partner_id.vendor_code or ''
            do_vendor_date  = (str(record.do_vendor_date).replace('-','').replace(':','').replace(' ',''))[2:] or ''
            do_vendor_ref   = (str(record.do_vendor_ref)[-6:]) or ''
            record.batch_name = partner_code + do_vendor_date + do_vendor_ref

    @api.multi
    def _get_invoice_status(self):
        status = ''
        for picking in self:
            if picking.sale_id.invoice_ids:
                status = 'paid'
            for inv in picking.sale_id.invoice_ids:
                if inv.state !='paid':
                    status = 'Not Paid'
            picking.invoice_status = status

    @api.multi
    def _get_qty_summary(self):
        for picking in self:
            qty_summary_dict = {'roll': 0, 'roll_kg': 0.0, 'piece': 0, 'piece_kg': 0.0}
            for pack in picking.pack_operation_product_ids:
                for lot in pack.pack_lot_ids:
                    if lot.lot_id.type=='roll':
                        qty_summary_dict['roll'] += 1 
                        qty_summary_dict['roll_kg'] += lot.qty
                        #qty_summary_dict['roll_kg'] += pack.qty_done
                    elif lot.lot_id.type=='piece':
                        qty_summary_dict['piece'] += 1 
                        qty_summary_dict['piece_kg'] += lot.qty
                        #qty_summary_dict['piece_kg'] += pack.qty_done
                    else:
                        qty_summary_dict['roll'] += 1 
                        qty_summary_dict['roll_kg'] += lot.qty
                        
            picking.qty_summary = """Roll   : %s (%skg)\nPiece : %s (%skg)""" % (str(qty_summary_dict['roll']), str(qty_summary_dict['roll_kg']), 
                                                                         str(qty_summary_dict['piece']), str(qty_summary_dict['piece_kg']))

    #Columns
    do_vendor_date  = fields.Date(string='DO Vendor Date')
    do_vendor_ref   = fields.Char(string='DO Vendor No.')
    batch_name      = fields.Char(string='Batch Number', store=True, compute='_get_batch_name')
    invoice_status  = fields.Char(string='Invoice Status', compute='_get_invoice_status')
    qty_summary     = fields.Text(string='Summary Qty', compute='_get_qty_summary')
    count_print_internalmove   = fields.Integer(string='Count Print Internal Move')
    count_print_goodsreceive   = fields.Integer(string='Count Print Goods Receive')
    count_print_pengambilan     = fields.Integer(string='Count Print Pengambilan')
    count_print_deliveryorder   = fields.Integer(string='Count Print Delivery Order')
    count_print_retur           = fields.Integer(string='Count Print Retur')

    @api.multi
    def func_count_print_internalmove(self):
        count_print_internalmove = self.count_print_internalmove + 1
        self.write({'count_print_internalmove' : count_print_internalmove})
        return self.count_print_internalmove

    @api.multi
    def func_count_print_goodsreceive(self):
        count_print_goodsreceive = self.count_print_goodsreceive + 1
        self.write({'count_print_goodsreceive' : count_print_goodsreceive})
        return self.count_print_goodsreceive
    
    @api.multi
    def func_count_print_pengambilan(self):
        count_print_pengambilan = self.count_print_pengambilan + 1
        self.write({'count_print_pengambilan' : count_print_pengambilan})
        return self.count_print_pengambilan
    
    @api.multi
    def func_count_print_deliveryorder(self):
        count_print_deliveryorder = self.count_print_deliveryorder + 1
        self.write({'count_print_deliveryorder' : count_print_deliveryorder})
        return self.count_print_deliveryorder

    @api.multi
    def func_count_print_retur(self):
        count_print_retur = self.count_print_retur + 1
        self.write({'count_print_retur' : count_print_retur})
        return self.count_print_retur
    
    def _create_lots_for_picking(self):
        Lot = self.env['stock.production.lot']
        for pack_op_lot in self.mapped('pack_operation_ids').mapped('pack_lot_ids'):
            if not pack_op_lot.lot_id:
                lot = Lot.create({'name': pack_op_lot.lot_name, 'receive_date': self.min_date, 'batch_name': pack_op_lot.operation_id.picking_id.batch_name, 'product_id': pack_op_lot.operation_id.product_id.id})
                pack_op_lot.write({'lot_id': lot.id})
        # TDE FIXME: this should not be done here
        self.mapped('pack_operation_ids').mapped('pack_lot_ids').filtered(lambda op_lot: op_lot.qty == 0.0).unlink()
    create_lots_for_picking = _create_lots_for_picking
    
    @api.multi
    def do_new_transfer(self):
        for picking in self:
            if picking.sale_id and picking.picking_type_id.code=='outgoing':
                if picking.invoice_status != 'paid':
                    raise UserError(_('Can not Process until Invoice Paid'))
            #Check Estimate Roll vs Actual Roll
            for pack in picking.pack_operation_product_ids:
                if pack.product_id.tracking=='lot' and pack.estimate_qty_roll != pack.count_qty_lot and picking.picking_type_code=='incoming':
                    raise UserError(_('Total S/N must : %s' % str(pack.estimate_qty_roll)))
        res = super(Picking, self).do_new_transfer()
        return res
    
    @api.multi
    def do_transfer(self):
        for picking in self:
            if picking.sale_id:
                if picking.invoice_status != 'paid':
                    raise UserError(_('Can not Process until Invoice Paid'))
        res = super(Picking, self).do_transfer()
        return res

    @api.multi
    def action_done(self):
        for picking in self:
            if picking.sale_id:
                if picking.invoice_status != 'paid':
                    raise UserError(_('Can not Process until Invoice Paid'))
        res = super(Picking, self).action_done()
        return res

class StockMove(models.Model):
    _inherit = 'stock.move'
    
    #Columns
    #internal_move_id         = fields.Many2one('internal.move', string='Internal Move')
    
    
    
    @api.multi
    def assign_picking(self): 
        """ Try to assign the moves to an existing picking that has not been
        reserved yet and has the same procurement group, locations and picking
        type (moves should already have them identical). Otherwise, create a new
        picking to assign them to. """
        Picking = self.env['stock.picking']
        for move in self:
            recompute = False
            picking = Picking.search([
                ('group_id', '=', move.group_id.id),
                ('location_id', '=', move.location_id.id),
                ('location_dest_id', '=', move.location_dest_id.id),
                ('picking_type_id', '=', move.picking_type_id.id),
                ('printed', '=', False),
                ('state', 'in', ['draft', 'confirmed', 'waiting', 'partially_available', 'assigned'])], limit=1)
            if not picking:
                recompute = True
                picking = Picking.create(move._get_new_picking_values())
            move.write({'picking_id': picking.id})

            # If this method is called in batch by a write on a one2many and
            # at some point had to create a picking, some next iterations could
            # try to find back the created picking. As we look for it by searching
            # on some computed fields, we have to force a recompute, else the
            # record won't be found.
            if recompute:
                move.recompute()
        return True

class StockPackOperation(models.Model):
    _inherit = 'stock.pack.operation'
    
    #Columns
    count_print_packbarcode   = fields.Integer(string='Count Print Pack Barcode')
    color_name      = fields.Many2one('product.color','Color',readonly=True, related="product_id.color_name")

    @api.multi
    def func_count_print_packbarcode(self):
        count_print_packbarcode = self.count_print_packbarcode + 1
        self.write({'count_print_packbarcode' : count_print_packbarcode})
        return self.count_print_packbarcode
    
    @api.multi
    def get_pack_qty(self):
        estimate_qty_roll = 0
        for pack in self:
            estimate_qty_roll       = math.ceil(pack.product_qty / pack.product_id.vendor_kg_roll)
            pack.estimate_qty_roll  = estimate_qty_roll
            count_qty_lot       = len(pack.pack_lot_ids)
            pack.count_qty_lot  = count_qty_lot
            
    @api.onchange('pack_lot_ids')
    def onchange_pack_lot_ids(self):
        print "xxxx-.>>", int(len(self.pack_lot_ids)) ,'vs', self.estimate_qty_roll
        if int(len(self.pack_lot_ids)) > self.estimate_qty_roll:
            raise UserError(_('Total S/N must : %s') % (self.estimate_qty_roll))
        
    #Columns
    estimate_qty_roll     = fields.Integer(string='Estimate Roll', compute='get_pack_qty')
    count_qty_lot         = fields.Integer(string='Total S/N', compute='get_pack_qty')
    item_checked          = fields.Boolean(string='Checked')
    
    @api.multi
    def print_pack_barcode(self):
#         self.filtered(lambda s: s.state == 'draft').write({'state': 'sent'})
        return self.env['report'].get_action(self, 'ping_modifier_cutting.report_pack_operation_ping')
    
class StockPackOperationLot(models.Model):
    _inherit = 'stock.pack.operation.lot'
    
    @api.model
    def _get_lot_number(self):
        print "### _get_number###", self
        new_lot_number = 'R'+str(fields.Datetime.now()).replace('-','').replace(':','').replace(' ','')
        #Make it Delay
        time.sleep(1)
        return new_lot_number
    
    @api.model
    def _get_batch_number(self):
        print "### _get_number###"
        new_lot_number = 'R'+str(fields.Datetime.now()).replace('-','').replace(':','').replace(' ','')
        return new_lot_number
    
    lot_name    = fields.Char('Lot/Serial Number', default=_get_lot_number)
#     batch_name  = fields.Char('Batch Number', default=_get_lot_number)
    
class ProcurementOrder(models.Model):
    _inherit = "procurement.order"
    
    #Columns
    restrict_lot_id     = fields.Many2one('stock.production.lot', string='Lot / SN')
    
    def _get_stock_move_values(self):
        print  "### _get_stock_move_values ###"
        ''' Returns a dictionary of values that will be used to create a stock move from a procurement.
        This function assumes that the given procurement has a rule (action == 'move') set on it.

        :param procurement: browse record
        :rtype: dictionary
        '''
        group_id = False
        if self.rule_id.group_propagation_option == 'propagate':
            group_id = self.group_id.id
        elif self.rule_id.group_propagation_option == 'fixed':
            group_id = self.rule_id.group_id.id
        date_expected = (datetime.strptime(self.date_planned, DEFAULT_SERVER_DATETIME_FORMAT) - relativedelta(days=self.rule_id.delay or 0)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        # it is possible that we've already got some move done, so check for the done qty and create
        # a new move with the correct qty
        qty_done = sum(self.move_ids.filtered(lambda move: move.state == 'done').mapped('product_uom_qty'))
        qty_left = max(self.product_qty - qty_done, 0)
        
        print "self---->", self, self.rule_id, self.rule_id.location_src_id, self.location_id
        
        #raise UserError(_('XXX'))
        
        return {
            'name': self.name[:2000],
            'company_id': self.rule_id.company_id.id or self.rule_id.location_src_id.company_id.id or self.rule_id.location_id.company_id.id or self.company_id.id,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom.id,
            'product_uom_qty': qty_left,
            'restrict_lot_id': self.restrict_lot_id.id,
            'partner_id': self.rule_id.partner_address_id.id or (self.group_id and self.group_id.partner_id.id) or False,
            'location_id': self.sale_line_id.pickup_location_id.id or self.rule_id.location_src_id.id,
            'location_dest_id': self.location_id.id,
            'move_dest_id': self.move_dest_id and self.move_dest_id.id or False,
            'procurement_id': self.id,
            'rule_id': self.rule_id.id,
            'procure_method': self.rule_id.procure_method,
            'origin': self.origin,
            'picking_type_id': self.rule_id.picking_type_id.id,
            'group_id': group_id,
            'route_ids': [(4, route.id) for route in self.route_ids],
            'warehouse_id': self.rule_id.propagate_warehouse_id.id or self.rule_id.warehouse_id.id,
            'date': date_expected,
            'date_expected': date_expected,
            'propagate': self.rule_id.propagate,
            'priority': self.priority,
        }