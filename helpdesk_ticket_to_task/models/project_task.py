from odoo import fields, models, _


class ProjectTask(models.Model):
    _inherit = 'project.task'

    helpdesk_ticket_id = fields.Many2one(
        'helpdesk.ticket', string='Helpdesk Ticket', index='btree_not_null', copy=False)

    def action_open_helpdesk_ticket(self):
        self.ensure_one()
        return {
            'name': _('Helpdesk Ticket'),
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'form',
            'res_id': self.helpdesk_ticket_id.id,
        }
