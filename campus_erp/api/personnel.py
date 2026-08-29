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
@frappe.whitelist()
def list_recent_loans(search=None, limit=20):
    filters = []
    if search:
        filters = [["employee_name", "like", f"%{search}%"]]
    return frappe.get_all(
        "SMS Personnel Loan",
        filters=filters,
        fields=["parent as personnel_info", "employee_id", "employee_name", "department",
                "al_no", "date", "loan_type", "basic_pay", "previous_loan", "amount", "reason"],
        order_by="date desc",
        limit_page_length=limit,
    )

@frappe.whitelist()
def add_loan_application(employee_id, loan_type, amount, reason=None, basic_pay=None, previous_loan=None):
    parent = frappe.get_doc("Personnel Info", employee_id)
    al_no = frappe.model.naming.make_autoname("LN.#####")
    row = parent.append("loan_ledgers", {
        "employee_id": employee_id,
        "employee_name": f"{parent.first_name} {parent.last_name}",
        "department": parent.department,
        "al_no": al_no,
        "date": frappe.utils.today(),
        "loan_type": loan_type,
        "basic_pay": basic_pay,
        "previous_loan": previous_loan,
        "amount": amount,
        "reason": reason,
    })
    parent.save()
    return {"success": True, "name": row.name, "al_no": al_no}

@frappe.whitelist()
def get_personnel_kpis():
    total = frappe.db.count("Personnel Info")
    rows = frappe.db.sql(
        "select employee_status, count(*) as n from `tabPersonnel Info` group by employee_status",
        as_dict=True,
    )
    counts = {"Regular": 0, "Contractual": 0, "Part Timer": 0, "Probationary": 0}
    for row in rows:
        status = row.get("employee_status")
        if status in counts:
            counts[status] = row["n"]
    return {
        "total": total,
        "regular": counts["Regular"],
        "contractual": counts["Contractual"],
        "part_timer": counts["Part Timer"],
        "probationary": counts["Probationary"],
    }


@frappe.whitelist()
def get_employee(employee_id):
    return frappe.db.get_value(
        "Personnel Info",
        employee_id,
        ["name as employee_id", "first_name", "last_name", "department"],
        as_dict=True,
    )
