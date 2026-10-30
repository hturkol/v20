from odoo import api, fields, models, _


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    task_ids = fields.One2many('project.task', 'helpdesk_ticket_id', string='Tasks', copy=False)
    task_count = fields.Integer(compute='_compute_task_count', string='Task Count')

    @api.depends('task_ids')
    def _compute_task_count(self):
        for ticket in self:
            ticket.task_count = len(ticket.task_ids)

    def action_create_task(self):
        self.ensure_one()
        return {
            'name': _('Create Task from Ticket'),
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket.task.wizard',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_helpdesk_ticket_id': self.id,
                'default_name': self.name,
                'default_description': self.description,
                'default_user_id': self.user_id.id,
            },
        }

    def action_open_tasks(self):
        self.ensure_one()
        action = {
            'name': _('Tasks'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'context': {'create': False},
        }
        if len(self.task_ids) == 1:
            action.update(view_mode='form', res_id=self.task_ids.id)
        else:
            action.update(view_mode='list,form', domain=[('id', 'in', self.task_ids.ids)])
        return action
