import frappe
from frappe.model.document import Document


class SMSTranscript(Document):
	def validate(self):
		if self.receivable_balance_at_issuance and self.receivable_balance_at_issuance > 0:
			frappe.throw("Receivable balance must be zero or less before a transcript can be issued.")
