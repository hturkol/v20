# SPDX-License-Identifier: LicenseRef-Projet-Proprietary
#
# Copyright (c) 2025 Projet İş Çözümleri Limited Şirketi
#
# This file is part of a proprietary Odoo addon.
# Use of this file is governed by the LICENSE file included
# in the root of this repository.
from odoo import fields, models, _


class ResPartner(models.Model):
    _inherit = "res.partner"

    partner_product_ids = fields.One2many(
        comodel_name="res.partner.product",
        inverse_name="partner_id",
        string="Customer Products",
    )
    partner_product_count = fields.Integer(
        compute="_compute_partner_product_count",
    )

    def _compute_partner_product_count(self):
        data = self.env["res.partner.product"]._read_group(
            [("partner_id", "in", self.ids)],
            ["partner_id"],
            ["__count"],
        )
        counts = {partner.id: count for partner, count in data}
        for partner in self:
            partner.partner_product_count = counts.get(partner.id, 0)

    def action_open_product_bulk_add(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Add Products"),
            "res_model": "partner.product.bulk.add",
            "view_mode": "form",
            "target": "new",
            "context": {"default_partner_id": self.id},
        }

    def action_view_partner_products(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "partner_products.res_partner_product_action"
        )
        action["domain"] = [("partner_id", "=", self.id)]
        action["context"] = {"default_partner_id": self.id}
        return action
