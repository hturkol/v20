# SPDX-License-Identifier: LicenseRef-Projet-Proprietary
#
# Copyright (c) 2025 Projet İş Çözümleri Limited Şirketi
#
# This file is part of a proprietary Odoo addon.
# Use of this file is governed by the LICENSE file included
# in the root of this repository.
from odoo import api, fields, models


class ResPartnerProduct(models.Model):
    _name = "res.partner.product"
    _description = "Customer Product"
    _order = "partner_id, sequence, id"

    sequence = fields.Integer(default=10)
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        required=True,
        ondelete="cascade",
        index=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        required=True,
        domain=[("sale_ok", "=", True)],
    )
    product_tmpl_id = fields.Many2one(
        related="product_id.product_tmpl_id",
        store=True,
        index=True,
    )
    version_id = fields.Many2one(
        comodel_name="partner.product.version",
        string="Version",
        ondelete="set null",
    )
    partner_category_ids = fields.Many2many(
        related="partner_id.category_id",
        string="Customer Tags",
        store=True,
        readonly=True,
    )
    product_tag_ids = fields.Many2many(
        related="product_id.product_tmpl_id.product_tag_ids",
        string="Product Tags",
        store=True,
        readonly=True,
    )
    note = fields.Char()

    @api.depends("partner_id", "product_id", "version_id")
    def _compute_display_name(self):
        for line in self:
            name = line.product_id.display_name or ""
            if line.version_id:
                name = f"{name} ({line.version_id.name})"
            line.display_name = name
