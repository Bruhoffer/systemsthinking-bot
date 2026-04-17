"""'Fixes that Fail' archetype quiz + Behaviour Over Time (BOT) questions."""

# ── Part 1: MCQ (archetype) ──────────────────────────────────────────────────

MCQ_QUESTIONS: list[dict] = [
    {
        "question": (
            "Which of the following best describes the **'Fixes that Fail'** archetype?"
        ),
        "options": [
            "A short-term fix that permanently solves the underlying problem.",
            "A solution that relieves symptoms in the short term but generates "
            "side-effects that worsen the original problem over time.",
            "A fix that fails immediately and must be abandoned.",
            "A situation where the problem is too complex for any solution to work.",
        ],
        "answer": 1,
        "explanation": (
            "'Fixes that Fail' describes a structural pattern where an intervention "
            "targets symptoms rather than root causes. It feels effective at first — "
            "which is exactly what makes the pattern dangerous — but delayed side-effects "
            "eventually amplify the original problem, creating a cycle of escalating fixes."
        ),
    },
    {
        "question": (
            "In the Borneo DDT case, what was the **'fix'** being applied, "
            "and what symptom was it targeting?"
        ),
        "options": [
            "Parachuting cats — to reduce the rat population.",
            "Draining swamps — to eliminate mosquito breeding grounds.",
            "Spraying DDT — to reduce the mosquito population and lower malaria incidence.",
            "Relocating villagers — to separate people from the infected areas.",
        ],
        "answer": 2,
        "explanation": (
            "The WHO's fix was DDT spraying, targeting the mosquito population as the "
            "proximate cause of malaria. It worked — mosquito numbers fell and malaria "
            "incidence dropped. But DDT entered food chains it was never meant to reach, "
            "triggering a cascade of unintended consequences across the entire ecosystem."
        ),
    },
    {
        "question": (
            "Why did the harmful side-effects of DDT spraying appear **much later** "
            "than the initial benefits?"
        ),
        "options": [
            "The WHO stopped monitoring the programme after early success.",
            "Mosquitoes evolved resistance to DDT, reversing the gains.",
            "DDT bioaccumulation through the food chain (insects → geckos → cats) "
            "required time to reach lethal concentrations at each level.",
            "Villagers continued applying DDT independently after the programme ended.",
        ],
        "answer": 2,
        "explanation": (
            "Bioaccumulation is a built-in delay: each trophic level must consume large "
            "quantities of the level below before the dose becomes lethal. Geckos had to "
            "eat hundreds of DDT-laden insects; cats had to eat many geckos. These "
            "biological delays are what make 'Fixes that Fail' so difficult to diagnose — "
            "by the time the side-effects arrive, the original fix is long forgotten."
        ),
    },
    {
        "question": (
            "In a Causal Loop Diagram of 'Fixes that Fail', "
            "how does the **unintended side-effect path** typically connect "
            "back to the original problem?"
        ),
        "options": [
            "It forms a reinforcing loop that amplifies the fix indefinitely.",
            "It is a linear chain — side-effects do not feed back to the problem.",
            "It creates a second balancing loop that routes through unintended "
            "consequences, eventually worsening the original problem.",
            "It cancels out the main balancing loop, making the system neutral.",
        ],
        "answer": 2,
        "explanation": (
            "The archetype has two balancing loops sharing the same 'problem' node. "
            "Loop 1 (the fix): Problem → Fix → Problem↓ (short delay, effective). "
            "Loop 2 (the side-effect): Fix → Side-effects → Problem↑ (long delay, "
            "harmful). Because Loop 2 has a longer delay, decision-makers only see "
            "Loop 1 working at first — and often apply more of the fix, making things worse."
        ),
    },
    {
        "question": (
            "Which real-world scenario is **another example** of the "
            "'Fixes that Fail' archetype?"
        ),
        "options": [
            "Using a backup generator when the power goes out.",
            "Prescribing broad-spectrum antibiotics for every minor infection, "
            "which over time selects for antibiotic-resistant bacteria.",
            "Saving money over several months to buy a higher-quality, longer-lasting product.",
            "Hiring extra staff to handle a temporary surge in customer demand.",
        ],
        "answer": 1,
        "explanation": (
            "Antibiotics are a classic 'Fixes that Fail' case: each prescription reduces "
            "infection symptoms (the fix works), but also kills susceptible bacteria and "
            "leaves resistant strains to multiply. Over time, the pool of resistant bacteria "
            "grows, making future infections harder to treat — the original problem worsens. "
            "The other options are straightforward solutions without problematic feedback loops."
        ),
    },
]

TOTAL_MCQ = len(MCQ_QUESTIONS)

# ── Part 2: BOT (Behaviour Over Time) — chat-based ──────────────────────────
# Each BOT question has a prompt shown to the student and a reference_answer
# used by the evaluator LLM to judge correctness.

BOT_QUESTIONS: list[dict] = [
    {
        "question": (
            "Right after DDT spraying begins, what do you think happens to "
            "**Malaria Incidence** over the first few months? Describe the trend."
        ),
        "reference_answer": (
            "Malaria incidence decreases sharply in the short term because DDT kills "
            "the mosquitoes that transmit malaria. This is the intended effect of the fix."
        ),
    },
    {
        "question": (
            "Now think about the **Cat Population**. What happens to it over a "
            "longer time period (months to years) after DDT spraying? Why?"
        ),
        "reference_answer": (
            "The cat population decreases over time, but with a significant delay. "
            "DDT bioaccumulates in insects, then in geckos that eat the insects, and "
            "finally in cats that eat the geckos. The concentrated DDT eventually kills "
            "the cats. This is a delayed unintended consequence."
        ),
    },
    {
        "question": (
            "What happens to the **Rat Population** over time after DDT spraying begins? "
            "Describe the shape of the curve — does it go up immediately, stay flat, "
            "or does something else happen?"
        ),
        "reference_answer": (
            "The rat population stays flat (or even slightly decreases) at first, "
            "then increases sharply after a significant delay. The delay exists because "
            "the causal chain is long: DDT accumulates in insects → geckos eat insects "
            "and accumulate DDT → cats eat geckos and die → with cats gone, rats have "
            "no predator and their population explodes. Each step takes time, so the "
            "rat population surge happens well after DDT spraying — not immediately. "
            "This is a classic delayed side-effect."
        ),
    },
    {
        "question": (
            "Why does the **Rat Population** increase with a significant delay "
            "after DDT spraying begins? Trace the causal chain."
        ),
        "reference_answer": (
            "The causal chain: DDT → bioaccumulates in insects → geckos eat insects "
            "and accumulate DDT → cats eat geckos and die → with cats gone, rat population "
            "explodes. Each step requires time (bioaccumulation delays), so the rat increase "
            "happens much later than the initial DDT spraying. This delay is what makes the "
            "unintended consequence so hard to predict."
        ),
    },
]

TOTAL_BOT = len(BOT_QUESTIONS)

# Legacy aliases for backward compatibility
QUESTIONS = MCQ_QUESTIONS
TOTAL_QUESTIONS = TOTAL_MCQ
