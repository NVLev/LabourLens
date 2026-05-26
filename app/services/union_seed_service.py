from app.database.models import Union, UnionPortal

UNION_PORTALS = [
    {
        "union": {
            "key": "pam",
            "name_fi": "Palvelualojen ammattiliitto PAM",
            "website": "https://www.pam.fi",
        },
        "portal": {
            "catalog_url": "https://www.pam.fi/tyoehtosopimukset/pamin-alojen-tyoehtosopimukset-aakkosjarjestyksessa/",
        },
    },
    {
        "union": {
            "key": "rakennusliitto",
            "name_fi": "Rakennusliitto",
            "website": "https://rakennusliitto.fi",
        },
        "portal": {
            "catalog_url": "https://rakennusliitto.fi/tyoehtosopimukset/",
        },
    },
    {
            "union": {
                "key": "kirkonalat",
                "name_fi": "Kirkon alat",
                "website": "https://kirkonalat.fi",
            },
            "portal": {
                "catalog_url": "https://kirkonalat.fi/tyoehtosopimukset/",
            },
        },
        {
            "union": {
                "key": "konepaallystoliitto",
                "name_fi": "Suomen Konepäällystöliitto",
                "website": "https://www.konepaallystoliitto.fi",
            },
            "portal": {
                "catalog_url": "https://www.konepaallystoliitto.fi/tyoehtosopimukset/",
            },
        },
]


async def seed_unions_and_portals(session) -> dict:
    from sqlalchemy import select
    created_unions = created_portals = skipped = 0

    for entry in UNION_PORTALS:
        # Union
        result = await session.execute(
            select(Union).where(Union.key == entry["union"]["key"])
        )
        union = result.scalar_one_or_none()
        if union is None:
            union = Union(**entry["union"])
            session.add(union)
            await session.flush()
            created_unions += 1

        # UnionPortal
        result = await session.execute(
            select(UnionPortal).where(
                UnionPortal.union_id == union.id,
                UnionPortal.catalog_url == entry["portal"]["catalog_url"],
            )
        )
        portal = result.scalar_one_or_none()
        if portal is None:
            session.add(UnionPortal(
                union_id=union.id,
                catalog_url=entry["portal"]["catalog_url"],
            ))
            created_portals += 1
        else:
            skipped += 1

    await session.commit()
    return {
        "created_unions": created_unions,
        "created_portals": created_portals,
        "skipped": skipped,
    }