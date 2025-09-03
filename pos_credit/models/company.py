from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    account_journal_payment_debit_account_id = fields.Many2one(
        'account.account',
        string='Journal Outstanding Receipts Account'
        )
