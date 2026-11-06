# Cross-model review (reviewer: openai/gpt-6.1-sol)

The reviewer is a different model family from the scorer (Claude Sonnet 5.5). It does two things: (1) **blind re-scoring** of everyone from the same evidence and rubric, and (2) an **audit**: it sees Sonnet's scores and cited quotes for the review packet, plus everyone whose blind score differs by ≥2, and checks them.

## 1. Blind agreement (all scored people)

| dimension | n (both scored) | exact | within 1 | Spearman ρ | Sonnet mean | reviewer mean | only one says insufficient |
|---|---|---|---|---|---|---|---|
| ai_overall | 581 | 76% | 100% | 0.90 | 2.11 | 1.87 | 15 |
| agi_pilled | 352 | 62% | 100% | 0.63 | 2.03 | 1.78 | 192 |
| x_risk | 502 | 84% | 98% | 0.87 | 1.72 | 1.75 | 69 |
| china_race | 415 | 72% | 97% | 0.88 | 2.17 | 1.85 | 159 |
| regulation | 535 | 80% | 100% | 0.86 | 2.40 | 2.36 | 40 |

"Exact" means within 0.5, because Sonnet's score is an average of two runs.

## 2. Audit

41 people, 205 person-dimensions. The reviewer disagreed on **36** (18%), flagged citations as not supporting the score on **67**, and flagged **7** summaries.

### Disagreements and citation problems

**Abdul El-Sayed** (Democratic, MI)

- **agi_pilled** (bad citations s30): His own description of AI as transformative and capable of shaping the world supports 2, but he does not explicitly anticipate AGI or human-level intelligence. In s30, the numerical job-loss forecast is attributed to Anthropic's CEO, not independently stated as his own prediction.
- **regulation** (bad citations s15): Explicit demands for a frontier-research pause and federal intervention clearly support 4. S15 merely announces 22 proposals without describing their contents, so it cannot establish their regulatory strength.

**Adriano Espaillat** (Democrat, NY)

- **agi_pilled** (bad citations s28): The statement that AI could 'revolutionize our society' in s20 supports transformative expectations without AGI. However, saying AI 'is NOW' in s28 establishes present importance, not the scale of transformation required for a 2.
- **china_race** (Sonnet insufficient_evidence → reviewer 1): The rubric expressly allows 1 when someone discusses AI substantively and race framing barely features. This extensive substantive record contains no China or race framing, so 1 is better supported than insufficient_evidence.

**Andrew Ogles** (Republican, TN)

- **agi_pilled** (bad citations s18): The transformative potential and absence of a ceiling described in s12 and s15 support 2, without establishing an expectation of AGI. In s18, the statement about capabilities beyond human understanding is attributed to an Anthropic witness, not expressed as Ogles's own expectation.
- **x_risk** (bad citations s15, s18, s38): Infrastructure destruction and economy-wide cyber vulnerabilities support serious misuse risk in s24 and s26. However, s15 compares competitive dynamics rather than endorsing AI catastrophe, s18 reports someone else's fear, and s38 supports the rubric's dismissive level for doomsday risk rather than level 2.

**Andy Harris** (Republican, MD)

- **ai_overall** (Sonnet 1.0 → reviewer 0; bad citations s4, s5): The statements present AI principally as a threat, including possible extinction, without acknowledging benefits. The extinction warning and call to put the brakes on superintelligence support 0 more directly than 1; outright rejection of all AI is not required for 0.
- **summary**: The summary is otherwise supported, but its attribution of data-center energy costs to Harris's AI concerns exceeds s2: that quote mentions companies' energy costs and ratepayers without identifying AI or data centers.

**Angus S. King, Jr.** (Independent, ME)

- **ai_overall** (Sonnet 2.0 → reviewer 1; bad citations ): The citations establish both benefits and concerns, but not roughly equal emphasis. Across the statements, concern dominates, particularly the warnings about concealment, uncontrolled capabilities, and possible extinction; acknowledged practical benefits make 1 more appropriate than 0.
- **agi_pilled** (bad citations s10, s21): Self-replication, increasing intelligence, concealment, and his endorsement of taking a ten-year extinction warning seriously support 3. However, s10 establishes only general transformative potential, while s21 reports Xi's warning rather than expressing King's own expectation of AGI.
- **x_risk** (bad citations s21): His call to heed the extinction warning, combined with his proposed regulatory slowdown and international safety dialogue, supports treating existential risk as a major priority. The probability in s24 is attributed to industry, but King explicitly endorses taking the warning seriously; s21 instead reports Xi's position.
- **china_race** (bad citations s21): S18 explicitly advocates dialogue with China, and s19 rejects a race to the bottom on safety, directly supporting 0. S21 reports Xi's warning but does not itself advocate cooperation or reject race framing.
- **summary**: The summary is largely supported, but 'permitting' is not established by the supplied statements: s4 refers only to an unspecified process. Also, his explicit objection is to a race to the bottom on AI safety, not necessarily to all competition with China.

