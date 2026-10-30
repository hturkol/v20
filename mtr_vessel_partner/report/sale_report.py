# SPDX-License-Identifier: LicenseRef-Projet-Proprietary
#
# Copyright (c) 2025 Projet İş Çözümleri Limited Şirketi
#
# This file is part of a proprietary Odoo addon.
# Use of this file is governed by the LICENSE file included
# in the root of this repository.

from odoo import models
from odoo.fields import Domain


class SaleReport(models.Model):
    _inherit = 'sale.report'

    def _order_line_domain(self):
        # Master quotations are commercial umbrella documents: their value is
        # carried by the generated vessel quotations, so they must not be
        # counted again in sales analysis.
        return super()._order_line_domain() & Domain(
            'order_id.is_master_quotation', '!=', True)
