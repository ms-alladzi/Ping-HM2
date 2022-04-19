import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from odoo.osv import expression

import odoo.addons.decimal_precision as dp

class ProductSupplierInfo(models.Model):
    _inherit   = 'product.supplierinfo'
    
    @api.model
    def create(self, vals):
        if vals.get('reference', 'New') == 'New':
            vals['reference'] = self.env['ir.sequence'].next_by_code('vendor.pricelist') or '/'
        return super(ProductSupplierInfo, self).create(vals)
    
    reference       = fields.Char(string="Name", default='New')
    branch_ids      = fields.Many2many('res.branch',string='Branch')

#Mater Configuration
class ProductColorGroup(models.Model):
    _name = "product.color.group"
    
    name            = fields.Char(string='Name', required=True)

class ProductColor(models.Model):
    _name = "product.color"
    
    name            = fields.Char(string='Name', required=True)

class ProductCategorySecondary(models.Model):
    _name = "product.category.secondary"
    
    name            = fields.Char(string='Name', required=True)

class ProductMaterial(models.Model):
    _name = "product.material"
    
    name            = fields.Char(string='Name', required=True)

class ProductMaterialCode(models.Model):
    _name = "product.material.code"
    
    name            = fields.Char(string='Name', required=True)
    
class ProductMaterialType(models.Model):
    _name = "product.material.type"
    
    name            = fields.Char(string='Name', required=True)
    
class ProductMaterialSpecification(models.Model):
    _name = "product.material.specification"
    
    name            = fields.Char(string='Name', required=True)
    

#####################

#Mater Vendor Configuration

class VendorInitial(models.Model):
    _name = "vendor.initial"
    
    name            = fields.Char(string='Name', required=True)

class VendorMaterialOriginalName(models.Model):
    _name = "vendor.material.original.name"
    
    name            = fields.Char(string='Name', required=True)

class VendorMaterialName(models.Model):
    _name = "vendor.material.name"
    
    name            = fields.Char(string='Name', required=True)
    
class ProductVendorMaterialSpecification(models.Model):
    _name = "product.vendor.material.specification"
    
    name            = fields.Char(string='Name', required=True)

class VendorProductColorGroup(models.Model):
    _name = "vendor.product.color.group"
    
    name            = fields.Char(string='Name', required=True)

class VendorProductColor(models.Model):
    _name = "vendor.product.color"
    
    name            = fields.Char(string='Name', required=True)

#####################

class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    sales_type      = fields.Selection([('regular','Regular'),('exclusive','Special Order')], string='Sales Type', required=False, default='regular')

    material_name   = fields.Many2one('product.material', string='Wide Specification', required=False)
    material_code   = fields.Many2one('product.material.code', string='Material Code', required=False)
    material_type   = fields.Many2one('product.material.type', string='Material Type', required=False)
    material_specification   = fields.Many2one('product.material.specification',string='Gramasi Specification', required=False)
    weight_type     = fields.Selection([('brutto','Brutto'),('netto','Netto')], string='Weight Type', required=False)
    color_group_id  = fields.Many2one('product.color.group', string='Ping Color Groups', required=False)
    color_name      = fields.Many2one('product.color', string='Ping Color', required=False)
    
    #Supplier
    vendor_id               = fields.Many2one('res.partner', string='Vendor', domain=[('supplier','=',True)], required=False)
    vendor_initial              = fields.Many2one('vendor.initial', string='Vendor Initial', required=False)
    vendor_original_name        = fields.Many2one('vendor.material.original.name', string='Vendor Original Name', required=False)
    vendor_material_name      = fields.Many2one('vendor.material.name', string='Vendor Material Type', required=False)

    vendor_color_group_id  = fields.Many2one('vendor.product.color.group', string='Vendor Color Groups', required=False)
    vendor_color_name      = fields.Many2one('vendor.product.color', string='Vendor Color', required=False)
    vendor_material_specification   = fields.Many2one('product.vendor.material.specification', string='Vendor Material Specification', required=False)
    vendor_kg_roll          = fields.Float(string='Estimate Kg/Roll', required=False, default=20.0)
    
    list_price_roll     = fields.Float('Roll Price (Kg)', default=1.0,digits=dp.get_precision('Product Price'))
    list_price_pieces   = fields.Float('Pieces Price (Kg)', default=1.0,digits=dp.get_precision('Product Price'))
    list_price_bundling = fields.Float('Bundling Price', default=1.0,digits=dp.get_precision('Product Price'))
    
    discount_list_price_roll     = fields.Float('Discount Roll Price (Kg)', default=0.0,digits=dp.get_precision('Product Price'))
    discount_list_price_pieces   = fields.Float('Discount Pieces Price (Kg)', default=0.0,digits=dp.get_precision('Product Price'))
    discount_list_price_bundling = fields.Float('Discount Bundling Price', default=0.0,digits=dp.get_precision('Product Price'))
    
    #Membership
    membership_cutting_sequence   = fields.Char(string='Cutting Order Code', required=True, default='A')
    
    #Material Dictionary
    material_dictionary_ids         = fields.One2many('material.dictionary.header', 'product_id', string='Material Dictionary')
    note_detail                     = fields.Text(string='Note Details')
    
    categ_secondary_id      = fields.Many2one('product.category.secondary', string='Product Category')
    procurement_status      = fields.Selection([('continue','Continue'),('discontinue','Discontinue')], string='Procurement Status', required=False, default='continue')
    
    branch_ids      = fields.Many2many('res.branch',string='Branch')
    
    state   = fields.Selection([('draft','Draft'),('propose','Waiting Approval'),('approve','Approved'),('cancel','Rejected')], string='State', default='draft', track_visibility='always')
    for_packing     = fields.Boolean(string="for Packing")
    
    @api.multi
    def action_propose(self):
        self.write({'state': 'propose'})

    @api.multi
    def action_approve(self):
        self.seller_ids.unlink()
        vals = {'name'          : self.vendor_id.id,
                'product_name'  : self.vendor_original_name.name,
                'branch_ids'    : self.branch_ids,
                'product_tmpl_id'   : self.id,}
        self.env['product.supplierinfo'].create(vals)
        self.write({'state': 'approve'})

    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})

    @api.multi
    def action_set_to_draft(self):
        self.write({'state': 'draft'})
    