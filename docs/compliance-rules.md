# Compliance rules — sources and open questions

**Checklist support, not legal advice.**

The checklist is defined in [`src/influencesignal/rules/no.yaml`](../src/influencesignal/rules/no.yaml). This page explains how the rules were sourced and what is still open.

## How the rules were sourced (1 October 2026)

| Source | URL | Last updated (as shown) | Used for |
|---|---|---|---|
| Forbrukertilsynet (Norwegian Consumer Authority) — Guide to labelling advertising in social media (Veileder for merking av reklame i sosiale medier) | https://www.forbrukertilsynet.no/lov-og-rett/veiledninger-og-retningslinjer/someveiledning | 18 May 2026 | `ad_identified`, `label_wording`, `stories_each_labelled` |
| Forbrukertilsynet — Labelling of retouched advertising (Merking av retusjert reklame) | https://www.forbrukertilsynet.no/vi-jobber-med/merking-av-retusjert-reklame | 11 April 2025 | `retouch_label` |
| Forbrukertilsynet — Frequently asked questions about retouched advertising (Ofte stilte spørsmål om retusjert reklame) | https://www.forbrukertilsynet.no/vi-jobber-med/merking-av-retusjert-reklame/ofte-stilte-sporsmal-om-retusjert-reklame | 29 September 2025 | `retouch_label` (filters, digital make-up) |
| Lovdata (official legal database) — Marketing Control Act (markedsføringsloven) | https://lovdata.no/dokument/NL/lov/2009-01-09-2 | — | §§ 2 and 8 |
| Lovdata — Alcohol Act (alkoholloven) § 9-2 | https://lovdata.no/dokument/NL/lov/1989-06-02-27/§9-2 | — | restricted category: alcohol |
| Lovdata — Tobacco Control Act (tobakksskadeloven) § 22 | https://lovdata.no/dokument/NL/lov/1973-03-09-14/§22 | — | restricted category: tobacco/nicotine |
| Helsedirektoratet (Norwegian Directorate of Health) — Advertising ban (Forbud mot reklame, tobakksskadeloven) | https://www.helsedirektoratet.no/veiledere/tobakksskadeloven/reklameforbud | 12 May 2026 | restricted category: tobacco/nicotine (scope, social media) |
| Lovdata — Regulation on labelling of retouched advertising (forskrift om merking av retusjert reklame, FOR-2022-06-17-1114) | https://lovdata.no/dokument/SF/forskrift/2022-06-17-1114 | — | `retouch_label` (size, placement, video) |
| Forbrukertilsynet — Guide to labelling retouched advertising (Veileder for merking av retusjert reklame) | https://www.forbrukertilsynet.no/vi-jobber-med/merking-av-retusjert-reklame/forbrukertilsynets-veiledning-om-merking-av-retusjert-reklame | 18 August 2026 | `retouch_label` (the mark contains «REKLAME») |
| Lovdata — Gambling Act (pengespilloven) § 6 | https://lovdata.no/dokument/NL/lov/2022-03-18-12/§6 | — | restricted category: gambling |
| Lovdata — Markedsføringsloven § 19 (§§ 19–21) | https://lovdata.no/dokument/NL/lov/2009-01-09-2/§19 | — | restricted category: children |
| Forbrukertilsynet — Children can see and hear your advertising (Barn kan se og høre reklamen din) | https://www.forbrukertilsynet.no/vi-jobber-med/barn-og-unge/barn-og-reklame/barn-kan-se-og-hore-reklamen-din | — | restricted category: children (guidance) |

The quotes were taken from the pages by automated extraction and stay in the original Norwegian; each carries an unofficial English translation (`quote_en`), which the app shows first. Before you rely on a quote, open the URL and confirm the wording is still current.

## Correction to the original brief

The brief cited **markedsføringsloven § 3** for advertising identification. The current Lovdata text (amended by the Act of 16 June 2023 no. 38, in force 1 October 2023) titles § 3 *Dokumentasjon av markedsføring* (documentation of marketing). Forbrukertilsynet's guide now bases the labelling duty on **§ 8 første ledd** (section 8, first paragraph: misleading omissions — not making the commercial purpose clear) and **ehandelsloven § 9** (the E-Commerce Act). The YAML cites those.

## Resolved on 1 October 2026 (second pass)

- **Corner of the retouching mark.** The regulation (FOR-2022-06-17-1114 § 1) says upper left, below any filters and usernames; another corner only if a different mandatory mark already occupies it. Forbrukertilsynet's overview page (April 2025) still says "venstre hjørne" (left corner) with the right corner as a fallback; the regulation governs.
- **Text on the mark.** Forbrukertilsynet's guide (updated 18 August 2026) states that the mark contains the word «REKLAME» (advertisement). The checklist still asks for the official file from https://retusjert.forbrukertilsynet.no/ rather than a recreation.
- **Gambling.** Pengespilloven § 6 (marketing only as far as needed to inform and channel play to responsible offers; forbidden to market gambling not permitted under the act, to market to minors, or to market directly to people who opted out). Detailed rules: pengespillforskriften.
- **Children.** Markedsføringsloven §§ 19–21; § 19 requires particular care when marketing is aimed at, or can be seen or heard by, children.

## Open questions — `TODO(verify)`

1. **Nicotine products.** Tobakksskadeloven § 22 bans advertising for tobacco products and, by its fifth paragraph, tobakkssurrogater, tobakksimitasjoner and tobakksutstyr (tobacco surrogates, imitations and accessories). § 2 separately defines "nikotinprodukter" (nicotine products). Neither § 22 nor [Helsedirektoratet's guide to the advertising ban](https://www.helsedirektoratet.no/veiledere/tobakksskadeloven/reklameforbud) (updated 12 May 2026) names nicotine products; the guide's examples of surrogates are nicotine-free ("e-sigaretter uten nikotin" — nicotine-free e-cigarettes; "tobakks- og nikotinfri snus" — tobacco- and nicotine-free snus). Whether the ban covers, for example, nicotine pouches with nicotine but no tobacco is therefore not confirmed. The flag is raised for the whole tobacco/nicotine category either way. The same guide confirms the ban applies in social media (Instagram, Snapchat, TikTok, YouTube) and that posts by people closely connected to the business can circumvent it.

## Editing the rules

- Keep `id` values stable once used; saved answers refer to them.
- `applies_when` is one of `always`, `shows_person`, `format_story`, `restricted_category`.
- Every rule needs at least one `https://` source; the loader refuses the file otherwise, and refuses a file whose English disclaimer no longer says it is not legal advice.
- The app reloads the YAML automatically when the file changes.
