# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.tools import float_is_zero


class AccountMove(models.Model):

    _inherit = 'account.move'

    pos_payment_ids = fields.One2many('pos.payment', 'account_move_id')

    def _get_invoiced_lot_values(self):
        self.ensure_one()

        lot_values = super(AccountMove, self)._get_invoiced_lot_values()

        if self.state == 'draft':
            return lot_values

        # user may not have access to POS orders, but it's ok if they have
        # access to the invoice
        for order in self.sudo().pos_order_ids:
            for line in order.lines:
                lots = line.pack_lot_ids or False
                if lots:
                    for lot in lots:
                        lot_values.append({
                            'product_name': lot.product_id.name,
                            'quantity': line.qty if lot.product_id.tracking == 'lot' else 1.0,
                            'uom_name': line.product_uom_id.name,
                            'lot_name': lot.lot_name,
                        })
        return lot_values

    def _get_reconciled_vals(self, partial, amount, counterpart_line):
        """Add pos_payment_name field in the reconciled vals to be able to show the payment method in the invoice."""
        result = super()._get_reconciled_vals(partial, amount, counterpart_line)
        if counterpart_line.move_id.sudo().pos_payment_ids:
            pos_payment = counterpart_line.move_id.sudo().pos_payment_ids
            result['pos_payment_name'] = pos_payment.payment_method_id.name
        return result

    def _compute_amount(self):
        super(AccountMove, self)._compute_amount()
        for inv in self:
            if inv.type in ['out_invoice', 'out_refund'] and inv.pos_order_ids and any(s != 'closed' for s in inv.pos_order_ids.mapped('session_id.state')):
                amount = 0
                rounding = 0.0
                amountTotal = 0
                amountResidual = 0

                rounding = inv.pos_order_ids.currency_id.rounding
                amountResidual = inv.amount_residual
                amountTotal = inv.amount_total

                isPaid = float_is_zero(amountResidual, rounding)
                if isPaid:
                    inv.invoice_payment_state = 'paid'
                else:
                    inv.invoice_payment_state = 'not_paid'

    def with_company(self, company):
        """ with_company(company)

        Return a new version of this recordset with a modified context, such that::

            result.env.company = company
            result.env.companies = self.env.companies | company

        :param company: main company of the new environment.
        :type company: :class:`~odoo.addons.base.models.res_company` or int

        .. warning::

            When using an unauthorized company for current user,
            accessing the company(ies) on the environment may trigger
            an AccessError if not done in a sudoed environment.
        """
        if not company:
            # With company = None/False/0/[]/empty recordset: keep current environment
            return self

        company_id = int(company)
        allowed_company_ids = self.env.context.get('allowed_company_ids', [])
        if allowed_company_ids and company_id == allowed_company_ids[0]:
            return self
        # Copy the allowed_company_ids list
        # to avoid modifying the context of the current environment.
        allowed_company_ids = list(allowed_company_ids)
        if company_id in allowed_company_ids:
            allowed_company_ids.remove(company_id)
        allowed_company_ids.insert(0, company_id)

        return self.with_context(allowed_company_ids=allowed_company_ids)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _stock_account_get_anglo_saxon_price_unit(self):
        self.ensure_one()
        if not self.product_id:
            return self.price_unit
        price_unit = super(AccountMoveLine, self)._stock_account_get_anglo_saxon_price_unit()
        order = self.move_id.pos_order_ids
        if order:
            price_unit = - order._get_pos_anglo_saxon_price_unit(
                self.product_id,
                self.move_id.partner_id.id,
                self.quantity
                )
        return price_unit
