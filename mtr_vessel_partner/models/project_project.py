# SPDX-License-Identifier: LicenseRef-Projet-Proprietary
#
# Copyright (c) 2025 Projet İş Çözümleri Limited Şirketi
#
# This file is part of a proprietary Odoo addon.
# Use of this file is governed by the LICENSE file included
# in the root of this repository.

from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    vessel_id = fields.Many2one(
        'res.partner', 'Vessel', index=True, copy=False, check_company=True,
        domain="[('is_vessel', '=', True)]",
        help='Vessel this project/installation is executed for.')
