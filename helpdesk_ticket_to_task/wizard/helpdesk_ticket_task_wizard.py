from odoo import fields, models, _
from odoo.exceptions import UserError


class HelpdeskTicketTaskWizard(models.TransientModel):
    _name = 'helpdesk.ticket.task.wizard'
    _description = 'Create Task from Helpdesk Ticket'

    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', string='Ticket', required=True)
    name = fields.Char('Title', required=True)
    description = fields.Html('Description')
    project_id = fields.Many2one(
        'project.project', string='Project', required=True, domain=[('is_template', '=', False)])
    user_id = fields.Many2one('res.users', string='Assigned to', domain=[('share', '=', False)])

    def action_create(self):
        self.ensure_one()
        ticket = self.helpdesk_ticket_id
        if ticket.task_ids:
            raise UserError(_("A task has already been created for this ticket."))

        task = self.env['project.task'].with_context(mail_create_nolog=True).create(self._get_task_values())

        # Unlike the standard conversion (project_helpdesk), the ticket is not archived.
        ticket_sudo, task_sudo = ticket.sudo(), task.sudo()
        ticket_sudo.message_post(
            body=_("Task %s created from this ticket.", task_sudo._get_html_link()),
            subtype_xmlid='mail.mt_note',
        )
        task_sudo.message_post_with_source(
            'mail.message_origin_link',
            render_values={'self': task_sudo, 'origin': ticket_sudo},
            subtype_xmlid='mail.mt_note',
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Task'),
            'res_model': 'project.task',
            'res_id': task.id,
            'views': [(self.env.ref('project.view_task_form2').id, 'form')],
            'target': 'current',
        }

    def _get_task_values(self):
        ticket = self.helpdesk_ticket_id
        vals = {
            'name': self.name,
            'description': self.description,
            'project_id': self.project_id.id,
            'helpdesk_ticket_id': ticket.id,
            'partner_id': (ticket.partner_id or self.project_id.partner_id).id,
        }
        if self.user_id:
            vals['user_ids'] = [(6, 0, self.user_id.ids)]
        return vals
