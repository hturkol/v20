# SPDX-License-Identifier: LicenseRef-Projet-Proprietary
#
# Copyright (c) 2025 Projet İş Çözümleri Limited Şirketi
#
# This file is part of a proprietary Odoo addon.
# Use of this file is governed by the LICENSE file included
# in the root of this repository.

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    master_line_id = fields.Many2one(
        'sale.order.line', 'Master Quotation Line', copy=False, index=True,
        help='Master quotation line this vessel order line was allocated from.')
    vessel_line_ids = fields.One2many(
        'sale.order.line', 'master_line_id', 'Vessel Lines', readonly=True, copy=False,
        help='Vessel order lines allocated from this master line.')
    allocated_amount = fields.Monetary(
        'Allocated Amount', compute='_compute_vessel_allocation', compute_sudo=True,
        currency_field='currency_id',
        help='Total amount already distributed to vessel quotations from this line.')
    remaining_amount = fields.Monetary(
        'Remaining Amount', compute='_compute_vessel_allocation', compute_sudo=True,
        currency_field='currency_id',
        help='Master line amount not yet distributed to vessel quotations.')

    @api.depends('vessel_line_ids.price_subtotal', 'vessel_line_ids.state', 'price_subtotal')
    def _compute_vessel_allocation(self):
        for line in self:
            if line.order_id.is_master_quotation:
                allocated = sum(
                    line.vessel_line_ids.filtered(
                        lambda vessel_line: vessel_line.state != 'cancel'
                    ).mapped('price_subtotal'))
                line.allocated_amount = allocated
                line.remaining_amount = line.price_subtotal - allocated
            else:
                line.allocated_amount = 0.0
                line.remaining_amount = 0.0
