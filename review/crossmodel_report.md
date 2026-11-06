# Cross-model review (reviewer: openai/gpt-6.1-sol)

The reviewer is a different model family from the scorer (Claude Sonnet 5.5). It does two things: (1) **blind re-scoring** of everyone from the same evidence and rubric, and (2) an **audit**: it sees Sonnet's scores and cited quotes for the review packet, plus everyone whose blind score differs by ≥2, and checks them.

## 1. Blind agreement (all scored people)

| dimension | n (both scored) | exact | within 1 | Spearman ρ | Sonnet mean | reviewer mean | only one says insufficient |
|---|---|---|---|---|---|---|---|
| ai_overall | 577 | 78% | 100% | 0.89 | 2.10 | 1.90 | 20 |
| agi_pilled | 304 | 66% | 100% | 0.66 | 2.12 | 1.86 | 77 |
| x_risk | 483 | 80% | 98% | 0.84 | 1.83 | 1.72 | 98 |
| china_race | 402 | 78% | 98% | 0.90 | 2.14 | 1.93 | 25 |
| regulation | 549 | 80% | 99% | 0.86 | 2.37 | 2.34 | 25 |

"Exact" means within 0.5, because Sonnet's score is an average of two runs.

## 2. Audit

49 people, 245 person-dimensions. The reviewer disagreed on **45** (18%), flagged citations as not supporting the score on **175**, and flagged **8** summaries.

### Disagreements and citation problems

**Abdul El-Sayed** (Democratic, MI)

- **agi_pilled** (bad citations s12, s26, s30, s23): S16 supports a world-shaping, transformative view. The other citations do not establish that scale: s30 attributes the numerical forecast to someone else, while warnings about unexpected capabilities or loss of control do not themselves establish expectations of AGI.
- **x_risk** (bad citations s23, s37): S28 and s25 explicitly establish existential risk as a major priority. S23 establishes loss-of-control concern at level 3, while s37 establishes catastrophic nuclear and biological risks without independently establishing level-4 prioritization.
- **china_race** (Sonnet 1.0 → reviewer 0; bad citations s23): S23 criticizes race framing as a rationale for creating dangerously uncontrolled AI, supporting level 0. Its substantive criticism matters more than the fact that China appears only once.
- **regulation** (bad citations s36, s15, s33): The explicit frontier-research pause in s34 directly supports level 4. Generic demands for regulation or public oversight, and the existence of an unspecified 22-proposal plan, do not independently establish that level.

**Adam B. Schiff** (Democrat, CA)

- **ai_overall** (bad citations s59, s42): His explicit overall assessments acknowledge both substantial promise and risks, supporting 2. However, s59 and s42 are risk-only statements and do not themselves support the balanced level.
- **agi_pilled** (bad citations s53, s30, s15): S51 explicitly treats approaching AGI as real, while s52 connects the reported warning to his own demand for urgent safeguards. S30 and s15 support transformative impact rather than AGI, and s53 does not specifically establish AGI or human-level AI expectations.
- **x_risk** (bad citations s40, s1): His adopted existential-risk concerns and warning about rogue agents support 3, without clearly establishing existential risk as a top-tier priority. S40 addresses human authorization of military force, and s1 supports safety oversight; neither directly establishes advanced-AI loss of control or existential risk.
- **china_race** (bad citations s33, s43): S44 and s53 establish recurring competition concerns balanced with safety cooperation. S33 uses others' fears about China to attack alleged corruption without clearly adopting those fears, while s43 primarily concerns corruption and does not establish recurring China-race framing.
- **regulation** (bad citations s52, s31, s53, s32): S1 and s59 directly support substantial mandatory oversight, but the evidence does not clearly specify a comprehensive regulatory regime warranting 4. The other cited statements support unspecified safeguards, opposition to preemption, or international coordination rather than level-3 company obligations; 'liability-style rules' is also not established.

**Adam Smith** (Democrat, WA)

- **ai_overall** (bad citations s5): Praise for AI applications and local innovation, alongside chatbot and military-capability concerns, supports a mixed assessment. However, s5 merely reports discussing an AI Medicaid pilot; it expresses neither criticism nor concern.
- **x_risk** (Sonnet insufficient_evidence → reviewer 1): In s9, he explicitly raises chatbot mental-health risks, which is sufficient for level 1. The military-capability misunderstanding concern in s6 does not explicitly establish catastrophic risk.
- **regulation** (bad citations s2): S9 directly supports targeted chatbot mental-health guardrails. S2 asks about policymaking agility across several technologies but does not endorse specific AI rules or establish a regulatory level.
- **summary**: The summary incorrectly attributes concern about AI Medicaid preauthorization to Smith: s5 only identifies it as a meeting topic. The remaining characterization is broadly supported.

**Ami Bera** (Democrat, CA)

- **ai_overall** (bad citations s1, s12, s13): The balanced assessments in s6 and s18 support 2. Under the rubric's level-specific citation rule, s1 and s12 express benefits without balancing risks, while s13 expresses concern and urgency without balancing benefits.
- **agi_pilled** (Sonnet 2.0 → reviewer 1; bad citations s3, s18, s13): Rapid transformation of one sector in s3 establishes an expected impact, but not economy-and-society-wide transformation comparable to the internet or industrial revolution. Neither speed and safeguards in s13 nor the vague autonomy concern in s18 establishes level 2.
- **x_risk** (Sonnet 3.0 → reviewer 2; bad citations s18, s17, s14): S17 supports serious national-security risk and crisis escalation, warranting 2 rather than 3. Worry about AI 'thinking on its own' does not clearly acknowledge loss of human control, and s14 leaves the safety risks unspecified.
- **china_race** (bad citations s4, s17, s14): S7 and s11 establish recurring concern about preserving a technological edge over China without making the race overriding. S4 provides only general international competitiveness, while s14 and s17 directly support the rubric's cooperation category rather than level-2 race framing.
- **regulation** (Sonnet 3.0 → reviewer 2; bad citations s10, s8, s13, s18, s11, s6): Congressional approval of chip exports supports targeted controls, while the other citations call for unspecified safeguards, oversight, or an undefined framework. None establishes substantial company obligations such as liability, audits, or frontier-model safety testing required for level 3.

**Andrew Ogles** (Republican, TN)

