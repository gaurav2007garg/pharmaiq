"""Build a portable, formula-driven audit workbook from the active simulation."""
from io import BytesIO
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter as L
from simulator import validate, shares


def build_audit(df, baseline, scenario, constants=None, diagnostics=None):
    df=validate(df)
    unit='respondent_id' if 'respondent_id' in df else 'segment'
    products=list(scenario)
    if list(baseline)!=products: raise ValueError('Baseline and scenario products must match in order.')
    attrs=list(df.attribute.unique()); keys=list(dict.fromkeys(zip(df.attribute,df.level)))
    matrix=df.pivot(index=unit,columns=['attribute','level'],values='utility')
    meta=df.groupby(unit)[['segment','weight']].first().reindex(matrix.index)
    wb=Workbook(); guide=wb.active; guide.title='Read me'
    for row in [['PharmaIQ | Preference share audit'],['Scope','Active filtered population; baseline and scenario; MNL'],['Method','Sum selected part-worths; EXP(total minus row maximum); normalize within respondent; weight probabilities.'],['Inputs','Utilities and Profiles are exported snapshots. Selected utility cells link to the exported utility matrix for the exported profiles.'],['Important','Changing a profile label in Excel does not change the linked utility cells. Reconfigure profiles in PharmaIQ and export again.'],['Validation','Summary compares Excel formulas with Python results at export time.'],['Interpretation','Conditional preference shares, not actual market shares. No opt-out.'],['Unit',unit],['Units',len(meta)],['Total weight',float(meta.weight.sum())]]: guide.append(row)
    u=wb.create_sheet('Utilities'); u.append([unit,'Segment','Weight']+[f'{a} | {l}' for a,l in keys]);
    for idx,m in meta.iterrows(): u.append([str(idx),str(m.segment),float(m.weight)]+[float(matrix.loc[idx,k]) for k in keys])
    p=wb.create_sheet('Profiles'); p.append(['Case','Product']+attrs)
    for case,profiles in [('Baseline',baseline),('Scenario',scenario)]:
        for name in products: p.append([case,name]+[profiles[name][a] for a in attrs])
    if constants is not None:
        ksheet=wb.create_sheet('Calibration constants'); ksheet.append([unit]+products)
        for idx in meta.index: ksheet.append([str(idx)]+[float(constants.loc[idx,p]) for p in products])
        guide.append(['Calibration','Fixed utility constants added to each product total. Targets and fit refer to the full calibration population; summary uses the active filter.'])
        if diagnostics is not None:
            ds=wb.create_sheet('Calibration fit'); ds.append(list(diagnostics.columns))
            for row in diagnostics.itertuples(index=False,name=None): ds.append(list(row))
    n=len(products); a=len(attrs); end=len(meta)+1; probcols={}; weightedcols={}
    for case,profiles in [('Baseline',baseline),('Scenario',scenario)]:
        s=wb.create_sheet(case+' calc'); headers=[unit,'Segment','Weight']
        for name in products: headers += [f'{name} | {attr}' for attr in attrs]
        totalstart=4+n*a; maxcol=totalstart+n; expstart=maxcol+1; denom=expstart+n; probstart=denom+1; weightedstart=probstart+n; check=weightedstart+n
        headers += [f'{name} | Total utility' for name in products]+['Max utility']+[f'{name} | exp shifted' for name in products]+['Denominator']+[f'{name} | Probability' for name in products]+[f'{name} | Weighted probability' for name in products]+['Probability sum']
        s.append(headers)
        for r in range(2,end+1):
            row=[f'=Utilities!A{r}',f'=Utilities!B{r}',f'=Utilities!C{r}']
            for name in products:
                for attr in attrs: row.append(f'=Utilities!{L(4+keys.index((attr,profiles[name][attr])))}{r}')
            for j in range(n): row.append(f'=SUM({L(4+j*a)}{r}:{L(3+(j+1)*a)}{r})'+(f"+'Calibration constants'!{L(j+2)}{r}" if constants is not None else ''))
            row.append(f'=MAX({L(totalstart)}{r}:{L(maxcol-1)}{r})')
            for j in range(n): row.append(f'=EXP({L(totalstart+j)}{r}-{L(maxcol)}{r})')
            row.append(f'=SUM({L(expstart)}{r}:{L(denom-1)}{r})')
            for j in range(n): row.append(f'={L(expstart+j)}{r}/{L(denom)}{r}')
            for j in range(n): row.append(f'=C{r}*{L(probstart+j)}{r}')
            row.append(f'=SUM({L(probstart)}{r}:{L(weightedstart-1)}{r})'); s.append(row)
        for col in range(probstart,weightedstart):
            for r in range(2,end+1): s.cell(r,col).number_format='0.00%'
        for r in range(2,end+1): s.cell(r,check).number_format='0.000000'
        probcols[case]=probstart; weightedcols[case]=weightedstart
    summary=wb.create_sheet('Share summary',1); summary.append(['Population','Product','Units','Weight','Baseline Excel','Scenario Excel','Change (pp)','Baseline Python','Scenario Python','Max abs difference','Check'])
    b,bd=shares(df,baseline,constants); c,cd=shares(df,scenario,constants)
    segments=list(meta.groupby('segment').weight.sum().loc[lambda x:x>0].index)
    for group in [None]+segments:
        for j,name in enumerate(products):
            r=summary.max_row+1; label='Overall' if group is None else str(group)
            count=f'=COUNTA(Utilities!A2:A{end})' if group is None else f'=COUNTIF(Utilities!B2:B{end},A{r})'
            weight=f'=SUM(Utilities!C2:C{end})' if group is None else f'=SUMIF(Utilities!B2:B{end},A{r},Utilities!C2:C{end})'
            forms=[]
            for case in ['Baseline','Scenario']:
                col=L(weightedcols[case]+j); rng=f"'{case} calc'!{col}2:{col}{end}"
                forms.append(f'=SUM({rng})/D{r}' if group is None else f'=SUMIF(Utilities!B2:B{end},A{r},{rng})/D{r}')
            bv=float(b[name]) if group is None else float(bd.loc[(bd.segment==group)&(bd['product']==name),'share'].iloc[0]); cv=float(c[name]) if group is None else float(cd.loc[(cd.segment==group)&(cd['product']==name),'share'].iloc[0])
            summary.append([label,name,count,weight,*forms,f'=(F{r}-E{r})*100',bv,cv,f'=MAX(ABS(E{r}-H{r}),ABS(F{r}-I{r}))',f'=IF(J{r}<1E-9,"PASS","CHECK")'])
            for col in [5,6,8,9]: summary.cell(r,col).number_format='0.00%'
            summary.cell(r,7).number_format='+0.00;-0.00;0.00'; summary.cell(r,10).number_format='0.00E+00'
    for s in wb:
        s.freeze_panes='D2' if s.title.endswith('calc') or s.title=='Utilities' else 'A2'
        s.sheet_view.showGridLines=False
        for cell in s[1]: cell.fill=PatternFill('solid',fgColor='17365D'); cell.font=Font(color='FFFFFF',bold=True); cell.alignment=Alignment(wrap_text=True,vertical='center')
        s.row_dimensions[1].height=44
        for col in range(1,s.max_column+1): s.column_dimensions[L(col)].width=26 if col<=2 else 22
        if s.title!='Read me': s.auto_filter.ref=s.dimensions
    guide.column_dimensions['A'].width=26; guide.column_dimensions['B'].width=105
    for row in guide.iter_rows(min_row=2):
        row[1].alignment=Alignment(wrap_text=True,vertical='center'); guide.row_dimensions[row[0].row].height=34
    output=BytesIO(); wb.save(output); return output.getvalue()
