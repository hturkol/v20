# -*- coding: utf-8 -*-
{
    'name': 'Helpdesk Ticket to Task',
    'version': '20.0.1.0.0',
    'summary': 'Create a project task from a helpdesk ticket while keeping the ticket active',
    'description': """
Helpdesk Ticket to Task
=======================

The standard "Convert to Task" action archives the ticket, so follow-up can
only be done on the task. This module adds a "Create Task" button on the ticket
that creates a linked task and keeps the ticket active:

* The work is done on the task, the customer is informed from the ticket.
* Smart buttons link the ticket and the task in both directions.
* Ticket and task chatters log the link.
    """,
    'author': 'Projet İş Çözümleri Ltd. Şti.',
    'website': 'https://projet.solutions',
    'category': 'Services/Helpdesk',
    'depends': [
        'helpdesk',
        'project',
    ],
    'data': [
        'security/ir.access.csv',
        'wizard/helpdesk_ticket_task_wizard_views.xml',
        'views/helpdesk_ticket_views.xml',
        'views/project_task_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
