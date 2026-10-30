# SPDX-License-Identifier: LicenseRef-Projet-Proprietary
#
# Copyright (c) 2025 Projet İş Çözümleri Limited Şirketi
#
# This file is part of a proprietary Odoo addon.
# Use of this file is governed by the LICENSE file included
# in the root of this repository.

from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestMtrVesselPartner(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.management = cls.env['res.partner'].create({'name': 'MTR Management Co'})
        cls.legal_a = cls.env['res.partner'].create({'name': 'Vessel Owner A'})
        cls.legal_b = cls.env['res.partner'].create({'name': 'Vessel Owner B'})
        cls.product = cls.env['product.product'].create({
            'name': 'Training Service',
            'type': 'service',
            'list_price': 100.0,
            'invoice_policy': 'order',
        })
        cls.product_b = cls.env['product.product'].create({
            'name': 'VR Training',
            'type': 'service',
            'list_price': 50.0,
        })
        cls.vessel_a = cls.env['res.partner'].create({
            'name': 'MV Alpha',
            'is_vessel': True,
            'imo_number': '9000001',
            'parent_id': cls.legal_a.id,
            'vessel_management_id': cls.management.id,
        })
        cls.vessel_b = cls.env['res.partner'].create({
            'name': 'MV Beta',
            'is_vessel': True,
            'imo_number': '9000002',
            'parent_id': cls.legal_b.id,
            'vessel_management_id': cls.management.id,
        })
        cls.vessel_c = cls.env['res.partner'].create({
            'name': 'MV Gamma',
            'is_vessel': True,
            'imo_number': '9000003',
            'parent_id': cls.legal_a.id,
            'vessel_management_id': cls.management.id,
        })
        cls.master = cls.env['sale.order'].create({
            'partner_id': cls.management.id,
            'is_master_quotation': True,
            'order_line': [
                Command.create({
                    'product_id': cls.product.id,
                    'product_uom_qty': 2,
                    'price_unit': 80.0,
                }),
                Command.create({
                    'product_id': cls.product_b.id,
                    'product_uom_qty': 1,
                    'price_unit': 40.0,
                }),
            ],
        })
        cls.master_line = cls.master.order_line[0]
        cls.master_line_b = cls.master.order_line[1]
        cls.Wizard = cls.env['mtr.vessel.quotation.wizard']

    def _create_wizard(self, vessels, amounts=None):
        alloc_cmds = []
        for line in self.master.order_line.filtered(lambda l: not l.display_type):
            for vessel in vessels:
                amount = (
                    amounts[(vessel, line)] if amounts is not None
                    else line.price_subtotal / len(vessels))
                alloc_cmds.append(Command.create({
                    'vessel_id': vessel.id,
                    'order_line_id': line.id,
                    'amount': amount,
                }))
        return self.Wizard.create({
            'master_order_id': self.master.id,
            'line_ids': [
                Command.create({'vessel_id': vessel.id, 'selected': True})
                for vessel in vessels
            ],
            'alloc_ids': alloc_cmds,
        })

    # --- Partner vessel model ---
    def test_imo_number_unique(self):
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': 'MV Alpha II', 'is_vessel': True,
                'imo_number': '9000001',
            })

    def test_master_quotation_not_confirmable(self):
        with self.assertRaises(ValidationError):
            self.master.action_confirm()

    # --- Wizard ---
    def test_wizard_default_lines(self):
        vals = self.Wizard.with_context(
            default_master_order_id=self.master.id).default_get(['line_ids', 'alloc_ids'])
        self.assertEqual(len(vals['line_ids']), 3)
        # 3 vessels x 2 master lines, equal split of the remaining totals
        self.assertEqual(len(vals['alloc_ids']), 6)
        # every generated allocation must carry vessel + master line references
        for cmd in vals['alloc_ids']:
            self.assertTrue(cmd[2]['vessel_id'])
            self.assertTrue(cmd[2]['order_line_id'])
        amounts_line = [
            cmd[2]['amount'] for cmd in vals['alloc_ids']
            if cmd[2]['order_line_id'] == self.master_line.id]
        self.assertAlmostEqual(sum(amounts_line), 160.0)

    def test_create_vessel_orders_variable_amounts(self):
        wizard = self._create_wizard(
            self.vessel_a | self.vessel_b,
            amounts={
                (self.vessel_a, self.master_line): 100.0,
                (self.vessel_b, self.master_line): 60.0,
                (self.vessel_a, self.master_line_b): 25.0,
                (self.vessel_b, self.master_line_b): 15.0,
            })
        wizard.action_create_quotations()

        orders = self.master.vessel_order_ids
        self.assertEqual(len(orders), 2)

        order_a = orders.filtered(lambda order: order.vessel_id == self.vessel_a)
        self.assertEqual(order_a.partner_id, self.legal_a)
        self.assertEqual(order_a.vessel_id, self.vessel_a)
        line_a = order_a.order_line.filtered(
            lambda line: line.master_line_id == self.master_line)
        self.assertEqual(line_a.price_unit, 100.0)
        self.assertEqual(line_a.product_uom_qty, 1.0)
        self.assertEqual(line_a.discount, 0.0)

        self.assertEqual(self.master_line.allocated_amount, 160.0)
        self.assertEqual(self.master_line.remaining_amount, 0.0)
        self.assertEqual(self.master_line_b.allocated_amount, 40.0)

        order_a.action_confirm()
        self.assertEqual(order_a.state, 'sale')

    def test_duplicate_vessel_order_blocked(self):
        self._create_wizard(self.vessel_a).action_create_quotations()
        with self.assertRaises(ValidationError):
            self._create_wizard(self.vessel_a).action_create_quotations()

    def test_reopen_wizard_suggests_remaining(self):
        self._create_wizard(
            self.vessel_a | self.vessel_b,
            amounts={
                (self.vessel_a, self.master_line): 100.0,
                (self.vessel_b, self.master_line): 60.0,
                (self.vessel_a, self.master_line_b): 25.0,
                (self.vessel_b, self.master_line_b): 15.0,
            }).action_create_quotations()
        # All of master_line is allocated; only line_b has 0 remaining too.
        # Add a late vessel → suggestions must be based on remaining amounts.
        vals = self.Wizard.with_context(
            default_master_order_id=self.master.id).default_get(['line_ids', 'alloc_ids'])
        vessel_c_allocs = [
            cmd[2] for cmd in vals['alloc_ids']
            if cmd[2]['vessel_id'] == self.vessel_c.id]
        self.assertEqual(len(vessel_c_allocs), 2)
        self.assertTrue(all(alloc['amount'] == 0.0 for alloc in vessel_c_allocs))
        # vessel_a/b rows must show their existing quotations and stay unselected
        line_a = [
            cmd[2] for cmd in vals['line_ids']
            if cmd[2]['vessel_id'] == self.vessel_a.id]
        self.assertFalse(line_a[0]['selected'])
        self.assertTrue(line_a[0]['sale_order_id'])

    def test_selected_vessel_without_alloc_gets_suggestion(self):
        # vessel selected in the list but with no allocation rows
        # (e.g. added manually) → automatic suggestion from remaining amounts.
        wizard = self.Wizard.create({
            'master_order_id': self.master.id,
            'line_ids': [
                Command.create({'vessel_id': self.vessel_a.id, 'selected': True}),
            ],
        })
        wizard.action_create_quotations()
        order = self.master.vessel_order_ids
        self.assertEqual(len(order), 1)
        line = order.order_line.filtered(
            lambda l: l.master_line_id == self.master_line)
        self.assertEqual(line.price_unit, self.master_line.price_subtotal)

    # --- Manual vessel selection on orders ---
    def test_vessel_onchange_sets_legal_entity(self):
        order = self.env['sale.order'].new({'vessel_id': self.vessel_a.id})
        order._onchange_vessel_id()
        self.assertEqual(order.partner_id, self.legal_a)