**Anna Paulina Luna** (Republican, FL)

- **x_risk** (bad citations s34): The escape-from-containment claim and proposed kill switch to protect humanity directly support loss-of-control concern. However, s34 describes catastrophe from losing the AI race, not existential risk or loss of human control.
- **regulation** (bad citations s44, s22): Her proposed required kill switch, alongside explicit bans and criminal penalties for abusive deepfakes, supports substantial safety requirements, though not comprehensive licensing. Calling for a special session does not itself endorse regulation, and the unidentified 'AI clause' in s22 cannot establish a regulatory position.

**Bernard Sanders** (Independent, VT)

- **agi_pilled** (bad citations s161, s86, s218, s182): s161 reports scientists' predictions; s86 and s218 establish plausible superintelligence rather than independently establishing level 4, while s182 establishes transformative AI without AGI. Nevertheless, his own repeated demands to ban superintelligence and his civilizational and nuclear comparisons establish its centrality, supporting 4 overall.
- **x_risk** (bad citations s86): s86 explicitly establishes concern about existential risk and loss of control, but by itself fits level 3 rather than establishing top-tier priority. The other citations clearly establish level 4 through nuclear comparisons and urgent demands for international action.

**Betty McCollum** (Democrat, MN)

- **china_race** (Sonnet insufficient_evidence → reviewer 1; bad citations s2, s4): The rubric assigns 1 when substantive AI discussion exists but race framing barely features; these statements contain extensive substantive discussion and no China framing. Neither a generic national-security meeting reference nor military-surveillance concerns establish insufficient evidence under that rule.

**Bill Cassidy** (Republican, LA)

- **china_race** (Sonnet 2.0 → reviewer 0; bad citations s28, s13, s14): S28 explicitly challenges the race-to-superintelligence rationale, supporting 0 rather than 2. S13 concerns Chinese access to sensitive data, and s14 advocates global leadership without mentioning China; neither establishes recurring AI competition with China.
- **regulation** (bad citations s24): His endorsed restrictions on recursive self-improvement, self-generated goals and open-ended autonomy go beyond targeted privacy or child-safety rules and support 3 despite opposition to one-size-fits-all regulation. S24 asks about liability rather than endorsing liability requirements.

**Bill Foster** (Democrat, IL)

- **ai_overall** (Sonnet 2.0 → reviewer 1): The citations establish both benefits and concerns, but the substantive statements overwhelmingly emphasize dangers, inadequate preparedness, and urgent safeguards. General commitments to harness AI's potential and celebrations of research do not establish roughly equal optimism and concern.
- **regulation** (Sonnet 3.0 → reviewer 4; bad citations s76): S76 explicitly calls for comprehensive AI legislation, which the rubric places at 4 rather than 3. Licensing or a new agency is not required: his comprehensive-regulation demand, reinforced by mandatory hardware safeguards and physical-containment prescriptions, supports 4.

**Brad Sherman** (Democrat, CA)

- **regulation** (Sonnet 3.0 → reviewer 2; bad citations s31, s37, s36, s20, s27): These citations establish research funding, publicly funded evaluation, creators' rights, and a general preference for transparency—not substantial requirements imposed on AI companies. Although s35 clearly favors regulation and international agreements, their unspecified content does not establish the company obligations or broad regulatory framework needed to move beyond 2.

**Christopher A. Coons** (Democrat, DE)

- **agi_pilled** (bad citations s114, s115): Statements s73, s69, and s86 support transformative AI, but not a near-to-medium-term expectation of AGI or superintelligence. Statements s114 and s115 concern international risk reduction and slowing development, rather than establishing an AGI expectation or the scale of transformation.
- **china_race** (Sonnet 3.0 → reviewer 2): The cited statements genuinely support strong race framing, but the full record balances competition with extensive domestic safety concerns and explicit criticism of racing. His calls for cooperation in s114–s116 and the explicit balance in s119 make competition a recurring theme rather than the primary lens overall.

