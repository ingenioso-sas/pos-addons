# Copyright 2017 Artyom Losev
# Copyright 2018 Kolushov Alexandr <https://it-projects.info/team/KolushovAlexandr>
# License MIT (https://opensource.org/licenses/MIT).

from functools import reduce
from pyexpat import model
import psycopg2
import logging
from odoo import _, api, fields, models, tools
from odoo.tools import float_is_zero, float_round
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

SO_CHANNEL = "pos_sale_orders"
INV_CHANNEL = "pos_invoices"


class PosOrder(models.Model):
    _inherit = "pos.order"

    invoice_to_pay = fields.Boolean(
        string='',
        default=False,
        help='')

    @api.model
    def _order_fields(self, ui_order):
        """
            Se anaden campos para verificar si es un pago de una factura existente
            (invoice_to_pay.id) o es una nueva factura.
        """
        process_line = super(PosOrder, self)._order_fields(ui_order) 
        if 'invoice_to_pay' in (ui_order):
            # factura existente con id ui_order['invoice_to_pay']['id']
            process_line['invoice_to_pay'] = ui_order['invoice_to_pay']     
            process_line['account_move'] = ui_order['invoice_to_pay']['id']     
            process_line['state'] = 'invoiced' # orden ya facturada
        else:
            process_line['invoice_to_pay'] = False
        
        return process_line

    @api.model
    def process_invoices_creation(self, sale_order_id):
        order = self.env["sale.order"].browse(sale_order_id)
        inv_id = order._create_invoices(final=True)
        if inv_id.state == 'draft': # factura sin publicar publicada
            inv_id.sudo().with_context(force_company=order.company_id.id).action_post()
            # inv_id.sudo().with_context(force_company=order.company_id.id).post()
        return inv_id.id


    def action_pos_order_paid(self):
        if not self._is_pos_order_paid():
            raise UserError(_("Order %s is not fully paid.") % self.name)
        if(self.invoice_to_pay):
            self.write({'state': 'invoiced'})
        else:
            self.write({'state': 'paid'})
        return self.create_picking()

    # @api.model
    # def create_from_ui(self, orders, draft=False):
    #     invoices_to_pay = [o for o in orders if o.get("data").get("invoice_to_pay")]
    #     original_orders = [o for o in orders if o not in invoices_to_pay]

    #     res = super(PosOrder, self).create_from_ui(original_orders, draft=draft)
    #     if invoices_to_pay:
    #         self.create_from_ui_aux(invoices_to_pay, draft=draft)

    #     return res

    # def create_from_ui_aux(self, orders, draft=False):
    #     """ Create and update Orders from the frontend PoS application.

    #     Create new orders and update orders that are in draft status. If an order already exists with a status
    #     diferent from 'draft'it will be discareded, otherwise it will be saved to the database. If saved with
    #     'draft' status the order can be overwritten later by this function.

    #     :param orders: dictionary with the orders to be created.
    #     :type orders: dict.
    #     :param draft: Indicate if the orders are ment to be finalised or temporarily saved.
    #     :type draft: bool.
    #     :Returns: list -- list of db-ids for the created and updated orders.
    #     """
    #     order_ids = []
    #     for order in orders:
    #         existing_order = False
    #         if 'server_id' in order['data']:
    #             existing_order = self.env['pos.order'].search(
    #                 ['|', ('id', '=', order['data']['server_id']), ('pos_reference', '=', order['data']['name'])],
    #                 limit=1)
    #         order_aux = order['data']
    #         # statement_ids = order["statement_ids"]
    #         invoice_to_pay = order_aux["invoice_to_pay"]
    #         # original_order = self.env['pos.order'].search([('account_move', '=', invoice_to_pay["id"])])
    #         # total_pay = reduce(lambda x, y: x + y, [x[2]["amount"] for x in statement_ids])
    #         # total_pay = invoice_to_pay['amount_residual']
    #         # order_aux['amount_total'] = total_pay
    #         # order_aux['amount_paid'] = total_pay
    #         # order_aux['amount_return'] = order_aux['amount_return'] - total_pay
    #         # order_aux['account_move'] = invoice_to_pay["id"]
    #         # order_aux['state'] = "invoiced"
    #         # order_aux['to_invoice'] = True
    #         # order_aux["partner_id"] = invoice_to_pay['partner_id'][0]
    #         if (existing_order and existing_order.state == 'draft') or not existing_order:
    #             order_id = self._process_order(order, draft, existing_order)
    #             # original_order = self.env['pos.order'].search([('id', '=', order_id)])                existing_order = existing_order[0]
    #             ## aplicar en tiempo real el pago e las facturas sin esperar a cerrar sala
    #             # order._apply_invoice_payments()
    #             order_ids.append(order_id)
    #     return self.env['pos.order'].search_read(domain=[('id', 'in', order_ids)], fields = ['id', 'pos_reference'])

    # def _apply_invoice_payments(self):
    #     """
    #         Utilizado para aplicar en tiempo real el pago e las facturas sin esperar a cerrar sala
    #     """
    #     receivable_account = self.env["res.partner"]._find_accounting_partner(self.partner_id).property_account_receivable_id
    #     payment_moves = self.payment_ids._create_payment_moves()
    #     invoice_receivable = self.account_move.line_ids.filtered(lambda line: line.account_id == receivable_account)
    #     # Reconcile the invoice to the created payment moves.
    #     # But not when the invoice's total amount is zero because it's already reconciled.
    #     if not invoice_receivable.reconciled and receivable_account.reconcile:
    #         payment_receivables = payment_moves.mapped('line_ids').filtered(lambda line: line.account_id == receivable_account)
    #         (invoice_receivable | payment_receivables).reconcile()

