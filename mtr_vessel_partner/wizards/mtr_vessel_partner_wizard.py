# SPDX-License-Identifier: LicenseRef-Projet-Proprietary
#
# Copyright (c) 2025 Projet İş Çözümleri Limited Şirketi
#
# This file is part of a proprietary Odoo addon.
# Use of this file is governed by the LICENSE file included
# in the root of this repository.

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tools import float_is_zero
from odoo.tools.misc import format_amount


class MtrVesselQuotationWizard(models.TransientModel):
    _name = 'mtr.vessel.quotation.wizard'
    _description = 'Create Vessel Quotations Wizard'

    master_order_id = fields.Many2one('sale.order', 'Master Quotation', required=True, readonly=True)
    partner_id = fields.Many2one(related='master_order_id.partner_id', string='Management Company')
    currency_id = fields.Many2one(related='master_order_id.currency_id')
    line_ids = fields.One2many('mtr.vessel.quotation.wizard.line', 'wizard_id', 'Vessels')
    alloc_ids = fields.One2many('mtr.vessel.quotation.wizard.alloc', 'wizard_id', 'Allocation')
    distribution_warning = fields.Html(
        'Allocation Differences', compute='_compute_distribution_warning', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        master = self.env['sale.order'].browse(
            self.env.context.get('default_master_order_id')
            or self.env.context.get('active_id'))
        if not master.exists():
            return res
        vessels = self.env['res.partner'].search([
            ('is_vessel', '=', True),
            ('vessel_management_id.commercial_partner_id', '=',
             master.partner_id.commercial_partner_id.id),
        ])
        existing = {
            order.vessel_id.id: order.id
            for order in master.vessel_order_ids
            if order.vessel_id
        }
        new_vessels = vessels.filtered(lambda vessel: vessel.id not in existing)
        if 'line_ids' in fields_list:
            res['line_ids'] = [
                Command.create({
                    'vessel_id': vessel.id,
                    'sale_order_id': existing.get(vessel.id),
                    'selected': vessel.id not in existing,
                })
                for vessel in vessels
            ]
        if 'alloc_ids' in fields_list and new_vessels:
            res['alloc_ids'] = [
                Command.create(alloc_vals)
                for alloc_vals in master._get_vessel_allocation_suggestions(new_vessels)
            ]
        return res

    @api.depends('line_ids.selected', 'alloc_ids.order_line_id', 'alloc_ids.amount')
    def _compute_distribution_warning(self):
        for wizard in self:
            if not wizard.master_order_id or not wizard.currency_id:
                wizard.distribution_warning = False
                continue
            selected_vessels = wizard.line_ids.filtered('selected').vessel_id
            items = []
            for line in wizard.master_order_id.order_line:
                if line.display_type or line.is_downpayment:
                    continue
                allocated = line.allocated_amount + sum(
                    wizard.alloc_ids.filtered(
                        lambda alloc: alloc.order_line_id == line
                        and alloc.vessel_id in selected_vessels).mapped('amount'))
                difference = line.price_subtotal - allocated
                if not float_is_zero(difference, precision_rounding=wizard.currency_id.rounding):
                    items.append('<li>%s: %s / %s (%s %s)</li>' % (
                        line.name.split('\n')[0],
                        format_amount(self.env, allocated, wizard.currency_id),
                        format_amount(self.env, line.price_subtotal, wizard.currency_id),
                        _('difference:'),
                        format_amount(self.env, difference, wizard.currency_id),
                    ))
            if items:
                wizard.distribution_warning = (
                    '<div class="alert alert-warning" role="alert">'
                    '<strong>%s</strong><ul class="mb-0">%s</ul></div>'
                ) % (_('Allocated amounts differ from the master line totals:'), ''.join(items))
            else:
                wizard.distribution_warning = False

    def action_create_quotations(self):
        self.ensure_one()
        master = self.master_order_id
        lines = self.line_ids.filtered(lambda line: line.selected and not line.sale_order_id)
        if not lines:
            raise UserError(_('Please select at least one vessel without an existing quotation.'))
        # Selected vessels without any allocation rows (e.g. added manually to
        # the list) get automatic suggestions based on the remaining amounts.
        fallback_vessels = lines.vessel_id.filtered(
            lambda vessel: vessel not in self.alloc_ids.vessel_id)
        fallback = {
            (suggestion['vessel_id'], suggestion['order_line_id']): suggestion['amount']
            for suggestion in master._get_vessel_allocation_suggestions(fallback_vessels)
        }
        orders = self.env['sale.order']
        for line in lines:
            allocations = {
                alloc.order_line_id.id: alloc.amount
                for alloc in self.alloc_ids
                if alloc.vessel_id == line.vessel_id
            }
            for (vessel_id, order_line_id), amount in fallback.items():
                if vessel_id == line.vessel_id.id:
                    allocations.setdefault(order_line_id, amount)
            order = master._create_vessel_order(line.vessel_id, allocations=allocations)
            orders |= order
            line.sale_order_id = order
        if self.distribution_warning:
            master.message_post(
                body=Markup('<p>%s</p>%s') % (
                    _('Vessel quotations %s created.', ', '.join(orders.mapped('name'))),
                    Markup(self.distribution_warning)),
                message_type='notification')
        else:
            master.message_post(
                body=_('Vessel quotations created: %s', ', '.join(orders.mapped('name'))),
                message_type='notification')
        return orders._get_records_action(name=_('Vessel Quotations'))


class MtrVesselQuotationWizardLine(models.TransientModel):
    _name = 'mtr.vessel.quotation.wizard.line'
    _description = 'Vessel Quotation Wizard Line'

    wizard_id = fields.Many2one('mtr.vessel.quotation.wizard', required=True, ondelete='cascade')
    selected = fields.Boolean('Create', default=True)
    vessel_id = fields.Many2one(
        'res.partner', 'Vessel', required=True, domain="[('is_vessel', '=', True)]")
    partner_id = fields.Many2one(
        related='vessel_id.parent_id', string='Legal Entity')
    imo_number = fields.Char(related='vessel_id.imo_number', string='IMO Number')
    sale_order_id = fields.Many2one('sale.order', 'Existing Quotation', readonly=True)
    allocated_total = fields.Monetary(
        'Allocated Total', compute='_compute_allocated_total',
        currency_field='currency_id', readonly=True)
    currency_id = fields.Many2one(related='wizard_id.currency_id')

    @api.depends('wizard_id.alloc_ids.vessel_id', 'wizard_id.alloc_ids.amount')
    def _compute_allocated_total(self):
        for line in self:
            line.allocated_total = sum(
                line.wizard_id.alloc_ids.filtered(
                    lambda alloc: alloc.vessel_id == line.vessel_id).mapped('amount'))

    @api.onchange('vessel_id')
    def _onchange_vessel_id(self):
        existing = {
            order.vessel_id.id: order.id
            for order in self.wizard_id.master_order_id.vessel_order_ids
            if order.vessel_id
        }
        self.sale_order_id = existing.get(self.vessel_id.id)
        self.selected = not self.sale_order_id

    @api.constrains('vessel_id')
    def _check_vessel_id(self):
        for line in self:
            others = line.wizard_id.line_ids - line
            if line.vessel_id and line.vessel_id in others.vessel_id:
                raise ValidationError(
                    _('Vessel %s is already in the list.', line.vessel_id.display_name))


class MtrVesselQuotationWizardAlloc(models.TransientModel):
    _name = 'mtr.vessel.quotation.wizard.alloc'
    _description = 'Vessel Quotation Allocation Line'

    wizard_id = fields.Many2one('mtr.vessel.quotation.wizard', required=True, ondelete='cascade')
    # NOTE: readonly values are skipped by the web client when saving o2m
    # records — the view must keep force_save="1" on vessel_id/order_line_id.
    vessel_id = fields.Many2one(
        'res.partner', 'Vessel', required=True, readonly=True,
        domain="[('is_vessel', '=', True)]")
    order_line_id = fields.Many2one(
        'sale.order.line', 'Master Line', required=True, readonly=True)
    product_id = fields.Many2one(related='order_line_id.product_id', string='Product')
    line_subtotal = fields.Monetary(
        related='order_line_id.price_subtotal', string='Master Total', readonly=True)
    currency_id = fields.Many2one(related='order_line_id.currency_id')
    amount = fields.Monetary('Allocated Amount', currency_field='currency_id')

    _vessel_line_uniq = models.Constraint(
        'UNIQUE(wizard_id, vessel_id, order_line_id)',
        'Each vessel can only have one allocation per product line.',
    )