**Christopher R. Deluzio** (Democrat, PA)

- **agi_pilled** (bad citations s22): S18 and s23 treat superintelligence as a real possibility requiring urgent action, but provide no explicit arrival timeline. S22 reports what Americans are hearing and does not itself establish an expectation of AGI or superintelligence.
- **x_risk** (bad citations s20, s22): S18's emergency framing and s23's proposed ban on superintelligence beyond human control establish catastrophic risk as a major priority. S20 ambiguously uses existential language about workers and education, while s22 attributes the extinction possibility to what people are hearing rather than directly asserting it.
- **china_race** (bad citations s2, s21): S24 explicitly calls for bringing China into international action, fitting the cooperation criterion for 0. S2 concerns defense companies' ethical restrictions, and s21 mentions unnamed adversaries; neither establishes a position on cooperation or competition with China.

**Denise Powell** (Democratic, NE)

- **agi_pilled** (Sonnet insufficient_evidence → reviewer 1; bad citations s2): Across several substantive AI statements, she discusses ordinary benefits, employment effects, and oversight without suggesting radical transformation. The rubric permits 1 on that basis; s2 supports ordinary economic impacts rather than requiring insufficient evidence.
- **x_risk** (Sonnet insufficient_evidence → reviewer 1; bad citations s2): She discusses concrete ordinary harms, particularly job displacement, without catastrophic framing, satisfying level 1. The kill-switch proposal alone does not establish concern about loss of control or existential risk.
- **summary**: The summary slightly overstates s3: she mentions an aging grid and rising energy costs, but does not explicitly identify AI-related grid strain or connect those costs to AI.

**Erin Houchin** (Republican, IN)

- **x_risk** (Sonnet 1.0 → reviewer 3; bad citations s16): In s16, she explicitly treats an advanced AI system escaping its testing environment and accessing unauthorized systems as a real concern, which supports the rubric's loss-of-control category. Framing the response as transparency does not make the underlying concern an ordinary harm; she does not, however, establish extinction risk as a major priority.

**George Whitesides** (Democrat, CA)

- **china_race** (Sonnet 2.0 → reviewer 1; bad citations s22): China appears explicitly only in s35, with broader adversary competition in s9 and s15; race framing remains marginal across this extensive record. In s22, the competitive dynamic concerns AI companies, not competition with China.

**Greg Casar** (Democrat, TX)

- **ai_overall** (bad citations s26): The overwhelmingly harm-focused statements support 0. However, s26 describes technological transformation and calls for broadly shared benefits; it does not itself support a very concerned overall assessment.
- **agi_pilled** (bad citations s77): His repeated emergency framing and efforts to ban superintelligence make it central to his AI agenda, supporting 4. But s77 only explains recursive self-improvement; by itself, it does not establish that he expects it imminently or regards AGI as central.

**Jennifer L. McClellan** (Democrat, VA)

- **agi_pilled** (bad citations s20, s13, s32, s21): Her endorsement of near-term extinction warnings in s33, reinforced by her own humanity-ending warning in s36, supports treating radically powerful AI as a real planning concern. However, s20, s13 and s21 establish transformation or disruption rather than AGI, while s32 describes autonomous misconduct without establishing human-level or superintelligent capabilities.
- **x_risk** (bad citations s30, s32): Her explicit existential framing, nuclear comparison and demand for oversight before AI ends humanity support level 4. Individually, s30 and s32 support loss-of-control concerns at level 3 rather than establishing existential risk as a major priority.
- **regulation** (bad citations s40): Her own demands for federal oversight, regulatory authority and guardrails support level 3, without a sufficiently specified comprehensive regulatory regime for level 4. In s40, the explicit call for frontier-model oversight is attributed to company CEOs; her criticism of congressional inaction signals sympathy but does not independently specify her proposed rules.

**Kevin Kiley** (Independent, CA)

