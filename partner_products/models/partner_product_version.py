# SPDX-License-Identifier: LicenseRef-Projet-Proprietary
#
# Copyright (c) 2025 Projet İş Çözümleri Limited Şirketi
#
# This file is part of a proprietary Odoo addon.
# Use of this file is governed by the LICENSE file included
# in the root of this repository.
from odoo import fields, models


class PartnerProductVersion(models.Model):
    _name = "partner.product.version"
    _description = "Customer Product Version"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    product_tmpl_ids = fields.Many2many(
        comodel_name="product.template",
        string="Products",
        help="Leave empty to make this version available for all products.",
    )
