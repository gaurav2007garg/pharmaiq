# PharmaIQ v0.3
A local Streamlit prototype of a segmented conjoint preference simulator. The other two modules are placeholders.

## Windows PowerShell
Install Python 3.11 or 3.12 from python.org if needed. Extract this ZIP and open PowerShell in the extracted `pharmaiq` folder.

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m streamlit run app.py
```

Open the localhost URL printed in the terminal. Ctrl+C stops the server.

## Data
The included synthetic CSV has segment, weight, attribute, level, utility columns. Weights repeat for each row within a segment and are normalized across segments. Each segment must contain all attribute/level combinations. The model uses segment-average utilities, a multinomial logit and weighted segment shares. These are preference shares, not actual market forecasts. No opt-out or alternative-specific constants. Segment-average predictions may differ from respondent-level predictions. No API key is needed.

## Test status
Core model unit tests are included. Browser/interface tests and user acceptance testing are still required.

## v0.3 respondent-level simulation
Upload the existing five-column format for segment averages, or add `respondent_id` for individual utilities. Each respondent needs a complete set of attribute levels, a consistent segment and a nonnegative weight repeated on every row. Use weight 1 for unweighted research. The included synthetic respondent CSV contains 200 fictional HCPs. Probabilities are computed separately per respondent using MNL and then weighted across the selected population. Attribute importance is calculated per respondent before weighted aggregation; respondents with zero total utility range are excluded from importance only. Segment filters apply to baseline and scenario alike. Baselines remain session-only. Individual utility estimation from raw choice tasks is not yet implemented. Individual probabilities are exportable; avoid uploading identifiable research data. Twelve model unit tests passed; browser testing remains required.

## v0.4.0 — Calibration
Enable Market share calibration after setting and saving the baseline profiles. Choose stated or observed shares and overall, segment, or (stated shares with respondent data) respondent calibration. Targets are fractions, not percentages, and must sum to one per group. Download the template for the selected alternative set. `sample_stated_shares.csv` is a fictional respondent-level target file for the default 200-HCP, three-product demo. It is not survey evidence. The first product is the reference constant (zero). Overall and segment fits use iterative proportional updates; respondent fits use log target/probability ratios. Rows with zeros are smoothed with a configurable uniform mixture (default 0.1%). Changing the locked baseline refits constants, changing scenario profiles or segment filters does not. Calibration fit is for the full dataset, simulation is for the selected population. Audit exports include fixed fitted constants and target diagnostics; a separate uncalibrated audit can also be downloaded. Excel recalculates shares, not the optimizer. No new dependencies. Browser and Excel recalculation acceptance tests remain local. Multiple saved scenarios and tornado charts are deferred.

## v0.5.0
Tornado sensitivity: select a product and show tornado analysis in the Sensitivity analysis tab. The reference is the current scenario; each attribute is varied across its tested levels while all other profiles and fitted calibration constants stay fixed. Ranges are ranked by span. Net competitive redistribution compares current and locked baseline shares; it is not a switching matrix.

CBC Utility Estimation: upload long-format CSV/XLSX, one row per displayed alternative, with respondent_id, task_id, alternative_id, chosen (0/1), optional segment, and one column per categorical attribute. All extra columns are treated as attributes. Exactly one choice per task. Reference level is the alphabetically first level of each attribute. Fits conditional logit with optional L2 penalty (default 0.01, total negative log likelihood scale), pooled or separately by segment. Holdout is by complete tasks within respondents. Fits use training tasks only; select 0% holdout to fit all tasks after validation. Reports log loss, equal-choice null, fractional tie-adjusted hit rate and McFadden pseudo-R² (holdout is predictive analogue). Full rank is checked on within-task contrasts. Export utilities, probabilities and diagnostics. Click Use estimated utilities in simulator, then switch to Market Simulator and select Estimated CBC utilities. Segment weights are respondent counts, not patient volumes. Separate segment models may differ in utility scale. No HB, respondent-specific estimation, none option, alternative-specific constants, standard errors or sampling weights in estimation. Simulator calibration and formula-driven audit retained; CBC estimation itself is not reproduced by Excel formulas.

## v0.6.0 — Oncology Intelligence

Open Oncology Intelligence in the sidebar. Synthetic demo runs offline; its assets and study IDs are fictional. Select Live ClinicalTrials.gov to search the public v2 registry (no key). Search conditions, interventions (including OR expressions), sponsor and additional terms; results are capped at the selected limit, with provenance and truncation warning. Filter phases/status/sponsors and export filtered studies, milestones and retrieval provenance. Counts are unique registered studies, not assets or market shares. A registry primary completion month is not a promised readout or regulatory milestone. Mechanism classification, line-of-therapy normalization, FDA monitoring and verified competitive threat assessment are not automated. The optional AI brief sends up to 50 selected public records to OpenAI (separate API key/billing; configurable model). Review NCT citations against source records; AI output is not automatically fact-checked. No key is written to disk by the app. Keep this version local until authentication and data governance are implemented. API docs: https://clinicaltrials.gov/data-api/api and https://developers.openai.com/api/docs/guides/text. Tests use mocked registry responses; live networking and Streamlit UI require local acceptance testing.
## v0.6.1
Top-ten sponsor view, development status filter, registry arm-based asset matrix, asset evidence export and optional single-study AI classification with editable review. Arm labels do not establish investigational focus or ownership. AI output is unverified and requires review. Existing simulator retained.
