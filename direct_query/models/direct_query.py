from odoo import fields, api, models
from odoo.exceptions import UserError
from datetime import datetime
import pytz
from pytz import timezone
from odoo.exceptions import Warning

class MsQuery(models.Model):

    _name = "ms.query"
    _description = "Execute Query"
    _inherit = ['mail.thread']
    
    backup = fields.Text('Backup Syntax', help="Backup your query if needed")
    name = fields.Text('Syntax', required=True)
    result = fields.Text('Result')
    summary_header = fields.Text('Summary Header')
    room_summary = fields.Text('Summary Body')


    def get_real_datetime(self):
        if not self.env.user.tz :
            raise Warning("Please set your timezone in Users menu.")
        return pytz.UTC.localize(datetime.now()).astimezone(timezone(self.env.user.tz))
    
    @api.multi
    def execute_query(self):
        all_asset_detail = []
        main_header = []
        if not self.name:
            return
        while self.name[:1] == ' ':
            self.name = self.name[1:]
        prefix = self.name[:6].upper()
        try :
            self.env.cr.execute(self.name)
        except Exception as e :
            raise UserError(e)

        if prefix == 'SELECT':
            result = self.env.cr.dictfetchall()
            if result:
                self.result = result
            else:
                self.result = "Data not found"
        elif prefix == 'UPDATE' :
            self.result = '%d row affected'%(self.env.cr.rowcount)
        else :
            self.result = 'Successful'
        self.message_post('%s<br><br>Executed on %s'%(self.name,str(self.get_real_datetime())[:19]))
