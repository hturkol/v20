# SPDX-License-Identifier: LicenseRef-Projet-Proprietary
#
# Copyright (c) 2025 Projet İş Çözümleri Limited Şirketi
#
# This file is part of a proprietary Odoo addon.
# Use of this file is governed by the LICENSE file included
# in the root of this repository.
{
    'name': 'MTR Vessel Sales',
    'version': '20.0.1.0.0',
    'summary': 'Master quotation to per-vessel sale orders for maritime customers',
    'description': """
Allows preparing a single Master Quotation for a management company and
generating one sale order per vessel, invoiced to the vessel's own legal
entity, while keeping full traceability back to the master quotation.

* Vessels are partner records flagged with "Is Vessel"; their parent
  (Company) is the legal entity that gets invoiced
* Master Quotation flag on sale orders with a vessel quotation smart button
* Wizard to generate per-vessel quotations from an allocation matrix that
  splits the discounted master line totals over the vessels (equal split
  suggested, freely adjustable per vessel, soft warning on mismatch)
* Duplicate protection per Master Quotation + Vessel
* Per-line allocated/remaining tracking on the master quotation
* Master quotations are kept out of the sales report to avoid double counting
* Vessel link on projects generated from vessel sale orders
        """,
    'category': 'Sales',

    'author': 'Projet İş Çözümleri Ltd. Şti.',
    'website': 'https://projet.solutions',

    'depends': ['sale_management', 'project'],

    'data': [
        'security/ir.model.access.csv',

        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/project_project_views.xml',

        'wizards/mtr_vessel_partner_wizard_views.xml',
    ],

    'maintainer': 'Projet İş Çözümleri Ltd. Şti.',
    'license': 'Other proprietary',

    'sequence': 1453,
    'installable': True,
    'application': False,
    'auto_install': False,
}
