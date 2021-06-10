# Copyright (c) 2015, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals, absolute_import, print_function
import click
import frappe
from frappe.commands import pass_context, get_site
from repost_sles.main import repost_all_stock_vouchers, set_basic_rate_manually


@click.command('repost-sles')
@click.option('--from-date', required=True, help='Starting date to repost from')
@click.option('--no-repost-gle', is_flag=True, default=False, help='Do not repost related General Ledger entries')
@pass_context
def repost_sles(context, from_date, no_repost_gle=False):
	site = get_site(context)
	with frappe.init_site(site):
		frappe.connect()
		repost_all_stock_vouchers(from_date, not no_repost_gle)


@click.command('set-manual-fg-rate')
@click.option('--item-code', required=True, help='Finished Good Item for which basic rate is to be set')
@click.option('--rate', required=True, type=float, help='Basic Rate to be set')
@click.option('--from-date', required=True, help='Starting date for which manual basic rate is to be set')
@click.option('--to-date', required=True, help='Ending date for which manual basic rate is to be set')
@pass_context
def set_manual_fg_rate(context, item_code, rate, from_date, to_date):
	site = get_site(context)
	with frappe.init_site(site):
		frappe.connect()
		set_basic_rate_manually(item_code, rate, from_date, to_date)
		frappe.db.commit()


commands = [
	repost_sles,
	set_manual_fg_rate
]
