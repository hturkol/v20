# SPDX-License-Identifier: LicenseRef-Projet-Proprietary
#
# Copyright (c) 2025 Projet İş Çözümleri Limited Şirketi
#
# This file is part of a proprietary Odoo addon.
# Use of this file is governed by the LICENSE file included
# in the root of this repository.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Command


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_master_quotation = fields.Boolean(
        'Is Master Quotation', tracking=True, copy=False,
        help='A master quotation is the umbrella commercial document of a management company. '
             'It cannot be confirmed or invoiced; per-vessel quotations are generated from it.')
    master_order_id = fields.Many2one(
        'sale.order', 'Master Quotation', copy=False, index=True,
        domain="[('is_master_quotation', '=', True)]",
        help='Master quotation this vessel quotation was generated from.')
    vessel_order_ids = fields.One2many(
        'sale.order', 'master_order_id', 'Vessel Quotations', readonly=True, copy=False)
    vessel_order_count = fields.Integer(
        '# Vessel Quotations', compute='_compute_vessel_order_count', compute_sudo=True)
    vessel_id = fields.Many2one(
        'res.partner', 'Vessel', copy=False, index=True, tracking=True, check_company=True,
        domain="[('is_vessel', '=', True)]",
        help='Vessel (partner record) this quotation was created for. The order is '
             'invoiced to the vessel\'s legal entity.')

    _master_vessel_uniq = models.Constraint(
        'UNIQUE(master_order_id, vessel_id)',
        'A quotation already exists for this vessel under the same master quotation.',
    )

    @api.depends('vessel_order_ids')
    def _compute_vessel_order_count(self):
        for order in self:
            order.vessel_order_count = len(order.vessel_order_ids)

    @api.constrains('is_master_quotation', 'master_order_id')
    def _check_master_quotation(self):
        for order in self:
            if order.master_order_id == order:
                raise ValidationError(_('An order cannot be its own master quotation.'))
            if order.is_master_quotation and order.master_order_id:
                raise ValidationError(
                    _('A master quotation cannot be linked to another master quotation.'))

    @api.onchange('vessel_id')
    def _onchange_vessel_id(self):
        # When a vessel is picked manually on the order, its legal entity
        # (the vessel's parent company) becomes the invoicing customer.
        if self.vessel_id and not self.is_master_quotation:
            self.partner_id = self.vessel_id.parent_id or self.vessel_id

    # --- Actions ---
    def action_confirm(self):
        masters = self.filtered('is_master_quotation')
        if masters:
            raise ValidationError(_(
                'Master quotations (%(names)s) are commercial umbrella documents and cannot be '
                'confirmed or invoiced. Create vessel quotations instead.',
                names=', '.join(masters.mapped('name'))))
        res = super().action_confirm()
        self._propagate_vessel_to_projects()
        return res

    def action_create_vessel_quotations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Vessel Quotations'),
            'res_model': 'mtr.vessel.quotation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_master_order_id': self.id},
        }

    def action_view_vessel_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Vessel Quotations'),
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.vessel_order_ids.ids)],
            'context': {'default_master_order_id': self.id},
        }

    # --- Vessel order creation ---
    def _get_vessel_allocation_suggestions(self, vessels):
        """Suggest how to split each master line total over the given vessels.

        Each suggestion splits the line's *remaining* amount (master subtotal minus
        what was already allocated to earlier vessel orders) equally; the last
        vessel absorbs the rounding remainder. Suggestions are only defaults —
        the user is expected to adjust them in the allocation matrix.
        """
        self.ensure_one()
        suggestions = []
        product_lines = self.order_line.filtered(
            lambda line: not line.display_type and not line.is_downpayment)
        count = len(vessels)
        for line in product_lines:
            remaining = max(0.0, line.price_subtotal - line.allocated_amount)
            share = self.currency_id.round(remaining / count) if count else 0.0
            distributed = 0.0
            for index, vessel in enumerate(vessels):
                if index == count - 1:
                    amount = self.currency_id.round(remaining - distributed)
                else:
                    amount = share
                    distributed = self.currency_id.round(distributed + amount)
                suggestions.append({
                    'vessel_id': vessel.id,
                    'order_line_id': line.id,
                    'amount': max(0.0, amount),
                })
        return suggestions

    def _create_vessel_order(self, vessel, allocations=None):
        self.ensure_one()
        existing = self.vessel_order_ids.filtered(lambda order: order.vessel_id == vessel)
        if existing:
            state_label = dict(existing[:1]._fields['state'].selection)[existing[:1].state]
            raise ValidationError(_(
                'A quotation (%(order)s, state: %(state)s) already exists for vessel %(vessel)s '
                'under this master quotation.',
                order=existing[:1].name, state=state_label, vessel=vessel.name))
        return self.env['sale.order'].create(
            self._prepare_vessel_order_vals(vessel, allocations=allocations))

    def _prepare_vessel_order_vals(self, vessel, allocations=None):
        self.ensure_one()
        order_lines = []
        for line in self.order_line:
            if line.is_downpayment:
                continue
            if not line.display_type and allocations is not None:
                if line.id not in allocations:
                    continue
                order_lines.append(Command.create(
                    self._prepare_vessel_order_line_vals(line, amount=allocations[line.id])))
            else:
                order_lines.append(Command.create(self._prepare_vessel_order_line_vals(line)))
        vals = {
            # The order is invoiced to the vessel's legal entity: the vessel's
            # parent company when set, otherwise the vessel partner itself.
            'partner_id': (vessel.parent_id or vessel).id,
            'pricelist_id': self.pricelist_id.id,
            'currency_id': self.currency_id.id,
            'payment_term_id': self.payment_term_id.id,
            'team_id': self.team_id.id,
            'user_id': self.user_id.id,
            'company_id': self.company_id.id,
            'validity_date': self.validity_date,
            'origin': self.name,
            'client_order_ref': vessel.name,
            'note': self.note,
            'master_order_id': self.id,
            'vessel_id': vessel.id,
            'order_line': order_lines,
        }
        for fname in ('opportunity_id', 'campaign_id', 'medium_id', 'source_id'):
            if fname in self._fields and self[fname]:
                vals[fname] = self[fname].id
        return vals

    def _prepare_vessel_order_line_vals(self, line, amount=None):
        vals = {
            'display_type': line.display_type,
            'name': line.name,
            'sequence': line.sequence,
        }
        if line.display_type:
            return vals
        vals.update({
            'product_id': line.product_id.id,
            'product_uom_qty': line.product_uom_qty if amount is None else 1.0,
            'product_uom_id': line.product_uom_id.id,
            'price_unit': line.price_unit if amount is None else amount,
            'discount': line.discount if amount is None else 0.0,
        })
        if amount is not None:
            vals['master_line_id'] = line.id
        if line.tax_ids:
            vals['tax_ids'] = [Command.set(line.tax_ids.ids)]
        if 'analytic_distribution' in line._fields and line.analytic_distribution:
            vals['analytic_distribution'] = line.analytic_distribution
        return vals

    # --- Project integration ---
    def _propagate_vessel_to_projects(self):
        for order in self.filtered('vessel_id'):
            projects = self.env['project.project']
            for fname in ('project_id', 'project_ids'):
                if fname in order._fields:
                    projects |= order[fname]
            projects = projects.filtered(lambda project: not project.vessel_id)
            if projects:
                projects.vessel_id = order.vessel_id.id
