# SPDX-License-Identifier: LicenseRef-Projet-Proprietary
#
# Copyright (c) 2026 Projet İş Çözümleri Limited Şirketi
#
# This file is part of a proprietary Odoo addon.
# Use of this file is governed by the LICENSE file included
# in the root of this repository.
{
    'name': 'MTR Linked Companies',
    'version': '20.0.1.0.0',
    'summary': 'Independent companies under a group company, aggregated in smart buttons',
    'description': """
Allows linking a fully independent customer/vendor (own Tax ID, own
receivable account, own payment terms) under a group company while all
standard smart buttons on the group still roll up the children's
documents.

* "Independent Company" flag on the contact form makes a child partner
  its own commercial entity again (pre-v20 behavior), so its Tax ID and
  accounting settings are never synchronized with the parent
* Bypasses the core same-Tax-ID guard so partners with existing journal
  entries can be linked under a group company
* Standard Sales / Invoices / Bills / Opportunities counters and their
  actions already aggregate over the parent hierarchy (child_of) - no
  overrides needed
* "Group Company" related field on sale orders and invoices for
  pivot/group-by reporting
* Linked Companies smart button on the group company
        """,
    'category': 'Sales',

    'author': 'Projet İş Çözümleri Ltd. Şti.',
    'website': 'https://projet.solutions',

    'depends': ['account', 'sale_management', 'project'],

    'data': [
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
    ],

    'maintainer': 'Projet İş Çözümleri Ltd. Şti.',
    'license': 'Other proprietary',

    'sequence': 1453,
    'installable': True,
    'application': False,
    'auto_install': False,
}
