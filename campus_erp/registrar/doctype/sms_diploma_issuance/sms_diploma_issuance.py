import frappe
from frappe.model.document import Document


class SMSDiplomaIssuance(Document):
	def validate(self):
		if not self.balance_cleared_confirmed:
			frappe.throw("Balance must be confirmed cleared before a diploma can be issued.")
