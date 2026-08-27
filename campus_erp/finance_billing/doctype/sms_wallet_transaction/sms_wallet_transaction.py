import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import flt


class SMSWalletTransaction(Document):
	def validate(self):
		if not self.debit and not self.credit:
			frappe.throw(_("Either Debit or Credit must be set."))
		wallet = frappe.get_doc("SMS Wallet Account", self.wallet_account)
		if wallet.disabled:
			frappe.throw(_("Wallet Account {0} is disabled.").format(self.wallet_account))
		if self.debit and self.transaction_type not in ("Payment", "Reversal"):
			frappe.throw(_("Debit is only valid for Payment or Reversal transactions."))

	def on_submit(self):
		self.refresh_wallet_balance()

	def on_cancel(self):
		self.refresh_wallet_balance()

	def refresh_wallet_balance(self):
		txn = frappe.qb.DocType("SMS Wallet Transaction")
		result = (
			frappe.qb.from_(txn)
			.select((Sum(txn.credit) - Sum(txn.debit)).as_("balance"))
			.where((txn.wallet_account == self.wallet_account) & (txn.docstatus == 1))
		).run()
		new_balance = flt(result[0][0]) if result and result[0][0] is not None else 0
		frappe.db.set_value("SMS Wallet Account", self.wallet_account, "balance", new_balance)
