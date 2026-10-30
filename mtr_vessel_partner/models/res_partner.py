# SPDX-License-Identifier: LicenseRef-Projet-Proprietary
#
# Copyright (c) 2025 Projet İş Çözümleri Limited Şirketi
#
# This file is part of a proprietary Odoo addon.
# Use of this file is governed by the LICENSE file included
# in the root of this repository.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_vessel = fields.Boolean(
        'Vessel', copy=False, index=True,
        help='This partner is a vessel. Its parent company is the legal entity '
             'that gets invoiced for vessel orders.')
    imo_number = fields.Char('IMO Number', copy=False, index=True)
    flag_id = fields.Many2one('res.country', 'Flag')
    vessel_management_id = fields.Many2one(
        'res.partner', 'Management Company', index=True, copy=False,
        help='Ship management company operating this vessel.')

    vessel_order_ids = fields.One2many('sale.order', 'vessel_id', 'Vessel Orders', readonly=True)
    vessel_project_ids = fields.One2many('project.project', 'vessel_id', 'Vessel Projects', readonly=True)

    vessel_order_count = fields.Integer('# Orders', compute='_compute_vessel_counts', compute_sudo=True)
    vessel_project_count = fields.Integer('# Projects', compute='_compute_vessel_counts', compute_sudo=True)
    vessel_invoice_count = fields.Integer('# Invoices', compute='_compute_vessel_counts', compute_sudo=True)

    @api.constrains('is_vessel', 'imo_number', 'company_id')
    def _check_vessel_imo_unique(self):
        for partner in self.filtered(lambda p: p.is_vessel and p.imo_number):
            duplicates = self.search_count([
                ('is_vessel', '=', True),
                ('imo_number', '=', partner.imo_number),
                ('company_id', 'in', (partner.company_id.id, False)),
                ('id', '!=', partner.id),
            ])
            if duplicates:
                raise ValidationError(_(
                    'A vessel with IMO number %s already exists.', partner.imo_number))

    @api.depends('vessel_order_ids', 'vessel_project_ids', 'vessel_order_ids.invoice_ids')
    def _compute_vessel_counts(self):
        for partner in self:
            partner.vessel_order_count = len(partner.vessel_order_ids)
            partner.vessel_project_count = len(partner.vessel_project_ids)
            partner.vessel_invoice_count = len(partner._get_vessel_invoices())

    def _get_vessel_invoices(self):
        return self.vessel_order_ids.invoice_ids.filtered(
            lambda move: move.move_type in ('out_invoice', 'out_refund') and move.state != 'cancel')

    # --- Actions ---
    def action_view_vessel_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sale Orders'),
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('vessel_id', '=', self.id)],
            'context': {'default_vessel_id': self.id},
        }

    def action_view_vessel_projects(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Projects'),
            'res_model': 'project.project',
            'view_mode': 'kanban,list,form',
            'domain': [('vessel_id', '=', self.id)],
            'context': {'default_vessel_id': self.id},
        }

    def action_view_vessel_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoices'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self._get_vessel_invoices().ids)],
        }
