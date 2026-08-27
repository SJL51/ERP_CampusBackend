import frappe

@frappe.whitelist()
def search_personnel(query):
    query = f"%{query}%"
    return frappe.get_all(
        "Personnel Info",
        or_filters=[
            ["first_name", "like", query],
            ["last_name", "like", query],
            ["middle_name", "like", query],
        ],
        fields=["name as employee_id", "first_name", "last_name", "middle_name", "department"],
        limit_page_length=10,
    )

@frappe.whitelist()
def list_recent_leaves(search=None, limit=20):
    filters = []
    if search:
        filters = [["employee_name", "like", f"%{search}%"]]
    return frappe.get_all(
        "SMS Personnel Leaves",
        filters=filters,
        fields=["parent as personnel_info", "employee_id", "employee_name", "department",
                "leave_type", "from_date", "to_date", "half_day", "reason", "date"],
        order_by="date desc",
        limit_page_length=limit,
    )
    
@frappe.whitelist()
def add_leave_application(employee_id, leave_type, from_date, to_date, half_day=0, reason=None, other_leave_reason=None):
    parent = frappe.get_doc("Personnel Info", employee_id)
    row = parent.append("leaves", {
        "employee_id": employee_id,
        "employee_name": f"{parent.first_name} {parent.last_name}",
        "department": parent.department,
        "date": frappe.utils.today(),
        "leave_type": leave_type,
        "other_leave_reason": other_leave_reason,
        "from_date": from_date,
        "to_date": to_date,
        "half_day": half_day,
        "reason": reason,
    })
    parent.save()
    return {"success": True, "name": row.name}