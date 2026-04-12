"""'Fixes that Fail' archetype quiz — questions, answers, and explanations."""

QUESTIONS: list[dict] = [
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

TOTAL_QUESTIONS = len(QUESTIONS)