- **agi_pilled** (Sonnet 4.0 → reviewer 3; bad citations s13, s20, s28, s19, s23, s1): These citations establish transformative expectations and AGI as a possibility worth urgently preparing for, but not the explicit short timelines or AGI-centered civilizational framing needed for 4. In particular, s20 describes the labs' goal, and s28 attributes the sooner-than-expected arrival claim to a witness.
- **x_risk** (bad citations s34): Statements s13 and s35 directly establish concern about misaligned behavior and loss of human control. Statement s34 concerns potentially disastrous international arms races, not specifically loss of control or existential risk.
- **china_race** (Sonnet 2.0 → reviewer 0; bad citations s21, s34, s38): The clearest policy position rejects dangerous arms races and favors international collaboration, supporting 0 despite concern about America's advantage in s2. Statement s21 invokes China to illustrate the difficulty of slowing progress, while s34 and s38 support cooperation rather than recurring competition with China.

**Michael K. Simpson** (Republican, ID)

- **regulation** (Sonnet 2.0 → reviewer insufficient_evidence; bad citations s2): S2 supports targeted regulation of data centers' local energy-cost impacts, not explicitly regulation of AI. Without an explicit AI connection or rules governing AI systems or companies as such, assigning an AI-regulation score stretches the evidence.
- **summary**: The summary accurately describes the project announcement and support for data center safeguards, but saying both statements concern AI infrastructure overstates s2: it discusses data centers without explicitly connecting them to AI.

**Michael R. Turner** (Republican, OH)

- **agi_pilled** (Sonnet 2 → reviewer 1; bad citations s1, s4): Calling AI important for analytical assistance does not establish transformative expectations, and the generic statement about AI and quantum jointly reshaping the world falls short of an internet- or industrial-revolution-scale claim. Across several statements, he discusses practical capabilities and geopolitical applications without clearly anticipating radical technological change.

**Mike Levin** (Democrat, CA)

- **x_risk** (bad citations s16): s17 directly supports level 3 by endorsing concern about catastrophic loss of control. s16 demands regulation but does not identify catastrophic or existential risk.
- **china_race** (bad citations s9): China barely features across substantial AI discussion, and s8 concerns chip diversion rather than a dominant race framing. s9's global energy race is not evidence about an AI race with China.

**Mike Quigley** (Democrat, IL)

- **agi_pilled** (Sonnet 2 → reviewer 1; bad citations s4, s3): Rapid advancement, lethal potential, and possible loss of control do not establish an expectation of economy- or society-wide transformation. Across several substantive statements, he does not explicitly anticipate AGI or describe radical societal change.
- **regulation** (Sonnet 4.0 → reviewer 3; bad citations s5, s6, s4, s3): These statements support substantial oversight, including third-party audits, independent inspectors, and kill-switch requirements. They do not establish comprehensive regulation, frontier-model licensing, a new regulatory agency, or a pause; a congressional select committee is not a regulatory agency.

**Nancy Mace** (Republican, SC)

- **agi_pilled** (bad citations s113, s114, s165): Her own framing of a 'race to singularity' in s156 supports treating AGI as a real possibility. However, s113 and s114 report others' timelines without adopting them, and s165's nuclear-weapon analogy concerns geopolitical competition rather than AGI.
- **x_risk** (Sonnet 0.0 → reviewer 2; bad citations s166, s168, s161, s41, s7, s160): These citations do not explicitly reject catastrophic or existential risk: s166 leaves the referent of 'hoax' unspecified, the company-warning comments challenge motives, and s41 concerns existing prohibitions rather than clearly denying capability. Her explicit concerns about AI-fueled cyberattacks threatening national security and critical infrastructure in s42 support 2, while her existential-risk questions do not establish an endorsed loss-of-control concern.
- **summary**: Most of the summary is supported, but saying she calls AI-safety warnings a 'hoax' overstates s166: the supplied excerpt does not identify what 'it' refers to. She does explicitly question the sincerity of companies' safety warnings and their motives for seeking intervention.

**Nancy Pelosi** (Democrat, CA)

- **agi_pilled** (Sonnet 2.0 → reviewer 1; bad citations s10): Calling AI a transformative technology that will shape America's future does not clearly establish societal transformation on the scale required for level 2. Across several statements, she discusses innovation, policy, and specific harms without articulating radical change or AGI expectations.
- **x_risk** (Sonnet insufficient_evidence → reviewer 1; bad citations s4, s9): These citations identify ordinary harms involving consumers, data, intellectual property, and impersonation, supporting level 1 rather than insufficient evidence. The rubric does not require an extended discussion of risks, and none of the statements introduces catastrophic risk.

