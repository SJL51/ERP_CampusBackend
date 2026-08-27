# Copyright (c) 2026, School Administration and contributors
# For license information, please see license.txt
"""
Finance Billing business rules (blueprint Phase 2). Per the same guiding
principle as registrar.py (blueprint §4.3): DocTypes own schema and
permissions only; every rule that used to live inline in a VB button-click
handler (or worse, re-implemented per form) lives here once instead.

SMS Student Assessment posts real GL Entry rows against the Student party
type (see its on_submit()/make_gl_entries(), mirroring Education's own Fees
doctype). Student payments are recorded as real, submitted ERPNext Payment
Entry documents rather than a shadow ledger, so the same collection reports
and account balances ERPNext already knows how to produce stay correct with
zero extra plumbing. erpnext's Payment Entry has no validation case for
party_type "Student" in get_valid_reference_doctypes() (it falls through to
None, so validate_reference_documents() never checks reference existence,
docstatus, or amount for a Student-party payment) — record_payment() below is
therefore the only gate that actually protects against a bad reference, and
it must be used instead of building Payment Entry documents ad hoc per form.

"Balance owed" fields (SMS Student Assessment.receivable/payment, SMS Wallet
Account.balance) are caches only. They are never incremented — they are
always fully recomputed from the real ledger (submitted Payment Entry
References, or submitted SMS Wallet Transaction rows) each time, the same
"recompute from source of truth, never trust an incrementally-updated cache"
pattern already used by registrar.py's compute_grade_points.
"""

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import flt

# Rounding tolerance for balance comparisons (a centavo), so float noise from
# repeated recomputation never trips an over/under-payment guard by itself.
FLT_TOLERANCE = 0.01


@frappe.whitelist()
def record_payment(
	assessment: str,
	amount: float,
	mode_of_payment: str | None = None,
	reference_no: str | None = None,
) -> dict:
	"""Single canonical entry point for recording a student's payment against
	an SMS Student Assessment. Creates and submits a real Payment Entry
	(party_type="Student") rather than a shadow ledger, then recomputes the
	assessment's payment/receivable from the real Payment Entry References —
	never trusts or increments a cached balance.
	"""
	amount = flt(amount)
	if amount <= 0:
		frappe.throw(_("Payment amount must be greater than zero."))

	doc = frappe.get_doc("SMS Student Assessment", assessment)
	if doc.docstatus != 1:
		frappe.throw(
			_("Assessment {0} must be submitted before a payment can be recorded against it.").format(assessment)
		)

	# erpnext's Payment Entry does not validate references for party_type
	# "Student" at all (get_valid_reference_doctypes() has no case for it),
	# so this is the only place that actually checks the payment makes
	# sense. Overpayment is allowed (refunds/credits happen in the real
	# world) but flagged rather than silently swallowed.
	if amount - flt(doc.receivable) > FLT_TOLERANCE:
		frappe.msgprint(
			_("Payment of {0} exceeds the outstanding receivable of {1} for {2}. Recording as an overpayment.").format(
				amount, doc.receivable, assessment
			)
		)

	paid_to = frappe.get_cached_value("Company", doc.company, "default_cash_account")
	if not paid_to:
		frappe.throw(_("Company {0} has no Default Cash Account configured.").format(doc.company))

	pe = frappe.get_doc(
		{
			"doctype": "Payment Entry",
			"payment_type": "Receive",
			"party_type": "Student",
			"party": doc.student,
			"party_name": doc.student_name,
			"company": doc.company,
			"paid_from": doc.receivable_account,
			"paid_to": paid_to,
			"paid_amount": amount,
			"received_amount": amount,
			"reference_no": reference_no or "N/A",
			"reference_date": frappe.utils.today(),
			"references": [
				{
					"reference_doctype": "SMS Student Assessment",
					"reference_name": doc.name,
					"allocated_amount": amount,
					"total_amount": doc.total_fee,
					"outstanding_amount": doc.receivable,
				}
			],
		}
	)
	if mode_of_payment:
		pe.mode_of_payment = mode_of_payment

	pe.insert(ignore_permissions=frappe.has_permission("Payment Entry", "create"))
	pe.submit()

	balance = refresh_assessment_balance(doc.name)
	return {
		"payment_entry": pe.name,
		"assessment_payment": balance["payment"],
		"assessment_receivable": balance["receivable"],
	}


@frappe.whitelist()
def refresh_assessment_balance(assessment: str) -> dict:
	"""Recomputes SMS Student Assessment.payment/receivable by summing every
	submitted Payment Entry Reference row against this assessment — a full
	recompute from the real ledger, never an increment of the cached value.
	Written via frappe.db.set_value (not doc.save()) so this never re-triggers
	validate()'s one-active-assessment check.
	"""
	total_fee = frappe.db.get_value("SMS Student Assessment", assessment, "total_fee")
	if total_fee is None:
		frappe.throw(_("SMS Student Assessment {0} not found.").format(assessment))

	per = frappe.qb.DocType("Payment Entry Reference")
	pe = frappe.qb.DocType("Payment Entry")
	result = (
		frappe.qb.from_(per)
		.join(pe)
		.on(per.parent == pe.name)
		.select(Sum(per.allocated_amount).as_("total"))
		.where(
			(per.reference_doctype == "SMS Student Assessment")
			& (per.reference_name == assessment)
			& (pe.docstatus == 1)
		)
	).run(as_dict=True)

	payment = flt(result[0].total) if result and result[0].total is not None else 0.0
	receivable = flt(total_fee) - payment

	frappe.db.set_value("SMS Student Assessment", assessment, {"payment": payment, "receivable": receivable})
	return {"payment": payment, "receivable": receivable}


