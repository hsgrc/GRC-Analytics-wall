GRC Restricted Dashboard Pages

This bundle contains individual dashboard pages extracted from the user-supplied Analytics Wall HTML. The Analytics Wall wrapper is intentionally NOT included.

Install the contents under the project folder ui/dashboards/, but do not mount that folder as a public static directory. Serve a dashboard only through an application route which checks the current local development session and the exact authorized dashboard key.

Dashboard routing keys:
- challan.html -> challan and traffic fine questions
- customer_fleet.html -> customer-specific fleet questions (must be filtered to the verified customer's data before public deployment)
- insurance_vehicle.html -> insurance provider and vehicle insurance analysis
- renewal_membership.html -> membership status and renewal questions
- vehicle_portfolio.html -> aggregate vehicle portfolio and state-wise counts
- renewal_claims.html -> renewal/claims bucket questions

Security note: name/mobile matching alone is not real authentication. Keep the dashboard route local-development-only until proper login/session access controls and customer-level filtering are implemented.
