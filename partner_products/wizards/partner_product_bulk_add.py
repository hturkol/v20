# SPDX-License-Identifier: LicenseRef-Projet-Proprietary
#
# Copyright (c) 2025 Projet İş Çözümleri Limited Şirketi
#
# This file is part of a proprietary Odoo addon.
# Use of this file is governed by the LICENSE file included
# in the root of this repository.
from odoo import api, fields, models


class PartnerProductBulkAdd(models.TransientModel):
    _name = "partner.product.bulk.add"
    _description = "Bulk Add Products to Customer"

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        required=True,
        readonly=True,
    )
    version_id = fields.Many2one(
        comodel_name="partner.product.version",
        string="Group",
    )
    categ_id = fields.Many2one(
        comodel_name="product.category",
        string="Product Category",
    )
    tag_ids = fields.Many2many(
        comodel_name="product.tag",
        string="Tags",
    )
    product_ids = fields.Many2many(
        comodel_name="product.product",
        string="Products",
        domain=[("sale_ok", "=", True)],
    )

    @api.onchange("version_id", "categ_id", "tag_ids")
    def _onchange_fill_products(self):
        version_products = (
            self.version_id.product_tmpl_ids.product_variant_ids
            if self.version_id
            else self.env["product.product"].browse()
        )
        if not version_products and not self.categ_id and not self.tag_ids:
            return
        products = version_products
        if self.categ_id or self.tag_ids:
            domain = [("sale_ok", "=", True)]
            if self.categ_id:
                domain.append(
                    ("product_tmpl_id.categ_id", "child_of", self.categ_id.id)
                )
            if self.tag_ids:
                domain.append(
                    ("all_product_tag_ids", "in", self.tag_ids.ids)
                )
            filtered = self.env["product.product"].search(domain)
            products = products & filtered if products else filtered
        self.product_ids = products

    def action_add(self):
        self.ensure_one()
        existing = self.partner_id.partner_product_ids.product_id
        self.env["res.partner.product"].create(
            [
                {
                    "partner_id": self.partner_id.id,
                    "product_id": product.id,
                    "version_id": self.version_id.id,
                }
                for product in self.product_ids - existing
            ]
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "view_mode": "form",
            "res_id": self.partner_id.id,
            "target": "current",
        }
