from odoo import fields, models, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from gdata.contentforshopping.data import Availability
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
import datetime as dt


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    @api.depends('order_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        res = super(SaleOrder, self)._amount_all()
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                # FORWARDPORT UP TO 10.0
                if order.company_id.tax_calculation_rounding_method == 'round_globally':
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=order.partner_shipping_id)
                    amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                else:
                    amount_tax += line.price_tax
            
            downpayment_percent_min = order.company_id.minimum_downpayment / 100
            downpayment_percent_max = order.company_id.maximum_downpayment / 100
            
            order.update({
#                 'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
#                 'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
#                 'amount_total': amount_untaxed + amount_tax,
                
                'downpayment_percent_min'   : downpayment_percent_min, 
                'downpayment_percent_max'   : downpayment_percent_max,
                
                'downpayment_amount_min'    : round(downpayment_percent_min * (amount_untaxed + amount_tax),-3),
                'downpayment_amount_max'    : round(downpayment_percent_max * (amount_untaxed + amount_tax),-3),
            })
            
    #@api.depends('internal_move_ids')
    def _get_internal_move_count(self):
        for order in self:
            order.internal_move_count = len(order.internal_move_ids)
        
    @api.multi
    def _get_qty_summary(self):
        qty_summary         = ''
        qty_summary_dict    = {'roll' : 0,  'roll_kg': 0.0, 
                               'piece': 0, 'piece_kg': 0.0}
        pickup_location_ids = []
        pickup_location     = ""
        for order in self:
            for line in order.order_line:
                pickup_location_ids.append(line.pickup_location_id.name) 
                if line.type=='roll':
                    for lot in line.sale_order_line_lots:
                        qty_summary_dict['roll'] += 1
                    qty_summary_dict['roll_kg'] += line.product_uom_qty
                elif line.type=='piece':
                    for lot in line.sale_order_line_lots:
                        qty_summary_dict['piece'] += 1
                    qty_summary_dict['piece_kg'] += line.product_uom_qty
            order.qty_summary = """Roll   : %s (%s kg) \nPiece : %s (%s kg)""" % (str(qty_summary_dict['roll']), str(qty_summary_dict['roll_kg']),
                                                                                  str(qty_summary_dict['piece']), qty_summary_dict['piece_kg'])
            for loc_name in list(set(pickup_location_ids)):
                if pickup_location:
                    pickup_location = loc_name + ", " + loc_name
                else:
                    pickup_location = loc_name
            order.pickup_location   = pickup_location
    
    @api.one
    @api.depends('internal_move_ids','internal_move_ids.state')
    def compute_ready_invoiced(self):
        for sale in self:
            #print "sale--->", sale
            all_internal_move_ids_non_cancel = len(sale.internal_move_ids.filtered(lambda int: int.state != 'cancel'))
            all_internal_move_ids_done       = len(sale.internal_move_ids.filtered(lambda int: int.state == 'done'))
            
            if sale.internal_move_ids and not sale.cutting_order_id and all_internal_move_ids_done == all_internal_move_ids_non_cancel:
                #print "sale.internal_move_ids--->", sale.internal_move_ids 
                sale.ready_invoiced = True
                #sale.action_confirm()
                #sale.invalidate_cache()
                #sale.action_invoice_create(grouped=True)
                #raise UserError(_('Exist'))
            else:
                sale.ready_invoiced = False
    
    @api.multi
    def confirm_and_invoice(self):
        self.action_confirm()
        self.invalidate_cache()
        
            
