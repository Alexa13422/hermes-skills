---
name: medical-clinic-comparisons
description: "Use when comparing clinics and diagnostic tests."
version: 1.0.0
---

# Medical Clinic Comparisons

## Procedure

1. **Define the exact service before searching.** Distinguish anatomical terms that may be confused in local languages—for example, MRI of the breast/mammary glands versus MRI of the chest. Record whether contrast, implants, a particular protocol, a referral, or an interpretation by a subspecialist is required.
2. **Search official clinic pages first.** Retrieve the service page, price list, equipment page, specialist profile, and booking/contact page in parallel. Use an aggregator only to discover candidates or prices, then confirm decisive details with the provider.
3. **Build a comparable evidence table** for every viable provider: exact test name, total price and whether contrast is included, location, scanner/model and field strength if published, named interpreting doctor and relevant specialty, BI-RADS/reporting protocol if published, booking route, and date/access caveats.
4. **Resolve price ambiguity before recommending.** If a price list displays both a procedure price and a separate contrast fee, state the possible total as a range and tell the user exactly what to confirm at booking; do not silently choose one interpretation.
5. **Rank only against explicit clinical criteria.** For breast MRI, prioritize a named breast-imaging radiologist and access to a breast/oncology care pathway over generic “modern equipment” claims. Scanner field strength is one factor, not proof that a clinic is best.
6. **Give a short recommendation hierarchy.** Name a first choice with its reason, one or two alternatives for a different priority (fast appointment, price, scanner comfort, coordinated oncology care), and practical booking wording in the clinic’s language.
7. **State preparation only from the provider or treating clinician.** Flag common booking requirements—recent creatinine for gadolinium, prior imaging, cycle timing, implants, renal function, pregnancy/lactation, and previous biopsy—but do not convert general information into individualized medical advice.
8. **Cite every current provider claim inline and render a source list** using `grounded-citations`. Cite official clinic pages for prices, equipment, and staff; cite any third-party profile only as supplementary evidence.

## Decision Rules

- Recommend a specialist breast-imaging interpretation when evaluating a suspicious lesion, hereditary/high risk, previous breast cancer, or surgical planning; an MRI scanner alone cannot establish that expertise.
- Prefer a center with a documented coordinated breast/oncology pathway when a cancer diagnosis is known or strongly suspected; recommend an imaging-only provider for straightforward monitoring only when its reporting expertise is clear.
- Separate **MRI for implant integrity** from **contrast-enhanced MRI for breast tissue**. The former can often use a non-contrast implant protocol; the latter usually requires a dedicated dynamic contrast protocol. Confirm the clinical aim rather than assuming they are interchangeable.
- Do not call a clinic “the best” based on reviews, price, or tesla alone. Say which criterion makes it the best fit.

## Pitfalls

- **Confirm that “breast” rather than “thoracic/chest” MRI is booked**, because the names can look similar while the clinical protocol and coil are different.
- **Do not compare raw prices without testing inclusions**, because contrast, radiologist report, DICOM images, urgent reporting, and consultation may be billed separately.
- **Do not infer breast-MRI expertise from a radiologist whose published focus is another body system**, because generic MRI proficiency does not demonstrate breast-imaging specialization.
- **Treat clinics’ technology marketing as provider claims, not an independent measure of diagnostic superiority**, because image quality also depends on the breast coil, protocol, patient motion, and interpretation.
- **Do not let an appointment marketplace substitute for the clinic’s own current price list**, because its price, staff, and availability can lag the provider.
- **Avoid clinical guarantees and broad safety claims**, because suitability for gadolinium contrast and timing after procedures require an individual clinical assessment.

## Output Shape

Write in the user’s language and be direct:

1. a one-line recommendation;
2. 2–4 ranked options with price and reason to choose each;
3. a short “what to ask while booking” list in the local language;
4. only the preparation points relevant to the requested study;
5. concise inline citations and a Sources block.

Do not pad a clinic comparison with generic explanations of MRI unless they affect the choice.