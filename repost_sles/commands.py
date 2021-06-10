# Copyright (c) 2015, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals, absolute_import, print_function
import click
import frappe
from frappe.commands import pass_context, get_site
from repost_sles.main import repost_all_stock_vouchers


@click.command('repost-sles')
@click.option('--from-date', help='Starting date to repost from')
@click.option('--repost-gle', default=True, help='Repost related General Ledger entries')
@pass_context
def repost_sles(context, from_date, repost_gle=True):
	site = get_site(context)
	with frappe.init_site(site):
		frappe.connect()
		repost_all_stock_vouchers(from_date, repost_gle)


commands = [
	repost_sles
]
