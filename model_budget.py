"""Persistent conservative cost reservations for model inference."""
import math
import threading
import uuid

class Budget:
    def __init__(self,max_cost,daily,metadata,gateway=None,*,wait_for_capacity=False):
        if not math.isfinite(max_cost) or max_cost<=0:raise ValueError('max_cost must be positive')
        if gateway is None:import llm;gateway=llm
        self.gateway=gateway;self.max_cost=max_cost;self.daily=daily;self.metadata=metadata
        self.baseline=gateway.spent('openrouter');self.lock=threading.Lock();self.uncertain=0
        if not math.isfinite(self.baseline) or self.baseline<0:raise ValueError('Invalid model ledger')
        self.condition=threading.Condition(self.lock);self.active=0
        self.wait_for_capacity=wait_for_capacity

    def call(self,model,messages,max_tokens,tag,**options):
        gateway=self.gateway;pricing=self.metadata[model]['pricing']
        input_bound=sum(len(m['content'].encode()) for m in messages)+500
        # Bytes conservatively bound input tokens. A tier above that bound cannot apply.
        # Unknown threshold formats remain included, so new provider formats fail safely.
        tiers=[pricing,*[tier for tier in pricing.get('overrides',[])
            if type(tier.get('min_prompt_tokens')) not in (int,float)
            or not math.isfinite(tier['min_prompt_tokens'])
            or tier['min_prompt_tokens']<=input_bound]]
        input_rate=max(float(t.get('prompt',pricing['prompt'])) for t in tiers)
        output_rate=max(float(t.get('completion',pricing['completion'])) for t in tiers)
        request_rate=max(float(t.get('request',pricing.get('request',0)) or 0) for t in tiers)
        if any(not math.isfinite(v) or v<0 for v in (input_rate,output_rate,request_rate)):raise ValueError('Invalid model pricing')
        reserve=input_bound*input_rate+max_tokens*output_rate+request_rate
        return self.call_reserved(model,messages,max_tokens,tag,reserve,response_format={'type':'json_object'},**options)

    def call_reserved(self,model,messages,max_tokens,tag,reserve,*,request_timeout=240,**options):
        """Use a conservative bound that also includes caller-specific tool costs."""
        if type(reserve) not in (int,float) or not math.isfinite(reserve) or reserve<0:
            raise ValueError('Invalid request reservation')
        gateway=self.gateway
        request_id='federal-analysis-'+uuid.uuid4().hex
        with self.condition:
            while True:
                spent=gateway.spent('openrouter')
                monthly=gateway.spent_this_month('openrouter') if self.daily else 0
                if not math.isfinite(spent) or not math.isfinite(monthly) or spent<self.baseline-1e-8:
                    raise ValueError('Invalid or regressed model ledger')
                blocked=(spent-self.baseline+reserve>self.max_cost or spent+reserve>=gateway.BUDGETS['openrouter'] or
                    (self.daily and monthly+reserve>=gateway.BUDGETS.get('monthly',{}).get('openrouter',math.inf)))
                if not blocked:break
                if not self.wait_for_capacity or not self.active:
                    raise gateway.BudgetExceeded('Federal analysis budget limit; resume later')
                self.condition.wait()
            gateway._log('openrouter',reserve,tag,{'phase':'reservation','request_id':request_id,'model':model,'cost_uncertain':True})
            self.active+=1
        # One transport attempt per persisted reservation. Uncertain requests keep their charge.
        try:
            try:
                result=gateway.chat(messages,model=model,tag=tag,max_tokens=max_tokens,
                                    retry_attempts=1,request_timeout=request_timeout,**options)
            except Exception as exc:
                with self.lock:
                    if isinstance(exc,getattr(gateway,'PreflightBudgetExceeded',())):
                        gateway._log('openrouter',-reserve,tag,{'phase':'reconciliation','request_id':request_id,'model':model,
                            'reason':'local_preflight_rejection','cost_uncertain':False})
                    elif isinstance(exc,getattr(gateway,'OpenRouterRequestError',())) and exc.rejected_before_inference:
                        # Only a confirmed rejection before provider dispatch releases its charge.
                        gateway._log('openrouter',-reserve,tag,{'phase':'reconciliation','request_id':request_id,'model':model,
                            'http_status':exc.status_code,'limit_source':exc.limit_source,'reason':'rejected_before_inference',
                            'cost_uncertain':False})
                    else:self.uncertain+=1
                raise
            cost=(result.get('usage') or {}).get('cost')
            with self.lock:
                if type(cost) in (int,float) and math.isfinite(cost) and cost>=0:
                    gateway._log('openrouter',-reserve,tag,{'phase':'reconciliation','request_id':request_id,'model':model,
                        'generation_id':result.get('id'),'cost_uncertain':False})
                else:self.uncertain+=1
            return result
        finally:
            with self.condition:
                self.active-=1
                self.condition.notify_all()

