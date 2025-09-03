# -*- coding: utf-8 -*-
from odoo import fields, models


class PosSession(models.Model):
    _inherit = 'pos.session'

    opening_notes = fields.Text(string="Opening Notes")

    cash_real_difference = fields.Monetary(
        string='Difference',
        readonly=True
        )
    cash_real_transaction = fields.Monetary(
        string='Transaction',
        readonly=True
        )
    cash_real_expected = fields.Monetary(string="Expected", readonly=True)

    failed_pickings = fields.Boolean(compute='_compute_picking_count')

    update_stock_at_closing = fields.Boolean(
        'Stock should be updated at closing'
        )

    def _compute_picking_count(self):
        for pos in self:
            pickings = pos.order_ids.mapped('picking_ids').filtered(lambda x: x.state != 'done')
            pos.picking_count = len(pickings.ids)

    def action_stock_picking(self):
        pickings = self.order_ids.mapped('picking_ids').filtered(lambda x: x.state != 'done')
        action_picking = self.env.ref('stock.action_picking_tree_ready')
        action = action_picking.read()[0]
        action['context'] = {}
        action['domain'] = [('id', 'in', pickings.ids)]
        return action
