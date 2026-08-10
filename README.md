# Teacher Allocation Optimizer

**How to optimally assign hundreds of teachers to courses while respecting eligibility rules, workload limits, and institutional constraints?**

Full-stack optimization system that automates teacher-to-course allocation using CP-SAT (Constraint Programming), with data validation, audit trails, scenario simulation, and a web dashboard for operational monitoring.

## Key Highlights

| Feature | Detail |
|---------|--------|
| Solver | Google OR-Tools CP-SAT |
| Approach | Constraint programming + GRASP metaheuristic |
| Validation | Automated rule checking with inconsistency reports |
| Scenarios | What-if policy simulations for decision support |
| Interface | React + FastAPI web dashboard |
| Audit | Full traceability per allocation round |

## Stack

`Python` · `OR-Tools (CP-SAT)` · `FastAPI` · `React` · `TypeScript` · `Vite` · `Pandas` · `SQLite`

## Architecture

```
├── vbeta1.0/               # Production release package
│   ├── engines/            # Primary + scenario engines
│   ├── backend/            # API with auth & coordination
│   ├── frontend/           # Built React app
│   ├── docs/               # Full documentation (10 chapters)
│   └── scripts/            # Install, test, release tools

```

## How It Works

1. **Upload** — Institutional spreadsheet with teachers, courses, and constraints
2. **Validate** — Automated rule-checking flags inconsistencies before solving
3. **Optimize** — CP-SAT solver finds optimal teacher-course assignments
4. **Audit** — Every round generates traceability reports (JSON + XLSX)
5. **Simulate** — Run alternative scenarios to compare policy impacts
6. **Monitor** — Web dashboard tracks execution and results

## How to Run

```bash
git clone https://github.com/guilhermehrsilva/teacher-allocation-optimizer.git
cd teacher-allocation-optimizer/vbeta1.0
pip install -r requirements.txt
python executar.py
```

### Web Interface

```bash
# Backend
cd vbeta1.0/backend && pip install -r requirements.txt && python run.py

# Frontend
cd vbeta1.0/frontend && npm install && npm run dev
```
