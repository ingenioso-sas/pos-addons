from odoo import fields, models


class PosConfig(models.Model):

    _inherit = 'pos.config'
    _description = 'Point of Sale Configuration'

    cash_rounding = fields.Boolean(string="Cash Rounding")