- **ai_overall** (bad citations s23, s37, s38): The huge upside in s12 and enthusiasm in s30 support mostly optimistic. However, s23 expresses a threat concern, while s37 and s38 attack regulatory motives or doomsday narratives rather than directly establish his overall assessment of AI.
- **agi_pilled** (bad citations s9): Statements s12 and s15 support unusually transformative expectations without an adopted expectation of AGI. Statement s9 describes broad financial-sector applications, but does not itself establish transformation at the rubric's level 2.
- **x_risk** (bad citations s38, s30): Infrastructure destruction and economy-wide cyber exploitation support serious misuse risk, without an explicit endorsement of existential loss of control. Statement s38 instead supports level 0, while s30's unspecified autonomous cyber incident does not itself establish catastrophic scale.
- **china_race** (bad citations s35, s25, s31, s27): Statements s34 and s36 explicitly use competition with China to oppose slowing or constraining innovation, supporting level 4. The other cited statements establish strong race framing, but do not themselves show competition overriding constraints.
- **regulation** (bad citations s12, s29): His explicit warnings against congressional overreaction and slowing innovation support a light-touch stance, although s16 shows substantial countervailing support for restrictions. Statement s12 calls for guardrails without establishing a preference for minimal regulation, and s29 proposes a cyber task force rather than AI regulation.

**Andy Harris** (Republican, MD)

- **ai_overall** (Sonnet 1.0 → reviewer 0; bad citations s4): The statements present AI predominantly as a source of harm, without acknowledging benefits. The extinction warning in s4 supports the rubric's threat-centered level 0; level 0 does not require a sweeping condemnation of every AI use.
- **agi_pilled** (bad citations s6): Statements s4–s5 treat superintelligence as a real possibility requiring action, supporting level 3. Statement s6 describes rapid technological progress but does not itself establish expectations about AGI or superintelligence.
- **regulation** (bad citations s6, s3, s4): Statement s7 directly supports level 3 through company liability. Statement s3 supports targeted surveillance safeguards, while s6 concerns legislative capacity and s4 describes risk; neither of the latter establishes a regulatory position.

**Bernard Sanders** (Independent, VT)

- **agi_pilled** (bad citations s161, s182, s1, s86): The full record supports 4 because superintelligence becomes central to his policy agenda, including a proposed permanent ban. However, s161 reports scientists' expectations rather than clearly adopting them, s182 and s1 establish transformation without AGI (level 2), and s86 establishes superintelligence as a plausible possibility (level 3).
- **x_risk** (bad citations s86): His nuclear-weapons comparisons and demands for urgent international action support 4, reinforced by s136, s199 and s214. Taken alone, s86 establishes personal concern about existential risk, which supports level 3 rather than its elevation to a top-tier priority.
- **regulation** (bad citations s253): The proposed pauses, permanent superintelligence ban and data-center moratorium clearly support 4. However, s253 calls for product safety regulation without specifying a comprehensive framework or pause, so it supports a lower regulatory level.

**Betty McCollum** (Democrat, MN)

- **ai_overall** (bad citations s1, s5): Her overall emphasis on threats, bans, and a development pause supports mostly concerned. However, s1 and s5 individually balance substantial benefits against harms rather than directly supporting that level.
- **agi_pilled** (bad citations s5, s7): S6 directly treats superintelligence as a real possibility requiring action, supporting 3. S5 supports transformative AI at level 2, while s7 does not itself establish an expectation of AGI or superintelligence.
- **x_risk** (bad citations s5): Her explicit existential-threat warning and proposed superintelligence ban, reinforced by the development-pause demand, support treating the risk as a major priority. S5 mentions risks to humanity but does not explicitly establish existential risk or its priority.
- **regulation** (bad citations s8, s5): S6 and s7 directly support level 4 through a superintelligence ban and a pause pending strong federal regulation. S5 and s8 support accountability and safeguards, but do not themselves establish comprehensive regulation or a pause.

**Bill Hagerty** (Republican, TN)

- **ai_overall** (bad citations s5, s14): The overall record is predominantly optimistic while acknowledging manageable harms. Individually, s5 expresses a mixed position and s14 addresses harm to artists; neither directly supports level 3.
- **agi_pilled** (Sonnet 2.0 → reviewer 3; bad citations s38): In s38, he goes beyond reporting conversations by expressing his own priorities for responsibly supplying power to superintelligence, treating it as a practical planning possibility. This supports level 3 rather than the cited level 2, without making AGI central or specifying imminent timelines.
- **x_risk** (Sonnet 2.0 → reviewer 1; bad citations s12, s33, s35, s14): S12 raises potentially malign biological-data uses but does not identify bioweapons or catastrophic-scale consequences; s33 and s35 concern IP theft and security without catastrophic framing. S14 concerns ordinary reputational and livelihood harms, so the cited evidence does not establish level 2.
- **regulation** (Sonnet 1.0 → reviewer 2; bad citations s28, s13): He repeatedly supports concrete protections involving copyright, transparency, and ratepayer costs, while opposing overly restrictive regulation, making targeted regulation the best overall fit. S13 supports mandatory targeted requirements rather than level 1, while s28's explicit liability position points toward stronger regulation.

**Brad Sherman** (Democrat, CA)

- **agi_pilled** (bad citations s28, s27, s26): The successor-species framing in s4, nuclear comparison in s2, and overriding legislative priority in s31 support 4. However, s28 establishes superintelligence as a possibility without the level-4 urgency or civilizational comparison, while s27 and s26 do not directly establish level-4 AGI expectations.
- **x_risk** (bad citations s26): His apocalypse language, explicit existential warnings, and designation of control research as his most important legislation support 4. Although s26 expresses his own control concerns, recommending a book with an extinction-themed title does not itself establish that extinction prevention is his top-tier priority.
- **china_race** (bad citations s32): Competition with China recurs, especially in s25–s26, but remains balanced against safety concerns. S32 explicitly substitutes international cooperation for race framing and therefore directly supports level 0 rather than level 2.
- **regulation** (Sonnet 3.0 → reviewer 2; bad citations s35, s34, s37, s20, s36, s31): The evidence supports targeted safety, transparency, and creators' rights measures, but does not establish substantial regulatory obligations on AI companies. S35 leaves regulatory scope unspecified; research funding, government evaluation, and general endorsements of transparency or compensation do not themselves establish level-3 mandates.

**Chris Van Hollen** (Democrat, MD)

- **x_risk** (bad citations s29, s31): His own statements about humanity's future being on the line and the urgent need to prevent global catastrophic harm support 4. However, s29 describes containment failures without establishing existential stakes, and s31 calls for slowing development without identifying existential risk as the reason.
- **regulation** (bad citations s38, s6, s39): Calls to pump the brakes on frontier development and withdraw an unsafe model support 4. Liability in s38 and mandatory safety testing in s39 support 3, while opposition to state-law preemption in s6 does not itself establish support for comprehensive regulation or pauses.

**Christopher A. Coons** (Democrat, DE)

