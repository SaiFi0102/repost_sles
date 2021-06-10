import frappe
import datetime
import os
import json
from frappe.utils import flt


def repost_all_stock_vouchers(from_date, repost_gle=True):
	frappe.flags.ignored_closed_or_disabled = 1
	frappe.flags.do_not_update_reserved_qty = 1
	frappe.db.auto_commit_on_many_writes = 1

	print("Repost GLEs: {0}".format(repost_gle))

	date_where_condition = ""
	date_and_condition = ""
	if from_date:
		print("From Date: {0}".format(frappe.format(from_date)))
		date_condition = "posting_date >= {0}".format(frappe.db.escape(from_date))
		date_where_condition = "where {0}".format(date_condition)
		date_and_condition = "and {0}".format(date_condition)

	print("Enabling Allow Negative Stock")
	frappe.db.set_value("Stock Settings", None, "allow_negative_stock", 1)

	filename = "repost_all_stock_vouchers_checkpoint.json"
	if not os.path.isfile(filename):
		print("No checkpoint found")
		print("Updating Purchase Valuation Rates")
		precs = frappe.db.sql("select 'Purchase Receipt' as doctype, name from `tabPurchase Receipt` where docstatus=1 {0}".format(date_and_condition))
		pinvs = frappe.db.sql("select 'Purchase Invoice' as doctype, name from `tabPurchase Invoice` where docstatus=1 {0}".format(date_and_condition))
		for doctype, name in precs + pinvs:
			doc = frappe.get_doc(doctype, name)

			doc.set_landed_cost_voucher_amount()
			doc.update_valuation_rate("items")

			for d in doc.items:
				d.db_update()

			doc.clear_cache()

		frappe.db.commit()

		print("Getting Stock Vouchers List")
		vouchers = frappe.db.sql("""
			select distinct voucher_type, voucher_no
			from `tabStock Ledger Entry` sle
			{0}
			order by posting_date, posting_time, creation
		""".format(date_where_condition))

		print("Deleting SLEs")
		frappe.db.sql("delete from `tabStock Ledger Entry` {0}".format(date_where_condition))

		if repost_gle:
			print("Deleting GLEs")
			for voucher_type, voucher_no in vouchers:
				frappe.db.sql("""delete from `tabGL Entry` where voucher_type=%s and voucher_no=%s""", (voucher_type, voucher_no))
			print()

		frappe.db.commit()
	else:
		print("Checkpoint found")
		with open(filename, "r") as f:
			vouchers = json.loads(f.read())

	start_time = datetime.datetime.now()
	print("Starting at: {0}".format(start_time))

	i = 0
	for voucher_type, voucher_no in vouchers:
		try:
			doc = frappe.get_doc(voucher_type, voucher_no)
			if voucher_type == "Stock Entry":
				doc.calculate_rate_and_amount()

				doc.db_update()
				for d in doc.items:
					d.db_update()

			elif voucher_type=="Purchase Receipt" and doc.is_subcontracted == "Yes":
				doc.validate()

			elif voucher_type=="Delivery Note":
				for d in doc.items:
					if d.target_warehouse:
						d.db_set('target_warehouse', None)

			doc.update_stock_ledger()

			if repost_gle:
				doc.make_gl_entries(repost_future_gle=False, from_repost=True)

			frappe.db.commit()
			i += 1
			doc.clear_cache()

			now_time = datetime.datetime.now()
			total_duration = now_time - start_time
			repost_rate = flt(i) / total_duration.seconds if total_duration.seconds else "Inf"
			remaining_duration = datetime.timedelta(seconds=(len(vouchers) - i) / flt(repost_rate)) if flt(repost_rate) else "N/A"
			print("{0} / {1}: Elapsed Time: {4} | Rate: {5:.2f} Vouchers/Sec | ETA: {6} | {2} {3}".format(i, len(vouchers), voucher_type, voucher_no,
				total_duration, flt(repost_rate), remaining_duration))
		except:
			with open(filename, "w") as f:
				print("Creating checkpoint")
				f.write(json.dumps(vouchers[i:]))

			frappe.db.rollback()
			raise

	print("Disabling Allow Negative Stock")
	frappe.db.set_value("Stock Settings", None, "allow_negative_stock", 0)
	frappe.db.commit()
	frappe.db.auto_commit_on_many_writes = 0

	if os.path.isfile(filename):
		print("Deleting Checkpoint")
		os.remove(filename)


def set_basic_rate_manually(item_code, rate, from_date, to_date):
	rate = flt(rate)

	print("Item Code: {0}".format(item_code))
	print("Rate: {0}".format(frappe.format(rate)))
	print("From Date: {0}".format(from_date))
	print("To Date: {0}".format(to_date))

	date_condition = ""
	if from_date:
		date_condition += " and ste.posting_date >= %(from_date)s"
	if from_date:
		date_condition += " and ste.posting_date <= %(to_date)s"

	args = {
		'item_code': item_code,
		'from_date': from_date,
		'to_date': to_date,
		'rate': rate
	}

	stes = frappe.db.sql_list("""
		select distinct ste.name
		from `tabStock Entry` ste
		inner join `tabStock Entry Detail` d on d.parent = ste.name
		where ste.purpose in ('Manufacture', 'Repack')
			and ste.docstatus = 1
			and d.item_code = %(item_code)s
			and ifnull(d.t_warehouse, '') != ''
			{0}
	""".format(date_condition), args)

	for name in stes:
		print(name)

	frappe.db.sql("""
		update `tabStock Entry Detail` d
		inner join `tabStock Entry` ste on d.parent = ste.name
		set d.rate = %(rate)s, d.set_basic_rate_manually = 1
		where ste.purpose in ('Manufacture', 'Repack')
			and ste.docstatus = 1
			and d.item_code = %(item_code)s
			and ifnull(d.t_warehouse, '') != ''
			{0}
	""".format(date_condition), args)
