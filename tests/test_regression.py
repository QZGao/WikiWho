import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from WikiWho.wikiwho import Wikiwho, _match_word_sequences
from WikiWho.utils import split_into_paragraphs

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

ARTICLES = [
    "Adam Himebauch",
    "Splatoon 3",
]


def slug(title):
    return title.lower().replace(" ", "_")


def load_fixture(title):
    rev_path = os.path.join(FIXTURES_DIR, f"{slug(title)}_revisions.json")
    golden_path = os.path.join(FIXTURES_DIR, f"{slug(title)}_golden.json")
    if not os.path.exists(rev_path) or not os.path.exists(golden_path):
        pytest.skip(
            f"Fixtures missing for '{title}' — run 'python -m tests.generate_fixtures' on master first"
        )
    with open(rev_path, encoding="utf-8") as f:
        revisions = json.load(f)
    with open(golden_path, encoding="utf-8") as f:
        golden = json.load(f)
    return revisions, golden


@pytest.mark.parametrize("title", ARTICLES)
def test_token_authorship_matches_master(title):
    revisions, golden = load_fixture(title)

    ww = Wikiwho(title)
    ww.analyse_article(revisions)

    tokens = [
        {
            "str": t.value,
            "token_id": t.token_id,
            "o_rev_id": t.origin_rev_id,
            "in": list(t.inbound),
            "out": list(t.outbound),
        }
        for t in ww.tokens
    ]

    assert len(tokens) == len(golden), (
        f"Token count mismatch: got {len(tokens)}, expected {len(golden)}"
    )
    for i, (got, want) in enumerate(zip(tokens, golden)):
        assert got == want, (
            f"token[{i}] ({got['str']!r}) mismatch:\n  got:  {got}\n  want: {want}"
        )


def test_moved_words_before_link_are_recovered():
    previous = (
        [f"p{index}" for index in range(12)]
        + ["lived", "in", "[[", "victoria", ",", "british", "columbia", "]]", "from", "1900"]
        + [f"q{index}" for index in range(12)]
    )
    current = (
        [f"q{index}" for index in range(12)]
        + ["lived", "in", "[[", "victoria", ",", "british", "columbia", "]]", "from", "1900"]
        + [f"p{index}" for index in range(12)]
    )

    mapping, _ = _match_word_sequences(
        previous,
        current,
        full_text_prev=previous,
        full_text_curr=current,
    )

    assert mapping[current.index("lived")] == previous.index("lived")


def test_template_field_survives_spacing_change_and_move():
    previous_row = [
        "{{", "singlechart", "|", "switzerland", "|", "62", "|",
        "artist", "=", "vanessa", "amorosi", "}}",
    ]
    current_row = [
        "{{", "single", "chart", "|", "switzerland", "|", "62", "|",
        "artist", "=", "vanessa", "amorosi", "}}",
    ]
    previous = previous_row + ["one", "thing", "leads", "2", "another"] + ["tail"] * 8
    current = ["one", "thing", "leads", "2", "another"] + current_row + ["tail"] * 8

    mapping, _ = _match_word_sequences(
        previous,
        current,
        full_text_prev=previous,
        full_text_curr=current,
    )

    assert mapping[current.index("switzerland")] == previous.index("switzerland")


def test_inline_template_end_is_not_split_as_table_markup():
    text = "{{linktext|偉大|}}한 {{linktext|遺産|}}"

    assert split_into_paragraphs(text) == [text]
    assert "{|\n| cell\n|}" in split_into_paragraphs("{|\n| cell\n|}")
