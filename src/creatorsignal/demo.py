"""Deterministic fictional demo: the brand "Fjellbrus" (a sports drink), 25 creators and two campaigns.

Everything here is invented by code. It represents no real person, brand, campaign or result. Handles start
with ``demo_`` and e-mail addresses use the reserved ``example.com`` domain so nothing can be mistaken for a
real account.

The demo moves creators through the pipeline with ``Store.move_engagement``, so it obeys the same Paid gate
as the app.
"""

from __future__ import annotations

import random

from .rules import RuleSet
from .storage import Store
from .io import FYLKER

DEMO_NOTICE = (
    "Fictional demo: the brand Fjellbrus, every creator, handle, campaign and number here is invented by code. "
    "It represents no real person, brand or result."
)
SEED = 20261001

_FIRST_NAMES = (
    "Kari", "Ola", "Ingrid", "Jonas", "Sigrid", "Magnus", "Nora", "Henrik", "Ida", "Emil", "Thea", "Sander",
    "Maja", "Tobias", "Live", "Aksel", "Frida", "Mathias", "Astrid", "Eirik", "Solveig", "Vegard", "Hedda",
    "Trygve", "Marte",
)
_NICHES = (
    ("trener", "trening"), ("loper", "løping"), ("fjell", "fjellturer"), ("ski", "ski"), ("sykkel", "sykkel"),
    ("kost", "kosthold"), ("friluft", "friluft"), ("yoga", "yoga"), ("fotball", "fotball"), ("hverdag", "hverdag"),
)
_PLATFORM_MIX = ("instagram",) * 12 + ("tiktok",) * 7 + ("youtube",) * 3 + ("snapchat",) * 3


def demo_creators(seed: int = SEED) -> list[dict]:
    rng = random.Random(seed)
    platforms = list(_PLATFORM_MIX)
    rng.shuffle(platforms)
    creators = []
    for index, first in enumerate(_FIRST_NAMES):
        slug_word, tag = _NICHES[index % len(_NICHES)]
        second_tag = _NICHES[(index * 3 + 1) % len(_NICHES)][1]
        handle = f"demo_{first.lower()}_{slug_word}"
        followers = int(round(rng.choice((3, 5, 8, 12, 18, 25, 40, 60, 95, 150)) * 1000 * rng.uniform(0.85, 1.2), -2))
        engagement = round(max(1.2, 9.0 - followers / 25000 + rng.uniform(-1.0, 1.0)), 1)
        primary = platforms[index]
        handles = {platform: "" for platform in ("instagram", "tiktok", "youtube", "snapchat")}
        handles[primary] = handle
        if primary != "instagram" and rng.random() < 0.5:
            handles["instagram"] = handle
        reel_rate = int(round(max(1500, followers * rng.uniform(0.25, 0.45)), -2))
        creators.append(
            {
                "name": f"{first} {chr(65 + index % 26)}. (demo)",
                **handles,
                "followers": followers,
                "engagement_rate": engagement,
                "niche_tags": ", ".join(dict.fromkeys((tag, second_tag))),
                "region": FYLKER[(index * 7) % len(FYLKER)],
                "contact_email": f"{handle}@example.com",
                "contact_phone": "",
                "rate_card": f"Reel/video {reel_rate:,} NOK · story {int(round(reel_rate * 0.4, -2)):,} NOK".replace(",", " "),
                "notes": "Fictional demo creator.",
            }
        )
    return creators


def _primary_platform(creator: dict) -> str:
    for platform in ("tiktok", "youtube", "snapchat", "instagram"):
        if creator.get(platform):
            return platform
    return "instagram"


def _format_for(platform: str, rng: random.Random) -> str:
    if platform == "youtube":
        return "video"
    if platform == "snapchat":
        return "story"
    if platform == "tiktok":
        return "video"
    return rng.choice(("reel", "reel", "post", "story"))


def _results(followers: int, fee: float, rng: random.Random, strength: float) -> dict:
    reach = followers * rng.uniform(0.25, 0.7) * strength
    views = reach * rng.uniform(1.4, 2.8)
    clicks = views * rng.uniform(0.003, 0.014) * strength
    redemptions = clicks * rng.uniform(0.04, 0.16) * strength
    revenue = redemptions * rng.uniform(260, 420)
    return {
        "reach": round(reach),
        "views": round(views),
        "clicks": round(clicks),
        "redemptions": round(redemptions),
        "revenue_nok": round(revenue, -1),
    }


def _answer_all(store: Store, deliverable_id: int, rules: RuleSet, campaign: dict, deliverable: dict) -> None:
    from .compliance import applicable_rules

    for rule in applicable_rules(deliverable, campaign, rules):
        answer = "na" if rule.allow_not_applicable and not deliverable.get("_retouched") else "yes"
        store.set_answer(deliverable_id, rule.id, answer)


