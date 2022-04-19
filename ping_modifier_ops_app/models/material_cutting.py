from odoo import models, tools

class MaterialCutting(models.Model):
    _inherit = 'material.cutting'

    def app_start_cutting(self):
        if self.state == 'draft':
            self.start_cutting()
        return True

    def app_finish_cutting(self):
        try:
            self.finish_cutting()
            return 'True'
        except Exception as e:
            return str(tools.ustr(e)).replace('\nNone', '')

    def get_material_cutting_list(self):
        data_list = []
        color_dict = {'draft': '#efb139', 'start': '#0FD2FD'}
        for record in self.env['material.cutting'].search([('state', 'not in', ['cancel', 'finish'])]):
            vals = {}
            vals['cutting_id'] = record.id
            vals['name'] = record.name
            vals['state'] = dict(record.fields_get(['state'])['state']['selection'])[record.state]
            vals['sale_order'] = record.sale_id.name if record.sale_id else ''
            vals['date'] = record.date
            vals['color'] = color_dict.get(record.state, '#E7DFDE')
            vals['cutting_order_sequence'] = record.cutting_order_sequence or ''
            vals['operator'] = record.operator_id.name.name if record.operator_id and record.operator_id.name else ''
            data_list.append(vals)
        return data_list

    def get_material_cutting_detail(self):
        if any((not x.move_id) or (x.move_state in ['draft', 'waiting', 'confirmed', 'assigned']) for x in self.move_transformation_ids):
            data_list = []
            for line_id in self.move_transformation_ids:
                vals = {}
                product_id = line_id.product_id
                vals['line_id'] = line_id.id
                vals['product'] = product_id.name
                vals['product_id'] = product_id.id
                vals['barcode'] = product_id.barcode or ''
                vals['item_no'] = product_id.default_code or ''
                vals['lot_name'] = line_id.lot_id.name if line_id.lot_id else ''
                vals['stock_qty'] = line_id.stock_qty
                vals['qty_done'] = line_id.quantity_done
                vals['state'] = dict(line_id.fields_get(['move_state'])['move_state']['selection'])[line_id.move_state] if line_id.move_state else ''
                vals['button'] = 'no'
                if not line_id.move_id or line_id.move_state in ['draft', 'waiting', 'confirmed']:
                    vals['button'] = 'Check'
                if line_id.move_state == 'assigned':
                    vals['button'] = 'Process'
                data_list.append(vals)
            return {
                'tab': 'transformation',
                'lines': data_list
            }
        elif any((not x.move_id) or (x.move_state in ['draft', 'waiting', 'confirmed', 'assigned']) for x in self.move_cutting_ids):
            data_list = []
            for line_id in self.move_cutting_ids:
                vals = {}
                product_id = line_id.product_id
                vals['line_id'] = line_id.id
                vals['product'] = product_id.name
                vals['product_id'] = product_id.id
                vals['barcode'] = product_id.barcode or ''
                vals['item_no'] = product_id.default_code or ''
                vals['lot_name'] = line_id.lot_id.name if line_id.lot_id else ''
                vals['quantity_order'] = line_id.quantity_order_related
                vals['stock_qty'] = line_id.stock_qty
                vals['qty_done'] = line_id.quantity_done
                vals['flag_1'] = line_id.flag_1
                vals['flag_2'] = line_id.flag_2
                vals['flag_3'] = line_id.flag_3
                vals['packing_status'] = line_id.packing_status or ''
                vals['packing_product'] = line_id.packing_product_id.name if line_id.packing_product_id else ''
                vals['state'] = dict(line_id.fields_get(['move_state'])['move_state']['selection'])[line_id.move_state] if line_id.move_state else ''
                vals['button'] = 'no'
                if (line_id.packing_status != 'ready') and (not line_id.move_id or line_id.move_state in ['draft', 'waiting', 'confirmed']):
                    vals['button'] = 'Check'
                if line_id.move_state == 'assigned':
                    vals['button'] = 'Process'
                data_list.append(vals)
            return {
                'tab': 'cutting',
                'lines': data_list
            }
        elif self.state == 'start':
            item_list = []
            packing_list = []
            for item in self.packing_items_ids:
                vals = {}
                vals['product'] = item.product_id.name if item.product_id else ''
                vals['quantity_done'] = item.quantity_done
                item_list.append(vals)
            for prod in self.packing_product_ids:
                packing_list.append({'name': prod.name})
            return {
                'netto_weight': self.netto_weight,
                'bruto_weight': self.bruto_weight,
                'tab': 'packing',
                'item_lines': item_list,
                'packing_lines': packing_list
            }
        return {}

    # Get Product List
    def get_product_list(self):
        partner_list = []
        for product_id in self.env['product.product'].search([]):
            vals = {}
            vals['id'] = product_id.id
            vals['name'] = product_id.name
            partner_list.append(vals)
        return partner_list

    #Get Cutting List
    def cutting_lines_lot(self):
        data_list = []
        for line in self.env['material.cutting.line'].search([('cutting_id', '=', self.id), ('packing_product_id', '=', False)]):
            vals = {}
            vals['line_id'] = line.id
            vals['lot_id'] = line.lot_id.id if line.lot_id else 0
            vals['lot_name'] = line.lot_id.name if line.lot_id else ''
            vals['quantity_done'] = line.quantity_done
            data_list.append(vals)
        return data_list

    def app_action_packing(self, data):
        try:
            vals = {}
            vals['name'] = data['name']
            vals['product_id'] = data['product_id']
            vals['cutting_id'] = self.id
            vals['cutting_line'] = [(6, 0, data['lines'])]
            wizz_id = self.env['packing.wizz'].sudo().create(vals)
            wizz_id.sudo().packing_process()
            return 'True'
        except Exception as e:
            return str(tools.ustr(e)).replace('\nNone', '')

MaterialCutting()

class MaterialTransformation(models.Model):
    _inherit = 'material.transformation'
    
    def app_transform_button_action(self):
        try:
            if (not self.move_id) or (self.move_state in ['draft', 'waiting', 'confirmed']):
                self.check_transformation()
            elif self.move_state == 'assigned':
                self.process_transformation()
            return 'True'
        except Exception as e:
            return str(tools.ustr(e)).replace('\nNone', '')
    
MaterialTransformation()

class MaterialCuttingLine(models.Model):
    _inherit = 'material.cutting.line'

    def app_write_flag(self, vals):
        try:
            self.write(vals)
            return 'True'
        except Exception as e:
            self.env.cr.rollback()
            return str(tools.ustr(e)).replace('\nNone', '')

    def app_check_action(self):
        try:
            self.check_cutting()
            return 'True'
        except Exception as e:
            return str(tools.ustr(e)).replace('\nNone', '')

    def app_process_action(self):
        try:
            self.process_cutting()
            return 'True'
        except Exception as e:
            return str(tools.ustr(e)).replace('\nNone', '')

MaterialCuttingLine()