- **ai_overall** (bad citations s68): His explicit assessments consistently balance substantial benefits and risks. S68 establishes a healthcare benefit with a safety qualification, but does not itself establish the roughly equal promise-and-risk assessment required for level 2.
- **agi_pilled** (bad citations s115, s112): S73 and s69 directly establish society-wide, century-defining transformation without an explicit expectation of AGI. S115 concerns slowing development, while s112 establishes loss-of-control and species-level risk rather than an expectation of AGI or a particular scale of socioeconomic transformation.
- **x_risk** (bad citations s111, s115, s116): S110 explicitly makes existential risk a top-agenda priority, and s114 invokes nuclear arms control and humanity's destruction. S111 acknowledges existential risk without establishing its priority, while s115 and s116 advocate guardrails and cooperation without independently establishing level-4 existential-risk prioritization.
- **china_race** (bad citations s116, s114): His repeated century-defining race language, chip restrictions, and demands for U.S. dominance support level 3, though not the overriding priority required for level 4. S116 and s114 specifically support level 0's criticism of racing and cooperation with China; they are countervailing evidence rather than direct support for the assigned race level.
- **regulation** (bad citations s111): Independent model oversight, company transparency, and research and whistleblower protections support substantial regulation beyond targeted deepfake rules. S111 calls for meaningful guardrails but supplies no regulatory substance sufficient to distinguish level 3 from other pro-regulatory levels.

**Christopher Murphy** (Democrat, CT)

- **ai_overall** (bad citations s25): His acknowledged benefits are outweighed by repeated warnings about economic and cultural harm. However, s25 describes benefits alone and does not itself support the mostly-concerned level.
- **agi_pilled** (bad citations s35): In s45, reaching AGI is a real prospect relevant to current policy choices, supporting 3; his other transformative-impact statements establish at least 2. Rejecting omnipotent, murderous AI in s35 does not establish whether he expects AGI.
- **x_risk** (bad citations s105, s75, s114): Statements s111 and s113 directly establish concern about losing human control. The unspecified destruction language in s75 and s105 does not independently establish that level, while s114 concerns cyberattacks and accountability rather than loss of control.
- **china_race** (Sonnet 1.0 → reviewer 2; bad citations s45, s106, s40, s94, s111, s67): China competition is recurring and explicit, including wanting to win the race and opposing chip exports, but is balanced by regulation and cooperation. None of these citations supports the assigned minimal level: they show substantive competition, rejection of anti-regulatory race arguments, or cooperation.
- **regulation** (bad citations s51, s113, s75, s110): His proposed overarching regulatory control of AI companies' power in s98 and broad regulatory regime in s86 support 4. Safety standards and liability in s51 and s113 support 3, s110 advocates targeted initial measures, and s75 establishes urgency without specifying comprehensive regulation.

**Christopher R. Deluzio** (Democrat, PA)

- **ai_overall** (bad citations s22): His acknowledgment of AI's potential is outweighed by his own repeated warnings about harms. However, s22 reports what Americans are hearing while attacking Republican leadership; it does not clearly adopt the reported claims.
- **agi_pilled** (bad citations s22, s19): Statements s18 and s23 treat superintelligence as a real possibility requiring action, but provide no explicit timeline or clear civilizational-turning-point comparison. Statement s19 addresses safety without establishing transformative capabilities, and s22 reports others' concerns.
- **x_risk** (bad citations s22, s20): Calling superintelligence a humanity-threatening emergency and supporting its prohibition because humans might be unable to stop it jointly support a top-priority rating. Statement s22 reports others' fears, while s20's ambiguous existential language does not independently establish level-4 catastrophic-risk prioritization.
- **china_race** (bad citations s21, s19, s18): Statement s24 supports cooperation by explicitly calling for bringing China to the table. Statement s21 concerns adversaries' military applications rather than cooperation or rejection of race framing, and s19 and s18 do not directly address China or an AI race.
- **regulation** (bad citations s22, s24, s14): The superintelligence ban and calls to pump the brakes support level 4. Statement s22 demands unspecified safety legislation, s24 advocates local consent and international leadership, and s14 supports targeted workplace rules; these do not themselves establish level-4 regulation.

**Claire Valdez** (Democratic, NY)

- **agi_pilled** (Sonnet insufficient_evidence → reviewer 2): In s3, she describes AI as embedded in the bedrock of daily life and warns that CEOs will reshape the entire economy through it. That addresses economy-wide transformation, supporting 2 without implying belief in AGI.
- **regulation** (bad citations s3): The explicit conditional moratorium in s4 and s5 supports 4 under the rubric's inclusion of pauses. However, s3's general accountability pledge does not independently establish substantial or comprehensive regulatory requirements.

**Dan Crenshaw** (Republican, TX)

- **ai_overall** (bad citations s11): His substantive statements predominantly favor AI development while acknowledging manageable risks. However, s11 balances protection and innovation without establishing a mostly optimistic outlook.
- **agi_pilled** (bad citations s18, s9): S26 and s31 support a major, lasting technological transformation. S18 describes rapid evolution without specifying transformative scale, while s9 promotes a healthcare discussion rather than expressing an economy- or society-wide transformation.
- **x_risk** (bad citations s31): S28 directly connects ChatGPT-enabled attacks on critical infrastructure to catastrophic security failures, supporting serious misuse risk. S31 acknowledges unspecified risks but does not support catastrophic-risk level 2.
- **china_race** (Sonnet 4.0 → reviewer 3; bad citations s17, s25, s19): China competition is a primary policy lens, but s31 explicitly rejects ignoring risks and requires developers to cover infrastructure costs, making 3 better supported than an overriding-race score of 4. S17 and s25 establish strong competition framing, and s19 mentions competition incidentally; none independently establishes level 4.
- **regulation** (bad citations s22): S3 directly endorses voluntary frameworks over prescriptive regulation, consistent with his later preference for streamlined development and limited requirements. S22 opposes banning AI, which does not itself establish opposition to ordinary regulation or a light-touch regulatory preference.

**Erin Houchin** (Republican, IN)

- **agi_pilled** (Sonnet insufficient_evidence → reviewer 1): Statement s6 addresses AI's lasting impact: it is 'here to stay' and will shape children's future. That supports the ordinary-technology level without establishing radical transformation or AGI expectations.
- **x_risk** (Sonnet 1 → reviewer 3; bad citations s16): In s16, she adopts an advanced system's escape from its testing environment and unauthorized access as a reason for developer accountability. This acknowledges a concrete loss-of-control concern, supporting level 3 rather than ordinary harms only; it does not establish extinction risk as a major priority.
- **china_race** (bad citations s15): Statements s14 and s16 establish recurring international competition balanced with safeguards. Statement s15 discusses companies' ability to compete without identifying China or international competition, so it does not independently support this dimension.
- **regulation** (Sonnet 2.0 → reviewer 3; bad citations s14, s16): Statement s16 extends her position beyond targeted child-safety rules to transparency and accountability requirements for the largest AI developers, supporting level 3. Statement s14 advocates a national development standard and rejects state patchworks rather than directly supporting the cited level-2 targeted protections.

