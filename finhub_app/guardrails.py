from finhub_app.domain import ReportContext


SYSTEM_GUARDRAILS = """
You are generating an educational investment report for a beginner investor.
The user has limited investing capacity, around USD 100 per month.

Rules:
- Do not give hard buy, sell, short, or all-in instructions.
- Do not claim certainty about future price movement.
- Use cautious language: consider, monitor, review, may, could, appears.
- Explain reasons in beginner-friendly language.
- Highlight concentration risk and diversification needs.
- Prefer risk-aware guidance over frequent trading.
- Include that the report is educational analysis, not financial advice.
- When suggesting a next step, make it budget-aware and conservative.
- Keep the short-term impact score separate from the long-term business quality score.
- Explain business quality metrics plainly; do not overstate incomplete or proxy data.
"""


def build_report_prompt(context: ReportContext) -> str:
    return f"""
Create a daily pre-market investment report.

User profile:
- Monthly budget: USD {context.profile.monthly_budget_usd:.2f}
- Beginner: {context.profile.beginner}

Portfolio and watchlist:
{context.positions}

Market snapshots:
{context.market_snapshots}

Fundamental snapshots:
{context.fundamental_snapshots}

News:
{context.news}

SEC filings:
{context.filings}

Impact assessments:
{context.impacts}

Business quality assessments:
{context.business_quality}

Required sections:
1. Plain-English summary
2. Short-term impact score
3. Business quality score
4. Holdings impact
5. Watchlist opportunities
6. Diversification and budget guidance
7. Key risks
8. No-urgent-action note when appropriate
9. Educational disclaimer
"""
