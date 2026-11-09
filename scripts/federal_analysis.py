"""Federal broad analysis: offline plan/build and bounded resumable model labeling."""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import federal_analysis as analysis

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['plan','label','build'])
    parser.add_argument('--ids',help='Comma-separated current eligible profile IDs')
    parser.add_argument('--stages',help='Comma-separated model stages for a bounded retry')
    parser.add_argument('--max-cost',type=float,default=5)
    parser.add_argument('--budget-baseline',type=float,help='Earlier ledger spend for a shared model-stage allowance')
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--daily',action='store_true')
    args=parser.parse_args();ids=set(args.ids.split(',')) if args.ids else None
    if args.command=='plan':report=analysis.plan(ROOT,ids)
    elif args.command=='build':report=analysis.build(ROOT)['coverage']
    else:
        from federal_analysis_models import run
        allowance=args.max_cost
        if args.budget_baseline is not None:
            import llm
            allowance=max(0,allowance-(llm.spent('openrouter')-args.budget_baseline))
        report=run(ROOT,allowance,args.workers,ids,args.daily,stages=args.stages.split(',') if args.stages else None)
    print(json.dumps(report,indent=2))
    if args.command=='label' and report['status']!='ok':return 1
    return 0
if __name__=='__main__':raise SystemExit(main())