def load_demo(store: Store, rules: RuleSet, seed: int = SEED) -> None:
    """Replace the store's contents with the fictional demo workspace."""
    rng = random.Random(seed + 1)
    store.clear()
    creators = demo_creators(seed)
    creator_ids = [store.add_creator(creator, is_demo=True) for creator in creators]

    spring = store.add_campaign(
        {
            "name": "Fjellbrus Vårløp 2026",
            "brand": "Fjellbrus (fictional)",
            "goal": "awareness",
            "category": "general",
            "budget_nok": 180000,
            "start_date": "2026-04-01",
            "end_date": "2026-05-31",
            "landing_url": "https://fjellbrus.example/varlop",
            "brief": (
                "Fictional demo brief. Show Fjellbrus as the drink for the first long spring runs. One feed post "
                "or reel per creator, honest about taste, no health claims. Label every post «Reklame» at the start."
            ),
            "deliverables_template": "1 × reel or video (+ optional story) · discount code VARLOP-<NAME> (15 %)",
        },
        is_demo=True,
    )
    autumn = store.add_campaign(
        {
            "name": "Fjellbrus Høstfjell 2026",
            "brand": "Fjellbrus (fictional)",
            "goal": "sales",
            "category": "general",
            "budget_nok": 120000,
            "start_date": "2026-09-01",
            "end_date": "2026-10-31",
            "landing_url": "https://fjellbrus.example/hostfjell?ref=demo",
            "brief": (
                "Fictional demo brief. Autumn hiking: Fjellbrus in the backpack. Drive code redemptions in the web "
                "shop. Label «Reklame» at the start; use the retouching mark if any filter changes body or skin."
            ),
            "deliverables_template": "1 × reel/video + 1 × story · discount code HOST-<NAME> (20 %)",
        },
        is_demo=True,
    )

    # Spring: ten creators, finished campaign (Reported/Paid), one Paid via a written override.
    spring_people = creator_ids[:10]
    _run_campaign(
        store, rules, spring, spring_people, creators, creator_ids, rng,
        plan=["Reported"] * 7 + ["Paid"] * 3,
        published_on="2026-04-{day:02d}",
        override_index=8,
    )
    # Autumn: ten creators across every stage; one published post is missing its label.
    autumn_people = creator_ids[10:20]
    _run_campaign(
        store, rules, autumn, autumn_people, creators, creator_ids, rng,
        plan=["Shortlist", "Shortlist", "Contacted", "Contacted", "Negotiating", "Contracted", "Content in review",
              "Published", "Published", "Paid"],
        published_on="2026-09-{day:02d}",
        missing_label_index=7,
        unchecked_index=8,
    )


def _run_campaign(
    store: Store,
    rules: RuleSet,
    campaign_id: int,
    people: list[int],
    creators: list[dict],
    creator_ids: list[int],
    rng: random.Random,
    *,
    plan: list[str],
    published_on: str,
    override_index: int | None = None,
    missing_label_index: int | None = None,
    unchecked_index: int | None = None,
) -> None:
    from .storage import STAGES

    campaign = store.campaign(campaign_id)
    code_prefix = "VARLOP" if "Vår" in campaign["name"] else "HOST"
    store.add_to_shortlist(campaign_id, people)
    engagements = store.engagements(campaign_id).set_index("creator_id")["id"].to_dict()
    for position, (creator_id, target) in enumerate(zip(people, plan)):
        creator = creators[creator_ids.index(creator_id)]
        engagement_id = int(engagements[creator_id])
        target_index = STAGES.index(target)
        has_deliverable = target_index >= STAGES.index("Contracted")
        published = target_index >= STAGES.index("Published")
        if has_deliverable:
            platform = _primary_platform(creator)
            fmt = _format_for(platform, rng)
            fee = float(int(round(max(1500, creator["followers"] * rng.uniform(0.22, 0.42)), -2)))
            day = 3 + position * 2
            retouched = rng.random() < 0.3
            deliverable = {
                "platform": platform,
                "format": fmt,
                "due_date": published_on.format(day=day),
                "fee_nok": fee,
                "discount_code": f"{code_prefix}-{creator['name'].split()[0].upper()}",
                "published_date": published_on.format(day=day) if published else "",
                "post_url": "",
                "shows_person": fmt != "post" or rng.random() < 0.7,
            }
            deliverable_id = store.add_deliverable(engagement_id, deliverable)
            if published:
                deliverable["_retouched"] = retouched
                if position == missing_label_index:
                    # The visible warning: the post went out without an advertising label.
                    store.set_answer(deliverable_id, "ad_identified", "no", "Label missing on the published post.")
                    store.set_answer(deliverable_id, "label_wording", "no", "Caption says «samarbeid» only.")
                elif position == unchecked_index:
                    pass  # published but nobody has done the checklist yet
                elif position == override_index:
                    store.set_answer(deliverable_id, "ad_identified", "yes")
                    store.set_override(
                        deliverable_id,
                        "Fictional demo: post was archived before the wording check; screenshot on file shows "
                        "«Reklame» at the start of the caption.",
                    )
                else:
                    _answer_all(store, deliverable_id, rules, campaign, deliverable)
                strength = 1.25 if position % 4 == 0 else (0.7 if position % 5 == 0 else 1.0)
                if target in ("Reported", "Paid") or position == unchecked_index:
                    store.set_results(deliverable_id, _results(creator["followers"], fee, rng, strength))
            if target_index >= STAGES.index("Published") and fmt in ("reel", "video") and rng.random() < 0.35:
                story = dict(deliverable, format="story", fee_nok=float(int(round(fee * 0.35, -2))))
                story_id = store.add_deliverable(engagement_id, story)
                if published and position not in (missing_label_index, unchecked_index):
                    _answer_all(store, story_id, rules, campaign, story)
                if target in ("Reported", "Paid"):
                    store.set_results(story_id, _results(creator["followers"], story["fee_nok"], rng, 0.6))
                if position in (missing_label_index, unchecked_index):
                    store.set_answer(story_id, "ad_identified", "yes")
        for stage in STAGES[1 : target_index + 1]:
            store.move_engagement(engagement_id, stage, rules)
