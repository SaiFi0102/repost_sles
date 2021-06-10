import frappe
from frappe.utils import flt
from erpnext.controllers.buying_controller import BuyingController
from erpnext.controllers.selling_controller import SellingController
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
import erpnext.accounts.party


def update_ordered_and_reserved_qty(self):
	if not frappe.flags.do_not_update_reserved_qty:
		old_update_ordered_and_reserved_qty(self)


old_update_ordered_and_reserved_qty = BuyingController.update_ordered_and_reserved_qty
if BuyingController.update_ordered_and_reserved_qty is not update_ordered_and_reserved_qty:
	BuyingController.update_ordered_and_reserved_qty = update_ordered_and_reserved_qty


def update_reserved_qty(self):
	if not frappe.flags.do_not_update_reserved_qty:
		old_update_reserved_qty(self)


old_update_reserved_qty = SellingController.update_reserved_qty
if SellingController.update_reserved_qty is not update_reserved_qty:
	SellingController.update_reserved_qty = update_reserved_qty


def validate_party_frozen_disabled(party_type, party_name):
	if not frappe.flags.ignored_closed_or_disabled:
		old_validate_party(party_type, party_name)


old_validate_party = erpnext.accounts.party.validate_party_frozen_disabled
if erpnext.accounts.party.validate_party_frozen_disabled is not validate_party_frozen_disabled:
	erpnext.accounts.party.validate_party_frozen_disabled = validate_party_frozen_disabled


def set_basic_rate_for_finished_goods(self, raw_material_cost=0, scrap_material_cost=0):
	total_fg_qty = 0
	if not raw_material_cost and self.get("items"):
		raw_material_cost = sum([flt(row.basic_amount) for row in self.items
			if row.s_warehouse and not row.t_warehouse])

	total_fg_qty = sum([flt(row.qty) for row in self.items
		if row.t_warehouse and not row.s_warehouse])

	if self.purpose in ["Manufacture", "Repack"]:
		for d in self.get("items"):
			if d.set_basic_rate_manually: continue

			if (d.transfer_qty and (d.bom_no or d.t_warehouse)
				and (getattr(self, "pro_doc", frappe._dict()).scrap_warehouse != d.t_warehouse)):

				if (self.work_order and self.purpose == "Manufacture"
					and frappe.db.get_single_value("Manufacturing Settings", "material_consumption")):
					bom_items = self.get_bom_raw_materials(d.transfer_qty)
					raw_material_cost = sum([flt(row.qty)*flt(row.rate) for row in bom_items.values()])

				if raw_material_cost and self.purpose == "Manufacture":
					d.basic_rate = flt((raw_material_cost - scrap_material_cost) / flt(d.transfer_qty), d.precision("basic_rate"))
					d.basic_amount = flt((raw_material_cost - scrap_material_cost), d.precision("basic_amount"))
				elif self.purpose == "Repack" and total_fg_qty:
					d.basic_rate = flt(raw_material_cost) / flt(total_fg_qty)
					d.basic_amount = d.basic_rate * flt(d.qty)


old_set_basic_fg_rate = StockEntry.set_basic_rate_for_finished_goods
if StockEntry.set_basic_rate_for_finished_goods is not set_basic_rate_for_finished_goods:
	StockEntry.set_basic_rate_for_finished_goods = set_basic_rate_for_finished_goods