#     @api.multi
#     def _write(self, vals):
#         pre_not_ready_invoiced = self.filtered(lambda sale: not sale.ready_invoiced)
#         pre_ready_invoiced = self - pre_not_ready_invoiced
#         
#         print "pre_ready_invoiced------>>#1", pre_ready_invoiced
#         
#         #pre_reconciled = self - pre_not_reconciled
#         res = super(SaleOrder, self)._write(vals)
#         
#         ready_invoiced = self.filtered(lambda sale: sale.ready_invoiced)
#         not_ready_invoiced = self - ready_invoiced
#         
#         print "not_ready_invoiced------>>#2", not_ready_invoiced
#         
#         
#         print "vals--->", vals
#         ready_invoiced = self.filtered(lambda sale: not sale.ready_invoiced)
#         print "raise UserError(_('Exist'))---->", ready_invoiced
#         
#         (ready_invoiced & pre_ready_invoiced).filtered(lambda sale: sale.state == 'cutting_order' and not sale.cutting_order_id).action_confirm()
#         (ready_invoiced & pre_ready_invoiced).filtered(lambda sale: sale.state == 'cutting_order' and not sale.cutting_order_id).action_invoice_create()
#         
#         #raise UserError(_('Exist Write'))
#         return res
    
    ##Columns
    branch_id       = fields.Many2one('res.branch', 'Branch', required=True, index=True,default=lambda self: self.env.user.branch_id.id)
    sales_channel       = fields.Selection([('offline','Offline'),('whatsapp','Whatsapp'),('marketplace','Marketplace')], string='Channel')
    
    cutting_order_id    = fields.Many2one('material.cutting', string='Cutting Order', copy=False)
    
    ##Customer Scoring
    customer_scoring        = fields.Selection([('good','Good customer'),('bad','Bad customer')], related='partner_id.customer_scoring',string='Customer Scoring')
    
    ##Additional Order Name
    order_contact_name          = fields.Char(string='Name')
    order_contact_mobile        = fields.Char(string='Mobile Phone')
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char()
    
    sample_check        = fields.Boolean(string='Sample Check')
    terms_check         = fields.Boolean(string='Terms Check')
    
    downpayment_percent_min = fields.Float(string='Min. % DP', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    downpayment_percent_max = fields.Float(string='Max. % DP', store=True, readonly=True, compute='_amount_all', track_visibility='always')

    downpayment_amount_min = fields.Monetary(string='Min. DP', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    downpayment_amount_max = fields.Monetary(string='Max. DP', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    
    internal_move_ids   = fields.Many2many('stock.picking', string='Internal Move of this Sales Order')
    internal_move_count = fields.Integer(string='Internal Move Count', compute='_get_internal_move_count')
    
    qty_summary         = fields.Text(string='Summary Qty', compute='_get_qty_summary')
    pickup_location     = fields.Text(string='Pickup Location', compute='_get_qty_summary')
    
    ready_invoiced      = fields.Boolean(string='Ready Invoiced', store=True, readonly=True, compute='compute_ready_invoiced')
    
    reason              = fields.Text(string='Notes')
    
    count_print_quotation   = fields.Integer(string='Count Print Quotation')
    warning_error       = fields.Char(string="Warning Error", track_visibility='onchange')
        
    
#     order_line = fields.One2many('sale.order.line', 'order_id', string='Order Lines', states={'draft': [('readonly', False)]}, copy=True, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        #('reserved', 'Reserved'),
        ('quotation', 'Quotation'),
        ('downpayment', 'Waiting DP'),
        ('cutting_ordered', 'Sales Order'),
        ('cutting_process', 'Cutting On Processing'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Done'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')
    sale_status         = fields.Selection([('dp_first','DP First'),('invoice_sent','Invoice Sent'),
                                            ('invoice_paid','Invoice Paid'),('ready_to_deliver','Ready to Deliver')],string="Status SO")
    delivery_type       = fields.Selection([('pickup','Pick Up'),('delivery','Delivery')],string='Delivery Type')
    
    @api.multi
    def func_count_print_quotation(self):
        count_print_quotation = self.count_print_quotation + 1
        self.write({'count_print_quotation' : count_print_quotation})
        return self.count_print_quotation
    
    @api.onchange('order_contact_mobile')
    def onchange_check_contact(self):
        mobile  = self.order_contact_mobile
        contacts = self.env['res.partner'].search([('mobile','=',mobile)])
        if mobile and contacts:
            message = """Customer Registered : """
            for contact in contacts:
                message += "\n - %s" % contact.name
            raise UserError(_(message))
    
    @api.multi
    def action_view_internal_move(self):
        internal_moves = self.mapped('internal_move_ids')
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        if len(internal_moves) >= 1:
            action['domain'] = [('id', 'in', internal_moves.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
    
    @api.multi
    def create_internal_move(self):
        internal_move_ids = []
        for order in self:
            picking_location_dict = []
            picking_exist_id = []
            for l in order.order_line:
                if not l.type in ['roll','piece']: 
                    continue
                #Loop Lot
                move_lot_ids = []
                total_qty = 0.0
                for line_lot in l.sale_order_line_lots:
                    #print "line_lots--->", line_lot
                    
                    location_id         = line_lot.location_id.id
                    if l.type=='piece':
                        location_dest_id    = order.branch_id.transformation_loc_src_id.id
                    elif l.type=='roll':
                        location_dest_id    = l.pickup_location_id.id
                    
                    ##Create Picking Internal Move
                    #if line_lot.location_id.id not in  picking_location_dict:
                    if picking_location_dict:
                        picking_exist_id = self.env['stock.picking'].search([('id','in',picking_location_dict),('location_id','=',line_lot.location_id.id),('location_dest_id','=',location_dest_id)], limit=1)
                    if not picking_exist_id:
                        picking_id = self.env['stock.picking'].create({
                            #'date'              : fields.Datetime.now(),
                            'sale_id'           : order.id,
                            'origin'            : order.name,
                            'picking_type_id'   : order.branch_id.int_picking_type_id.id,
                            'company_id'        : order.company_id.id,
                            'branch_id'         : order.branch_id.id,
                            'location_id'       : line_lot.location_id.id,
                            'location_dest_id'  : location_dest_id,
                            })
                        print "## Picking Internal Move Created"
                        #picking_location_dict[line_lot.location_id.id] = picking_id.id
                        picking_location_dict.append(picking_id.id)
                        internal_move_ids.append((4,picking_id.id))
                    ###
                    
                    
                    total_qty += line_lot.stock_qty
                    move_lot_ids.append((0,0,{'lot_id': line_lot.id, 'quantity': line_lot.stock_qty, 'quantity_done': line_lot.stock_qty}))
                
                    move = self.env['stock.move'].create({
                        'name'          : l.name, 
                        'date'          : fields.Datetime.now(),
                        'date_expected' : fields.Datetime.now(),
                        'product_id'    : l.product_id.id,
                        'product_uom'   : l.product_uom.id,
                        'product_uom_qty': line_lot.stock_qty,
                        'location_id'       : location_id,
                        'location_dest_id'  : location_dest_id,
                        #'move_dest_id': self.procurement_ids and self.procurement_ids[0].move_dest_id.id or False,
                        #'procurement_id': self.procurement_ids and self.procurement_ids[0].id or False,
                        'company_id'        : order.company_id.id,
                        'origin'            : order.name,
                        'restrict_lot_id'   : line_lot.id,
                        'picking_id'        : (picking_exist_id and picking_exist_id.id) or picking_id.id
                        #'picking_id'        : picking_location_dict[line_lot.location_id.id] 
                        #'group_id': self.order_id.l.procurement_group_id.id,
                        #'propagate': False,#self.propagate,
                        #'lot_ids'           : move_lot_ids,
                        #'internal_move_id'  : internal_move_id.id,
                        #'active_move_lot_ids' : move_lot_ids,
                    })
                    print "move---->", move
            #raise UserError(_('Customer Exist'))
            order.write({'internal_move_ids' : internal_move_ids})
    
    @api.multi
    def create_request_cutting(self):
        print "###create_request_cutting###"
        ##Create Internal Move
        #self.create_internal_move()
        
        for l in self.order_line:
            if l.type=='piece':
                print "###### BUTUH POTONG #######"
                l.create_cutting_line()
    
    @api.multi
    def check_customer_exist(self, order_contact_mobile=False):
        contact_exist = self.env['res.partner'].search(['|',('phone','=',self.order_contact_mobile),('mobile','=',self.order_contact_mobile)])
        if len(contact_exist) >= 1:
            contact_exist_list = ''
            for i in contact_exist:
                contact_exist_list = contact_exist_list + i.name + ', '
            raise UserError(_('Customer Exist : %s' % contact_exist_list))
    
    @api.onchange('order_contact_mobile')
    def onchange_order_contact_mobile(self):
        if self.order_contact_mobile:
            self.check_customer_exist()
            
    @api.multi
    def check_double_order(self):
        print "self.date_order----->", dt.datetime.strptime(self.date_order, '%Y-%m-%d %H:%M:%S')
        date_from   = dt.datetime.strptime(self.date_order, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d 00:00:01')
        date_to     = dt.datetime.strptime(self.date_order, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d 23:59:59')
        
        print "From - To ", date_from, date_to
        
        print "self.date_order----->", self.date_order[:10], type(self.date_order)
        sale_today_ids = self.search([('date_order','>=',date_from),('date_order','<=',date_to),('partner_id','=',self.partner_id.id),('id','!=',self.id)])
        if len(sale_today_ids) >= 1:
            sale_today_list = ''
            for i in sale_today_ids:
                sale_today_list = sale_today_list + i.name + ', '
            raise UserError(_('Sales Today : %s' % sale_today_list))
        else:
            raise UserError(_("No Duplicated Order today"))
            
    @api.multi
    def open_check_product(self):
        view = self.env.ref('ping_modifier_cutting.view_order_line_form')
#         view = self.env.ref('ping_modifier_cutting.view_searching_product_wizz_form')
#         wiz = self.env['change.dest.location'].create({'location_dest_id': self.location_dest_id.id,
#                                                        'picking_id' : self.id})
        # TDE FIXME: a return in a loop, what a good idea. Really.
        print "self.id--->", self.id
        return {
            'name': _('Change Destination Location'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order.line',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            #'res_id': wiz.id,
            #'context': self.env.context,
            'context': {'default_order_id': self.id}
        }
    
    @api.multi
    def cancel_reason(self):
        view = self.env.ref('ping_modifier_cutting.view_cancel_wizz')
#         view = self.env.ref('ping_modifier_cutting.view_searching_product_wizz_form')
#         wiz = self.env['change.dest.location'].create({'location_dest_id': self.location_dest_id.id,
#                                                        'picking_id' : self.id})
        # TDE FIXME: a return in a loop, what a good idea. Really.
        return {
            'name': _('Cancel Reason'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'cancel.wizz',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            #'res_id': wiz.id,
            #'context': self.env.context,
            #'context': {'default_order_id': self.id}
        }
        
#     @api.multi
#     def reserved(self):
#         for o in self:
#             for l in o.order_line:
#                 for llot in l.sale_order_line_lots:
#                     print  "llot.id--->", llot.id
#                     availability = l.product_id._compute_quantities_dict(lot_id=llot.id, owner_id=False, package_id=False, from_date=False, to_date=False)
#                     print "availability-->", availability
#             #raise UserError(_('XXXX'))
#             o.write({'state' : 'reserved'})

    @api.multi
    def quotation(self):
        for o in self:
            if not o.terms_check:
                raise UserError(_('Please Checklist Terms Check First before Click Quotation Button'))
            o.create_handling_fee()
            o.create_rounding()
            o.write({'state' : 'quotation'})

    @api.multi
    def confirm_order(self):
        for o in self:
            if o.partner_id.membership_state in ['free','paid'] and o.partner_id.customer_scoring != 'bad':
                order_piece_and_roll = o.order_line.filtered(lambda line: line.type in ['piece','roll'])
                if len(order_piece_and_roll) >= 1:
                    ##Create Internal Move
                    self.create_internal_move()
                
                for l in o.order_line:
                    if l.type in ['piece']:
                        print"****** Piece ******"
                        #o.create_request_cutting()
                        l.create_cutting_line()
                        
                        #Make sure runing just 1 Time
                #If no other items Piece or Roll
                if len(order_piece_and_roll) >= 1:
                    return o.write({'state' : 'cutting_ordered'})
                #raise UserError(_('xxx'))
                
                o.action_confirm()
            else:
                o.write({'state' : 'downpayment'})
                
    @api.multi
    def create_handling_fee(self):
        print "###create_handling_fee###"
        handling_fee_obj = self.env['handling.fee.config']
        for o in self:
            if o.amount_untaxed != 0.0:
                handling_fee = handling_fee_obj.search([('min','<=',o.amount_untaxed),('max','>=',o.amount_untaxed)])
                print "#handling_fee--->", handling_fee
                if handling_fee:
                    handling_fee.handling_fee_amount
                    self.env['sale.order.line'].create({'product_id' : o.company_id.handling_fee_product_id.id,
                                                        'type'       : 'other',
                                                        'price_unit' : handling_fee.handling_fee_amount,
                                                        'product_uom_qty' : 1,
                                                        'order_id'   : o.id})
    @api.multi
    def create_rounding(self):
        print "###create_rounding###"
        for o in self:
            #Check Existing Rounding Then Remove
            for l in o.order_line:
                if l.product_id == o.company_id.rounding_product_id:
                    l.unlink()
                
            rounding_amount = float(str(float(o.amount_total))[-5:])
            if rounding_amount > 0.0:
                self.env['sale.order.line'].create({'product_id' : o.company_id.rounding_product_id.id,
                                                    'type'       : 'other',
                                                    'price_unit' : -rounding_amount,
                                                    'product_uom_qty' : 1,
                                                    'order_id'   : o.id})
    @api.multi
    def action_confirm(self):
        for order in self:
            order.create_rounding()
        res = super(SaleOrder, self).action_confirm()
        
#         self.create_request_cutting()
        
#     @api.multi
#     def check_stock_by_lot(self):
    
    @api.multi
    def action_cancel(self):
        for order in self:
            if order.state == 'cutting_ordered':
                order.partner_id.customer_scoring = 'bad'
        return self.write({'state': 'cancel'})
    
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    @api.model
    def default_get(self, fields):
        res = super(SaleOrderLine, self).default_get(fields)
        print "self.env.context----->>", self.env.context
        sale = self.env['sale.order'].browse([self.env.context.get('active_id')])
        res.update({
            'order_id'       : self.env.context.get('active_id'),
            'branch_id'      : sale.branch_id.id,
            })
        return res
    
    @api.multi
    @api.depends('sale_order_line_lots')
    def lot_count(self):
        for o in self:
            count = len(o.sale_order_line_lots)
            o.sale_order_line_lots_count    = count
    
    #Columns
    color_group_id  = fields.Many2one('product.color.group','Color Group',readonly=True, related="product_id.color_group_id")
    color_name      = fields.Many2one('product.color','Color',readonly=True, related="product_id.color_name")
    type        = fields.Selection([('roll','Roll'),('piece','Eceran'),('other','Other')], string='Type', required=True)
    cutting     = fields.Selection([('yes','Yes'),('no','No')], string='Cutting', required=False)
    sale_order_line_lots        = fields.Many2many('stock.production.lot', 'sale_line_lot_rel', 'sale_line_id', 'lot_id',string="Order Line Lots", copy=False, readonly=False)
    sale_order_line_lots_count  = fields.Integer(compute='lot_count' ,string="Realization Roll Qty", copy=False, readonly=False)
    #sale_order_line_lots    = fields.One2many('sale.order.line.lots', 'sale_order_line_id', string='Order Line Lots')
    quantity_order_roll = fields.Integer(string='Ordered Roll Qty', digits=dp.get_precision('Product Unit of Measure'), required=True, default=0)
    quantity_order  = fields.Float(string='Ordered Qty', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0)
    product_uom_qty = fields.Float(string='Realization Qty', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0)
    
    discount_amount = fields.Float(string='Discount')
    
    pickup_location_id  = fields.Many2one('stock.location', string='Pickup Location')
    #branch_id           = fields.Many2one('branch', string='Branch')
    branch_id           = fields.Many2one('res.branch', string='Branch')
    
    ####
    product_lot_ids1    = fields.One2many('searching.product.line.wizz', 'sale_order_id', 'Lines', domain=[('type','=','1')])
    product_lot_ids2    = fields.One2many('searching.product.line.wizz', 'sale_order_id', 'Lines', domain=[('type','=','2')])
    product_lot_ids3    = fields.One2many('searching.product.line.wizz', 'sale_order_id', 'Lines', domain=[('type','=','3')])
    see_more            = fields.Boolean(string="See More (1)...")
    see_more3           = fields.Boolean(string="See More (2)...")
    
    @api.multi
    def unlink(self):
        lot_reserved_ids = self.env['lot.reserved'].search([('sale_line_id','=',self.id)])
        lot_ids = [i.lot_id for i in lot_reserved_ids]
            
        if self.filtered(lambda x: x.state in ('sale', 'done')):
            raise UserError(_('You can not remove a sale order line.\nDiscard changes and try setting the quantity to 0.'))
        res = super(SaleOrderLine, self).unlink()
        ###
        for l in lot_ids:
            l.check_available_qty()
        ###
        return res
    
    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        print "###product_id_change2"
        if not self.product_id:
            return {'domain': {'product_uom': []}}

        vals = {}
        domain = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
        if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
            vals['product_uom'] = self.product_id.uom_id
            vals['product_uom_qty'] = 1.0

        product = self.product_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id.id,
            quantity=vals.get('product_uom_qty') or self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id
        )

        result = {'domain': domain}

        title = False
        message = False
        warning = {}
        if product.sale_line_warn != 'no-message':
            title = _("Warning for %s") % product.name
            message = product.sale_line_warn_msg
            warning['title'] = title
            warning['message'] = message
            result = {'warning': warning}
            if product.sale_line_warn == 'block':
                self.product_id = False
                return result
        
        name = (product.name and product.name or '') \
                    + (product.color_group_id and ' '+product.color_group_id.name or '') \
                    + (product.color_name and ' '+product.color_name.name or '')

        
#         name = product.name_get()[0][1]
#         if product.description_sale:
#             name += '\n' + product.description_sale
        vals['name'] = name

        self._compute_tax_id()

        if self.order_id.pricelist_id and self.order_id.partner_id:
            vals['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(self._get_display_price(product), product.taxes_id, self.tax_id, self.company_id)
        self.update(vals)

        return result
    
    @api.onchange('quantity_order_roll', 'product_id')
    def onchange_product_roll(self):
        if self.type in ['roll'] and self.product_id:
            self.quantity_order = self.quantity_order_roll * self.product_id.vendor_kg_roll
    
    @api.onchange('product_id','quantity_order','product_uom_qty','type','cutting')
    def onchange_product(self):
        if self.type in ['piece'] and self.cutting=='yes':
            self.product_uom_qty = self.quantity_order + 0.2
        else:
            self.product_uom_qty = self.quantity_order
        
        quantity_tolerance_min  = self.quantity_order - 0.9
        quantity_tolerance_max  = self.quantity_order + 0.9
        lot_obj = self.env['stock.production.lot']
        lot_ids1 = lot_obj.search([('product_id','=',self.product_id.id),('type','=','piece'),('available_qty','>=',quantity_tolerance_min),('available_qty','<=',quantity_tolerance_max),('available_qty','>',0.0)], order="batch_name,available_qty,name")
        lot_ids2 = lot_obj.search([('product_id','=',self.product_id.id),('type','=','piece'),('id','not in',lot_ids1.ids),('available_qty','>',0.0)], order="batch_name,available_qty,name")
        lot_ids3 = lot_obj.search([('product_id','=',self.product_id.id),('type','=','roll'),('available_qty','>',0.0)], order="batch_name,available_qty,name")
        
#         print "lot_ids--->", lot_ids.ids
#
#         for i in lot_ids1:
#             print "Lot---->>", i
#             print "lot.available_qty---->", i.available_qty
            
        product_lot_ids1 = [(0, 0, {'product_lot_id' : lot.id, 'available_qty': lot.available_qty, 'type': '1'}) for lot in lot_ids1]
        product_lot_ids2 = [(0, 0, {'product_lot_id' : lot.id, 'available_qty': lot.available_qty, 'type': '2'}) for lot in lot_ids2]
        product_lot_ids3 = [(0, 0, {'product_lot_id' : lot.id, 'available_qty': lot.available_qty, 'type': '3'}) for lot in lot_ids3]
        
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
        lost_ids = []
        batch_name = []
        
        print "###active_id----->>", active_id
        so = self.env['sale.order'].browse(active_id)
        try:
            for o in self:
                for l1 in o.product_lot_ids1:
                    if l1.selected==True:
                        lost_ids.append((4, l1.product_lot_id.id))
                        batch_name.append(l1.batch_name)
                for l2 in o.product_lot_ids2:
                    if l2.selected==True:
                        lost_ids.append((4, l2.product_lot_id.id))
                        batch_name.append(l2.batch_name)
                for l3 in o.product_lot_ids3:
                    if l3.selected==True:
                        lost_ids.append((4, l3.product_lot_id.id))
                        batch_name.append(l3.batch_name)
                
                ##Check batch Duplicate
                print "l3.product_lot_id.id---->", l3.product_lot_id
                print "batch_name---->", batch_name
                count_batch_name = len(list(set(batch_name)))
                if count_batch_name > 1:
                    print "count_batch_name----->>", count_batch_name
                    so.write({'warning_error': 'You Can not Selected multi batch in one line'})
                    raise ValidationError(_('You Can not Selected multi batch in one line'))
                ##
                
                print "lost_ids---->", lost_ids  
                ##Get Lot Name
                batch_name = """"""
                if lost_ids:
                    for lot in lost_ids:
                        batch_name = self.env['stock.production.lot'].browse([lot[1]]).batch_name
                self.update({ 'name': (batch_name and batch_name+' - '+o.name) or o.name,
                              'sale_order_line_lots'  : lost_ids})
                
                kg_lot_qty = 0.0
                for l in lost_ids:
                    kg_lot_qty += self.env['stock.production.lot'].browse(l[1]).available_qty
                    if o.type=='piece' and o.product_uom_qty > self.env['stock.production.lot'].browse(l[1]).available_qty and abs(o.product_uom_qty - self.env['stock.production.lot'].browse(l[1]).available_qty) > 0.9:
                        raise UserError(_('Qty Available not Enought'))
                    self.env['lot.reserved'].create({'sale_line_id': o.id,'lot_id': l[1]})
                if o.type=='roll':
                    count_lot           = int(len(o.sale_order_line_lots))
                    quantity_order_roll = int(o.quantity_order_roll)
                    self.update({ 'product_uom_qty' : kg_lot_qty,
                                  'quantity_order'  : kg_lot_qty,})
                    
                    #Check lot vs Qty
                    if count_lot != quantity_order_roll:
                        print "count_lot vs quantity_order_roll",count_lot,quantity_order_roll  
                        so.write({'warning_error': 'Qty Order Roll not same with selected Lot'})
                        raise ValidationError(_('Qty Order Roll not same with selected Lot'))
        except:
            print "### except ###"
            self.unlink()
            warning = {
                    'title': _('Warning!'),
                    'message': _('Qty Available not Enought!'),
                }
            return {'warning': warning}
            #raise ValidationError(_('Qty Available not Enought'))
            
    
    @api.onchange('product_uom', 'product_uom_qty')
    def product_uom_change(self):
        return
    
    @api.multi
    @api.onchange('type','cutting','product_id','quantity_order','product_uom_qty')
    def onchange_new_pricing(self):
        vals = {}
        #Put Price
        if self.product_id and self.type:
            if self.type=='roll':
                self.cutting= 'no'
                new_price   = self.product_id.list_price_roll
            elif self.type=='piece':
                new_price   = self.product_id.list_price_pieces
            else:
                new_price   = self.product_id.list_price
            self.price_unit = new_price
        else:
            self.price_unit = 0.0
        #Put Disc Amount
        if self.product_id and self.cutting=='no':
            if self.type=='roll':
                self.discount_amount    = self.product_id.discount_list_price_roll
            elif self.type=='piece':
                self.discount_amount    = self.product_id.discount_list_price_pieces
        else:
            self.discount_amount = 0.0
            
    
    @api.onchange('discount_amount','price_unit')
    def onchange_discount_amount(self):
        if self.price_unit != 0.0 and self.discount_amount != 0.0:
            self.discount = (self.discount_amount/self.price_unit)*100
        else:
            self.discount = 0.0
    
    @api.multi
    def find_operator(self):
        list_operator = self.env['cutting.operator'].search([('state','=','ready')], order="order_number,sequence", limit=1)
        if not list_operator:
            raise UserError(_('No Operator Ready'))
        list_operator.write({'order_number' : list_operator.order_number + 1})
        return list_operator
    
    @api.multi
    def create_cutting(self):
        #Find Available Operator
        operator_id = self.find_operator()
        cutting_order_id = self.env['material.cutting'].create({
            'origin'    : self.order_id.name,
            'date'      : fields.Datetime.now(),
            'sale_id'   : self.order_id.id,
            'operator_id' : operator_id.id,
            'branch_id'      : self.order_id.branch_id.id,
            'company_id'     : self.order_id.company_id.id,
            })
        self.order_id.write({'cutting_order_id' : cutting_order_id.id})
        return cutting_order_id
    
    @api.multi
    def create_cutting_line(self):
        transformation_obj  = self.env['material.transformation']
        cutting_line_obj    = self.env['material.cutting.line']
        
        cutting_order_id = self.order_id.cutting_order_id
        if not cutting_order_id:
            cutting_order_id = self.create_cutting()
        
        for l in self.sale_order_line_lots:
            if l.type == 'roll' and self.cutting=='yes':
                vals_transformation = {'lot_id' : l.id, 'stock_qty': l.stock_qty,'transformation_cutting_id' : cutting_order_id.id, 'sale_line_id': self.id, 'company_id': self.order_id.company_id.id}
                transformation_obj.create(vals_transformation)
            elif l.type == 'piece':
                if self.cutting=='no':
                    if l.stock_qty != self.quantity_order:
                        raise UserError(_('Stock and Order Quantity must be same !'))
                vals_cutting = {'src_lot_id' : l.id, 'lot_id' : l.id, 'stock_qty': l.stock_qty,'quantity_done' : 0.0, 'quantity_order_related': self.quantity_order 
                                ,'cutting_id' : cutting_order_id.id, 'sale_line_id': self.id}
                cutting_line_obj.create(vals_cutting)
#                 else:
#                     if l.stock_qty != self.quantity_order:
#                         raise UserError(_('Stock and Order Quantity must be same !'))
#                     vals_cutting = {'lot_id' : l.id, 'stock_qty': l.stock_qty,'quantity_done' : self.quantity_order ,'cutting_id' : cutting_order_id.id}#, 'without_cutting' : True}
#                     cutting_line_obj.create(vals_cutting)
            
    @api.multi
    def create_cutting_line2(self):
        print "self.sale_order_line_lots--->", len(self.sale_order_line_lots)
        if self.cutting=='yes' and len(self.sale_order_line_lots) > 1:
            raise UserError(_(''))
        cutting_order_id = self.order_id.cutting_order_id
        if not cutting_order_id:
            cutting_order_id = self.create_cutting()
            
        print "cutting_order_id.date--->", cutting_order_id    
        move_lot_ids = []
        
        #Loop Lot
        for line_lot in self.sale_order_line_lots:
            print "line_lots--->", line_lot
            move_lot_ids.append((0,0,{'lot_id': line_lot.id,'quantity': self.product_uom_qty}))
        
        move = self.env['stock.move'].create({
            'name': cutting_order_id.name,
            'date': cutting_order_id.date,
            'date_expected': cutting_order_id.date,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom.id,
            'product_uom_qty': self.product_uom_qty,
            'location_id': 15,
            'location_dest_id': self.product_id.property_stock_production.id,
            #'move_dest_id': self.procurement_ids and self.procurement_ids[0].move_dest_id.id or False,
            #'procurement_id': self.procurement_ids and self.procurement_ids[0].id or False,
            'company_id': self.company_id.id,
            'raw_material_cutting_id': cutting_order_id.id,
            'origin': self.order_id.name,
            'group_id': self.order_id.cutting_order_id.procurement_group_id.id,
            'propagate': False,#self.propagate,
            'active_move_lot_ids' : move_lot_ids
        })
        move.action_confirm()
        
        move = self.env['stock.move'].create({
            'name': cutting_order_id.name,
            'date': cutting_order_id.date,
            'date_expected': cutting_order_id.date,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom.id,
            'product_uom_qty': self.product_uom_qty,
            'location_id': self.product_id.property_stock_production.id,
            'location_dest_id': 15,
            #'move_dest_id': self.procurement_ids and self.procurement_ids[0].move_dest_id.id or False,
            #'procurement_id': self.procurement_ids and self.procurement_ids[0].id or False,
            'company_id': self.company_id.id,
            'cutting_id': cutting_order_id.id,
            'origin': self.order_id.name,
            'group_id': self.order_id.cutting_order_id.procurement_group_id.id,
            'propagate': False,#self.propagate,
            'active_move_lot_ids' : move_lot_ids
        })
        move.action_confirm()
        return move
    
    @api.multi
    def _action_procurement_create(self):
        """
        Create procurements based on quantity ordered. If the quantity is increased, new
        procurements are created. If the quantity is decreased, no automated action is taken.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        new_procs = self.env['procurement.order']  # Empty recordset
        for line in self:
            if line.state != 'sale' or not line.product_id._need_procurement():
                continue
            qty = 0.0
            for proc in line.procurement_ids.filtered(lambda r: r.state != 'cancel'):
                qty += proc.product_qty
            if float_compare(qty, line.product_uom_qty, precision_digits=precision) >= 0:
                continue

            if not line.order_id.procurement_group_id:
                vals = line.order_id._prepare_procurement_group()
                line.order_id.procurement_group_id = self.env["procurement.group"].create(vals)
            ##Loop Sales Lot
            if line.sale_order_line_lots:
                for lot in line.sale_order_line_lots:
                    vals = line._prepare_order_line_procurement(group_id=line.order_id.procurement_group_id.id)
                    vals['product_qty'] = lot.stock_qty if line.type=='roll' else line.product_uom_qty - qty
                    ###
                    vals['sale_line_id']    = line.id
                    vals['restrict_lot_id'] = lot.id
                    new_proc = self.env["procurement.order"].with_context(procurement_autorun_defer=True).create(vals)
                    new_proc.message_post_with_view('mail.message_origin_link',
                        values={'self': new_proc, 'origin': line.order_id},
                        subtype_id=self.env.ref('mail.mt_note').id)
                    new_procs += new_proc
            else:
                vals = line._prepare_order_line_procurement(group_id=line.order_id.procurement_group_id.id)
                vals['product_qty'] = line.product_uom_qty - qty
                ###
                vals['sale_line_id']    = line.id
            ###
                new_proc = self.env["procurement.order"].with_context(procurement_autorun_defer=True).create(vals)
                new_proc.message_post_with_view('mail.message_origin_link',
                    values={'self': new_proc, 'origin': line.order_id},
                    subtype_id=self.env.ref('mail.mt_note').id)
                new_procs += new_proc
        new_procs.run()
        return new_procs
    
    @api.multi
    def open_search_product(self):
        view = self.env.ref('ping_modifier_cutting.view_sale_line_search_wizz_form')
#         view = self.env.ref('ping_modifier_cutting.view_searching_product_wizz_form')
#         wiz = self.env['change.dest.location'].create({'location_dest_id': self.location_dest_id.id,
#                                                        'picking_id' : self.id})
        # TDE FIXME: a return in a loop, what a good idea. Really.
        return {
            'name': _('Sample Search Product'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.line.search.wizz',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            #'res_id': wiz.id,
            #'context': self.env.context,
            #'context': {'default_cutting_id': self.id}
        }

# class SaleOrderLineLots(models.Model):
#     _name = 'sale.order.line.lots'
#     
#     sale_order_line_id  = fields.Many2one('sale.order.line', string='Sale Order Line')
#     lot_id      = fields.Many2one('stock.production.lot', string='Lot', required=True)
#     quantity    = fields.Integer(string='Quantity', required=True)
    
