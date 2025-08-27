from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    is_cash_count = fields.Boolean(string='Cash', compute="_compute_is_cash_count", store=True)

    cash_journal_id = fields.Many2one('account.journal',
        string='Journal',
        domain=[('type', 'in', ('cash', 'bank'))],
        ondelete='restrict',
        help='The payment method is of type cash. A cash statement will be automatically generated.\n' 
             'Leave empty to use the receivable account of customer.\n' 
             'Defines the journal where to book the accumulated payments (or individual payment if Identify Customer is true) after closing the session.\n' 
             'For cash journal, we directly write to the default account in the journal via statement lines.\n' 
             'For bank journal, we write to the outstanding account specified in this payment method.\n' 
             'Only cash and bank journals are allowed.')

    split_transactions = fields.Boolean(
        string='Identify Customer',
        default=False,
        help='Forces to set a customer when using this payment method and splits the journal entries for each customer. It could slow down the closing process.')
    
    active = fields.Boolean(default=True)
    type = fields.Selection(selection=[('cash', 'Cash'), ('bank', 'Bank'), ('pay_later', 'Customer Account')], compute="_compute_type")

    @api.depends('type')
    def _compute_hide_use_payment_terminal(self):
        no_terminals = not bool(self._fields['use_payment_terminal'].selection(self))
        for payment_method in self:
            payment_method.hide_use_payment_terminal = no_terminals or payment_method.type in ('cash', 'pay_later')
    
    @api.depends('cash_journal_id', 'split_transactions')
    def _compute_type(self):
        for pm in self:
            if pm.cash_journal_id.type in {'cash', 'bank'}:
                pm.type = pm.cash_journal_id.type
            else:
                pm.type = 'pay_later'

    @api.onchange('cash_journal_id')
    def _onchange_journal_id(self):
        if self.is_cash_count:
            self.use_payment_terminal = False

    @api.depends('type')
    def _compute_is_cash_count(self):
        for pm in self:
            pm.is_cash_count = pm.type == 'cash'

    @api.onchange('is_cash_count')
    def _onchange_is_cash_count(self):
        if not self.is_cash_count:
            self.cash_journal_id = False
        else:
            self.use_payment_terminal = False
