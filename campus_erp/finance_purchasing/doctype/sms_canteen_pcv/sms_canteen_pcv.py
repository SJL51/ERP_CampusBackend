import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class SMSCanteenPCV(Document):
	def validate(self):
		if not self.encoder:
			self.encoder = frappe.session.user
		self.amount = sum(flt(row.debit_amount) for row in self.details)

	def before_submit(self):
		if not self.details:
			frappe.throw(_("At least one detail line is required before submitting a PCV."))