class AccountPayment(models.Model):
    _inherit = "account.payment"

    pos_session_id = fields.Many2one("pos.session", string="POS session")
    cashier = fields.Many2one("res.users")
    datetime = fields.Datetime(string="Datetime", default=fields.Datetime.now)


class AccountInvoice(models.Model):
    _inherit = "account.move"

    def action_updated_invoice(self):
        message = {"channel": INV_CHANNEL, "id": self.id}
        self.env["pos.config"].search([])._send_to_channel(INV_CHANNEL, message)

    @api.model
    def get_invoice_lines_for_pos(self, move_ids):
        res = self.env["account.move.line"].search_read(
            [("mode_id", "in", move_ids)],
            [
                "id",
                "move_id",
                "name",
                "account",
                "product",
                "price_unit",
                "qty",
                "tax",
                "discount",
                "amount",
            ],
        )
        return res

    @api.depends("payment_move_line_ids.amount_residual")
    def _get_payment_info_JSON(self):
        for record in self:
            if not record.payment_move_line_ids:
                pass
            for move in record.payment_move_line_ids:
                if move.payment_id.cashier:
                    if move.move_id.ref:
                        move.move_id.ref = "{} by {}".format(
                            move.move_id.ref, move.payment_id.cashier.name
                        )
                    else:
                        move.move_id.name = "{} by {}".format(
                            move.move_id.name, move.payment_id.cashier.name
                        )
        data = super(AccountInvoice, self)._get_payment_info_JSON()
        return data


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_updated_sale_order(self):
        message = {"channel": SO_CHANNEL, "id": self.id}
        self.env["pos.config"].search([])._send_to_channel(SO_CHANNEL, message)

    @api.model
    def get_order_lines_for_pos(self, sale_order_ids):
        res = []
        order_lines = self.env["sale.order.line"].search(
            [("order_id", "in", sale_order_ids)]
        )
        for i in order_lines:
            line = {
                "order_id": i.order_id.id,
                "id": i.id,
                "name": i.name,
                "product": i.product_id.name,
                "uom_qty": i.product_uom_qty,
                "qty_delivered": i.qty_delivered,
                "qty_invoiced": i.qty_invoiced,
                "tax": [tax.name or " " for tax in i.tax_id],
                "discount": i.discount,
                "subtotal": i.price_subtotal,
                "total": i.price_total,
                "invoiceble": (
                    (i.qty_delivered > 0) or (i.product_id.invoice_policy == "order")
                ),
            }
            res.append(line)
        return res


class PosConfig(models.Model):
    _inherit = "pos.config"

    def _get_default_writeoff_account(self):
        acc = self.env["account.account"].search([("code", "=", 220000)]).id
        return acc if acc else False

    show_invoices = fields.Boolean(help="Show invoices in POS", default=True)
    show_sale_orders = fields.Boolean(help="Show sale orders in POS", default=True)
    pos_invoice_pay_writeoff_account_id = fields.Many2one(
        "account.account",
        string="Difference Account",
        help="The account is used for the difference between due and paid amount",
        default=_get_default_writeoff_account,
    )
    invoice_cashier_selection = fields.Boolean(
        string="Select Invoice Cashier",
        help="Ask for a cashier when fetch invoices",
        defaul=True,
    )
    sale_order_cashier_selection = fields.Boolean(
        string="Select Sale Order Cashier",
        help="Ask for a cashier when fetch orders",
        defaul=True,
    )


