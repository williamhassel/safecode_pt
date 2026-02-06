# Master Thesis Timeline: SafeCode

**Start:** Monday, January 20, 2026  
**End:** Tuesday, June 16, 2026  
**Total duration:** 21 weeks (with Easter break in weeks 14–15)

---

## Phase 1: Foundation and Ethics (Weeks 1–2)

### Week 1: Jan 20–26 ✓
- [x] Supervisor meeting: aligned on scope and priorities
- [x] SIKT form submitted
- [ ] Implement generation for all 10 OWASP vulnerability types
- [ ] Update project timeline

### Week 2: Jan 27–Feb 2
- Complete OWASP vulnerability coverage (carry-over from week 1)
- Confirm SIKT approval status
- Set up logging infrastructure for user interaction tracking
- Begin participant recruitment planning

**Milestone 1 (Feb 2):** All 10 vulnerability types generating valid challenges, ethics process initiated

---

## Phase 2: Agentic Pipeline and Infrastructure (Weeks 3–5)

### Week 3: Feb 3–9
- Implement verification agent improvements
- Add static analysis agent (Bandit integration)
- Measure and document generation success rates per vulnerability type

### Week 4: Feb 10–16
- Implement pre-generated challenge pool
- Background Celery tasks for continuous generation
- Instant challenge delivery (eliminate user-facing latency)

### Week 5: Feb 17–23
- Implement pedagogical review agent (basic version)
- Integration testing of full pipeline
- Begin drafting Implementation chapter
- Finalize participant recruitment (aim for 15–20 confirmed)

**Milestone 2 (Feb 23):** Agentic pipeline operational, platform ready for user testing

---

## Phase 3: First User Study (Weeks 6–7)

### Week 6: Feb 24–Mar 2
- Conduct first round of user testing (10–15 participants)
- SafeCode challenges only (no SecureCodeWarrior comparison yet)
- Collect accuracy, time, completion data
- Post-session interviews

### Week 7: Mar 3–9
- Complete remaining first-round sessions
- Preliminary quantitative analysis
- Code qualitative interview data
- Document usability issues and confusion points

**Milestone 3 (Mar 9):** First user study complete, preliminary findings documented

---

## Phase 4: Refinement (Weeks 8–9)

### Week 8: Mar 10–16
- Systematic analysis of first-round data
- Prioritize platform improvements
- Implement critical fixes

### Week 9: Mar 17–23
- Complete platform refinements
- Improve distractor generation if needed
- Prepare second study protocol with SecureCodeWarrior comparison
- Draft preliminary Results section

**Milestone 4 (Mar 23):** Platform refined based on user feedback, second study ready

---

## Phase 5: Second User Study with Comparison (Weeks 10–13)

### Week 10: Mar 24–30
- Begin second round (15–20 participants)
- Participants use both SafeCode AND SecureCodeWarrior
- Counterbalanced order

### Week 11: Mar 31–Apr 6
- Continue second-round sessions
- Comparative interviews
- Begin updating Background/Related Work chapters

### Week 12: Apr 7–13
- Complete all sessions
- Compile full dataset
- Draft Method chapter

### Week 13: Apr 14–20
- Buffer week for any delayed sessions
- Begin systematic analysis of comparative data

**Milestone 5 (Apr 20):** All data collection complete

---

## Easter Break: Weeks 14–15 (Apr 21–May 4)

Reduced work expected. Use for:
- Light writing and editing
- Catching up if behind schedule
- Rest before final push

---

## Phase 6: Analysis and Results (Weeks 16–17)

### Week 16: May 5–11
- Complete quantitative analysis
- Statistical comparisons between platforms
- Finalize qualitative themes
- Structure findings for RQ1 and RQ2

### Week 17: May 12–18
- Write Results chapter
- Create figures and tables
- Document answers to both research questions
- Send draft to supervisor

**Milestone 6 (May 18):** Results chapter complete

---

## Phase 7: Writing and Integration (Weeks 18–19)

### Week 18: May 19–25
- Write Discussion chapter
- Comparison with related work
- Limitations and threats to validity
- Write Conclusion and Future Work

### Week 19: May 26–Jun 1
- Revise Introduction and Abstract
- Integrate all chapters
- Address supervisor feedback
- Check references and formatting

**Milestone 7 (Jun 1):** Complete thesis draft

---

## Phase 8: Final Revision (Weeks 20–21)

### Week 20: Jun 2–8
- Supervisor review of complete draft
- Major revisions
- Proofreading

### Week 21: Jun 9–16
- Final revisions
- Format check against NTNU requirements
- Submit by June 16

**Milestone 8 (Jun 16):** Thesis submitted

---

## Current Status (End of Week 1)

| Task | Status | Notes |
|------|--------|-------|
| Supervisor meeting | ✓ Done | Aligned on two-week plan |
| SIKT form | ✓ Done | Awaiting response |
| 10 OWASP vulnerability types | In progress | Currently 2/10 working (sqli, xss) |
| Timeline update | In progress | This document |

### Carry-over to Week 2
The OWASP implementation is the priority. Currently working:
- SQL Injection (sqli) ✓
- Cross-Site Scripting (xss) ✓

Remaining 8 to implement:
1. Path Traversal (path_traversal)
2. Command Injection (cmdi)
3. XML External Entity (xxe)
4. Insecure Deserialization (insecure_deser)
5. Server-Side Request Forgery (ssrf)
6. Weak Cryptography (weak_crypto)
7. Hardcoded Credentials (hardcoded_creds)
8. Authentication Bypass (auth_bypass)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SIKT approval delayed | Medium | High | Follow up weekly, have contingency study design |
| Some vuln types won't generate reliably | High | Medium | Document failure rates, focus on working types |
| Insufficient participants | Medium | High | Recruit from multiple sources, start early |
| SecureCodeWarrior access issues | Low | High | Confirm access this week |
| Implementation takes longer than planned | High | Medium | Prioritize core features, defer nice-to-haves |

---

## Notes for Next Supervisor Meeting

- Report on OWASP implementation progress
- Discuss any vulnerability types proving difficult
- Confirm SecureCodeWarrior access
- Review SIKT status
- Adjust timeline if needed based on week 2 progress
