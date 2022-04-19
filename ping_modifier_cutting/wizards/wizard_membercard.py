from odoo import models, fields, api, _


class MembercardWizz(models.TransientModel):
    _name = 'membercard.wizz'
    
    name            = fields.Char(string='Name', required=False)
    partner_id      = fields.Many2one('res.partner',string='Member', required=True)
    ##Attachment
#     image_payment_attachment          = fields.Binary(string='Upload Payment')
#     payment_attachment_name     = fields.Char(string='Payment Attachment')


    # image: all image fields are base64 encoded and PIL-supported
    image = fields.Binary("Image", attachment=True,
        help="This field holds the image used as avatar for this contact, limited to 1024x1024px",)
    image_medium = fields.Binary("Medium-sized image", attachment=True,
        help="Medium-sized image of this contact. It is automatically "\
             "resized as a 128x128px image, with aspect ratio preserved. "\
             "Use this field in form views or some kanban views.")
    image_small = fields.Binary("Small-sized image", attachment=True,
        help="Small-sized image of this contact. It is automatically "\
             "resized as a 64x64px image, with aspect ratio preserved. "\
             "Use this field anywhere a small image is required.")
    
    
    
    @api.multi
    def print_membercard(self):
#         self.filtered(lambda s: s.state == 'draft').write({'state': 'sent'})
        print "self-->", self.partner_id.write({'image_background_membercard_medium' : self.image})
        return self.env['report'].get_action(self.partner_id, 'ping_modifier_cutting.report_member_card_ping')
    
    
#     @api.multi
#     def packing_process(self):
#         active_id = self.env.context.get('active_id')
#         for o in self:
#             ##Insert Packing Cover
#             packing_item_exist = self.env['packing.items'].search([('product_id','=',o.product_id.id),('cutting_id','=',o.cutting_id.id)])
#             if packing_item_exist:
#                 packing_item_exist.write({'quantity_done' : packing_item_exist.quantity_done + 1})
#             else:
#                 self.env['packing.items'].create({'product_id' : o.product_id.id, 'quantity_done': 1, 'cutting_id' : o.cutting_id.id})
#             ##Insert Packing Items
#             packing_product_id = self.env['packing.product'].create({'name' : o.name, 'cutting_id' : o.cutting_id.id})
#             for l in o.cutting_line:
#                 l.write({'packing_product_id' : packing_product_id.id})
