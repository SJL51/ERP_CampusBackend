# Copyright (c) 2026, School Administration and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SMSStatutoryContributionBracket(Document):
	def validate(self):
		if self.range_to and self.range_from and self.range_to < self.range_from:
			frappe.throw("Salary Range To must not be less than Salary Range From")

		shares = [self.er_share or 0, self.ee_share or 0]
		if self.bracket_type == "SSS":
			shares.append(self.ec_share or 0)
		self.total = sum(shares)
