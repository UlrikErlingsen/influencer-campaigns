# Compliance rules — sources and open questions

**Checklist support, not legal advice.**

The checklist is defined in [`src/creatorsignal/rules/no.yaml`](../src/creatorsignal/rules/no.yaml). This page explains how the rules were sourced and what is still open.

## How the rules were sourced (1 October 2026)

| Source | URL | Last updated (as shown) | Used for |
|---|---|---|---|
| Forbrukertilsynet — Veileder for merking av reklame i sosiale medier | https://www.forbrukertilsynet.no/lov-og-rett/veiledninger-og-retningslinjer/someveiledning | 18 May 2026 | `ad_identified`, `label_wording`, `stories_each_labelled` |
| Forbrukertilsynet — Merking av retusjert reklame | https://www.forbrukertilsynet.no/vi-jobber-med/merking-av-retusjert-reklame | 11 April 2025 | `retouch_label` |
| Forbrukertilsynet — Ofte stilte spørsmål om retusjert reklame | https://www.forbrukertilsynet.no/vi-jobber-med/merking-av-retusjert-reklame/ofte-stilte-sporsmal-om-retusjert-reklame | 29 September 2025 | `retouch_label` (filters, digital make-up) |
| Lovdata — Markedsføringsloven | https://lovdata.no/dokument/NL/lov/2009-01-09-2 | — | §§ 2 and 8 |
| Lovdata — Alkoholloven § 9-2 | https://lovdata.no/dokument/NL/lov/1989-06-02-27/§9-2 | — | restricted category: alcohol |
| Lovdata — Tobakksskadeloven § 22 | https://lovdata.no/dokument/NL/lov/1973-03-09-14/§22 | — | restricted category: tobacco/nicotine |
| Lotteri- og stiftelsestilsynet — ban on marketing unlicensed gambling | https://lottstift.no/content/uploads/2023/01/22_04830-1-Informasjon-om-forbudet-mot-markedsforing-av-pengespill-uten-tillatelse.pdf | — | restricted category: gambling |
| Forbrukertilsynet — Barn kan se og høre reklamen din | https://www.forbrukertilsynet.no/vi-jobber-med/barn-og-unge/barn-og-reklame/barn-kan-se-og-hore-reklamen-din | — | restricted category: children |

The quotes were taken from the pages by automated extraction. Before you rely on a quote, open the URL and confirm the wording is still current.

## Correction to the original brief

The brief cited **markedsføringsloven § 3** for advertising identification. The current Lovdata text (amended by lov 16. juni 2023 nr. 38, in force 1 October 2023) titles § 3 *Dokumentasjon av markedsføring*. Forbrukertilsynet's guide now bases the labelling duty on **§ 8 første ledd** (misleading omissions — not making the commercial purpose clear) and **ehandelsloven § 9**. The YAML cites those.

## Open questions — `TODO(verify)`

1. **Text on the retouching mark.** The official pages fetched did not state the exact words printed on the standard mark. The checklist therefore asks whether "the standard mark" is shown and points to Forbrukertilsynet's marking service (https://retusjert.forbrukertilsynet.no/) for the official file. Do not recreate the mark from memory.
2. **Corner of the retouching mark.** The main page says "venstre hjørne" (right corner if it collides with other elements); one extraction of the guide said "øvre venstre hjørne". Check the guide.
3. **Nicotine products.** How the tobacco advertising ban applies to each nicotine product (snus, nicotine pouches, e-cigarettes) needs checking against tobakksskadeloven's definitions.
4. **Gambling.** The exact section of pengespilloven and the rules for licensed operators.
5. **Children.** The applicable sections of markedsføringsloven on marketing aimed at children.

## Editing the rules

- Keep `id` values stable once used; saved answers refer to them.
- `applies_when` is one of `always`, `shows_person`, `format_story`, `restricted_category`.
- Every rule needs at least one `https://` source; the loader refuses the file otherwise, and refuses a file whose English disclaimer no longer says it is not legal advice.
- The app reloads the YAML automatically when the file changes.