@frappe.whitelist()
def compute_discount(discount_code: str, tuition: float, misc_fee: float) -> dict:
	"""Pure calculation helper mirroring the legacy's discount-calc logic in
	one place, for the frontend to call before an SMS Student Assessment is
	even created (rather than duplicating this math per form — one of the
	original blueprint's flagged tech-debt items).
	"""
	discount = frappe.get_doc("SMS Discount", discount_code)
	if discount.is_disabled:
		frappe.throw(_("Discount {0} is disabled.").format(discount_code))

	tuition = flt(tuition)
	misc_fee = flt(misc_fee)

	if discount.tf_discount_mode == "Fixed Amount":
		tuition_discount = flt(discount.tf_discount_value)
	elif discount.tf_discount_mode == "Percentage":
		base = tuition
		if discount.on_tf and discount.tf_base == "Tuition + Misc":
			base = tuition + misc_fee
		tuition_discount = base * flt(discount.tf_discount_value) / 100
	else:
		tuition_discount = 0.0

	if discount.misc_discount_mode == "Fixed Amount":
		misc_discount = flt(discount.misc_discount_value)
	elif discount.misc_discount_mode == "Percentage":
		misc_discount = misc_fee * flt(discount.misc_discount_value) / 100
	else:
		misc_discount = 0.0

	return {"tuition_discount": flt(tuition_discount), "misc_discount": flt(misc_discount)}


def _ensure_wallet_enabled() -> None:
	if not frappe.db.get_single_value("Education Settings", "enable_wallet"):
		frappe.throw(_("The Wallet feature is not enabled (Education Settings > Enable Wallet)."))


@frappe.whitelist()
def wallet_topup(wallet_account: str, amount: float, particular: str | None = None) -> dict:
	"""Creates and submits an SMS Wallet Transaction crediting a top-up. The
	doctype's own on_submit() fully recomputes SMS Wallet Account.balance from
	all submitted transactions — this function never writes balance directly.
	"""
	_ensure_wallet_enabled()
	amount = flt(amount)
	if amount <= 0:
		frappe.throw(_("Top-up amount must be greater than zero."))
	if not frappe.db.exists("SMS Wallet Account", wallet_account):
		frappe.throw(_("Wallet Account {0} not found.").format(wallet_account))

	txn = frappe.get_doc(
		{
			"doctype": "SMS Wallet Transaction",
			"wallet_account": wallet_account,
			"transaction_type": "Top-up",
			"credit": amount,
			"particular": particular,
		}
	)
	txn.insert(ignore_permissions=frappe.has_permission("SMS Wallet Transaction", "create"))
	txn.submit()
	return {"name": txn.name, "balance": frappe.db.get_value("SMS Wallet Account", wallet_account, "balance")}


@frappe.whitelist()
def wallet_payment(wallet_account: str, amount: float, particular: str | None = None) -> dict:
	"""Creates and submits an SMS Wallet Transaction debiting a payment.
	Checks the wallet's current balance fresh from the database (never a
	value the caller might be holding stale) before allowing the debit.
	"""
	_ensure_wallet_enabled()
	amount = flt(amount)
	if amount <= 0:
		frappe.throw(_("Payment amount must be greater than zero."))
	if not frappe.db.exists("SMS Wallet Account", wallet_account):
		frappe.throw(_("Wallet Account {0} not found.").format(wallet_account))

	current_balance = flt(frappe.db.get_value("SMS Wallet Account", wallet_account, "balance"))
	if amount - current_balance > FLT_TOLERANCE:
		frappe.throw(
			_("Insufficient wallet balance: available {0}, requested {1}.").format(current_balance, amount)
		)

	txn = frappe.get_doc(
		{
			"doctype": "SMS Wallet Transaction",
			"wallet_account": wallet_account,
			"transaction_type": "Payment",
			"debit": amount,
			"particular": particular,
		}
	)
	txn.insert(ignore_permissions=frappe.has_permission("SMS Wallet Transaction", "create"))
	txn.submit()
	return {"name": txn.name, "balance": frappe.db.get_value("SMS Wallet Account", wallet_account, "balance")}


@frappe.whitelist()
def get_wallet_balance(wallet_account: str) -> dict:
	"""Thin read accessor for the frontend. Balance is a recomputed cache
	(see SMS Wallet Transaction.refresh_wallet_balance()); callers should go
	through this rather than assuming a direct /api/resource/ read is the
	source of truth.
	"""
	return {"balance": frappe.db.get_value("SMS Wallet Account", wallet_account, "balance")}


@frappe.whitelist()
def record_past_receivable(student: str, as_of_date: str | None = None) -> dict:
	"""Thin snapshot-log writer for the scheduled job the migration blueprint
	calls for (another step owns the actual cron wiring in hooks.py). Sums
	the student's real GL Entry rows (party_type="Student") fresh every time
	rather than trusting any cached balance.
	"""
	if not frappe.db.exists("Student", student):
		frappe.throw(_("Student {0} not found.").format(student))

	gle = frappe.qb.DocType("GL Entry")
	result = (
		frappe.qb.from_(gle)
		.select((Sum(gle.debit) - Sum(gle.credit)).as_("receivable"))
		.where((gle.party_type == "Student") & (gle.party == student) & (gle.is_cancelled == 0))
	).run(as_dict=True)

	receivable = flt(result[0].receivable) if result and result[0].receivable is not None else 0.0

	doc = frappe.get_doc(
		{
			"doctype": "SMS Past Receivable",
			"student": student,
			"receivable": receivable,
			"as_of_date": as_of_date or frappe.utils.today(),
		}
	)
	doc.insert(ignore_permissions=frappe.has_permission("SMS Past Receivable", "create"))
	return {"name": doc.name, "receivable": receivable}
