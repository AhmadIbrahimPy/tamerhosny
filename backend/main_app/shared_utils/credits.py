def dedupe_credits(credits, item_attr, extra_label=None):
    """Collapse repeated SongCredit/MediaCredit rows for the same
    song/media/person into one entry, combining every role the person
    played (e.g. singer + composer + arranger on one song) into a single
    "roles" list instead of showing the same card once per role.
    """
    grouped = {}
    order = []
    for credit in credits:
        item = getattr(credit, item_attr)
        if item.pk not in grouped:
            grouped[item.pk] = {item_attr: item, 'roles': []}
            order.append(item.pk)
        label = credit.get_role_display()
        if extra_label:
            extra = extra_label(credit)
            if extra:
                label = f'{label} ({extra})'
        grouped[item.pk]['roles'].append(label)
    return [grouped[pk] for pk in order]
