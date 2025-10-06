# Fix Combobox Refresh Issue

## Tasks
- [x] Modify sales/views.py: add _load_product_options() to refresh_all
- [x] Modify payroll/views.py: add _load_employees_combo() to refresh_all
- [x] Modify loans/views.py: add refresh_all method with load_loans, load_employees, update_alerts
- [x] Modify advances_to_third_parties/views.py: add _load_product_options() to refresh_all
- [x] Modify inventory/views.py: add _load_product_options() to refresh_all
- [x] Modify main_window.py: add case for advances in _on_tab_changed
- [ ] Test the changes
