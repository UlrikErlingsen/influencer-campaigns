# Compliance rules — sources and open questions

**Checklist support, not legal advice.**

The checklist is defined in [`src/influencesignal/rules/no.yaml`](../src/influencesignal/rules/no.yaml). This page explains how the rules were sourced and what is still open.

## How the rules were sourced (1 October 2026)

| Source | URL | Last updated (as shown) | Used for |
|---|---|---|---|
| Forbrukertilsynet — Veileder for merking av reklame i sosiale medier | https://www.forbrukertilsynet.no/lov-og-rett/veiledninger-og-retningslinjer/someveiledning | 18 May 2026 | `ad_identified`, `label_wording`, `stories_each_labelled` |
| Forbrukertilsynet — Merking av retusjert reklame | https://www.forbrukertilsynet.no/vi-jobber-med/merking-av-retusjert-reklame | 11 April 2025 | `retouch_label` |
| Forbrukertilsynet — Ofte stilte spørsmål om retusjert reklame | https://www.forbrukertilsynet.no/vi-jobber-med/merking-av-retusjert-reklame/ofte-stilte-sporsmal-om-retusjert-reklame | 29 September 2025 | `retouch_label` (filters, digital make-up) |
| Lovdata — Markedsføringsloven | https://lovdata.no/dokument/NL/lov/2009-01-09-2 | — | §§ 2 and 8 |
| Lovdata — Alkoholloven § 9-2 | https://lovdata.no/dokument/NL/lov/1989-06-02-27/§9-2 | — | restricted category: alcohol |
| Lovdata — Tobakksskadeloven § 22 | https://lovdata.no/dokument/NL/lov/1973-03-09-14/§22 | — | restricted category: tobacco/nicotine |
| Helsedirektoratet — Forbud mot reklame (tobakksskadeloven) | https://www.helsedirektoratet.no/veiledere/tobakksskadeloven/reklameforbud | 12 May 2026 | restricted category: tobacco/nicotine (scope, social media) |
| Lovdata — Forskrift om merking av retusjert reklame (FOR-2022-06-17-1114) | https://lovdata.no/dokument/SF/forskrift/2022-06-17-1114 | — | `retouch_label` (size, placement, video) |
| Forbrukertilsynet — Veileder for merking av retusjert reklame | https://www.forbrukertilsynet.no/vi-jobber-med/merking-av-retusjert-reklame/forbrukertilsynets-veiledning-om-merking-av-retusjert-reklame | 18 August 2026 | `retouch_label` (the mark contains «REKLAME») |
| Lovdata — Pengespilloven § 6 | https://lovdata.no/dokument/NL/lov/2022-03-18-12/§6 | — | restricted category: gambling |
| Lovdata — Markedsføringsloven § 19 (§§ 19–21) | https://lovdata.no/dokument/NL/lov/2009-01-09-2/§19 | — | restricted category: children |
| Forbrukertilsynet — Barn kan se og høre reklamen din | https://www.forbrukertilsynet.no/vi-jobber-med/barn-og-unge/barn-og-reklame/barn-kan-se-og-hore-reklamen-din | — | restricted category: children (guidance) |

The quotes were taken from the pages by automated extraction. Before you rely on a quote, open the URL and confirm the wording is still current.

## Correction to the original brief

The brief cited **markedsføringsloven § 3** for advertising identification. The current Lovdata text (amended by lov 16. juni 2023 nr. 38, in force 1 October 2023) titles § 3 *Dokumentasjon av markedsføring*. Forbrukertilsynet's guide now bases the labelling duty on **§ 8 første ledd** (misleading omissions — not making the commercial purpose clear) and **ehandelsloven § 9**. The YAML cites those.

## Resolved on 1 October 2026 (second pass)

- **Corner of the retouching mark.** The regulation (FOR-2022-06-17-1114 § 1) says upper left, below any filters and usernames; another corner only if a different mandatory mark already occupies it. Forbrukertilsynet's overview page (April 2025) still says "venstre hjørne" with the right corner as a fallback; the regulation governs.
- **Text on the mark.** Forbrukertilsynet's guide (updated 18 August 2026) states that the mark contains the word «REKLAME». The checklist still asks for the official file from https://retusjert.forbrukertilsynet.no/ rather than a recreation.
- **Gambling.** Pengespilloven § 6 (marketing only as far as needed to inform and channel play to responsible offers; forbidden to market gambling not permitted under the act, to market to minors, or to market directly to people who opted out). Detailed rules: pengespillforskriften.
- **Children.** Markedsføringsloven §§ 19–21; § 19 requires particular care when marketing is aimed at, or can be seen or heard by, children.

## Open questions — `TODO(verify)`

1. **Nicotine products.** Tobakksskadeloven § 22 bans advertising for tobacco products and, by its fifth paragraph, tobakkssurrogater, tobakksimitasjoner and tobakksutstyr. § 2 separately defines "nikotinprodukter". Neither § 22 nor [Helsedirektoratet's guide to the advertising ban](https://www.helsedirektoratet.no/veiledere/tobakksskadeloven/reklameforbud) (updated 12 May 2026) names nicotine products; the guide's examples of surrogates are nicotine-free ("e-sigaretter uten nikotin", "tobakks- og nikotinfri snus"). Whether the ban covers, for example, nicotine pouches with nicotine but no tobacco is therefore not confirmed. The flag is raised for the whole tobacco/nicotine category either way. The same guide confirms the ban applies in social media (Instagram, Snapchat, TikTok, YouTube) and that posts by people closely connected to the business can circumvent it.

## Editing the rules

- Keep `id` values stable once used; saved answers refer to them.
- `applies_when` is one of `always`, `shows_person`, `format_story`, `restricted_category`.
- Every rule needs at least one `https://` source; the loader refuses the file otherwise, and refuses a file whose English disclaimer no longer says it is not legal advice.
- The app reloads the YAML automatically when the file changes.