**Gabe Vasquez** (Democrat, NM)

- **ai_overall** (bad citations s2, s5): His warnings about superintelligence dominate the limited positive acknowledgment of AI research. However, s2 and s5 concern particular data-center proposals and practices without explicitly connecting them to AI, so they do not directly establish his overall AI outlook.
- **x_risk** (Sonnet 3.0 → reviewer 1; bad citations s4, s6): Calling unguarded superintelligence development a 'great risk' does not explicitly acknowledge loss of control or existential risk. He expresses risk concerns, but none of the statements identifies a catastrophic mechanism or outcome sufficient for levels 2–4.

**Gary C. Peters** (Democrat, MI)

- **ai_overall** (bad citations s9): His statements collectively balance substantial benefits with serious risks. However, s9 describes harms alone and does not directly support the balanced level.
- **agi_pilled** (bad citations s17): His descriptions of society-wide transformation and effects on foundational human capacities support 2, without an adopted expectation of AGI. In s17, the unspecified referent of 'this' makes the timeline unusable as evidence of transformative AI.
- **x_risk** (bad citations s8, s67, s3, s59): S30 directly establishes serious misuse risk through AI-enabled bioweapons. The other cited statements mention cybersecurity or national-security risks without specifying the large-scale or catastrophic consequences required for level 2.
- **china_race** (bad citations s59): Countering China and maintaining U.S. AI leadership recur alongside responsible-development concerns, supporting 2. S59 concerns security against foreign-adversary technology, not competition or winning an AI race.
- **regulation** (Sonnet 3.0 → reviewer 4; bad citations s69, s22, s29, s60): S69 explicitly calls for slowing AI development until guardrails exist, meeting the rubric's pause criterion for 4 rather than 3. S22 and s29 establish narrower transparency and administrative measures, while s60 merely asks who will judge state laws.

**George Whitesides** (Democrat, CA)

- **ai_overall** (bad citations s4, s35, s6): His statements overall acknowledge benefits but emphasize harms and the need to slow development. However, s4, s35, and s6 individually express a balanced promise-and-guardrails position rather than a predominantly concerned outlook.
- **agi_pilled** (bad citations s26, s35): S2 and s37 explicitly treat superintelligence as something policymakers must address, supporting 3 without an imminent timeline. S26 discusses accelerated AI research without directly establishing an expectation of AGI, while s35 supports transformative applications rather than human-level or superintelligent AI.
- **x_risk** (bad citations s26, s31, s18, s23): His proposed global stand-down to establish existential-risk red lines supports treating this as a major priority; the aircraft analogy in s29 also clearly adopts, rather than merely reports, concern about catastrophe. S18 and s31 establish loss-of-control concerns at level 3, while s26 and s23 propose pauses without themselves specifying existential risk.
- **regulation** (bad citations s36, s30, s21): The explicit frontier-development pause and global slowdown proposals support 4, even though s28 describes the stand-down as voluntary. S36 supports binding safety standards at level 3, while s30 and s21 endorse guardrails without specifying a level-4 regulatory approach.

**Greg Casar** (Democrat, TX)

- **ai_overall** (bad citations s26): His overall framing is overwhelmingly threat-focused. However, s26 emphasizes technological transformation and broadly shared progress rather than directly supporting a very concerned overall stance.
- **agi_pilled** (bad citations s74, s77, s26, s57): The full record supports 4 through the centrality of superintelligence, urgency about its development, and the nuclear-revolution comparison. Individually, s74, s77 and s57 establish superintelligence as a serious possibility without the additional level-4 framing, while s26 supports transformative AI at level 2.
- **x_risk** (bad citations s68, s64, s58): S60 explicitly treats an extinction warning as an emergency requiring action, and s59 and s62 adopt nuclear-danger comparisons. S68, s64 and s58 directly support loss-of-control concern at level 3, but do not themselves establish existential risk as a top-tier priority at level 4.
- **china_race** (bad citations s38): S65 and s67 explicitly reject the AI arms race, and s25 rejects competition at workers' expense. S38 calls for international safety cooperation but does not address China or reject race framing.
- **regulation** (bad citations s38, s51): The proposed bans, federal agency oversight and pauses clearly support 4. S38 and s51 call for mandatory testing, transparency and oversight, which directly support level 3 rather than independently establishing comprehensive regulation at level 4.

**James P. McGovern** (Democrat, MA)

- **x_risk** (bad citations s14, s18): Statements s10 and s12 support treating existential risk as a major priority; s12 explicitly adopts the reported concern by calling even a fraction of that probability unacceptable. However, s14 discusses human-rights risks without explicit existential framing, while s18 merely lists an existential threat among several issues rather than establishing level-4 priority.
- **regulation** (bad citations s3, s2, s9): The federal data center moratorium in s6 and s7 directly supports level 4, reinforced by the call to pump the brakes in s16. Opposing state-law preemption in s2 and s3, and rejecting industry self-regulation in s9, do not independently establish comprehensive regulation or pauses.

**Jennifer L. McClellan** (Democrat, VA)

- **agi_pilled** (Sonnet 3.0 → reviewer 2; bad citations s20, s33, s34, s13, s37, s21): She clearly expects society-wide transformation, but none of these statements establishes an expectation of AGI, human-level AI, or superintelligence. Existential warnings and rogue-AI concerns do not by themselves establish that intelligence threshold, and s37 reports another person's timeline rather than explicitly adopting it.
- **x_risk** (bad citations s30, s32): Statements s33, s34, and s36 support treating existential risk as a major priority, including nuclear comparisons and an explicit warning about humanity ending. Statement s30 supports loss-of-control concern at level 3, while s32 concerns cybersecurity incidents and hearings without establishing level-4 prioritization.
- **regulation** (bad citations s36, s35, s19, s34, s42): Her call for comprehensive action in s37, read with her broader demands for policy-wide AI governance, supports level 4. The other cited statements establish oversight, regulatory authority, opposition to preemption, or unspecified guardrails, but do not individually establish comprehensive regulation at that level.

**Josh Hawley** (Republican, MO)

