# Finance App
# Fivera

A web app for UK sole traders. It shows how much tax you owe as you go, rather than finding out in January.

www.fivera.co.uk

## The problem

When you go self-employed, nobody takes tax off your income for you. You track your income and expenses all year, work out which costs are allowable, and then face a Self Assessment bill. That bill can include payments on account for the following year. The bill is even harder to estimate if you also have a salary, because your business profit is taxed on top of your PAYE income.

## What it does

- **Live tax estimate:** income tax, Class 4 National Insurance and student loan repayments on your profit, updated as you add income and expenses.
- **Side hustle aware:** stacks your business profit on top of any employed salary, so the estimate only shows the extra tax you owe and doesn't double-count what PAYE has already taken.
- **Allowable expenses:** HMRC expense categories, with dual-purpose costs handled by business-use percentage, simplified mileage, and flat-rate or actual home office costs.
- **Payments on account:** works out your balancing payment and both payments on account, and shows them against the 31 January and 31 July deadlines.
- **Invoicing:** client contacts, PDF invoices and status tracking, with paid invoices flowing straight into income.
- **Recurring and upcoming items:** schedule regular income and costs, and approve each one when it actually happens.
- **Tax year switching:** 2025/26 and 2026/27 rates. All thresholds live in config, not code, so a new tax year is a data update.

A personal side covers salary take-home pay, savings, debts and pensions.

## Tech stack

- **Back end:** Python, FastAPI, SQLAlchemy, Alembic and PostgreSQL, hosted on Railway.
- **Front end:** React and Vite, hosted on Cloudflare Pages.
- **Other:** JWT authentication, Resend for email, and test suites in pytest and Vitest.

## How it was built

Designed the product and specified the tax rules. Most of the code was written with Claude Code (AI-assisted development).

## Running locally

```bash
git clone https://github.com/b-a-skinner/finance-app.git

# Back end
cd finance-app/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head && python seed.py
uvicorn app.main:app --reload

# Front end (in a second terminal)
cd finance-app/frontend
npm install
npm run dev
```

*Estimates only. This app is not tax advice.* [Optional: a screenshot of the Business dashboard here]
