# Power BI semantic model

`ServiceOpsAnalytics.SemanticModel` is a source-controlled Power BI semantic model in
TMDL format. It imports `analytics_mart.fct_ticket_performance` and
`analytics_mart.dim_date` from PostgreSQL and contains model measures for:

- SLA compliance and evaluated/compliant ticket counts;
- open and breached backlog plus average backlog age;
- first-response time and MTTR;
- reopened ticket count and reopen rate;
- ticket volume and month-over-month category trend.

Run the dbt build first. In Power BI Desktop, create or open a Power BI Project using the
TMDL semantic-model format, replace its generated semantic-model folder with
`ServiceOpsAnalytics.SemanticModel`, and restart Desktop. Set the `PostgreSQLHost` and
`PostgreSQLDatabase` parameters for the target environment, then supply PostgreSQL
credentials through Power BI's data-source settings. Credentials are intentionally absent
from these tracked files.

Use `Calendar[Date]` on the time axis and `Ticket Performance[Category]` as the legend for
category trends. `History Quality` separates exact V4+ lifecycle histories from the
explicit migration snapshots retained for older tickets.

The TMDL structure and required measures are checked in CI. Refresh and visual-layout
review still require Power BI Desktop or a Fabric workspace; neither is silently claimed
by the repository's cross-platform CI.