- **ai_overall** (bad citations s247, s49): The overall record is predominantly concerned while acknowledging possible benefits. However, s247 and s49 individually express a balanced, conditional view rather than directly supporting the mostly-concerned level.
- **agi_pilled** (bad citations s163): The transformative language and printing-press/atom-bomb comparison support 2 without establishing expectations of AGI. Statement s163 expresses a threat to liberty but does not itself establish the scale of technological transformation required for this level.
- **x_risk** (Sonnet 3.0 → reviewer 1; bad citations s246, s6, s190, s283, s243): These citations do not clearly establish autonomous loss of control or existential risk: the control language concerns political power and liberty, the atom-bomb comparison is an open-ended analogy, and testing or rogue-agent hearing announcements do not establish that position. His clearly adopted concerns center on jobs, children, privacy, manipulation and corporate power.
- **china_race** (bad citations s130): Repeated opposition to Chinese AI partnerships, supply chains and technology transfers supports a recurring but non-dominant competition theme. Statement s130 invokes past free-trade arguments about China as an analogy, not competition with China over AI.
- **regulation** (Sonnet 3.0 → reviewer 4; bad citations s208, s218): Statement s3 explicitly endorses a deployment moratorium until adequate safety cases exist, meeting the rubric's level 4 criterion despite his many narrower proposals. Statements s208 and s218 concern targeted chatbot restrictions and layoff reporting, respectively, rather than directly supporting level 3.

**Julia Brownley** (Democrat, CA)

- **agi_pilled** (Sonnet insufficient_evidence → reviewer 1; bad citations s1, s2): She does address AI's future importance: it will change how people live in coming years and be 'very, very important.' These statements frame consequential but ordinary technological development, supporting 1 rather than insufficient evidence.
- **regulation** (Sonnet 2.0 → reviewer insufficient_evidence; bad citations s6, s4): Supporting an implementation pilot does not establish support for targeted AI regulations. The proposed technology agency would advise Congress about regulation; she does not endorse particular rules or give it regulatory authority.

**Kevin Kiley** (Independent, CA)

- **ai_overall** (bad citations s18, s29, s23): His explicit balancing of substantial benefits and urgent safety concerns supports 2, especially in s7, s35, and s36. Individually, s18 and s29 express optimism, while s23 expresses concern; they do not directly support the balanced level.
- **agi_pilled** (Sonnet 4.0 → reviewer 3; bad citations s13, s28, s19, s23, s20, s1): S13 and s28 establish AGI as a real possibility requiring preparation, supporting 3 rather than 4; none supplies an explicit short timeline or civilizational-turning-point comparison. The remaining citations describe general acceleration or transformation, or report labs' goals, rather than directly establishing level 4.
- **x_risk** (bad citations s37, s12, s2): S13 and s35 directly establish concern about misaligned capabilities and maintaining human control. S37 and s12 emphasize alignment without identifying loss of control or existential consequences, while s2's brief list of concerns does not clearly establish that level.
- **china_race** (Sonnet 2.0 → reviewer 0; bad citations s2, s38, s21, s34): S34 explicitly advocates international communication to avoid disastrous arms races, supporting 0, reinforced by s38's emphasis on collaboration and shared safety. S2 and s21 establish limited geopolitical awareness, not recurring competition at level 2; s34 and s38 likewise do not support that score.
- **regulation** (bad citations s21, s8, s10, s14): S17's fraud penalties and s4's transparency proposal support targeted rules at level 2. S21 and s8 instead support a light-touch stance, s10 concerns research funding rather than regulation, and s14 does not endorse a specific regulatory measure.

**Kurt Alme** (Republican, MT)

- **ai_overall** (Sonnet 3.0 → reviewer 2; bad citations s4, s3): His substantive discussion balances benefits against community harms and required guardrails; s3 and s4 support that balance rather than predominantly optimistic framing. The broad pro-innovation language in s1 should not outweigh his more specific AI-related statements.
- **x_risk** (Sonnet insufficient_evidence → reviewer 1): His own concerns about AI data centers include water quality, electricity costs and community impacts, particularly in s5–s7. These are ordinary harms without catastrophic framing, which satisfies level 1; the rubric does not require a more general discussion of AI risks.
- **china_race** (bad citations s8): S1 minimally connects AI to American global innovation leadership, supporting level 1. S8 discusses technological intellectual-property theft generally without explicitly connecting China to AI, so it is not direct evidence of an AI-race stance.
- **regulation** (bad citations s1): The concrete transparency, water, electricity and community-acceptance requirements support targeted rules at level 2. S1's general opposition to stifling innovation does not directly support that regulatory level.

**Martin Heinrich** (Democrat, NM)

- **agi_pilled** (bad citations s52, s45, s29): s43 supports a transformative, lasting impact, reinforced by s35. The other cited statements describe applications, enthusiasm, or rapid advancement without establishing transformative scale.
- **x_risk** (Sonnet 3 → reviewer 1; bad citations s2, s58, s33): Interpretability and controllability research, an unspecified warning, and support for a Safety Institute do not establish concern about existential risk or losing control of advanced AI. His explicit concerns include ordinary harms such as privacy violations, deepfakes, and effects on jobs.
- **china_race** (bad citations s27, s17): Global competitiveness recurs in his own statements, including s36, s37, and s46, while remaining balanced with other priorities. s27 discusses military capabilities rather than international competition, and s17 reports Microsoft's findings without clearly adopting a competitive-policy position.
- **regulation** (bad citations s30, s32, s1, s42): His endorsement of the executive order as a legislative baseline and support for a federal Safety Institute support substantial governance. Generic guardrail language, transparency requirements, and an unspecified prohibition do not independently establish level 3.
- **summary**: The summary is broadly accurate, but it attributes support for safety testing that the statements do not explicitly establish. His recurring competitive framing concerns American global leadership generally; an adopted China-specific competition stance is less clearly supported.

**Melat Kiros** (Democratic, CO)

- **agi_pilled** (bad citations s28, s2): s23 and s34 treat superintelligence as a real possibility requiring action, supporting 3. s28 and s2 support transformative economic change at level 2, not specifically AGI or superintelligence.
- **x_risk** (Sonnet 4.0 → reviewer 3; bad citations s23, s34, s35, s32): s23 and s34 clearly establish concern about losing control of advanced AI, but do not clearly establish existential or extinction risk as a top-tier priority warranting 4. s35 uses existential language about climate, the economy, and democracy rather than clearly identifying extinction risk, while s32 is only a general demand for regulation.
- **regulation** (bad citations s35, s32, s14): The explicit ASI pause and data center moratoriums in s34, s36, and s22 directly support 4. s35 and s32 demand regulation without specifying a level-4 framework, while s14 calls for safeguards against particular harms rather than comprehensive regulation or pauses.

**Nydia M. Velázquez** (Democrat, NY)