**Rashida Tlaib** (Democrat, MI)

- **x_risk** (Sonnet 1.0 → reviewer 3; bad citations s17): In s17 she affirmatively states that AI is advancing faster than its creators can responsibly control, acknowledging a real control concern consistent with level 3. Explicit extinction language is not required at that level; her other cited concerns support ordinary-harms framing.
- **china_race** (Sonnet insufficient_evidence → reviewer 1): The rubric assigns level 1 when AI receives substantive discussion but China competition barely features. This extensive set of substantive AI statements contains no China-race framing.

**Rebecca Cooke** (Democratic, WI)

- **agi_pilled** (Sonnet insufficient_evidence → reviewer 1; bad citations s2, s16): The rubric explicitly assigns 1 when several AI statements concern ordinary technology without suggesting radical transformation. The cited statements fit that pattern, reinforced by her repeated discussion of deepfakes and infrastructure impacts.
- **china_race** (Sonnet insufficient_evidence → reviewer 1): The rubric permits 1 when AI is discussed substantively and race framing barely features. These numerous substantive statements contain no China or race framing, satisfying that criterion.
- **regulation** (Sonnet 2.0 → reviewer 4; bad citations s9, s8): Her proposed federal moratorium on all new data-center construction is a broad mandatory infrastructure pause, not merely targeted deepfake or transparency regulation. Under the rubric's explicit inclusion of pauses at level 4, these citations support a stronger score, although she does not propose pausing AI development itself.

**Ro Khanna** (Democrat, CA)

- **ai_overall** (Sonnet 2.0 → reviewer 1): The citations establish genuine appreciation of AI's benefits, but the full record is predominantly concerned with displacement, inequality, corporate power and eventually extinction. Acknowledging benefits does not make promise and risk roughly equal in his overall presentation.
- **agi_pilled** (bad citations s21, s255, s244): His warnings about recursive self-improvement and loss of control support treating advanced AI as a real possibility, without establishing an explicit AGI timeline. However, s21 reports someone else's timeline and asks a question; s255 and s244 establish catastrophic-risk concern rather than an expectation of AGI or human-level AI.
- **china_race** (bad citations s246, s242, s106): Competition with China recurs substantively, supporting 2 rather than minimal race framing. The three flagged statements support cooperation, rubric level 0; they show an important countercurrent but do not establish that competitive framing barely features.

**Sam Forstag** (Democratic, MT)

- **x_risk** (bad citations s14): His own repeated descriptions of extinction risk as the country's biggest threat clearly support 4. However, s14 reports a CEO's and researcher's warnings rather than independently stating his own assessment.
- **china_race** (Sonnet insufficient_evidence → reviewer 1): The rubric permits 1 when AI is discussed substantively and race framing barely features. These numerous substantive statements contain no China or race framing, meeting that criterion.
- **regulation** (Sonnet 4.0 → reviewer 3; bad citations s22, s21, s1, s2, s15): These statements support substantial mandatory safeguards, including kill switches, independent safety verification, and infrastructure conditions. They establish level 3, but not an explicit comprehensive regulatory framework, frontier licensing regime, new agency, or pause sufficient for level 4.

**Scott H. Peters** (Democrat, CA)

- **agi_pilled** (Sonnet insufficient_evidence → reviewer 1): The rubric explicitly assigns 1 when several AI statements discuss ordinary applications and policy without suggesting radical transformation. Across these statements, that condition is met; the absence of AGI language does not require insufficient_evidence.
- **china_race** (Sonnet 2.0 → reviewer 1; bad citations s1, s2): Statements s1 and s2 concern Chinese hacking and insecure data handling, not competition for AI leadership. Only s10 explicitly invokes an innovation race involving AI, making race framing a minor rather than recurring theme.

**Scott Wiener** (Democratic, CA)

- **agi_pilled** (bad citations s1, s2, s126): S1 and s2 report others' views, and s126 establishes transformative importance rather than an expectation of AGI. His own warnings about runaway AI and responses to superhuman intelligence nevertheless support 3; the justification also overlooks the explicit timeline in the quoted material in s2.
- **china_race** (bad citations s95): S117 directly supports cooperation with China, making 0 appropriate. S95 instead criticizes chip sales as undermining U.S. dominance; it does not support rejecting race framing, while s3 and s115 concern an industry arms race rather than specifically China.

