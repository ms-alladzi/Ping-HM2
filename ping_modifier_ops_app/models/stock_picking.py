# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _
import time
import math
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def write_vendor_data(self, vals):
        self.write(vals)
        return self.batch_name

    # List View - Receiving, Picking and Internal Transfer
    def get_picking_list(self, picking_type_id):
        data_list = []
        status_dict = {'draft': 'Draft', 'waiting': 'Waiting', 'confirmed': 'Waiting', 'partially_available': 'Partially Picked', 'assigned': 'Ready'}
        color_dict = {'draft': '#E7DFDE', 'waiting': '#efb139', 'confirmed': '#efb139', 'partially_available': '#8c557a', 'assigned': '#008000'}
        for picking_id in self.env['stock.picking'].search([('state', 'not in', ['cancel', 'done']), ('picking_type_id', '=', picking_type_id)]):
            vals = {}
            vals['picking_id'] = picking_id.id
            vals['name'] = picking_id.name
            vals['backorder'] = picking_id.backorder_id.name if picking_id.backorder_id else ''
            vals['ref'] = picking_id.origin or ''
            vals['floor'] = ''
            vals['do_vendor_date'] = picking_id.do_vendor_date or ''
            vals['do_vendor_no'] = picking_id.do_vendor_ref or ''
            vals['batch_no'] = picking_id.batch_name or ''
            vals['est_qty'] = picking_id.qty_summary or ''
            try:
                vals['transfer_method'] = dict(picking_id.fields_get(['transfer_method'])['transfer_method']['selection'])[picking_id.transfer_method]
            except:
                vals['transfer_method'] = ''
            vals['date_scheduled'] = str(picking_id.min_date) if picking_id.min_date else ''
            vals['partner'] = picking_id.partner_id.name_get()[0][1] if picking_id.partner_id else ''
            if (picking_id.picking_type_code != 'incoming') and (picking_id.state == 'assigned'):
                vals['status'] = 'Picked'
            else:
                vals['status'] = status_dict.get(picking_id.state, '')
            vals['color'] = color_dict.get(picking_id.state, '')
            vals['src_location'] = picking_id.location_id.name_get()[0][1]
            vals['dest_location'] = picking_id.location_dest_id.name_get()[0][1]
            vals['location'] = vals['src_location'] + ' → ' + vals['dest_location']
            data_list.append(vals)
        return data_list

    # Incoming get data for APP
    def get_incoming_data(self):
        self.ensure_one()
        data_list = []
        for move_id in self.move_lines:
            vals = {}
            product_id = move_id.product_id
            vals['move_id'] = move_id.id
            vals['product_id'] = product_id.id
            vals['product'] = product_id.name
            vals['barcode'] = product_id.barcode or ''
            vals['item_no'] = product_id.default_code or ''
            vals['qty'] = move_id.product_qty
            vals['tracking'] = product_id.tracking
            vals['scanned_qty'] = move_id.incoming_reserved
            vals['roll'] = math.ceil(move_id.product_qty / product_id.vendor_kg_roll)
            scanned_data = []
            for scanned_id in move_id.scanned_ids:
                scanned_data.append({'lot_name': scanned_id.name, 'qty': scanned_id.qty})
            vals['scanned_data'] = scanned_data
            data_list.append(vals)
        return data_list

    # Outgoing & Internal Transfer get data for APP
    def get_picking_transfer_data(self):
        self.ensure_one()
        data_list = []
        for move_id in self.move_lines:
            vals = {}
            product_id = move_id.product_id
            vals['move_id'] = move_id.id
            vals['product_id'] = product_id.id
            vals['product'] = product_id.name
            vals['barcode'] = product_id.barcode or ''
            vals['item_no'] = product_id.default_code or ''
            vals['qty'] = move_id.product_uom_qty
            vals['tracking'] = product_id.tracking
            vals['roll'] = math.ceil(move_id.product_qty / product_id.vendor_kg_roll)
            scanned_qty = 0.0
            scanned_data = []
            for pack_id in self.pack_operation_product_ids.filtered(lambda x: x.product_id == move_id.product_id):
                scanned_qty += pack_id.qty_done
                for pack_lot in pack_id.pack_lot_ids.filtered(lambda y: y.qty > 0):
                    lot_vals = {}
                    lot_vals['lot_name'] = pack_lot.lot_id.name
                    lot_vals['lot_id'] = pack_lot.lot_id.id
                    lot_vals['scanned_qty'] = pack_lot.qty
                    scanned_data.append(lot_vals)
            vals['scanned_qty'] = scanned_qty
            vals['scanned_data'] = scanned_data
            data_list.append(vals)
        return data_list

    def app_action_reserve(self):
        self.action_assign()
        status_dict = {'draft': 'Draft', 'waiting': 'Waiting', 'confirmed': 'Waiting', 'partially_available': 'Partially Picked', 'assigned': 'Picked'}
        return status_dict.get(self.state, '')

    def app_action_assign(self, data_list):
        self.ensure_one()
        if self.state not in ['confirmed', 'partially_available', 'assigned']:
            return False
        if self.picking_type_code == 'incoming':
            self.do_unreserve()
            self.action_assign()
            for data in data_list:
                move_id = self.env['stock.move'].browse(data['move_id'])
                move_id.scanned_ids.unlink()
                if move_id.product_id.tracking == 'none':
                    pack_id = self.env['stock.pack.operation'].search([('product_id', '=', move_id.product_id.id), ('picking_id', '=', self.id)])
                    if pack_id:
                        pack_id.write({'qty_done': pack_id.qty_done + data['qty']})
                        move_id.write({'incoming_reserved': data['qty']})
                else:
                    pack_id = self.env['stock.pack.operation'].search([('product_id', '=', move_id.product_id.id), ('picking_id', '=', self.id)])
                    pack_lot_list = []
                    for lot_dict in data['scanned_data']:
                        self.env['stock.move.scanned'].create({'move_id': move_id.id, 'name': lot_dict['lot_name'], 'qty': lot_dict['qty']})
                        vals = {}
                        if self.picking_type_id.use_existing_lots:
                            lot_id = self.env['stock.production.lot'].search([('product_id', '=', pack_id.product_id.id), ('name', '=', lot_dict.get('lot_name', ''))], limit=1)
                            if not lot_id:
                                lot_id = self.env['stock.production.lot'].create({'name': lot_dict.get('lot_name', ''), 'product_id': pack_id.product_id.id})
                            vals['lot_id'] = lot_id.id
                        vals['lot_name'] = lot_dict.get('lot_name', '')
                        vals['qty'] = lot_dict.get('qty')
                        pack_lot_list.append((0, 0, vals))
                    pack_id.pack_lot_ids.unlink()
                    pack_id.write({'pack_lot_ids': pack_lot_list, 'qty_done': data.get('qty', 0)})
                    move_id.write({'incoming_reserved': data['qty']})
        else:
            data_list = filter(lambda x: x.get('qty') > 0, data_list)
            # self.with_context(picking_reserve=data_list).action_assign()
            for data in data_list:
                move_id = self.env['stock.move'].browse(data['move_id'])
                if move_id.product_id.tracking == 'none':
                    pack_id = self.env['stock.pack.operation'].search([('product_id', '=', move_id.product_id.id), ('picking_id', '=', self.id)], limit=1)
                    if pack_id:
                        pack_id.write({'qty_done': data['qty']})
                else:
                    pack_id = self.env['stock.pack.operation'].search([('product_id', '=', move_id.product_id.id), ('picking_id', '=', self.id)], limit=1)
                    for lot_dict in data['scanned_data']:
                        lot_id = self.env['stock.production.lot'].search([('product_id', '=', pack_id.product_id.id), ('name', '=', lot_dict.get('lot_name', ''))], limit=1)
                        for pack_lot in pack_id.pack_lot_ids.filtered(lambda y: y.lot_id == lot_id):
                            pack_lot.write({'qty': lot_dict.get('qty')})
                    pack_id.write({'qty_done': data.get('qty', 0)})
        return True

    def action_picked_done(self):
        self.ensure_one()
        try:
            transfer_dict = self.do_new_transfer()
            if type(transfer_dict) == dict and transfer_dict.get('res_model') and transfer_dict.get('res_id'):
                wiz_obj = self.env[transfer_dict['res_model']].browse(transfer_dict['res_id'])
                wiz_obj.process()
            backorder = self.search([('backorder_id', '=', self.id)], order='id desc', limit=1)
            if backorder and backorder.state in ['partially_available', 'assigned']:
                backorder.do_unreserve()
            return True
        except:
            return False

StockPicking()


class StockPackOperationLot(models.Model):
    _inherit = 'stock.pack.operation.lot'

    def get_lot_number_rpc(self):
        new_lot_number = 'R' + str(fields.Datetime.now()).replace('-', '').replace(':', '').replace(' ', '')
        # Make it Delay
        time.sleep(1)
        return new_lot_number

StockPackOperationLot()