- **ai_overall** (bad citations s7, s2): Statements s3, s4, and s6 directly support a balanced assessment. Statements s7 and s2 discuss risks alone and do not independently support the balanced level required by the citation rule.
- **regulation** (bad citations s5, s3): Safeguards for federal AI tools and annual SBA reporting in s8 and s9 support targeted regulation. Small-business assistance in s5 and general responsible-use language in s3 do not themselves establish support for regulatory requirements.

**Patty Murray** (Democrat, WA)

- **ai_overall** (bad citations s33): Statements s2, s16, s31, and s32 support a balanced assessment of opportunities and risks. Statement s33 addresses danger and urgent safety action, not a balanced overall outlook.
- **agi_pilled** (bad citations s26, s33): The Manhattan Project comparison in s5 and economy-and-future reshaping language in s27 support transformative significance without establishing AGI expectations. Statements s26 and s33 establish power and safety concerns, not the scale of future transformation.
- **x_risk** (Sonnet 3.0 → reviewer 1; bad citations s27, s33, s34, s31): None of these statements acknowledges loss of control or existential risk: s27 reports experts' catastrophe warning while criticizing Trump, and the others endorse safety concerns without specifying catastrophic outcomes. Her clearly articulated risks concern health care, children, mental health, privacy, and jobs; neither the nuclear-plant analogy nor unspecified 'worst risks' establishes level 3.
- **china_race** (bad citations s1): Statement s30 explicitly calls for negotiating AI safeguards with China, supporting level 0. Statement s1 instead expresses concern about China's pursuit of AI dominance and does not support that level.
- **regulation** (bad citations s12, s14): Her urgent calls for federal regulation and rejection of industry self-regulation support level 3, particularly s33–s35. Statements s12 and s14 defend states' ability to enact protections but do not independently establish substantial company-level obligations at that level.
- **summary**: The summary overstates the evidence by saying she has begun voicing concern about catastrophic AI risks after speaking with Hinton. She adopts Hinton's general safety concerns, but does not identify them as catastrophic or existential; the explicit catastrophe warning is attributed to experts in a criticism of Trump.

**Richard McCormick** (Republican, GA)

- **ai_overall** (Sonnet 3.0 → reviewer 4; bad citations s97, s51, s100): His overwhelming enthusiasm, dismissal of existential danger, and repeated arguments that government should get out of AI's way support 4. The listed citations emphasize transformative benefits with minimal qualification, rather than the manageable-risk framing supporting 3.
- **x_risk** (Sonnet 1.0 → reviewer 0; bad citations s90, s64, s118, s9): S90 explicitly rejects existential risk, directly supporting 0 rather than 1. S9 raises AI-related biological threats consistent with serious misuse, while s64 and s118 oppose pauses without independently stating a risk assessment.
- **regulation** (Sonnet 1.0 → reviewer 0; bad citations s75, s30, s38): His opposition to additional Washington restrictions, rejection of state AI rules, and support for a moratorium meet the rubric's strongly anti-regulation category. These citations support 0 rather than 1; his support for existing liability and narrow protections does not negate that stance.

**Ro Khanna** (Democrat, CA)

- **agi_pilled** (bad citations s21, s247): His urgent call to pause recursive self-improvement supports treating radically advanced AI as a real possibility. However, s21 reports another person's timeline and solicits an assessment, while s247 establishes existential concern without specifying AGI, superintelligence, or human-level capability.
- **x_risk** (bad citations s247): The worldwide pause proposal, urgent containment agenda, and nuclear-war comparison support level 4. By itself, s247 acknowledges existential and loss-of-control risks, which establishes level 3 rather than their top-tier prioritization.
- **china_race** (bad citations s155, s246, s242, s255): Recurring competition statements support level 2 overall, particularly s19, s31, s63, and s75. However, s155 offers only general leadership language, while s246, s242, and s255 support level 0 cooperation or rejection of race framing rather than level 2.
- **regulation** (bad citations s172, s71): The agency, certification, and worldwide pause proposals clearly establish level 4. Mandatory third-party verification in s172 supports level 3, while s71 supports protective regulation and opposition to preemption without establishing a comprehensive regulatory framework.
- **summary**: The summary is otherwise supported, but it dates the catastrophic-risk shift too early. Late-2025 statements emphasize employment, inequality, and ordinary safety concerns; explicit extinction and loss-of-control prioritization emerges in September–October 2026.

**Ruben Gallego** (Democrat, AZ)

- **agi_pilled** (Sonnet 3.0 → reviewer 2; bad citations s20, s23, s4, s21): His comparisons with previous technologies and warnings about autonomous decisions support a transformative outlook, but do not establish an expectation of AGI, superintelligence, or human-level AI. None of the cited statements directly supports level 3; s4 does not itself establish the scale of transformation.
- **x_risk** (bad citations s19, s2): The autonomous killing and escaped-monster framing supports concern about loss of human control. However, s19 establishes catastrophic or national-security danger without loss of control, and s2 concerns misuse by bad actors rather than level-3 risk.
- **china_race** (Sonnet 1.0 → reviewer 0; bad citations s3, s21, s24, s1): S21 and s24 explicitly criticize race framing as a justification for allowing dangerous AI, supporting level 0 rather than minimal engagement. S3 endorses competitiveness rather than rejection, while s1's government-controlling-role language does not establish a China or international-race position.
- **regulation** (Sonnet 4.0 → reviewer 3; bad citations s3, s4, s19, s2, s25, s26): Liability and substantial safety obligations support level 3, but the statements do not explicitly endorse comprehensive AI regulation, licensing, a new regulatory agency, or a pause. A congressional select committee and an unspecified 'comprehensive response' do not establish level 4; the other citations support reporting obligations or liability instead.
- **summary**: The summary overstates support for comprehensive regulation and US leadership. The statements support substantial safeguards and maintaining competitiveness, but s1's 'controlling role' refers to government's role, not clearly US global leadership; a select committee, liability, and worker policies do not by themselves establish a comprehensive regulatory framework.

**Sam Forstag** (Democratic, MT)

- **regulation** (Sonnet 4.0 → reviewer 3; bad citations s21, s22, s1, s2, s15, s4): Mandatory third-party safety verification and kill switches support substantial regulation at level 3; generic oversight demands do not establish level 4. The power-supply condition restricts infrastructure construction, rather than establishing comprehensive AI regulation, frontier-model licensing, a new agency, or a pause on AI development.

**Sam T. Liccardo** (Democrat, CA)

