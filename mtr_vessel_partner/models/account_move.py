# SPDX-License-Identifier: LicenseRef-Projet-Proprietary
#
# Copyright (c) 2025 Projet İş Çözümleri Limited Şirketi
#
# This file is part of a proprietary Odoo addon.
# Use of this file is governed by the LICENSE file included
# in the root of this repository.

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    vessel_id = fields.Many2one(
        'res.partner', 'Vessel', compute='_compute_vessel_id', compute_sudo=True,
        help='Vessel linked through the originating sale order. '
             'Empty when the invoice lines relate to multiple vessels or none.')

    @api.depends('invoice_line_ids.sale_line_ids.order_id.vessel_id')
    def _compute_vessel_id(self):
        for move in self:
            vessels = move.invoice_line_ids.sale_line_ids.order_id.vessel_id
            move.vessel_id = vessels[:1] if len(vessels) == 1 else False