**Shelley Moore Capito** (Republican, WV)

- **ai_overall** (bad citations s10): Her own statements emphasize benefits while recognizing manageable harms, supporting 3. However, s10 presents a department's account of its policies and guidance, not clearly Capito's own assessment of AI.
- **agi_pilled** (bad citations s1, s14): The unprecedented-change and internet comparison in s13 supports 2 without establishing AGI expectations. S1 establishes strategic competition rather than economy-wide transformation, while s14 attributes the central cannot-slow-down argument to the president.
- **china_race** (bad citations s14): S1, s4, and s9 establish a strong international-race framing, including explicit competition with China. The stronger claim in s14 that slowing down means losing is explicitly presented as the president's position, so it should not independently establish hers.
- **regulation** (bad citations s17, s14): Her support for anti-fraud legislation and child and privacy safeguards supports targeted regulation, alongside voluntary guidelines. S17 reports CEOs' request for a regulatory floor without explicitly endorsing that framework, and s14 neither establishes her regulatory position nor supplies her own argument against constraints.
- **summary**: The overall characterization is largely supported, but saying she supports a bipartisan look at a regulatory floor overstates s17: the floor is requested by CEOs, while her own commitment is to bipartisan attention to benefits and dangers.

**Sherrod Brown** (Democratic, OH)

- **agi_pilled** (bad citations s3, s9): S2's explicit warning about a major transformation of the economy supports 2. Calling AI a tool in s3 and the next step in s9 does not independently substantiate transformative expectations.
- **china_race** (Sonnet insufficient_evidence → reviewer 1): The rubric permits 1 when substantive AI discussion is present but race framing barely features. These statements discuss AI substantively without invoking China or an AI race.

**Stephen F. Lynch** (Democrat, MA)

- **x_risk** (Sonnet 4.0 → reviewer 3; bad citations s37, s40, s41, s39): These statements clearly establish concern about loss of control and potential existential harm, supporting level 3. They do not clearly establish existential-risk mitigation as a top-tier priority; frightening language and references to humanity's existence alone do not establish level 4.

**Valerie P. Foushee** (Democrat, NC)

- **x_risk** (bad citations s120): In s120, the harder-to-control concern is attributed to researchers; her explicit position concerns whistleblower treatment and company accountability, not acceptance of catastrophic loss of control. Her own risk framing remains predominantly concrete harms, while s7 treats existential risks as speculative but legitimate research subjects rather than explicitly dismissing them.

**William Lawrence** (Democratic, MI)

- **agi_pilled** (bad citations s1, s6, s9): Calling AI a 'mass unemployment machine' in s5 supports expectations of major economic transformation, though only narrowly. Increasing capabilities, reported extinction warnings, and a proposed development pause do not themselves establish expectations of transformative or human-level AI.
- **x_risk** (bad citations s5): The extinction warning in s5 is attributed to experts rather than independently endorsed there. However, s6 explicitly judges even a 1% extinction probability unacceptable, and the advanced-AI pause in s9 supports treating this as a major policy priority.
- **china_race** (Sonnet insufficient_evidence → reviewer 1): The rubric permits 1 when substantive AI discussion contains little race framing. These statements discuss AI extensively without mentioning China or competition, satisfying that condition.

**William R. Timmons IV** (Republican, SC)

- **agi_pilled** (bad citations s23): The explicit description of an AI-driven technological revolution in s6 supports 2. Calling AI 'the way of the future' in s23 does not independently establish transformative expectations.
- **china_race** (Sonnet 2.5 → reviewer 1; bad citations s24, s23, s5, s14): China appears explicitly only in s18, fitting the rubric's minimal category rather than a recurring or primary China-race lens. The other citations concern generic international competitiveness, relocation, or warfare involving Russia and Ukraine, not competition with China.
- **summary**: The summary accurately describes his opportunity-oriented outlook, federal-preemption emphasis, and lack of explicit AGI or existential-risk discussion. However, it overstates China's role by describing the recurring federal-framework argument as aimed at staying ahead of China; most statements instead invoke general innovation, compliance costs, and international competitiveness.

**Yassamin Ansari** (Democrat, AZ)

- **ai_overall** (bad citations s2): The overwhelmingly threat-focused statements support 0 overall. However, s2 supports a more balanced or optimistic position, not 0; it is evidence of her earlier stance rather than direct support for this score.