- **ai_overall** (bad citations s21, s7, s70): The balanced score is directly supported by s83, s20, and s18. Individually, s7 and s21 express optimism rather than balance, while s70 addresses risks and safeguards without expressing the opportunity side.
- **agi_pilled** (bad citations s103, s95): Superintelligence escaping human control in s96 and recursive self-improvement in s45 support 3. Accelerating frontier capabilities and progress on an AGI-named benchmark do not themselves establish an expectation of human-level AI.
- **x_risk** (bad citations s68, s99, s102): His explicit concern about uncontrolled superintelligence, combined with demands for immediate congressional action on catastrophic risk, supports treating this as a major priority. However, s68, s99, and s102 discuss catastrophic risk without independently establishing existential risk as a top-tier priority.
- **china_race** (bad citations s107, s96): Competition is recurring but balanced by safety and cooperation, supporting 2 overall. Under the rubric, s107 and s96 directly support the cooperation/rejection-of-race level rather than the assigned competitive-framing level.
- **regulation** (bad citations s77, s15, s40): The concrete safety framework in s39 and explicit standards and liability in s106 support 3. Generic demands for safeguards in s77 and replacement federal regulation in s15 do not establish substantial regulatory requirements, while s40 advocates a lighter-touch referee model.

**Sara Jacobs** (Democrat, CA)

- **agi_pilled** (Sonnet 2.0 → reviewer 3; bad citations s43, s34, s23): In s43, she treats achieving AGI as a real, policy-relevant possibility, supporting level 3 rather than merely economy-wide transformation. Statements s34 and s23 concern distribution and taxation without establishing the scale of transformation required for level 2.
- **x_risk** (bad citations s37, s38, s6): Statements s47 and s50 directly establish concern about losing control, while s39 explicitly entertains an extinction outcome. Statements s37, s38, and s6 support catastrophic-risk concern but do not themselves establish loss of control or existential risk at level 3.
- **china_race** (bad citations s45): Competition is a recurring frame, but she consistently balances it against safety and adoption. Statement s45 specifically criticizes the race and calls for bilateral dialogue, supporting level 0 rather than level 2.
- **regulation** (bad citations s48, s41, s29, s46): Her comprehensive, multilevel regulatory approach in s51–s52, together with enforceable frontier-model standards in s22, supports level 4; licensing or a pause is not required. The flagged citations establish general regulatory support or a bill announcement, not the comprehensive scope required at that level.

**Sarah McBride** (Democrat, DE)

- **ai_overall** (bad citations s10, s14, s3, s15): s1 and s4 directly balance substantial benefits against risks, supporting 2. s10 concerns the scale of change rather than its desirability; s3, s14, and s15 emphasize dangers and protective action rather than a balanced overall assessment.
- **x_risk** (bad citations s1): Protecting 'our existence,' describing oversight as 'existentially urgent,' and requesting that Congress remain in session together establish a major priority. s1 supports serious misuse risks at level 2, not existential risk as a top-tier priority.
- **china_race** (bad citations s3): s13 briefly acknowledges competition with China without making it a central policy lens. s3's global arms-control proposal does not itself mention China or competition, and does not explicitly reject race framing.
- **regulation** (bad citations s2, s15, s4): s3's broad domestic and international regulatory agenda, reinforced by s13 and the cross-sector approach in s11, supports comprehensive regulation. s2 and s4 establish support for regulation without specifying level-4 breadth, while s15 requests urgent action without specifying regulatory measures.

**Scott Wiener** (Democratic, CA)

- **ai_overall** (bad citations s21, s125): The overall record balances substantial benefits against substantial risks. Individually, s21 supports optimism rather than balance, while s125 emphasizes potentially disastrous effects without substantively acknowledging benefits.
- **agi_pilled** (bad citations s116, s128, s108): His own descriptions of AI's historic power and economy-wide transformation support 2. Reporting Trump's superhuman-intelligence race, criticizing superintelligence glorification, and acknowledging loss of control do not clearly establish his own expectation of AGI or human-level AI.
- **x_risk** (Sonnet 4.0 → reviewer 3; bad citations s5, s112, s108, s132, s116, s114): S108 and s112 clearly establish that he takes loss of control and runaway-AI catastrophe seriously, and s5 adopts concern about extinction. These citations do not clearly establish the additional level-4 claim that existential or extinction risk specifically is a top-tier priority; several discuss only unspecified catastrophic risks.
- **china_race** (bad citations s3, s115): S117 explicitly supports collaboration with China, establishing 0. S3 concerns competition among technology companies, and s115 does not establish an international race context; neither directly supports this dimension.
- **regulation** (bad citations s124, s125, s113): S123 and s116 directly support 4 through independent regulators, a regulatory body, and slowing development. S124, s125, and s113 support government regulation or opposition to weak preemption, but do not themselves establish level-4 regulatory measures.

**Seth Moulton** (Democrat, MA)

- **ai_overall** (bad citations s40, s37): His overall presentation is predominantly concerned, while acknowledging benefits. However, s40 explicitly balances great opportunities against great risks, and s37 balances leadership with restrictions rather than directly supporting a mostly concerned assessment.
- **agi_pilled** (bad citations s36, s37, s20): Calling AI the most important technology of our lifetime in s43 supports transformative significance without AGI. The other citations establish longevity, inevitability, or danger, not transformation at level 2.
- **x_risk** (bad citations s9, s19, s20, s34, s22): S15 explicitly adopts extinction-risk mitigation as a global priority and directly establishes level 4. The other citations concern dangerous weapons, national-security threats, or safeguards; nuclear comparisons alone do not establish that existential risk is a major priority.
- **china_race** (bad citations s6, s17, s33): S32, s38, and s28 support a strong race framing. S6 does not establish an AI context, while s17 and s33 balance competition with safety and international rules, fitting level 2 more directly.
- **regulation** (Sonnet 4.0 → reviewer 3; bad citations s34, s40, s33, s35, s37, s20): These statements support substantial restrictions, safety requirements, accountability, and government oversight. They do not clearly establish a comprehensive regulatory regime, frontier licensing, a new agency, or a pause; regulation at multiple governmental levels is not itself comprehensive regulation.

**Shelley Moore Capito** (Republican, WV)

- **ai_overall** (bad citations s16, s7, s13): Her enthusiasm about medical applications and benefits across sectors supports an overall 3. However, s16, s7 and s13 present benefits and risks in balanced terms, supporting level 2 rather than level 3.
- **agi_pilled** (Sonnet 2.0 → reviewer 1; bad citations s13, s14, s1): These statements establish rapid development and lasting strategic importance, not an internet-scale transformation of society or the economy; the numerical internet comparison is explicitly attributed to others. Her own discussion of enduring importance and applications supports level 1, without establishing level 2.
- **regulation** (bad citations s3, s17, s18): The fraud legislation and children's and privacy safeguards in s5 and s16 support targeted regulation. By contrast, s3 supports voluntary standards at level 1, s17 reports industry requests without clearly endorsing a regulatory floor, and s18 merely expresses willingness to consider regulations.
- **summary**: The summary is largely supported, but saying she 'warns against slowing down' converts her report of the president's position in s14 into her own position. Her own statements clearly support winning the race, but do not explicitly adopt that warning.

