# SPDX-License-Identifier: LicenseRef-Projet-Proprietary
#
# Copyright (c) 2025 Projet İş Çözümleri Limited Şirketi
#
# This file is part of a proprietary Odoo addon.
# Use of this file is governed by the LICENSE file included
# in the root of this repository.
{
    "name": "Partner Products",
    "summary": "Track which products each customer owns and their assigned groups",
    "version": "20.0.1.0.0",
    "development_status": "Production/Stable",
    "author": "Projet İş Çözümleri Ltd. Şti.",
    "website": "https://projet.solutions",
    "category": "Sales Management",
    "license": "Other proprietary",
    "depends": ["contacts", "product"],
    "data": [
        "security/ir.access.csv",
        "wizards/partner_product_bulk_add_views.xml",
        "views/partner_product_version_views.xml",
        "views/res_partner_product_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "sequence": 1453,
    "maintainer": "Projet İş Çözümleri Ltd. Şti.",
}