class PosSession(models.Model):
    _inherit = "pos.session"

    session_payments = fields.One2many(
        "account.bank.statement",
        "pos_session_id",
        string="Invoice Payments",
        help="Show invoices paid in the Session",
    )
    session_invoices_total = fields.Float(
        "Invoices", compute="_compute_session_invoices_total"
    )

    def _compute_session_invoices_total(self):
         for rec in self:
            rec.session_invoices_total = sum(
                rec.session_payments.mapped("move_line_ids").mapped("move_id").mapped("amount_total") + [0]
            )

    def action_invoice_payments(self):
        ## relacionado con odoo/addons/account/models/account_bank_statement.py [fast_counterpart_creation]
        payments = self.env["account.bank.statement"].search(
            [("pos_session_id", "in", self.ids)]
        )
        invoices = payments.mapped("move_line_ids").mapped("move_id").ids
        domain = [("id", "in", invoices)]
        return {
            "name": _("Invoice Payments"),
            "type": "ir.actions.act_window",
            "domain": domain,
            "res_model": "account.move",
            "view_type": "form",
            "view_mode": "tree,form",
        }

class AccountMove(models.Model):

    _inherit = 'account.move'
    # pos_payment_ids = fields.One2many('pos.payment', 'account_move_id')

    def _compute_amount(self):

        super(AccountMove, self)._compute_amount()        
        for inv in self:            
            if inv.type in ['out_invoice', 'out_refund'] and inv.pos_order_ids and any(s != 'closed' for s in inv.pos_order_ids.mapped('session_id.state')):
                rounding = inv.pos_order_ids.currency_id.rounding
                amountResidual = inv.amount_residual
                # amountTotal = inv.amount_total

                isPaid = float_is_zero(amountResidual, rounding)
                if isPaid:
                    inv.invoice_payment_state = 'paid'
                
                else:
                    inv.invoice_payment_state = 'not_paid'



class PostPayment(models.Model):
    _inherit = "pos.payment"

    account_move_id = fields.Many2one('account.move')

    # def _create_payment_moves(self):
    #     result = self.env['account.move']
    #     for payment in self:
    #         order = payment.pos_order_id
    #         payment_method = payment.payment_method_id
    #         # if payment_method.type == 'pay_later' or float_is_zero(payment.amount, precision_rounding=order.currency_id.rounding):
    #         if float_is_zero(payment.amount, precision_rounding=order.currency_id.rounding):
    #             continue
    #         accounting_partner = self.env["res.partner"]._find_accounting_partner(payment.partner_id)
    #         pos_session = order.session_id
    #         journal = pos_session.config_id.journal_id
    #         payment_move = self.env['account.move'].with_context(default_journal_id=journal.id).create({
    #             'journal_id': journal.id,
    #             'date': fields.Date.context_today(payment),
    #             'ref': _('Invoice payment for %s (%s) using %s') % (order.name, order.account_move.name, payment_method.name),
    #             'pos_payment_ids': payment.ids,
    #         })
    #         result |= payment_move
    #         payment.write({'account_move_id': payment_move.id})
    #         amounts = pos_session._update_amounts({'amount': 0, 'amount_converted': 0}, {'amount': payment.amount}, payment.payment_date)
    #         credit_line_vals = pos_session._credit_amounts({
    #             'account_id': accounting_partner.property_account_receivable_id.id,
    #             'partner_id': accounting_partner.id,
    #             'move_id': payment_move.id,
    #         }, amounts['amount'], amounts['amount_converted'])
    #         debit_line_vals = pos_session._debit_amounts({
    #             'account_id': pos_session.company_id.account_default_pos_receivable_account_id.id,
    #             'move_id': payment_move.id,
    #         }, amounts['amount'], amounts['amount_converted'])
    #         self.env['account.move.line'].with_context(check_move_validity=False).create([credit_line_vals, debit_line_vals])
    #         payment_move.post()
    #     return result  


class PosPaymentMethod(models.Model):
    _name = "pos.payment.method"
    _description = "Point of Sale Payment Methods"
    _order = "id asc"
    _inherit = 'pos.payment.method'

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
    
    is_cash_count = fields.Boolean(string='Cash', compute="_compute_is_cash_count", store=True)
    active = fields.Boolean(default=True)
    type = fields.Selection(selection=[('cash', 'Cash'), ('bank', 'Bank'), ('pay_later', 'Customer Account')], compute="_compute_type")
    hide_use_payment_terminal = fields.Boolean(compute='_compute_hide_use_payment_terminal', help='Technical field which is used to '
                                               'hide use_payment_terminal when no payment interfaces are installed.')
                                               
    @api.depends('type')
    def _compute_is_cash_count(self):
        for pm in self:
            pm.is_cash_count = pm.type == 'cash'
    

    @api.depends('cash_journal_id', 'split_transactions')
    def _compute_type(self):
        for pm in self:
            if pm.cash_journal_id.type in {'cash', 'bank'}:
                pm.type = pm.cash_journal_id.type
            else:
                pm.type = 'pay_later'

    @api.depends('type')
    def _compute_hide_use_payment_terminal(self):
        no_terminals = not bool(self._fields['use_payment_terminal'].selection(self))
        for payment_method in self:
            payment_method.hide_use_payment_terminal = no_terminals or payment_method.type in ('cash', 'pay_later')