**Stephen F. Lynch** (Democrat, MA)

- **ai_overall** (bad citations s39): The repeated acknowledgment of substantial benefits alongside risks supports a balanced overall score. However, s39 expresses strong alarm, not a balanced assessment, and should not be cited as support for level 2.
- **agi_pilled** (bad citations s39): His explicit discussion of superintelligence and alignment supports level 3, but there is no explicit short timeline or clear claim that AGI is imminent. Statement s39 alone discusses an uncontrolled weapon without establishing AGI or transformative capabilities.
- **x_risk** (Sonnet 4.0 → reviewer 3; bad citations s37, s40, s39, s41): These statements establish genuine concern about loss of control and threats to humanity, supporting level 3. They do not clearly establish existential-risk mitigation as a top-tier priority, so they do not support the cited level 4.
- **china_race** (bad citations s4, s27, s38): Statements s1 and s3 establish recurring competition framing balanced against democratic safeguards. Statement s4 reports the commission's position without clearly adopting it, s27 addresses Chinese surveillance rather than competitive leadership, and s38 supports rejection of race framing rather than level 2.

**Tammy Duckworth** (Democrat, IL)

- **regulation** (Sonnet 3.0 → reviewer 2; bad citations s9, s11, s6, s8, s2): These statements support mandatory safeguards, preserving state authority and targeted interventions, but none specifies substantial company obligations such as liability, audits or frontier-model safety testing. Rejecting self-regulation does not by itself establish level 3.

**Tom Emmer** (Republican, MN)

- **china_race** (bad citations s5): Statements s8 and s9 establish a strong China-race framing. Statement s5 advocates leadership without identifying China or a race, so it does not independently support level 3.
- **regulation** (bad citations s8, s9): Statement s7 supports an innovation-first, anti-red-tape stance while preserving local control. Statements s8 and s9 discuss competition and general deliberateness, not a preference for light-touch regulation.

**Valerie P. Foushee** (Democrat, NC)

- **ai_overall** (bad citations s116, s27, s63): Her overall emphasis on harms supports 1. However, s116, s27, and s63 balance benefits with safeguards rather than directly supporting a mostly concerned assessment.
- **agi_pilled** (bad citations s106, s36, s7): Her descriptions of AI transforming the world and the economy and society support 2 through s52 and s63. Merely changing society or reshaping work does not independently establish that scale, and s7 concerns risk prioritization rather than expectations of transformative capabilities.
- **x_risk** (Sonnet 2.0 → reviewer 1; bad citations s102, s118, s97, s120, s7): The hacks, personal-data threats, and objections to autonomous weapons lack the large-scale catastrophic framing required for 2; s120 reports researchers' control concerns without clearly adopting them. In s7 she deprioritizes speculative existential risks while allowing their legitimacy as research subjects, rather than clearly rejecting their possibility.
- **regulation** (bad citations s90): Mandatory safety assessments, criminal penalties, and accountability for company-caused harms directly support 3. However, s90 supports federal testing and evaluation capacity, not requirements imposed on AI companies.

**Vicente Gonzalez** (Democrat, TX)

- **ai_overall** (bad citations s1, s5): His own statements balance AI's potential to bring local industry (s3) with concern about AI-enabled scams (s2). However, s1 merely reports a third-party GDP estimate, and s5 does not itself connect the described scam to AI.
- **x_risk** (bad citations s5): S2 directly supports concern about ordinary AI-enabled fraud, with no catastrophic framing. S5 describes a scam but does not identify AI involvement.
- **summary**: The summary overstates his endorsement of economic growth: s1 reports a GDP projection without clearly adopting it. His own economic optimism is supported more narrowly by s3's local-industry proposal. S4 criticizes the President's conduct, but describing it as mocking the use of AI imagery is less precise.

**W. Gregory Steube** (Republican, FL)

- **x_risk** (bad citations s5, s7): The comparison in s6 to supposedly world-ending Y2K failures supports dismissiveness toward catastrophic AI alarm. However, s5 and s7 reject fear generically without identifying catastrophic or existential risk.
- **china_race** (bad citations s5, s10): S7 explicitly makes national security and winning the AI race against China priorities, supporting 3. S5 and s10 express general leadership ambitions but do not independently establish that China competition is a primary policy lens.
- **regulation** (bad citations s9, s7, s8): S10 directly supports a mostly anti-regulatory stance. S9 reports companies' objections without clearly adopting them, s7 predicts presidential opposition rather than specifying his own regulatory position, and s8 demands human verification without proposing regulation.
- **summary**: The summary mostly tracks the statements, but saying he himself argues regulation could hurt smaller firms overstates s9: he reports that argument from companies without clearly endorsing it.

**William Lawrence** (Democratic, MI)

- **agi_pilled** (bad citations s1): Calling AI a 'mass unemployment machine' in s5 supports an expectation of transformative economic disruption. However, s1 establishes growing capability, not the scale of societal transformation required for level 2.
- **x_risk** (Sonnet 4.0 → reviewer 3; bad citations s6, s5, s9): In s6, he personally adopts extinction risk as a real concern, supporting level 3, but does not clearly establish it as a top-tier priority required for level 4. The extinction warning in s5 is attributed to experts, while s9 neither mentions existential risk nor explicitly grounds its proposed pause in that risk.
- **regulation** (bad citations s3): The moratorium and advanced-AI development pause in s2 and s9 support level 4. Signing an unspecified AI Pact in s3 does not independently establish support for regulation at that level.

**Yassamin Ansari** (Democrat, AZ)

- **ai_overall** (bad citations s2): The dominant framing presents AI as a threat, supporting 0. However, s2 supports a balanced or optimistic outlook on sustainable AI development, not level 0; acknowledging it as counterevidence does not make it a supporting citation.
- **agi_pilled** (bad citations s33): Her adopted warnings about a rapidly disappearing window for action and a 'code red moment for humanity' support 4. Standing alone, s33 advocates banning superintelligence without establishing an expected timeline or civilizational turning point, so it does not directly support that level.
- **regulation** (bad citations s11): Her proposed development pause, superintelligence ban, and new federal oversight agency clearly support 4. But s11 supports specific state-level protections and opposition to preemption, not comprehensive regulation at level 4.
