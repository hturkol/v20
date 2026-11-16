# SPDX-License-Identifier: LicenseRef-Projet-Proprietary
#
# Copyright (c) 2026 Projet İş Çözümleri Limited Şirketi
#
# This file is part of a proprietary Odoo addon.
# Use of this file is governed by the LICENSE file included
# in the root of this repository.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import SQL


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_linked_company = fields.Boolean(
        'Independent Company', copy=False, index=True, tracking=True,
        help='A linked company keeps its own commercial entity under a parent '
             'company: its Tax ID, receivable/payable accounts, payment terms and '
             'journal entries are never synchronized with the parent. Standard '
             'smart buttons on the parent still aggregate its documents '
             '(child_of hierarchy).')
    linked_company_count = fields.Integer(
        '# Linked Companies', compute='_compute_linked_company_count', compute_sudo=True)
    linked_project_count = fields.Integer(
        '# Linked Projects', compute='_compute_linked_project_count', compute_sudo=True)

    @api.depends('child_ids.is_linked_company')
    def _compute_linked_company_count(self):
        for partner in self:
            partner.linked_company_count = len(
                partner.child_ids.filtered('is_linked_company'))

    @api.depends('child_ids')
    def _compute_linked_project_count(self):
        Project = self.env['project.project']
        for partner in self:
            partner.linked_project_count = Project.search_count(
                [('partner_id', 'child_of', partner.id)])

    # --- Commercial entity ---
    # In v20, every partner with a parent_id takes the parent's commercial
    # entity. For linked companies we restore the pre-v20 rule: a flagged
    # child is its own commercial entity (is_company becomes True once it
    # has a valid Tax ID), which disables all commercial-field syncing in
    # both directions and keeps its journal entries on itself.

    @api.depends('parent_id.commercial_partner_id', 'parent_id', 'is_linked_company')
    def _compute_commercial_partner(self):
        for partner in self:
            if not partner.parent_id or partner.is_linked_company:
                partner.commercial_partner_id = partner
            else:
                partner.commercial_partner_id = partner.parent_id.commercial_partner_id

    def _write_commercial_sync(self, sync_vals):
        # The core downward sync only skips `is_company` children; a linked
        # company without a Tax ID stays is_company=False and would receive
        # the parent's commercial values. Protect it explicitly.
        dependent = self - self.filtered('is_linked_company')
        if dependent:
            super(ResPartner, dependent)._write_commercial_sync(sync_vals)

    def _get_complete_name(self):
        if self.is_linked_company:
            # without a Tax ID is_company stays False, and the core would
            # prefix the name with commercial_company_name -- which is the
            # record itself, doubling the name ("test1, test1")
            return (self.name or '').strip()
        return super()._get_complete_name()

    @api.onchange('parent_id')
    def onchange_parent_id(self):
        if self.is_linked_company:
            # keep the company's own address in the form
            return {}
        return super().onchange_parent_id()

    @api.onchange('is_linked_company')
    def _onchange_is_linked_company(self):
        # 'contact' children inherit the parent's address and cannot edit their
        # own; 'other' is exempt from address sync, so a linked company gets an
        # editable address block (and keeps it on save, see _set_group_parent).
        self.type = 'other' if self.is_linked_company else 'contact'

    @api.onchange('type')
    def _onchange_type_linked_company(self):
        # address types (invoice/delivery/other address kinds) cannot carry an
        # independent commercial identity
        if self.type not in ('contact', 'other'):
            self.is_linked_company = False

    # --- Writing ---
    def write(self, vals):
        if 'is_linked_company' in vals and not vals['is_linked_company']:
            still_linked = self.filtered(
                lambda partner: vals.get('parent_id', partner.parent_id.id))
            if still_linked:
                parents = self.env['res.partner'].browse(
                    {vals.get('parent_id') or p.parent_id.id for p in still_linked})
                raise ValidationError(_(
                    'The "Independent Company" flag cannot be removed while the partner '
                    'is still linked to %(parents)s. Remove the parent company first.',
                    parents=', '.join(parents.mapped('name'))))
        if not vals.get('parent_id'):
            return super().write(vals)

        # The account module blocks setting a parent on partners that have
        # journal items with a different Tax ID, then repartners those items
        # to the commercial entity. Both are address-contact semantics; a
        # linked company keeps its history, so it takes the bypassed path.
        linked = self.filtered(
            lambda partner: partner.is_linked_company or vals.get('is_linked_company'))
        regular = self - linked
        res = super(ResPartner, regular).write(vals) if regular else True
        if linked:
            own_vals = {key: value for key, value in vals.items() if key != 'parent_id'}
            if own_vals:
                super(ResPartner, linked).write(own_vals)
            linked._set_group_parent(vals['parent_id'])
        return res

    def _set_group_parent(self, parent_id):
        """Set ``parent_id`` on linked companies, bypassing the account
        same-VAT guard via the low-level ``_write``. The record is its own
        commercial entity, so nothing else in ``_fields_sync`` applies."""
        parent = self.env['res.partner'].browse(parent_id).exists()
        if not parent:
            raise ValidationError(_('The selected parent company does not exist.'))
        for partner in self:
            if partner.parent_id == parent:
                continue
            write_vals = {'parent_id': parent_id}
            if partner.type == 'contact':
                # 'other' exempts the record from both directions of address sync
                write_vals['type'] = 'other'
            # _write() skips modified(); mirror write() so dependents on the
            # parent chain (stored related group_company_id, commercial
            # partner, parent_path...) get invalidated and recomputed
            rel_fnames = [f for f in write_vals if partner._fields[f].relational]
            if rel_fnames:
                partner.modified(rel_fnames, before=True)
            partner._write(write_vals)
            partner.invalidate_recordset(list(write_vals))
            partner.modified(list(write_vals))
            partner._check_parent_id()
        self._check_company(['parent_id'])

    # --- Invoice totals ---
    def _invoice_total(self):
        # Linked companies keep their own commercial entity, so core totals
        # that attribute invoices to the commercial partner miss them on the
        # group company. Aggregate posted customer invoices over the whole
        # parent hierarchy instead, walking parent_id up to each ancestor.
        self.total_invoiced = 0.0
        if not self.ids:
            return
        all_partners = self.with_context(active_test=False).search_fetch(
            [('id', 'child_of', self.ids)], ['parent_id'])
        query_res = self.env.execute_query(SQL(
            """SELECT move.partner_id, SUM(move.amount_total_signed * COALESCE(currency_rate.rate, 1))
                 FROM account_move move
                 LEFT JOIN res_partner partner
                   ON partner.id = move.partner_id
                 LEFT JOIN res_company company
                   ON company.id = COALESCE(partner.company_id, %(default_company_id)s)
                 /* To use the exchange rate effective at the creation of the invoice. */
                 LEFT JOIN LATERAL (
                     SELECT rate
                       FROM res_currency_rate
                      WHERE company_id = move.company_id
                        AND currency_id = company.currency_id
                        AND name < move.date
                      ORDER BY name DESC
                      LIMIT 1
                 ) currency_rate
                   ON TRUE
                WHERE move.state NOT IN ('draft', 'cancel')
                  AND move.company_id IN %(company_ids)s
                  AND move.partner_id IN %(partner_ids)s
                  AND move.move_type IN ('out_invoice', 'out_refund')
                GROUP BY move.partner_id""",
            partner_ids=tuple(all_partners.ids),
            company_ids=tuple(self.env.companies.ids),
            default_company_id=self.env.company.id,
        ))
        all_partners_by_id = {partner.id: partner for partner in all_partners}
        for partner_id, total in query_res:
            partner = all_partners_by_id[partner_id]
            while partner:
                if partner in self:
                    partner.total_invoiced += total
                partner = partner.parent_id

    # --- Actions ---
    def action_view_linked_projects(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Projects'),
            'res_model': 'project.project',
            'view_mode': 'kanban,list,form',
            'domain': [('partner_id', 'child_of', self.id)],
        }

    def action_view_linked_companies(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Linked Companies'),
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [('id', 'child_of', self.id), ('is_linked_company', '=', True)],
            'context': {
                'default_parent_id': self.id,
                'default_is_linked_company': True,
            },
        }
