# Copyright (c) 2026, School Administration and contributors
# For license information, please see license.txt
"""
Finance module (blueprint Phase 2: Billing + Purchasing) custom fields,
extending real installed DocTypes rather than duplicating them — see
IMPLEMENTATION-MAPPING.md's two Finance sections for the field-by-field
rationale.

Link-target translation (blueprint name -> real DocType this app extends):
  SMS Fee Code -> Fee Category (education)         SMS Chart of Account -> Account (erpnext)
  SMS GL Voucher -> Journal Entry (erpnext)         SMS Finance Settings -> Education Settings (billing half) /
                                                                             Buying Settings (purchasing half)
  SMS Purchase Requisition -> Material Request      SMS Purchase Order -> Purchase Order (erpnext)
  SMS Supplier -> Supplier (erpnext)                SMS Item -> Item (erpnext)
  SMS Item Supplier/Price History -> Item Price     SMS Code -> SMS Code (campus_erp, Administration, Phase 0)
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Fee Category": [
		{"fieldname": "code_type", "label": "Code Type", "fieldtype": "Select",
			"options": "Header\nDetail", "default": "Detail", "insert_after": "item_defaults"},
		{"fieldname": "header", "label": "Header Group", "fieldtype": "Link", "options": "Fee Category",
			"description": "Only for Detail rows", "depends_on": "eval:doc.code_type=='Detail'", "insert_after": "code_type"},
		{"fieldname": "priority", "label": "Payment Allocation Priority", "fieldtype": "Int",
			"description": "Drives Priority-mode payment allocation; absorbs the legacy Fee Priority Setting table",
			"insert_after": "header"},
		{"fieldname": "is_disabled", "label": "Disabled", "fieldtype": "Check", "insert_after": "priority"},
	],
	"Education Settings": [
		{"fieldname": "sms_finance_tab", "fieldtype": "Tab Break", "label": "Finance Billing (PH)", "insert_after": "cor_layout"},
		{"fieldname": "billing_due_date", "label": "Billing Due Date", "fieldtype": "Date", "insert_after": "sms_finance_tab"},
		{"fieldname": "surcharge_percent", "label": "Installment Surcharge %", "fieldtype": "Percent", "insert_after": "billing_due_date"},
		{"fieldname": "column_break_sms_fin_1", "fieldtype": "Column Break", "insert_after": "surcharge_percent"},
		{"fieldname": "enable_wallet", "label": "Enable Student Wallet (e-cash)", "fieldtype": "Check", "default": "0",
			"description": "Gate for the SMS Wallet Account/Transaction screens — open product question per the migration blueprint; defaults off until Finance confirms the e-cash feature is still in active use",
			"insert_after": "column_break_sms_fin_1"},
	],
	"Material Request": [
		{"fieldname": "sms_purchasing_tab", "fieldtype": "Tab Break", "label": "Purchasing (PH)", "insert_after": "last_scanned_warehouse"},
		{"fieldname": "requested_by", "label": "Requested By", "fieldtype": "Link", "options": "Employee", "insert_after": "sms_purchasing_tab"},
		{"fieldname": "pr_purpose", "label": "Purpose", "fieldtype": "Small Text", "insert_after": "requested_by"},
		{"fieldname": "column_break_sms_mr_1", "fieldtype": "Column Break", "insert_after": "pr_purpose"},
		{"fieldname": "branch", "label": "Branch", "fieldtype": "Link", "options": "Branch", "insert_after": "column_break_sms_mr_1"},
		{"fieldname": "total_amount", "label": "Total Amount", "fieldtype": "Currency", "read_only": 1,
			"description": "Computed, read-only — Material Request has no header total by default", "insert_after": "branch"},
	],
	"Material Request Item": [
		{"fieldname": "supplier", "label": "Supplier", "fieldtype": "Link", "options": "Supplier",
			"description": "Needed to later group requisition lines into one Purchase Order per distinct supplier",
			"insert_after": "price_list_rate"},
	],
	"Purchase Order": [
		{"fieldname": "sms_purchasing_section", "fieldtype": "Section Break", "label": "Purchasing (PH)", "insert_after": "last_scanned_warehouse"},
		{"fieldname": "branch", "label": "Branch", "fieldtype": "Link", "options": "Branch", "insert_after": "sms_purchasing_section"},
		{"fieldname": "settlement_reference", "label": "Settlement Voucher", "fieldtype": "Link", "options": "Journal Entry",
			"read_only": 1, "insert_after": "branch"},
		{"fieldname": "column_break_sms_po_1", "fieldtype": "Column Break", "insert_after": "settlement_reference"},
		{"fieldname": "payables_settled", "label": "Payables Settled", "fieldtype": "Check", "insert_after": "column_break_sms_po_1"},
	],
	"Supplier": [
		{"fieldname": "sms_supplier_section", "fieldtype": "Section Break", "label": "Legacy / Purchasing (PH)", "insert_after": "column_break_mglr"},
		{"fieldname": "legacy_supplier_code", "label": "Legacy Supplier Code", "fieldtype": "Data", "read_only": 1, "insert_after": "sms_supplier_section"},
		{"fieldname": "branch", "label": "Branch", "fieldtype": "Link", "options": "Branch", "insert_after": "legacy_supplier_code"},
		{"fieldname": "column_break_sms_sup_1", "fieldtype": "Column Break", "insert_after": "branch"},
		{"fieldname": "tax_percent", "label": "Tax %", "fieldtype": "Float", "insert_after": "column_break_sms_sup_1"},
	],
	"Item": [
		{"fieldname": "sms_item_section", "fieldtype": "Section Break", "label": "Purchasing (PH)", "insert_after": "deferred_accounting_section"},
		{"fieldname": "default_cost", "label": "Default Cost", "fieldtype": "Currency", "insert_after": "sms_item_section"},
		{"fieldname": "column_break_sms_item_1", "fieldtype": "Column Break", "insert_after": "default_cost"},
		{"fieldname": "max_order_qty", "label": "Max Order Qty", "fieldtype": "Float", "insert_after": "column_break_sms_item_1"},
	],
	"Item Price": [
		{"fieldname": "branch", "label": "Branch", "fieldtype": "Link", "options": "Branch",
			"description": "Only if per-branch cost ceilings genuinely differ from one Price List per branch", "insert_after": "batch_no"},
	],
	"Buying Settings": [
		{"fieldname": "sms_buying_section", "fieldtype": "Section Break", "label": "Legacy Settings (PH)", "insert_after": "validate_consumed_qty"},
		{"fieldname": "max_pr_amount", "label": "Max PR Amount (no admin sign-off)", "fieldtype": "Currency", "insert_after": "sms_buying_section"},
		{"fieldname": "column_break_sms_buy_1", "fieldtype": "Column Break", "insert_after": "max_pr_amount"},
		{"fieldname": "price_history_active_year", "label": "Price History Active Year", "fieldtype": "Int", "insert_after": "column_break_sms_buy_1"},
	],
}


def sync_finance_property_setters():
	"""Extends Journal Entry Account's reference_type Select so a replenishment
	Journal Entry line can carry a polymorphic back-reference to the Canteen
	PCV batch it settles — mirrors Phase 1's Student Log 'type' extension."""
	frappe.make_property_setter(
		{
			"doctype": "Journal Entry Account",
			"fieldname": "reference_type",
			"property": "options",
			"value": (
				"Sales Invoice\nPurchase Invoice\nJournal Entry\nSales Order\nPurchase Order\n"
				"Expense Claim\nAsset\nLoan\nPayroll Entry\nEmployee Advance\n"
				"Exchange Rate Revaluation\nInvoice Discounting\nFees\nFull and Final Statement\n"
				"Payment Entry\nBank Transaction\nSMS Canteen PCV"
			),
			"property_type": "Text",
		},
		validate_fields_for_doctype=False,
	)


def sync_finance_custom_fields():
	"""Idempotent — safe to call from after_migrate every time (blueprint Phase 2)."""
	create_custom_fields(CUSTOM_FIELDS, update=True)
	sync_finance_property_setters()
	frappe.clear_cache()
